# Meeting-Notes Copilot

Turns a short meeting recording into a searchable, actionable record: local
speech-to-text -> structured JSON summary -> a vector store that builds up
over time -> grounded Q&A across every past meeting -> an agent that files
the action items and creates calendar follow-ups through a real MCP tool.

**Demo recording**: [`demo_recording.mp4`](./demo_recording.mp4) (5:04) -- a
full end-to-end run narrated live, including the real audio recording below
actually being transcribed.

## Architecture

```
 audio file
     |
     v
 [ STT: faster-whisper, local, no API key ]           stt_ms
     |
     v
 [ Summarizer: Claude (via OpenRouter), few-shot -> structured JSON ] llm_ms
     |
     v
 [ Chroma vector store: chunk + embed + upsert ]      (per-meeting)
     |
     v
 [ RAG Q&A: top-k retrieve -> cite -> answer          retrieval_ms, llm_ms
   or "I can't find this in the provided context" ]
     |
     v
 [ Router agent: tool-calling loop, MAX_ITERATIONS ]   llm_ms (per iteration)
     |         |
     |         +--> write_action_items  --\
     |                                     |--> MCP server (stdio JSON-RPC)  mcp_tool_ms
     +--> create_calendar_event (HITL) --/
```

Ingestion is a **sequential pipeline** (fixed steps, no branching needed).
The action step is a **router**: the agent decides per action item whether
it needs only a durable record or also a calendar event, and reaches both
tools only through a real MCP server (`src/mcp_server.py`), not a hard-coded
function call. See `DESIGN_NOTE.md` for why.

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
# then edit .env and set OPENROUTER_API_KEY (get one at https://openrouter.ai/keys)
```

LLM calls go through [OpenRouter](https://openrouter.ai)'s OpenAI-compatible
API rather than a provider-native SDK, and default to `anthropic/claude-haiku-4.5`
(configurable via `OPENROUTER_MODEL` in `.env`) -- see `DESIGN_NOTE.md` for why.

First run downloads two small models automatically (needs internet once):
a `faster-whisper` "base" STT model (~140MB) and Chroma's default embedding
model (~80MB). Both then run fully offline.

## Add your own recording

Drop a 2-3 minute audio file (`.wav`/`.mp3`/`.m4a`/`.flac`/`.ogg`) into
`data/recordings/` -- a standup, a design discussion, or you reading out a
fake meeting. See `data/recordings/README.md`. The four transcripts in
`data/seed_meetings/` are text seed data (allowed by the assignment for
bootstrapping retrieval) so cross-meeting Q&A has more than one meeting to
search across.

## Run it

```bash
# 1. Seed the vector store with the four sample meetings
python -m src.cli ingest-seed

# 2. Transcribe + ingest your real recording
python -m src.cli ingest-audio "data/recordings/your_file.wav" --title "Standup" --date "2026-09-09"

# 3. Ask grounded questions across every ingested meeting
python -m src.cli ask "What did we decide about the billing migration?"
python -m src.cli ask "Did we discuss quarterly revenue targets?"   # should refuse

# 4. Run the router agent + MCP tools for a meeting's action items
python -m src.cli act meeting_1_billing_migration
# (prompts for confirmation before creating a calendar event -- HITL)

# Or run everything in one scripted pass (use this for your demo recording):
python -m src.cli demo

# Prove the MCP round trip is real, not a hard-coded call:
python -m src.cli mcp-tools

# Run the evaluation set:
python -m src.cli eval
```

Every stage logs its latency (and token counts, where an LLM call is
involved) to `logs/run_log.jsonl` and prints a one-line summary, e.g.:

```
[timing] stt_ms: 812.4 ms (audio_path=..., duration_s=142.3, language=en)
[timing] llm_ms: 640.1 ms (stage_detail=summarize, input_tokens=612, output_tokens=180)
[timing] total_ms: 1502.7 ms (meeting_id=a1b2c3d4)
```

## Where each session lives

| Session | Where |
|---|---|
| 1. Foundations | `src/config.py` (API key from env, never committed), `src/llm.py` (hand-managed `messages` array, deliberately chosen low `temperature`) |
| 2. Prompting | `src/summarizer.py` (schema-constrained JSON output + a few-shot example) |
| 3. RAG | `src/vector_store.py` (chunking, embeddings, Chroma), `src/qa.py` (top-k retrieval, cited grounded answers) |
| 4. Agents | `src/agent.py` (tool-calling loop, correct `tool_call_id` handling, every call logged, `MAX_ITERATIONS` cap) |
| 5. Architectures | Sequential pipeline (`src/pipeline.py`) + Router (`src/agent.py`) -- see `DESIGN_NOTE.md` |
| 6. MCP | `src/mcp_server.py` (MCP tools) + `src/mcp_client.py` (real stdio JSON-RPC client, not a direct function call) |
| 7. Audio/Visual | `src/stt.py` (faster-whisper), latency logged via `logging_utils.timed_stage` |

## Safety

- Every tool call goes through the MCP server and is logged (tool name, input, result).
- `MAX_ITERATIONS` (default 6, see `.env.example`) hard-caps the agent loop.
- `create_calendar_event` requires a human-in-the-loop `y/N` confirmation
  unless you pass `--yes` (used to make `demo` non-interactive).

## Repo layout

```
src/               pipeline, agent, MCP server/client, CLI
data/seed_meetings/    4 sample transcripts (text seed data)
data/recordings/       drop your own real audio here
data/summaries/        generated structured JSON per meeting (gitignored)
data/action_items/     generated MCP tool output (gitignored)
data/calendar/         generated MCP tool output (gitignored)
chroma_db/             generated vector store (gitignored)
logs/                  generated timing/token logs (gitignored)
eval/                  eval_set.json (input) + eval_set.md (write-up)
DESIGN_NOTE.md         ~300-word design note (personalize before submitting)
```
