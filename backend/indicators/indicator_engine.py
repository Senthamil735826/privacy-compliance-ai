import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List


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
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("\xa0", " ").replace("\u200b", "")

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
    return re.compile(
        r"\b" + re.escape(keyword.lower()) + r"\b",
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
    return [
        keyword
        for keyword in keywords
        if contains_keyword(text, keyword)
    ]


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
                group_matches = [
                    keyword
                    for keyword in group
                    if contains_keyword(sentence, keyword)
                ]

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
# EVIDENCE COLLECTION
# ============================================================

def find_evidence(
    text: str,
    any_matches: List[str],
    passed_all_rules: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Return relevant evidence without duplicate sentences."""

    sentences = split_sentences(text)
    evidence = []
    seen = set()

    # --------------------------------------------------------
    # ANY evidence
    # --------------------------------------------------------

    for sentence in sentences:
        matches = [
            keyword
            for keyword in any_matches
            if contains_keyword(sentence, keyword)
        ]

        if matches:
            key = sentence.casefold()

            if key not in seen:
                evidence.append({
                    "text": sentence,
                    "matches": matches,
                    "matched_by": "ANY",
                    "evidence_type": "any"
                })
                seen.add(key)

    # --------------------------------------------------------
    # Complete ALL-rule evidence
    # --------------------------------------------------------

    for rule_result in passed_all_rules:
        for item in rule_result["matching_sentences"]:
            sentence = item["text"]
            key = sentence.casefold()

            if key in seen:
                continue

            matched_keywords = []

            for group_matches in item["matched_groups"]:
                matched_keywords.extend(group_matches)

            evidence.append({
                "text": sentence,
                "matches": list(dict.fromkeys(matched_keywords)),
                "matched_by": "ALL",
                "rule_index": rule_result["rule_index"],
                "evidence_type": "complete"
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

    any_matches = find_any_matches(
        text,
        indicator.get("any", [])
    )

    passed_all_rules = check_all_rules(
        text,
        indicator.get("all", [])
    )

    evidence = find_evidence(
        text,
        any_matches,
        passed_all_rules
    )

    any_matched = bool(any_matches)
    all_matched = bool(passed_all_rules)

    matched_by = []

    if any_matched:
        matched_by.append("ANY")

    if all_matched:
        matched_by.append("ALL")

    return {
        "id": indicator["id"],
        "name": indicator["name"],
        "primary": indicator.get("primary"),
        "matched": any_matched or all_matched,
        "matched_by": " / ".join(matched_by) if matched_by else "NONE",
        "any_matches": any_matches,
        "all_matches": [
            {
                "rule": item["rule"],
                "matched_groups": item["matched_groups"]
            }
            for item in passed_all_rules
        ],
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
