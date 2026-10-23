"""Anthropic Claude evaluator for privacy compliance indicators."""

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


class ClaudeEvaluator(BaseLLMEvaluator):
    """Evaluate privacy policy evidence using Anthropic Claude models."""

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise MissingConfigError(
                agent_name=self.agent_name,
                indicator_id="",
                message="ANTHROPIC_API_KEY is not configured.",
            )

        self.model = model or os.getenv("CLAUDE_MODEL", self.DEFAULT_MODEL)
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None

    @property
    def agent_name(self) -> str:
        return "claude"

    def _get_client(self):
        """Lazily initialize the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=self._api_key,
                    timeout=self.timeout,
                )
            except ImportError as err:
                raise MissingConfigError(
                    agent_name=self.agent_name,
                    indicator_id="",
                    message=f"anthropic package is not installed: {err}",
                ) from err
        return self._client

    def evaluate(
        self,
        *,
        evidence: str,
        indicator_id: str,
        indicator_description: str,
    ) -> EvaluationResult:
        """Evaluate evidence against the indicator using Claude."""
        # Step 1: Check for empty input (no API call needed)
        if not evidence or not evidence.strip():
            return self.inconclusive_result(
                indicator_id=indicator_id,
                rationale="No policy evidence was provided.",
            )

        # Step 2: Build untrusted data prompt
        prompt = self.build_prompt(
            evidence=evidence,
            indicator_id=indicator_id,
            indicator_description=indicator_description,
        )

        # Step 3: Call API with bounded retries on transient errors
        client = self._get_client()
        import anthropic

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = client.messages.create(
                    model=self.model,
                    max_tokens=800,
                    system=(
                        "You are an objective privacy policy compliance auditor. "
                        "Respond ONLY with valid JSON. Never include commentary, greetings, or markdown outside JSON."
                    ),
                    messages=[{"role": "user", "content": prompt}],
                )

                if not response.content:
                    raise ProviderError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message="Claude returned empty content blocks.",
                    )

                raw_text = response.content[0].text
                return self.parse_and_validate(
                    raw_content=raw_text,
                    indicator_id=indicator_id,
                    original_evidence=evidence,
                )

            except anthropic.AuthenticationError as exc:
                # Do NOT retry authentication failures
                raise AuthFailureError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Claude authentication failed: {exc}",
                    original_exception=exc,
                ) from exc

            except anthropic.BadRequestError as exc:
                msg = str(exc).lower()
                if "credit" in msg or "balance" in msg or "quota" in msg:
                    # Do NOT retry quota exhaustion
                    raise QuotaExhaustedError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Claude quota exhausted: {exc}",
                        original_exception=exc,
                    ) from exc

                raise InvalidResponseError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Claude bad request: {exc}",
                    original_exception=exc,
                ) from exc

            except anthropic.RateLimitError as exc:
                msg = str(exc).lower()
                if "credit" in msg or "balance" in msg or "quota" in msg:
                    # Do NOT retry quota exhaustion
                    raise QuotaExhaustedError(
                        agent_name=self.agent_name,
                        indicator_id=indicator_id,
                        message=f"Claude quota exhausted: {exc}",
                        original_exception=exc,
                    ) from exc

                # Transient rate limit: retry with backoff
                last_error = RateLimitedError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Claude rate limited: {exc}",
                    original_exception=exc,
                )
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise last_error from exc

            except anthropic.NotFoundError as exc:
                # Model does not exist or account lacks access
                raise ModelUnavailableError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Claude model '{self.model}' not found or unavailable: {exc}",
                    original_exception=exc,
                ) from exc

            except (anthropic.APITimeoutError, anthropic.APIConnectionError) as exc:
                last_error = TimeoutNetworkError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Claude connection timeout or network failure: {exc}",
                    original_exception=exc,
                )
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise last_error from exc

            except ProviderError:
                raise

            except Exception as exc:
                raise ProviderError(
                    agent_name=self.agent_name,
                    indicator_id=indicator_id,
                    message=f"Claude evaluation error ({type(exc).__name__}): {exc}",
                    original_exception=exc,
                ) from exc

        if last_error:
            raise last_error
        raise ProviderError(
            agent_name=self.agent_name,
            indicator_id=indicator_id,
            message="Claude evaluation failed after retries.",
        )
