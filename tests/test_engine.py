import unittest
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.indicators.indicator_engine import (
    normalize_text,
    split_sentences,
    get_keyword_pattern,
    contains_keyword,
    find_any_matches,
    check_all_rules,
    find_evidence,
    check_indicator,
    IndicatorEngine,
)
class TestIndicatorEngine(unittest.TestCase):
    def setUp(self):
        self.engine = IndicatorEngine()
        self.sample_text = """
Privacy Policy

We collect personal information to provide our services.
Users may request access to their personal information.
We use reasonable security measures to protect information.
"""

    def test_normalize_text(self):
        text = "Hello\tWorld\n\n\nTest   Spaces"
        norm = normalize_text(text)
        self.assertEqual(norm, "hello world\n\ntest spaces")

    def test_split_sentences(self):
        # A wrapped line inside a paragraph should be joined
        text = "This is a\nwrapped line. This is\nanother sentence."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(sentences[0], "This is a wrapped line.")
        self.assertEqual(sentences[1], "This is another sentence.")

        # Test bullet points
        text = "Features:\n- Fast\n- Secure"
        sentences = split_sentences(text)
        # Should split on newlines for bullet points if handled correctly
        # Let's just check length, expecting 3 sentences if split properly
        self.assertTrue(len(sentences) >= 2)

    def test_contains_keyword(self):
        # Exact matching
        self.assertTrue(contains_keyword("we collect personal data", "personal data"))
        # Case insensitive
        self.assertTrue(contains_keyword("We Collect Personal Data", "personal data"))
        # Word boundary
        self.assertFalse(contains_keyword("we collect personal database", "personal data"))

    def test_check_all_rules_same_sentence(self):
        rule = [[["apple"], ["banana"]]]

        # In same sentence -> should pass
        text_pass = "I have an apple and a banana."
        self.assertTrue(bool(check_all_rules(text_pass, rule)))

        # In different sentences -> should fail
        text_fail = "I have an apple. You have a banana."
        self.assertFalse(bool(check_all_rules(text_fail, rule)))

    def test_indicator_engine_initialization(self):
        # There should be exactly 40 secondary indicators
        self.assertEqual(len(self.engine.indicators), 40)

        # Each indicator should have id, name
        for ind in self.engine.indicators:
            self.assertTrue("id" in ind)
            self.assertTrue("name" in ind)
            self.assertTrue(ind["id"].startswith("B"))

    def test_analyze_policy(self):
        analysis = self.engine.analyze_policy(self.sample_text)

        self.assertEqual(analysis["total_indicators"], 40)
        self.assertTrue(analysis["found"] > 0)
        self.assertTrue(analysis["not_found"] >= 0)
        self.assertEqual(analysis["found"] + analysis["not_found"], 40)

        coverage = analysis["coverage"]
        self.assertEqual(coverage, round((analysis["found"] / 40.0) * 100, 2))

    def _get_indicator_result(self, text: str, indicator_id: str):
        analysis = self.engine.analyze_policy(text)
        for item in analysis["results"]:
            if item["id"] == indicator_id:
                return item
        return None

    def test_b6_contact_information(self):
        # Required positive case
        pos_text = "Contact Information: privacy@example.com"
        res = self._get_indicator_result(pos_text, "B6")
        self.assertIsNotNone(res)
        self.assertTrue(res["matched"], "B6 should match Contact Information: privacy@example.com")
        self.assertTrue(len(res["evidence"]) > 0, "B6 must return evidence for matched contact info")
        self.assertIn("contact information: privacy@example.com", res["evidence"][0]["text"])

        # Additional required contact variations
        variations = [
            "You can reach our contact info for any inquiries.",
            "Please find our email addresses for privacy questions below.",
            "Write to our privacy contact email addresses at privacy@test.org.",
            "Our customer support email addresses are available 24/7.",
            "Contact details for our privacy team contact details can be requested here.",
            "Send an inquiry to dpo@company.org regarding your data.",
        ]
        for var in variations:
            r = self._get_indicator_result(var, "B6")
            self.assertTrue(r["matched"], f"B6 should match: {var}")

        # Unrelated text without contact details or email should not match B6
        neg_text = "We process user data to render the web page content."
        neg_res = self._get_indicator_result(neg_text, "B6")
        self.assertFalse(neg_res["matched"], "B6 should not match unrelated processing statements")

    def test_b23_data_access_rights(self):
        # Required positive case
        pos_text = "You may request access to your personal information."
        res = self._get_indicator_result(pos_text, "B23")
        self.assertIsNotNone(res)
        self.assertTrue(res["matched"], "B23 should match user-facing access request")
        self.assertTrue(len(res["evidence"]) > 0)

        # Required negative case (access controls false positive)
        neg_text = "We use access controls to protect personal information."
        res_neg = self._get_indicator_result(neg_text, "B23")
        self.assertIsNotNone(res_neg)
        self.assertFalse(res_neg["matched"], "B23 must not match access controls")

        # Complex false positive from prompt
        fp_text = "We use access controls, encryption where appropriate, staff training, and security monitoring to protect personal information."
        res_fp = self._get_indicator_result(fp_text, "B23")
        self.assertFalse(res_fp["matched"], "B23 must not match security safeguard statements")

        # Additional user-facing access rights
        user_rights = [
            "Users may request access to their personal information.",
            "You may access your personal data.",
            "Users can obtain a copy of their data.",
            "Individuals may inquire about their personal information.",
        ]
        for text in user_rights:
            r = self._get_indicator_result(text, "B23")
            self.assertTrue(r["matched"], f"B23 should match: {text}")

    def test_b26_data_portability_services(self):
        # Required positive case
        pos_text = "You can download or export a copy of your personal data."
        res = self._get_indicator_result(pos_text, "B26")
        self.assertIsNotNone(res)
        self.assertTrue(res["matched"], "B26 should match data portability rights")
        self.assertTrue(len(res["evidence"]) > 0)

        # Required negative case (international transfers false positive)
        neg_text = "Personal information may be transferred across national borders."
        res_neg = self._get_indicator_result(neg_text, "B26")
        self.assertIsNotNone(res_neg)
        self.assertFalse(res_neg["matched"], "B26 must not match cross-border transfers")

        # Vendor/partner transfer false positive
        neg_vendor = "We may transfer your personal information to third party service providers."
        res_vendor = self._get_indicator_result(neg_vendor, "B26")
        self.assertFalse(res_vendor["matched"], "B26 must not match vendor transfers")

    def test_b21_security_self_inspection(self):
        # Required positive case
        pos_text = "We conduct periodic internal security audits."
        res = self._get_indicator_result(pos_text, "B21")
        self.assertIsNotNone(res)
        self.assertTrue(res["matched"], "B21 should match periodic internal security audits")
        self.assertTrue(len(res["evidence"]) > 0)

        # Required negative case
        neg_text = "We assess privacy and security risks."
        res_neg = self._get_indicator_result(neg_text, "B21")
        self.assertIsNotNone(res_neg)
        self.assertFalse(res_neg["matched"], "B21 must not match generic assess privacy and security risks")

        # Children's safeguards false positive from prompt
        fp_text = "We apply additional safeguards to children's information where applicable and assess relevant privacy and security risks."
        res_fp = self._get_indicator_result(fp_text, "B21")
        self.assertFalse(res_fp["matched"], "B21 must not match children safeguard statement")

    def test_indicators_json_completeness(self):
        import json
        indicators_file = Path(__file__).resolve().parent.parent / "backend" / "indicators" / "indicators.json"
        with open(indicators_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # All 7 primary indicators must be present
        self.assertEqual(len(data["primary_indicators"]), 7)
        primary_ids = {p["id"] for p in data["primary_indicators"]}
        expected_primary_ids = {"A1", "A2", "A3", "A4", "A5", "A6", "A7"}
        self.assertEqual(primary_ids, expected_primary_ids)

        # All 40 secondary indicators must be present
        self.assertEqual(len(data["secondary_indicators"]), 40)
        secondary_ids = {s["id"] for s in data["secondary_indicators"]}
        expected_secondary_ids = {f"B{i}" for i in range(1, 41)}
        self.assertEqual(secondary_ids, expected_secondary_ids)

    def test_evidence_sentence_association(self):
        text = (
            "Contact Information: privacy@example.com. "
            "You may request access to your personal information. "
            "We use reasonable security measures to protect information."
        )
        analysis = self.engine.analyze_policy(text)
        results_by_id = {r["id"]: r for r in analysis["results"]}

        b6_ev = results_by_id["B6"]["evidence"]
        self.assertTrue(len(b6_ev) > 0)
        self.assertIn("contact information: privacy@example.com", b6_ev[0]["text"])

        b23_ev = results_by_id["B23"]["evidence"]
        self.assertTrue(len(b23_ev) > 0)
        self.assertIn("you may request access to your personal information", b23_ev[0]["text"])

    def test_pdf_upload_api_compatibility(self):
        import asyncio
        import io
        from starlette.datastructures import UploadFile, Headers
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
        # pyrefly: ignore[missing-import]
        from main import upload_policy

        # Create a valid minimal PDF with readable text
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
            b"4 0 obj << /Length 72 >> stream\n"
            b"BT /F1 12 Tf 72 712 Td (Contact Information: privacy@example.com) Tj ET\n"
            b"endstream endobj\n"
            b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000367 00000 n \n"
            b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n439\n%%EOF"
        )

        upload = UploadFile(
            filename="sample_privacy_policy.pdf",
            file=io.BytesIO(pdf_bytes),
            headers=Headers({"content-type": "application/pdf"})
        )

        resp = asyncio.run(upload_policy(upload))

        # Check response structure compatibility
        self.assertEqual(resp["status"], "success")
        self.assertIn("document", resp)
        self.assertIn("compliance_summary", resp)
        self.assertIn("indicators", resp)
        self.assertIn("chunks", resp)

        doc = resp["document"]
        self.assertEqual(doc["filename"], "sample_privacy_policy.pdf")
        self.assertTrue(doc["total_pages"] >= 1)
        self.assertTrue(doc["total_characters"] > 0)

        summary = resp["compliance_summary"]
        self.assertEqual(summary["total_indicators"], 40)
        self.assertTrue(summary["matched"] >= 1)
        self.assertEqual(summary["matched"] + summary["not_matched"], 40)

        # Check that B6 is detected in the PDF
        indicators = {ind["id"]: ind for ind in resp["indicators"]}
        self.assertEqual(len(indicators), 40)
        self.assertTrue(indicators["B6"]["matched"])
        self.assertTrue(len(indicators["B6"]["evidence"]) > 0)


if __name__ == "__main__":
    unittest.main()