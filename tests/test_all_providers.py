"""Smoke-test five AI providers without displaying credentials."""

import os
import pytest
from dotenv import load_dotenv

# Load the .env file from the project root.
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

TEST_PROMPT = (
    "Reply with exactly: API CONNECTION SUCCESSFUL"
)


def check_openai():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing")

    from openai import OpenAI
    client = OpenAI(api_key=key, timeout=30.0)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        messages=[{"role": "user", "content": TEST_PROMPT}],
        max_tokens=30,
    )
    return response.choices[0].message.content or ""


def check_gemini():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing")

    from google import genai
    client = genai.Client(api_key=key)
    import time
    last_exc = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
                contents=TEST_PROMPT,
            )
            if response.text:
                return response.text
        except Exception as e:
            last_exc = e
            time.sleep(2.0 * (attempt + 1))

    if last_exc:
        raise last_exc
    raise RuntimeError("Gemini returned an empty response")


def check_deepseek():
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing")

    from openai import OpenAI
    client = OpenAI(
        api_key=key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        timeout=30.0,
    )
    response = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        messages=[{"role": "user", "content": TEST_PROMPT}],
        max_tokens=30,
    )
    return response.choices[0].message.content or ""


def check_groq():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing")

    from openai import OpenAI
    client = OpenAI(
        api_key=key,
        base_url="https://api.groq.com/openai/v1",
        timeout=30.0,
    )
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        messages=[{"role": "user", "content": TEST_PROMPT}],
        max_tokens=100,
    )
    return response.choices[0].message.content or ""


def check_claude():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is missing")

    import anthropic

    model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    client = anthropic.Anthropic(api_key=key, timeout=30.0)
    response = client.messages.create(
        model=model,
        messages=[{"role": "user", "content": TEST_PROMPT}],
        max_tokens=50,
    )
    if not response.content:
        raise RuntimeError("Claude returned empty content blocks")
    return response.content[0].text


def check_openrouter():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is missing")

    from openai import OpenAI
    client = OpenAI(
        api_key=key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        timeout=30.0,
        default_headers={
            "HTTP-Referer": "https://symbolonlaw.ai",
            "X-Title": "Symbolon Law",
        },
    )
    response = client.chat.completions.create(
        model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        messages=[{"role": "user", "content": TEST_PROMPT}],
        max_tokens=30,
    )
    return response.choices[0].message.content or ""


TESTS = [
    ("OpenAI", check_openai),
    ("Gemini", check_gemini),
    ("DeepSeek", check_deepseek),
    ("Groq", check_groq),
    ("Anthropic Claude", check_claude),
    ("OpenRouter", check_openrouter),
]



@pytest.mark.live
def test_live_all_providers_smoke():
    """Opt-in live integration test for all providers."""
    for name, fn in TESTS:
        try:
            res = fn()
            assert res
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code in (400, 402, 429):
                # Quota or balance restriction
                pytest.skip(f"{name} account restriction: {exc}")
            raise


if __name__ == "__main__":
    results = []

    for name, test in TESTS:
        print(f"\nTesting {name}...")
        try:
            answer = test()
            print("PASS:", name)
            print("Response:", answer[:200])
            results.append((name, "PASS"))
        except Exception as exc:
            status_code = getattr(
                getattr(exc, "response", None),
                "status_code",
                None,
            )
            detail = ""
            if status_code == 429:
                detail = " (Quota / credit balance exhausted)"
            elif status_code == 402:
                detail = " (Insufficient balance - account requires payment)"
            elif status_code == 404:
                detail = " (Model not found or invalid account identifier)"

            message = f"HTTP {status_code}{detail}" if status_code else type(exc).__name__
            print("FAIL:", name, "-", message)
            results.append((name, f"FAIL ({message})"))

    print("\n========== SUMMARY ==========")
    for name, status in results:
        print(f"{name}: {status}")

    passed = sum("PASS" in status for _, status in results)
    print(f"\n{passed}/{len(results)} providers passed.")
