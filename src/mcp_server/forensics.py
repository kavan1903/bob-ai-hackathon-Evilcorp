"""Core forensic reasoning logic for DocuVerity.

Kept dependency-free and framework-agnostic on purpose: server.py wraps these
functions as MCP tools, but they can be unit-tested or called directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

INDICATOR_CATEGORIES = [
    "font_inconsistency",
    "signature_mismatch",
    "paper_anomaly",
    "ink_spread_anomaly",
    "metadata_flag",
]

# Weight reflects how strongly each indicator, alone, tends to correlate with
# forgery in questioned-document practice. These are illustrative defaults —
# a real deployment should have these calibrated by a certified examiner.
INDICATOR_WEIGHTS = {
    "font_inconsistency": 15,
    "signature_mismatch": 30,
    "paper_anomaly": 20,
    "ink_spread_anomaly": 15,
    "metadata_flag": 20,
}

ANOMALY_CATEGORY_MAP = {
    ("signature_mismatch",): "Signature Forgery",
    ("font_inconsistency",): "Typographic Forgery",
    ("paper_anomaly",): "Physical Substrate Tampering",
    ("ink_spread_anomaly",): "Physical Substrate Tampering",
    ("metadata_flag",): "Digital Metadata Tampering",
}

EXAMINATION_STANDARDS = {
    "Signature Forgery": [
        "ASTM E2290 - Standard Guide for Examination of Handwritten Items",
        "SWGDOC Standard for Examination of Signatures",
    ],
    "Typographic Forgery": [
        "ASTM E2325 - Standard Guide for Nonintrusive Examination of Documents",
    ],
    "Physical Substrate Tampering": [
        "ASTM E1789 - Standard Guide for Writing Ink Identification",
        "ASTM E444 - Standard Guide for Scope of Work of Forensic Document Examiners",
    ],
    "Digital Metadata Tampering": [
        "SWGDE Best Practices for Digital Evidence Examination",
    ],
    "Composite / Multiple Indicators": [
        "ASTM E444 - Standard Guide for Scope of Work of Forensic Document Examiners",
        "SWGDOC Standard for Examination of Signatures",
        "SWGDE Best Practices for Digital Evidence Examination",
    ],
}


@dataclass
class Observation:
    """A single examiner-reported indicator flag."""

    category: str  # one of INDICATOR_CATEGORIES
    detail: str = ""
    severity: str = "moderate"  # low | moderate | high


@dataclass
class ObservationSet:
    document_id: str
    observations: list[Observation] = field(default_factory=list)

    def flagged_categories(self) -> list[str]:
        return sorted({o.category for o in self.observations})


SEVERITY_MULTIPLIER = {"low": 0.5, "moderate": 1.0, "high": 1.3}


def classify_anomaly(obs_set: ObservationSet) -> str:
    """Classify the dominant anomaly type from a set of flagged indicators."""
    flagged = obs_set.flagged_categories()
    if not flagged:
        return "No Anomaly Detected"
    if len(flagged) > 1:
        return "Composite / Multiple Indicators"
    return ANOMALY_CATEGORY_MAP.get(tuple(flagged), "Composite / Multiple Indicators")


def score_forgery_confidence(obs_set: ObservationSet) -> dict:
    """Return a 0-100 confidence score plus a per-indicator breakdown."""
    breakdown = {}
    total = 0.0
    for obs in obs_set.observations:
        weight = INDICATOR_WEIGHTS.get(obs.category, 10)
        multiplier = SEVERITY_MULTIPLIER.get(obs.severity, 1.0)
        contribution = min(weight * multiplier, 100)
        breakdown[obs.category] = round(contribution, 1)
        total += contribution
    score = round(min(total, 100), 1)
    return {"score": score, "breakdown": breakdown}


def map_to_examination_standard(anomaly_type: str) -> list[str]:
    return EXAMINATION_STANDARDS.get(
        anomaly_type, ["No standard mapping available for this anomaly type"]
    )


def draft_expert_report(
    obs_set: ObservationSet,
    anomaly_type: str,
    confidence: dict,
    standards: list[str],
    examiner_name: Optional[str] = None,
) -> str:
    """Render a structured expert opinion report as Markdown."""
    lines = [
        f"# Expert Opinion — Document {obs_set.document_id}",
        "",
        f"**Examiner:** {examiner_name or 'TBD'}",
        f"**Anomaly Classification:** {anomaly_type}",
        f"**Forgery Confidence Score:** {confidence['score']} / 100",
        "",
        "## Observations",
    ]
    for obs in obs_set.observations:
        lines.append(f"- **{obs.category}** (severity: {obs.severity}): {obs.detail}")

    lines += ["", "## Confidence Breakdown"]
    for category, contribution in confidence["breakdown"].items():
        lines.append(f"- {category}: +{contribution}")

    lines += ["", "## Relevant Examination Standards"]
    for standard in standards:
        lines.append(f"- {standard}")

    lines += [
        "",
        "## Disclaimer",
        (
            "This report was drafted with the assistance of an AI-guided "
            "workflow (DocuVerity) using documented, rule-based heuristics. "
            "It is a first-pass draft only and must be reviewed, validated, "
            "and signed off by a certified forensic document examiner before "
            "any court submission."
        ),
    ]
    return "\n".join(lines)
