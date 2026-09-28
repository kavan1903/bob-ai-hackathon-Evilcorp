"""Generate a ground-truth test set of fictional ID cards and certificates.

Every forged file differs from the genuine one in exactly one controlled way,
and manifest.json records which check category should fire and where.
All names, numbers and institutions are fictional.

    python samples/make_test_documents.py            -> samples/testdocs/
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
OUT = HERE / "testdocs"
FONTS = Path("C:/Windows/Fonts")
W, H = 1012, 640
PAPER = (238, 241, 236)
NAVY = (25, 35, 95)
GREY = (95, 95, 95)

FIELDS = [
    ("name", "Name", "RAHUL KUMAR VERMA"),
    ("dob", "Date of Birth", "12-08-1996"),
    ("idno", "ID Number", "4821 7730 5519"),
    ("address", "Address", "14 Lake View Road, Pune"),
    ("valid", "Valid until", "02-01-2032"),
]


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def paper_texture(seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = np.empty((H, W, 3), dtype=float)
    img[:] = PAPER
    img += rng.normal(0, 2.5, size=(H, W, 1))
    yy, xx = np.mgrid[0:H, 0:W]
    for k in range(6):
        wave = np.abs(yy - (140 + 80 * k + 18 * np.sin(xx / 37.0 + k))) < 0.8
        img[wave] -= (14, 8, 14)
    return np.clip(img, 0, 255)


def signature_points(person: str, variant: int = 0, tremor: float = 0.0, slant_deg: float = 0.0,
                     sx: float = 1.0, sy: float = 1.0) -> list[np.ndarray]:
    params = {
        "A": dict(L=230, f=(3.1, 5.3, 8.2), amp=(9, 26, 9), ph=(0.3, 1.1, 2.0), lifts=(0.38, 0.71)),
        "B": dict(L=210, f=(2.2, 6.6, 4.1), amp=(14, 18, 12), ph=(1.7, 0.2, 0.9), lifts=(0.25, 0.58)),
    }[person]
    rng = np.random.default_rng(100 + variant)
    jit = lambda v, s: v * (1 + rng.normal(0, s))
    t = np.linspace(0, 1, 500)
    f1, f2, f3 = params["f"]
    a1, a2, a3 = (jit(a, 0.04) for a in params["amp"])
    p1, p2, p3 = (p + rng.normal(0, 0.05) for p in params["ph"])
    x = t * params["L"] + a1 * np.sin(2 * math.pi * f1 * t + p1)
    y = a2 * np.sin(2 * math.pi * f2 * t + p2) + a3 * np.sin(2 * math.pi * f3 * t + p3)
    if tremor:
        noise = np.random.default_rng(55 + variant).normal(0, tremor, size=(2, t.size))
        x, y = x + noise[0], y + noise[1]
    x, y = x * sx, y * sy
    x = x + y * math.tan(math.radians(slant_deg))
    pts = np.stack([x, y], axis=1)
    cuts = [int(c * len(t)) for c in params["lifts"]]
    strokes = np.split(pts, cuts)
    flourish_x = np.linspace(pts[:, 0].min() + 10, pts[:, 0].max() * 0.9, 60)
    flourish = np.stack([flourish_x, np.full_like(flourish_x, 34) + 3 * np.sin(flourish_x / 25)], axis=1)
    return strokes + [flourish]


def draw_signature(draw: ImageDraw.ImageDraw, strokes, origin, color=NAVY, width=3):
    ox, oy = origin
    for s in strokes:
        pts = [(ox + float(px), oy + float(py)) for px, py in s]
        draw.line(pts, fill=color, width=width, joint="curve")


def signature_image(strokes, size=(360, 130)) -> Image.Image:
    img = Image.new("RGB", size, (250, 250, 248))
    draw_signature(ImageDraw.Draw(img), strokes, (60, 55))
    return img


def render_card(overrides: dict | None = None, signature=None, seed: int = 7) -> tuple[Image.Image, dict]:
    """Render the card. overrides[field] may set font, size, color, blur, whiteout. Returns image + field boxes."""
    overrides = overrides or {}
    base = paper_texture(seed)
    for key, ov in overrides.items():
        if ov.get("whiteout"):
            x0, y0, x1, y1 = ov["whiteout"]
            tone = np.array(ov.get("tone", (248, 249, 246)), dtype=float)
            grain = np.random.default_rng(3).normal(0, ov.get("grain", 0.8), size=(y1 - y0, x1 - x0, 1))
            base[y0:y1, x0:x1] = tone + grain
    img = Image.fromarray(base.astype(np.uint8))
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 96], fill=(34, 84, 132))
    d.text((40, 22), "UNION OF ARDENIA (FICTIONAL)", font=font("arialbd.ttf", 30), fill=(255, 255, 255))
    d.text((40, 60), "National Identity Card - specimen for testing only", font=font("arial.ttf", 18), fill=(220, 230, 240))

    d.rectangle([40, 130, 250, 400], fill=(118, 124, 132))
    d.ellipse([95, 170, 195, 280], fill=(160, 150, 140))
    d.rectangle([80, 285, 210, 400], fill=(80, 90, 110))

    boxes = {}
    y = 128
    for key, label, value in FIELDS:
        ov = overrides.get(key, {})
        d.text((300, y), label, font=font("arial.ttf", 18), fill=GREY)
        f = font(ov.get("font", "arial.ttf"), ov.get("size", 26))
        text = ov.get("text", value)
        pos = (300, y + 22)
        bbox = d.textbbox(pos, text, font=f)
        if ov.get("blur"):
            layer = Image.new("L", img.size, 0)
            ImageDraw.Draw(layer).text(pos, text, font=f, fill=255)
            layer = layer.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(ov["blur"]))
            ink = Image.new("RGB", img.size, ov.get("color", NAVY))
            img.paste(ink, (0, 0), layer)
            d = ImageDraw.Draw(img)
        else:
            d.text(pos, text, font=f, fill=ov.get("color", NAVY))
        boxes[key] = [bbox[0] - 4, bbox[1] - 4, bbox[2] + 4, bbox[3] + 4]
        y += 66

    d.text((300, 470), "Holder's signature", font=font("arial.ttf", 16), fill=GREY)
    sig = signature if signature is not None else signature_points("A", variant=0)
    draw_signature(d, sig, (330, 520))
    boxes["signature"] = [300, 480, 640, 600]
    d.text((40, 600), "Issued 03-01-2022 by the Ardenia Registration Authority. This specimen has no legal validity.",
           font=font("arial.ttf", 14), fill=GREY)
    return img, boxes


def exif_bytes(software: str) -> bytes:
    exif = Image.Exif()
    exif[0x0131] = software
    return exif.tobytes()


def make_all(out: Path = OUT) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"documents": [], "signature_pairs": []}

    def add(name, img, expected, region=None, note="", fmt="PNG", **save_kw):
        path = out / name
        img.save(path, fmt, **save_kw)
        manifest["documents"].append({"file": name, "expected": expected, "region": region, "note": note})

    genuine, boxes = render_card()
    add("id_genuine.png", genuine, [], note="Clean original")
    add("id_genuine_q90.jpg", genuine, [], fmt="JPEG", quality=90, exif=exif_bytes("EPSON Scan 3.9"),
        note="Clean original, JPEG, scanner software in EXIF")

    img, b = render_card({"dob": {"font": "times.ttf", "size": 28}})
    add("id_font_swap.png", img, ["typography"], b["dob"], "Date of birth retyped in Times New Roman")

    img, b = render_card({"idno": {"color": (30, 30, 30)}})
    add("id_ink_colour.png", img, ["ink"], b["idno"], "ID number written in black instead of navy")

    img, b = render_card({"address": {"blur": 1.3}})
    add("id_ink_spread.png", img, ["ink"], b["address"], "Address ink feathered / spread")

    img, b = render_card({"address": {"blur": 0.7}})
    add("id_ink_spread_subtle.png", img, ["ink"], b["address"], "Address ink slightly feathered (subtle)")

    img, b = render_card({"idno": {"color": (45, 45, 80)}})
    add("id_ink_colour_subtle.png", img, ["ink"], b["idno"], "ID number in a slightly different blue-black ink (subtle)")

    wx = [292, 412, 560, 456]
    img, b = render_card({"valid": {"whiteout": wx, "text": "02-01-2042"}})
    add("id_erasure.png", img, ["substrate"], wx, "Validity date erased (lighter, smoother patch) and rewritten")

    img, b = render_card({"valid": {"whiteout": wx, "text": "02-01-2042", "tone": (241, 244, 239), "grain": 1.8}})
    add("id_erasure_subtle.png", img, ["substrate"], wx, "Validity date erased, patch close to paper tone (subtle)")

    forged_sig = signature_points("A", variant=9, tremor=1.1, slant_deg=14, sx=0.9, sy=1.15)
    img, b = render_card(signature=forged_sig)
    add("id_signature_simulated.png", img, ["signature"], b["signature"], "Signature simulated (tremor, slant, proportions)")

    img, b = render_card(signature=signature_points("B", variant=0))
    add("id_signature_other.png", img, ["signature"], b["signature"], "Signature of a different person")

    add("id_edited_exif.jpg", genuine, ["digital"], None, "Saved from Photoshop (EXIF Software tag)",
        fmt="JPEG", quality=90, exif=exif_bytes("Adobe Photoshop 25.0 (Windows)"))

    img, b = render_card({"dob": {"font": "times.ttf", "size": 28}, "idno": {"color": (30, 30, 30)}})
    add("id_composite.png", img, ["typography", "ink"], None, "Font swap + ink colour change")

    img, _ = render_card({"dob": {"font": "times.ttf", "size": 28}})
    add("id_font_swap_q85.jpg", img, ["typography"], b["dob"], "Font swap, JPEG q85", fmt="JPEG", quality=85)

    exemplar = signature_image(signature_points("A", variant=0))
    exemplar.save(out / "sig_exemplar_A.png")
    for name, strokes, match in [
        ("sig_questioned_A_genuine.png", signature_points("A", variant=3), True),
        ("sig_questioned_A_genuine2.png", signature_points("A", variant=4), True),
        ("sig_questioned_A_simulated.png", forged_sig, False),
        ("sig_questioned_B_other.png", signature_points("B", variant=0), False),
    ]:
        signature_image(strokes).save(out / name)
        manifest["signature_pairs"].append({"questioned": name, "exemplar": "sig_exemplar_A.png", "same_writer": match})
    exemplar.save(out / "sig_questioned_A_identical.png")
    manifest["signature_pairs"].append({"questioned": "sig_questioned_A_identical.png", "exemplar": "sig_exemplar_A.png",
                                        "same_writer": True, "identical_copy": True})

    for name, path, expected, note in make_pdfs(out):
        manifest["documents"].append({"file": name, "expected": expected, "region": None, "note": note})

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def make_pdfs(out: Path) -> list[tuple]:
    """Cover-and-retype forgeries of the sample certificate: a white box over '61.4%'
    with '91.4%' typed on top in Times-Roman."""
    from samples.make_sample_pdfs import (BOARD_SYSTEM, GENUINE_LINES, ISSUE_ISO_DATE, ISSUE_PDF_DATE,
                                          _content, _info, _stream, _write_section, _xref_and_trailer,
                                          build_certificate)
    helv = font("arial.ttf", 14)
    line_idx = 4
    prefix = "with an aggregate of "
    x = 72 + helv.getlength(prefix)
    y = 780 - 18 * (line_idx + 1)
    w = helv.getlength("61.4%")
    overlay = (f"1 1 1 rg {x - 1:.1f} {y - 3:.1f} {w + 3:.1f} 16 re f "
               f"0 0 0 rg BT /F2 14 Tf {x:.1f} {y:.1f} Td (91.4%) Tj ET").encode()
    page_obj = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents [4 0 R 9 0 R] "
                b"/Resources << /Font << /F1 5 0 R /F2 8 0 R >> >> >>")
    times = b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>"
    title = "Diploma Certificate SBTE-2023-004417"
    results = []

    buf, xref = build_certificate(GENUINE_LINES, BOARD_SYSTEM, ISSUE_PDF_DATE, ISSUE_ISO_DATE, title)
    offsets = _write_section(buf, {3: page_obj, 8: times, 9: _stream(overlay),
                                   7: _info("SBTE CertGen 3.2", ISSUE_PDF_DATE, "D:20240203221500+05'30'", title)})
    _xref_and_trailer(buf, offsets, 10, 7, xref)
    (out / "cert_cover_retype.pdf").write_bytes(bytes(buf))
    results.append(("cert_cover_retype.pdf", out / "cert_cover_retype.pdf", ["typography", "digital"],
                    "White box over 61.4% with 91.4% typed in Times, saved as incremental update"))

    from samples.make_sample_pdfs import _xmp
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R /Metadata 6 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: page_obj,
        4: _stream(_content(GENUINE_LINES)),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: _stream(_xmp(ISSUE_ISO_DATE, BOARD_SYSTEM), b" /Type /Metadata /Subtype /XML"),
        7: _info(BOARD_SYSTEM, ISSUE_PDF_DATE, ISSUE_PDF_DATE, title),
        8: times,
        9: _stream(overlay),
    }
    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = _write_section(buf, objects)
    _xref_and_trailer(buf, offsets, 10, 7, None)
    (out / "cert_cover_retype_flat.pdf").write_bytes(bytes(buf))
    results.append(("cert_cover_retype_flat.pdf", out / "cert_cover_retype_flat.pdf", ["typography"],
                    "Same cover-and-retype, re-saved as one clean revision with original metadata"))

    import shutil
    shutil.copy(HERE / "genuine_certificate.pdf", out / "cert_genuine.pdf")
    results.append(("cert_genuine.pdf", out / "cert_genuine.pdf", [], "Genuine certificate PDF"))
    return results


if __name__ == "__main__":
    m = make_all(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
    print(f"{len(m['documents'])} documents, {len(m['signature_pairs'])} signature pairs -> {OUT}")
