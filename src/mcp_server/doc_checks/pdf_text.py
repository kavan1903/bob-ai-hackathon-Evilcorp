"""Typography checks on the text layer of a PDF.

Interprets each page's content stream just enough to know where every text run
is drawn, in which font and size, and where filled rectangles are painted.
Flags:
- cover-up: an opaque white/near-white box painted over text drawn earlier
  (the classic "white-out and retype" edit), or text drawn on top of other text
- font inconsistency: a font used by a single short run that sits inside a line
  set in another font
Also extracts embedded images (scanned pages, signatures) for the image checks.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ContentStream

from .image_checks import check

MIN_IMAGE_SIDE = 150


@dataclass
class Run:
    page: int
    x: float
    y: float
    size: float
    font: str
    text: str
    order: int

    @property
    def box(self) -> tuple[float, float, float, float]:
        width = max(len(self.text), 1) * 0.5 * self.size
        return (self.x, self.y - 0.2 * self.size, self.x + width, self.y + 0.8 * self.size)


def _overlap(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    area = (a[2] - a[0]) * (a[3] - a[1])
    return ix * iy / area if area > 0 else 0.0


def _text_of(operands) -> str:
    parts = []
    for op in operands:
        if isinstance(op, list):
            parts += [str(x) for x in op if isinstance(x, (str, bytes)) or hasattr(x, "original_bytes")]
        elif isinstance(op, (str, bytes)) or hasattr(op, "original_bytes"):
            parts.append(op.decode("latin-1") if isinstance(op, bytes) else str(op))
    return "".join(parts)


def _font_names(page) -> dict[str, str]:
    try:
        fonts = page["/Resources"]["/Font"]
        return {str(k): str(v.get_object().get("/BaseFont", k)).lstrip("/") for k, v in fonts.items()}
    except Exception:
        return {}


def parse_page(reader: PdfReader, pno: int) -> tuple[list[Run], list[dict]]:
    page = reader.pages[pno]
    contents = page.get_contents()
    if contents is None:
        return [], []
    names = _font_names(page)
    ops = ContentStream(contents, reader).operations
    runs, rects, pending = [], [], []
    fill_white = False
    font, size, leading = "?", 12.0, 0.0
    tx = ty = lx = ly = 0.0
    ctm = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    order = 0

    def show(text):
        nonlocal order
        if text.strip():
            sx, sy = ctm[0], ctm[3]
            runs.append(Run(pno, tx * sx + ctm[4], ty * sy + ctm[5], size * abs(sy), font, text, order))
            order += 1

    for operands, op in ops:
        op = op.decode() if isinstance(op, bytes) else op
        try:
            if op == "cm":
                ctm = [float(v) for v in operands]
            elif op in ("rg", "g", "k", "sc", "scn"):
                vals = [float(v) for v in operands if isinstance(v, (int, float)) or str(v).replace(".", "", 1).lstrip("-").isdigit()]
                fill_white = bool(vals) and (all(v >= 0.95 for v in vals) if op != "k" else all(v <= 0.05 for v in vals))
            elif op == "re":
                pending.append([float(v) for v in operands])
            elif op in ("f", "F", "f*", "B", "B*"):
                for x, y, w, h in pending:
                    rects.append({"box": (min(x, x + w), min(y, y + h), max(x, x + w), max(y, y + h)),
                                  "white": fill_white, "order": order, "page": pno})
                    order += 1
                pending = []
            elif op in ("n", "S", "s"):
                pending = []
            elif op == "BT":
                tx = ty = lx = ly = 0.0
            elif op == "Tf":
                font, size = names.get(str(operands[0]), str(operands[0]).lstrip("/")), float(operands[1])
            elif op == "TL":
                leading = float(operands[0])
            elif op in ("Td", "TD"):
                lx += float(operands[0]); ly += float(operands[1]); tx, ty = lx, ly
                if op == "TD":
                    leading = -float(operands[1])
            elif op == "Tm":
                lx, ly = float(operands[4]), float(operands[5]); tx, ty = lx, ly
            elif op == "T*":
                ly -= leading; tx, ty = lx, ly
            elif op in ("'", '"'):
                ly -= leading; tx, ty = lx, ly
                show(_text_of(operands[-1:]))
            elif op in ("Tj", "TJ"):
                show(_text_of(operands))
        except (ValueError, IndexError, TypeError):
            continue
    return runs, rects


def embedded_images(reader: PdfReader, limit: int = 6) -> list[tuple[str, Image.Image]]:
    out = []
    for pno, page in enumerate(reader.pages):
        try:
            for img in page.images:
                pil = Image.open(io.BytesIO(img.data))
                if min(pil.size) >= MIN_IMAGE_SIDE:
                    out.append((f"page {pno + 1} image {img.name}", pil))
                if len(out) >= limit:
                    return out
        except Exception:
            continue
    return out


def pdf_typography_checks(path: str) -> tuple[list[dict], dict]:
    reader = PdfReader(path)
    runs, rects = [], []
    for pno in range(len(reader.pages)):
        r, q = parse_page(reader, pno)
        runs += r; rects += q
    info = {"text_runs": len(runs), "fonts": sorted({f"{r.font} {r.size:g}pt" for r in runs})}
    if not runs:
        return [check("typography", "PDF text layer", "skipped",
                      "No text layer (scanned/image-only PDF) - image checks run on embedded images instead")], info

    covered = []
    for rect in (r for r in rects if r["white"]):
        on_page = [t for t in runs if t.page == rect["page"]]
        hidden = [t for t in on_page if t.order < rect["order"] and _overlap(t.box, rect["box"]) > 0.3
                  or t.order < rect["order"] and _overlap(rect["box"], t.box) > 0.3]
        if hidden:
            above = [t for t in on_page if t.order > rect["order"] and _overlap(t.box, rect["box"]) > 0.3]
            covered.append(f"white box over '{hidden[0].text.strip()[:40]}'" +
                           (f", then '{above[0].text.strip()}' typed on top in {above[0].font}" if above else ""))
    for i, a in enumerate(runs):
        for b in runs[i + 1:]:
            if a.page == b.page and _overlap(a.box, b.box) > 0.6 and a.text.strip() != b.text.strip():
                covered.append(f"'{b.text.strip()[:20]}' drawn over '{a.text.strip()[:20]}'")
    checks = [check("typography", "Covered or overwritten text (PDF)", "flag" if covered else "pass",
                    "; ".join(covered[:3]) if covered else "No text is hidden under boxes or overwritten",
                    "auto_text_cover_up")]

    usage: dict[str, int] = {}
    for r in runs:
        usage[r.font] = usage.get(r.font, 0) + len(r.text)
    odd = []
    for r in runs:
        if usage[r.font] <= 12 and len(usage) > 1:
            same_line = [o for o in runs if o is not r and o.page == r.page and abs(o.y - r.y) <= 0.4 * r.size and o.font != r.font]
            if same_line:
                odd.append(f"'{r.text.strip()}' in {r.font} {r.size:g}pt inside a line set in {same_line[0].font}")
    checks.append(check("typography", "Font consistency (PDF)", "flag" if odd else "pass",
                        "; ".join(odd[:3]) if odd else f"Fonts used consistently: {', '.join(info['fonts'][:4])}",
                        "auto_font_inconsistent", metrics=info))
    return checks, info
