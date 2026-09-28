"""DocuVerity Web UI — lightweight Flask API serving the premium dashboard.

Run:  python app.py          → opens http://localhost:5000
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure sibling modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from forensics import examine_case, render_report
from image_checker import analyze_image
from pdf_metadata import analyze_pdf
from gcp_docai import process_document

app = Flask(__name__, static_folder="ui", static_url_path="")

UPLOAD_DIR = Path(tempfile.gettempdir()) / "docuverity_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# ── Pages ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("ui", "index.html")


# ── API endpoints ────────────────────────────────────────────────────────────
@app.route("/api/analyze-pdf", methods=["POST"])
def api_analyze_pdf():
    """Upload a PDF and get metadata analysis back."""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    path = UPLOAD_DIR / secure_filename(f.filename)
    f.save(str(path))
    stated_date = request.form.get("stated_issue_date", "")
    expected_producer = request.form.get("expected_producer", "")
    try:
        result = analyze_pdf(str(path), stated_issue_date=stated_date,
                             expected_producer=expected_producer)
        
        # Call Google Cloud Document AI
        docai_result = process_document(str(path), "application/pdf")
        result["document_ai"] = docai_result
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/analyze-image", methods=["POST"])
def api_analyze_image():
    """Upload an image and get ELA + EXIF analysis back."""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    path = UPLOAD_DIR / secure_filename(f.filename)
    f.save(str(path))
    
    # Determine mime type
    mime = "image/jpeg"
    if path.suffix.lower() == ".png": mime = "image/png"
        
    try:
        # Import the master pipeline
        from master_pipeline import run_master_pipeline
        
        # Run the all-in-one automated pipeline
        findings = run_master_pipeline(str(path), file_type="image")
        
        result = {
            "file": secure_filename(f.filename),
            "findings": findings,
            "notes": ["Master pipeline execution successful."]
        }
        
        # Still attempt to call Google Cloud Document AI if configured
        try:
            docai_result = process_document(str(path), mime)
            result["document_ai"] = docai_result
        except:
            pass # Fails gracefully if GCP isn't configured
            
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/examine", methods=["POST"])
def api_examine():
    """Run the full forensic evaluation pipeline and return JSON + markdown report."""
    data = request.get_json(force=True)
    case = {
        "case_id": data.get("case_id", "UI-CASE"),
        "document_type": data.get("document_type", "generic"),
        "document_description": data.get("document_description", ""),
        "submitted_by": data.get("submitted_by", "DocuVerity UI"),
        "stated_issue_date": data.get("stated_issue_date", ""),
        "expected_producer": data.get("expected_producer", ""),
        "examiner": {
            "name": data.get("examiner_name", "Examiner"),
            "designation": data.get("examiner_designation", ""),
        },
        "findings": data.get("findings", []),
        "pdf_file": data.get("pdf_file", ""),
    }
    result = examine_case(case)
    report_md = render_report(case, result)
    return jsonify({
        "evaluation": result["evaluation"],
        "classification": result["classification"],
        "standards": result["standards"],
        "recommended_examinations": result["recommended_examinations"],
        "report_markdown": report_md,
    })


@app.route("/api/sample/<name>")
def api_sample(name):
    """Load a built-in sample case."""
    samples = {
        "tampered": {
            "case_id": "SAMPLE-TAMPERED",
            "document_type": "degree_certificate",
            "document_description": "Mock diploma certificate — marks changed from 61.4% to 91.4%",
            "stated_issue_date": "2023-06-15",
            "examiner_name": "Demo Examiner",
            "findings": [
                {"indicator": "mod_date_after_issue", "status": "present", "confidence": "high",
                 "note": "File modified 2024-02-03 after stated issue date 2023-06-15"},
                {"indicator": "producer_editing_tool", "status": "present", "confidence": "high",
                 "note": "Software: iLovePDF — editing tool 'ilovepdf' in producer/creator"},
                {"indicator": "metadata_inconsistent", "status": "present", "confidence": "moderate",
                 "note": "Mismatch in producer (Info 'iLovePDF' vs XMP 'SBTE CertGen 3.2')"},
                {"indicator": "incremental_updates", "status": "present", "confidence": "moderate",
                 "note": "3 revision(s) found in file"},
                {"indicator": "mod_after_creation", "status": "present", "confidence": "moderate",
                 "note": "CreationDate 2023-06-15, ModDate 2024-02-03 UTC"},
            ],
        },
        "genuine": {
            "case_id": "SAMPLE-GENUINE",
            "document_type": "degree_certificate",
            "document_description": "Genuine diploma certificate — unmodified original",
            "stated_issue_date": "2023-06-15",
            "examiner_name": "Demo Examiner",
            "findings": [
                {"indicator": "mod_date_after_issue", "status": "absent", "confidence": "high",
                 "note": "No creation/modification after stated issue date 2023-06-15"},
                {"indicator": "producer_editing_tool", "status": "absent", "confidence": "high",
                 "note": "Software: SBTE CertGen 3.2 — no editing tool found"},
                {"indicator": "metadata_inconsistent", "status": "absent", "confidence": "moderate",
                 "note": "Info dictionary and XMP agree"},
                {"indicator": "incremental_updates", "status": "absent", "confidence": "moderate",
                 "note": "1 revision(s) found in file"},
            ],
        },
        "forged_signature": {
            "case_id": "SAMPLE-FORGED-SIG",
            "document_type": "property_document",
            "document_description": "Property deed with suspected forged signature",
            "examiner_name": "Demo Examiner",
            "findings": [
                {"indicator": "tremor_hesitation", "status": "present", "confidence": "high",
                 "note": "Clear hesitation and drawn line quality observed in signature"},
                {"indicator": "blunt_starts_ends", "status": "present", "confidence": "high",
                 "note": "Blunt starts on initial strokes — lacks natural taper"},
                {"indicator": "unusual_pen_lifts", "status": "present", "confidence": "moderate",
                 "note": "Pen lifts at mid-letter positions not seen in exemplars"},
                {"indicator": "proportion_slant_mismatch", "status": "present", "confidence": "moderate",
                 "note": "Letter proportions differ significantly from exemplars"},
            ],
        },
    }
    if name not in samples:
        return jsonify({"error": "Unknown sample"}), 404
    return jsonify(samples[name])


if __name__ == "__main__":
    print("\n  DocuVerity Dashboard -> http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
