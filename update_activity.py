"""Update the recent GitHub activity section in README.md."""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any

import requests


GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "itsfourvn").strip()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "").strip()
README_PATH = Path("README.md")
START_MARKER = "<!--START_SECTION:activity-->"
END_MARKER = "<!--END_SECTION:activity-->"


def get_recent_events(limit: int = 15) -> list[str]:
    """Return up to ``limit`` readable public events for the user."""
    if not GITHUB_USERNAME:
        raise RuntimeError("GITHUB_USERNAME must not be empty.")

    headers = {"Accept": "application/vnd.github+json"}
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    response = requests.get(
        f"https://api.github.com/users/{GITHUB_USERNAME}/events/public",
        headers=headers,
        params={"per_page": 100},
        timeout=30,
    )
    response.raise_for_status()

    activity_lines: list[str] = []
    for event in response.json():
        if len(activity_lines) >= limit:
            break
        event_type = event.get("type")
        repo_name = event.get("repo", {}).get("name")
        if not repo_name:
            continue
        repo_name_html = html.escape(repo_name)
        repo_url = f"https://github.com/{repo_name}"
        payload: dict[str, Any] = event.get("payload") or {}

        if event_type == "PushEvent":
            branch = str(payload.get("ref", "refs/heads/main")).split("/")[-1]
            for commit in payload.get("commits") or []:
                if len(activity_lines) >= limit:
                    break
                sha = str(commit.get("sha", ""))
                if not sha:
                    continue
                message = html.escape(str(commit.get("message", "")).splitlines()[0][:120])
                short_sha = html.escape(sha[:7])
                branch_html = html.escape(branch)
                activity_lines.append(
                    f"{len(activity_lines) + 1}. 📦 Pushed [`{short_sha}`]"
                    f"({repo_url}/commit/{sha}) to [`{branch_html}`]"
                    f"({repo_url}/tree/{branch}) in [{repo_name_html}]({repo_url})"
                    f" - {message}"
                )
        elif event_type == "CreateEvent":
            ref_type = payload.get("ref_type")
            if ref_type == "repository":
                activity_lines.append(
                    f"{len(activity_lines) + 1}. ✨ Created repository "
                    f"[{repo_name_html}]({repo_url})"
                )
            elif ref_type == "branch" and payload.get("ref"):
                branch = html.escape(str(payload["ref"]))
                activity_lines.append(
                    f"{len(activity_lines) + 1}. 🌿 Created branch `{branch}` "
                    f"in [{repo_name_html}]({repo_url})"
                )
        elif event_type == "PullRequestEvent" and payload.get("action") == "opened":
            pull_request = payload.get("pull_request") or {}
            number = html.escape(str(pull_request.get("number", "")))
            title = html.escape(str(pull_request.get("title", "Untitled")))
            url = pull_request.get("html_url", repo_url)
            activity_lines.append(
                f"{len(activity_lines) + 1}. 🔀 Opened PR [#{number} {title}]"
                f"({url}) in [{repo_name_html}]({repo_url})"
            )

    return activity_lines


def update_readme(new_activities: list[str]) -> bool:
    """Replace the marked activity block and return whether it changed."""
    if not README_PATH.exists():
        raise FileNotFoundError(f"README not found: {README_PATH}")
    content = README_PATH.read_text(encoding="utf-8")
    start = content.find(START_MARKER)
    end = content.find(END_MARKER, start + len(START_MARKER))
    if start < 0 or end < 0:
        raise ValueError("README activity markers are missing or out of order.")

    activity_block = "\n".join(new_activities) if new_activities else "No recent public activity."
    new_content = content[: start + len(START_MARKER)] + "\n" + activity_block + "\n" + content[end:]
    if new_content == content:
        return False
    README_PATH.write_text(new_content, encoding="utf-8")
    return True


if __name__ == "__main__":
    activities = get_recent_events()
    print("README activity updated." if update_readme(activities) else "README activity is already current.")
