"""Offline unit tests for ClaudeEvaluator with mocked Anthropic API."""

import pytest
from unittest.mock import MagicMock, patch

from backend.agents.claude_evaluator import ClaudeEvaluator
from backend.agents.llm_evaluator import EvaluationResult, LLMEvaluator
from backend.agents.provider_errors import (
    AuthFailureError,
    InvalidResponseError,
    MissingConfigError,
    ModelUnavailableError,
    QuotaExhaustedError,
    RateLimitedError,
    TimeoutNetworkError,
)


def _mock_content_block(text: str):
    block = MagicMock()
    block.text = text
    return [block]


# ============================================================================
# PROTOCOL & INITIALIZATION
# ============================================================================

def test_claude_evaluator_protocol_adherence():
    """Verify ClaudeEvaluator complies with LLMEvaluator runtime protocol."""
    evaluator = ClaudeEvaluator(api_key="mock_key")
    assert isinstance(evaluator, LLMEvaluator)
    assert evaluator.agent_name == "claude"


def test_claude_evaluator_missing_api_key():
    """Verify MissingConfigError is raised when no API key is configured."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(MissingConfigError, match="ANTHROPIC_API_KEY is not configured"):
            ClaudeEvaluator(api_key=None)


def test_claude_evaluator_empty_evidence_no_api_call():
    """Verify empty evidence immediately returns inconclusive without invoking API."""
    evaluator = ClaudeEvaluator(api_key="mock_key")
    evaluator._get_client = MagicMock()  # If called, test fails

    res = evaluator.evaluate(
        evidence="   \n  ",
        indicator_id="B1",
        indicator_description="Test indicator",
    )
    assert res.decision == "inconclusive"
    assert res.confidence == 0.0
    assert res.agent_name == "claude"
    assert res.evidence == []
    evaluator._get_client.assert_not_called()


# ============================================================================
# RESPONSE PARSING & QUOTE VERIFICATION
# ============================================================================

def test_claude_evaluator_valid_response():
    """Verify successful parsing of a valid JSON response from Claude."""
    evaluator = ClaudeEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client

    sample_evidence = "We collect your email and device ID to deliver services."
    valid_json = (
        '{"decision": "compliant", "confidence": 0.95, '
        '"rationale": "Explicitly details collected data.", '
        '"evidence": ["We collect your email and device ID"]}'
    )
    mock_client.messages.create.return_value.content = _mock_content_block(valid_json)

    res = evaluator.evaluate(
        evidence=sample_evidence,
        indicator_id="B7",
        indicator_description="Data collection types",
    )

    assert isinstance(res, EvaluationResult)
    assert res.decision == "compliant"
    assert res.confidence == 0.95
    assert "Explicitly details" in res.rationale
    assert res.evidence == ["We collect your email and device ID"]


def test_claude_evaluator_markdown_json_response():
    """Verify Claude code fences (```json ... ```) are cleanly extracted."""
    evaluator = ClaudeEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client

    sample_evidence = "Users can delete their account at any time in settings."
    fenced_json = (
        "```json\n"
        '{\n  "decision": "compliant",\n  "confidence": 0.88,\n'
        '  "rationale": "Clear deletion right.",\n'
        '  "evidence": ["Users can delete their account at any time"]\n}\n'
        "```"
    )
    mock_client.messages.create.return_value.content = _mock_content_block(fenced_json)

    res = evaluator.evaluate(
        evidence=sample_evidence,
        indicator_id="B25",
        indicator_description="Right to erasure",
    )
    assert res.decision == "compliant"
    assert res.confidence == 0.88
    assert len(res.evidence) == 1


def test_claude_evaluator_fabricated_quote_filtered():
    """Verify fabricated quotes (not in original text) are dropped and confidence is penalized."""
    evaluator = ClaudeEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client

    sample_evidence = "Data is encrypted in transit using TLS 1.3."
    hallucinated_json = (
        '{"decision": "compliant", "confidence": 0.9, '
        '"rationale": "Strong security.", '
        '"evidence": ["Data is stored in Switzerland for 10 years"]}'
    )
    mock_client.messages.create.return_value.content = _mock_content_block(hallucinated_json)

    res = evaluator.evaluate(
        evidence=sample_evidence,
        indicator_id="B16",
        indicator_description="Storage location",
    )
    # Fabricated quote should be stripped
    assert res.evidence == []
    # Confidence penalized because supporting quotes were fabricated
    assert res.confidence <= 0.4


# ============================================================================
# SCHEMA VALIDATION ERRORS
# ============================================================================

def test_claude_evaluator_invalid_json():
    """Verify invalid JSON raises InvalidResponseError."""
    evaluator = ClaudeEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client
    mock_client.messages.create.return_value.content = _mock_content_block("I think it is compliant.")

    with pytest.raises(InvalidResponseError, match="not valid JSON"):
        evaluator.evaluate(
            evidence="Some policy text.",
            indicator_id="B1",
            indicator_description="Policy Name",
        )


def test_claude_evaluator_invalid_decision():
    """Verify unknown decision string raises InvalidResponseError."""
    evaluator = ClaudeEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client
    mock_client.messages.create.return_value.content = _mock_content_block(
        '{"decision": "partially_compliant", "confidence": 0.5, "rationale": "mixed", "evidence": []}'
    )

    with pytest.raises(InvalidResponseError, match="Invalid decision value"):
        evaluator.evaluate(
            evidence="Some policy text.",
            indicator_id="B1",
            indicator_description="Policy Name",
        )


def test_claude_evaluator_invalid_confidence():
    """Verify confidence outside [0.0, 1.0] raises InvalidResponseError."""
    evaluator = ClaudeEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client
    mock_client.messages.create.return_value.content = _mock_content_block(
        '{"decision": "compliant", "confidence": 95, "rationale": "High score", "evidence": []}'
    )

    with pytest.raises(InvalidResponseError, match="Confidence must be a float between 0.0 and 1.0"):
        evaluator.evaluate(
            evidence="Some policy text.",
            indicator_id="B1",
            indicator_description="Policy Name",
        )


def test_claude_evaluator_empty_response():
    """Verify empty response raises InvalidResponseError."""
    evaluator = ClaudeEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client
    mock_client.messages.create.return_value.content = _mock_content_block("   ")

    with pytest.raises(InvalidResponseError, match="Model returned an empty response"):
        evaluator.evaluate(
            evidence="Some policy text.",
            indicator_id="B1",
            indicator_description="Policy Name",
        )


# ============================================================================
# PROVIDER ERRORS & EXCEPTION HANDLING
# ============================================================================

def test_claude_evaluator_auth_failure():
    """Verify Anthropic AuthenticationError translates to AuthFailureError."""
    import anthropic
    evaluator = ClaudeEvaluator(api_key="bad_key")
    mock_client = MagicMock()
    evaluator._client = mock_client

    mock_client.messages.create.side_effect = anthropic.AuthenticationError(
        message="Invalid API Key",
        response=MagicMock(status_code=401),
        body=None,
    )

    with pytest.raises(AuthFailureError, match="Claude authentication failed"):
        evaluator.evaluate(
            evidence="Some evidence",
            indicator_id="B1",
            indicator_description="Desc",
        )


def test_claude_evaluator_quota_exhausted():
    """Verify Anthropic RateLimitError with credit balance exhausted maps to QuotaExhaustedError."""
    import anthropic
    evaluator = ClaudeEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client

    mock_client.messages.create.side_effect = anthropic.RateLimitError(
        message="Your credit balance is too low to access the Anthropic API.",
        response=MagicMock(status_code=429),
        body=None,
    )

    with pytest.raises(QuotaExhaustedError, match="Claude quota exhausted"):
        evaluator.evaluate(
            evidence="Some evidence",
            indicator_id="B1",
            indicator_description="Desc",
        )


def test_claude_evaluator_bad_request_credit_exhausted():
    """Verify Anthropic BadRequestError (HTTP 400 credit balance too low) maps to QuotaExhaustedError."""
    import anthropic
    evaluator = ClaudeEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client

    mock_client.messages.create.side_effect = anthropic.BadRequestError(
        message="Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.",
        response=MagicMock(status_code=400),
        body=None,
    )

    with pytest.raises(QuotaExhaustedError, match="Claude quota exhausted"):
        evaluator.evaluate(
            evidence="Some evidence",
            indicator_id="B1",
            indicator_description="Desc",
        )



def test_claude_evaluator_model_unavailable():
    """Verify NotFoundError maps to ModelUnavailableError."""
    import anthropic
    evaluator = ClaudeEvaluator(api_key="mock_key", model="claude-unknown-999")
    mock_client = MagicMock()
    evaluator._client = mock_client

    mock_client.messages.create.side_effect = anthropic.NotFoundError(
        message="Model claude-unknown-999 not found",
        response=MagicMock(status_code=404),
        body=None,
    )

    with pytest.raises(ModelUnavailableError, match="model 'claude-unknown-999' not found"):
        evaluator.evaluate(
            evidence="Some evidence",
            indicator_id="B1",
            indicator_description="Desc",
        )


def test_claude_evaluator_timeout_retry():
    """Verify timeout triggers retry before raising TimeoutNetworkError."""
    import anthropic
    evaluator = ClaudeEvaluator(api_key="mock_key", max_retries=1)
    mock_client = MagicMock()
    evaluator._client = mock_client

    mock_client.messages.create.side_effect = anthropic.APITimeoutError(
        request=MagicMock()
    )

    with pytest.raises(TimeoutNetworkError, match="timeout or network failure"):
        evaluator.evaluate(
            evidence="Some evidence",
            indicator_id="B1",
            indicator_description="Desc",
        )

    # 1 initial attempt + 1 retry = 2 calls
    assert mock_client.messages.create.call_count == 2
