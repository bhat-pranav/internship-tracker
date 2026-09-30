"""SimplifyJobs Summer2027-Internships boards (main + off-season).

The workflow downloads README.md / README-Off-Season.md next to the repo root;
this module parses their HTML tables into job dicts. The main board is the
summer list; the off-season board has a Terms column ("Winter 2027, Spring 2027").
"""

import html
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

TABLE_RE = re.compile(r"<table>(.*?)</table>", re.DOTALL)
TR_RE = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
TH_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.DOTALL)
COMPANY_RE = re.compile(r'<a\s+href="(https://simplify\.jobs/c/[^"]+)"[^>]*>([^<]+)</a>')
APPLY_RE = re.compile(r'<a\s+href="([^"]+)"[^>]*>\s*<img[^>]*alt="Apply"', re.IGNORECASE)
POSTING_RE = re.compile(r"https://simplify\.jobs/p/([0-9a-fA-F-]{36})")
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

BOARDS = [
    ("current-main.md", "Simplify (main)", "Summer 2027"),
    ("current-offseason.md", "Simplify (off-season)", None),
]


def strip_html(fragment: str) -> str:
    for br in ("<br>", "<br/>", "<br />"):
        fragment = fragment.replace(br, " · ")
    fragment = html.unescape(TAG_RE.sub("", fragment))
    return WHITESPACE_RE.sub(" ", fragment).strip()


AGE_RE = re.compile(r"(\d+)\s*(d|w|mo|y)", re.I)


def _age_to_date(age: str) -> str:
    """"0d" / "3w" / "2mo" -> an approximate posted date."""
    m = AGE_RE.search(age)
    if not m:
        return ""
    days = int(m.group(1)) * {"d": 1, "w": 7, "mo": 30, "y": 365}[m.group(2).lower()]
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def _row_id(block: str, apply_url: str, company: str, role: str, location: str) -> str:
    # The simplify.jobs/p/<uuid> link survives edits to the row's text.
    m = POSTING_RE.search(block)
    if m:
        return "p:" + m.group(1).lower()
    if apply_url:
        return "a:" + apply_url.split("?")[0].rstrip("/")
    return "t:" + WHITESPACE_RE.sub(" ", f"{company}|{role}|{location}".lower()).strip()


def parse_board(path: str, source: str, default_terms) -> list:
    if not os.path.exists(path):
        return []
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    jobs, seen_ids = [], set()
    for table in TABLE_RE.findall(text):
        headers = [strip_html(h).lower() for h in TH_RE.findall(table)]
        terms_idx = headers.index("terms") if "terms" in headers else None
        age_idx = headers.index("age") if "age" in headers else None
        last_company = None
        for block in TR_RE.findall(table):
            tds = TD_RE.findall(block)
            if len(tds) < 4:
                continue
            first = strip_html(tds[0])
            m = COMPANY_RE.search(tds[0])
            if m:
                company = last_company = strip_html(m.group(2))
            elif "↳" in first and last_company:
                company = last_company
            else:
                continue
            role = strip_html(tds[1])
            location = strip_html(tds[2])
            apply_match = APPLY_RE.search(block)
            if not apply_match or "🔒" in block:  # closed or no link
                continue
            apply_url = apply_match.group(1)
            rid = _row_id(block, apply_url, company, role, location)
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            terms = strip_html(tds[terms_idx]) if terms_idx is not None else default_terms
            jobs.append(
                {
                    "id": rid,
                    "company": company,
                    "title": re.sub(r"[🎓🛂🇺🇸]", "", role).strip(),
                    "location": location,
                    "url": apply_url,
                    "posted": _age_to_date(strip_html(tds[age_idx])) if age_idx is not None and age_idx < len(tds) else "",
                    "terms": terms,
                    "flags": f"{first} {role}",  # 🛂 / 🇺🇸 sponsorship markers
                    "source": source,
                }
            )
    return jobs


def collect() -> list:
    jobs = []
    for path, source, default_terms in BOARDS:
        jobs.extend(parse_board(path, source, default_terms))
    return jobs
