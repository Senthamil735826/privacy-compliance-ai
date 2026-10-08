import json
import re
from pathlib import Path


# ============================================================
# PATH TO indicators.json
# ============================================================

INDICATORS_FILE = Path(__file__).parent / "indicators.json"


# ============================================================
# LOAD INDICATORS
# ============================================================

def load_indicators():
    with open(INDICATORS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):
    """
    Normalize policy text before analysis.
    """

    text = text.lower()

    # Normalize spaces inside lines
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()


# ============================================================
# SPLIT TEXT INTO SENTENCES
# ============================================================

def split_sentences(text):
    """
    Split policy text into readable evidence units.

    First splits by paragraphs, replaces internal line breaks
    with spaces, and splits by sentence-ending punctuation.
    """

    paragraphs = re.split(r"\n\n+", text)

    sentences = []

    for para in paragraphs:

        # Join broken lines within the same paragraph
        para = para.replace("\n", " ")

        parts = re.split(
            r"(?<=[.!?])\s+",
            para
        )

        for part in parts:

            part = part.strip()

            if part and part not in sentences:
                sentences.append(part)

    return sentences


# ============================================================
# CHECK KEYWORD MATCH
# ============================================================

def contains_keyword(text, keyword):
    """
    Check if a keyword exists in text using word boundaries.
    """
    pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
    return bool(re.search(pattern, text))


# ============================================================
# CHECK ANY KEYWORDS
# ============================================================

def find_any_matches(text, keywords):
    """
    Return keywords where at least one keyword
    appears anywhere in the text.
    """

    matches = []

    for keyword in keywords:

        if contains_keyword(text, keyword):
            matches.append(keyword)

    return matches


# ============================================================
# CHECK ALL RULES
# ============================================================

def check_all_rules(text, all_rules):
    """
    Check compound ALL rules.

    Structure:

    all:
    [
        [
            ["keyword1", "keyword2"],
            ["keyword3", "keyword4"]
        ]
    ]

    Meaning:

        (keyword1 OR keyword2)
        AND
        (keyword3 OR keyword4)

    Multiple outer rules are treated as alternatives.
    """

    passed_rules = []

    for rule in all_rules:

        rule_passed = True

        matched_groups = []

        for group in rule:

            group_matches = []

            for keyword in group:

                if contains_keyword(text, keyword):
                    group_matches.append(keyword)

            # Every group must have at least
            # one matching keyword.
            if not group_matches:

                rule_passed = False

                break

            matched_groups.append(group_matches)

        if rule_passed:

            passed_rules.append({
                "rule": rule,
                "matched_groups": matched_groups
            })

    return passed_rules


# ============================================================
# FIND EVIDENCE
# ============================================================

def find_evidence(text, any_matches, passed_all_rules):
    """
    Find sentences containing the successfully matched keywords.

    This provides human-readable evidence showing
    why an indicator was detected.
    """

    sentences = split_sentences(text)

    evidence = []

    successful_keywords = set(any_matches)
    for rule_res in passed_all_rules:
        for group in rule_res["matched_groups"]:
            for keyword in group:
                successful_keywords.add(keyword)

    if not successful_keywords:
        return []

    for sentence in sentences:

        sentence_lower = sentence.lower()

        matched_in_sentence = []

        for keyword in successful_keywords:
            if contains_keyword(sentence_lower, keyword):
                matched_in_sentence.append(keyword)

        if matched_in_sentence:
            evidence.append({
                "text": sentence,
                "matches": matched_in_sentence
            })

    return evidence


# ============================================================
# CHECK ONE INDICATOR
# ============================================================

def check_indicator(text, indicator):

    # --------------------------------------------------------
    # ANY matching
    # --------------------------------------------------------

    any_matches = find_any_matches(
        text,
        indicator.get("any", [])
    )

    # --------------------------------------------------------
    # ALL matching
    # --------------------------------------------------------

    all_rules = indicator.get("all", [])

    passed_all_rules = check_all_rules(
        text,
        all_rules
    )

    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    evidence = find_evidence(
        text,
        any_matches,
        passed_all_rules
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    any_matched = len(any_matches) > 0

    all_matched = len(passed_all_rules) > 0

    matched = any_matched or all_matched

    matched_by_list = []
    if any_matched:
        matched_by_list.append("ANY")
    if all_matched:
        matched_by_list.append("ALL")

    return {
        "id": indicator["id"],
        "name": indicator["name"],
        "primary": indicator["primary"],
        "matched": matched,
        "matched_by": " / ".join(matched_by_list) if matched_by_list else "NONE",
        "any_matches": any_matches,
        "all_matches": passed_all_rules,
        "evidence": evidence
    }


# ============================================================
# ANALYZE POLICY
# ============================================================

def analyze_policy(text):

    # Normalize input
    text = normalize_text(text)

    # Load indicator definitions
    data = load_indicators()

    results = []

    # Analyze every secondary indicator
    for indicator in data["secondary_indicators"]:

        result = check_indicator(
            text,
            indicator
        )

        results.append(result)

    return results


# ============================================================
# PRINT RESULT
# ============================================================

def print_results(results):

    found_count = 0
    total_count = len(results)

    print()
    print("=" * 70)
    print("PRIVACY COMPLIANCE INDICATOR ANALYSIS")
    print("=" * 70)

    for result in results:

        status = "FOUND" if result["matched"] else "NOT FOUND"

        if result["matched"]:
            found_count += 1

        print()
        print(
            f"{result['id']} - "
            f"{result['name']} : "
            f"{status}"
        )

        if result["matched"]:
            print(f"   Matched by: {result['matched_by']}")

        # ----------------------------------------------------
        # ANY Matches
        # ----------------------------------------------------

        if result["any_matches"]:

            print(
                "   ANY Matches:",
                ", ".join(result["any_matches"])
            )

        # ----------------------------------------------------
        # ALL Rules
        # ----------------------------------------------------

        if result["all_matches"]:

            print()
            print("   ALL Rules Passed:")

            for rule_result in result["all_matches"]:

                print("      - Rule matched:")

                for group in rule_result["matched_groups"]:

                    print(
                        "         OR group:",
                        ", ".join(group)
                    )

        # ----------------------------------------------------
        # Evidence
        # ----------------------------------------------------

        if result["evidence"]:

            print()
            print("   Evidence:")

            for item in result["evidence"]:

                print(
                    "      -",
                    item["text"]
                )

    # ========================================================
    # SUMMARY
    # ========================================================

    not_found_count = total_count - found_count

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"Total Indicators : {total_count}"
    )

    print(
        f"Found            : {found_count}"
    )

    print(
        f"Not Found        : {not_found_count}"
    )

    if total_count > 0:

        percentage = (
            found_count / total_count
        ) * 100

        print(
            f"Coverage         : {percentage:.2f}%"
        )

    print("=" * 70)


# ============================================================
# TEST POLICY
# ============================================================

if __name__ == "__main__":

    sample_policy = """

Privacy Policy

Version number: 2.0

Effective date: January 1, 2026

Last updated: September 1, 2026

Data controller: ABC Technologies Pvt Ltd

Contact information:
Customer service email: support@example.com


Purpose of collection:

We collect and process personal information and data
for the purpose of providing our services.

The company clearly explains how personal information
is collected.

We are open and transparent.

We use cookies, browser cache, local storage,
log files, web beacons and SDK technologies.

We obtain user consent before collecting personal information.

Explicit consent may be required.

Users can refuse collection and opt-out.

Users can turn off permission and cancel authorization.

We provide special protection for minors.

We apply appropriate protection measures for minors.

We only collect the minimum necessary personal data.

Personal data is used only for the declared purpose.

Sensitive personal information such as biometric data,
face information and health data receives additional protection.

Separate consent may be required for sensitive information.


Personal data is stored on secure servers located in India.

We retain personal information only for the required retention period
and delete personal information after the retention period expires.

Personal data is securely deleted according to our deletion mechanism.

Our organization maintains ISO27001 security certification
and follows applicable security qualification requirements.

We use technical security measures to protect personal data.

We have an emergency response process for security incidents
and data leaks.

We conduct regular security risk assessments and internal audits.

Users will be notified of any security incident or data leak.


Users have the right to access their personal information
and request a copy of their personal data.

Users may correct or update their personal information
and request deletion of their personal data.

Users may withdraw or revoke their consent at any time.

Users can export and transfer their personal data
and receive a copy of their information.

Users can manage their privacy preferences and permission settings.

Recommendation and push settings can also be toggled.

Users may cancel their account and delete their account data.

Users can submit complaints through our complaint channel
or contact us by email.

Users may also report privacy concerns
to the appropriate supervisory authority.


We may entrust certain personal information processing activities
to trusted partners for specific purposes and within a defined scope.

We obtain explicit authorization from users prior to processing
personal information through third parties.

The names and identities of recipients, third-party partners,
and entrusted parties are disclosed where applicable.

Recipients and entrusted parties must comply with confidentiality,
security responsibilities, and applicable data protection obligations.

Public disclosure of personal information may involve risk assessment
and prominent notification to users.

For cross-border data transfers, we assess applicable security measures
before transmitting personal information overseas.


We have specific rules for collecting children's personal information
and minors' information.

We identify child users through age verification
and may require guardian verification.

Children's personal information may be anonymized
or de-identified when required.

We provide special protection mechanisms
for children's privacy and apply strict protection measures.

We conduct security and risk assessments
for children's information and evaluate potential impacts.

    """

    # ========================================================
    # RUN ANALYSIS
    # ========================================================

    results = analyze_policy(sample_policy)

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================

    print_results(results)