"""Render and send one email per pipeline."""

import html
import os

from notifier import send_email

DIGEST_CAP = 150


def _logs_url() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    return f"{server}/{repo}/actions" if repo else "https://github.com"


def _sort(jobs: list) -> list:
    return sorted(jobs, key=lambda j: (not j.get("big"), j["company"].lower(), j["title"].lower()))


def _tags(job: dict) -> str:
    tags = [job["source"]]
    if not job.get("term_stated"):
        tags.append("term not stated")
    return " · ".join(tags)


def subject(label: str, jobs: list, initial: bool) -> str:
    if initial:
        return f"[{label}] Initial list: {len(jobs)} open roles"
    unique = list(dict.fromkeys(j["company"] for j in _sort(jobs)))
    preview = ", ".join(unique[:3])
    more = f" +{len(unique) - 3} more" if len(unique) > 3 else ""
    return f"[{label}] {len(jobs)} new: {preview}{more}"


def render_html(label: str, jobs: list, total: int, initial: bool) -> str:
    rows = []
    for j in jobs:
        star = "⭐ " if j.get("big") else ""
        rows.append(
            "<tr>"
            '<td style="padding:10px 0;border-bottom:1px solid #eee;vertical-align:top;">'
            f'<div style="font-weight:600;font-size:14px;color:#111;">{star}{html.escape(j["company"])}</div>'
            f'<div style="font-size:14px;color:#333;margin-top:2px;">{html.escape(j["title"])}</div>'
            f'<div style="font-size:12px;color:#666;margin-top:2px;">'
            f'{html.escape(j["location"] or "Location not listed")}</div>'
            f'<div style="font-size:11px;color:#999;margin-top:2px;">{html.escape(_tags(j))}</div>'
            "</td>"
            '<td style="padding:10px 0;border-bottom:1px solid #eee;vertical-align:middle;'
            'text-align:right;white-space:nowrap;">'
            f'<a href="{html.escape(j["url"])}" style="display:inline-block;padding:6px 14px;'
            "background:#2563eb;color:#fff;text-decoration:none;border-radius:4px;"
            'font-size:13px;font-weight:600;">Apply</a></td></tr>'
        )
    head = f"{total} open roles right now" if initial else f"{len(jobs)} new role{'s' if len(jobs) != 1 else ''}"
    note = ""
    if len(jobs) < total:
        note = (
            f'<p style="font-size:12px;color:#888;">Showing the top {len(jobs)} of {total} '
            "(big names first).</p>"
        )
    return (
        "<html><body style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        'sans-serif;background:#f7f7f7;margin:0;padding:20px;">'
        '<div style="max-width:640px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;">'
        f'<h1 style="font-size:18px;margin:0 0 4px;color:#111;">{html.escape(label)}: {head}</h1>'
        '<p style="font-size:12px;color:#888;margin:0 0 8px;">⭐ = big-name company. '
        "Sponsorship is checked against the posting text; roles that say they won't "
        "sponsor are dropped, silence is kept.</p>"
        f"{note}"
        '<table cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;">'
        + "\n".join(rows)
        + "</table>"
        '<hr style="border:0;border-top:1px solid #eee;margin:20px 0 8px;">'
        f'<p style="color:#aaa;font-size:11px;margin:0;">internship-tracker · '
        f'<a href="{_logs_url()}" style="color:#aaa;">workflow logs</a></p>'
        "</div></body></html>"
    )


def render_plain(label: str, jobs: list) -> str:
    lines = [f"[{label}] {len(jobs)} role(s)", ""]
    for j in jobs:
        lines.append(f"{'* ' if j.get('big') else ''}{j['company']} - {j['title']}")
        lines.append(f"    {j['location'] or '(location not listed)'}  [{_tags(j)}]")
        lines.append(f"    {j['url']}")
    return "\n".join(lines)


def send_pipeline(label: str, jobs: list, initial: bool = False) -> bool:
    ordered = _sort(jobs)
    shown = ordered[:DIGEST_CAP] if initial else ordered
    return send_email(
        subject(label, ordered, initial),
        render_html(label, shown, len(ordered), initial),
        render_plain(label, shown),
        from_name=f"Internship Tracker ({label})",
    )
