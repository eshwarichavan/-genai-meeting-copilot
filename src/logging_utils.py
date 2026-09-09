"""Per-stage latency + token logging.

Every pipeline stage is wrapped in `timed_stage(name)`. On exit it appends one
JSON line to logs/run_log.jsonl and prints a one-line summary, so cost/latency
(Session 1) is visible for every run instead of only in a demo screenshot.
"""
import contextlib
import json
import time
from datetime import datetime, timezone

from . import config


@contextlib.contextmanager
def timed_stage(name: str):
    record = {"stage": name}
    start = time.perf_counter()
    try:
        yield record
    finally:
        record["ms"] = round((time.perf_counter() - start) * 1000, 1)
        record["ts"] = datetime.now(timezone.utc).isoformat()
        _append_log(record)
        extra = ", ".join(
            f"{k}={v}" for k, v in record.items() if k not in ("stage", "ms", "ts")
        )
        suffix = f" ({extra})" if extra else ""
        print(f"[timing] {name}: {record['ms']} ms{suffix}")


def _append_log(record: dict) -> None:
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.LOGS_DIR / "run_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
