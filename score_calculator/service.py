import json
from pathlib import Path

import pandas as pd

from contests import contest_dates

from .calculators import create


def run(
    input_directory: Path,
    performances_directory: Path,
    contests_directory: Path,
    output_directory: Path,
) -> None:
    """Write each institution's score in every contest, newest contest first."""
    with (input_directory / "options.json").open() as file:
        options = json.load(file)
    calculator = create(options["calculator"], options["parameters"])
    performances = pd.read_csv(performances_directory / "performances.csv")
    dates = contest_dates(contests_directory)
    unknown = sorted(set(performances["Contest"]) - set(dates))
    if unknown:
        raise ValueError(f"Missing contest dates: {', '.join(unknown)}")
    contests = sorted(set(performances["Contest"]), key=lambda name: (dates[name], name))
    # Rows keep contest ranking order, so each group lists the best team first.
    ranked = performances.dropna(subset=["Institution", "Performance"])
    scores = {
        f"Score In {contest}": {
            institution: calculator.calculate(rows["Performance"].tolist())
            for institution, rows in ranked[ranked["Contest"] == contest].groupby("Institution")
        }
        for contest in reversed(contests)
    }
    scores = pd.DataFrame(scores).rename_axis("Institution").sort_index()
    scores = scores.sort_values(scores.columns[0], ascending=False, na_position="last", kind="stable")
    ranks = scores.rank(ascending=False, method="min").astype("Int64")
    ranks.columns = [column.replace("Score In ", "Score Rank In ") for column in ranks.columns]
    output_directory.mkdir(parents=True, exist_ok=True)
    scores.to_csv(output_directory / "score_history.csv")
    ranks.to_csv(output_directory / "score_rank_history.csv")
