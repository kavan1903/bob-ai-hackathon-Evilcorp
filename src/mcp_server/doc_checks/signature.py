"""Signature location and comparison against a known (exemplar) signature.

Features are size-independent: aspect ratio, slant, ink distribution on a
coarse grid, horizontal/vertical projection profiles and boundary roughness
(tremor). A near pixel-identical match is reported separately, because a
genuine writer never produces two identical signatures - an exact copy means
the signature was transplanted (cut-and-paste or digital overlay).
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from .layout import Page, otsu

# Midpoint between same-writer (<=0.06) and forged/other-writer (>=0.21) scores on the synthetic
# test set; must be re-calibrated on a real signature corpus (e.g. CEDAR) before casework use.
MISMATCH_THRESHOLD = 0.13
IDENTICAL_IOU = 0.93


def locate(page: Page) -> tuple[list[int], np.ndarray] | None:
    """Return (box, ink mask) of the most signature-like region, or None."""
    g = page.glyph_height
    ph, pw = page.ink.shape
    # Thin strokes that are neither text nor page-spanning rules/frames/borders.
    strokes = [c for c in page.graphics if c["fill"] < 0.35 and c["area"] > 3 * g * g * 0.1
               and c["w"] < 0.5 * pw and c["h"] < 0.4 * ph and c["h"] > 1.5 * g]
    if not strokes:
        return None
    groups: list[list[dict]] = []
    for c in sorted(strokes, key=lambda c: c["x0"]):
        for grp in groups:
            gx1 = max(p["x1"] for p in grp); gy0 = min(p["y0"] for p in grp); gy1 = max(p["y1"] for p in grp)
            if c["x0"] <= gx1 + 3 * g and c["y0"] <= gy1 + 2 * g and c["y1"] >= gy0 - 2 * g:
                grp.append(c)
                break
        else:
            groups.append([c])
    best = max(groups, key=lambda grp: sum(p["area"] for p in grp))
    x0 = min(p["x0"] for p in best); y0 = min(p["y0"] for p in best)
    x1 = max(p["x1"] for p in best); y1 = max(p["y1"] for p in best)
    pad = int(g)
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(page.ink.shape[1], x1 + pad), min(page.ink.shape[0], y1 + pad)
    word_ids = set()
    for w in page.words:
        wx0, wy0, wx1, wy1 = w.box
        ids = np.unique(page.labels[wy0:wy1, wx0:wx1])
        word_ids.update(int(i) for i in ids if i > 0)
    sub = page.labels[y0:y1, x0:x1]
    mask = page.ink[y0:y1, x0:x1] & ~np.isin(sub, list(word_ids))
    return [x0, y0, x1, y1], mask


def mask_from_image(img: Image.Image) -> np.ndarray:
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    return gray < otsu(gray)


def _crop(mask: np.ndarray) -> np.ndarray:
    ys, xs = np.nonzero(mask)
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def features(mask: np.ndarray) -> dict:
    m = _crop(mask)
    h, w = m.shape
    ys, xs = np.nonzero(m)
    yc, xc = ys - ys.mean(), xs - xs.mean()
    slant = float(np.arctan2((xc * yc).mean(), (yc * yc).mean() + 1e-6))
    norm = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((192, 64), Image.BILINEAR), dtype=np.float32) / 255
    grid = norm.reshape(4, 16, 12, 16).mean(axis=(1, 3)).ravel()
    hprof = norm.mean(axis=1); vprof = norm.reshape(64, 48, 4).mean(axis=(0, 2))
    perim = float((m & ~ndi.binary_erosion(m)).sum())
    smooth = ndi.binary_closing(m, iterations=2)
    rough = perim / max(float((smooth & ~ndi.binary_erosion(smooth)).sum()), 1.0)
    return {"aspect": w / h, "slant": slant, "grid": grid, "hprof": hprof, "vprof": vprof,
            "density": float(m.mean()), "rough": rough, "norm": norm}


def _corr(a, b) -> float:
    a, b = a - a.mean(), b - b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def compare(questioned: np.ndarray, exemplar: np.ndarray) -> dict:
    q, e = features(questioned), features(exemplar)
    inter = np.minimum(q["norm"], e["norm"]).sum(); union = np.maximum(q["norm"], e["norm"]).sum()
    iou = float(inter / (union + 1e-9))
    parts = {
        "proportions": abs(np.log(q["aspect"] / e["aspect"])),
        "slant": abs(q["slant"] - e["slant"]),
        "ink layout": (1 - _corr(q["grid"], e["grid"])) / 2,
        "profiles": (2 - _corr(q["hprof"], e["hprof"]) - _corr(q["vprof"], e["vprof"])) / 4,
        "stroke roughness": abs(np.log(q["rough"] / e["rough"])),
    }
    weights = {"proportions": 0.8, "slant": 1.2, "ink layout": 1.0, "profiles": 1.0, "stroke roughness": 1.5}
    distance = float(sum(weights[k] * v for k, v in parts.items()) / sum(weights.values()))
    return {"distance": round(distance, 3), "iou": round(iou, 3), "identical": iou >= IDENTICAL_IOU,
            "components": {k: round(float(v), 3) for k, v in parts.items()},
            "slant_deg": (round(float(np.degrees(q["slant"])), 1), round(float(np.degrees(e["slant"])), 1)),
            "roughness": (round(q["rough"], 3), round(e["rough"], 3))}


def signature_checks(page: Page | None, exemplar: Image.Image | None, questioned_crop: Image.Image | None = None) -> list[dict]:
    from .image_checks import check
    if questioned_crop is not None:
        qmask, box = mask_from_image(questioned_crop), None
    else:
        found = locate(page) if page is not None else None
        if found is None:
            return [check("signature", "Signature comparison", "skipped", "No signature-like handwriting found in the document")]
        box, qmask = found
    if qmask.sum() < 30:
        return [check("signature", "Signature comparison", "skipped", "Signature region contains too little ink to analyse")]
    regions = [box] if box else []
    if exemplar is None:
        return [check("signature", "Signature comparison", "skipped",
                      "Signature located" + (f" at {tuple(box)}" if box else "") +
                      " - upload a known genuine signature of the same person to compare", regions=regions)]
    res = compare(qmask, mask_from_image(exemplar))
    out = [check("signature", "Exact-copy (transplanted signature) test", "flag" if res["identical"] else "pass",
                 f"Signature is {res['iou'] * 100:.0f}% pixel-identical to the exemplar - genuine signatures always vary; "
                 "an exact copy indicates it was pasted" if res["identical"]
                 else f"Signature is not an exact copy of the exemplar ({res['iou'] * 100:.0f}% overlap)",
                 "auto_signature_identical", regions if res["identical"] else [], res)]
    if not res["identical"]:
        worst = max(res["components"], key=res["components"].get)
        mismatch = res["distance"] > MISMATCH_THRESHOLD
        out.append(check("signature", "Signature comparison with exemplar", "flag" if mismatch else "pass",
                         f"Difference score {res['distance']:.2f} (threshold {MISMATCH_THRESHOLD}); biggest difference: {worst}; "
                         f"slant {res['slant_deg'][0]}° vs {res['slant_deg'][1]}°, roughness {res['roughness'][0]} vs {res['roughness'][1]}",
                         "auto_signature_mismatch", regions if mismatch else [], res))
    return out
