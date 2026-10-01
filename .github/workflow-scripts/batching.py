"""Queue of matched roles waiting for the next digest email.

Roles are recorded the moment they're found (so they never repeat), but emailed
in batches: at most one email per pipeline every BATCH_MINUTES.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

PATH = Path("snapshots/pending.json")
BATCH_MINUTES = 120
SLACK_MINUTES = 5  # runs land a few minutes off the 2h mark
KEEP = ("company", "title", "location", "url", "source", "big", "tier1",
        "term_stated", "posted", "deadline", "pipelines", "did")


def now() -> datetime:
    return datetime.now(timezone.utc)


def load() -> dict:
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
        return {"last_sent": data.get("last_sent"), "jobs": data.get("jobs", [])}
    except (OSError, ValueError):
        return {"last_sent": None, "jobs": []}


def save(state: dict) -> None:
    PATH.parent.mkdir(exist_ok=True)
    PATH.write_text(json.dumps(state, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")


def enqueue(state: dict, jobs: list) -> None:
    have = {(j["did"], tuple(j["pipelines"])) for j in state["jobs"]}
    for job in jobs:
        slim = {k: job.get(k) for k in KEEP}
        if (slim["did"], tuple(slim["pipelines"])) not in have:
            state["jobs"].append(slim)


def is_due(state: dict, at: datetime = None) -> bool:
    """True when something is waiting and a full batch window has passed."""
    if not state["jobs"]:
        return False
    at = at or now()
    if not state["last_sent"]:
        return False  # window starts at the first run; nothing was sent yet
    last = datetime.fromisoformat(state["last_sent"])
    return at - last >= timedelta(minutes=BATCH_MINUTES - SLACK_MINUTES)


def mark_sent(state: dict, key: str) -> None:
    """Remove a delivered pipeline from every queued role."""
    kept = []
    for job in state["jobs"]:
        job["pipelines"] = [p for p in job["pipelines"] if p != key]
        if job["pipelines"]:
            kept.append(job)
    state["jobs"] = kept
