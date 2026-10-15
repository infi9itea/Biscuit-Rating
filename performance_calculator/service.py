import json
from pathlib import Path

import pandas as pd

from contests import load_contests
from institution_finder import InstitutionFinder

from .calculators import create

COLUMNS = ["Contest", "Team", "Institution", "Performance"]


def run(
    input_directory: Path,
    contests_directory: Path,
    output_directory: Path,
    institution_database: Path = Path("institution_finder/data/institutions.json"),
) -> Path:
    """Write every team's performance, with its canonical institution name."""
    with (input_directory / "options.json").open() as file:
        options = json.load(file)
    calculator = create(options["calculator"], options["parameters"])
    finder = InstitutionFinder(institution_database)
    rows = []
    for contest in load_contests(contests_directory):
        maximum_solved = max((team.solved for team in contest.teams if team.rank is not None), default=0)
        for team in contest.teams:
            rows.append({
                "Contest": contest.name,
                "Team": team.name,
                "Institution": finder.resolve(team.institution),
                "Performance": (
                    calculator.calculate(team.rank, team.solved, maximum_solved)
                    if team.rank is not None
                    else None
                ),
            })
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / "performances.csv"
    pd.DataFrame(rows, columns=COLUMNS).to_csv(output_path, index=False)
    return output_path
