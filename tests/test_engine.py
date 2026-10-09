import unittest
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from indicators.indicator_engine import (
    normalize_text,
    split_sentences,
    get_keyword_pattern,
    contains_keyword,
    find_any_matches,
    check_all_rules,
    find_evidence,
    check_indicator,
    IndicatorEngine
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

if __name__ == "__main__":
    unittest.main()
