import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from contests import ParsedContest, save_contest
from parser import run as parse
from performance_calculator import run as calculate_performances
from performance_calculator.calculators import PerformanceCalculator
from rating_calculator import run as calculate_ratings
from rating_calculator.calculators import RatingCalculator
from score_calculator import run as calculate_scores
from score_calculator.calculators import ScoreCalculator


ROOT = Path(__file__).resolve().parents[1]


def test_calculator_models_are_abstract():
    for model in [PerformanceCalculator, ScoreCalculator, RatingCalculator]:
        with pytest.raises(TypeError):
            model()


def test_calculator_pipeline_generates_declared_outputs():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        contests = root / "contests"
        performances = root / "performances"
        scores = root / "scores"
        ratings = root / "ratings"
        parse(ROOT / "parser/input", contests)
        calculate_performances(ROOT / "performance_calculator/input", contests, performances)
        calculate_scores(ROOT / "score_calculator/input", performances, contests, scores)
        calculate_ratings(ROOT / "rating_calculator/input", scores, contests, ratings)
        assert sorted(path.name for path in performances.iterdir()) == ["performances.csv"]
        assert sorted(path.name for path in scores.iterdir()) == [
            "score_history.csv",
            "score_rank_history.csv",
        ]
        assert sorted(path.name for path in ratings.iterdir()) == [
            "latest_ratings.csv",
            "rating_rank_history.csv",
            "ratings_history.csv",
        ]
        performance_columns = pd.read_csv(performances / "performances.csv").columns.tolist()
        assert performance_columns == ["Contest", "Team", "Institution", "Performance"]
        parsed_team_count = sum(
            len(json.loads(path.read_text())["teams"])
            for path in (contests / "contests").glob("*.json")
        )
        assert len(pd.read_csv(performances / "performances.csv")) == parsed_team_count
        assert "Rating After NDUB 2026" in pd.read_csv(ratings / "ratings_history.csv")
        assert pd.read_csv(ratings / "latest_ratings.csv").columns.tolist() == [
            "Institution",
            "Rating",
        ]


def test_performance_calculator_uses_canonical_institution_names():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        contests = root / "contests"
        output = root / "performances"
        parse(ROOT / "parser/input", contests)
        calculate_performances(ROOT / "performance_calculator/input", contests, output)
        institutions = set(pd.read_csv(output / "performances.csv")["Institution"].dropna())
        assert "BANGLADESH UNIVERSITY OF ENGINEERING AND TECHNOLOGY" in institutions
        assert "BANGLADESH UNIVERSITY OF ENGINEERING & TECHNOLOGY" not in institutions


def write_contests(directory: Path, dates: dict[str, str]) -> None:
    for name, contest_date in dates.items():
        save_contest(directory, ParsedContest(name=name, date=contest_date, parser="TOPH", teams=[]))


def test_score_calculator_orders_contests_newest_first():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        performances = root / "performances"
        performances.mkdir()
        pd.DataFrame([
            ("NEW", "A", "UNIVERSITY OF DHAKA", 4000),
            ("OLD", "A", "UNIVERSITY OF DHAKA", 2000),
            ("OLD", "B", None, 3000),
        ], columns=["Contest", "Team", "Institution", "Performance"]).to_csv(
            performances / "performances.csv",
            index=False,
        )
        write_contests(root / "contests", {"NEW": "2026-02-01", "OLD": "2025-01-01"})
        calculate_scores(ROOT / "score_calculator/input", performances, root / "contests", root / "scores")
        scores = pd.read_csv(root / "scores/score_history.csv")
        assert scores.columns.tolist() == ["Institution", "Score In NEW", "Score In OLD"]
        assert scores["Institution"].tolist() == ["UNIVERSITY OF DHAKA"]
        write_contests(root / "other-contests", {"NEW": "2026-02-01"})
        with pytest.raises(ValueError, match="Missing contest dates: OLD"):
            calculate_scores(ROOT / "score_calculator/input", performances, root / "other-contests", root / "scores")


def test_rating_calculator_fails_when_credited_contest_is_missing():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        scores = root / "scores"
        scores.mkdir()
        pd.DataFrame([{"Institution": "UNIVERSITY OF DHAKA", "Score In OTHER": 4000}]).to_csv(
            scores / "score_history.csv",
            index=False,
        )
        with pytest.raises(ValueError, match="Missing contest scores: CUET 2024"):
            calculate_ratings(ROOT / "rating_calculator/input", scores, ROOT / "parser/output", root / "ratings")
        write_contests(root / "contests", {"OTHER": "2026-01-01"})
        with pytest.raises(ValueError, match="Missing contest data: CUET 2024"):
            calculate_ratings(ROOT / "rating_calculator/input", scores, root / "contests", root / "ratings")
