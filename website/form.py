"""The "Get listed" form: its data from the members file, and its settings."""

import json
from pathlib import Path

import pandas as pd

from members import is_missing

from .theme import institution_name, institution_search_text

# The Google Form questions the page fills in, in order. Their titles become the
# response sheet's column headers, which `biscuit import-form` reads.
QUESTIONS = ["Name", "Handle", "Institution", "Teams"]


def form_data(members_path: Path, contests_path: Path) -> dict:
    """Every institution, and every contest's teams per institution with their known handles."""
    frame = pd.read_csv(members_path, dtype=str, keep_default_na=False)
    member_columns = [column for column in frame.columns if column.startswith("member")]
    contests = json.loads(contests_path.read_text())["contests"]
    teams: dict[str, dict[str, list]] = {}
    for row in frame.to_dict("records"):
        handles = [row[column] for column in member_columns if not is_missing(row[column])]
        teams.setdefault(row["contest"].upper(), {}).setdefault(row["institution"], []).append(
            {"name": row["team_name"], "members": handles}
        )
    institutions = sorted(set(frame["institution"]))
    return {
        "institutions": [{"id": name, "name": institution_name(name), "search": institution_search_text(name)} for name in institutions],
        # Newest first, as people remember them.
        "contests": [
            {
                "name": contest["name"],
                "date": contest["date"],
                "standings": contest.get("standings", ""),
                "teams": {
                    institution: sorted(entries, key=lambda team: team["name"].lower())
                    for institution, entries in teams.get(contest["name"].upper(), {}).items()
                },
            }
            for contest in sorted(contests, key=lambda contest: contest["date"], reverse=True)
        ],
        "questions": QUESTIONS,
    }


def form_settings(path: Path | None) -> dict:
    """Where submissions go: a Google Form's formResponse address and its question entry ids.

    Without an address, the page offers the answers as a CSV file to send instead.
    """
    settings = json.loads(path.read_text()) if path and path.is_file() else {}
    return {"action": settings.get("action", ""), "entries": settings.get("entries", {})}
