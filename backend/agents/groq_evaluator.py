"""Groq-backed evaluator for privacy compliance indicators."""

import os
import time
from typing import Optional

from dotenv import find_dotenv, load_dotenv

from backend.agents.base_evaluator import BaseLLMEvaluator
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

load_dotenv(find_dotenv(usecwd=True))


class GroqEvaluator(BaseLLMEvaluator):
    """Evaluate privacy policy evidence using a Groq-hosted LLM."""

    DEFAULT_MODEL = "openai/gpt-oss-20b"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self._api_key:
            raise MissingConfigError(
                agent_name=self.agent_name,
                indicator_id="",
                message="GROQ_API_KEY is not configured.",
            )

        self.model = model or os.getenv("GROQ_MODEL", self.DEFAULT_MODEL)
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None

    @property
    def agent_name(self) -> str:
        return "groq"

    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self._api_key, timeout=self.timeout)
            except ImportError:
                # Fallback to OpenAI-compatible client
                try:
                    from openai import OpenAI
                    self._client = OpenAI(
                        api_key=self._api_key,
                        base_url="https://api.groq.com/openai/v1",
                        timeout=self.timeout,
                    )
                except ImportError as err:
                    raise MissingConfigError(
                        agent_name=self.agent_name,
                        indicator_id="",
                        message=f"Neither groq nor openai package is installed: {err}",
                    ) from err
        return self._client

    def evaluate(
        self,
        *,
        evidence: str,
        indicator_id: str,
        indicator_description: str,
    ) -> EvaluationResult:
        if not evidence or not evidence.strip():
            return self.inconclusive_result(
                indicator_id=indicator_id,
                rationale="No policy evidence was provided.",
            )

        prompt = self.build_prompt(
            evidence=evidence,
            indicator_id=indicator_id,
            indicator_description=indicator_description,
        )

        client = self._get_client()

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a careful privacy policy compliance evaluator. "
                                "Return valid JSON only."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_completion_tokens=600,
                    temperature=0.0,
                )

                content = response.choices[0].message.content or ""
                return self.parse_and_validate(
                    raw_content=content,
                    indicator_id=indicator_id,
                    original_evidence=evidence,
                )

            except Exception as exc:
                err_str = str(exc).lower()
                status_code = getattr(exc, "status_code", None)

                if "401" in err_str or status_code == 401:
                    raise AuthFailureError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Groq authentication failed: {exc}",
                        original_exception=exc,
                    ) from exc

                if "404" in err_str or status_code == 404 or "model_not_found" in err_str:
                    raise ModelUnavailableError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Groq model '{self.model}' not found or unavailable: {exc}",
                        original_exception=exc,
                    ) from exc

                if "429" in err_str or status_code == 429:
                    if "credit" in err_str or "quota" in err_str or "balance" in err_str:
                        raise QuotaExhaustedError(
                            agent_name=self.agent_name,
                            indicator_id=indicator_id,
                            message=f"Groq quota exhausted: {exc}",
                            original_exception=exc,
                        ) from exc

                    last_error = RateLimitedError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Groq rate limited: {exc}",
                        original_exception=exc,
                    )
                    if attempt < self.max_retries:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    raise last_error from exc

                if "timeout" in err_str or "connection" in err_str:
                    last_error = TimeoutNetworkError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Groq connection timeout: {exc}",
                        original_exception=exc,
                    )
                    if attempt < self.max_retries:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    raise last_error from exc

                raise ProviderError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Groq evaluation error ({type(exc).__name__}): {exc}",
                    original_exception=exc,
                ) from exc

        if last_error:
            raise last_error
        raise ProviderError(
            agent_name=self.agent_name,
            indicator_id=indicator_id,
            message="Groq evaluation failed after retries.",
        )

    @staticmethod
    def _parse_response(
        content: str,
        indicator_id: str,
    ) -> dict:
        """Parse and validate the model's JSON response (backward-compatible)."""
        import json

        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Model response must be a JSON object.")

        decision = data.get("decision")
        if decision not in {"compliant", "non_compliant", "inconclusive"}:
            raise ValueError(f"Invalid decision: {decision!r}")

        confidence = data.get("confidence")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0.0 <= confidence <= 1.0
        ):
            raise ValueError("Confidence must be between 0 and 1.")

        rationale = data.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("Rationale must be a non-empty string.")

        evidence = data.get("evidence", [])
        if not isinstance(evidence, list) or not all(
            isinstance(item, str) for item in evidence
        ):
            raise ValueError("Evidence must be a list of strings.")

        return {
            "decision": decision,
            "confidence": float(confidence),
            "rationale": rationale.strip(),
            "evidence": evidence,
        }

