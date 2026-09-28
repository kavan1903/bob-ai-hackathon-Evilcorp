import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pdf_metadata import _decode_pdf_string, analyze_pdf, parse_pdf_date  # noqa: E402
from samples.make_sample_pdfs import make_all  # noqa: E402


def status(report, indicator):
    return next((f["status"] for f in report["findings"] if f["indicator"] == indicator), None)


class TestPdfMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.paths = make_all(Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_genuine_certificate_has_no_digital_anomalies(self):
        r = analyze_pdf(str(self.paths["genuine"]), stated_issue_date="2023-06-15")
        self.assertEqual(r["revisions"], 1)
        for f in r["findings"]:
            self.assertEqual(f["status"], "absent", f)

    def test_tampered_certificate_is_flagged_on_every_digital_check(self):
        r = analyze_pdf(str(self.paths["tampered"]), stated_issue_date="2023-06-15")
        self.assertEqual(r["revisions"], 2)
        for indicator in ["incremental_updates", "mod_after_creation", "producer_editing_tool",
                          "metadata_inconsistent", "mod_date_after_issue"]:
            self.assertEqual(status(r, indicator), "present", indicator)
        self.assertEqual([h["Producer"] for h in r["info_history"]], ["SBTE CertGen 3.2", "iLovePDF"])
        self.assertEqual(r["info"]["Producer"], "iLovePDF")

    def test_expected_producer_mismatch_is_flagged(self):
        r = analyze_pdf(str(self.paths["genuine"]), expected_producer="NationalCertSystem")
        self.assertEqual(status(r, "producer_editing_tool"), "present")

    def test_on_demand_certificate_not_penalised_for_late_creation(self):
        path = str(self.paths["on_demand"])
        on_demand = analyze_pdf(path, stated_issue_date="2021-05-01", generated_on_demand=True)
        self.assertEqual(status(on_demand, "mod_date_after_issue"), "absent")
        naive = analyze_pdf(path, stated_issue_date="2021-05-01")
        self.assertEqual(status(naive, "mod_date_after_issue"), "present")

    def test_sha256_is_recorded_for_chain_of_custody(self):
        r = analyze_pdf(str(self.paths["genuine"]))
        self.assertEqual(len(r["sha256"]), 64)

    def test_linearized_file_counts_as_one_revision(self):
        path = Path(self.tmp.name) / "linearized.pdf"
        path.write_bytes(b"%PDF-1.7\n1 0 obj << /Linearized 1 >> endobj\n%%EOF\nrest\n%%EOF\n")
        self.assertEqual(analyze_pdf(str(path))["revisions"], 1)

    def test_non_pdf_is_rejected(self):
        path = Path(self.tmp.name) / "fake.pdf"
        path.write_bytes(b"GIF89a not a pdf")
        with self.assertRaises(ValueError):
            analyze_pdf(str(path))

    def test_missing_file_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            analyze_pdf("does_not_exist.pdf")


class TestParsing(unittest.TestCase):
    def test_pdf_date_timezone_converted_to_utc(self):
        self.assertEqual(parse_pdf_date("D:20230615100000+05'30'"),
                         datetime(2023, 6, 15, 4, 30, tzinfo=timezone.utc))

    def test_pdf_date_without_timezone(self):
        self.assertEqual(parse_pdf_date("D:2023061510"), datetime(2023, 6, 15, 10, tzinfo=timezone.utc))

    def test_utf16_hex_string(self):
        token = b"<FEFF00690030>"
        self.assertEqual(_decode_pdf_string(token), "i0")

    def test_escaped_literal_string(self):
        self.assertEqual(_decode_pdf_string(rb"(Board \(fictional\))"), "Board (fictional)")


if __name__ == "__main__":
    unittest.main()
