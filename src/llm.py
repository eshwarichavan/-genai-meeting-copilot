"""Thin wrapper around the OpenAI-compatible client, pointed at OpenRouter.

Deliberately thin: every caller builds and owns its own `messages` array
(Session 1 requirement) instead of hiding it behind a framework abstraction.
Routed through OpenRouter rather than a provider-native SDK because that is
the credential actually available for this project -- see DESIGN_NOTE.md.
Still defaults to a Claude model (`anthropic/claude-haiku-4.5`), just reached
through OpenRouter's OpenAI-compatible chat.completions API, which is why the
`messages`/`tools`/`response_format` shapes below are OpenAI-style rather
than Anthropic-native content blocks.
"""
from openai import OpenAI

from . import config

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not config.OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        default_headers = {}
        if config.OPENROUTER_SITE_URL:
            default_headers["HTTP-Referer"] = config.OPENROUTER_SITE_URL
        if config.OPENROUTER_APP_NAME:
            default_headers["X-Title"] = config.OPENROUTER_APP_NAME
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.OPENROUTER_API_KEY,
            default_headers=default_headers or None,
        )
    return _client


def chat(messages, system: str | None = None, tools: list | None = None,
         max_tokens: int = 1024, temperature: float | None = None,
         response_schema: dict | None = None, schema_name: str = "response"):
    full_messages = ([{"role": "system", "content": system}] if system else []) + messages

    kwargs = dict(
        model=config.OPENROUTER_MODEL,
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=config.TEMPERATURE if temperature is None else temperature,
    )
    if tools:
        kwargs["tools"] = tools
    if response_schema:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": response_schema},
        }
    return _get_client().chat.completions.create(**kwargs)
