"""DeepSeek evaluator for privacy compliance indicators."""

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


class DeepSeekEvaluator(BaseLLMEvaluator):
    """Evaluate privacy policy evidence using DeepSeek models."""

    DEFAULT_MODEL = "deepseek-chat"
    DEFAULT_BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self._api_key:
            raise MissingConfigError(
                agent_name=self.agent_name,
                indicator_id="",
                message="DEEPSEEK_API_KEY is not configured.",
            )

        self.model = model or os.getenv("DEEPSEEK_MODEL", self.DEFAULT_MODEL)
        self.base_url = (
            base_url
            or os.getenv("DEEPSEEK_BASE_URL")
            or self.DEFAULT_BASE_URL
        )
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None

    @property
    def agent_name(self) -> str:
        return "deepseek"

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
                    message=f"openai package is not installed for DeepSeek: {err}",
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
                                "You are an objective privacy policy compliance auditor. "
                                "Return valid JSON only."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=600,
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

                # HTTP 402 or insufficient balance -> QuotaExhaustedError (no retry)
                if (
                    status_code == 402
                    or "insufficient balance" in err_str
                    or "insufficient_balance" in err_str
                ):
                    raise QuotaExhaustedError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"DeepSeek balance insufficient: {exc}",
                        original_exception=exc,
                    ) from exc

                if status_code == 401 or "authentication" in err_str:
                    raise AuthFailureError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"DeepSeek authentication failed: {exc}",
                        original_exception=exc,
                    ) from exc

                if status_code == 404 or "model_not_found" in err_str:
                    raise ModelUnavailableError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"DeepSeek model '{self.model}' not found or unavailable: {exc}",
                        original_exception=exc,
                    ) from exc

                if status_code == 429:
                    last_error = RateLimitedError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"DeepSeek rate limited: {exc}",
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
                        message=f"DeepSeek connection timeout: {exc}",
                        original_exception=exc,
                    )
                    if attempt < self.max_retries:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    raise last_error from exc

                raise ProviderError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"DeepSeek evaluation error ({type(exc).__name__}): {exc}",
                    original_exception=exc,
                ) from exc

        if last_error:
            raise last_error
        raise ProviderError(
            agent_name=self.agent_name,
            indicator_id=indicator_id,
            message="DeepSeek evaluation failed after retries.",
        )
