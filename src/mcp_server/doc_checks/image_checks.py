"""Image-based checks for three of the five categories:

- typography: characters that have no identical twin elsewhere on the page
  (retyped in another font), and stroke-weight outliers with sharp edges
- ink: colour (hue) outliers among text of the same size, and ink spread
  (thicker strokes with softer edges)
- paper: background patches whose tone or grain differs from the rest of the
  sheet (erasure, white-out, pasted paper); noise inconsistency for photos

Each word is only compared with words of similar size, so headings and small
labels are never judged against body text.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

from .layout import Page, Word, robust_z

TWIN_DISTANCE = 0.06
MIN_GLYPHS_FOR_TWIN = 5


def check(category, name, result, detail, indicator=None, regions=None, metrics=None) -> dict:
    return {"category": category, "check": name, "result": result, "detail": detail,
            "indicator": indicator, "regions": regions or [], "metrics": metrics or {}}


def _peers(words: list[Word], w: Word, tol: float = 0.25) -> list[Word]:
    return [o for o in words if o is not w and abs(o.height - w.height) <= tol * w.height]


def _box_text(boxes) -> str:
    return ", ".join(f"({b[0]},{b[1]})-({b[2]},{b[3]})" for b in boxes[:4]) + (" …" if len(boxes) > 4 else "")


# ---------------------------------------------------------------- typography
def _text_lines(page: Page) -> list[dict]:
    """Group words into text lines (the unit a forger retypes: a field value or a sentence)."""
    lines: dict[int, list[Word]] = {}
    for w in page.words:
        lines.setdefault(w.line, []).append(w)
    out = []
    for idx, ws in lines.items():
        out.append({"line": idx, "words": ws,
                    "box": (min(w.box[0] for w in ws), min(w.box[1] for w in ws),
                            max(w.box[2] for w in ws), max(w.box[3] for w in ws)),
                    "height": float(np.median([w.height for w in ws])),
                    "sharpness": float(np.median([w.sharpness for w in ws]))})
    return out


def _glyph_table(page: Page) -> dict:
    """All glyphs as normalised 32x48 darkness images, tagged with their text line."""
    objs = ndi.find_objects(page.labels)
    span = max(page.paper_level - page.ink_level, 1.0)
    imgs, hs, ws, lines = [], [], [], []
    for w in page.words:
        x0, y0, x1, y1 = w.box
        ids = np.unique(page.labels[y0:y1, x0:x1])
        for i in ids[ids > 0]:
            sl = objs[i - 1]
            gy0, gy1, gx0, gx1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
            if gy1 - gy0 < 0.5 * w.height:
                continue
            g = page.gray[max(gy0 - 1, 0):gy1 + 1, max(gx0 - 1, 0):gx1 + 1]
            dark = Image.fromarray((np.clip((page.paper_level - g) / span, 0, 1) * 255).astype(np.uint8))
            nw = max(1, round(dark.width * 32 / dark.height))
            a = np.asarray(dark.resize((nw, 32), Image.BILINEAR), dtype=np.float32) / 255
            canvas = np.zeros((32, 48), dtype=np.float32)
            off = max(0, (48 - nw) // 2)
            canvas[:, off:off + min(nw, 48)] = a[:, :48]
            imgs.append(canvas); hs.append(gy1 - gy0); ws.append(gx1 - gx0); lines.append(w.line)
    imgs = np.stack(imgs) if imgs else np.zeros((0, 32, 48), np.float32)
    return {"img": imgs, "mass": imgs.reshape(len(imgs), -1).sum(1), "h": np.array(hs, float),
            "w": np.array(ws, float), "line": np.array(lines)}


NEAR_TWIN_BAND = (0.10, 0.40)


def _twin_stats(page: Page) -> dict[int, dict]:
    """Per text line: share of characters with an identical twin in another line, and share that
    are 'near twins' (similar but not identical - the same character in a different font)."""
    t = _glyph_table(page)
    n = len(t["img"])
    best = np.ones(n)
    size_ratio = np.ones(n)
    flat = t["img"].reshape(n, -1)
    for i in range(n):
        cand = ((t["line"] != t["line"][i]) & (np.abs(t["h"] - t["h"][i]) <= np.maximum(2, 0.12 * t["h"][i]))
                & (np.abs(t["w"] - t["w"][i]) <= np.maximum(2, 0.35 * t["w"][i])))
        if cand.any():
            idx = np.nonzero(cand)[0]
            d = np.abs(flat[idx] - flat[i]).sum(1) / (t["mass"][idx] + t["mass"][i] + 1e-6)
            k = int(d.argmin())
            best[i] = float(d[k])
            size_ratio[i] = t["h"][i] / t["h"][idx[k]]
    stats = {}
    for ln in np.unique(t["line"]):
        sel = t["line"] == ln
        b = best[sel]
        stats[int(ln)] = {"n": int(len(b)), "twins": float((b <= TWIN_DISTANCE).mean()),
                          "near": float(((b > NEAR_TWIN_BAND[0]) & (b <= NEAR_TWIN_BAND[1])).mean()),
                          "size_ratio": float(np.median(size_ratio[sel]))}
    return stats


def _column_siblings(lines: list[dict], ln: dict, tol: float) -> list[dict]:
    return [o for o in lines if o is not ln and abs(o["box"][0] - ln["box"][0]) <= tol
            and abs(o["height"] - ln["height"]) <= 0.15 * ln["height"]]


def typography_checks(page: Page) -> list[dict]:
    checks = []
    st = _twin_stats(page)
    lines = [ln for ln in _text_lines(page) if st.get(ln["line"], {}).get("n", 0) >= MIN_GLYPHS_FOR_TWIN]
    tol = max(4.0, 0.6 * page.glyph_height)
    fields = [ln for ln in lines if len(_column_siblings(lines, ln, tol)) >= 2]
    if not fields:
        checks.append(check("typography", "Character consistency across aligned text lines", "skipped",
                            "No column of same-size text lines with enough repeated characters to compare"))
    else:
        flagged = []
        for ln in fields:
            sib = _column_siblings(lines, ln, tol)
            ref = float(np.median([st[o["line"]]["twins"] for o in sib]))
            sharp_ref = float(np.median([o["sharpness"] for o in sib]))
            s = st[ln["line"]]
            soft = ln["sharpness"] < 0.9 * sharp_ref   # blurred text is an ink question, not a font one
            # Near-twins that are consistently smaller/larger mean the same font at another size
            # (e.g. a smaller label) - only same-size near-twins indicate a different font.
            same_size = abs(s["size_ratio"] - 1.0) <= 0.06
            if s["twins"] <= 0.2 and s["near"] >= 0.5 and ref >= 0.5 and same_size and not soft:
                flagged.append(ln["box"])
        checks.append(check(
            "typography", "Character consistency across aligned text lines", "flag" if flagged else "pass",
            (f"{len(flagged)} line(s) whose characters resemble - but never exactly match - the same characters in "
             f"neighbouring lines (likely retyped in a different font): {_box_text(flagged)}") if flagged else
            f"Characters in {len(fields)} aligned text lines match identical characters elsewhere on the page",
            "auto_font_inconsistent", flagged, {"lines_compared": len(fields)}))

    weight_flags = []
    for w in page.words:
        peers = _peers(page.words, w)
        if len(peers) < 3:
            continue
        ratio_ref = np.median([p.stroke_ratio for p in peers])
        sharp_ref = np.median([p.sharpness for p in peers])
        if w.stroke_ratio >= 1.4 * ratio_ref and w.sharpness > 0.9 * sharp_ref:
            weight_flags.append(w.box)
    checks.append(check(
        "typography", "Stroke weight consistency", "flag" if weight_flags else "pass",
        f"{len(weight_flags)} text run(s) printed noticeably bolder than text of the same size: {_box_text(weight_flags)}"
        if weight_flags else "Stroke weight is consistent among text of the same size",
        "auto_font_inconsistent", weight_flags))
    return checks


# ---------------------------------------------------------------------- ink
def _chroma(c: np.ndarray) -> np.ndarray:
    r, g, b = c
    # Hue carries the ink identity; lightness is down-weighted because thin strokes read lighter.
    return np.array([r - g, b - (r + g) / 2, 0.15 * (0.299 * r + 0.587 * g + 0.114 * b)])


def ink_checks(page: Page) -> list[dict]:
    checks = []
    colour_flags, details = [], []
    for w in page.words:
        peers = _peers(page.words, w)
        if len(peers) < 3:
            continue
        ref = np.median([_chroma(p.color) for p in peers], axis=0)
        d = float(np.linalg.norm(_chroma(w.color) - ref))
        spread = np.median([np.linalg.norm(_chroma(p.color) - ref) for p in peers])
        if d > max(14.0, 5 * spread):
            colour_flags.append(w.box)
            details.append(f"RGB {tuple(int(v) for v in w.color)}")
    comparable = sum(1 for w in page.words if len(_peers(page.words, w)) >= 3)
    if comparable < 4:
        checks.append(check("ink", "Ink colour consistency", "skipped", "Not enough text of the same size to compare ink colour"))
    else:
        checks.append(check(
            "ink", "Ink colour consistency", "flag" if colour_flags else "pass",
            f"{len(colour_flags)} text run(s) in a different ink colour from text of the same size "
            f"({'; '.join(details[:3])}): {_box_text(colour_flags)}" if colour_flags
            else f"Ink colour is consistent across {comparable} comparable text runs",
            "auto_ink_colour_mismatch", colour_flags))

    spread_flags = []
    for w in page.words:
        peers = _peers(page.words, w)
        if len(peers) < 3:
            continue
        ratio_ref = np.median([p.stroke_ratio for p in peers])
        sharp_ref = np.median([p.sharpness for p in peers])
        thick_soft = w.stroke_ratio >= 1.4 * ratio_ref and w.sharpness <= 0.9 * sharp_ref
        blurred = w.sharpness <= 0.75 * sharp_ref
        if thick_soft or blurred:
            spread_flags.append(w.box)
    if comparable < 4:
        checks.append(check("ink", "Ink spread / edge sharpness", "skipped", "Not enough text of the same size to compare"))
    else:
        checks.append(check(
            "ink", "Ink spread / edge sharpness", "flag" if spread_flags else "pass",
            f"{len(spread_flags)} text run(s) with thicker, softer-edged strokes than text of the same size "
            f"(ink feathering / spread): {_box_text(spread_flags)}" if spread_flags
            else "Ink edges are equally sharp across comparable text",
            "auto_ink_spread", spread_flags))
    return checks


# -------------------------------------------------------------------- paper
def paper_checks(page: Page) -> list[dict]:
    checks = []
    gray = page.gray
    tile = int(max(12, round(2 * page.glyph_height)))
    near_ink = ndi.binary_dilation(page.ink, iterations=3)
    resid = np.abs(gray - ndi.median_filter(gray, size=3))
    rows, cols = gray.shape[0] // tile, gray.shape[1] // tile
    means = np.full((rows, cols), np.nan)
    noise = np.full((rows, cols), np.nan)
    for r in range(rows):
        for c in range(cols):
            sl = (slice(r * tile, (r + 1) * tile), slice(c * tile, (c + 1) * tile))
            ok = ~near_ink[sl]
            if ok.mean() < 0.4:
                continue
            m = float(gray[sl][ok].mean())
            if abs(m - page.paper_level) > 25:
                continue
            means[r, c] = m
            noise[r, c] = float(resid[sl][ok].mean())
    valid = ~np.isnan(means)
    if valid.sum() < 20:
        checks.append(check("substrate", "Background tone and texture", "skipped",
                            "Too little visible paper background to analyse"))
    else:
        zm = np.full_like(means, np.nan); zn = np.full_like(noise, np.nan)
        zm[valid] = robust_z(means[valid], 0.004)
        zn[valid] = robust_z(noise[valid], 0.05)
        nref = np.median(noise[valid])
        smooth_bright = (zm > 4) & (noise < 0.7 * nref)
        strong = np.abs(zm) > 8
        smooth = zn < -4
        flagged = np.where(valid, smooth_bright | strong | smooth, False)
        lab, n = ndi.label(flagged)
        regions = []
        for i, sl in enumerate(ndi.find_objects(lab), start=1):
            if (lab[sl] == i).sum() >= 2:
                regions.append([sl[1].start * tile, sl[0].start * tile, sl[1].stop * tile, sl[0].stop * tile])
        checks.append(check(
            "substrate", "Background tone and texture", "flag" if regions else "pass",
            f"{len(regions)} background patch(es) lighter/smoother or differently textured than the rest of the sheet "
            f"(possible erasure, white-out or pasted paper): {_box_text(regions)}" if regions
            else f"Paper tone and grain are uniform across {int(valid.sum())} background tiles",
            "auto_paper_patch", regions,
            {"tiles": int(valid.sum()), "paper_level": round(page.paper_level, 1), "grain": round(float(nref), 2)}))
    checks.append(check("substrate", "UV fluorescence, watermark, security features", "skipped",
                        "Physical properties cannot be seen in an uploaded file - examine the original under UV / transmitted light"))
    return checks


def photo_noise_check(page: Page, threshold: float) -> dict:
    img = Image.fromarray(page.gray.astype(np.uint8))
    resid = np.abs(page.gray - np.asarray(img.filter(ImageFilter.MedianFilter(3)), dtype=np.float32))
    h, w = resid.shape
    bh, bw = max(h // 4, 1), max(w // 4, 1)
    blocks = [float(resid[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw].mean()) for i in range(4) for j in range(4)]
    blocks = [b for b in blocks if b > 0.02] or [1e-6]
    ratio = max(blocks) / (float(np.median(blocks)) + 1e-6)
    return check("substrate", "Noise consistency across the image", "flag" if ratio > threshold else "pass",
                 f"Noisiest region is {ratio:.2f}x the typical noise level (threshold {threshold:.2f})",
                 "auto_noise_inconsistent", metrics={"noise_ratio": round(ratio, 3)})
