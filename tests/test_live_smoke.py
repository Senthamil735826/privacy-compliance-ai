"""Opt-in live smoke tests for LLM providers.

These tests make real network calls and require valid credentials with credits.
They are marked with @pytest.mark.live and skipped by default in normal offline CI.

Run explicitly with:
    pytest tests/test_live_smoke.py -m live
"""

import os
import pytest

from backend.agents.claude_evaluator import ClaudeEvaluator
from backend.agents.gemini_evaluator import GeminiEvaluator
from backend.agents.groq_evaluator import GroqEvaluator


@pytest.mark.live
def test_live_claude_smoke():
    """Live smoke test for Anthropic Claude evaluator."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set in environment.")

    from backend.agents.provider_errors import QuotaExhaustedError

    evaluator = ClaudeEvaluator()
    try:
        res = evaluator.evaluate(
            evidence="We collect your email address for account authentication.",
            indicator_id="B7",
            indicator_description="Types of personal data collected",
        )
        assert res.agent_name == "claude"
        assert res.decision in {"compliant", "non_compliant", "inconclusive"}
        assert 0.0 <= res.confidence <= 1.0
        print(f"\n[LIVE CLAUDE SUCCESS]: {res.to_dict()}")
    except QuotaExhaustedError as exc:
        pytest.skip(f"Anthropic account has insufficient credit balance: {exc.message}")


@pytest.mark.live
def test_live_groq_smoke():
    """Live smoke test for Groq evaluator."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY not set in environment.")

    from backend.agents.provider_errors import QuotaExhaustedError

    evaluator = GroqEvaluator()
    try:
        res = evaluator.evaluate(
            evidence="We collect your email address for account authentication.",
            indicator_id="B7",
            indicator_description="Types of personal data collected",
        )
        assert res.agent_name == "groq"
        assert res.decision in {"compliant", "non_compliant", "inconclusive"}
        print(f"\n[LIVE GROQ SUCCESS]: {res.to_dict()}")
    except QuotaExhaustedError as exc:
        pytest.skip(f"Groq account has insufficient quota: {exc.message}")


@pytest.mark.live
def test_live_gemini_smoke():
    """Live smoke test for Gemini evaluator."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set in environment.")

    from backend.agents.provider_errors import QuotaExhaustedError

    evaluator = GeminiEvaluator()
    try:
        res = evaluator.evaluate(
            evidence="We collect your email address for account authentication.",
            indicator_id="B7",
            indicator_description="Types of personal data collected",
        )
        assert res.agent_name == "gemini"
        assert res.decision in {"compliant", "non_compliant", "inconclusive"}
        print(f"\n[LIVE GEMINI SUCCESS]: {res.to_dict()}")
    except QuotaExhaustedError as exc:
        pytest.skip(f"Gemini quota exhausted: {exc.message}")


@pytest.mark.live
def test_live_openai_smoke():
    """Live smoke test for OpenAI evaluator."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set in environment.")

    from backend.agents.openai_evaluator import OpenAIEvaluator
    from backend.agents.provider_errors import QuotaExhaustedError

    evaluator = OpenAIEvaluator()
    try:
        res = evaluator.evaluate(
            evidence="We collect your email address for account authentication.",
            indicator_id="B7",
            indicator_description="Types of personal data collected",
        )
        assert res.agent_name == "openai"
        assert res.decision in {"compliant", "non_compliant", "inconclusive"}
        print(f"\n[LIVE OPENAI SUCCESS]: {res.to_dict()}")
    except QuotaExhaustedError as exc:
        pytest.skip(f"OpenAI account has insufficient balance / quota exhausted: {exc.message}")


@pytest.mark.live
def test_live_deepseek_smoke():
    """Live smoke test for DeepSeek evaluator."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set in environment.")

    from backend.agents.deepseek_evaluator import DeepSeekEvaluator
    from backend.agents.provider_errors import QuotaExhaustedError

    evaluator = DeepSeekEvaluator()
    try:
        res = evaluator.evaluate(
            evidence="We collect your email address for account authentication.",
            indicator_id="B7",
            indicator_description="Types of personal data collected",
        )
        assert res.agent_name == "deepseek"
        assert res.decision in {"compliant", "non_compliant", "inconclusive"}
        print(f"\n[LIVE DEEPSEEK SUCCESS]: {res.to_dict()}")
    except QuotaExhaustedError as exc:
        pytest.skip(f"DeepSeek account has insufficient balance: {exc.message}")


@pytest.mark.live
def test_live_openrouter_smoke():
    """Live smoke test for OpenRouter evaluator."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set in environment.")

    from backend.agents.openrouter_evaluator import OpenRouterEvaluator
    from backend.agents.provider_errors import QuotaExhaustedError

    evaluator = OpenRouterEvaluator()
    try:
        res = evaluator.evaluate(
            evidence="We collect your email address for account authentication.",
            indicator_id="B7",
            indicator_description="Types of personal data collected",
        )
        assert res.agent_name == "openrouter"
        assert res.decision in {"compliant", "non_compliant", "inconclusive"}
        assert 0.0 <= res.confidence <= 1.0
        print(f"\n[LIVE OPENROUTER SUCCESS]: {res.to_dict()}")
    except QuotaExhaustedError as exc:
        pytest.skip(f"OpenRouter account has insufficient credits: {exc.message}")



