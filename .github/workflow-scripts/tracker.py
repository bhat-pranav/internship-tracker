"""docs/jobs.json: every role that has been alerted, for the dashboard in docs/.

Statuses (applied, interview, ...) live in the browser, not here; this file
only records what was found, when, and whether it is still listed.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

PATH = Path("docs/jobs.json")
FIELDS = ("company", "title", "location", "url", "source", "posted", "deadline")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load() -> dict:
    try:
        return {j["id"]: j for j in json.loads(PATH.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return {}


def update(store: dict, matched: list, alerted: list) -> dict:
    """`matched` = everything currently listed (refresh last_seen);
    `alerted` = jobs just emailed (add new entries)."""
    today = _today()
    seen_now = {j["did"] for j in matched}
    for entry in store.values():
        if entry["id"] in seen_now:
            entry["last_seen"] = today
    for job in alerted:
        did = job["did"]
        entry = store.get(did)
        if entry is None:
            entry = store[did] = {"id": did, "first_seen": today}
        for f in FIELDS:
            if job.get(f):
                entry[f] = job[f]
        entry["pipelines"] = sorted(set(entry.get("pipelines", [])) | set(job["pipelines"]))
        entry["big"] = bool(job.get("big"))
        entry["tier1"] = bool(job.get("tier1"))
        entry["term_stated"] = bool(job.get("term_stated"))
        entry["last_seen"] = today
    return store


def save(store: dict) -> None:
    PATH.parent.mkdir(exist_ok=True)
    rows = sorted(store.values(), key=lambda j: (j["first_seen"], j["company"].lower()), reverse=True)
    PATH.write_text(json.dumps(rows, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
