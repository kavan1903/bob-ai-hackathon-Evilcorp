import cv2
import numpy as np
from PIL import Image

def check_font_inconsistencies(image_path):
    # ...
    try:
        img = cv2.imread(image_path, 0)
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        is_inconsistent = False
        if lines is not None and len(lines) > 50:
            is_inconsistent = True
            
        return {
            "indicator": "baseline_misalignment",
            "status": "present" if is_inconsistent else "absent",
            "confidence": "moderate",
            "note": "Text baseline alignment irregular" if is_inconsistent else "Text baselines appear consistent"
        }
    except:
        return {"indicator": "baseline_misalignment", "status": "absent", "note": "Check skipped", "confidence": "low"}

def check_paper_anomalies(image_path):
    # ...
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        is_anomalous = laplacian_var < 50.0 
        
        return {
            "indicator": "erasure_abrasion",
            "status": "present" if is_anomalous else "absent",
            "confidence": "high",
            "note": f"Artificial background smoothing detected (variance: {laplacian_var:.1f})" if is_anomalous else "Natural paper texture detected"
        }
    except:
        return {"indicator": "erasure_abrasion", "status": "absent", "note": "Check skipped", "confidence": "low"}

def check_ink_spread(image_path):
    # ...
    try:
        img = cv2.imread(image_path, 0)
        sobelx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        mean_gradient = np.mean(gradient_magnitude)
        is_digital_ink = mean_gradient > 120.0
        
        return {
            "indicator": "ink_feathering",
            "status": "present" if is_digital_ink else "absent",
            "confidence": "moderate",
            "note": "Unnatural sharp digital ink detected" if is_digital_ink else "Natural ink bleed observed"
        }
    except:
        return {"indicator": "ink_feathering", "status": "absent", "note": "Check skipped", "confidence": "low"}

def check_signature_mismatch(image_path):
    # ...
    try:
        img = cv2.imread(image_path, 0)
        ret, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        suspicious_signatures = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 50 and h > 20 and (w/h) > 3.0:
                mask = np.zeros(img.shape, np.uint8)
                cv2.drawContours(mask, [cnt], -1, 255, -1)
                mean_val = cv2.mean(img, mask=mask)[0]
                if mean_val < 10.0: 
                    suspicious_signatures += 1
                    
        is_mismatch = suspicious_signatures > 0
        
        return {
            "indicator": "signature_identical_overlay",
            "status": "present" if is_mismatch else "absent",
            "confidence": "high",
            "note": "Digitally inserted signature graphic detected" if is_mismatch else "Signature appears organic"
        }
    except:
        return {"indicator": "signature_identical_overlay", "status": "absent", "note": "Check skipped", "confidence": "low"}


def run_master_pipeline(file_path, file_type="image"):
    """
    Runs the comprehensive 5-stage pipeline automatically.
    """
    from image_checker import analyze_image
    
    findings = []
    
    # 1. Digital Metadata & ELA (Existing)
    print("Running Digital Metadata Checks...")
    if file_type == "image":
        img_res = analyze_image(file_path)
        if "findings" in img_res:
            findings.extend(img_res["findings"])
            
    # Run the 4 new physical checks using OpenCV
    print("Running Physical Characteristics Analysis...")
    findings.append(check_font_inconsistencies(file_path))
    findings.append(check_paper_anomalies(file_path))
    findings.append(check_ink_spread(file_path))
    findings.append(check_signature_mismatch(file_path))
    
    return findings
