import sys
import io
from pathlib import Path

# pyrefly: ignore[missing-import]
import pytest
from fastapi.testclient import TestClient

# Ensure project root and backend are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.indicators.indicator_engine import IndicatorEngine
from backend.main import app

engine = IndicatorEngine()

# ============================================================================
# COMPREHENSIVE TEST DATA: (indicator_id, [positives], [negatives])
# At least 2 positives and 2 negatives per indicator B1-B40, including near misses
# ============================================================================

INDICATOR_TEST_CASES = [
    (
        "B1",
        [
            "Basic Information - Privacy Policy Name: Sample Smart Services Privacy Policy",
            "This document is the official User Privacy Policy for our application.",
        ],
        [
            "Please read this Privacy Policy carefully to understand our data practices.",
            "We adhere to a strict company security policy regarding corporate equipment.",
            "Our terms of service govern intellectual property ownership.",
        ],
    ),
    (
        "B2",
        [
            "Version Number: 1.0",
            "Current version: Version number 1.0.",
        ],
        [
            "This is the revised version of our compliance manual.",
            "We updated version 3.2 of the backend database drivers.",
            "The release notes describe minor bug fixes.",
        ],
    ),
    (
        "B3",
        [
            "Effective Date: January 1, 2026",
            "Effective date: January 1, 2026.",
        ],
        [
            "This statement is effective from the date of account registration.",
            "We implement effective security controls against cyber attacks.",
            "The special pricing discount is effective until Friday.",
        ],
    ),
    (
        "B4",
        [
            "Last Updated: September 1, 2026",
            "Revision date: August 15, 2026.",
        ],
        [
            "We will revise the last updated date when changes are made.",
            "We regularly update our software packages to fix system bugs.",
            "Customer records were modified by the customer support agent.",
        ],
    ),
    (
        "B5",
        [
            "The Data Controller responsible for your personal data is Example Digital Ltd.",
            "Acme Corp acts as the personal info processor under applicable law.",
        ],
        [
            "The gaming controller connects to the mobile device via bluetooth.",
            "The traffic controller directed vehicles away from the highway.",
        ],
    ),
    (
        "B6",
        [
            "Contact Information: privacy@example.com.",
            "Please direct questions to our customer support email address: support@domain.com.",
        ],
        [
            "We do not store plain email text in unencrypted server logs.",
            "Contact our sales department for bulk enterprise pricing discounts.",
        ],
    ),
    (
        "B7",
        [
            "We collect personal information for the purpose of providing our services.",
            "Personal data is collected and processed only to achieve the purpose of our services.",
        ],
        [
            "We collect discarded plastic bottles for environmental recycling purposes.",
            "Our company has a clear commercial purpose.",
        ],
    ),
    (
        "B8",
        [
            "We explain the categories of personal data collected in this policy.",
            "We explicitly state what information is collected and clearly explain its usage.",
        ],
        [
            "The glass display case has transparent acrylic panels.",
            "The teacher will explain the mathematical equation on the chalkboard.",
        ],
    ),
    (
        "B9",
        [
            "Our website uses cookies and web beacons to remember user preferences.",
            "The mobile application integrates a third-party tracking SDK.",
        ],
        [
            "The cafeteria baked fresh chocolate cookies for dessert.",
            "We store local files on encrypted SSD hardware.",
        ],
    ),
    (
        "B10",
        [
            "We notify users and obtain explicit consent before collecting sensitive data.",
            "Where required, we inform individuals and request authorization to use their records.",
        ],
        [
            "We notify subscribers whenever scheduled server maintenance occurs.",
            "Staff members must authorize physical badge requests.",
        ],
    ),
    (
        "B11",
        [
            "Users can opt-out of optional analytics and promotional messages at any time.",
            "You may refuse collection of usage diagnostics in the account settings.",
        ],
        [
            "The security guard will refuse entry to visitors without identification.",
            "Please close all active applications before shutting down the operating system.",
        ],
    ),
    (
        "B12",
        [
            "We do not collect information from minors without verifiable guardian's consent.",
            "Special protective measures are enforced to protect children using our services.",
        ],
        [
            "The vehicle sustained minor paint scratches during parking.",
            "Adult account holders are responsible for protecting their credentials.",
        ],
    ),
    (
        "B13",
        [
            "We collect only the minimum necessary data to provide the requested service.",
            "Personal data processed is strictly necessary for purpose of fulfilling transactions.",
        ],
        [
            "A minimum purchase of twenty dollars is necessary to receive free shipping.",
            "We collect user feedback across all customer satisfaction channels.",
        ],
    ),
    (
        "B14",
        [
            "Personal data will be used only for declared purposes and not for other purposes.",
            "We enforce purpose limitation and do not process info beyond purpose scope.",
        ],
        [
            "The primary purpose of this sorting algorithm is to optimize memory usage.",
            "We restrict vehicle access in the corporate pedestrian courtyard.",
        ],
    ),
    (
        "B15",
        [
            "We obtain separate consent before processing biometric fingerprint data.",
            "Sensitive personal info such as medical health data receives heightened safeguards.",
        ],
        [
            "Employees are encouraged to take regular breaks to maintain physical health.",
            "The customer service agent greeted each guest with a warm and friendly face.",
        ],
    ),
    (
        "B16",
        [
            "User information is stored in secure cloud infrastructure servers located at Virginia.",
            "All domestic storage of customer records occurs within company servers and data centers.",
        ],
        [
            "Our flagship retail store location is situated in downtown Chicago.",
            "Remember to save your unsaved document drafts to local desktop folders.",
        ],
    ),
    (
        "B17",
        [
            "We retain personal data only for as long as necessary for the stated duration.",
            "Customer records are stored until account deletion according to our retention period.",
        ],
        [
            "The veteran employee will retain his leadership role for the upcoming fiscal quarter.",
            "We save temporary cache files until the operating system restarts.",
        ],
    ),
    (
        "B18",
        [
            "Our data security systems have achieved ISO27001 compliance certification.",
            "We maintain official security certification under the national level protection framework.",
        ],
        [
            "The software architect holds a university degree qualification in mathematics.",
            "The passenger vehicle passed its annual mechanical safety inspection.",
        ],
    ),
    (
        "B19",
        [
            "We use access control, data encryption, and security monitoring to protect personal information.",
            "Our systems apply reasonable technical and organizational safeguards against unauthorized breach.",
        ],
        [
            "The front entrance is locked with a physical brass deadbolt at night.",
            "Security guards monitor the parking facility perimeter fence.",
        ],
    ),
    (
        "B20",
        [
            "In case of a data leak, our emergency contingency plan ensures rapid response and remediation.",
            "We maintain a structured security incident disposal and remedial measures mechanism.",
        ],
        [
            "The basement water pipe has a minor plumbing leak behind the wall.",
            "Emergency exit stairwells are equipped with battery-powered backup lighting.",
        ],
    ),
    (
        "B21",
        [
            "We conduct periodic internal security audits of our data handling systems.",
            "Our compliance team performs regular security self-inspections and annual security audits.",
        ],
        [
            "We assess privacy and security risks.",
            "We apply additional safeguards to children's information where applicable and assess relevant privacy and security risks.",
        ],
    ),
    (
        "B22",
        [
            "If a confirmed security incident occurs, we will notify affected individuals promptly.",
            "In the event of a personal data leak, we will inform regulatory authorities as required by law.",
        ],
        [
            "We notify newsletter subscribers whenever a new recipe article is published.",
            "The receptionist informed the visitor that the conference room was ready.",
        ],
    ),
    (
        "B23",
        [
            "You may request access to your personal information at any time.",
            "Users have the right to obtain a copy of their personal data.",
        ],
        [
            "We use access controls to protect personal information.",
            "We use access controls, encryption where appropriate, staff training, and security monitoring to protect personal information.",
        ],
    ),
    (
        "B24",
        [
            "You have the right to correct personal information or submit a deletion request.",
            "Users may request correction of inaccurate data or delete personal data.",
        ],
        [
            "The proofreader made a grammatical correction to the first chapter.",
            "We update software libraries across production servers every weekend.",
        ],
    ),
    (
        "B25",
        [
            "You can withdraw consent for processing by submitting a request through your profile.",
            "Users retain the right to revoke consent and cancel authorization at any time.",
        ],
        [
            "The athlete decided to withdraw from the marathon competition.",
            "We cancel dental appointments if the patient gives less than an hour of notice.",
        ],
    ),
    (
        "B26",
        [
            "You can download or export a copy of your personal data in machine-readable format.",
            "Users have the right to data portability to receive a copy of their personal data.",
        ],
        [
            "Personal information may be transferred across national borders.",
            "We may transfer your personal information to third party service providers.",
        ],
    ),
    (
        "B27",
        [
            "You can configure your privacy preferences and toggle recommendation settings in the app.",
            "Manage mobile push permission settings directly within your account settings.",
        ],
        [
            "The hotel kitchen accommodates dietary preferences for vegetarian diners.",
            "We recommend reading our customer reviews before placing an order.",
        ],
    ),
    (
        "B28",
        [
            "Users may cancel account registration and delete account data permanently.",
            "You have the right to apply for cancellation and close your account.",
        ],
        [
            "We had to cancel the outdoor football tournament because of a thunderstorm.",
            "Bank account transfers require three business days to clear.",
        ],
    ),
    (
        "B29",
        [
            "You can send feedback to our dedicated complaint email channel.",
            "Users have the right to report privacy violations to the competent supervisory authority.",
        ],
        [
            "The sports cable channel broadcasts live football matches around the clock.",
            "Restaurant patrons occasionally complain about long wait times.",
        ],
    ),
    (
        "B30",
        [
            "We engage trusted partners for entrusted processing under strict data sharing agreements.",
            "Personal data shared with service providers is strictly limited to the necessary purpose and scope.",
        ],
        [
            "She was entrusted with leading the community fundraising committee.",
            "Our company shares office space with an architecture consultancy.",
        ],
    ),
    (
        "B31",
        [
            "We obtain explicit authorization before processing and separate consent prior to sharing data.",
            "Obtain authorization before processing is mandatory prior to any secondary data use.",
        ],
        [
            "He gave his verbal authorization to park the delivery truck in the driveway.",
            "Please read the lab manual thoroughly before processing the chemical samples.",
        ],
    ),
    (
        "B32",
        [
            "We disclose each data recipient identity, including third-party name and entrusted party details.",
            "Data may be provided to specific cloud hosting providers and analytics providers.",
        ],
        [
            "The scholarship recipient thanked the selection committee at the banquet.",
            "Our business partner opened a new boutique downtown.",
        ],
    ),
    (
        "B33",
        [
            "Our contracts establish third-party obligations and a strict confidentiality duty for all vendors.",
            "We legally define the recipient's obligations and security responsibility for data protection.",
        ],
        [
            "Every citizen has a moral duty to perform community service.",
            "The political third party participated actively in the televised debate.",
        ],
    ),
    (
        "B34",
        [
            "We conduct a disclosure risk assessment prior to any public disclosure of system metrics.",
            "Where required to disclose externally, prominent notification and risk assessments are carried out.",
        ],
        [
            "The publicly traded firm made a public disclosure of fourth-quarter corporate revenues.",
            "We notify commuters about public transport schedule revisions.",
        ],
    ),
    (
        "B35",
        [
            "If we transfer personal data overseas, we execute standard contract clauses for international data transfer.",
            "Cross-border data flow and cross-border transmission require a rigorous security assessment.",
        ],
        [
            "The student travelled overseas to study Italian art history.",
            "Standard contract templates are stored in the legal department repository.",
        ],
    ),
    (
        "B36",
        [
            "We do not knowingly collect children's personal information without parental authorization.",
            "Our rules for collecting children's personal information adhere to strict statutory safeguards.",
        ],
        [
            "Children gathered happily to watch the puppet performance in the courtyard.",
            "The university archive collects historical manuscripts and rare photographs.",
        ],
    ),
    (
        "B37",
        [
            "Our system implements an age verification and age judgment mechanism to identify child users.",
            "We use guardian verification procedures to verify whether minors access restricted features.",
        ],
        [
            "The trial judge reviewed the closing arguments presented by the attorneys.",
            "The mechanical clock mechanism requires winding every seven days.",
        ],
    ),
    (
        "B38",
        [
            "We promptly anonymize children's info and enforce children's data desensitization.",
            "Our platform will de-identify children's info to protect minor identities.",
        ],
        [
            "The whistleblower submitted an anonymous complaint to the ethics hotline.",
            "The author published her collection of short stories under a pseudonym.",
        ],
    ),
    (
        "B39",
        [
            "We enforce dedicated protection mechanisms for child privacy protection.",
            "Children's privacy protection measures mandate strict protection for young learners.",
        ],
        [
            "A fiberglass helmet provides vital protection while skateboarding.",
            "High SPF sunscreen delivers effective protection against solar radiation.",
        ],
    ),
    (
        "B40",
        [
            "We conduct a children's info risk assessment before deploying educational applications.",
            "Our compliance auditors perform a children's data security assessment and impact assessment.",
        ],
        [
            "The cardiologist carried out a clinical risk assessment of cardiac symptoms.",
            "The environmental agency conducted a coastal flood impact assessment.",
        ],
    ),
]

# Unrelated texts that should not trigger ANY of the 40 indicators
UNRELATED_TEXTS = [
    (
        "recipe",
        "Preheat the oven to 375 degrees Fahrenheit. Mix the flour, sugar, and baking powder "
        "in a large ceramic bowl, then whisk the eggs and melted butter until completely smooth.",
    ),
    (
        "source_code",
        "function computeFibonacci(n) { if (n <= 1) return n; let a = 0, b = 1; "
        "for (let i = 2; i <= n; i++) { const c = a + b; a = b; b = c; } return b; }",
    ),
    (
        "financial_boilerplate",
        "The yield on 10-year Treasury bonds declined by four basis points following "
        "the Federal Reserve open market committee monetary policy statement.",
    ),
    (
        "astronomy",
        "The James Webb Space Telescope observed distant spiral galaxies located approximately "
        "thirteen billion light-years from Earth in deep space.",
    ),
]


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

# Expand positive cases: (indicator_id, pos_text)
POSITIVE_PARAMS = [
    (ind_id, pos_text)
    for ind_id, positives, _ in INDICATOR_TEST_CASES
    for pos_text in positives
]

# Expand negative cases: (indicator_id, neg_text)
NEGATIVE_PARAMS = [
    (ind_id, neg_text)
    for ind_id, _, negatives in INDICATOR_TEST_CASES
    for neg_text in negatives
]


@pytest.mark.parametrize("indicator_id,pos_text", POSITIVE_PARAMS)
def test_indicator_positive(indicator_id, pos_text):
    result = engine.analyze_policy(pos_text)
    match_found = False
    evidence_found = False

    for ind in result["results"]:
        if ind["id"] == indicator_id:
            match_found = ind["matched"]
            evidence_found = len(ind["evidence"]) > 0
            break

    assert match_found is True, (
        f"Expected indicator {indicator_id} to match positive text: '{pos_text}'"
    )
    assert evidence_found is True, (
        f"Expected indicator {indicator_id} to have evidence for: '{pos_text}'"
    )


@pytest.mark.parametrize("indicator_id,neg_text", NEGATIVE_PARAMS)
def test_indicator_negative(indicator_id, neg_text):
    result = engine.analyze_policy(neg_text)
    match_found = False

    for ind in result["results"]:
        if ind["id"] == indicator_id:
            match_found = ind["matched"]
            break

    assert match_found is False, (
        f"Expected indicator {indicator_id} NOT to match negative text: '{neg_text}'"
    )


@pytest.mark.parametrize("text_type,unrelated_text", UNRELATED_TEXTS)
def test_unrelated_texts_trigger_nothing(text_type, unrelated_text):
    result = engine.analyze_policy(unrelated_text)
    matched_ids = [ind["id"] for ind in result["results"] if ind["matched"]]

    assert matched_ids == [], (
        f"Unrelated text ({text_type}) should trigger 0 indicators, "
        f"but triggered: {matched_ids}"
    )
    assert result["found"] == 0


# ============================================================================
# API CONTRACT & SNAPSHOT TESTS (FastAPI TestClient)
# ============================================================================

def test_api_contract_upload_endpoint():
    client = TestClient(app)

    # Valid minimal PDF bytes
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 72 >> stream\n"
        b"BT /F1 12 Tf 72 712 Td (Contact Information: privacy@example.com) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \n0000000244 00000 n \n0000000367 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n439\n%%EOF"
    )

    response = client.post(
        "/api/policy/upload",
        files={
            "file": (
                "sample_privacy_policy.pdf",
                io.BytesIO(pdf_bytes),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200, (
        f"Expected HTTP 200, got {response.status_code}: {response.text}"
    )
    data = response.json()

    # Exact Top-Level Keys
    assert set(data.keys()) == {
        "status",
        "document_id",
        "indexed_chunks",
        "document",
        "compliance_summary",
        "indicators",
        "chunks",
    }
    assert data["status"] == "success"
    assert isinstance(data["document_id"], str) and data["document_id"]
    assert isinstance(data["indexed_chunks"], int) and data["indexed_chunks"] >= 0

    # Document Section Schema
    doc = data["document"]
    assert set(doc.keys()) == {
        "document_id",
        "indexed_chunks",
        "filename",
        "total_pages",
        "total_characters",
        "total_chunks",
    }
    assert isinstance(doc["filename"], str)
    assert isinstance(doc["total_pages"], int)
    assert isinstance(doc["total_characters"], int)
    assert isinstance(doc["total_chunks"], int)
    assert doc["filename"] == "sample_privacy_policy.pdf"
    assert doc["total_pages"] >= 1

    # Compliance Summary Section Schema
    summary = data["compliance_summary"]
    assert set(summary.keys()) == {
        "total_indicators",
        "matched",
        "not_matched",
        "coverage",
    }
    assert summary["total_indicators"] == 40
    assert isinstance(summary["matched"], int)
    assert isinstance(summary["not_matched"], int)
    assert isinstance(summary["coverage"], (int, float))
    assert summary["matched"] + summary["not_matched"] == 40

    # Indicators List Schema
    indicators = data["indicators"]
    assert isinstance(indicators, list)
    assert len(indicators) == 40

    expected_keys = {
        "id",
        "name",
        "primary",
        "matched",
        "matched_by",
        "any_matches",
        "all_matches",
        "evidence",
    }

    for ind in indicators:
        assert set(ind.keys()) == expected_keys
        assert isinstance(ind["id"], str)
        assert isinstance(ind["name"], str)
        assert isinstance(ind["primary"], str)
        assert isinstance(ind["matched"], bool)
        assert isinstance(ind["matched_by"], str)
        assert isinstance(ind["any_matches"], list)
        assert isinstance(ind["all_matches"], list)
        assert isinstance(ind["evidence"], list)

        for ev in ind["evidence"]:
            assert set(ev.keys()) >= {
                "text",
                "matches",
                "matched_by",
                "evidence_type",
            }
            assert isinstance(ev["text"], str)
            assert isinstance(ev["matches"], list)
            assert isinstance(ev["matched_by"], str)
            assert isinstance(ev["evidence_type"], str)

    # Chunks Section Schema
    chunks = data["chunks"]
    assert isinstance(chunks, list)

    for chunk in chunks:
        assert set(chunk.keys()) == {"chunk_id", "text", "start", "end"}
        assert isinstance(chunk["chunk_id"], int)
        assert isinstance(chunk["text"], str)
        assert isinstance(chunk["start"], int)
        assert isinstance(chunk["end"], int)


# ============================================================================
# REGRESSION TEST: B22 INCIDENT NOTIFICATION
# ============================================================================
def test_b22_detects_sample_policy_incident_notification_wording():
    text = (
        "We periodically review security practices and investigate suspected "
        "data incidents. If a security incident creates a notification obligation, "
        "we will notify affected individuals and relevant authorities as required "
        "by applicable law."
    )

    result = engine.analyze_policy(text)

    b22 = next(
        indicator
        for indicator in result["results"]
        if indicator["id"] == "B22"
    )

    assert b22["matched"] is True, (
        "B22 should detect the sample policy's incident-notification language."
    )
    assert len(b22["evidence"]) > 0
