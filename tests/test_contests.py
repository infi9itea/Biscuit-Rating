import tempfile
from datetime import date
from pathlib import Path

from contests import ParsedContest, Team, contest_dates, contest_path, load_contests, save_contest


ROOT = Path(__file__).resolve().parents[1]


def test_load_contests_returns_contests_oldest_first():
    contests = load_contests(ROOT / "parser/output")
    dates = [contest.date for contest in contests]
    assert dates == sorted(dates)
    assert all(contest.teams for contest in contests)


def test_saved_contest_round_trips_and_provides_its_date():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        contest = ParsedContest(
            name="TEST 2026",
            date="2026-03-01",
            parser="TOPH",
            teams=[Team(rank=1, name="A", institution="X", solved=3, penalty=10, first_solve_count=1)],
        )
        save_contest(root, contest)
        assert contest_path(root, "TEST 2026") == root / "contests/test-2026.json"
        assert load_contests(root) == [contest]
        assert contest_dates(root) == {"TEST 2026": date(2026, 3, 1)}
