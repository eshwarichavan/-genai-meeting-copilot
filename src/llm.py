"""Thin wrapper around the Anthropic client.

Deliberately thin: every caller builds and owns its own `messages` array
(Session 1 requirement) instead of hiding it behind a framework abstraction.

Note: the current Messages API for this model family has no `temperature`
parameter (confirmed by calling it directly -- see DESIGN_NOTE.md). Its
replacement determinism knob is `output_config.effort`; structured JSON
output is native via `output_config.format` (a json_schema), rather than
prompt-only JSON instructions.
"""
import anthropic

from . import config

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def chat(messages, system: str | None = None, tools: list | None = None,
         max_tokens: int = 1024, effort: str | None = None,
         response_schema: dict | None = None):
    output_config: dict = {"effort": config.CLAUDE_EFFORT if effort is None else effort}
    if response_schema:
        output_config["format"] = {"type": "json_schema", "schema": response_schema}

    kwargs = dict(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=messages,
        output_config=output_config,
    )
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    return _get_client().messages.create(**kwargs)
