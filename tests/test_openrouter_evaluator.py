"""Offline unit tests for OpenRouterEvaluator with mocked OpenAI API."""

import pytest
from unittest.mock import MagicMock, patch

from backend.agents.llm_evaluator import EvaluationResult, LLMEvaluator
from backend.agents.openrouter_evaluator import OpenRouterEvaluator
from backend.agents.provider_errors import (
    AuthFailureError,
    InvalidResponseError,
    MissingConfigError,
    ModelUnavailableError,
    QuotaExhaustedError,
    RateLimitedError,
    TimeoutNetworkError,
)


def _mock_completion_response(text: str):
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = text
    response.choices = [choice]
    return response


# ============================================================================
# PROTOCOL & INITIALIZATION
# ============================================================================

def test_openrouter_evaluator_protocol_adherence():
    """Verify OpenRouterEvaluator complies with LLMEvaluator runtime protocol."""
    evaluator = OpenRouterEvaluator(api_key="mock_key")
    assert isinstance(evaluator, LLMEvaluator)
    assert evaluator.agent_name == "openrouter"


def test_openrouter_evaluator_missing_api_key():
    """Verify MissingConfigError is raised when no API key is configured."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(MissingConfigError, match="OPENROUTER_API_KEY is not configured"):
            OpenRouterEvaluator(api_key=None)


def test_openrouter_evaluator_empty_evidence_no_api_call():
    """Verify empty evidence immediately returns inconclusive without invoking API."""
    evaluator = OpenRouterEvaluator(api_key="mock_key")
    evaluator._get_client = MagicMock()

    res = evaluator.evaluate(
        evidence="   \n  ",
        indicator_id="B1",
        indicator_description="Test indicator",
    )
    assert res.decision == "inconclusive"
    assert res.confidence == 0.0
    assert res.agent_name == "openrouter"
    assert res.evidence == []
    evaluator._get_client.assert_not_called()


# ============================================================================
# RESPONSE PARSING & QUOTE VERIFICATION
# ============================================================================

def test_openrouter_evaluator_valid_response():
    """Verify successful parsing of a valid JSON response from OpenRouter."""
    evaluator = OpenRouterEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client

    sample_evidence = "We collect your email and device ID to deliver services."
    valid_json = (
        '{"decision": "compliant", "confidence": 0.95, '
        '"rationale": "Explicitly details collected data.", '
        '"evidence": ["We collect your email and device ID"]}'
    )
    mock_client.chat.completions.create.return_value = _mock_completion_response(valid_json)

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


def test_openrouter_evaluator_markdown_json_response():
    """Verify OpenRouter code fences (```json ... ```) are cleanly extracted."""
    evaluator = OpenRouterEvaluator(api_key="mock_key")
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
    mock_client.chat.completions.create.return_value = _mock_completion_response(fenced_json)

    res = evaluator.evaluate(
        evidence=sample_evidence,
        indicator_id="B25",
        indicator_description="Right to erasure",
    )
    assert res.decision == "compliant"
    assert res.confidence == 0.88
    assert len(res.evidence) == 1


def test_openrouter_evaluator_fabricated_quote_filtered():
    """Verify fabricated quotes (not in original text) are dropped and confidence penalized."""
    evaluator = OpenRouterEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client

    sample_evidence = "Data is encrypted in transit using TLS 1.3."
    hallucinated_json = (
        '{"decision": "compliant", "confidence": 0.9, '
        '"rationale": "Strong security.", '
        '"evidence": ["Data is stored in Switzerland for 10 years"]}'
    )
    mock_client.chat.completions.create.return_value = _mock_completion_response(hallucinated_json)

    res = evaluator.evaluate(
        evidence=sample_evidence,
        indicator_id="B16",
        indicator_description="Storage location",
    )
    assert res.evidence == []
    assert res.confidence <= 0.4


# ============================================================================
# SCHEMA VALIDATION ERRORS
# ============================================================================

def test_openrouter_evaluator_invalid_json():
    """Verify non-JSON response raises InvalidResponseError."""
    evaluator = OpenRouterEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client
    mock_client.chat.completions.create.return_value = _mock_completion_response("Not JSON at all")

    with pytest.raises(InvalidResponseError, match="not valid JSON"):
        evaluator.evaluate(
            evidence="Some policy text.",
            indicator_id="B1",
            indicator_description="Policy Name",
        )


def test_openrouter_evaluator_invalid_decision():
    """Verify unknown decision string raises InvalidResponseError."""
    evaluator = OpenRouterEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client
    mock_client.chat.completions.create.return_value = _mock_completion_response(
        '{"decision": "unknown_status", "confidence": 0.5, "rationale": "test", "evidence": []}'
    )

    with pytest.raises(InvalidResponseError, match="Invalid decision value"):
        evaluator.evaluate(
            evidence="Some policy text.",
            indicator_id="B1",
            indicator_description="Policy Name",
        )


def test_openrouter_evaluator_invalid_confidence():
    """Verify out-of-range confidence raises InvalidResponseError."""
    evaluator = OpenRouterEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client
    mock_client.chat.completions.create.return_value = _mock_completion_response(
        '{"decision": "compliant", "confidence": 1.5, "rationale": "test", "evidence": []}'
    )

    with pytest.raises(InvalidResponseError, match="Confidence must be a float between 0.0 and 1.0"):
        evaluator.evaluate(
            evidence="Some policy text.",
            indicator_id="B1",
            indicator_description="Policy Name",
        )


def test_openrouter_evaluator_empty_response():
    """Verify empty response raises InvalidResponseError."""
    evaluator = OpenRouterEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client
    mock_client.chat.completions.create.return_value = _mock_completion_response("")

    with pytest.raises(InvalidResponseError, match="Model returned an empty response"):
        evaluator.evaluate(
            evidence="Some policy text.",
            indicator_id="B1",
            indicator_description="Policy Name",
        )


# ============================================================================
# PROVIDER ERRORS & EXCEPTION HANDLING
# ============================================================================

def test_openrouter_evaluator_auth_failure():
    """Verify 401 / invalid API key translates to AuthFailureError."""
    evaluator = OpenRouterEvaluator(api_key="bad_key")
    mock_client = MagicMock()
    evaluator._client = mock_client

    exc = Exception("Unauthorized: Invalid API Key")
    exc.status_code = 401
    mock_client.chat.completions.create.side_effect = exc

    with pytest.raises(AuthFailureError, match="OpenRouter authentication failed"):
        evaluator.evaluate(
            evidence="Some evidence",
            indicator_id="B1",
            indicator_description="Desc",
        )


def test_openrouter_evaluator_credits_exhausted():
    """Verify 402 / credit balance exhausted translates to QuotaExhaustedError."""
    evaluator = OpenRouterEvaluator(api_key="mock_key")
    mock_client = MagicMock()
    evaluator._client = mock_client

    exc = Exception("Payment Required: User has insufficient credits")
    exc.status_code = 402
    mock_client.chat.completions.create.side_effect = exc

    with pytest.raises(QuotaExhaustedError, match="OpenRouter credits exhausted"):
        evaluator.evaluate(
            evidence="Some evidence",
            indicator_id="B1",
            indicator_description="Desc",
        )


def test_openrouter_evaluator_model_unavailable():
    """Verify 404 / model not found translates to ModelUnavailableError."""
    evaluator = OpenRouterEvaluator(api_key="mock_key", model="unknown/model-xyz")
    mock_client = MagicMock()
    evaluator._client = mock_client

    exc = Exception("Model 'unknown/model-xyz' not found")
    exc.status_code = 404
    mock_client.chat.completions.create.side_effect = exc

    with pytest.raises(ModelUnavailableError, match="model 'unknown/model-xyz' not found"):
        evaluator.evaluate(
            evidence="Some evidence",
            indicator_id="B1",
            indicator_description="Desc",
        )


def test_openrouter_evaluator_rate_limited_retry():
    """Verify 429 rate limit triggers retries then raises RateLimitedError."""
    evaluator = OpenRouterEvaluator(api_key="mock_key", max_retries=1)
    mock_client = MagicMock()
    evaluator._client = mock_client

    exc = Exception("Rate limit exceeded")
    exc.status_code = 429
    mock_client.chat.completions.create.side_effect = exc

    with patch("time.sleep"):
        with pytest.raises(RateLimitedError, match="OpenRouter rate limited"):
            evaluator.evaluate(
                evidence="Some evidence",
                indicator_id="B1",
                indicator_description="Desc",
            )

    assert mock_client.chat.completions.create.call_count == 2


def test_openrouter_evaluator_timeout_retry():
    """Verify timeout triggers retries then raises TimeoutNetworkError."""
    evaluator = OpenRouterEvaluator(api_key="mock_key", max_retries=1)
    mock_client = MagicMock()
    evaluator._client = mock_client

    exc = Exception("Connection timeout error")
    mock_client.chat.completions.create.side_effect = exc

    with patch("time.sleep"):
        with pytest.raises(TimeoutNetworkError, match="OpenRouter connection timeout"):
            evaluator.evaluate(
                evidence="Some evidence",
                indicator_id="B1",
                indicator_description="Desc",
            )

    assert mock_client.chat.completions.create.call_count == 2
