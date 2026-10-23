"""Provider health check service with caching, error differentiation, and safe reporting.

Never logs, prints, or exposes API keys or secrets.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from dotenv import find_dotenv, load_dotenv

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


# ============================================================================
# STATUS DEFINITIONS
# ============================================================================

STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
STATUS_READY = "READY"
STATUS_AUTH_ERROR = "AUTH_ERROR"
STATUS_INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
STATUS_RATE_LIMITED = "RATE_LIMITED"
STATUS_MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
STATUS_NETWORK_ERROR = "NETWORK_ERROR"
STATUS_ERROR = "ERROR"
STATUS_UNKNOWN = "UNKNOWN"

STATUS_LABELS = {
    STATUS_READY: "Ready",
    STATUS_NOT_CONFIGURED: "Not Configured",
    STATUS_AUTH_ERROR: "Authentication Failed",
    STATUS_INSUFFICIENT_BALANCE: "Insufficient Balance",
    STATUS_RATE_LIMITED: "Rate Limited",
    STATUS_MODEL_UNAVAILABLE: "Model Unavailable",
    STATUS_NETWORK_ERROR: "Connection Error",
    STATUS_ERROR: "Provider Error",
    STATUS_UNKNOWN: "Not Yet Verified",
}

STATUS_DESCRIPTIONS = {
    STATUS_READY: "API verified and operational.",
    STATUS_NOT_CONFIGURED: "API key is not configured or contains a placeholder value.",
    STATUS_AUTH_ERROR: "Credentials invalid or unauthorized. Verify your API key.",
    STATUS_INSUFFICIENT_BALANCE: "Account credits exhausted or balance too low to serve requests.",
    STATUS_RATE_LIMITED: "Provider rate limit or temporary quota restriction.",
    STATUS_MODEL_UNAVAILABLE: "Configured model is unavailable or unsupported on this account.",
    STATUS_NETWORK_ERROR: "Network connection or request timeout reaching provider API.",
    STATUS_ERROR: "Provider encountered an operational failure.",
    STATUS_UNKNOWN: "Provider has not yet been verified.",
}


@dataclass
class ProviderHealthResult:
    """Detailed health check result for an LLM provider."""

    provider: str
    name: str
    model: str
    configured: bool
    status: str
    status_label: str
    is_available: bool
    last_verified_at: Optional[str] = None
    error: Optional[str] = None
    error_detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def sanitize_message(msg: str) -> str:
    """Strip any accidental key patterns or raw credentials from messages."""
    if not msg:
        return ""
    # Redact common key prefixes
    msg = re.sub(r"sk-[a-zA-Z0-9_\-]{8,}", "[REDACTED_API_KEY]", msg)
    msg = re.sub(r"AIza[a-zA-Z0-9_\-]{15,}", "[REDACTED_API_KEY]", msg)
    msg = re.sub(r"gsk_[a-zA-Z0-9_\-]{15,}", "[REDACTED_API_KEY]", msg)
    return msg.strip()


def is_placeholder(key: Optional[str]) -> bool:
    """Check if an API key string is missing, empty, or a known placeholder."""
    if not key or not key.strip():
        return True
    low = key.strip().lower()
    placeholders = [
        "your_",
        "placeholder",
        "change_me",
        "todo",
        "xxx",
        "sk-placeholder",
        "my_api_key",
        "api_key_here",
    ]
    return any(p in low for p in placeholders)


# ============================================================================
# PROVIDER METADATA
# ============================================================================

PROVIDER_SPECS = {
    "gemini": {
        "name": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "env_model": "GEMINI_MODEL",
        "default_model": "gemini-3.5-flash",
    },
    "groq": {
        "name": "Groq LPU Engine",
        "env_key": "GROQ_API_KEY",
        "env_model": "GROQ_MODEL",
        "default_model": "openai/gpt-oss-20b",
    },
    "claude": {
        "name": "Anthropic Claude",
        "env_key": "ANTHROPIC_API_KEY",
        "env_model": "CLAUDE_MODEL",
        "default_model": "claude-3-5-sonnet-20241022",
    },
    "openai": {
        "name": "OpenAI GPT",
        "env_key": "OPENAI_API_KEY",
        "env_model": "OPENAI_MODEL",
        "default_model": "gpt-4.1-mini",
    },
    "deepseek": {
        "name": "DeepSeek LLM",
        "env_key": "DEEPSEEK_API_KEY",
        "env_model": "DEEPSEEK_MODEL",
        "default_model": "deepseek-chat",
    },
    "openrouter": {
        "name": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "env_model": "OPENROUTER_MODEL",
        "default_model": "openai/gpt-4o-mini",
    },
}


# ============================================================================
# HEALTH CHECK SERVICE
# ============================================================================

class ProviderHealthService:
    """Thread-safe, cached health checking for all 5 AI evaluators."""

    def __init__(self, cache_ttl_seconds: int = 300) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, Tuple[float, ProviderHealthResult]] = {}
        self._lock = threading.Lock()

    def get_configured_model(self, provider_id: str) -> str:
        spec = PROVIDER_SPECS.get(provider_id, {})
        env_model = spec.get("env_model")
        default_model = spec.get("default_model", "default")
        return (os.getenv(env_model) if env_model else None) or default_model

    def is_configured(self, provider_id: str) -> bool:
        spec = PROVIDER_SPECS.get(provider_id, {})
        raw_key = os.getenv(spec.get("env_key", ""))
        return not is_placeholder(raw_key)

    def check_provider(
        self,
        provider_id: str,
        force: bool = False,
    ) -> ProviderHealthResult:
        """Verify health of an individual provider with cache support."""
        if provider_id not in PROVIDER_SPECS:
            return ProviderHealthResult(
                provider=provider_id,
                name=provider_id.title(),
                model="unknown",
                configured=False,
                status=STATUS_NOT_CONFIGURED,
                status_label=STATUS_LABELS[STATUS_NOT_CONFIGURED],
                is_available=False,
                error="Unknown provider",
            )

        with self._lock:
            now = time.time()
            if not force and provider_id in self._cache:
                timestamp, cached_result = self._cache[provider_id]
                if now - timestamp < self.cache_ttl_seconds:
                    return cached_result

        # Perform the actual check
        result = self._perform_health_check(provider_id)

        with self._lock:
            self._cache[provider_id] = (time.time(), result)

        return result

    def _perform_health_check(self, provider_id: str) -> ProviderHealthResult:
        spec = PROVIDER_SPECS[provider_id]
        name = spec["name"]
        model = self.get_configured_model(provider_id)
        raw_key = os.getenv(spec["env_key"])

        # Check 1: Key presence and placeholder check
        if not raw_key or not raw_key.strip():
            return ProviderHealthResult(
                provider=provider_id,
                name=name,
                model=model,
                configured=False,
                status=STATUS_NOT_CONFIGURED,
                status_label=STATUS_LABELS[STATUS_NOT_CONFIGURED],
                is_available=False,
                error=f"{spec['env_key']} is not set.",
                error_detail="Add your API key to the environment or .env file to enable this provider.",
            )

        if is_placeholder(raw_key):
            return ProviderHealthResult(
                provider=provider_id,
                name=name,
                model=model,
                configured=False,
                status=STATUS_NOT_CONFIGURED,
                status_label=STATUS_LABELS[STATUS_NOT_CONFIGURED],
                is_available=False,
                error=f"{spec['env_key']} contains a placeholder value.",
                error_detail="Replace placeholder with a real API key.",
            )

        # Check 2: Execute evaluator probe request
        iso_now = datetime.now(timezone.utc).isoformat()
        evaluator = None

        try:
            if provider_id == "gemini":
                from backend.agents.gemini_evaluator import GeminiEvaluator
                evaluator = GeminiEvaluator(model=model, max_retries=0)
            elif provider_id == "groq":
                from backend.agents.groq_evaluator import GroqEvaluator
                evaluator = GroqEvaluator(model=model, timeout=12.0, max_retries=0)
            elif provider_id == "claude":
                from backend.agents.claude_evaluator import ClaudeEvaluator
                evaluator = ClaudeEvaluator(model=model, timeout=12.0, max_retries=0)
            elif provider_id == "openai":
                from backend.agents.openai_evaluator import OpenAIEvaluator
                evaluator = OpenAIEvaluator(model=model, timeout=12.0, max_retries=0)
            elif provider_id == "deepseek":
                from backend.agents.deepseek_evaluator import DeepSeekEvaluator
                evaluator = DeepSeekEvaluator(model=model, timeout=12.0, max_retries=0)
            elif provider_id == "openrouter":
                from backend.agents.openrouter_evaluator import OpenRouterEvaluator
                evaluator = OpenRouterEvaluator(model=model, timeout=12.0, max_retries=0)
            else:
                raise ValueError(f"Unknown provider: {provider_id}")

            # Send minimal compliance probe
            res = evaluator.evaluate(
                evidence="We collect user email addresses for login security.",
                indicator_id="B7",
                indicator_description="Types of personal data collected",
            )

            # Validate response structure
            if not res or not res.decision or res.confidence < 0.0:
                return ProviderHealthResult(
                    provider=provider_id,
                    name=name,
                    model=model,
                    configured=True,
                    status=STATUS_ERROR,
                    status_label=STATUS_LABELS[STATUS_ERROR],
                    is_available=False,
                    last_verified_at=iso_now,
                    error="Invalid response structure from evaluator.",
                )

            # Success
            return ProviderHealthResult(
                provider=provider_id,
                name=name,
                model=model,
                configured=True,
                status=STATUS_READY,
                status_label=STATUS_LABELS[STATUS_READY],
                is_available=True,
                last_verified_at=iso_now,
                error=None,
                error_detail=None,
            )

        except QuotaExhaustedError as exc:
            msg = sanitize_message(exc.message)
            return ProviderHealthResult(
                provider=provider_id,
                name=name,
                model=model,
                configured=True,
                status=STATUS_INSUFFICIENT_BALANCE,
                status_label=STATUS_LABELS[STATUS_INSUFFICIENT_BALANCE],
                is_available=False,
                last_verified_at=iso_now,
                error="Account credit balance is exhausted or too low.",
                error_detail=msg[:250],
            )

        except AuthFailureError as exc:
            msg = sanitize_message(exc.message)
            return ProviderHealthResult(
                provider=provider_id,
                name=name,
                model=model,
                configured=True,
                status=STATUS_AUTH_ERROR,
                status_label=STATUS_LABELS[STATUS_AUTH_ERROR],
                is_available=False,
                last_verified_at=iso_now,
                error="Authentication failed with provider.",
                error_detail=msg[:250],
            )

        except RateLimitedError as exc:
            msg = sanitize_message(exc.message)
            return ProviderHealthResult(
                provider=provider_id,
                name=name,
                model=model,
                configured=True,
                status=STATUS_RATE_LIMITED,
                status_label=STATUS_LABELS[STATUS_RATE_LIMITED],
                is_available=False,
                last_verified_at=iso_now,
                error="Provider rate limit reached.",
                error_detail=msg[:250],
            )

        except ModelUnavailableError as exc:
            msg = sanitize_message(exc.message)
            return ProviderHealthResult(
                provider=provider_id,
                name=name,
                model=model,
                configured=True,
                status=STATUS_MODEL_UNAVAILABLE,
                status_label=STATUS_LABELS[STATUS_MODEL_UNAVAILABLE],
                is_available=False,
                last_verified_at=iso_now,
                error=f"Model '{model}' is unavailable or not supported.",
                error_detail=msg[:250],
            )

        except TimeoutNetworkError as exc:
            msg = sanitize_message(exc.message)
            return ProviderHealthResult(
                provider=provider_id,
                name=name,
                model=model,
                configured=True,
                status=STATUS_NETWORK_ERROR,
                status_label=STATUS_LABELS[STATUS_NETWORK_ERROR],
                is_available=False,
                last_verified_at=iso_now,
                error="Connection timed out or network error.",
                error_detail=msg[:250],
            )

        except Exception as exc:
            # Fallback classification based on message keywords
            err_str = str(exc)
            low = err_str.lower()
            msg = sanitize_message(err_str)

            if "insufficient_quota" in low or "credit_balance_exhausted" in low or "insufficient balance" in low or "402" in low:
                status = STATUS_INSUFFICIENT_BALANCE
                err_summary = "Account credit balance is exhausted or too low."
            elif "401" in low or "invalid_api_key" in low or "unauthenticated" in low:
                status = STATUS_AUTH_ERROR
                err_summary = "Authentication failed with provider."
            elif "429" in low:
                status = STATUS_RATE_LIMITED
                err_summary = "Provider rate limit reached."
            elif "404" in low or "model_not_found" in low:
                status = STATUS_MODEL_UNAVAILABLE
                err_summary = f"Model '{model}' not found."
            elif "timeout" in low or "connection" in low:
                status = STATUS_NETWORK_ERROR
                err_summary = "Network connection failed."
            else:
                status = STATUS_ERROR
                err_summary = f"{type(exc).__name__}: Operational error occurred."

            return ProviderHealthResult(
                provider=provider_id,
                name=name,
                model=model,
                configured=True,
                status=status,
                status_label=STATUS_LABELS.get(status, "Error"),
                is_available=False,
                last_verified_at=iso_now,
                error=err_summary,
                error_detail=msg[:250],
            )

    def check_all(self, force: bool = False) -> Dict[str, ProviderHealthResult]:
        """Check all 5 providers concurrently in parallel threads and return results dict."""
        from concurrent.futures import ThreadPoolExecutor

        results = {}
        with ThreadPoolExecutor(max_workers=len(PROVIDER_SPECS)) as executor:
            futures = {
                pid: executor.submit(self.check_provider, pid, force)
                for pid in PROVIDER_SPECS
            }
            for pid, future in futures.items():
                try:
                    results[pid] = future.result()
                except Exception as exc:
                    spec = PROVIDER_SPECS.get(pid, {})
                    results[pid] = ProviderHealthResult(
                        provider=pid,
                        name=spec.get("name", pid),
                        model=self.get_configured_model(pid),
                        configured=False,
                        status=STATUS_ERROR,
                        status_label=STATUS_LABELS[STATUS_ERROR],
                        is_available=False,
                        error=f"Health check execution failed: {exc}",
                    )
        return results

    def get_status_payload(self, force: bool = False) -> Dict[str, Any]:
        """Generate full JSON-ready status payload for frontend."""
        checks = self.check_all(force=force)

        providers_dict = {pid: res.to_dict() for pid, res in checks.items()}

        available = [pid for pid, res in checks.items() if res.is_available]
        configured = [pid for pid, res in checks.items() if res.configured]
        unavailable = [pid for pid, res in checks.items() if not res.is_available and res.configured]

        return {
            "status": "online",
            "providers": providers_dict,
            "summary": {
                "total_providers": len(PROVIDER_SPECS),
                "configured_count": len(configured),
                "available_count": len(available),
                "ready_providers": available,
                "unavailable_providers": unavailable,
            },
        }

    def get_available_evaluators(self) -> List[Any]:
        """Instantiate only verified operational evaluators."""
        checks = self.check_all(force=False)
        active_evaluators = []

        if checks.get("gemini") and checks["gemini"].is_available:
            try:
                from backend.agents.gemini_evaluator import GeminiEvaluator
                active_evaluators.append(GeminiEvaluator(model=checks["gemini"].model))
            except Exception:
                pass

        if checks.get("groq") and checks["groq"].is_available:
            try:
                from backend.agents.groq_evaluator import GroqEvaluator
                active_evaluators.append(GroqEvaluator(model=checks["groq"].model))
            except Exception:
                pass

        if checks.get("claude") and checks["claude"].is_available:
            try:
                from backend.agents.claude_evaluator import ClaudeEvaluator
                active_evaluators.append(ClaudeEvaluator(model=checks["claude"].model))
            except Exception:
                pass

        if checks.get("openai") and checks["openai"].is_available:
            try:
                from backend.agents.openai_evaluator import OpenAIEvaluator
                active_evaluators.append(OpenAIEvaluator(model=checks["openai"].model))
            except Exception:
                pass

        if checks.get("deepseek") and checks["deepseek"].is_available:
            try:
                from backend.agents.deepseek_evaluator import DeepSeekEvaluator
                active_evaluators.append(DeepSeekEvaluator(model=checks["deepseek"].model))
            except Exception:
                pass

        if checks.get("openrouter") and checks["openrouter"].is_available:
            try:
                from backend.agents.openrouter_evaluator import OpenRouterEvaluator
                active_evaluators.append(OpenRouterEvaluator(model=checks["openrouter"].model))
            except Exception:
                pass

        return active_evaluators


# Global singleton instance
global_health_service = ProviderHealthService(cache_ttl_seconds=300)
