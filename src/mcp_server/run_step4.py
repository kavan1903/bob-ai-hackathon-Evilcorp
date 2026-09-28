import os
import json
from pathlib import Path

# Add parent directory to path so we can import modules
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from forensics import examine_case, render_report, save_report
from image_checker import analyze_image

def main():
    out_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    examiner = {"name": "Bob Assistant", "designation": "AI Document Examiner"}
    
    # --- Case 1: Genuine Signature (CEDAR) ---
    case_1 = {
        "case_id": "CASE-001-GENUINE",
        "document_type": "property_document",
        "document_description": "Property deed with genuine signature",
        "submitted_by": "State Police",
        "examiner": examiner,
        "findings": [
            {"indicator": "tremor_hesitation", "status": "absent", "confidence": "high", "note": "Signature is fluid and natural."},
            {"indicator": "proportion_slant_mismatch", "status": "absent", "confidence": "high", "note": "Proportions match exemplars."},
            {"indicator": "tracing_guidelines", "status": "absent", "confidence": "high", "note": "No indented guidelines found."}
        ]
    }
    
    # --- Case 2: Forged Signature (CEDAR) ---
    case_2 = {
        "case_id": "CASE-002-FORGED",
        "document_type": "property_document",
        "document_description": "Property deed with suspected forged signature",
        "submitted_by": "State Police",
        "examiner": examiner,
        "findings": [
            {"indicator": "tremor_hesitation", "status": "present", "confidence": "high", "note": "Clear hesitation and drawn line quality observed."},
            {"indicator": "blunt_starts_ends", "status": "present", "confidence": "high", "note": "Blunt starts on initial strokes."},
            {"indicator": "tracing_guidelines", "status": "absent", "confidence": "high", "note": "No guidelines found."}
        ]
    }
    
    # --- Case 3: Tampered Digital Image (CG-1050) ---
    # We will run our image checker on a sample tampered image to generate findings
    # Assuming cg1050 dataset is downloaded in datasets/cg1050
    tampered_img_dir = Path(os.path.dirname(os.path.abspath(__file__))).parents[3] / "datasets" / "cg1050" / "TRAINING_CG-1050" / "TRAINING" / "TAMPERED"
    
    image_findings = []
    if tampered_img_dir.exists():
        tampered_images = list(tampered_img_dir.glob("*.*"))
        if tampered_images:
            sample_img = tampered_images[0]
            print(f"Running image checker on {sample_img}")
            img_result = analyze_image(str(sample_img))
            image_findings = img_result.get("findings", [])
            
    case_3 = {
        "case_id": "CASE-003-DIGITAL",
        "document_type": "identity_document",
        "document_description": "Digital scan of an identity document",
        "submitted_by": "Immigration",
        "examiner": examiner,
        "findings": image_findings
    }
    
    cases = [case_1, case_2, case_3]
    
    for case in cases:
        print(f"Processing {case['case_id']}...")
        result = examine_case(case)
        report_md = render_report(case, result)
        saved_path = save_report(case['case_id'], report_md, out_dir)
        print(f"Report saved to {saved_path}")
        
    print("Step 4 complete. 3 reports generated.")

if __name__ == "__main__":
    main()
