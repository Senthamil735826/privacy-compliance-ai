"""Typed provider error hierarchy for privacy compliance evaluators.

Failures are operational errors, NOT opinions. They must never be converted
into inconclusive compliance decisions or counted in voting denominators.
"""

from typing import Optional


class ProviderError(Exception):
    """Base exception for all LLM provider operational failures."""

    def __init__(
        self,
        agent_name: str,
        indicator_id: str,
        message: str,
        original_exception: Optional[Exception] = None,
    ) -> None:
        self.agent_name = agent_name
        self.indicator_id = indicator_id
        self.message = message
        self.original_exception = original_exception
        super().__init__(f"[{agent_name}] {indicator_id}: {message}")

    def to_dict(self) -> dict:
        return {
            "error_type": self.__class__.__name__,
            "agent_name": self.agent_name,
            "indicator_id": self.indicator_id,
            "message": self.message,
        }


class MissingConfigError(ProviderError):
    """Provider API key or required configuration is not provided."""
    pass


class AuthFailureError(ProviderError):
    """Provider rejected credentials (HTTP 401 / Invalid API Key). Do not retry."""
    pass


class QuotaExhaustedError(ProviderError):
    """Account credit balance is exhausted or billing quota exceeded (e.g. HTTP 429 credit_balance_exhausted or HTTP 402). Do not retry."""
    pass


class RateLimitedError(ProviderError):
    """Transient rate limit reached (HTTP 429 concurrency / request limit). May retry with backoff."""
    pass


class TimeoutNetworkError(ProviderError):
    """Network connection timeout or unreachable endpoint."""
    pass


class ModelUnavailableError(ProviderError):
    """The specified model was not found (HTTP 404) or is not accessible."""
    pass


class InvalidResponseError(ProviderError):
    """Provider returned empty, unparseable, or schema-violating output."""
    pass
