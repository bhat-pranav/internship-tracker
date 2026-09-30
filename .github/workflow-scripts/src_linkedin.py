"""LinkedIn public guest job search (no login). Best-effort: LinkedIn rate
limits shared runner IPs, so failures are counted and surfaced, not hidden."""

import html
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Each query runs against each location. Titles are re-filtered locally, so
# these only need to be broad enough to surface candidates.
QUERIES = [
    "Software Engineer Intern",
    "Software Developer Intern",
    "Software Engineering Co-op",
    "Software Developer Co-op",
    "Full Stack Developer Intern",
    "Backend Developer Intern",
    "Frontend Developer Intern",
    "Data Analyst Intern",
    "Data Science Intern",
    "Machine Learning Intern",
    "AI Engineer Intern",
    "Business Intelligence Intern",
    "Product Manager Intern",
    "Associate Product Manager Intern",
    "Systems Engineer Intern",
    "Mechanical Engineering Intern",
    "Quantitative Developer Intern",
    "Business Analyst Intern",
    "Solutions Engineer Intern",
    "Technical Support Engineer Intern",
]
LOCATIONS = ["United States", "Canada"]


def clean_text(raw: str) -> str:
    return WHITESPACE_RE.sub(" ", html.unescape(TAG_RE.sub("", raw))).strip()


def _get(url: str, timeout: int = 15) -> str:
    """GET with a gentle backoff: LinkedIn answers 429 to bursts."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 2:
                raise
            time.sleep(6 * (attempt + 1))


def _cls(tag: str, cls: str, extra: str = "") -> re.Pattern:
    return re.compile(
        rf"<{tag}[^>]*class=\"[^\"]*{cls}[^\"]*\"[^>]*{extra}>(.*?)</{tag}>", re.DOTALL
    )


TITLE_RE = _cls("h3", "base-search-card__title")
COMPANY_RE = _cls("h4", "base-search-card__subtitle")
LOC_RE = _cls("span", "job-search-card__location")
LINK_RE = re.compile(r"<a[^>]*class=\"[^\"]*base-card__full-link[^\"]*\"[^>]*href=\"([^\"]+)\"", re.DOTALL)
ID_RE = re.compile(r"-(\d{8,12})(?:\Z|/|\?)")


def search(query: str, location: str) -> list:
    # f_TPR=r86400: posted within the last 24h (seen-state handles repeats).
    url = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
        f"keywords={urllib.parse.quote(query)}&location={urllib.parse.quote(location)}"
        "&f_TPR=r86400&start=0"
    )
    time.sleep(1.5)
    content = _get(url)
    jobs = []
    for card in content.split("<li")[1:]:
        m_title, m_co, m_link = TITLE_RE.search(card), COMPANY_RE.search(card), LINK_RE.search(card)
        if not (m_title and m_co and m_link):
            continue
        m_loc = LOC_RE.search(card)
        link = m_link.group(1).split("?")[0]
        m_id = ID_RE.search(link)
        jobs.append(
            {
                "id": f"li:{m_id.group(1)}" if m_id else f"li:{link}",
                "company": clean_text(m_co.group(1)),
                "title": clean_text(m_title.group(1)),
                "location": clean_text(m_loc.group(1)) if m_loc else "",
                "url": link,
                "linkedin_id": m_id.group(1) if m_id else None,
                "source": "LinkedIn",
            }
        )
    return jobs


def collect() -> list:
    tasks = [(q, loc) for q in QUERIES for loc in LOCATIONS]
    found, failures = {}, 0
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(search, q, loc): (q, loc) for q, loc in tasks}
        for fut in as_completed(futures):
            try:
                for j in fut.result():
                    found.setdefault(j["id"], j)
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"WARN: LinkedIn {futures[fut]!r} failed: {e}", file=sys.stderr)
    print(f"LinkedIn: {len(found)} cards, {failures}/{len(tasks)} queries failed")
    if failures == len(tasks):
        raise RuntimeError("LinkedIn degraded: every query failed (rate limited?)")
    return list(found.values())


def description(job: dict) -> str:
    if not job.get("linkedin_id"):
        return ""
    time.sleep(1)  # be gentle: only new matches reach here
    page = _get(
        f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job['linkedin_id']}"
    )
    return clean_text(page)
