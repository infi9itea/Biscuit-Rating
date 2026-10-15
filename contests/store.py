import json
from datetime import date
from pathlib import Path

from .records import ParsedContest


def contest_id(name: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in name).strip("-")


def contest_path(directory: Path, name: str) -> Path:
    return directory / "contests" / f"{contest_id(name)}.json"


def save_contest(directory: Path, contest: ParsedContest) -> None:
    path = contest_path(directory, contest.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as file:
        json.dump(contest.to_dict(), file, indent=4)


def load_contests(directory: Path) -> list[ParsedContest]:
    """Load every contest, oldest first."""
    contests = [
        ParsedContest.from_dict(json.loads(path.read_text()))
        for path in (directory / "contests").glob("*.json")
    ]
    return sorted(contests, key=lambda contest: (contest.date, contest.name))


def contest_dates(directory: Path) -> dict[str, date]:
    """Map each contest's name to its date."""
    return {contest.name: date.fromisoformat(contest.date) for contest in load_contests(directory)}
