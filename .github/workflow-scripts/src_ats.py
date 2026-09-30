"""Company ATS boards (Greenhouse / Lever / Ashby): the fastest signal, since
postings show up here before LinkedIn or the Simplify lists pick them up.
Companies live in ats_companies.json.
"""

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

COMPANIES_PATH = Path(__file__).resolve().parent / "ats_companies.json"
TAG_RE = re.compile(r"<[^>]+>")


def fetch_json(url: str):
    last_err = None
    for _ in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - retry once, then report
            last_err = e
    raise last_err


def board_jobs(company: dict) -> list:
    """Return [{id, title, location, url, ...}] for one company's board."""
    ats, slug = company["ats"], company["slug"]
    if ats == "greenhouse":
        data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        return [
            {
                "id": f"g:{slug}:{j['id']}",
                "title": j["title"],
                "location": (j.get("location") or {}).get("name", ""),
                "url": j.get("absolute_url", ""),
                "detail_url": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{j['id']}",
            }
            for j in data.get("jobs", [])
        ]
    if ats == "lever":
        data = fetch_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        return [
            {
                "id": f"l:{slug}:{j.get('id', j.get('hostedUrl', ''))}",
                "title": j.get("text", ""),
                "location": (j.get("categories") or {}).get("location") or "",
                "url": j.get("hostedUrl", ""),
                "description": f"{j.get('descriptionPlain', '')} {j.get('additionalPlain', '')}",
            }
            for j in data
        ]
    if ats == "ashby":
        data = fetch_json(
            "https://api.ashbyhq.com/posting-api/job-board/" + urllib.parse.quote(slug)
        )
        jobs = []
        for j in data.get("jobs", []):
            locs = [j.get("location", "")] + [
                s.get("location", "") for s in j.get("secondaryLocations", [])
            ]
            jobs.append(
                {
                    "id": f"a:{slug}:{j.get('id', j.get('jobUrl', ''))}",
                    "title": j.get("title", ""),
                    "location": " / ".join(x for x in locs if x),
                    "url": j.get("jobUrl") or j.get("applyUrl", ""),
                    "description": j.get("descriptionPlain", ""),
                }
            )
        return jobs
    raise ValueError(f"unknown ats {ats!r}")


def collect() -> list:
    companies = json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))
    jobs, failed = [], []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(board_jobs, c): c for c in companies}
        for fut in as_completed(futures):
            c = futures[fut]
            try:
                board = fut.result()
            except Exception as e:  # noqa: BLE001 - one bad board can't kill the run
                failed.append(c["name"])
                print(f"WARN: {c['ats']}:{c['slug']} failed: {e}", file=sys.stderr)
                continue
            for j in board:
                j["company"] = c["name"]
                j["source"] = "Company site"
                jobs.append(j)
    print(f"ATS: {len(jobs)} postings from {len(companies) - len(failed)}/{len(companies)} boards")
    if len(failed) > len(companies) // 2:
        raise RuntimeError(f"ATS degraded: {len(failed)}/{len(companies)} boards failed")
    return jobs


def description(job: dict) -> str:
    """Posting text for the sponsorship check (fetched only for new matches)."""
    if job.get("description"):
        return job["description"]
    if job.get("detail_url"):
        content = fetch_json(job["detail_url"]).get("content", "")
        return TAG_RE.sub(" ", html.unescape(content))
    return ""
