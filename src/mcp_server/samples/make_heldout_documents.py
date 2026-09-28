"""Held-out test set: a different document design the detectors were NOT tuned on.

Degree certificate, landscape, cream paper, Calibri body text in black ink,
Georgia title, signer B, different resolution. Forgeries use Verdana, a blue
pen, feathering, an erased patch and a simulated signature.

    python samples/make_heldout_documents.py   -> samples/heldout/
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from samples.make_test_documents import draw_signature, exif_bytes, font, signature_image, signature_points  # noqa: E402

OUT = HERE / "heldout"
W, H = 1600, 1130
PAPER = (246, 240, 225)
INK = (22, 22, 24)
LINES = [
    ("intro", "This is to certify that"),
    ("name", "PRIYA SURESH NAIR"),
    ("award", "has been awarded the degree of"),
    ("degree", "Bachelor of Technology in Computer Science"),
    ("cgpa", "with a CGPA of 7.82 in the year 2021"),
    ("regno", "Registration No. ARD/2017/88213"),
    ("date", "Date of issue: 14-09-2021"),
]


def render(overrides=None, signature=None):
    overrides = overrides or {}
    rng = np.random.default_rng(21)
    base = np.empty((H, W, 3), dtype=float)
    base[:] = PAPER
    base += rng.normal(0, 3.0, size=(H, W, 1))
    for key, ov in overrides.items():
        if ov.get("erase"):
            x0, y0, x1, y1 = ov["erase"]
            base[y0:y1, x0:x1] = np.array((251, 247, 236), dtype=float) + np.random.default_rng(4).normal(0, 1.0, (y1 - y0, x1 - x0, 1))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, W - 40, H - 40], outline=(120, 30, 40), width=6)
    d.text((220, 90), "ARDENIA UNIVERSITY (FICTIONAL)", font=font("georgiab.ttf", 56), fill=(110, 20, 30))
    boxes, y = {}, 230
    for key, text in LINES:
        ov = overrides.get(key, {})
        f = font(ov.get("font", "calibri.ttf"), ov.get("size", 38))
        text = ov.get("text", text)
        pos = (200, y)
        bb = d.textbbox(pos, text, font=f)
        if ov.get("blur"):
            layer = Image.new("L", img.size, 0)
            ImageDraw.Draw(layer).text(pos, text, font=f, fill=255)
            layer = layer.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(ov["blur"]))
            img.paste(Image.new("RGB", img.size, ov.get("color", INK)), (0, 0), layer)
        else:
            d.text(pos, text, font=f, fill=ov.get("color", INK))
        boxes[key] = [bb[0] - 4, bb[1] - 4, bb[2] + 4, bb[3] + 4]
        y += 82
    d.text((1080, 1000), "Registrar", font=font("calibri.ttf", 30), fill=INK)
    draw_signature(d, signature or signature_points("B", variant=0), (1060, 900), color=INK, width=4)
    boxes["signature"] = [1040, 860, 1400, 1000]
    return img, boxes


def make_all(out: Path = OUT) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    docs = []

    def add(name, img, expected, note, fmt="PNG", **kw):
        img.save(out / name, fmt, **kw)
        docs.append({"file": name, "expected": expected, "note": note})

    g, b = render()
    add("deg_genuine.png", g, [], "Genuine")
    add("deg_genuine_q80.jpg", g, [], "Genuine, JPEG q80", fmt="JPEG", quality=80, exif=exif_bytes("Canon DR-C225 scanner"))
    add("deg_genuine_small.png", g.resize((1120, 791), Image.LANCZOS), [], "Genuine, downscaled to 70%")
    add("deg_font_swap.png", render({"cgpa": {"font": "verdana.ttf", "size": 33, "text": "with a CGPA of 9.82 in the year 2021"}})[0],
        ["typography"], "CGPA line retyped in Verdana")
    add("deg_font_swap_times.png", render({"cgpa": {"font": "times.ttf", "size": 40, "text": "with a CGPA of 9.82 in the year 2021"}})[0],
        ["typography"], "CGPA line retyped in Times New Roman")
    add("deg_ink_blue.png", render({"regno": {"color": (20, 40, 140)}})[0], ["ink"], "Registration number in blue ink")
    add("deg_ink_spread.png", render({"date": {"blur": 1.0}})[0], ["ink"], "Issue date feathered")
    add("deg_erasure.png", render({"cgpa": {"erase": [190, 555, 900, 610], "text": "with a CGPA of 9.82 in the year 2021"}})[0],
        ["substrate"], "CGPA erased and rewritten")
    forged = signature_points("B", variant=7, tremor=1.2, slant_deg=-12, sx=1.1, sy=0.85)
    add("deg_signature_simulated.png", render(signature=forged)[0], ["signature"], "Registrar signature simulated")
    add("deg_edited_exif.jpg", g, ["digital"], "Saved from GIMP", fmt="JPEG", quality=90, exif=exif_bytes("GIMP 2.10.36"))
    signature_image(signature_points("B", variant=0)).save(out / "sig_exemplar_B.png")
    manifest = {"documents": docs, "exemplar": "sig_exemplar_B.png"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    m = make_all()
    print(f"{len(m['documents'])} held-out documents -> {OUT}")
