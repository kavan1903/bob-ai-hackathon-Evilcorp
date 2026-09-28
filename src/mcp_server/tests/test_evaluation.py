import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import classify, evaluate, verbal_equivalent  # noqa: E402
from indicators import INDICATORS, checklist_for  # noqa: E402
from standards import standards_for  # noqa: E402


def f(indicator, status="present", confidence="moderate"):
    return {"indicator": indicator, "status": status, "confidence": confidence}


class TestIndicators(unittest.TestCase):
    def test_every_indicator_has_valid_lrs(self):
        for ind in INDICATORS.values():
            self.assertGreater(ind.lr_present, 1, ind.id)
            self.assertLess(ind.lr_absent, 1, ind.id)

    def test_checklist_follows_document_type_order(self):
        items = checklist_for("vaccination_certificate")
        self.assertEqual(items[0]["category"], "Digital file & metadata")
        self.assertFalse(any(i["category"] == "Signatures & handwriting" for i in items))

    def test_unknown_document_type_falls_back_to_generic(self):
        self.assertEqual(len(checklist_for("nonsense")), len(INDICATORS))


class TestEvaluation(unittest.TestCase):
    def test_single_finding_lr_is_indicator_lr(self):
        ev = evaluate([f("tremor_hesitation")])
        self.assertAlmostEqual(ev.combined_lr, 8.0, places=2)
        self.assertIn("weak support", ev.verbal_conclusion)
        self.assertIn("forged or altered, rather than genuine", ev.verbal_conclusion)

    def test_same_category_findings_are_damped(self):
        ev = evaluate([f("tremor_hesitation"), f("blunt_starts_ends")])
        expected = math.log10(8) + 0.5 * math.log10(5)
        self.assertAlmostEqual(ev.combined_log10_lr, expected, places=3)
        self.assertIn("moderate support", ev.verbal_conclusion)

    def test_different_categories_are_not_damped(self):
        ev = evaluate([f("tremor_hesitation"), f("watermark_absent")])
        self.assertAlmostEqual(ev.combined_log10_lr, math.log10(8) + math.log10(15), places=3)

    def test_absent_findings_support_genuineness(self):
        ev = evaluate([f("watermark_absent", "absent"), f("security_feature_missing", "absent")])
        self.assertLess(ev.combined_log10_lr, 0)
        self.assertIn("genuine and unaltered", ev.verbal_conclusion)

    def test_low_confidence_weakens_finding(self):
        ev = evaluate([f("tremor_hesitation", confidence="low")])
        self.assertAlmostEqual(ev.combined_lr, math.sqrt(8), places=2)

    def test_no_findings_is_neutral(self):
        ev = evaluate([])
        self.assertEqual(ev.combined_log10_lr, 0)
        self.assertIn("do not meaningfully support", ev.verbal_conclusion)
        self.assertEqual(ev.triage_score, 50.0)

    def test_combined_lr_is_capped(self):
        many = [f(i, confidence="high") for i in INDICATORS]
        self.assertEqual(evaluate(many).combined_log10_lr, 6.0)

    def test_unknown_indicators_are_reported_not_scored(self):
        ev = evaluate([f("made_up_indicator"), f("tremor_hesitation")])
        self.assertEqual(ev.unknown_indicators, ["made_up_indicator"])
        self.assertEqual(len(ev.contributions), 1)

    def test_verbal_scale_boundaries(self):
        self.assertIn("weak support", verbal_equivalent(0.9))
        self.assertIn("moderately strong support", verbal_equivalent(2.5))
        self.assertIn("very strong support", verbal_equivalent(5.0))
        self.assertIn("extremely strong support", verbal_equivalent(6.5))


class TestClassification(unittest.TestCase):
    def test_transplanted_signature(self):
        cls = classify(evaluate([f("signature_identical_overlay")]))
        self.assertEqual(cls["primary_mechanism"]["mechanism"], "transplanted_signature")
        self.assertEqual(cls["secondary_mechanisms"], [])

    def test_composite_when_two_strong_mechanisms(self):
        cls = classify(evaluate([f("tremor_hesitation"), f("mod_date_after_issue", confidence="high")]))
        self.assertEqual(cls["anomaly_type"], "Composite forgery")
        self.assertEqual(cls["primary_mechanism"]["mechanism"], "digital_manipulation")

    def test_nothing_found(self):
        cls = classify(evaluate([f("watermark_absent", "absent")]))
        self.assertIsNone(cls["primary_mechanism"])


class TestStandards(unittest.TestCase):
    def test_digital_adds_electronic_record_provision(self):
        s = standards_for(["digital"])
        self.assertTrue(any("s.63" in p for p in s["legal_provisions_to_verify"]))

    def test_signature_standards_included(self):
        s = standards_for(["signature"])
        self.assertTrue(any("Handwritten" in x for x in s["examination_standards"]))


if __name__ == "__main__":
    unittest.main()
