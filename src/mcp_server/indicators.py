"""Catalogue of forgery indicators an examiner can check.

Each indicator carries a likelihood ratio (LR):
    LR = P(finding | document forged/altered) / P(finding | document genuine)

The LR values are illustrative starting points chosen to reflect the relative
diagnostic strength of each finding in questioned-document practice. They are
NOT calibrated against casework data and must be reviewed by a certified
examiner before real use.
"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = {
    "typography": "Typography & printing",
    "signature": "Signatures & handwriting",
    "substrate": "Paper & security features",
    "ink": "Ink & writing instruments",
    "digital": "Digital file & metadata",
}

# Forgery mechanisms an indicator points towards.
MECHANISMS = {
    "text_alteration": "Text insertion / alteration of an existing genuine document",
    "counterfeit": "Counterfeit document (not produced on genuine stock or by the issuer)",
    "simulated_signature": "Simulated (freehand-copied) signature",
    "traced_signature": "Traced signature",
    "transplanted_signature": "Transplanted (cut-and-paste / digitally overlaid) signature",
    "erasure": "Erasure followed by re-entry",
    "digital_manipulation": "Digital editing of an electronic document",
}


@dataclass(frozen=True)
class Indicator:
    id: str
    category: str
    label: str
    question: str
    lr_present: float
    mechanism: str
    lr_absent: float = 0.85


_INDICATOR_LIST = [
    # --- typography -------------------------------------------------------
    Indicator("font_family_mismatch", "typography",
              "Font face differs from the issuer's known template",
              "Does any field use a different typeface from the issuer's genuine template?",
              6.0, "text_alteration"),
    Indicator("spacing_irregular", "typography",
              "Irregular character or word spacing within a line",
              "Is character/word spacing irregular in any field compared with surrounding text?",
              4.0, "text_alteration"),
    Indicator("baseline_misalignment", "typography",
              "Field text sits off the baseline of surrounding text",
              "Is any text misaligned with the baseline or margins of the surrounding printed text?",
              5.0, "text_alteration"),
    Indicator("print_process_mismatch", "typography",
              "Printing process differs within the document",
              "Under magnification, is any field printed by a different process (e.g. inkjet on an offset-printed form)?",
              12.0, "text_alteration", lr_absent=0.7),
    # --- signature --------------------------------------------------------
    Indicator("tremor_hesitation", "signature",
              "Tremor, hesitation or unnatural pen pauses in the signature",
              "Does the signature show tremor, hesitation or slow, drawn line quality?",
              8.0, "simulated_signature"),
    Indicator("blunt_starts_ends", "signature",
              "Blunt stroke beginnings/endings instead of tapered flying strokes",
              "Do strokes start and end bluntly where the exemplars show tapered strokes?",
              5.0, "simulated_signature"),
    Indicator("unusual_pen_lifts", "signature",
              "Pen lifts at positions not seen in exemplars",
              "Are there pen lifts or patched strokes at unusual positions?",
              4.0, "simulated_signature"),
    Indicator("proportion_slant_mismatch", "signature",
              "Letter proportions or slant inconsistent with exemplars",
              "Are letter proportions, slant or spacing inconsistent with the known exemplars?",
              6.0, "simulated_signature"),
    Indicator("tracing_guidelines", "signature",
              "Indented guide lines or pencil traces beneath the signature",
              "Under oblique light / ESDA, are there indented guide lines or pencil traces under the signature?",
              20.0, "traced_signature", lr_absent=0.9),
    Indicator("signature_identical_overlay", "signature",
              "Signature superimposes exactly on another known signature",
              "Does the signature superimpose exactly (pixel-identical) on another known signature?",
              50.0, "transplanted_signature", lr_absent=0.9),
    # --- substrate --------------------------------------------------------
    Indicator("uv_fluorescence_differs", "substrate",
              "Paper fluoresces differently under UV than genuine stock",
              "Under UV, does the paper's fluorescence differ from genuine stock?",
              7.0, "counterfeit"),
    Indicator("watermark_absent", "substrate",
              "Expected watermark missing or incorrect",
              "Is the issuer's watermark missing, incorrect or simulated by printing?",
              15.0, "counterfeit", lr_absent=0.6),
    Indicator("security_feature_missing", "substrate",
              "Security features (microprint, hologram, guilloche) missing or degraded",
              "Are microprint, hologram, guilloche or other security features missing or degraded?",
              15.0, "counterfeit", lr_absent=0.6),
    Indicator("erasure_abrasion", "substrate",
              "Localised fibre disturbance indicating erasure",
              "Is there localised fibre disturbance, thinning or sheen indicating mechanical/chemical erasure?",
              10.0, "erasure"),
    # --- ink --------------------------------------------------------------
    Indicator("ink_differentiation", "ink",
              "Different ink formulations within the same entry",
              "Under VSC/IR, do parts of the same entry respond differently (different inks)?",
              12.0, "text_alteration", lr_absent=0.75),
    Indicator("ink_feathering", "ink",
              "Ink feathering over a treated or erased area",
              "Does ink feather or bleed abnormally in a localised area (treated surface)?",
              5.0, "erasure"),
    Indicator("overwriting_retouching", "ink",
              "Strokes overwritten or retouched",
              "Are any strokes or digits overwritten or retouched?",
              6.0, "text_alteration"),
    Indicator("line_crossing_sequence", "ink",
              "Line-crossing sequence inconsistent with the stated order of writing",
              "Is the sequence of intersecting strokes inconsistent with the claimed order of entries?",
              8.0, "text_alteration"),
    # --- digital ----------------------------------------------------------
    Indicator("mod_after_creation", "digital",
              "File modified after it was created",
              "Does the file's modification date differ from its creation date?",
              2.5, "digital_manipulation"),
    Indicator("mod_date_after_issue", "digital",
              "File created or modified after the stated issue date",
              "Was the file created or modified after the date the document claims to be issued?",
              20.0, "digital_manipulation", lr_absent=0.8),
    Indicator("producer_editing_tool", "digital",
              "Producer/creator is an editing tool, not the issuer's system",
              "Does the PDF producer/creator indicate an editing tool rather than the issuer's system?",
              6.0, "digital_manipulation"),
    Indicator("incremental_updates", "digital",
              "Multiple incremental saves appended to the file",
              "Does the file contain more than one revision (incremental updates)?",
              3.0, "digital_manipulation"),
    Indicator("metadata_inconsistent", "digital",
              "Info dictionary and XMP metadata disagree",
              "Do the PDF Info dictionary and XMP metadata disagree on dates or producer?",
              4.0, "digital_manipulation"),
    Indicator("verification_failed", "digital",
              "QR code / online verification does not match the issuer's record",
              "Does the QR code or verification URL fail to validate against the issuer's record?",
              40.0, "counterfeit", lr_absent=0.3),
    # LRs below are measured, not assumed: on 50 original + 50 tampered CG1050
    # images the current ELA check flagged 28% of tampered vs 26% of originals.
    Indicator("ela_anomaly", "digital",
              "Error Level Analysis shows uneven compression",
              "Does Error Level Analysis show regions compressed differently from the rest of the image?",
              1.1, "digital_manipulation", lr_absent=0.97),
    Indicator("editing_software_in_exif", "digital",
              "Image metadata names editing software",
              "Does the image's EXIF Software tag name an editing tool (e.g. Photoshop, GIMP, Canva)?",
              5.0, "digital_manipulation", lr_absent=0.95),
    # --- automated detectors (doc_checks) ----------------------------------
    # PROVISIONAL LRs: set from the synthetic ground-truth test set, not from casework.
    # Exception: auto_noise_inconsistent is measured on 1,460 CG-1050 images (5% false-positive point).
    Indicator("auto_font_inconsistent", "typography",
              "Automated: text run in a different font from matching text",
              "Automated check - does any field use a different font from the rest of the document?",
              4.0, "text_alteration", lr_absent=0.9),
    Indicator("auto_text_cover_up", "typography",
              "Automated: text hidden under a box or overwritten (PDF)",
              "Automated check - is any text in the PDF covered by a white box or drawn over other text?",
              20.0, "text_alteration", lr_absent=0.9),
    Indicator("auto_signature_mismatch", "signature",
              "Automated: signature differs from the known exemplar",
              "Automated check - does the questioned signature differ from the known genuine signature?",
              6.0, "simulated_signature", lr_absent=0.7),
    Indicator("auto_signature_identical", "signature",
              "Automated: signature is an exact copy of the exemplar",
              "Automated check - is the signature a pixel-identical copy of another signature?",
              30.0, "transplanted_signature", lr_absent=0.95),
    Indicator("auto_paper_patch", "substrate",
              "Automated: background patch differs in tone/grain",
              "Automated check - is there a lighter, smoother or differently textured patch in the background?",
              6.0, "erasure", lr_absent=0.9),
    Indicator("auto_noise_inconsistent", "substrate",
              "Automated: noise level inconsistent across the image",
              "Automated check - is one region of the image much noisier than the rest?",
              3.16, "digital_manipulation", lr_absent=0.88),
    Indicator("auto_ink_colour_mismatch", "ink",
              "Automated: text in a different ink colour",
              "Automated check - is any text run in a different ink colour from text of the same size?",
              5.0, "text_alteration", lr_absent=0.9),
    Indicator("auto_ink_spread", "ink",
              "Automated: ink spread / softer edges",
              "Automated check - do any strokes show ink spread (thicker, softer edges) compared with similar text?",
              3.0, "erasure", lr_absent=0.95),
]

AUTOMATED = {i.id for i in _INDICATOR_LIST if i.id.startswith("auto_")} | {
    "mod_after_creation", "mod_date_after_issue", "producer_editing_tool", "incremental_updates",
    "metadata_inconsistent", "ela_anomaly", "editing_software_in_exif"}

# What a genuine document shows for each check - used to explain findings.
GENUINE_EXPECTATION = {
    "font_family_mismatch": "Every field uses the issuer's standard template typeface.",
    "spacing_irregular": "Character and word spacing is uniform across each line.",
    "baseline_misalignment": "All text sits on the same baseline and margins as the printed form.",
    "print_process_mismatch": "The whole document is printed by one process (e.g. all offset or all laser).",
    "tremor_hesitation": "Signature strokes are fast and fluent, with smooth line quality.",
    "blunt_starts_ends": "Strokes begin and end with tapered 'flying' ends from a moving pen.",
    "unusual_pen_lifts": "Pen lifts occur only where the signer habitually lifts in exemplars.",
    "proportion_slant_mismatch": "Letter proportions and slant match the signer's known exemplars.",
    "tracing_guidelines": "No indented guide lines or pencil traces under the signature.",
    "signature_identical_overlay": "Natural variation - no two genuine signatures superimpose exactly.",
    "uv_fluorescence_differs": "Paper fluorescence under UV matches the issuer's genuine stock.",
    "watermark_absent": "The issuer's watermark is present and embedded in the paper (not printed).",
    "security_feature_missing": "Microprint, hologram and guilloche patterns are present and sharp.",
    "erasure_abrasion": "Paper fibres are undisturbed with uniform surface sheen.",
    "ink_differentiation": "Each entry is written in a single, consistent ink.",
    "ink_feathering": "Ink lines are crisp with no localised bleeding.",
    "overwriting_retouching": "Strokes and digits are written once, without retouching.",
    "line_crossing_sequence": "Stroke crossings match the stated order of writing.",
    "mod_after_creation": "Creation and modification dates are the same (file never edited).",
    "mod_date_after_issue": "File was created on or before the stated issue date and not edited after.",
    "producer_editing_tool": "Producer/creator is the issuer's own certificate system.",
    "incremental_updates": "Single revision - the file was saved once by the issuer.",
    "metadata_inconsistent": "Info dictionary and XMP metadata agree on dates and producer.",
    "verification_failed": "QR code / verification URL validates against the issuer's record.",
    "ela_anomaly": "Compression error level is uniform across the whole image.",
    "editing_software_in_exif": "EXIF shows the camera/scanner, not an editing program.",
    "auto_font_inconsistent": "Every field uses the same typeface; repeated characters are identical everywhere.",
    "auto_text_cover_up": "Each piece of text is drawn once; nothing is hidden under white boxes.",
    "auto_signature_mismatch": "Signature matches the writer's known signature in shape, slant and proportions.",
    "auto_signature_identical": "Natural variation - no two genuine signatures are pixel-identical.",
    "auto_paper_patch": "Paper tone and grain are uniform across the whole sheet.",
    "auto_noise_inconsistent": "Sensor/scan noise is uniform across the whole image.",
    "auto_ink_colour_mismatch": "All text of the same kind is in one consistent ink colour.",
    "auto_ink_spread": "Ink edges are equally crisp across comparable text.",
}

INDICATORS: dict[str, Indicator] = {i.id: i for i in _INDICATOR_LIST}

# Which categories to examine for each document type, in examination order.
DOCUMENT_TYPES = {
    "vaccination_certificate": {
        "label": "Vaccination / health certificate",
        "categories": ["digital", "typography", "substrate"],
    },
    "degree_certificate": {
        "label": "Degree / marksheet / academic certificate",
        "categories": ["substrate", "typography", "signature", "ink", "digital"],
    },
    "property_document": {
        "label": "Property deed / sale agreement / stamp paper",
        "categories": ["signature", "ink", "substrate", "typography"],
    },
    "fir_or_official_record": {
        "label": "FIR / official record / register entry",
        "categories": ["ink", "typography", "signature", "substrate"],
    },
    "identity_document": {
        "label": "Identity document",
        "categories": ["substrate", "typography", "digital"],
    },
    "generic": {
        "label": "Other / unspecified document",
        "categories": list(CATEGORIES),
    },
}


def checklist_for(document_type: str) -> list[dict]:
    doc = DOCUMENT_TYPES.get(document_type, DOCUMENT_TYPES["generic"])
    items = []
    for category in doc["categories"]:
        for ind in _INDICATOR_LIST:
            if ind.category == category and not ind.id.startswith("auto_"):
                items.append({
                    "indicator": ind.id,
                    "category": CATEGORIES[category],
                    "question": ind.question,
                })
    return items
