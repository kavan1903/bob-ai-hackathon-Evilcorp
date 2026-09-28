"""Page layout analysis shared by the image detectors.

Finds ink, groups glyphs into text lines and words, and measures each word:
height, stroke width, stroke-width variation (serif/contrast), ink colour,
edge transition (spread) and the surrounding paper tone.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

MAX_SIDE = 2200


@dataclass
class Word:
    box: tuple[int, int, int, int]
    height: float
    stroke: float
    stroke_cv: float
    color: np.ndarray
    transition: float
    line: int
    n_glyphs: int
    sharpness: float = 0.0

    @property
    def stroke_ratio(self) -> float:
        return self.stroke / max(self.height, 1.0)


@dataclass
class Page:
    rgb: np.ndarray
    gray: np.ndarray
    scale: float
    ink: np.ndarray
    ink_level: float
    paper_level: float
    glyph_height: float
    words: list[Word] = field(default_factory=list)
    graphics: list[dict] = field(default_factory=list)
    labels: np.ndarray | None = None


def load_image(img: Image.Image) -> tuple[np.ndarray, float]:
    img = img.convert("RGB")
    scale = 1.0
    if max(img.size) > MAX_SIDE:
        scale = MAX_SIDE / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    return np.asarray(img, dtype=np.float32), scale


def otsu(gray: np.ndarray) -> float:
    hist, edges = np.histogram(gray, bins=256, range=(0, 256))
    p = hist / hist.sum()
    omega, mu = np.cumsum(p), np.cumsum(p * np.arange(256))
    between = (mu[-1] * omega - mu) ** 2 / (omega * (1 - omega) + 1e-12)
    return float(edges[int(np.nanargmax(between)) + 1])  # class 0 includes the chosen bin


def _words_in_line(comps: list[dict], gap_factor: float) -> list[list[dict]]:
    comps = sorted(comps, key=lambda c: c["x0"])
    h = np.median([c["h"] for c in comps])
    groups, current = [], [comps[0]]
    for c in comps[1:]:
        if c["x0"] - max(p["x1"] for p in current) > gap_factor * h:
            groups.append(current)
            current = [c]
        else:
            current.append(c)
    groups.append(current)
    return groups


def _measure_word(page_rgb, gray, labels, comps, line_idx, ink_level, paper_level) -> Word:
    x0 = min(c["x0"] for c in comps); x1 = max(c["x1"] for c in comps)
    y0 = min(c["y0"] for c in comps); y1 = max(c["y1"] for c in comps)
    ids = [c["id"] for c in comps]
    sub = labels[y0:y1, x0:x1]
    mask = np.isin(sub, ids)
    edt = ndi.distance_transform_edt(mask)
    ridge = mask & (edt >= ndi.maximum_filter(edt, size=3)) & (edt > 0)
    rv = edt[ridge] if ridge.any() else edt[mask]
    stroke_cv = float(np.std(rv) / (np.mean(rv) + 1e-6))
    core = mask & (edt >= max(1.0, 0.5 * float(edt.max())))
    color = np.median(page_rgb[y0:y1, x0:x1][core if core.sum() >= 5 else mask], axis=0)

    pad = 3
    gy0, gy1 = max(0, y0 - pad), min(gray.shape[0], y1 + pad)
    gx0, gx1 = max(0, x0 - pad), min(gray.shape[1], x1 + pad)
    g = gray[gy0:gy1, gx0:gx1]
    own = np.isin(labels[gy0:gy1, gx0:gx1], ids)
    near = ndi.binary_dilation(own, iterations=2)
    local_ink = float(np.median(g[own])) if own.any() else ink_level
    span = max(paper_level - local_ink, 1.0)
    mid = (g > local_ink + 0.3 * span) & (g < paper_level - 0.3 * span) & near
    transition = float(mid.sum() / max(mask.sum(), 1))

    # Sub-pixel stroke width: anti-aliased ink mass / half the outline length.
    mass = float(np.clip((paper_level - g[near]) / span, 0, 1).sum())
    outline = float((own & ~ndi.binary_erosion(own)).sum())
    stroke = 2 * mass / max(outline, 1.0)

    gyy, gxx = np.gradient(g)
    grad = np.hypot(gyy, gxx)
    edge = near & ~ndi.binary_erosion(own, iterations=1)
    sharpness = float(np.percentile(grad[edge], 75) / span) if edge.any() else 0.0
    return Word((x0, y0, x1, y1), float(y1 - y0), stroke, stroke_cv, color, transition, line_idx,
                len(comps), sharpness)


def analyze_layout(img: Image.Image) -> Page:
    rgb, scale = load_image(img)
    gray = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    thr = otsu(gray)
    ink = gray < thr
    paper_level = float(np.median(gray[~ink])) if (~ink).any() else 255.0

    labels, n = ndi.label(ink, structure=np.ones((3, 3)))
    objs = ndi.find_objects(labels)
    areas = ndi.sum(ink, labels, index=np.arange(1, n + 1)) if n else []
    comps = []
    for i, sl in enumerate(objs):
        if sl is None:
            continue
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        h, w, area = y1 - y0, x1 - x0, float(areas[i])
        if area < 4:
            continue
        comps.append({"id": i + 1, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "h": h, "w": w,
                      "area": area, "fill": area / (h * w)})

    cand = [c for c in comps if 5 <= c["h"] <= 120 and c["fill"] < 0.9 and c["w"] <= 3 * c["h"] + 10]
    glyph_h = float(np.median([c["h"] for c in cand])) if cand else 20.0
    text, graphics = [], []
    for c in comps:
        big = c["h"] > 2.6 * glyph_h or c["w"] > 6 * glyph_h
        (graphics if big else text).append(c)

    ink_level = float(np.median(gray[ink])) if ink.any() else 0.0
    page = Page(rgb, gray, scale, ink, ink_level, paper_level, glyph_h, graphics=graphics)

    text.sort(key=lambda c: (c["y0"] + c["y1"]) / 2)
    lines: list[dict] = []
    for c in text:
        cy = (c["y0"] + c["y1"]) / 2
        for line in reversed(lines[-8:]):
            ly0, ly1 = line["y0"] / len(line["comps"]), line["y1"] / len(line["comps"])
            if ly0 - 0.25 * (ly1 - ly0) <= cy <= ly1 + 0.25 * (ly1 - ly0):
                line["comps"].append(c); line["y0"] += c["y0"]; line["y1"] += c["y1"]
                break
        else:
            lines.append({"comps": [c], "y0": c["y0"], "y1": c["y1"]})

    for li, line in enumerate(lines):
        if len(line["comps"]) < 2:
            continue
        for group in _words_in_line(line["comps"], gap_factor=0.55):
            if len(group) >= 2:
                page.words.append(_measure_word(rgb, gray, labels, group, li, page.ink_level, paper_level))
    page.labels = labels
    return page


def robust_z(values: np.ndarray, floor_frac: float = 0.05) -> np.ndarray:
    med = np.median(values)
    mad = 1.4826 * np.median(np.abs(values - med))
    mad = max(mad, floor_frac * abs(med), 1e-6)
    return (values - med) / mad


def to_original(box, scale: float) -> list[int]:
    return [round(v / scale) for v in box]
