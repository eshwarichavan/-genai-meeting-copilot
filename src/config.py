"""Central configuration. All values are overridable via environment variables / .env."""
import os
import pathlib

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
SUMMARIES_DIR = DATA_DIR / "summaries"
ACTION_ITEMS_DIR = DATA_DIR / "action_items"
CALENDAR_DIR = DATA_DIR / "calendar"
SEED_MEETINGS_DIR = DATA_DIR / "seed_meetings"
CHROMA_DIR = BASE_DIR / os.getenv("CHROMA_DIR", "chroma_db")

# Session 1: API key lives only in the environment, never in source.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
# The current Messages API for this model family has no `temperature` param;
# `effort` is its replacement sampling/determinism knob (see DESIGN_NOTE.md).
# Chosen deliberately low: summarization/extraction and the action agent both
# need consistent, non-creative output, not exploration.
CLAUDE_EFFORT = os.getenv("CLAUDE_EFFORT", "low")

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

COLLECTION_NAME = "meetings"
TOP_K = int(os.getenv("TOP_K", "4"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "6"))
