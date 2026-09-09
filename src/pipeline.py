"""Sequential pipeline (Session 5): audio/text -> transcript -> structured JSON -> vector store.

This stage is intentionally NOT agentic -- it's a fixed sequence of
deterministic steps, which is easier to reason about and cheaper than an
agent for a task with no branching. The one place a decision has to be made
(what to do with each action item) is handed off to the router agent in
agent.py instead.
"""
import json
import uuid

from . import config, stt, summarizer, vector_store
from .logging_utils import timed_stage


def ingest_meeting(*, title: str, date: str, audio_path: str | None = None,
                    transcript_text: str | None = None, meeting_id: str | None = None) -> dict:
    if audio_path is None and transcript_text is None:
        raise ValueError("Provide either audio_path or transcript_text")

    meeting_id = meeting_id or uuid.uuid4().hex[:8]

    with timed_stage("total_ms") as rec:
        rec["meeting_id"] = meeting_id

        if transcript_text is None:
            transcript_text = stt.transcribe(audio_path)["text"]

        summary_json = summarizer.summarize(
            meeting_id=meeting_id, title=title, date=date, transcript_text=transcript_text
        )
        vector_store.add_meeting(meeting_id, title, date, summary_json, transcript_text)

        config.SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = config.SUMMARIES_DIR / f"{meeting_id}.json"
        summary_path.write_text(json.dumps(summary_json, indent=2), encoding="utf-8")

    return {
        "meeting_id": meeting_id,
        "transcript": transcript_text,
        "summary": summary_json,
        "summary_path": str(summary_path),
    }
