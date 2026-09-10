"""Central configuration. All values are overridable via environment variables / .env."""
import os
import pathlib

from dotenv import load_dotenv

# override=True: .env is the source of truth for this project's own keys,
# so a stray placeholder already sitting in the shell environment can't
# silently shadow the real key a developer put in .env.
load_dotenv(override=True)

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
SUMMARIES_DIR = DATA_DIR / "summaries"
ACTION_ITEMS_DIR = DATA_DIR / "action_items"
CALENDAR_DIR = DATA_DIR / "calendar"
SEED_MEETINGS_DIR = DATA_DIR / "seed_meetings"
CHROMA_DIR = BASE_DIR / os.getenv("CHROMA_DIR", "chroma_db")

# Session 1: API key lives only in the environment, never in source.
# LLM calls are routed through OpenRouter's OpenAI-compatible API (the
# credential available for this project) rather than a provider-native SDK.
# See DESIGN_NOTE.md for why.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-haiku-4.5")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "meeting-notes-copilot")
# Chosen deliberately low: summarization/extraction and the action agent both
# need consistent, non-creative output, not exploration.
TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.2"))

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

COLLECTION_NAME = "meetings"
TOP_K = int(os.getenv("TOP_K", "4"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "6"))
