import json
from pathlib import Path

import pandas as pd

from contests import load_contests
from members import find_team, load_members
from rating_calculator.calculators import create

PRIOR = "__PRIOR__"
HISTORY_COLUMNS = [
    "Handle", "Contest", "Date", "Team", "Institution", "Rank", "Teams",
    "Solved", "Problems", "First Solves", "Performance", "Rating",
]


def run(
    input_directory: Path,
    members_path: Path,
    performances_directory: Path,
    contests_directory: Path,
    rating_input_directory: Path,
    output_directory: Path,
) -> None:
    """Rate every member by their teams' performances with the Biscuit rating.

    Each person starts with a virtual contest rated `prior_rating`. Its share of a
    rating is prior_credit / (prior_credit + credits of every contest so far), so
    one lucky result cannot put a newcomer at the top, and only competing, not
    waiting, wears the prior down. Real contests still decay against each other.
    """
    options = json.loads((input_directory / "options.json").read_text())
    credits = {name.upper(): value for name, value in json.loads((rating_input_directory / "credits.json").read_text()).items()}
    rating_options = json.loads((rating_input_directory / "options.json").read_text())
    calculator = create(rating_options["calculator"], rating_options["parameters"])

    contests = {contest.name: contest for contest in load_contests(contests_directory)}
    # Team names are text even when they look like numbers or "NA".
    performances = pd.read_csv(
        performances_directory / "performances.csv",
        keep_default_na=False,
        na_values={"Institution": [""], "Performance": [""]},
        dtype={"Team": str},
    )

    def team_results(contest):
        # performances.csv lists each contest's teams in standings order.
        rows = performances[performances["Contest"] == contest.name].to_dict("records")
        if [row["Team"] for row in rows] != [team.name for team in contest.teams]:
            raise ValueError(f"performances.csv does not match the standings of {contest.name}")
        return {id(team): row for team, row in zip(contest.teams, rows)}

    results = {name: team_results(contest) for name, contest in contests.items()}

    entries = {}
    for membership in load_members(members_path):
        contest = contests[membership.contest]
        team = find_team(contest, membership.team_name, membership.institution)
        if team is None:
            raise ValueError(f"No team {membership.team_name!r} in {contest.name}; run `biscuit update` to see the problem.")
        row = results[contest.name][id(team)]
        ranked = [t for t in contest.teams if t.rank is not None]
        key = membership.handle.lower()
        entries.setdefault(key, []).append({
            "Handle": key,
            "Contest": contest.name,
            "Date": contest.date,
            "Team": team.name,
            "Institution": row["Institution"] if isinstance(row["Institution"], str) else team.institution,
            "Rank": team.rank,
            "Teams": len(ranked),
            "Solved": team.solved,
            "Problems": contest.problems or max((t.solved for t in ranked), default=0),
            "First Solves": team.first_solve_count,
            "Performance": row["Performance"],
        })

    history = []
    for key, rows in entries.items():
        rows.sort(key=lambda row: (row["Date"], row["Contest"]))
        dates = {row["Contest"]: pd.Timestamp(row["Date"]).date() for row in rows}
        weights = {**credits, PRIOR: options["prior_credit"]}
        scores = {PRIOR: options["prior_rating"]}
        for row in rows:
            if pd.notna(row["Performance"]) and row["Contest"] in credits:
                scores[row["Contest"]] = row["Performance"]
            # Dated at the latest contest, the prior keeps its full weight; scaling it by
            # how much of the contests' weight is left fixes its share at
            # prior_credit / (prior_credit + total credits).
            dates[PRIOR] = latest = dates[row["Contest"]]
            contests = [contest for contest in scores if contest != PRIOR]
            total = sum(credits[contest] for contest in contests)
            left = sum(calculator.weight(credits[contest], dates[contest], latest) for contest in contests)
            weights[PRIOR] = options["prior_credit"] * (left / total if total else 1)
            row["Rating"] = round(calculator.calculate(scores, weights, dates, row["Contest"]))
            history.append(row)

    output_directory.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(history, columns=HISTORY_COLUMNS)
    if not frame.empty:
        frame["Performance"] = frame["Performance"].round(0).astype("Int64")
        frame["Rank"] = frame["Rank"].astype("Int64")
    frame.sort_values(["Handle", "Date", "Contest"]).to_csv(output_directory / "history.csv", index=False)

    latest = frame.groupby("Handle").agg(
        Rating=("Rating", "last"),
        Peak=("Rating", "max"),
        Contests=("Contest", "size"),
        **{"Last Contest": ("Contest", "last"), "Institution": ("Institution", "last")},
    ) if not frame.empty else pd.DataFrame(columns=["Rating", "Peak", "Contests", "Last Contest", "Institution"])
    latest = latest.sort_values(["Rating", "Peak"], ascending=False, kind="stable")
    latest.rename_axis("Handle").to_csv(output_directory / "ratings.csv")
