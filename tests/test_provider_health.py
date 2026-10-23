"""Tests for ProviderHealthService, status mappings, caching, and sanitization."""

import pytest
from unittest.mock import MagicMock, patch

from backend.agents.llm_evaluator import EvaluationResult
from backend.agents.provider_errors import (
    AuthFailureError,
    MissingConfigError,
    ModelUnavailableError,
    ProviderError,
    QuotaExhaustedError,
    RateLimitedError,
    TimeoutNetworkError,
)
from backend.agents.provider_health import (
    ProviderHealthService,
    STATUS_AUTH_ERROR,
    STATUS_ERROR,
    STATUS_INSUFFICIENT_BALANCE,
    STATUS_MODEL_UNAVAILABLE,
    STATUS_NETWORK_ERROR,
    STATUS_NOT_CONFIGURED,
    STATUS_RATE_LIMITED,
    STATUS_READY,
    is_placeholder,
    sanitize_message,
)


# ============================================================================
# HELPER & SANITIZATION TESTS
# ============================================================================

def test_is_placeholder():
    assert is_placeholder(None) is True
    assert is_placeholder("") is True
    assert is_placeholder("   ") is True
    assert is_placeholder("your_api_key_here") is True
    assert is_placeholder("your_openai_api_key_here") is True
    assert is_placeholder("sk-placeholder123") is True
    assert is_placeholder("CHANGE_ME") is True
    assert is_placeholder("TODO") is True
    assert is_placeholder("real_api_key_val_123") is False


def test_sanitize_message():
    assert sanitize_message("Error with sk-abcdef1234567890 key") == "Error with [REDACTED_API_KEY] key"
    assert sanitize_message("Gemini AIzaSyB123456789012345 failed") == "Gemini [REDACTED_API_KEY] failed"
    assert sanitize_message("Groq gsk_1234567890123456 failed") == "Groq [REDACTED_API_KEY] failed"
    assert sanitize_message("") == ""


# ============================================================================
# HEALTH CHECK CLASSIFICATION TESTS
# ============================================================================

def test_missing_key_returns_not_configured(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    service = ProviderHealthService(cache_ttl_seconds=60)
    res = service.check_provider("gemini", force=True)
    assert res.status == STATUS_NOT_CONFIGURED
    assert res.configured is False
    assert res.is_available is False


def test_placeholder_key_returns_not_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_api_key_here")
    service = ProviderHealthService(cache_ttl_seconds=60)
    res = service.check_provider("gemini", force=True)
    assert res.status == STATUS_NOT_CONFIGURED
    assert res.configured is False
    assert res.is_available is False


def test_successful_provider_returns_ready(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_valid_mock_key_12345")
    service = ProviderHealthService(cache_ttl_seconds=60)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.return_value = EvaluationResult(
        agent_name="groq",
        indicator_id="B7",
        decision="compliant",
        confidence=0.95,
        rationale="Valid evidence found.",
        evidence=["user email"],
    )

    with patch("backend.agents.groq_evaluator.GroqEvaluator", return_value=mock_evaluator):
        res = service.check_provider("groq", force=True)
        assert res.status == STATUS_READY
        assert res.configured is True
        assert res.is_available is True
        assert res.error is None
        assert res.last_verified_at is not None


def test_auth_error_classification(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-invalid-test-key")
    service = ProviderHealthService(cache_ttl_seconds=60)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.side_effect = AuthFailureError("openai", "B7", "Invalid authentication header.")

    with patch("backend.agents.openai_evaluator.OpenAIEvaluator", return_value=mock_evaluator):
        res = service.check_provider("openai", force=True)
        assert res.status == STATUS_AUTH_ERROR
        assert res.is_available is False
        assert "Authentication failed" in res.error


def test_insufficient_balance_classification(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    service = ProviderHealthService(cache_ttl_seconds=60)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.side_effect = QuotaExhaustedError(
        "claude", "B7", "Your credit balance is too low to access the Anthropic API."
    )

    with patch("backend.agents.claude_evaluator.ClaudeEvaluator", return_value=mock_evaluator):
        res = service.check_provider("claude", force=True)
        assert res.status == STATUS_INSUFFICIENT_BALANCE
        assert res.is_available is False
        assert "exhausted or too low" in res.error


def test_rate_limited_classification(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test-key")
    service = ProviderHealthService(cache_ttl_seconds=60)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.side_effect = RateLimitedError("deepseek", "B7", "Rate limit reached. 60 req/min.")

    with patch("backend.agents.deepseek_evaluator.DeepSeekEvaluator", return_value=mock_evaluator):
        res = service.check_provider("deepseek", force=True)
        assert res.status == STATUS_RATE_LIMITED
        assert res.is_available is False


def test_model_unavailable_classification(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "valid_key")
    service = ProviderHealthService(cache_ttl_seconds=60)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.side_effect = ModelUnavailableError("gemini", "B7", "Model not found 404.")

    with patch("backend.agents.gemini_evaluator.GeminiEvaluator", return_value=mock_evaluator):
        res = service.check_provider("gemini", force=True)
        assert res.status == STATUS_MODEL_UNAVAILABLE
        assert res.is_available is False


def test_timeout_network_error_classification(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "valid_key")
    service = ProviderHealthService(cache_ttl_seconds=60)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.side_effect = TimeoutNetworkError("groq", "B7", "Connection timed out.")

    with patch("backend.agents.groq_evaluator.GroqEvaluator", return_value=mock_evaluator):
        res = service.check_provider("groq", force=True)
        assert res.status == STATUS_NETWORK_ERROR
        assert res.is_available is False


# ============================================================================
# CACHING TESTS
# ============================================================================

def test_health_check_caching(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "valid_key")
    service = ProviderHealthService(cache_ttl_seconds=300)

    call_count = 0

    def mock_eval(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return EvaluationResult("groq", "B7", "compliant", 0.9, "OK", ["quote"])

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.side_effect = mock_eval

    with patch("backend.agents.groq_evaluator.GroqEvaluator", return_value=mock_evaluator):
        # 1st call executes check
        res1 = service.check_provider("groq", force=False)
        assert call_count == 1
        assert res1.status == STATUS_READY

        # 2nd call uses cache (call_count does not increase)
        res2 = service.check_provider("groq", force=False)
        assert call_count == 1
        assert res2.status == STATUS_READY

        # 3rd call with force=True bypasses cache
        res3 = service.check_provider("groq", force=True)
        assert call_count == 2
        assert res3.status == STATUS_READY


def test_openrouter_health_check_ready(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-valid-test-key")
    service = ProviderHealthService(cache_ttl_seconds=60)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.return_value = EvaluationResult(
        agent_name="openrouter",
        indicator_id="B7",
        decision="compliant",
        confidence=0.92,
        rationale="OpenRouter validated test evidence.",
        evidence=["user email"],
    )

    with patch("backend.agents.openrouter_evaluator.OpenRouterEvaluator", return_value=mock_evaluator):
        res = service.check_provider("openrouter", force=True)
        assert res.status == STATUS_READY
        assert res.configured is True
        assert res.is_available is True
        assert res.error is None
        assert res.provider == "openrouter"


def test_openrouter_health_check_insufficient_credits(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-valid-test-key")
    service = ProviderHealthService(cache_ttl_seconds=60)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.side_effect = QuotaExhaustedError(
        "openrouter", "B7", "402 Payment Required: Insufficient OpenRouter credits."
    )

    with patch("backend.agents.openrouter_evaluator.OpenRouterEvaluator", return_value=mock_evaluator):
        res = service.check_provider("openrouter", force=True)
        assert res.status == STATUS_INSUFFICIENT_BALANCE
        assert res.is_available is False
        assert "credits" in res.error.lower() or "balance" in res.error.lower()

