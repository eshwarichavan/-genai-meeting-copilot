"""Session 4 (agent loop) + Session 5 (architecture pattern: Router).

Thought -> Action -> Observation, implemented with Claude's native tool-use
blocks: the model's own text is the Thought, a `tool_use` block is the
Action, and the `tool_result` we feed back is the Observation. The model is
instructed to act as a router -- deciding per action item whether it needs
only a durable record (write_action_items) or also a calendar follow-up
(create_calendar_event) -- rather than always taking the same path.

Safety: a hard MAX_ITERATIONS cap, every tool call logged, and a
human-in-the-loop confirmation before the one irreversible-ish action
(creating a calendar event).
"""
import json

from . import config, llm, mcp_client
from .logging_utils import timed_stage

TOOLS = [
    {
        "name": "write_action_items",
        "description": (
            "Persist a meeting's action items to a JSON file on disk. Call this "
            "exactly ONCE per meeting with the full list of action items, even "
            "if some of those items will also get a calendar event."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "meeting_id": {"type": "string"},
                "title": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "owner": {"type": ["string", "null"]},
                            "task": {"type": "string"},
                            "due_date": {"type": ["string", "null"]},
                        },
                        "required": ["task"],
                    },
                },
            },
            "required": ["meeting_id", "title", "items"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": (
            "Create a calendar follow-up for ONE action item that has a concrete "
            "due_date. Call this once per such item; skip items with no due_date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string"},
                "attendee": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["title", "date", "attendee"],
        },
    },
]

SYSTEM_PROMPT = """You are an action-taking agent for a meeting-notes copilot.
Given a meeting's structured summary, decide which tools to call so the action
items are not lost. Act as a router over the two available tools:
- ALWAYS call write_action_items exactly once with the full list of action items.
- For EACH action item that has a non-null due_date, ALSO call create_calendar_event
  for that single item (one call per item with a due_date).
- Do not invent owners, tasks, or dates that are not in the provided summary.
- Once you have made all necessary tool calls, reply with a short plain-text
  confirmation and stop calling tools."""


def run_agent(meeting_id: str, title: str, action_items: list, auto_approve: bool = False,
              max_iterations: int | None = None) -> dict:
    max_iterations = max_iterations or config.MAX_ITERATIONS
    messages = [{
        "role": "user",
        "content": (
            f"Meeting: {title} (id={meeting_id})\n"
            f"Action items:\n{json.dumps(action_items, indent=2)}\n\n"
            "Take the appropriate tool actions now."
        ),
    }]
    call_log = []

    for iteration in range(1, max_iterations + 1):
        with timed_stage("llm_ms") as rec:
            rec["stage_detail"] = "agent"
            rec["iteration"] = iteration
            resp = llm.chat(messages, system=SYSTEM_PROMPT, tools=TOOLS, max_tokens=1024)
            rec["input_tokens"] = resp.usage.input_tokens
            rec["output_tokens"] = resp.usage.output_tokens

        messages.append({"role": "assistant", "content": resp.content})
        tool_uses = [block for block in resp.content if block.type == "tool_use"]

        if not tool_uses:
            final_text = "".join(block.text for block in resp.content if block.type == "text")
            return {
                "status": "done",
                "iterations": iteration,
                "final_message": final_text,
                "log": call_log,
            }

        tool_results = []
        for tu in tool_uses:
            entry = {"iteration": iteration, "tool": tu.name, "input": tu.input, "tool_use_id": tu.id}

            if tu.name == "create_calendar_event" and not auto_approve:
                confirm = input(f"[HITL] Create calendar event {tu.input!r}? [y/N] ").strip().lower()
                if confirm != "y":
                    entry["result"] = "skipped by user (human-in-the-loop declined)"
                    call_log.append(entry)
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": tu.id, "content": entry["result"]}
                    )
                    continue

            with timed_stage("mcp_tool_ms") as rec:
                rec["tool"] = tu.name
                try:
                    result_text = mcp_client.call_tool(tu.name, tu.input)
                except Exception as exc:  # tool errors are observations, not crashes
                    result_text = f"ERROR calling {tu.name}: {exc}"

            entry["result"] = result_text
            call_log.append(entry)
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": result_text})

        messages.append({"role": "user", "content": tool_results})

    return {"status": "max_iterations_reached", "iterations": max_iterations, "log": call_log}
