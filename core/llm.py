"""Thin wrapper around the Google Gen AI SDK with friendly errors."""

from __future__ import annotations

from typing import Iterator, Sequence

from . import config


class LLMError(Exception):
    """A user-facing AI error."""


def friendly_error(exc: Exception) -> str:
    message = str(exc)
    low = message.lower()
    if "api key" in low or "api_key_invalid" in low or "unauthenticated" in low or "permission denied" in low:
        return (
            "That API key was rejected. Open Settings and check it — keys from Google AI "
            "Studio usually start with 'AIza'."
        )
    if "429" in low or "resource_exhausted" in low or "quota" in low or "rate limit" in low:
        return (
            "The free-tier limit was reached for this model. Wait a minute and retry, or "
            "switch to a lighter model in Settings."
        )
    if "404" in low or "not found" in low:
        return "That model isn't available to your key. Pick a different model in Settings."
    if "connect" in low or "network" in low or "timeout" in low or "getaddrinfo" in low:
        return "Couldn't reach Google. Check your internet connection and try again."
    return f"AI request failed: {message[:300]}"


def _require_key() -> str:
    key = config.get_api_key()
    if not key:
        raise LLMError("No API key is set. Add your free Gemini API key in Settings.")
    return key


def stream_chat(
    messages: Sequence[dict[str, str]],
    system_instruction: str,
    model: str | None = None,
    temperature: float = 0.6,
    max_output_tokens: int = 2048,
) -> Iterator[str]:
    """Yield text chunks for a chat turn."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_require_key())
    model = model or config.DEFAULT_MODEL

    contents = []
    for message in messages:
        role = "user" if message.get("role") == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=str(message.get("content", "")))])
        )

    settings = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )

    yielded = False
    try:
        stream = client.models.generate_content_stream(
            model=model, contents=contents, config=settings
        )
        for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yielded = True
                yield text
    except Exception as exc:  # noqa: BLE001 - surfaced as a friendly message
        raise LLMError(friendly_error(exc)) from exc

    if not yielded:
        raise LLMError(
            "The model returned an empty response. Try again, or switch models in Settings."
        )


def test_connection(api_key: str, model: str) -> str:
    """Make a tiny request and return the model's reply. Raises LLMError on failure."""
    from google import genai
    from google.genai import types

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: OK",
            config=types.GenerateContentConfig(temperature=0, max_output_tokens=10),
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise LLMError("Connected, but the model returned an empty reply.")
        return text
    except LLMError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise LLMError(friendly_error(exc)) from exc
