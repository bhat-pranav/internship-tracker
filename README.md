# Internship Tracker

Emails me new co-op / internship postings for two searches:

| Pipeline | Term | Where | Companies |
|---|---|---|---|
| **Winter 27** | Jan–Apr 2027 (also "Spring 2027") | US, Canada, remote | any; big names ranked first (⭐) |
| **Summer 27** | May–Aug 2027 | US only | big names only |

Roles: software, data/ML, design/systems/hardware, product, plus quant dev, fintech,
business analyst, solutions/support engineer. The title must say intern, co-op,
student, fellow or apprentice.

**Sponsorship:** postings that explicitly say they won't sponsor (or require US
citizenship / a clearance) are dropped, including Simplify's 🛂 and 🇺🇸 flags. A
posting that says nothing is kept. Canada-only roles skip this check.

## How it works

`watch.py` runs on GitHub Actions and polls three sources:

1. **Company ATS boards** (Greenhouse / Lever / Ashby), the fastest signal. `ats_companies.json`.
2. **SimplifyJobs Summer2027 lists**, main board (summer) and off-season board (has a Terms column).
3. **LinkedIn guest search**, best effort, at most once an hour.

Each posting is classified into a pipeline (`pipelines.py`, `job_filters.py`), deduped
against `snapshots/seen.json`, checked for sponsorship language, and emailed as one message
per pipeline with a `[Winter 27]` / `[Summer 27]` subject prefix. The first run sends one
"initial list" email per pipeline (top 150, big names first) and records everything else
as seen.

## Tuning

- `big_names.txt`: who counts as a big name (edit freely).
- `ats_companies.json`: boards to poll. Add `{"ats": "greenhouse|lever|ashby", "slug": "...", "name": "..."}`.
- `job_filters.py`: role keywords, title exclusions, region and sponsorship patterns.
- `pipelines.py`: pipeline definitions (seasons, regions, big-names-only).

## Setup

1. Enable 2-step verification on the Gmail account, then create an app password.
2. Repo secrets: `MAIL_USERNAME` (Gmail address), `MAIL_PASSWORD` (the app password), `MAIL_TO`.
3. Optional but recommended: trigger `workflow_dispatch` every ~10 minutes from cron-job.org
   (GitHub's own cron is delayed and drops runs).

## Local checks

```bash
python -m unittest discover -s tests
python .github/workflow-scripts/watch.py --dry-run   # prints what would be sent; no email, no state change
```
