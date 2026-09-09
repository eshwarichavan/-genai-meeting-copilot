"""Command-line entry point. Run with: python -m src.cli <command> ...

See README.md for the full walkthrough used in the demo recording.
"""
import argparse
import json

from . import config, pipeline, qa, agent, mcp_client

SEED_META = [
    {"file": "meeting_1_billing_migration.txt", "title": "Billing Migration Sync", "date": "2026-08-04"},
    {"file": "meeting_2_sprint_planning.txt", "title": "Sprint 42 Planning", "date": "2026-08-11"},
    {"file": "meeting_3_design_review.txt", "title": "Checkout Redesign Review", "date": "2026-08-18"},
    {"file": "meeting_4_incident_postmortem.txt", "title": "Payments Outage Postmortem", "date": "2026-08-25"},
]


def cmd_ingest_seed(args):
    for meta in SEED_META:
        path = config.SEED_MEETINGS_DIR / meta["file"]
        text = path.read_text(encoding="utf-8")
        result = pipeline.ingest_meeting(
            title=meta["title"], date=meta["date"], transcript_text=text, meeting_id=path.stem
        )
        print(f"\nIngested seed meeting '{meta['title']}' -> meeting_id={result['meeting_id']}")
        print(json.dumps(result["summary"], indent=2))


def cmd_ingest_audio(args):
    result = pipeline.ingest_meeting(title=args.title, date=args.date, audio_path=args.audio)
    print(f"\nmeeting_id={result['meeting_id']}")
    print("\nTRANSCRIPT:\n" + result["transcript"])
    print("\nSTRUCTURED SUMMARY:\n" + json.dumps(result["summary"], indent=2))

    if args.act:
        act_result = agent.run_agent(
            result["meeting_id"], args.title, result["summary"]["action_items"], auto_approve=args.yes
        )
        print("\nAGENT RESULT:\n" + json.dumps(act_result, indent=2, default=str))


def cmd_ask(args):
    result = qa.answer(args.question)
    print("\nANSWER:\n" + result["answer"])
    print("\nSOURCES: " + (", ".join(result["sources"]) if result["sources"] else "none"))
    if result["tokens"]:
        print(f"TOKENS: input={result['tokens']['input']} output={result['tokens']['output']}")


def cmd_act(args):
    summary_path = config.SUMMARIES_DIR / f"{args.meeting_id}.json"
    if not summary_path.exists():
        raise SystemExit(f"No summary found for meeting_id={args.meeting_id} at {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    result = agent.run_agent(
        args.meeting_id, summary["title"], summary["action_items"], auto_approve=args.yes
    )
    print(json.dumps(result, indent=2, default=str))


def cmd_mcp_tools(args):
    for tool in mcp_client.list_tools():
        print(f"- {tool.name}: {tool.description}")


def cmd_eval(args):
    eval_path = config.BASE_DIR / "eval" / "eval_set.json"
    cases = json.loads(eval_path.read_text(encoding="utf-8"))
    results = []
    passed = 0
    for case in cases:
        result = qa.answer(case["question"])
        ok = case["expected_contains"].lower() in result["answer"].lower()
        passed += int(ok)
        results.append({
            "id": case["id"], "question": case["question"], "expected_contains": case["expected_contains"],
            "actual_answer": result["answer"], "auto_pass": ok,
        })
        print(f"[{'PASS' if ok else 'CHECK'}] {case['id']}: {case['question']}")

    out_path = config.BASE_DIR / "eval" / "eval_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n{passed}/{len(cases)} auto-passed (heuristic substring match). "
          f"Full results written to {out_path}. Read eval/eval_set.md before "
          f"trusting this number -- some 'CHECK' rows may still be correct answers.")


def cmd_demo(args):
    print("=== 1. Ingesting seed meetings ===")
    cmd_ingest_seed(args)

    audio_files = sorted(
        p for p in config.DATA_DIR.joinpath("recordings").glob("*")
        if p.suffix.lower() in (".wav", ".mp3", ".m4a", ".flac", ".ogg")
    )
    real_meeting_id = None
    if audio_files:
        print(f"\n=== 2. Ingesting your real recording: {audio_files[0].name} ===")
        result = pipeline.ingest_meeting(
            title=args.title or "My Recorded Meeting", date=args.date or "2026-09-09",
            audio_path=str(audio_files[0]),
        )
        real_meeting_id = result["meeting_id"]
        print(json.dumps(result["summary"], indent=2))
    else:
        print("\n=== 2. Skipped: drop a real recording into data/recordings/ first ===")

    print("\n=== 3. Asking cross-meeting questions ===")
    for question in [
        "What did we decide about the billing migration?",
        "What's on the roadmap for the payments team, according to these meetings?",
    ]:
        print(f"\nQ: {question}")
        cmd_ask(argparse.Namespace(question=question))

    print("\n=== 4. Running the action agent (Router pattern + MCP tools) ===")
    target_meeting_id = real_meeting_id or SEED_META[0]["file"][:-4]
    cmd_act(argparse.Namespace(meeting_id=target_meeting_id, yes=args.yes))


def build_parser():
    parser = argparse.ArgumentParser(prog="meeting-copilot")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest-seed", help="Ingest the bundled seed meeting transcripts")
    p.set_defaults(func=cmd_ingest_seed)

    p = sub.add_parser("ingest-audio", help="Transcribe and ingest a real audio recording")
    p.add_argument("audio")
    p.add_argument("--title", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--act", action="store_true", help="Also run the action agent right after ingest")
    p.add_argument("--yes", action="store_true", help="Auto-approve calendar actions (skip HITL prompt)")
    p.set_defaults(func=cmd_ingest_audio)

    p = sub.add_parser("ask", help="Ask a question across all ingested meetings")
    p.add_argument("question")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("act", help="Run the MCP action agent for a previously ingested meeting")
    p.add_argument("meeting_id")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_act)

    p = sub.add_parser("mcp-tools", help="List tools exposed by the MCP server (proves the MCP round trip)")
    p.set_defaults(func=cmd_mcp_tools)

    p = sub.add_parser("eval", help="Run the evaluation question set in eval/eval_set.json")
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("demo", help="Run the full scripted end-to-end demo (use this for the recording)")
    p.add_argument("--title", default=None)
    p.add_argument("--date", default=None)
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_demo)

    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
