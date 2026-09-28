"""One pipeline for every upload: runs all five check categories on a PDF or image.

    typography  - fonts: retyped fields, covered/overwritten PDF text
    signature   - signature located and compared with a known exemplar
    substrate   - paper: erased/white-out/pasted patches; image noise consistency
    ink         - ink colour and ink spread
    digital     - PDF metadata history, EXIF editing software, compression (info)

Every check returns pass / flag / skipped (with the reason) / info, so the
report states what was examined and what could not be examined from a file.
"""
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from indicators import INDICATORS
from pdf_metadata import analyze_pdf

from .image_checks import check, ink_checks, paper_checks, photo_noise_check, typography_checks
from .layout import analyze_layout
from .pdf_text import embedded_images, pdf_typography_checks
from .signature import signature_checks

CATEGORIES = ["typography", "signature", "substrate", "ink", "digital"]
CATEGORY_LABELS = {"typography": "Font inconsistencies", "signature": "Signature mismatch",
                   "substrate": "Paper anomalies", "ink": "Ink spread & colour", "digital": "Digital metadata"}
PHOTO_NOISE_THRESHOLD = 4.96   # 5% false-positive point on CG-1050 originals
MIN_WORDS_FOR_DOCUMENT = 5
COLOURS = {"typography": (214, 40, 40), "signature": (130, 50, 200), "substrate": (230, 130, 0),
           "ink": (20, 110, 220), "digital": (60, 60, 60)}


def _digital_from_pdf(meta: dict) -> list[dict]:
    names = {"incremental_updates": "Number of saves (hidden re-saves)",
             "producer_editing_tool": "Software that produced the file",
             "mod_after_creation": "Modified after it was created",
             "mod_date_after_issue": "Created or modified after the stated issue date",
             "metadata_inconsistent": "Info metadata vs XMP metadata"}
    out = [check("digital", "Valid PDF file", "pass", f"{meta['size_bytes']:,} bytes"),
           check("digital", "Fingerprint (SHA-256)", "info", meta["sha256"])]
    found = {f["indicator"]: f for f in meta["findings"]}
    for ind, name in names.items():
        f = found.get(ind)
        out.append(check("digital", name, "flag" if f and f["status"] == "present" else "pass", f["note"], ind)
                   if f else check("digital", name, "skipped",
                                   "Enter the stated issue date to run this check" if ind == "mod_date_after_issue"
                                   else "Information not present in this file", ind))
    out.append(check("digital", "Digital signature", "info",
                     "Present (not validated)" if meta["has_digital_signature"] else "No digital signature in file"))
    return out


def _digital_from_image(img: Image.Image) -> list[dict]:
    from image_checker import EDITING_SOFTWARE, perform_ela
    exif = img.getexif()
    software = exif.get(0x0131) if exif else None
    out = [check("digital", "Valid image file", "pass", f"{img.format or 'image'}, {img.width}×{img.height} px, mode {img.mode}")]
    if software:
        hit = next((t for t in EDITING_SOFTWARE if t in str(software).lower()), None)
        out.append(check("digital", "Editing software in EXIF metadata", "flag" if hit else "pass",
                         f"EXIF Software: {software}" + (f" (editing tool '{hit}')" if hit else ""), "editing_software_in_exif"))
    else:
        out.append(check("digital", "Editing software in EXIF metadata", "skipped",
                         "No EXIF Software tag (common after screenshots, messaging apps or metadata stripping)"))
    ela = float(perform_ela(img))
    out.append(check("digital", "Error Level Analysis", "info",
                     f"ELA score {ela:.1f} - shown for reference only; not used in the verdict because it measured "
                     "at chance level (49.9%) on 1,460 benchmark images", metrics={"ela": round(ela, 2)}))
    return out


def _image_checks(img: Image.Image, exemplar, label: str = "") -> tuple[list[dict], object]:
    page = analyze_layout(img)
    checks = []
    if len(page.words) >= MIN_WORDS_FOR_DOCUMENT:
        checks += typography_checks(page) + ink_checks(page) + paper_checks(page)
    else:
        reason = "No printed text found - treated as a photograph"
        checks += [check("typography", "Font consistency", "skipped", reason),
                   check("ink", "Ink colour and spread", "skipped", reason),
                   photo_noise_check(page, PHOTO_NOISE_THRESHOLD)]
    checks += signature_checks(page, exemplar)
    if label:
        for c in checks:
            c["check"] = f"{c['check']} ({label})"
    return checks, page


def _evidence_png(page, checks: list[dict]) -> str | None:
    boxes = [(c["category"], r) for c in checks if c["result"] == "flag" for r in c["regions"]]
    if page is None:
        return None
    img = Image.fromarray(page.rgb.astype(np.uint8))
    draw = ImageDraw.Draw(img)
    for n, (cat, (x0, y0, x1, y1)) in enumerate(boxes, start=1):
        colour = COLOURS[cat]
        for k in range(3):
            draw.rectangle([x0 - 2 - k, y0 - 2 - k, x1 + 2 + k, y1 + 2 + k], outline=colour)
        tag = f"{n} {CATEGORY_LABELS[cat]}"
        tw = draw.textlength(tag)
        ty = max(0, y0 - 18)
        draw.rectangle([x0 - 4, ty, x0 + tw + 6, ty + 15], fill=colour)
        draw.text((x0, ty + 1), tag, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def summarise(checks: list[dict]) -> dict:
    out = {}
    for cat in CATEGORIES:
        mine = [c for c in checks if c["category"] == cat]
        flags = sum(c["result"] == "flag" for c in mine)
        passes = sum(c["result"] == "pass" for c in mine)
        out[cat] = {"label": CATEGORY_LABELS[cat], "status": "flag" if flags else "pass" if passes else "skipped",
                    "flagged": flags, "passed": passes, "checks": len(mine)}
    return out


def findings_from(checks: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for c in checks:
        ind = c.get("indicator")
        if ind not in INDICATORS or c["result"] not in ("flag", "pass"):
            continue
        status = "present" if c["result"] == "flag" else "absent"
        if ind in best and best[ind]["status"] == "present":
            continue
        best[ind] = {"indicator": ind, "status": status, "confidence": "moderate",
                     "note": c["detail"][:300], "source": "automated"}
    return list(best.values())


def analyze_document(path: str, *, stated_issue_date: str = "", expected_producer: str = "",
                     generated_on_demand: bool = False, exemplar_path: str | None = None) -> dict:
    p = Path(path)
    data = p.read_bytes()
    exemplar = Image.open(exemplar_path) if exemplar_path else None
    checks: list[dict] = []
    page = None
    meta = None
    if data.startswith(b"%PDF-"):
        kind = "pdf"
        meta = analyze_pdf(path, stated_issue_date=stated_issue_date, expected_producer=expected_producer,
                           generated_on_demand=generated_on_demand)
        checks += _digital_from_pdf(meta)
        typo, _info = pdf_typography_checks(path)
        checks += typo
        from pypdf import PdfReader
        images = embedded_images(PdfReader(path))
        if images:
            for label, img in images[:3]:
                img_checks, img_page = _image_checks(img, exemplar, label)
                checks += img_checks
                page = page or img_page
        else:
            reason = "Text-only PDF - no scanned image inside to examine for handwriting, paper or ink"
            checks += [check("signature", "Signature comparison", "skipped", reason),
                       check("substrate", "Background tone and texture", "skipped", reason),
                       check("ink", "Ink colour and spread", "skipped", reason)]
    else:
        kind = "image"
        img = Image.open(path)
        img.load()
        checks += _digital_from_image(img)
        img_checks, page = _image_checks(img, exemplar)
        checks += img_checks

    return {
        "file": p.name,
        "kind": kind,
        "sha256": hashlib.sha256(data).hexdigest(),
        "checks": checks,
        "summary": summarise(checks),
        "findings": findings_from(checks),
        "evidence_png": _evidence_png(page, checks),
        "pdf_metadata": meta,
    }
