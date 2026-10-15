import json
from pathlib import Path

import pandas as pd

from contests import contest_dates

from .calculators import create


def run(
    input_directory: Path,
    scores_directory: Path,
    contests_directory: Path,
    output_directory: Path,
) -> None:
    """Write each institution's rating after every credited contest."""
    with (input_directory / "credits.json").open() as file:
        credits = {name.upper(): value for name, value in json.load(file).items()}
    with (input_directory / "options.json").open() as file:
        options = json.load(file)
    dates = contest_dates(contests_directory)
    missing = [name for name in credits if name not in dates]
    if missing:
        raise ValueError(f"Missing contest data: {', '.join(missing)}")
    score_history = pd.read_csv(scores_directory / "score_history.csv", index_col="Institution")
    missing = [name for name in credits if f"Score In {name}" not in score_history]
    if missing:
        raise ValueError(f"Missing contest scores: {', '.join(missing)}")
    contests = sorted(credits, key=lambda name: (dates[name], name))

    calculator = create(options["calculator"], options["parameters"])
    ratings = {}
    for position, latest_contest in enumerate(contests):
        ratings[f"Rating After {latest_contest}"] = {
            institution: calculator.calculate(
                {
                    contest: row[f"Score In {contest}"]
                    for contest in contests[:position + 1]
                    if pd.notna(row[f"Score In {contest}"])
                },
                credits,
                dates,
                latest_contest,
            )
            for institution, row in score_history.iterrows()
        }
    ratings = pd.DataFrame(ratings).iloc[:, ::-1].rename_axis("Institution").sort_index()
    ratings = ratings.dropna(how="all")
    ratings = ratings.sort_values(ratings.columns[0], ascending=False, na_position="last", kind="stable")
    ranks = ratings.rank(ascending=False, method="min").astype("Int64")
    ranks.columns = [column.replace("Rating After ", "Rating Rank After ") for column in ranks.columns]
    ratings = ratings.astype(float).round(0).astype("Int64")
    output_directory.mkdir(parents=True, exist_ok=True)
    ratings.to_csv(output_directory / "ratings_history.csv")
    ranks.to_csv(output_directory / "rating_rank_history.csv")
    ratings[[ratings.columns[0]]].set_axis(["Rating"], axis=1).to_csv(output_directory / "latest_ratings.csv")
