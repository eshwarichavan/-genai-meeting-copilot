# Your real recording goes here

Drop one 2-3 minute audio file here (`.wav`, `.mp3`, `.m4a`, `.flac`, or `.ogg`) —
a standup, a design discussion, or you reading out a fake meeting out loud.
This is the recording the assignment requires you to make yourself; the four
transcripts in `data/seed_meetings/` are text-only seed data used to bootstrap
the vector store so cross-meeting retrieval has something to search.

`python -m src.cli demo` automatically picks up the first audio file it finds
in this folder. `python -m src.cli ingest-audio <path> --title "..." --date "..."`
lets you ingest a specific file directly.
