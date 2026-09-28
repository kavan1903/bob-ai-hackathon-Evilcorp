"""Examination standards and legal provisions relevant to each finding category.

Citations are reference pointers for the examiner, not verified legal advice.
Confirm the current edition of each standard and the applicability of each
provision before relying on it in a report.
"""
from __future__ import annotations

GENERAL_STANDARDS = [
    "ENFSI Guideline for Evaluative Reporting in Forensic Science (2015) - likelihood-ratio framework and verbal scale",
    "ASTM E2195 - Standard Terminology Relating to the Examination of Questioned Documents",
]

CATEGORY_STANDARDS = {
    "typography": [
        "SWGDOC Standard for Examination of Altered Documents",
        "SWGDOC Standard for Examination of Documents Produced with Toner Technology / Ink Jet Technology",
    ],
    "signature": [
        "ASTM E2290 - Standard Guide for Examination of Handwritten Items",
        "SWGDOC Standard for Examination of Handwritten Items",
        "SWGDOC Standard for Indentation Examinations (for traced signatures)",
    ],
    "substrate": [
        "ASTM E2325 - Standard Guide for Non-destructive Examination of Paper",
        "SWGDOC Standard for Examination of Altered Documents (erasures)",
    ],
    "ink": [
        "ASTM E1422 - Standard Guide for Test Methods for Forensic Writing Ink Comparison",
        "ASTM E1789 - Standard Guide for Writing Ink Identification",
    ],
    "digital": [
        "ISO/IEC 27037 - Guidelines for identification, collection, acquisition and preservation of digital evidence",
        "SWGDE Best Practices for Image Authentication",
    ],
}

LEGAL_PROVISIONS = {
    "always": [
        "Bharatiya Sakshya Adhiniyam, 2023, s.39 - opinion of experts (formerly Indian Evidence Act s.45)",
        "Bharatiya Nyaya Sanhita, 2023, s.336 - forgery (formerly IPC s.463/465)",
        "Bharatiya Nyaya Sanhita, 2023, s.340 - using a forged document or electronic record as genuine (formerly IPC s.471)",
    ],
    "digital": [
        "Bharatiya Sakshya Adhiniyam, 2023, s.63 - admissibility of electronic records / certificate (formerly Indian Evidence Act s.65B)",
    ],
}


def standards_for(categories: list[str]) -> dict:
    """categories: internal category ids (e.g. 'signature', 'digital')."""
    standards = list(GENERAL_STANDARDS)
    for cat in categories:
        for s in CATEGORY_STANDARDS.get(cat, []):
            if s not in standards:
                standards.append(s)
    legal = list(LEGAL_PROVISIONS["always"])
    if "digital" in categories:
        legal += LEGAL_PROVISIONS["digital"]
    return {
        "examination_standards": standards,
        "legal_provisions_to_verify": legal,
        "note": "Reference pointers only - confirm current editions and legal applicability before court use.",
    }
