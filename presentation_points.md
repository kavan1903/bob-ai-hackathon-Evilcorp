# DocuVerity: AI-Powered Document Forgery Detection Assistant

## Slide 1: Title & Team
**Project Title:** DocuVerity - Court-Admissible Document Forensics  
**Team Name:** Team Evilcorp  
**Team Members:**  
- [Your Name]
- [Member 2 Name]
- [Member 3 Name]  
**Track:** 1 - Physical & Digital Evidence  

---

## Slide 2: The Problem & Our Solution
**The Problem:**
- **Rampant Fraud:** Over 3,000+ fake degrees recorded in 2022, alongside forged COVID certificates and property documents.
- **Manual Bottleneck:** Current forensic verification is entirely manual, subjective, and struggles to detect modern digital alterations (like metadata spoofing and copy-pasted signatures).

**Our System (DocuVerity):**
- We built a **Bob-powered guided examination workflow** that completely automates forgery detection.
- **Why it wins:** Instead of using a "black-box" AI that courts reject, our system uses mathematically explainable Computer Vision and Likelihood Ratios to draft **court-admissible expert opinion reports**.

---

## Slide 3: The Input (What It Analyzes)
When an investigator uploads a suspected document (PDF or Image), our automated master pipeline simultaneously runs 5 forensic checks:

**1. Digital Metadata (EXIF/ELA):** Detects hidden incremental saves, modification dates after the issue date, and mismatched JPEG grids.
**2. Font Inconsistencies:** Uses OpenCV Edge Detection to flag misaligned text baselines indicating pasted text.
**3. Paper Anomalies:** Calculates Laplacian variance to detect artificial background smoothing (digital erasure).
**4. Signature Mismatches:** Maps contours to detect isolated, perfect-black strokes (transparent PNG signatures).
**5. Ink Spread:** Analyzes Sobel gradients to catch unnaturally sharp anti-aliased digital ink vs. natural bleeding ink.

---

## Slide 4: The Output & Validation (Demo)
*(Tip: Put screenshots of the UI on this slide!)*

**The Results Dashboard:**
- **Automated Triage Score:** The system classifies the anomaly type and outputs a strict Likelihood Ratio (e.g. "Possibility of Forgery is 99.8/100").
- **Explainable Findings:** The UI clearly lists exactly *why* it failed (e.g., "Software: iLovePDF detected" or "Unnatural sharp digital ink detected").
- **Legal Mapping:** Findings are automatically mapped to the *Bhartiya Sakshya Adhiniyam, 2023, s.63* (Admissibility of electronic records) and BNS sections for forgery.
- **Validation:** Tested and validated locally against the industry-standard **MIDV-2020 Gov ID Dataset** and the CG-1050 Kaggle Forgery dataset.
