from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.indicators.indicator_engine import (
    deduplicate_and_filter_matches,
    IndicatorEngine,
)

engine = IndicatorEngine()


def test_case_differences_deduplication():
    """Requirement 2 & 8: Deduplicate identical keyword matches case-insensitively."""
    matches = ["Personal Data", "personal data", "PERSONAL DATA"]
    sentence = "We collect Personal Data to provide the service."
    result = deduplicate_and_filter_matches(matches, sentence)

    assert len(result) == 1
    assert result[0].casefold() == "personal data"


def test_duplicate_and_trailing_punctuation_matches():
    """Requirement 2 & 8: Deduplicate identical matches and colon variants."""
    matches = [
        "Privacy Policy Name:",
        "Privacy Policy Name",
        "privacy policy name",
        "privacy policy name:",
    ]
    sentence = "Privacy Policy Name: Acme IoT Application Policy."
    result = deduplicate_and_filter_matches(matches, sentence)

    assert len(result) == 1
    assert result[0] == "Privacy Policy Name"


def test_overlapping_phrases_prefer_most_specific():
    """Requirement 3 & 8: When multiple configured phrases overlap, prefer the most specific phrase."""
    matches = [
        "Privacy Policy Name:",
        "Policy Name:",
        "Privacy Policy Name",
        "Policy Name",
        "privacy policy name",
        "policy name",
        "privacy policy",
        "policy",
    ]
    sentence = "Privacy Policy Name: Sample Smart Services Privacy Policy."
    result = deduplicate_and_filter_matches(matches, sentence)

    # Shorter nested phrases like "policy", "policy name", "privacy policy" must be eliminated
    result_lower = [r.lower() for r in result]
    assert "policy" not in result_lower
    assert "policy name" not in result_lower
    assert "privacy policy" not in result_lower
    assert any("privacy policy name" in r for r in result_lower)


def test_distinct_non_overlapping_matches_preserved():
    """Requirement 4 & 8: Preserve distinct, meaningful matches when they add information."""
    matches = ["request access", "personal data", "obtain a copy"]
    sentence = "Users have the right to request access to their personal data and obtain a copy."
    result = deduplicate_and_filter_matches(matches, sentence)

    assert len(result) == 3
    assert set(result) == {"request access", "personal data", "obtain a copy"}


def test_integrated_b1_evidence_keyword_attribution():
    """Verify B1 evidence keyword attribution on actual policy text."""
    sample = "Privacy Policy Name: Sample Smart Services Privacy Policy."
    res = engine.analyze_policy(sample)
    b1 = next(r for r in res["results"] if r["id"] == "B1")

    assert b1["matched"] is True
    assert len(b1["evidence"]) > 0

    ev = b1["evidence"][0]
    # Check that original sentence text is NOT modified (Requirement 5)
    assert "privacy policy name: sample smart services privacy policy" in ev["text"]

    matches = ev["matches"]
    matches_lower = [m.lower() for m in matches]

    # Redundant sub-phrases should not be present
    assert "policy" not in matches_lower
    assert "policy name" not in matches_lower
    assert "privacy policy" not in matches_lower

    # Most specific phrases are preserved
    assert any("privacy policy name" in m for m in matches_lower)
    assert any("smart services privacy policy" in m for m in matches_lower)


def test_integrated_cookies_keyword_attribution():
    """Verify B9 cookie evidence preserves distinct tags while dropping nested redundant words."""
    sample = "You can change cookie preferences or opt out of optional analytics through the privacy settings."
    res = engine.analyze_policy(sample)
    b9 = next(r for r in res["results"] if r["id"] == "B9")

    assert b9["matched"] is True
    ev = b9["evidence"][0]
    matches_lower = [m.lower() for m in ev["matches"]]

    # "cookie preferences" is more specific than "cookie" and "preferences" within that phrase
    if "cookie preferences" in matches_lower:
        assert "cookie" not in matches_lower
        assert "preferences" not in matches_lower
