import re
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

import pandas as pd

from contests import ParsedContest, Team, load_contests

BASE_COLUMNS = ["contest", "institution", "team_name"]
HANDLE = re.compile(r"^[A-Za-z0-9_.-]{3,24}$")


@dataclass(frozen=True)
class Membership:
    handle: str
    contest: str
    team_name: str
    institution: str


def is_missing(value: str) -> bool:
    """An empty cell means the handle was not provided."""
    return not value.strip()


def _member_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column.startswith("member")]


def _read(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.columns = [column.strip() for column in frame.columns]
    return frame.apply(lambda column: column.str.strip())


def load_members(path: Path) -> list[Membership]:
    """One membership per listed handle. Empty handle cells are skipped."""
    frame = _read(path)
    return [
        Membership(row[column], row["contest"].upper(), row["team_name"], row["institution"])
        for _, row in frame.iterrows()
        for column in _member_columns(frame)
        if not is_missing(row[column])
    ]


def rename_handles(path: Path, renames: dict[str, str]) -> int:
    """Write each handle in `renames` (matched ignoring case) as its new handle.

    Keeps one handle per person: a renamed Codeforces account, or a handle
    typed in the wrong letter case, becomes the current handle everywhere.
    Returns the number of cells changed.
    """
    lookup = {old.lower(): new for old, new in renames.items()}
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    changed = 0
    for column in _member_columns(frame):
        new = frame[column].map(lambda handle: lookup.get(handle.lower(), handle))
        changed += int((new != frame[column]).sum())
        frame[column] = new
    if changed:
        frame.to_csv(path, index=False)
    return changed


def find_team(contest: ParsedContest, team_name: str, institution: str) -> Team | None:
    """The team with this name; the institution breaks ties between equal names."""
    named = [team for team in contest.teams if team.name == team_name]
    if len(named) > 1:
        named = [team for team in named if team.institution.upper() == institution.upper()]
    return named[0] if len(named) == 1 else None


def validate(path: Path, contests_directory: Path) -> list[str]:
    """Return every problem in the members file."""
    frame = _read(path)
    missing = [column for column in BASE_COLUMNS if column not in frame.columns]
    if missing or not _member_columns(frame):
        return [f"{path.name} needs the columns {', '.join(BASE_COLUMNS)} and at least one member column."]
    contests = {contest.name: contest for contest in load_contests(contests_directory)}
    errors = []
    seen = {}
    for line, row in zip(range(2, len(frame) + 2), frame.to_dict("records")):
        where = f"{path.name} line {line}"
        contest = contests.get(row["contest"].upper())
        if contest is None:
            errors.append(f"{where}: unknown contest {row['contest']!r}.")
            continue
        same_name = [team for team in contest.teams if team.name == row["team_name"]]
        if same_name and find_team(contest, row["team_name"], row["institution"]) is None:
            errors.append(
                f"{where}: {len(same_name)} teams in {contest.name} are named {row['team_name']!r}; "
                f"its institution {row['institution']!r} does not single one out."
            )
        elif not same_name:
            names = sorted({team.name for team in contest.teams})
            suggestion = get_close_matches(row["team_name"], names, n=1)
            hint = f" Did you mean {suggestion[0]!r}?" if suggestion else ""
            errors.append(f"{where}: no team {row['team_name']!r} in {contest.name}.{hint}")
        for column in _member_columns(frame):
            handle = row[column]
            if is_missing(handle):
                continue
            if not HANDLE.match(handle):
                errors.append(f"{where}: {handle!r} is not a valid Codeforces handle.")
            key = (contest.name, handle.lower())
            if key in seen:
                errors.append(f"{where}: {handle} is already listed for {contest.name} on line {seen[key]}.")
            seen[key] = line
    return errors
