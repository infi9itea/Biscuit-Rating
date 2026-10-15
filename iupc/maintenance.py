import json
import shutil
from datetime import date
from pathlib import Path

from contests import load_contests
from institution_finder import InstitutionFinder
from parser import get_parser


def add_contest(
    root: Path,
    html_paths: list[Path],
    name: str,
    contest_date: str,
    parser: str,
    credit: float = 1,
) -> None:
    """Copy a contest's standings in and register it with the parser and the rating calculator."""
    name = name.strip().upper()
    date.fromisoformat(contest_date)
    get_parser(parser)
    if credit <= 0:
        raise ValueError("Credit must be greater than zero.")
    if not html_paths:
        raise ValueError("At least one contest HTML file is required.")
    contests_path = root / "parser/input/contests.json"
    credits_path = root / "rating_calculator/input/credits.json"
    contests = json.loads(contests_path.read_text())
    credits = json.loads(credits_path.read_text())
    if any(contest["name"].upper() == name for contest in contests["contests"]) or name in credits:
        raise ValueError(f"Contest already exists: {name}")
    destinations = [root / "parser/input/contest_files" / path.name for path in html_paths]
    for source, destination in zip(html_paths, destinations):
        if not source.is_file():
            raise FileNotFoundError(f"Contest HTML not found: {source}")
        if destination.exists():
            raise FileExistsError(f"Contest HTML already exists: {destination}")
    for source, destination in zip(html_paths, destinations):
        shutil.copy2(source, destination)
    contests["contests"].append({
        "name": name,
        "filenames": [path.name for path in html_paths],
        "parser": parser.upper(),
        "date": contest_date,
    })
    credits[name] = credit
    contests_path.write_text(json.dumps(contests, indent=2) + "\n")
    credits_path.write_text(json.dumps(credits, indent=2) + "\n")


def unresolved_institutions(
    contests_directory: Path,
    database_path: Path,
    contest_names: list[str] | None = None,
) -> dict[str, list[str]]:
    """Map each institution name in parsed standings that does not resolve to its contests."""
    finder = InstitutionFinder(database_path)
    contests = load_contests(contests_directory)
    if contest_names:
        selected = {name.upper() for name in contest_names}
        unknown = selected - {contest.name for contest in contests}
        if unknown:
            raise ValueError(f"Parsed contest not found: {', '.join(sorted(unknown))}")
        contests = [contest for contest in contests if contest.name in selected]
    unresolved = {}
    for contest in contests:
        for team in contest.teams:
            if team.institution and finder.resolve(team.institution) is None:
                appearances = unresolved.setdefault(team.institution.upper(), [])
                if contest.name not in appearances:
                    appearances.append(contest.name)
    return dict(sorted(unresolved.items()))
