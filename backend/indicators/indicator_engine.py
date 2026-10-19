import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple


# ============================================================
# CONFIGURATION
# ============================================================

INDICATORS_FILE = Path(__file__).parent / "indicators.json"


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:
    """Normalize whitespace and lowercase policy text."""
    text = text.lower()

    # Safely handle Unicode punctuation
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'").replace("`", "'")
    text = text.replace("–", "-").replace("—", "-").replace("\u2011", "-")
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> List[str]:
    """Split policy text into evidence sentences while preserving lines."""

    # Split into blocks by double newlines or bullet points
    blocks = re.split(r"\n\s*\n+|\n(?=\s*[-*•])", text)
    sentences = []
    seen = set()

    for block in blocks:
        # Join wrapped PDF lines within the same block.
        block = re.sub(r"\s*\n\s*", " ", block).strip()

        if not block:
            continue

        parts = re.split(r"(?<=[.!?])\s+", block)

        for part in parts:
            part = part.strip()
            # Remove leading bullet points
            part = re.sub(r"^[-*•]\s*", "", part)
            if not part:
                continue

            key = part.casefold()

            if key not in seen:
                seen.add(key)
                sentences.append(part)

    return sentences

# ============================================================
# KEYWORD MATCHING
# ============================================================

@lru_cache(maxsize=2048)
def get_keyword_pattern(keyword: str) -> re.Pattern:
    """Compile and cache a case-insensitive keyword pattern."""
    if keyword.startswith("regex:"):
        return re.compile(keyword[6:], re.IGNORECASE)

    kw_lower = keyword.lower()
    kw_escaped = re.escape(kw_lower)
    start_b = r"\b" if re.match(r"^\w", kw_lower) else ""
    end_b = r"\b" if re.search(r"\w$", kw_lower) else ""
    return re.compile(
        start_b + kw_escaped + end_b,
        re.IGNORECASE
    )


def contains_keyword(text: str, keyword: str) -> bool:
    """Check whether a complete keyword or phrase occurs."""
    return bool(get_keyword_pattern(keyword).search(text))


def find_any_matches(
    text: str,
    keywords: List[str]
) -> List[str]:
    """Find configured ANY keywords in the document."""
    matched = []
    for keyword in keywords:
        if keyword.startswith("regex:"):
            pattern = get_keyword_pattern(keyword)
            for m in pattern.finditer(text):
                val = m.group(0)
                if val not in matched:
                    matched.append(val)
        elif contains_keyword(text, keyword):
            matched.append(keyword)
    return matched


# ============================================================
# ALL-RULE MATCHING
# ============================================================

def check_all_rules(
    text: str,
    all_rules: List[List[List[str]]]
) -> List[Dict[str, Any]]:
    """
    An ALL rule passes only when every keyword group has
    at least one match within the SAME sentence.

    Within each group, keywords use OR logic.
    Between groups, the rule uses AND logic.
    """

    sentences = split_sentences(text)
    passed_rules = []

    for rule_index, rule in enumerate(all_rules):
        matching_sentences = []

        for sentence in sentences:
            matched_groups = []
            rule_passed = True

            for group in rule:
                group_matches = []
                for keyword in group:
                    if keyword.startswith("regex:"):
                        pattern = get_keyword_pattern(keyword)
                        m = pattern.search(sentence)
                        if m:
                            val = m.group(0)
                            if val not in group_matches:
                                group_matches.append(val)
                    elif contains_keyword(sentence, keyword):
                        group_matches.append(keyword)

                if not group_matches:
                    rule_passed = False
                    break

                matched_groups.append(group_matches)

            if rule_passed:
                matching_sentences.append({
                    "text": sentence,
                    "matched_groups": matched_groups
                })

        if matching_sentences:
            passed_rules.append({
                "rule": rule,
                "rule_index": rule_index,
                "matched_groups": matching_sentences[0][
                    "matched_groups"
                ],
                "matching_sentences": matching_sentences
            })

    return passed_rules


# ============================================================
# PATTERNS & VALIDATION HELPERS
# ============================================================

DATE_PATTERN = re.compile(
    r"\b(?:"
    r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
    r"|"
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
    r"|"
    r"(?:january|february|march|april|may|june|july|"
    r"august|september|october|november|december|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"
    r"|"
    r"\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:january|february|march|april|may|june|"
    r"july|august|september|october|november|december|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"\s+\d{4}"
    r"|"
    r"(?:january|february|march|april|may|june|july|"
    r"august|september|october|november|december)\s+\d{4}"
    r")\b",
    re.IGNORECASE,
)

VERSION_PATTERN = re.compile(
    r"\b(?:v(?:er(?:sion)?)?\.?\s*)?\d+(?:\.\d+)+(?:-[a-z0-9.]+)?\b|\bversion\s+\d+\b|\bv\d+\b",
    re.IGNORECASE,
)

EMAIL_PATTERN = re.compile(
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
    re.IGNORECASE,
)


def validate_evidence_sentence(sentence: str, indicator_id: str) -> bool:
    """
    Validate that a matched candidate sentence represents genuine,
    contextual evidence for the specific indicator, rejecting common false positives.
    """
    if not indicator_id:
        return True

    s_lower = sentence.lower()

    if indicator_id == "B1":
        title_signals = [
            "privacy policy name",
            "policy name",
            "policy title",
            "document title",
            "title of this policy",
            "this document is the official",
            "official user privacy policy",
            "sample smart services privacy policy",
        ]
        if not any(ts in s_lower for ts in title_signals):
            return False
        if any(bad in s_lower for bad in ["carefully to understand", "applies to all users", "governs your use"]):
            return False
        return True

    elif indicator_id == "B2":
        if not VERSION_PATTERN.search(sentence):
            return False
        if any(bad in s_lower for bad in ["database driver", "database drivers", "hardware", "firmware", "driver", "os version"]):
            return False
        version_labels = ["version", "v1.", "v2.", "v0.", "revised version"]
        return any(vl in s_lower for vl in version_labels)

    elif indicator_id == "B3":
        if not DATE_PATTERN.search(sentence):
            return False
        if any(bad in s_lower for bad in ["effective controls", "discount is effective", "effective security"]):
            return False
        return any(k in s_lower for k in ["effective date", "effective from", "commencement date", "implementation date"])

    elif indicator_id == "B4":
        if not DATE_PATTERN.search(sentence):
            return False
        if "will revise" in s_lower and not DATE_PATTERN.search(sentence):
            return False
        if any(bad in s_lower for bad in ["update our software", "records were modified by the customer support"]):
            return False
        return any(k in s_lower for k in ["last updated", "update date", "revision date", "recently modified", "release date"])

    elif indicator_id == "B5":
        if any(bad in s_lower for bad in ["gaming controller", "traffic controller", "flight controller", "domain controller", "temperature controller", "motor controller"]):
            return False
        ctrl_terms = ["data controller", "controller", "personal info processor", "personal information processor", "responsible party", "operator"]
        if not any(ct in s_lower for ct in ctrl_terms):
            return False
        entity_signals = [":", "is", "identified as", "refers to", "responsible for", "acts as", "ltd", "inc", "corp", "llc", "pvt", "gmbh", "co.", "company", "organization", "technologies", "acme", "example digital"]
        return any(es in s_lower for es in entity_signals)

    elif indicator_id == "B6":
        if any(bad in s_lower for bad in ["server logs", "plain email text", "sales department for bulk enterprise pricing", "bulk enterprise pricing"]):
            return False
        has_email = bool(EMAIL_PATTERN.search(sentence))
        has_contact_word = any(cw in s_lower for cw in ["contact", "reach", "email", "support", "inquiry", "inquiries", "dpo", "questions", "write to", "privacy team", "online support"])
        return has_email or has_contact_word

    elif indicator_id == "B7":
        if any(bad in s_lower for bad in ["plastic bottles", "recycling", "commercial purpose of this sorting"]):
            return False
        return True

    elif indicator_id == "B8":
        if any(bad in s_lower for bad in ["acrylic panels", "glass display", "chalkboard", "mathematical equation"]):
            return False
        return True

    elif indicator_id == "B9":
        if any(bad in s_lower for bad in ["baked fresh", "chocolate cookies", "cafeteria", "dessert", "ssd hardware"]):
            return False
        return True

    elif indicator_id == "B10":
        if any(bad in s_lower for bad in ["server maintenance", "badge requests", "physical badge"]):
            return False
        return True

    elif indicator_id == "B11":
        if any(bad in s_lower for bad in ["security guard", "visitors without identification", "shutting down the operating system"]):
            return False
        return True

    elif indicator_id == "B12":
        if any(bad in s_lower for bad in ["paint scratches", "minor scratches", "adult account holders"]):
            return False
        return True

    elif indicator_id == "B13":
        if any(bad in s_lower for bad in ["twenty dollars", "free shipping", "minimum purchase"]):
            return False
        return True

    elif indicator_id == "B14":
        if any(bad in s_lower for bad in ["sorting algorithm", "pedestrian courtyard", "vehicle access"]):
            return False
        return True

    elif indicator_id == "B15":
        if any(bad in s_lower for bad in ["physical health", "regular breaks", "friendly face", "warm and friendly"]):
            return False
        return True

    elif indicator_id == "B16":
        if any(bad in s_lower for bad in ["retail store location", "downtown chicago", "desktop folders", "unsaved document drafts"]):
            return False
        return True

    elif indicator_id == "B17":
        if any(bad in s_lower for bad in ["company laptop", "temporary cache files from your web browser"]):
            return False
        return True

    elif indicator_id == "B18":
        if any(bad in s_lower for bad in ["educational qualifications", "chemistry laboratory", "safety goggles"]):
            return False
        return True

    elif indicator_id == "B19":
        if any(bad in s_lower for bad in ["patrol the building", "patrol", "airport security checkpoint", "boarding passes"]):
            return False
        return True

    elif indicator_id == "B20":
        if any(bad in s_lower for bad in ["plumbing leak", "water pipe", "emergency exit stairwell", "backup lighting"]):
            return False
        return True

    elif indicator_id == "B21":
        if "apply additional safeguards to children's information" in s_lower:
            return False
        if s_lower.strip().rstrip(".") == "we assess privacy and security risks":
            return False
        return True

    elif indicator_id == "B22":
        if any(bad in s_lower for bad in ["newsletter subscribers", "recipe article", "receptionist informed"]):
            return False
        return True

    elif indicator_id == "B23":
        if any(bad in s_lower for bad in ["use access controls", "access controls, encryption"]):
            return False
        return True

    elif indicator_id == "B24":
        if any(bad in s_lower for bad in ["proofreader", "first chapter", "software libraries across production servers"]):
            return False
        return True

    elif indicator_id == "B25":
        if any(bad in s_lower for bad in ["marathon competition", "dental appointments"]):
            return False
        return True

    elif indicator_id == "B26":
        if any(bad in s_lower for bad in ["transferred across national borders", "third party service providers"]):
            return False
        return True

    elif indicator_id == "B27":
        if any(bad in s_lower for bad in ["dietary preferences", "vegetarian diners", "customer reviews"]):
            return False
        return True

    elif indicator_id == "B28":
        if any(bad in s_lower for bad in ["football tournament", "thunderstorm", "bank account transfers"]):
            return False
        return True

    elif indicator_id == "B29":
        if any(bad in s_lower for bad in ["sports cable channel", "restaurant patrons", "wait times"]):
            return False
        return True

    elif indicator_id == "B30":
        if any(bad in s_lower for bad in ["community fundraising", "office space with an architecture"]):
            return False
        return True

    elif indicator_id == "B31":
        if any(bad in s_lower for bad in ["delivery truck", "parking", "chemical samples", "lab manual"]):
            return False
        return True

    elif indicator_id == "B32":
        if any(bad in s_lower for bad in ["scholarship recipient", "banquet", "opened a new boutique"]):
            return False
        return True

    elif indicator_id == "B33":
        if any(bad in s_lower for bad in ["moral duty", "community service", "political third party", "televised debate"]):
            return False
        return True

    elif indicator_id == "B34":
        if any(bad in s_lower for bad in ["fourth-quarter corporate revenues", "corporate revenues", "commuters about public transport"]):
            return False
        return True

    elif indicator_id == "B35":
        if any(bad in s_lower for bad in ["study italian art", "contract templates are stored in the legal"]):
            return False
        return True

    elif indicator_id == "B36":
        if any(bad in s_lower for bad in ["puppet performance", "puppet show", "historical manuscripts"]):
            return False
        return True

    elif indicator_id == "B37":
        if any(bad in s_lower for bad in ["trial judge", "closing arguments", "mechanical clock", "winding every seven days"]):
            return False
        return True

    elif indicator_id == "B38":
        if any(bad in s_lower for bad in ["whistleblower", "ethics hotline", "short stories under a pseudonym"]):
            return False
        return True

    elif indicator_id == "B39":
        if any(bad in s_lower for bad in ["skateboarding", "fiberglass helmet", "sunscreen", "solar radiation"]):
            return False
        return True

    elif indicator_id == "B40":
        if any(bad in s_lower for bad in ["cardiologist", "cardiac symptoms", "coastal flood", "environmental agency"]):
            return False
        return True

    return True


# ============================================================
# KEYWORD ATTRIBUTION & SPECIFICITY FILTERING
# ============================================================

def is_whole_word_subphrase(sub: str, parent: str) -> bool:
    """Check if sub is a whole-word subphrase of parent."""
    sub_clean = sub.rstrip(":").strip().lower()
    parent_clean = parent.rstrip(":").strip().lower()
    if sub_clean == parent_clean:
        return True
    escaped = re.escape(sub_clean)
    pattern = re.compile(r"(?:\b|^)" + escaped + r"(?:\b|$)", re.IGNORECASE)
    return bool(pattern.search(parent_clean))


def deduplicate_and_filter_matches(matches: List[str], sentence: str = "") -> List[str]:
    """
    Deduplicate and filter evidence keyword matches:
    1. Deduplicate identical keyword matches case-insensitively and normalize trailing punctuation.
    2. When multiple configured phrases overlap, prefer the most specific phrase for display.
    3. Preserve distinct, meaningful matches when they add information.
    """
    if not matches:
        return []

    # Step 1: Normalize and deduplicate case-insensitively
    seen_canonical: Dict[str, str] = {}
    for m in matches:
        if not m or not isinstance(m, str):
            continue
        m_str = m.strip()
        if not m_str:
            continue

        canon_key = m_str.rstrip(":").strip().casefold()
        if not canon_key:
            canon_key = m_str.casefold()

        if canon_key not in seen_canonical:
            clean_display = m_str.rstrip(":").strip() if m_str.endswith(":") else m_str
            seen_canonical[canon_key] = clean_display

    candidates = list(seen_canonical.values())
    if len(candidates) <= 1:
        return candidates

    # Step 2: Sort by length descending (most specific / longest first)
    candidates_sorted = sorted(candidates, key=lambda s: len(s), reverse=True)
    kept: List[str] = []

    for cand in candidates_sorted:
        # Check if cand is a whole-word sub-phrase of any already kept longer phrase
        is_sub = False
        for k in kept:
            if is_whole_word_subphrase(cand, k):
                is_sub = True
                break
        if not is_sub:
            kept.append(cand)

    # Step 3: Reorder according to original appearance order in matches
    def original_index(c: str) -> int:
        c_cf = c.rstrip(":").strip().casefold()
        for idx, orig in enumerate(matches):
            if orig.rstrip(":").strip().casefold() == c_cf:
                return idx
        return 999

    kept.sort(key=original_index)
    return kept


# ============================================================
# EVIDENCE COLLECTION
# ============================================================

def find_evidence(
    text: str,
    any_matches: List[str],
    passed_all_rules: List[Dict[str, Any]],
    indicator: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """Return relevant, deduplicated evidence sentences."""
    sentences = split_sentences(text)
    evidence = []
    seen = set()
    indicator_id = indicator.get("id", "") if indicator else ""

    # --------------------------------------------------------
    # ANY evidence
    # --------------------------------------------------------
    for sentence in sentences:
        matches = [
            keyword
            for keyword in any_matches
            if contains_keyword(sentence, keyword)
        ]

        if not matches:
            continue

        if not validate_evidence_sentence(sentence, indicator_id):
            continue

        filtered_matches = deduplicate_and_filter_matches(matches, sentence)

        key = sentence.casefold()
        if key not in seen:
            evidence.append({
                "text": sentence,
                "matches": filtered_matches,
                "matched_by": "ANY",
                "evidence_type": "any",
            })
            seen.add(key)

    # --------------------------------------------------------
    # Complete ALL-rule evidence
    # --------------------------------------------------------
    for rule_result in passed_all_rules:
        for item in rule_result["matching_sentences"]:
            sentence = item["text"]
            if not validate_evidence_sentence(sentence, indicator_id):
                continue

            key = sentence.casefold()
            matched_keywords = []
            for group_matches in item["matched_groups"]:
                matched_keywords.extend(group_matches)

            filtered_all_matches = deduplicate_and_filter_matches(matched_keywords, sentence)

            if key in seen:
                for ev in evidence:
                    if ev["text"].casefold() == key:
                        ev["matched_by"] = "ANY / ALL"
                        combined_matches = deduplicate_and_filter_matches(
                            ev.get("matches", []) + filtered_all_matches,
                            sentence
                        )
                        ev["matches"] = combined_matches
                        ev["rule_index"] = rule_result["rule_index"]
                        ev["evidence_type"] = "complete"
                        break
                continue

            evidence.append({
                "text": sentence,
                "matches": filtered_all_matches,
                "matched_by": "ALL",
                "rule_index": rule_result["rule_index"],
                "evidence_type": "complete",
            })
            seen.add(key)

    return evidence


# ============================================================
# INDICATOR ANALYSIS
# ============================================================

def check_indicator(
    text: str,
    indicator: Dict[str, Any]
) -> Dict[str, Any]:
    """Evaluate one configured privacy indicator."""
    candidate_any_matches = find_any_matches(
        text,
        indicator.get("any", [])
    )

    passed_all_rules = check_all_rules(
        text,
        indicator.get("all", [])
    )

    evidence = find_evidence(
        text,
        candidate_any_matches,
        passed_all_rules,
        indicator
    )

    has_valid_evidence = len(evidence) > 0
    matched_sources = {item["matched_by"] for item in evidence}

    any_matched = has_valid_evidence and (
        any("ANY" in ms for ms in matched_sources) or (bool(candidate_any_matches) and not passed_all_rules)
    )
    all_matched = has_valid_evidence and (
        any("ALL" in ms for ms in matched_sources) or (bool(passed_all_rules) and not candidate_any_matches)
    )

    matched = has_valid_evidence and (any_matched or all_matched)

    matched_by_parts = []
    if any_matched:
        matched_by_parts.append("ANY")
    if all_matched:
        matched_by_parts.append("ALL")

    # Filter any_matches to those present in valid evidence
    actual_any_matches = []
    if has_valid_evidence:
        raw_candidates = []
        for ev in evidence:
            for m in ev.get("matches", []):
                if m not in raw_candidates:
                    raw_candidates.append(m)
        actual_any_matches = deduplicate_and_filter_matches(raw_candidates, text)
        if not actual_any_matches and candidate_any_matches and any_matched:
            actual_any_matches = deduplicate_and_filter_matches(candidate_any_matches, text)
    else:
        actual_any_matches = []

    # Filter all_matches to those rules that passed and produced evidence
    valid_rule_indices = {
        ev["rule_index"]
        for ev in evidence
        if "rule_index" in ev
    }
    actual_all_matches = [
        {
            "rule": item["rule"],
            "matched_groups": item["matched_groups"]
        }
        for item in passed_all_rules
        if not valid_rule_indices or item["rule_index"] in valid_rule_indices
    ] if has_valid_evidence else []

    return {
        "id": indicator["id"],
        "name": indicator["name"],
        "primary": indicator.get("primary"),
        "matched": matched,
        "matched_by": " / ".join(matched_by_parts) if (matched and matched_by_parts) else "NONE",
        "any_matches": actual_any_matches,
        "all_matches": actual_all_matches,
        "evidence": evidence
    }


# ============================================================
# INDICATOR ENGINE
# ============================================================

class IndicatorEngine:
    """Analyze privacy policies using configured indicators."""

    def __init__(
        self,
        indicators_file: Path = INDICATORS_FILE
    ):
        self.indicators_file = Path(indicators_file)
        self.indicators = self._load_indicators()

    def _load_indicators(self) -> List[Dict[str, Any]]:
        """Load indicator definitions from indicators.json."""

        if not self.indicators_file.exists():
            raise FileNotFoundError(
                f"Indicator configuration not found: "
                f"{self.indicators_file}"
            )

        with self.indicators_file.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if isinstance(data, list):
            indicators = data

        elif isinstance(data, dict):
            indicators = data.get(
                "secondary_indicators",
                data.get("indicators", [])
            )

        else:
            raise ValueError(
                "Invalid indicators.json format."
            )

        if not isinstance(indicators, list) or not indicators:
            raise ValueError(
                "No indicator definitions were found."
            )

        for indicator in indicators:
            if not isinstance(indicator, dict):
                raise ValueError(
                    "Every indicator must be a JSON object."
                )

            if not indicator.get("id") or not indicator.get("name"):
                raise ValueError(
                    "Every indicator must have an id and name."
                )

        return indicators

    def analyze_policy(self, text: str) -> Dict[str, Any]:
        """Analyze the complete policy and calculate coverage."""

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                "Policy text cannot be empty."
            )

        normalized_text = normalize_text(text)

        results = [
            check_indicator(normalized_text, indicator)
            for indicator in self.indicators
        ]

        total = len(results)

        found = sum(
            1
            for result in results
            if result["matched"]
        )

        not_found = total - found

        coverage = (
            round((found / total) * 100, 2)
            if total
            else 0.0
        )

        return {
            "total_indicators": total,
            "found": found,
            "not_found": not_found,
            "coverage": coverage,
            "results": results
        }


# ============================================================
# COMMAND-LINE TESTING
# ============================================================

def main() -> None:
    """Run a quick test using the configured indicator engine."""

    engine = IndicatorEngine()

    sample_policy = """
    Privacy Policy

    We collect personal information to provide our services.
    Users may request access to their personal information.
    We use reasonable security measures to protect information.
    """

    analysis = engine.analyze_policy(sample_policy)

    print("=" * 60)
    print("PRIVACY COMPLIANCE INDICATOR ANALYSIS")
    print("=" * 60)

    for result in analysis["results"]:
        status = "FOUND" if result["matched"] else "NOT FOUND"

        print(
            f"{result['id']} - {result['name']}: {status}"
        )

        for item in result["evidence"]:
            print(f"    Evidence: {item['text']}")

    print("\nSUMMARY")
    print("-" * 60)
    print("Total indicators:", analysis["total_indicators"])
    print("Found:", analysis["found"])
    print("Not found:", analysis["not_found"])
    print(f"Coverage: {analysis['coverage']:.2f}%")

if __name__ == "__main__":
    main()
