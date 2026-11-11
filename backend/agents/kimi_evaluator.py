"""Kimi (Moonshot AI) evaluator for privacy compliance indicators."""

import os
import time
from typing import Optional
from dotenv import find_dotenv, load_dotenv

from backend.agents.base_evaluator import BaseLLMEvaluator
from backend.agents.llm_evaluator import EvaluationResult
from backend.agents.provider_errors import (
    AuthFailureError,
    InvalidResponseError,
    MissingConfigError,
    ModelUnavailableError,
    ProviderError,
    QuotaExhaustedError,
    RateLimitedError,
    TimeoutNetworkError,
)

load_dotenv(find_dotenv(usecwd=True))


class KimiEvaluator(BaseLLMEvaluator):
    """Evaluate privacy policy evidence using Moonshot AI (Kimi) API."""

    DEFAULT_MODEL = "kimi-k3"
    DEFAULT_BASE_URL = "https://api.moonshot.ai/v1"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("KIMI_API_KEY")
        if not self._api_key:
            raise MissingConfigError(
                agent_name=self.agent_name,
                indicator_id="",
                message="KIMI_API_KEY is not configured.",
            )

        self.model = model or os.getenv("KIMI_MODEL", self.DEFAULT_MODEL)
        self.base_url = (
            base_url
            or os.getenv("KIMI_BASE_URL")
            or self.DEFAULT_BASE_URL
        )
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None

    @property
    def agent_name(self) -> str:
        return "kimi"

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self._api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
            except ImportError as err:
                raise MissingConfigError(
                    agent_name=self.agent_name,
                    indicator_id="",
                    message=f"openai package is required for Kimi/Moonshot client: {err}",
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
                                "You are a specialized legal AI privacy compliance auditor. "
                                "Return only valid JSON matching the exact requested schema."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                )

                choices = response.choices
                if not choices:
                    raise InvalidResponseError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message="Kimi returned an empty completion list.",
                    )

                raw_content = choices[0].message.content or ""
                return self.parse_and_validate(
                    raw_content=raw_content,
                    indicator_id=indicator_id,
                    original_evidence=evidence,
                )

            except Exception as exc:
                err_str = str(exc).lower()
                status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)

                if "unauthorized" in err_str or status_code in (401, 403) or "invalid authentication" in err_str:
                    raise AuthFailureError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Kimi authentication failed: {exc}",
                        original_exception=exc,
                    ) from exc

                if "model_not_found" in err_str or status_code == 404:
                    raise ModelUnavailableError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Kimi model '{self.model}' not available: {exc}",
                        original_exception=exc,
                    ) from exc

                if status_code == 429 or "rate_limit" in err_str or "quota" in err_str or "balance" in err_str or "suspended" in err_str:
                    if "insufficient balance" in err_str or "quota" in err_str or "suspended" in err_str:
                        raise QuotaExhaustedError(
                            agent_name=self.agent_name,
                            indicator_id=indicator_id,
                            message=f"Kimi account balance/quota exhausted: {exc}",
                            original_exception=exc,
                        ) from exc

                    last_error = RateLimitedError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Kimi rate limited: {exc}",
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
                        message=f"Kimi connection timeout: {exc}",
                        original_exception=exc,
                    )
                    if attempt < self.max_retries:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    raise last_error from exc

                raise ProviderError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Kimi evaluation failed: {exc}",
                    original_exception=exc,
                ) from exc

        if last_error:
            raise last_error
        raise ProviderError(
            agent_name=self.agent_name,
            indicator_id=indicator_id,
            message="Kimi evaluation failed with unknown error.",
        )

