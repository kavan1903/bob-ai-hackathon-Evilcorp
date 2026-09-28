"""
generate_dataset.py
====================
Scans every image in the CG-1050 ORIGINAL / TAMPERED split, runs the full
five-category forensic pipeline, and writes two artefacts:

  dataset/training_features.csv   – one row per image, all five feature columns
  dataset/training_features.json  – same data, richer (includes sub-check details)

Five feature columns (one per required check):
  font_inconsistencies   – typography category: flag / pass / skipped
  signature_mismatch     – signature category: flag / pass / skipped
  paper_anomalies        – substrate category: flag / pass / skipped
  ink_spread             – ink category: flag / pass / skipped
  digital_metadata_flags – digital category: flag / pass / skipped

Additional columns carried through for ML / analysis:
  filename, label (0 = original, 1 = tampered), tamper_type,
  category_flags_total (0-5 count of "flag" categories),
  [all raw check details as json string]

Usage
-----
Run from the src/mcp_server directory so the local imports resolve:

    cd bob-ai-hackathon-doc-forge/src/mcp_server
    python generate_dataset.py

Optional overrides via environment variables:
    DATASET_ROOT   – path to the TRAINING folder (default: auto-detected)
    OUT_DIR        – where to write output files      (default: <repo>/dataset)
    MAX_PER_CLASS  – cap images per class for quick tests (default: 0 = all)
"""
from __future__ import annotations

import csv
import json
import os
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution – works whether invoked from the repo root or this dir.
# ---------------------------------------------------------------------------
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[1]

DATASET_ROOT_DEFAULT = (
    Path("C:/Users/hp/OneDrive/Desktop/Hackathon/datasets/cg1050/TRAINING_CG-1050/TRAINING")
)
DATASET_ROOT = Path(os.environ.get("DATASET_ROOT", DATASET_ROOT_DEFAULT))
OUT_DIR = Path(os.environ.get("OUT_DIR", REPO_ROOT / "dataset"))
MAX_PER_CLASS = int(os.environ.get("MAX_PER_CLASS", "0"))

# Add src/mcp_server to sys.path so doc_checks imports work.
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

# ---------------------------------------------------------------------------
# Tamper-type decoding from CG-1050 filename conventions
# ---------------------------------------------------------------------------
TAMPER_SUFFIX_MAP = {
    "_r":    "resampling",
    "_col":  "colour_manipulation",
    "_cm":   "copy_move",
    "_f":    "forgery",
    "_cp":   "copy_paste",
    "_cmfr": "copy_move_forgery",
}

def tamper_type_from_filename(name: str) -> str:
    stem = Path(name).stem.lower()
    # longer suffixes first to avoid partial matches
    for suffix, label in sorted(TAMPER_SUFFIX_MAP.items(), key=lambda x: -len(x[0])):
        # strip trailing digit: e.g. _r2, _col3
        for variant in (stem, stem.rstrip("1234567890")):
            if variant.endswith(suffix):
                return label
    return "unknown"


# ---------------------------------------------------------------------------
# Pipeline import
# ---------------------------------------------------------------------------
try:
    from doc_checks.pipeline import analyze_document, CATEGORIES, CATEGORY_LABELS
    PIPELINE_OK = True
except ImportError as _e:
    print(f"[WARN] Could not import doc_checks.pipeline: {_e}")
    print("       Falling back to master_pipeline (OpenCV-based checks only).")
    PIPELINE_OK = False

if not PIPELINE_OK:
    # Fallback: use master_pipeline which has the four OpenCV checks + ELA.
    from master_pipeline import (
        check_font_inconsistencies,
        check_paper_anomalies,
        check_ink_spread,
        check_signature_mismatch,
    )
    from image_checker import analyze_image

    def _fallback_analyze(path: str) -> dict:
        """Mimics the five-category summary using the OpenCV stubs."""
        img_res = analyze_image(path)
        # digital: ELA + EXIF from image_checker
        digital_flag = any(
            f["status"] == "present" for f in img_res.get("findings", [])
        )
        font_res = check_font_inconsistencies(path)
        paper_res = check_paper_anomalies(path)
        ink_res = check_ink_spread(path)
        sig_res = check_signature_mismatch(path)

        def _to_status(r):
            return "flag" if r.get("status") == "present" else "pass"

        summary = {
            "typography": {"status": _to_status(font_res),  "detail": font_res.get("note", "")},
            "signature":  {"status": _to_status(sig_res),   "detail": sig_res.get("note", "")},
            "substrate":  {"status": _to_status(paper_res), "detail": paper_res.get("note", "")},
            "ink":        {"status": _to_status(ink_res),   "detail": ink_res.get("note", "")},
            "digital":    {"status": "flag" if digital_flag else "pass",
                           "detail": "; ".join(f.get("note", "") for f in img_res.get("findings", []))},
        }
        return {"summary": summary, "checks": []}


# ---------------------------------------------------------------------------
# Core per-image analysis
# ---------------------------------------------------------------------------
CATEGORY_TO_FEATURE = {
    "typography": "font_inconsistencies",
    "signature":  "signature_mismatch",
    "substrate":  "paper_anomalies",
    "ink":        "ink_spread",
    "digital":    "digital_metadata_flags",
}


def analyze_one(path: str) -> dict:
    """Run the pipeline on one image and return a flat feature dict."""
    if PIPELINE_OK:
        try:
            result = analyze_document(path)
            summary = result["summary"]
            checks = result["checks"]
        except Exception as exc:
            tb = traceback.format_exc()
            # Return a row that records the error but keeps the schema intact.
            return {feat: "error" for feat in CATEGORY_TO_FEATURE.values()} | {
                "category_flags_total": -1,
                "error": str(exc)[:200],
                "checks_json": json.dumps({"error": str(exc), "trace": tb[:500]}),
            }
    else:
        result = _fallback_analyze(path)
        summary = result["summary"]
        checks = result["checks"]

    features: dict[str, str] = {}
    flags_total = 0
    for cat, feat in CATEGORY_TO_FEATURE.items():
        status = summary.get(cat, {}).get("status", "skipped")
        features[feat] = status
        if status == "flag":
            flags_total += 1

    # Compact per-check details for the JSON output.
    check_details = [
        {
            "category": c["category"],
            "check": c["check"],
            "result": c["result"],
            "detail": c.get("detail", "")[:300],
        }
        for c in checks
        if c["result"] in ("flag", "pass")
    ]

    return features | {
        "category_flags_total": flags_total,
        "error": "",
        "checks_json": json.dumps(check_details),
    }


# ---------------------------------------------------------------------------
# Collect image paths
# ---------------------------------------------------------------------------
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def collect_images(root: Path) -> list[tuple[Path, int]]:
    """Return (path, label) pairs: 0 = ORIGINAL, 1 = TAMPERED."""
    pairs: list[tuple[Path, int]] = []
    for label, sub in ((0, "ORIGINAL"), (1, "TAMPERED")):
        folder = root / sub
        if not folder.exists():
            print(f"[WARN] Folder not found: {folder}")
            continue
        imgs = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if MAX_PER_CLASS > 0:
            imgs = imgs[:MAX_PER_CLASS]
        pairs.extend((p, label) for p in imgs)
        print(f"  {sub}: {len(imgs)} images")
    return pairs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
CSV_FIELDS = [
    "filename",
    "label",
    "tamper_type",
    "font_inconsistencies",
    "signature_mismatch",
    "paper_anomalies",
    "ink_spread",
    "digital_metadata_flags",
    "category_flags_total",
    "error",
]


def main() -> None:
    if not DATASET_ROOT.exists():
        print(f"[ERROR] Dataset root not found: {DATASET_ROOT}")
        print("        Set the DATASET_ROOT environment variable to the correct path.")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "training_features.csv"
    json_path = OUT_DIR / "training_features.json"

    print(f"Dataset root : {DATASET_ROOT}")
    print(f"Output dir   : {OUT_DIR}")
    print(f"Pipeline     : {'doc_checks (full 5-category)' if PIPELINE_OK else 'master_pipeline (OpenCV fallback)'}")
    if MAX_PER_CLASS:
        print(f"Max per class: {MAX_PER_CLASS}")
    print()

    images = collect_images(DATASET_ROOT)
    print(f"\nTotal images: {len(images)}\n")

    rows: list[dict] = []
    json_rows: list[dict] = []
    errors = 0

    for i, (img_path, label) in enumerate(images, start=1):
        prefix = f"[{i:>4}/{len(images)}]"
        print(f"{prefix} {img_path.name} ...", end="", flush=True)

        features = analyze_one(str(img_path))
        ttype = "genuine" if label == 0 else tamper_type_from_filename(img_path.name)

        row = {
            "filename":     img_path.name,
            "label":        label,
            "tamper_type":  ttype,
        } | {k: features[k] for k in [
            "font_inconsistencies",
            "signature_mismatch",
            "paper_anomalies",
            "ink_spread",
            "digital_metadata_flags",
            "category_flags_total",
            "error",
        ]}

        rows.append(row)
        json_row = {**row, "checks": json.loads(features["checks_json"])}
        json_rows.append(json_row)

        flag_count = row["category_flags_total"]
        err_tag = f" [ERROR: {features['error'][:60]}]" if features["error"] else ""
        print(f" flags={flag_count}{err_tag}")
        if features["error"]:
            errors += 1

    # ------------------------------------------------------------------ CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    # ----------------------------------------------------------------- JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_rows, f, indent=2)

    # ----------------------------------------------------------- Stats summary
    total = len(rows)
    orig_rows  = [r for r in rows if r["label"] == 0]
    tamp_rows  = [r for r in rows if r["label"] == 1]

    print("\n" + "=" * 64)
    print(f"Dataset generation complete  –  {total} images processed ({errors} errors)")
    print(f"  ORIGINAL: {len(orig_rows)}   TAMPERED: {len(tamp_rows)}")
    print()
    print(f"{'Feature':<30}  {'orig flag%':>10}  {'tamp flag%':>10}")
    print("-" * 56)
    for feat in [
        "font_inconsistencies",
        "signature_mismatch",
        "paper_anomalies",
        "ink_spread",
        "digital_metadata_flags",
    ]:
        o_pct = 100 * sum(1 for r in orig_rows if r[feat] == "flag") / max(len(orig_rows), 1)
        t_pct = 100 * sum(1 for r in tamp_rows if r[feat] == "flag") / max(len(tamp_rows), 1)
        print(f"  {feat:<28}  {o_pct:>9.1f}%  {t_pct:>9.1f}%")

    print(f"\nOutput files:")
    print(f"  CSV  -> {csv_path}")
    print(f"  JSON -> {json_path}")
    print("=" * 64)


if __name__ == "__main__":
    main()
