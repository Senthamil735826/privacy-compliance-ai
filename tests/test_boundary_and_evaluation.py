import pytest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.indicators.indicator_engine import IndicatorEngine, normalize_text, split_sentences
from backend.ingestion.pdf_parser import extract_text_from_pdf
from backend.ingestion.cleaner import clean_text

engine = IndicatorEngine()


# ============================================================================
# BOUNDARY TESTS
# ============================================================================

def test_case_insensitivity():
    """Verify that indicators match regardless of uppercase, title case, or lowercase."""
    text_upper = "BASIC INFORMATION - PRIVACY POLICY NAME: SMART IOT SERVICES. EFFECTIVE DATE: JANUARY 1, 2026."
    res = engine.analyze_policy(text_upper)
    matched = {r["id"]: r for r in res["results"]}
    assert matched["B1"]["matched"] is True
    assert matched["B3"]["matched"] is True


def test_punctuation_variations():
    """Verify indicators match with various punctuation styles."""
    text = "Privacy Policy Name - Smart IoT Services; Effective Date - January 1, 2026! Contact Info: privacy@test.org."
    res = engine.analyze_policy(text)
    matched = {r["id"]: r for r in res["results"]}
    assert matched["B1"]["matched"] is True
    assert matched["B3"]["matched"] is True
    assert matched["B6"]["matched"] is True


def test_date_format_variations():
    """Test standard date formats: ISO, US, UK, and text formats."""
    dates = [
        "Effective Date: 2026-01-01",
        "Effective Date: 01/15/2026",
        "Effective Date: January 1, 2026",
        "Effective Date: 15 August 2026",
        "Effective Date: September 2026"
    ]
    for d in dates:
        res = engine.analyze_policy(d)
        matched = {r["id"]: r for r in res["results"]}
        assert matched["B3"]["matched"] is True, f"Failed to match date format in: {d}"
        assert len(matched["B3"]["evidence"]) > 0


def test_singular_and_plural_variations():
    """Verify singular and plural terms are matched properly."""
    text_singular = "Our website uses a cookie to remember user preferences. A minor requires parental consent."
    res_sing = engine.analyze_policy(text_singular)
    matched_sing = {r["id"]: r for r in res_sing["results"]}
    assert matched_sing["B9"]["matched"] is True
    assert matched_sing["B12"]["matched"] is True

    text_plural = "Our website uses cookies to remember user preferences. Minors require parental consent."
    res_plur = engine.analyze_policy(text_plural)
    matched_plur = {r["id"]: r for r in res_plur["results"]}
    assert matched_plur["B9"]["matched"] is True
    assert matched_plur["B12"]["matched"] is True


def test_repeated_sentences_deduplication():
    """Verify evidence does not contain duplicate sentences when repeated in the text."""
    repeated_text = (
        "Contact Information: privacy@example.com.\n\n"
        "Contact Information: privacy@example.com.\n\n"
        "Contact Information: privacy@example.com."
    )
    res = engine.analyze_policy(repeated_text)
    matched = {r["id"]: r for r in res["results"]}
    b6_evidence = matched["B6"]["evidence"]
    assert len(b6_evidence) == 1
    assert "privacy@example.com" in b6_evidence[0]["text"]


def test_empty_and_whitespace_documents():
    """Verify empty or whitespace-only documents raise a clear ValueError."""
    with pytest.raises(ValueError, match="Policy text cannot be empty"):
        engine.analyze_policy("")

    with pytest.raises(ValueError, match="Policy text cannot be empty"):
        engine.analyze_policy("   \n\t   ")


def test_long_policy_performance():
    """Verify engine handles long documents deterministically and quickly."""
    base_paragraph = (
        "We collect personal information for the purpose of providing our services. "
        "Users may request access to their personal information. "
        "We use reasonable security measures to protect information. "
        "You may cancel your account at any time. "
    )
    long_doc = base_paragraph * 200  # ~800 sentences
    res = engine.analyze_policy(long_doc)
    assert res["total_indicators"] == 40
    assert res["found"] >= 4
    # Ensure evidence is deduplicated
    for r in res["results"]:
        ev_texts = [e["text"] for e in r["evidence"]]
        assert len(ev_texts) == len(set(ev_texts))


# ============================================================================
# SUMMARY CONSISTENCY TESTS
# ============================================================================

def test_summary_and_category_counts():
    """Verify indicator counts, categories, and totals match the specification."""
    indicators = engine.indicators
    assert len(indicators) == 40

    primary_map = {
        "A1": ["B1", "B2", "B3", "B4", "B5", "B6"],
        "A2": ["B7", "B8", "B9", "B10", "B11", "B12"],
        "A3": ["B13", "B14", "B15"],
        "A4": ["B16", "B17", "B18", "B19", "B20", "B21", "B22"],
        "A5": ["B23", "B24", "B25", "B26", "B27", "B28", "B29"],
        "A6": ["B30", "B31", "B32", "B33", "B34", "B35"],
        "A7": ["B36", "B37", "B38", "B39", "B40"],
    }

    # Verify every secondary indicator has a unique ID and maps to expected primary category
    seen_ids = set()
    for ind in indicators:
        i_id = ind["id"]
        assert i_id not in seen_ids, f"Duplicate indicator ID: {i_id}"
        seen_ids.add(i_id)

        primary = ind["primary"]
        assert primary in primary_map, f"Invalid primary category: {primary}"
        assert i_id in primary_map[primary], f"{i_id} not in expected category {primary}"

    assert seen_ids == {f"B{i}" for i in range(1, 41)}


def test_repeated_analysis_determinism():
    """Verify that running analysis repeatedly on the same text returns deterministic results."""
    sample = (
        "Privacy Policy Name: Acme IoT Policy.\n"
        "Effective Date: January 1, 2026.\n"
        "Data Controller: Acme Corp.\n"
        "We use cookies to enhance user experience.\n"
    )
    res1 = engine.analyze_policy(sample)
    res2 = engine.analyze_policy(sample)

    assert res1["found"] == res2["found"]
    assert res1["not_found"] == res2["not_found"]
    assert res1["coverage"] == res2["coverage"]
    for r1, r2 in zip(res1["results"], res2["results"]):
        assert r1["id"] == r2["id"]
        assert r1["matched"] == r2["matched"]
        assert len(r1["evidence"]) == len(r2["evidence"])


# ============================================================================
# SAMPLE PDF END-TO-END TEST
# ============================================================================

def test_sample_pdf_end_to_end():
    """Verify the sample PDF analyzes properly with relevant evidence and expected indicator detections."""
    pdf_path = PROJECT_ROOT / "dataset" / "sample_privacy_policy.pdf"
    assert pdf_path.exists(), f"Sample PDF missing at {pdf_path}"

    extracted = extract_text_from_pdf(str(pdf_path))
    assert extracted["total_pages"] >= 1
    assert extracted["total_characters"] > 0

    cleaned = clean_text(extracted["text"])
    analysis = engine.analyze_policy(cleaned)

    assert analysis["total_indicators"] == 40
    assert analysis["found"] + analysis["not_found"] == 40
    assert analysis["coverage"] > 0.0

    # Key indicators that are explicitly present in the sample policy
    expected_matches = [
        "B1",   # Sample Smart Services Privacy Policy
        "B2",   # Version Number: 1.0
        "B3",   # Effective Date: January 1, 2026
        "B4",   # Last Updated: September 1, 2026
        "B5",   # Data Controller: Example Digital Services Pvt. Ltd.
        "B6",   # Contact Information: privacy@example.com
        "B7",   # purposes for collection
        "B8",   # explain the categories of personal data collected
        "B9",   # cookies and similar technologies
        "B10",  # provide notice and request consent
        "B11",  # opt out of optional analytics
        "B12",  # children's personal information without appropriate authorization
        "B13",  # reasonably necessary
        "B14",  # unrelated purposes without providing notice
        "B16",  # stored on systems operated by our company and contracted hosting providers
        "B17",  # retain personal information only for as long as necessary
        "B19",  # access controls, encryption where appropriate
        "B21",  # periodically review security practices
        "B22",  # notify affected individuals and relevant authorities
        "B23",  # request access to or correction
        "B24",  # request deletion
        "B25",  # withdraw consent
        "B27",  # privacy settings available in your account
        "B28",  # close your account
        "B29",  # submit a request or complaint
        "B30",  # share personal information with service providers that process information on our behalf
        "B31",  # use it only for authorized purposes
        "B32",  # identify categories of recipients
        "B33",  # require service providers to protect the information
        "B35",  # transferred across national borders
        "B36",  # collect children's personal information
        "B37",  # not directed to children under 13
        "B38",  # take steps to delete it
        "B39",  # additional safeguards to children's information
        "B40",  # assess relevant privacy and security risks
    ]

    results_by_id = {r["id"]: r for r in analysis["results"]}

    for ind_id in expected_matches:
        ind_res = results_by_id[ind_id]
        assert ind_res["matched"] is True, f"Indicator {ind_id} ({ind_res['name']}) should be matched in sample PDF"
        assert len(ind_res["evidence"]) > 0, f"Indicator {ind_id} must have non-empty evidence"

    # Indicators NOT present in the fictional sample PDF must NOT be marked matched (no false positives)
    not_present = [
        "B15",  # Special Purpose Usage (biometrics / health data - not in sample)
        "B18",  # Safety Qualification (ISO 27001 / SOC 2 certification - not in sample)
        "B20",  # Emergency Handling of Leaks (emergency contingency leak plan - not in sample)
        "B26",  # Data Portability Services (machine readable export/download - not in sample)
        "B34",  # Public Disclosure of Risks (external public disclosure - not in sample)
    ]
    for ind_id in not_present:
        ind_res = results_by_id[ind_id]
        assert ind_res["matched"] is False, f"Indicator {ind_id} ({ind_res['name']}) should NOT be matched in sample PDF"
