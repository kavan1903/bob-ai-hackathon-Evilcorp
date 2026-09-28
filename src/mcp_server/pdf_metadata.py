"""Dependency-free PDF metadata examination.

Reads the raw bytes of a PDF and extracts the evidence a document examiner
looks at for digital manipulation: revision count (incremental saves),
Info-dictionary history across revisions, XMP metadata, producer/creator
software, and date consistency. Produces findings in the same format the
examiner uses, so they feed straight into the evaluation.

Limitation: metadata stored inside compressed object streams is not decoded.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

EDITING_TOOLS = [
    "photoshop", "gimp", "ilovepdf", "smallpdf", "sejda", "pdfescape",
    "pdf-xchange", "phantompdf", "nitro", "canva", "paint.net", "inkscape",
    "pdfelement", "pdf editor", "pdfedit", "pdfcandy", "online2pdf",
]
DATE_TOLERANCE = timedelta(seconds=60)

_STRING = rb"(\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]*>)"
_INFO_KEYS = ["Producer", "Creator", "CreationDate", "ModDate", "Title", "Author"]


def _decode_pdf_string(token: bytes) -> str:
    if token.startswith(b"<"):
        raw = bytes.fromhex(re.sub(rb"\s", b"", token[1:-1]).decode())
    else:
        body = token[1:-1]
        raw = re.sub(rb"\\([()\\])", rb"\1", body)
        raw = raw.replace(b"\\n", b"\n").replace(b"\\r", b"\r")
    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be", errors="replace")
    return raw.decode("latin-1")


def parse_pdf_date(value: str | None) -> datetime | None:
    """Parse 'D:YYYYMMDDHHmmSS+hh'mm'' into an aware UTC datetime."""
    if not value:
        return None
    m = re.match(r"D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz+\-])?(\d{2})?'?(\d{2})?", value.strip())
    if not m:
        return None
    year, month, day, hour, minute, second, sign, tzh, tzm = m.groups()
    dt = datetime(int(year), int(month or 1), int(day or 1),
                  int(hour or 0), int(minute or 0), int(second or 0), tzinfo=timezone.utc)
    if sign in ("+", "-") and tzh:
        offset = timedelta(hours=int(tzh), minutes=int(tzm or 0))
        dt = dt - offset if sign == "+" else dt + offset
    return dt


def parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _info_dicts(data: bytes) -> list[dict]:
    """Every Info-style dictionary in file order (one per revision that wrote one)."""
    found = []
    for m in re.finditer(rb"<<(?:(?!<<|>>).)*?/(?:Producer|CreationDate|ModDate)(?:(?!<<|>>).)*>>", data, re.S):
        block = m.group(0)
        entry = {}
        for key in _INFO_KEYS:
            km = re.search(rb"/" + key.encode() + rb"\s*" + _STRING, block)
            if km:
                entry[key] = _decode_pdf_string(km.group(1))
        if entry:
            found.append(entry)
    return found


def _xmp(data: bytes) -> dict:
    m = re.search(rb"<x:xmpmeta.*?</x:xmpmeta>", data, re.S)
    if not m:
        return {}
    xml = m.group(0).decode("utf-8", errors="replace")
    out = {}
    for key, tag in [("CreateDate", "xmp:CreateDate"), ("ModifyDate", "xmp:ModifyDate"),
                     ("CreatorTool", "xmp:CreatorTool"), ("Producer", "pdf:Producer")]:
        tm = re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.S) or re.search(rf'{tag}="([^"]*)"', xml)
        if tm:
            out[key] = tm.group(1).strip()
    return out


def _finding(indicator: str, present: bool, note: str) -> dict:
    return {
        "indicator": indicator,
        "status": "present" if present else "absent",
        "confidence": "moderate",
        "note": note,
        "source": "pdf_metadata",
    }


def analyze_pdf(path: str, stated_issue_date: str = "", expected_producer: str = "",
                generated_on_demand: bool = False) -> dict:
    """Examine a PDF file.

    stated_issue_date: the date the document claims to be issued (YYYY-MM-DD).
    expected_producer: text expected in the Producer/Creator of genuine documents
        from this issuer (e.g. the issuer's certificate system).
    generated_on_demand: True for e-certificates that are rendered when
        downloaded (e.g. vaccination certificates) - their creation date is
        legitimately later than the issue date, so only modification is judged.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    data = p.read_bytes()
    if not data.startswith(b"%PDF-"):
        raise ValueError(f"Not a PDF file (missing %PDF- header): {path}")

    linearized = b"/Linearized" in data[:2048]
    eof_count = data.count(b"%%EOF")
    revisions = max(1, eof_count - (1 if linearized and eof_count > 1 else 0))

    history = _info_dicts(data)
    info: dict = {}
    for entry in history:
        info.update(entry)
    xmp = _xmp(data)

    created = parse_pdf_date(info.get("CreationDate")) or parse_iso_date(xmp.get("CreateDate"))
    modified = parse_pdf_date(info.get("ModDate")) or parse_iso_date(xmp.get("ModifyDate"))
    software = " | ".join(dict.fromkeys(filter(None, [info.get("Producer"), info.get("Creator"),
                                                      xmp.get("Producer"), xmp.get("CreatorTool")])))

    findings = []
    notes = []

    findings.append(_finding(
        "incremental_updates", revisions > 1,
        f"{revisions} revision(s) found in file" + (" (linearized file)" if linearized else "")))

    if created and modified:
        findings.append(_finding(
            "mod_after_creation", modified - created > DATE_TOLERANCE,
            f"CreationDate {created:%Y-%m-%d %H:%M} UTC, ModDate {modified:%Y-%m-%d %H:%M} UTC"))
    else:
        notes.append("Creation/modification dates not both present - date checks not performed.")

    if software:
        lowered = software.lower()
        tool_hit = next((t for t in EDITING_TOOLS if t in lowered), None)
        producer_mismatch = bool(expected_producer) and expected_producer.lower() not in lowered
        reason = (f"editing tool '{tool_hit}' in producer/creator" if tool_hit else
                  f"expected '{expected_producer}' not found" if producer_mismatch else
                  "no editing tool found")
        findings.append(_finding("producer_editing_tool", bool(tool_hit or producer_mismatch),
                                 f"Software: {software} - {reason}"))
    else:
        notes.append("No producer/creator recorded.")

    if xmp and info:
        mismatches = []
        if xmp.get("Producer") and info.get("Producer") and xmp["Producer"] != info["Producer"]:
            mismatches.append(f"producer (Info '{info['Producer']}' vs XMP '{xmp['Producer']}')")
        for label, a, b in [("creation date", info.get("CreationDate"), xmp.get("CreateDate")),
                            ("modification date", info.get("ModDate"), xmp.get("ModifyDate"))]:
            da, db = parse_pdf_date(a), parse_iso_date(b)
            if da and db and abs(da - db) > DATE_TOLERANCE:
                mismatches.append(label)
        findings.append(_finding("metadata_inconsistent", bool(mismatches),
                                 "Mismatch in: " + ", ".join(mismatches) if mismatches
                                 else "Info dictionary and XMP agree"))
    else:
        notes.append("Info dictionary or XMP packet missing - consistency check not performed.")

    if stated_issue_date:
        issue = datetime.fromisoformat(stated_issue_date).replace(tzinfo=timezone.utc)
        issue_end = issue + timedelta(days=1)
        candidates = [("modified", modified)] if generated_on_demand else [("created", created), ("modified", modified)]
        late = [f"{label} {dt:%Y-%m-%d}" for label, dt in candidates if dt and dt > issue_end]
        if any(dt for _, dt in candidates):
            if generated_on_demand and created and modified and modified - created <= DATE_TOLERANCE:
                late = []
            findings.append(_finding(
                "mod_date_after_issue", bool(late),
                (f"File {', '.join(late)} after stated issue date {stated_issue_date}" if late
                 else f"No creation/modification after stated issue date {stated_issue_date}")
                + (" (on-demand certificate: only post-creation edits judged)" if generated_on_demand else "")))

    return {
        "file": p.name,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "revisions": revisions,
        "linearized": linearized,
        "has_digital_signature": b"/ByteRange" in data,
        "info": info,
        "info_history": history,
        "xmp": xmp,
        "findings": findings,
        "notes": notes,
    }
