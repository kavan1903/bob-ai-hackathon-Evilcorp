import io
import os
from pathlib import Path
import pickle

import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

def extract_ela_features(img_path, quality=90):
    try:
        img = Image.open(img_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        buffer = io.BytesIO()
        img.save(buffer, 'JPEG', quality=quality)
        buffer.seek(0)
        temp_img = Image.open(buffer)
        
        ela_image = ImageChops.difference(img, temp_img)
        extrema = ela_image.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0: max_diff = 1
            
        scale = 255.0 / max_diff
        ela_image = ImageEnhance.Brightness(ela_image).enhance(scale)
        ela_array = np.array(ela_image)
        
        # Extract features
        return [np.mean(ela_array), np.std(ela_array), np.max(ela_array)]
    except Exception as e:
        return None

if __name__ == "__main__":
    print("Step 1: Extracting ELA features from the Kaggle dataset...")
    
    base_dir = Path("c:/Users/hp/OneDrive/Desktop/Hackathon/datasets/cg1050/TRAINING_CG-1050/TRAINING")
    original_dir = base_dir / "ORIGINAL"
    tampered_dir = base_dir / "TAMPERED"
    
    X = []
    y = []
    
    # Process Originals
    print("Processing Original (Genuine) images...")
    for img_path in list(original_dir.glob("*.*")):
        feats = extract_ela_features(img_path)
        if feats:
            X.append(feats)
            y.append(0) # 0 = Genuine
            
    # Process Tampered
    print("Processing Tampered (Forged) images...")
    for img_path in list(tampered_dir.glob("*.*")):
        feats = extract_ela_features(img_path)
        if feats:
            X.append(feats)
            y.append(1) # 1 = Forged
            
    X = np.array(X)
    y = np.array(y)
    
    print(f"\nExtracted features for {len(X)} images.")
    
    print("Step 2: Training the Machine Learning Model (Random Forest)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    print("\nStep 3: Evaluating Model Performance...")
    y_pred = model.predict(X_test)
    print(f"Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
    print("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Genuine", "Forged"]))
    
    model_path = "ela_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
        
    print(f"\nModel successfully trained and saved to {model_path}!")
