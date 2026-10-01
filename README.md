# Internship Tracker

Emails me new co-op / internship postings for two searches:

| Pipeline | Term | Where | Companies |
|---|---|---|---|
| **Winter 27** | Jan–Apr 2027 (also "Spring 2027") | US, Canada, remote | any; big names ranked first (⭐) |
| **Summer 27** | May–Aug 2027 | US only | big names only |

Roles: software, data/ML, design/systems/hardware, product, plus quant dev, fintech,
business analyst, solutions/support engineer. The title must say intern, co-op,
student, fellow or apprentice.

**Citizenship:** postings that require US citizenship, a security clearance or ITAR status
(including Simplify's 🇺🇸 flag) are dropped. Everything else passes, including roles that say
they don't sponsor visas. Canada-only roles skip this check.

## How it works

`watch.py` runs on GitHub Actions and polls three sources:

1. **Company ATS boards** (Greenhouse / Lever / Ashby), the fastest signal. `ats_companies.json`.
2. **SimplifyJobs Summer2027 lists**, main board (summer) and off-season board (has a Terms column).
3. **LinkedIn guest search**, best effort, at most once an hour.

Each posting is classified into a pipeline (`pipelines.py`, `job_filters.py`), deduped
against `snapshots/seen.json`, checked for citizenship requirements, and emailed as one message
per pipeline with a `[Winter 27]` / `[Summer 27]` subject prefix. New roles are collected and sent
as one digest per pipeline every 2 hours (`batching.py`, `BATCH_MINUTES`); they appear on the tracker page
as soon as they're found. The first run sends one
"initial list" email per pipeline (top 150, big names first) and records everything else
as seen.

## Extras

- **Tracker page** (`docs/`, served by GitHub Pages): every alerted role, with a status
  (New / Interested / Applied / OA / Interview / Offer / Rejected / Skip) and a notes box per role.
  Filters for pipeline, tier and search; sort by newest, deadline or company. Statuses are saved in
  the browser only; use Export/Import to move them between devices.
- **Freshness and deadlines:** each alert shows how old the posting is and any "rolling" /
  "closes <date>" text found in the posting.
- **Tier 1:** prefix a line in `big_names.txt` with `!` to mark a dream company. Its alerts get a
  ⭐⭐ subject line and sit at the top of the email.
- **Canada:** extra Canadian company boards, plus city-level co-op searches on LinkedIn
  (Toronto, Waterloo, Vancouver, Montreal).

## Tuning

- `big_names.txt`: who counts as a big name (edit freely).
- `ats_companies.json`: boards to poll. Add `{"ats": "greenhouse|lever|ashby", "slug": "...", "name": "..."}`.
- `job_filters.py`: role keywords, title exclusions, region and citizenship patterns.
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
python .github/workflow-scripts/watch.py --backfill-tracker   # rebuild docs/jobs.json from what is open now
```
