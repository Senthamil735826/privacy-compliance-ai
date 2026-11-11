"""Cohere evaluator for privacy compliance indicators."""

import os
import time
from typing import Optional
import requests
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


class CohereEvaluator(BaseLLMEvaluator):
    """Evaluate privacy policy evidence using Cohere Chat API."""

    DEFAULT_MODEL = "command-r-plus-08-2024"
    DEFAULT_BASE_URL = "https://api.cohere.com/v2/chat"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("COHERE_API_KEY")
        if not self._api_key:
            raise MissingConfigError(
                agent_name=self.agent_name,
                indicator_id="",
                message="COHERE_API_KEY is not configured.",
            )

        self.model = model or os.getenv("COHERE_MODEL", self.DEFAULT_MODEL)
        self.base_url = (
            base_url
            or os.getenv("COHERE_BASE_URL")
            or self.DEFAULT_BASE_URL
        )
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def agent_name(self) -> str:
        return "cohere"

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

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": "PrivacyComplianceAI/0.1.0",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    content_list = data.get("message", {}).get("content", [])
                    raw_text = content_list[0].get("text", "") if content_list else ""
                    return self.parse_and_validate(
                        raw_content=raw_text,
                        indicator_id=indicator_id,
                        original_evidence=evidence,
                    )

                status_code = resp.status_code
                err_text = resp.text
                err_lower = err_text.lower()

                if status_code in (401, 403) or "unauthorized" in err_lower or "invalid api key" in err_lower:
                    raise AuthFailureError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Cohere authentication failed: {err_text}",
                    )

                if status_code == 404 or "not found" in err_lower:
                    raise ModelUnavailableError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Cohere model '{self.model}' not found: {err_text}",
                    )

                if status_code == 429:
                    if "quota" in err_lower or "billing" in err_lower or "credit" in err_lower:
                        raise QuotaExhaustedError(
                            agent_name=self.agent_name,
                            indicator_id=indicator_id,
                            message=f"Cohere quota exhausted: {err_text}",
                        )
                    last_error = RateLimitedError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Cohere rate limited: {err_text}",
                    )
                    if attempt < self.max_retries:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    raise last_error

                raise ProviderError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Cohere API returned status {status_code}: {err_text}",
                )

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = TimeoutNetworkError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Cohere network error: {exc}",
                    original_exception=exc,
                )
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise last_error from exc

        if last_error:
            raise last_error
        raise ProviderError(
            agent_name=self.agent_name,
            indicator_id=indicator_id,
            message="Cohere evaluation failed with an unknown error.",
        )

