"""Transcript -> structured JSON summary.

Session 2: structured JSON output, grounded in the transcript. Enforced two
ways -- schema-constrained output (`response_format: json_schema`, strict)
so malformed JSON is rejected before it reaches this code, plus a one-shot
few-shot example so the model also learns the *content* shape (which fields
to fill vs. leave null), not just the syntax.
"""
import json
import re

from .logging_utils import timed_stage
from . import llm

SYSTEM_PROMPT = """You are a precise meeting-notes summarizer. You are given a raw \
meeting transcript. Produce a summary plus a list of action items.

Only include action items that are explicitly stated or clearly implied in the \
transcript. Never invent an owner, task, or due date that is not present in the \
transcript. If there are no action items, return an empty list."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "2-4 sentence summary of what was discussed and decided"},
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "owner": {"type": ["string", "null"]},
                    "task": {"type": "string"},
                    "due_date": {"type": ["string", "null"], "description": "date/day mentioned, or null"},
                },
                "required": ["task"],
            },
        },
    },
    "required": ["summary", "action_items"],
}

_FEWSHOT_TRANSCRIPT = (
    "Priya: Quick sync on the mobile crash. Raj, can you ship the hotfix by Friday?\n"
    "Raj: Yeah, I'll have the patch out by Friday.\n"
    "Priya: Great, and someone needs to update the status page.\n"
    "Sam: I'll do the status page today.\n"
    "Priya: Perfect, let's reconvene Monday."
)

_FEWSHOT_JSON = json.dumps(
    {
        "summary": (
            "The team discussed the mobile crash bug. Raj will ship a hotfix and "
            "Sam will update the status page; the group will reconvene Monday."
        ),
        "action_items": [
            {"owner": "Raj", "task": "Ship the hotfix for the mobile crash", "due_date": "Friday"},
            {"owner": "Sam", "task": "Update the status page", "due_date": "today"},
        ],
    },
    indent=2,
)


def summarize(meeting_id: str, title: str, date: str, transcript_text: str) -> dict:
    messages = [
        {"role": "user", "content": f"Transcript:\n{_FEWSHOT_TRANSCRIPT}"},
        {"role": "assistant", "content": _FEWSHOT_JSON},
        {"role": "user", "content": f"Transcript:\n{transcript_text}"},
    ]

    with timed_stage("llm_ms") as rec:
        resp = llm.chat(
            messages, system=SYSTEM_PROMPT, max_tokens=800,
            response_schema=RESPONSE_SCHEMA, schema_name="meeting_summary",
        )
        rec["stage_detail"] = "summarize"
        rec["input_tokens"] = resp.usage.prompt_tokens
        rec["output_tokens"] = resp.usage.completion_tokens

    raw_text = resp.choices[0].message.content.strip()
    parsed = _parse_json(raw_text)
    parsed["meeting_id"] = meeting_id
    parsed["title"] = title
    parsed["date"] = date
    parsed.setdefault("action_items", [])
    return parsed


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Model did not return valid JSON:\n{text}")
