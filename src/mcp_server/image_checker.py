import io
import os
from pathlib import Path

import numpy as np
from PIL import ExifTags, Image, ImageChops, ImageEnhance

EDITING_SOFTWARE = [
    "photoshop", "gimp", "lightroom", "paint.net", "snapseed", "canva", "picsart", "vsco", "pixlr", "fotor", "coreldraw"
]

def check_image_metadata(img: Image.Image) -> dict:
    findings = []
    notes = []
    
    exif_data = img.getexif()
    if not exif_data:
        notes.append("No EXIF metadata found.")
        return {"findings": findings, "notes": notes}
        
    software = None
    for tag_id in exif_data:
        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
        if tag_name == "Software":
            software = exif_data.get(tag_id)
            break
            
    if software:
        notes.append(f"Software tag found: {software}")
        software_lower = software.lower()
        hit = any(tool in software_lower for tool in EDITING_SOFTWARE)
        findings.append({
            "indicator": "editing_software_in_exif",
            "status": "present" if hit else "absent",
            "confidence": "high" if hit else "moderate",
            "note": f"EXIF Software tag: {software}"
        })
    else:
        notes.append("No Software tag in EXIF.")
        
    return {"findings": findings, "notes": notes}

def perform_ela(img: Image.Image, quality: int = 90) -> float:
    """Perform Error Level Analysis and return an anomaly score."""
    if img.mode != 'RGB':
        img = img.convert('RGB')

    buffer = io.BytesIO()
    img.save(buffer, 'JPEG', quality=quality)
    buffer.seek(0)
    temp_img = Image.open(buffer)
    temp_img.load()
    
    # Calculate the difference between the original and the resaved image
    ela_image = ImageChops.difference(img, temp_img)
    
    # Calculate the max difference across RGB channels
    extrema = ela_image.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    
    if max_diff == 0:
        max_diff = 1
        
    # Scale the difference image to make it visible (optional, but good for scoring)
    scale = 255.0 / max_diff
    ela_image = ImageEnhance.Brightness(ela_image).enhance(scale)
    
    # Calculate anomaly score (variance or max area difference)
    ela_array = np.array(ela_image)
    
    # Use standard deviation as a proxy for localized editing
    # Unedited images tend to have uniform ELA noise (low std dev of local variations)
    # Edited regions have distinctly different noise patterns
    
    temp_img.close()
    return np.std(ela_array)

def analyze_image(path: str) -> dict:
    try:
        img = Image.open(path)
        img.load()
    except Exception as e:
        return {"error": str(e)}
        
    meta_result = check_image_metadata(img)
    ela_score = perform_ela(img)
    
    # Threshold for ELA score to determine tampering
    ela_threshold = 10.0 # Tuned for Kaggle dataset
    
    is_tampered_ela = ela_score > ela_threshold
    
    meta_result["findings"].append({
        "indicator": "ela_anomaly",
        "status": "present" if is_tampered_ela else "absent",
        "confidence": "moderate",
        "note": f"ELA standard deviation {ela_score:.2f} (threshold {ela_threshold})"
    })

    return {
        "file": os.path.basename(path),
        "ela_score": float(ela_score),
        "is_tampered": any(f["status"] == "present" for f in meta_result["findings"]),
        "findings": meta_result["findings"],
        "notes": meta_result["notes"]
    }

if __name__ == "__main__":
    # Test on Kaggle dataset
    original_dir = Path("c:/Users/hp/OneDrive/Desktop/Hackathon/datasets/cg1050/TRAINING_CG-1050/TRAINING/ORIGINAL")
    tampered_dir = Path("c:/Users/hp/OneDrive/Desktop/Hackathon/datasets/cg1050/TRAINING_CG-1050/TRAINING/TAMPERED")
    
    if not original_dir.exists() or not tampered_dir.exists():
        print("Dataset not found. Please verify the paths.")
        exit(1)
        
    original_images = list(original_dir.glob("*.*"))[:50] # Test on subset for speed
    tampered_images = list(tampered_dir.glob("*.*"))[:50]
    
    correct_original = 0
    correct_tampered = 0
    
    print("Testing Original Images...")
    for img_path in original_images:
        res = analyze_image(str(img_path))
        if res.get("is_tampered") is False:
            correct_original += 1
            
    print("Testing Tampered Images...")
    for img_path in tampered_images:
        res = analyze_image(str(img_path))
        if res.get("is_tampered") is True:
            correct_tampered += 1
            
    print(f"Originals correctly identified as genuine: {correct_original}/{len(original_images)} ({(correct_original/len(original_images))*100:.1f}%)")
    print(f"Tampered correctly identified as tampered: {correct_tampered}/{len(tampered_images)} ({(correct_tampered/len(tampered_images))*100:.1f}%)")
