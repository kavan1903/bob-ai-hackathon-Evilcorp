"""DocuVerity web UI - local examination workbench.

Run:  python src/ui/app.py        then open http://127.0.0.1:8765
Uses only the Python standard library plus the DocuVerity modules.
"""
from __future__ import annotations

import base64
import json
import sys
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "mcp_server"
sys.path.insert(0, str(ENGINE))

from forensics import examine_case, render_report, save_report  # noqa: E402
from indicators import (DOCUMENT_TYPES, GENUINE_EXPECTATION, INDICATORS,  # noqa: E402
                        MECHANISMS, checklist_for)
from report_html import report_page  # noqa: E402

HOST, PORT = "127.0.0.1", 8765
UPLOAD_DIR = HERE / "uploads"
REPORT_DIR = HERE.parents[1] / "reports" / "ui"
MAX_UPLOAD = 25 * 1024 * 1024
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
SAMPLES = {
    "tampered_pdf": ENGINE / "samples" / "tampered_certificate.pdf",
    "genuine_pdf": ENGINE / "samples" / "genuine_certificate.pdf",
}


def meta() -> dict:
    return {
        "document_types": {k: v["label"] for k, v in DOCUMENT_TYPES.items()},
        "checklists": {
            k: [dict(item, genuine=GENUINE_EXPECTATION.get(item["indicator"], ""))
                for item in checklist_for(k)]
            for k in DOCUMENT_TYPES
        },
        "samples": list(SAMPLES),
    }


def verdict(log10_lr: float) -> dict:
    if log10_lr >= 1:
        return {"level": "forged", "label": "LIKELY FORGED / ALTERED"}
    if log10_lr >= 0.3:
        return {"level": "suspicious", "label": "SUSPICIOUS - FURTHER EXAMINATION NEEDED"}
    if log10_lr > -0.3:
        return {"level": "inconclusive", "label": "INCONCLUSIVE"}
    return {"level": "genuine", "label": "NO SIGN OF FORGERY IN THE CHECKS PERFORMED"}


def _store_upload(file: dict) -> Path:
    raw = base64.b64decode(file.get("data", ""), validate=True)
    if not raw:
        raise ValueError("Uploaded file is empty.")
    if len(raw) > MAX_UPLOAD:
        raise ValueError("File is larger than 25 MB.")
    suffix = Path(file.get("name", "")).suffix.lower()
    if raw.startswith(b"%PDF-"):
        suffix = ".pdf"
    elif suffix not in IMAGE_SUFFIXES:
        raise ValueError("Upload a PDF or an image (JPG, PNG, TIFF, BMP, WEBP).")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    path.write_bytes(raw)
    return path


def explain(result: dict) -> dict:
    contributions = result["evaluation"]["contributions"]
    why, consistent = [], []
    for c in sorted(contributions, key=lambda c: c["log10_contribution"], reverse=True):
        ind = INDICATORS[c["indicator"]]
        entry = {
            "check": c["label"],
            "category": c["category"],
            "found": c["note"] or ("Anomaly observed by examiner" if c["status"] == "present"
                                   else "Checked - no anomaly"),
            "genuine": GENUINE_EXPECTATION.get(c["indicator"], ""),
            "lr": c["lr"],
            "confidence": c["confidence"],
        }
        if c["status"] == "present":
            entry["points_to"] = MECHANISMS[ind.mechanism]
            why.append(entry)
        else:
            consistent.append(entry)
    return {"why": why, "consistent": consistent}


def _check(name: str, result: str, detail: str, indicator: str | None = None) -> dict:
    return {"check": name, "result": result, "detail": detail, "indicator": indicator}


def _from_finding(name: str, findings: dict, indicator: str, skipped_reason: str) -> dict:
    f = findings.get(indicator)
    if not f:
        return _check(name, "skipped", skipped_reason, indicator)
    return _check(name, "flag" if f["status"] == "present" else "pass", f["note"], indicator)


def automated_checks(case: dict, result: dict) -> list[dict]:
    pdf, img = result.get("pdf_metadata"), result.get("image_analysis")
    if pdf:
        found = {f["indicator"]: f for f in pdf["findings"]}
        date_reason = ("Enter the stated issue date to run this check" if not case.get("stated_issue_date")
                       else "File has no creation/modification dates")
        return [
            _check("Valid PDF file", "pass", f"{pdf['size_bytes']:,} bytes, starts with %PDF header"),
            _check("Fingerprint (SHA-256)", "info", pdf["sha256"]),
            _from_finding("Number of saves (hidden re-saves)", found, "incremental_updates", "Could not count revisions"),
            _from_finding("Software that produced the file", found, "producer_editing_tool", "No producer/creator recorded in file"),
            _from_finding("Modified after it was created", found, "mod_after_creation", "Creation/modification dates missing"),
            _from_finding("Created or modified after the stated issue date", found, "mod_date_after_issue", date_reason),
            _from_finding("Info metadata vs XMP metadata", found, "metadata_inconsistent", "File has no XMP metadata packet"),
            _check("Digital signature", "info", "Signature present (not validated)" if pdf["has_digital_signature"]
                   else "No digital signature in file"),
        ]
    if img:
        from PIL import Image
        with Image.open(case["image_file"]) as im:
            desc = f"{im.format or 'image'}, {im.width}×{im.height} px, mode {im.mode}"
        found = {f["indicator"]: f for f in img["findings"]}
        exif_reason = next((n for n in img["notes"] if "EXIF" in n), "No EXIF metadata")
        return [
            _check("Valid image file", "pass", desc),
            _from_finding("Editing software in EXIF metadata", found, "editing_software_in_exif", exif_reason),
            _from_finding("Error Level Analysis (compression consistency)", found, "ela_anomaly", "ELA could not run"),
        ]
    return []


def run_examination(body: dict) -> dict:
    case = {
        "case_id": (body.get("case_id") or f"UI-{uuid.uuid4().hex[:6].upper()}").strip(),
        "document_type": body.get("document_type") if body.get("document_type") in DOCUMENT_TYPES else "generic",
        "document_description": body.get("description", ""),
        "submitted_by": body.get("submitted_by") or "Not stated",
        "stated_issue_date": body.get("stated_issue_date", ""),
        "expected_producer": body.get("expected_producer", ""),
        "generated_on_demand": bool(body.get("generated_on_demand")),
        "examiner": {"name": body.get("examiner_name") or "TBD", "designation": "Document Examiner"},
        "findings": [
            {"indicator": f["indicator"], "status": f["status"],
             "confidence": f.get("confidence", "moderate"), "note": f.get("note", "")}
            for f in body.get("findings", [])
            if f.get("indicator") in INDICATORS and f.get("status") in ("present", "absent")
        ],
    }

    if body.get("sample") in SAMPLES:
        path = SAMPLES[body["sample"]]
        display_name = path.name
    elif body.get("file"):
        path = _store_upload(body["file"])
        display_name = Path(body["file"].get("name") or path.name).name
    else:
        path = display_name = None
    if path is not None:
        key = "pdf_file" if path.suffix.lower() == ".pdf" else "image_file"
        case[key] = str(path)
        case["document_description"] = case["document_description"] or display_name

    result = examine_case(case)
    report = render_report(case, result)
    report_path = save_report(case["case_id"], report, REPORT_DIR)
    report_html = report_page(report, f"DocuVerity report {case['case_id']}")
    report_path.with_suffix(".html").write_text(report_html, encoding="utf-8")

    machine = (result.get("pdf_metadata") or {}).get("findings", []) + \
              (result.get("image_analysis") or {}).get("findings", [])
    doc_items = checklist_for(case["document_type"])
    manual_ids = {f["indicator"] for f in case["findings"]}

    pdf, img = result.get("pdf_metadata"), result.get("image_analysis")
    file_facts = None
    if pdf:
        file_facts = {"type": "PDF", "sha256": pdf["sha256"], "revisions": pdf["revisions"],
                      "producer_history": [h.get("Producer", "-") for h in pdf["info_history"]],
                      "created": pdf["info"].get("CreationDate", "-"),
                      "modified": pdf["info"].get("ModDate", "-"), "notes": pdf["notes"]}
    elif img:
        file_facts = {"type": "Image", "ela_score": round(img["ela_score"], 2), "notes": img["notes"]}

    return {
        "case_id": case["case_id"],
        "verdict": verdict(result["evaluation"]["combined_log10_lr"]),
        "evaluation": {k: result["evaluation"][k] for k in
                       ("combined_lr", "combined_log10_lr", "verbal_conclusion", "triage_score")},
        "classification": result["classification"],
        "explanation": explain(result),
        "still_to_check": result["recommended_examinations"],
        "standards": result["standards"],
        "file_facts": file_facts,
        "file_name": display_name,
        "automated_checks": automated_checks(case, result),
        "machine_findings": [{"indicator": f["indicator"], "status": f["status"], "note": f["note"]} for f in machine],
        "coverage": {
            "checklist_total": len(doc_items),
            "examiner_recorded": len(manual_ids),
            "auto_answered": len({f["indicator"] for f in machine} - manual_ids),
        },
        "report_markdown": report,
        "report_html": report_html,
        "report_path": str(report_path),
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, status: int, data: dict) -> None:
        self._send(status, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/meta":
            self._json(200, meta())
        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/examine":
            return self._json(404, {"error": "Not found"})
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_UPLOAD * 2:
            return self._json(413, {"error": "Request too large."})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            self._json(200, run_examination(body))
        except (ValueError, FileNotFoundError, KeyError) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:  # surface unexpected failures to the UI instead of a dead request
            self._json(500, {"error": f"Examination failed: {exc}"})

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[ui] {self.address_string()} {fmt % args}\n")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"DocuVerity UI running at {url}  (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
