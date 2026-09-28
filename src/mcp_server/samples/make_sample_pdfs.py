"""Generate mock certificate PDFs for testing the metadata analyzer.

- genuine_certificate.pdf: issued once by the (fictional) board's system.
- tampered_certificate.pdf: the same file, re-saved by an online PDF editor
  months later with the marks changed via an incremental update. The XMP
  packet is left stale, as many editors do.
- on_demand_vaccination_certificate.pdf: generated at download time, months
  after the vaccination date, and never modified.

All names and institutions are fictional.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _xmp(create_iso: str, producer: str) -> bytes:
    return (
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmlns:pdf="http://ns.adobe.com/pdf/1.3/">'
        f"<xmp:CreateDate>{create_iso}</xmp:CreateDate>"
        f"<xmp:ModifyDate>{create_iso}</xmp:ModifyDate>"
        f"<xmp:CreatorTool>{producer}</xmp:CreatorTool>"
        f"<pdf:Producer>{producer}</pdf:Producer>"
        "</rdf:Description></rdf:RDF></x:xmpmeta>"
        '<?xpacket end="w"?>'
    ).encode()


def _stream(body: bytes, extra: bytes = b"") -> bytes:
    return b"<< /Length %d%s >>\nstream\n" % (len(body), extra) + body + b"\nendstream"


def _content(lines: list[str]) -> bytes:
    ops = [b"BT /F1 14 Tf 72 780 Td 18 TL"]
    for line in lines:
        ops.append(b"(" + line.encode("latin-1") + b") '")
    ops.append(b"ET")
    return b"\n".join(ops)


def _info(producer: str, created: str, modified: str, title: str) -> bytes:
    return (f"<< /Title ({title}) /Producer ({producer}) /Creator ({producer}) "
            f"/CreationDate ({created}) /ModDate ({modified}) >>").encode()


def _write_section(buf: bytearray, objects: dict[int, bytes]) -> dict[int, int]:
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(buf)
        buf += b"%d 0 obj\n" % num + objects[num] + b"\nendobj\n"
    return offsets


def _xref_and_trailer(buf: bytearray, offsets: dict[int, int], size: int, info: int, prev: int | None) -> int:
    xref_pos = len(buf)
    buf += b"xref\n"
    if prev is None:
        buf += b"0 %d\n0000000000 65535 f \n" % size
        for num in range(1, size):
            buf += b"%010d 00000 n \n" % offsets[num]
    else:
        for num in sorted(offsets):
            buf += b"%d 1\n%010d 00000 n \n" % (num, offsets[num])
    buf += b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R" % (size, info)
    if prev is not None:
        buf += b" /Prev %d" % prev
    buf += b" >>\nstartxref\n%d\n%%%%EOF\n" % xref_pos
    return xref_pos


def build_certificate(lines: list[str], producer: str, created_pdf: str, created_iso: str,
                      title: str) -> tuple[bytearray, int]:
    xmp = _xmp(created_iso, producer)
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R /Metadata 6 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>"),
        4: _stream(_content(lines)),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: _stream(xmp, b" /Type /Metadata /Subtype /XML"),
        7: _info(producer, created_pdf, created_pdf, title),
    }
    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = _write_section(buf, objects)
    xref_pos = _xref_and_trailer(buf, offsets, 8, 7, None)
    return buf, xref_pos


def append_edit(buf: bytearray, prev_xref: int, lines: list[str], producer: str,
                created_pdf: str, modified_pdf: str, title: str) -> bytearray:
    objects = {4: _stream(_content(lines)), 7: _info(producer, created_pdf, modified_pdf, title)}
    offsets = _write_section(buf, objects)
    _xref_and_trailer(buf, offsets, 8, 7, prev_xref)
    return buf


GENUINE_LINES = [
    "State Board of Technical Education (fictional)",
    "Diploma Certificate No. SBTE/2023/004417",
    "This is to certify that Rahul Verma (fictional)",
    "has passed the Diploma in Civil Engineering",
    "with an aggregate of 61.4% in May 2023.",
    "Date of issue: 15-06-2023",
]
TAMPERED_LINES = GENUINE_LINES[:4] + ["with an aggregate of 91.4% in May 2023.", GENUINE_LINES[5]]

BOARD_SYSTEM = "SBTE CertGen 3.2"
ISSUE_PDF_DATE = "D:20230615100000+05'30'"
ISSUE_ISO_DATE = "2023-06-15T10:00:00+05:30"


def make_all(out_dir: Path = HERE) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    title = "Diploma Certificate SBTE-2023-004417"

    genuine, _ = build_certificate(GENUINE_LINES, BOARD_SYSTEM, ISSUE_PDF_DATE, ISSUE_ISO_DATE, title)
    tampered, xref = build_certificate(GENUINE_LINES, BOARD_SYSTEM, ISSUE_PDF_DATE, ISSUE_ISO_DATE, title)
    tampered = append_edit(tampered, xref, TAMPERED_LINES, "iLovePDF",
                           ISSUE_PDF_DATE, "D:20240203221500+05'30'", title)

    vacc_lines = ["Ministry of Health (fictional) - Vaccination Certificate",
                  "Beneficiary: Priya Nair (fictional)",
                  "Dose 2 administered on 01-05-2021"]
    vaccination, _ = build_certificate(vacc_lines, "HealthPortal CertService",
                                       "D:20210910083000+05'30'", "2021-09-10T08:30:00+05:30",
                                       "Vaccination Certificate")

    paths = {
        "genuine": out_dir / "genuine_certificate.pdf",
        "tampered": out_dir / "tampered_certificate.pdf",
        "on_demand": out_dir / "on_demand_vaccination_certificate.pdf",
    }
    paths["genuine"].write_bytes(bytes(genuine))
    paths["tampered"].write_bytes(bytes(tampered))
    paths["on_demand"].write_bytes(bytes(vaccination))
    return paths


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
    for name, path in make_all(target).items():
        print(f"{name:10s} -> {path}")
