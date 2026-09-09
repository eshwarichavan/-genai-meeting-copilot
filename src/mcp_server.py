"""MCP server (Session 6): exposes the two real-world actions the agent can take.

Run standalone for debugging with: python -m src.mcp_server
Normally it is spawned as a subprocess by mcp_client.py over stdio.
"""
import json
from datetime import datetime, timezone

from mcp.server.mcpserver import MCPServer as FastMCP

from . import config

mcp = FastMCP("meeting-copilot-tools")


@mcp.tool()
def write_action_items(meeting_id: str, title: str, items: list[dict]) -> str:
    """Persist a meeting's action items to a JSON file on disk so they survive
    outside the vector store. Call this once per meeting with the full item list."""
    config.ACTION_ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.ACTION_ITEMS_DIR / f"{meeting_id}.json"
    payload = {
        "meeting_id": meeting_id,
        "title": title,
        "items": items,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return f"Wrote {len(items)} action item(s) to {path}"


@mcp.tool()
def create_calendar_event(title: str, date: str, attendee: str, description: str = "") -> str:
    """Create a calendar follow-up entry (append-only local store) for a single
    action item that has a concrete due date."""
    config.CALENDAR_DIR.mkdir(parents=True, exist_ok=True)
    path = config.CALENDAR_DIR / "calendar.jsonl"
    event = {
        "title": title,
        "date": date,
        "attendee": attendee,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    return f"Created calendar event '{title}' on {date} for {attendee}"


if __name__ == "__main__":
    mcp.run()
