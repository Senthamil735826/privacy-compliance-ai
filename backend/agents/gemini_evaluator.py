"""Google Gemini evaluator for privacy compliance indicators."""

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


class GeminiEvaluator(BaseLLMEvaluator):
    """Evaluate privacy policy evidence using Google Gemini models."""

    DEFAULT_MODEL = "gemini-3.5-flash"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            raise MissingConfigError(
                agent_name=self.agent_name,
                indicator_id="",
                message="GEMINI_API_KEY is not configured.",
            )

        self.model = model or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.max_retries = max_retries
        self._client = None

    @property
    def agent_name(self) -> str:
        return "gemini"

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except ImportError as err:
                raise MissingConfigError(
                    agent_name=self.agent_name,
                    indicator_id="",
                    message=f"google-genai package is not installed: {err}",
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
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )

                raw_text = response.text or ""
                return self.parse_and_validate(
                    raw_content=raw_text,
                    indicator_id=indicator_id,
                    original_evidence=evidence,
                )

            except Exception as exc:
                err_str = str(exc).lower()
                status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)

                if "not_found" in err_str or status_code == 404 or "no longer available" in err_str:
                    raise ModelUnavailableError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Gemini model '{self.model}' not found or unavailable: {exc}",
                        original_exception=exc,
                    ) from exc

                if "api_key" in err_str or "unauthenticated" in err_str or status_code == 401 or status_code == 403:
                    raise AuthFailureError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Gemini authentication failed: {exc}",
                        original_exception=exc,
                    ) from exc

                if "resource_exhausted" in err_str or status_code == 429:
                    if "quota" in err_str or "credit" in err_str or "billing" in err_str:
                        raise QuotaExhaustedError(
                            agent_name=self.agent_name,
                            indicator_id=indicator_id,
                            message=f"Gemini quota exhausted: {exc}",
                            original_exception=exc,
                        ) from exc

                    last_error = RateLimitedError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Gemini rate limited: {exc}",
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
                        message=f"Gemini connection timeout: {exc}",
                        original_exception=exc,
                    )
                    if attempt < self.max_retries:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    raise last_error from exc

                raise ProviderError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Gemini evaluation error ({type(exc).__name__}): {exc}",
                    original_exception=exc,
                ) from exc

        if last_error:
            raise last_error
        raise ProviderError(
            agent_name=self.agent_name,
            indicator_id=indicator_id,
            message="Gemini evaluation failed after retries.",
        )
