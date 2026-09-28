"""Likelihood-ratio evaluation of examiner findings.

Propositions (ENFSI Guideline for Evaluative Reporting, 2015 style):
    Hp: the questioned document is forged or has been altered
    Hd: the questioned document is genuine and unaltered

Each finding contributes log10(LR). Findings in the same category are rarely
independent (a simulated signature usually shows tremor AND blunt endings), so
within a category the strongest finding counts fully and each further one is
damped by half. This keeps a long list of correlated observations from
producing an overconfident result.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from indicators import CATEGORIES, INDICATORS, MECHANISMS

CONFIDENCE_EXPONENT = {"low": 0.5, "moderate": 1.0, "high": 1.2}
DAMPING = 0.5
MAX_ABS_LOG10_LR = 6.0  # beyond 10^6 the independence model is not credible

VERBAL_SCALE = [
    (1.0, "weak support"),
    (2.0, "moderate support"),
    (3.0, "moderately strong support"),
    (4.0, "strong support"),
    (6.0, "very strong support"),
    (math.inf, "extremely strong support"),
]


@dataclass
class Contribution:
    indicator: str
    label: str
    category: str
    status: str
    confidence: str
    note: str
    lr: float
    weight: float = 1.0

    @property
    def log10_contribution(self) -> float:
        return round(math.log10(self.lr) * self.weight, 4)


@dataclass
class Evaluation:
    contributions: list[Contribution]
    combined_log10_lr: float
    verbal_conclusion: str
    triage_score: float
    mechanisms: list[dict]
    categories_with_anomalies: list[str]
    unknown_indicators: list[str] = field(default_factory=list)

    @property
    def combined_lr(self) -> float:
        return 10 ** self.combined_log10_lr

    def to_dict(self) -> dict:
        return {
            "combined_lr": round(self.combined_lr, 2),
            "combined_log10_lr": round(self.combined_log10_lr, 2),
            "verbal_conclusion": self.verbal_conclusion,
            "triage_score": self.triage_score,
            "mechanisms": self.mechanisms,
            "categories_with_anomalies": self.categories_with_anomalies,
            "unknown_indicators": self.unknown_indicators,
            "contributions": [
                {
                    "indicator": c.indicator,
                    "label": c.label,
                    "category": CATEGORIES[c.category],
                    "status": c.status,
                    "confidence": c.confidence,
                    "lr": round(c.lr, 3),
                    "damping_weight": c.weight,
                    "log10_contribution": c.log10_contribution,
                    "note": c.note,
                }
                for c in self.contributions
            ],
        }


def verbal_equivalent(log10_lr: float) -> str:
    if abs(log10_lr) < 0.1:
        return "The findings do not meaningfully support either proposition."
    magnitude = abs(log10_lr)
    strength = next(label for upper, label in VERBAL_SCALE if magnitude <= upper)
    if log10_lr > 0:
        return (f"The findings provide {strength} for the proposition that the "
                f"document is forged or altered, rather than genuine.")
    return (f"The findings provide {strength} for the proposition that the "
            f"document is genuine and unaltered, rather than forged or altered.")


def _build_contribution(finding: dict) -> Contribution:
    ind = INDICATORS[finding["indicator"]]
    status = finding.get("status", "present")
    confidence = finding.get("confidence", "moderate")
    base_lr = ind.lr_present if status == "present" else ind.lr_absent
    exponent = CONFIDENCE_EXPONENT.get(confidence, 1.0)
    return Contribution(
        indicator=ind.id,
        label=ind.label,
        category=ind.category,
        status=status,
        confidence=confidence,
        note=finding.get("note", ""),
        lr=base_lr ** exponent,
    )


def _apply_damping(contributions: list[Contribution]) -> None:
    groups: dict[tuple[str, bool], list[Contribution]] = {}
    for c in contributions:
        groups.setdefault((c.category, c.lr >= 1), []).append(c)
    for group in groups.values():
        group.sort(key=lambda c: abs(math.log10(c.lr)), reverse=True)
        for rank, c in enumerate(group):
            c.weight = DAMPING ** rank


def evaluate(findings: list[dict]) -> Evaluation:
    unknown = [f.get("indicator", "?") for f in findings if f.get("indicator") not in INDICATORS]
    contributions = [
        _build_contribution(f)
        for f in findings
        if f.get("indicator") in INDICATORS and f.get("status", "present") in ("present", "absent")
    ]
    _apply_damping(contributions)

    total = sum(c.log10_contribution for c in contributions)
    total = max(-MAX_ABS_LOG10_LR, min(MAX_ABS_LOG10_LR, total))

    lr = 10 ** total
    triage_score = round(100 * lr / (1 + lr), 1)

    mechanism_scores: dict[str, float] = {}
    categories: list[str] = []
    for c in contributions:
        if c.lr > 1:
            mech = INDICATORS[c.indicator].mechanism
            mechanism_scores[mech] = mechanism_scores.get(mech, 0.0) + c.log10_contribution
            if CATEGORIES[c.category] not in categories:
                categories.append(CATEGORIES[c.category])
    mechanisms = [
        {"mechanism": m, "description": MECHANISMS[m], "log10_support": round(s, 2)}
        for m, s in sorted(mechanism_scores.items(), key=lambda kv: kv[1], reverse=True)
    ]

    return Evaluation(
        contributions=contributions,
        combined_log10_lr=round(total, 4),
        verbal_conclusion=verbal_equivalent(total),
        triage_score=triage_score,
        mechanisms=mechanisms,
        categories_with_anomalies=categories,
        unknown_indicators=unknown,
    )


def classify(evaluation: Evaluation) -> dict:
    mechs = evaluation.mechanisms
    if not mechs:
        return {
            "anomaly_type": "No anomaly indicative of forgery observed",
            "primary_mechanism": None,
            "secondary_mechanisms": [],
        }
    primary = mechs[0]
    secondary = [m for m in mechs[1:] if m["log10_support"] >= 0.5]
    anomaly_type = "Composite forgery" if secondary else primary["description"]
    return {
        "anomaly_type": anomaly_type,
        "primary_mechanism": primary,
        "secondary_mechanisms": secondary,
    }
