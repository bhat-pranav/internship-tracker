"""The two search pipelines and the logic that assigns a posting to them.

Winter 2027 (Jan-Apr, includes "Spring 2027" postings): US + Canada + remote,
any company, big names ranked first.
Summer 2027 (May-Aug): US only, big names only.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from job_filters import (
    regions,
    sponsorship_blocked,
    term_hints,
    term_years,
    wanted_title,
)

BIG_NAMES_PATH = Path(__file__).resolve().parent / "big_names.txt"

TARGET_YEAR = 2027


@dataclass(frozen=True)
class Pipeline:
    key: str
    label: str            # email subject prefix
    seasons: frozenset    # season words that count as this pipeline's term
    allowed_regions: frozenset
    big_names_only: bool


PIPELINES = {
    "winter": Pipeline(
        "winter", "Winter 27", frozenset({"winter", "spring"}),
        frozenset({"US", "CA"}), False,
    ),
    "summer": Pipeline(
        "summer", "Summer 27", frozenset({"summer"}),
        frozenset({"US"}), True,
    ),
}


# ---- big names -------------------------------------------------------------

_SUFFIX_RE = re.compile(r"\b(inc|llc|corp|corporation|ltd|limited|co|plc|gmbh)\b")
_PAREN_RE = re.compile(r"\(.*?\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_company(name: str) -> str:
    s = _PAREN_RE.sub(" ", name.lower().replace("&", " and "))
    s = _NON_ALNUM_RE.sub(" ", s)
    s = _SUFFIX_RE.sub(" ", s)
    return " ".join(s.split())


def _load_big_names() -> tuple:
    """Return (prefix, exact) dicts of normalized name -> is_tier1."""
    prefix, exact = {}, {}
    for line in BIG_NAMES_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tier1 = line.startswith("!")
        line = line.lstrip("!").strip()
        if line.endswith("="):
            exact[normalize_company(line[:-1])] = tier1
        else:
            prefix[normalize_company(line)] = tier1
    return prefix, exact


_PREFIX, _EXACT = _load_big_names()


def company_tier(company: str) -> int:
    """1 = tier 1 (dream company), 2 = big name, 0 = anything else."""
    n = normalize_company(company)
    if not n:
        return 0
    hits = []
    if n in _EXACT:
        hits.append(_EXACT[n])
    if n in _PREFIX:
        hits.append(_PREFIX[n])
    hits.extend(t for p, t in _PREFIX.items() if n.startswith(p + " "))
    if not hits:
        return 0
    return 1 if any(hits) else 2


def is_big_name(company: str) -> bool:
    return company_tier(company) > 0


# ---- classification --------------------------------------------------------

def _term_fits(pipeline: Pipeline, text: str) -> tuple:
    """Return (fits, stated). `stated` is False when the text names no term."""
    hints = term_hints(text)
    if not hints:
        years = term_years(text)
        # A lone year that isn't 2027 ("2026 Intern") is a different cycle.
        if years and TARGET_YEAR not in years:
            return False, False
        return True, False
    for season, year in hints:
        if season in pipeline.seasons and year in (None, TARGET_YEAR):
            return True, True
    return False, True


def classify(job: dict) -> list:
    """Return the pipeline keys this posting belongs to (empty = discard).

    Uses only cheap signals; the description-based sponsorship check runs
    later, on new postings only. Sets job["term_stated"] and job["big"].
    """
    title = job["title"]
    if not wanted_title(title):
        return []
    # Simplify flags ride in the role/company text; sponsorship emoji block here.
    if sponsorship_blocked(job.get("flags", "")):
        return []

    regs = regions(job.get("location", ""))
    if regs == {"OTHER"}:
        return []

    term_text = job.get("terms") or title
    tier = company_tier(job["company"])
    big = tier > 0
    out, stated_any = [], False
    for p in PIPELINES.values():
        if regs and not (regs & p.allowed_regions):
            continue
        if p.big_names_only and not big:
            continue
        fits, stated = _term_fits(p, term_text)
        if not fits:
            continue
        out.append(p.key)
        stated_any = stated_any or stated
    job["term_stated"] = stated_any
    job["big"] = big
    job["tier1"] = tier == 1
    job["regions"] = sorted(regs)
    return out


def needs_sponsorship_check(job: dict) -> bool:
    """Canada-only roles don't need US sponsorship, so skip the check there."""
    regs = set(job.get("regions", []))
    return not (regs == {"CA"})


def sponsorship_ok(job: dict, description: str) -> bool:
    if not needs_sponsorship_check(job):
        return True
    return not sponsorship_blocked(description or "")
