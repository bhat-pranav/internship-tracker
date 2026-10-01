"""Poll every source, sort postings into the Winter/Summer 2027 pipelines,
and email what's new. One process owns snapshots/seen.json.

    python watch.py                 # normal run
    python watch.py --dry-run       # print what would be sent, touch nothing
    (new roles are emailed in batches, one digest per pipeline every 2 hours)
    LINKEDIN=always|never|auto      # auto = only in the first 15 min of the hour
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import alerts
import batching
import src_ats
import src_linkedin
import src_simplify
import tracker
from job_filters import deadline_hint
from pipelines import PIPELINES, classify, sponsorship_ok

SEEN_PATH = Path("snapshots/seen.json")
WHITESPACE_RE = re.compile(r"\s+")

SOURCES = [
    ("ats", src_ats),
    ("simplify", src_simplify),
    ("linkedin", src_linkedin),
]


def display_id(job: dict) -> str:
    """Cross-source fingerprint so the same role isn't emailed once per source."""
    key = f"{job['company']}|{job['title']}|{job['location']}".lower()
    return "d:" + WHITESPACE_RE.sub(" ", key).strip()


def load_seen():
    if SEEN_PATH.exists():
        try:
            return set(json.loads(SEEN_PATH.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            pass
    return None


def save_seen(seen: set) -> None:
    SEEN_PATH.parent.mkdir(exist_ok=True)
    SEEN_PATH.write_text(json.dumps(sorted(seen), indent=0) + "\n", encoding="utf-8")


def linkedin_due() -> bool:
    mode = os.environ.get("LINKEDIN", "auto")
    if mode in ("always", "never"):
        return mode == "always"
    return datetime.now(timezone.utc).minute < 15


def collect_all() -> tuple:
    jobs, failed = [], []
    for name, mod in SOURCES:
        if name == "linkedin" and not linkedin_due():
            print("LinkedIn: skipped this run (hourly)")
            continue
        try:
            jobs.extend(mod.collect())
        except Exception as e:  # noqa: BLE001 - sources are independent
            failed.append(name)
            print(f"::warning::source {name} failed: {e}", file=sys.stderr)
    return jobs, failed


def description_for(job: dict) -> str:
    try:
        if job["source"] == "LinkedIn":
            return src_linkedin.description(job)
        if job["source"] == "Company site":
            return src_ats.description(job)
    except Exception as e:  # noqa: BLE001 - sponsorship check fails open
        print(f"WARN: description fetch failed for {job['url']}: {e}", file=sys.stderr)
    return ""


def main() -> int:
    dry = "--dry-run" in sys.argv
    backfill = "--backfill-tracker" in sys.argv
    seen = load_seen()
    first_run = seen is None
    seen = seen or set()

    raw, failed = collect_all()
    matched, keys_in_run = [], set()
    for job in raw:
        pipes = classify(job)
        if not pipes:
            continue
        job["pipelines"] = pipes
        did = display_id(job)
        if did in keys_in_run:
            continue
        keys_in_run.add(did)
        job["did"] = did
        matched.append(job)

    if backfill:
        # One-off: record every currently open match in the tracker without emailing.
        for job in matched:
            job.setdefault("deadline", "")
        eligible = [j for j in matched if sponsorship_ok(j, j.get("description", ""))]
        tracker.save(tracker.update(tracker.load(), matched, eligible))
        print(f"Tracker backfilled with {len(eligible)} roles")
        return 0

    new = [j for j in matched if j["id"] not in seen and j["did"] not in seen]

    # Sponsorship: only new postings, and only from text we already have on the
    # first run (fetching hundreds of descriptions for the initial list is slow).
    kept = []
    for job in new:
        text = job.get("description") or (
            "" if first_run else description_for(job)
        )
        if sponsorship_ok(job, text):
            job["deadline"] = deadline_hint(text)
            kept.append(job)
    print(f"Sources failed: {failed or 'none'} | raw={len(raw)} matched={len(matched)} "
          f"new={len(new)} after sponsorship={len(kept)} first_run={first_run}")

    # The very first run emails the full open list at once. After that, new roles
    # queue up and go out as one digest per pipeline every batching.BATCH_MINUTES.
    queue = batching.load()
    if first_run:
        outgoing = kept
    else:
        batching.enqueue(queue, kept)
        outgoing = queue["jobs"] if batching.is_due(queue) else []
        if not queue["last_sent"]:
            queue["last_sent"] = batching.now().isoformat()
        print(f"Queued: {len(queue['jobs'])} waiting, due={bool(outgoing)}")

    send_failed = False
    for key, pipeline in PIPELINES.items():
        batch = [j for j in outgoing if key in j["pipelines"]]
        if not batch:
            continue
        if dry:
            print(f"[dry-run] {pipeline.label}: {len(batch)}")
            for j in alerts._sort(batch)[:20]:
                print(f"   {'*' if j['big'] else ' '} {j['company']} | {j['title']} | {j['location']}")
            continue
        if alerts.send_pipeline(pipeline.label, batch, initial=first_run):
            if not first_run:
                batching.mark_sent(queue, key)
        else:
            send_failed = True
    if outgoing and not send_failed and not first_run:
        queue["last_sent"] = batching.now().isoformat()

    if not dry:
        # Roles are tracked and marked seen when found; the email may come later.
        tracker.save(tracker.update(tracker.load(), matched, kept))
        for job in matched:
            seen.add(job["id"])
            seen.add(job["did"])
        save_seen(seen)
        if first_run and not send_failed:
            queue["last_sent"] = batching.now().isoformat()
        batching.save(queue)

    if send_failed:
        print("::error::email failed to send; roles stay queued for the next run", file=sys.stderr)
    return 1 if (send_failed or len(failed) == len(SOURCES)) else 0


if __name__ == "__main__":
    sys.exit(main())
