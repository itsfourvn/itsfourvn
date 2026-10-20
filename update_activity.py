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


def get_recent_events(limit: int = 25) -> list[str]:
    """Return recent commits across all public repositories of the user."""
    if not GITHUB_USERNAME:
        raise RuntimeError("GITHUB_USERNAME must not be empty.")

    headers = {"Accept": "application/vnd.github+json"}
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    response = requests.get(
        f"https://api.github.com/users/{GITHUB_USERNAME}/repos",
        headers=headers,
        params={"per_page": 100, "sort": "updated", "direction": "desc"},
        timeout=30,
    )
    response.raise_for_status()

    commits: list[dict[str, Any]] = []
    for repo in response.json():
        repo_name = repo.get("full_name")
        if not repo_name:
            continue
        commits_response = requests.get(
            f"https://api.github.com/repos/{repo_name}/commits",
            headers=headers,
            params={"author": GITHUB_USERNAME, "per_page": 10},
            timeout=30,
        )
        if commits_response.status_code == 409:
            continue
        commits_response.raise_for_status()
        for commit in commits_response.json():
            commit_data = commit.get("commit") or {}
            author_date = (commit_data.get("author") or {}).get("date") or ""
            commits.append(
                {
                    "repo_name": repo_name,
                    "repo_url": f"https://github.com/{repo_name}",
                    "branch": repo.get("default_branch") or "main",
                    "sha": commit.get("sha", ""),
                    "url": commit.get("html_url", ""),
                    "message": str(commit_data.get("message", "")).splitlines()[0][:120],
                    "date": author_date,
                }
            )

    commits.sort(key=lambda commit: commit["date"], reverse=True)
    activity_lines: list[str] = []
    for commit in commits[:limit]:
        repo_name_html = html.escape(commit["repo_name"])
        branch_html = html.escape(commit["branch"])
        sha = html.escape(commit["sha"][:7])
        message = html.escape(commit["message"])
        activity_lines.append(
            f"{len(activity_lines) + 1}. 📦 Pushed [`{sha}`]({commit['url']}) "
            f"to [`{branch_html}`]({commit['repo_url']}/tree/{commit['branch']}) "
            f"in [{repo_name_html}]({commit['repo_url']}) - {message}"
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
