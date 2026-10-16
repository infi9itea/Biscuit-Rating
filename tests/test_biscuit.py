import json
import shutil
import tempfile
from pathlib import Path

import pytest

from biscuit.cli import main
from biscuit.maintenance import add_contest, unresolved_institutions
from biscuit.pipeline import STAGES, mermaid, stale_stages, update
from biscuit.validate import validate


ROOT = Path(__file__).resolve().parents[1]
DATA = [
    "parser",
    "performance_calculator",
    "score_calculator",
    "rating_calculator",
    "institution_finder",
    "contests",
    "members",
    "codeforces",
    "contestant_rating",
    "biscuit",
]


def copy_repository(destination: Path) -> None:
    for directory in DATA:
        shutil.copytree(ROOT / directory, destination / directory, ignore=shutil.ignore_patterns("__pycache__"))


def test_repository_data_is_valid_and_up_to_date():
    assert validate(ROOT) == []
    assert stale_stages(ROOT) == []


def test_stage_dependencies_are_declared_in_order():
    seen = set()
    for stage in STAGES:
        assert set(stage.dependencies) <= seen
        seen.add(stage.name)
    assert "contest_data --> score_calculator" in mermaid()


def add_alt_name_to_copy(root: Path, institution: str, alt_name: str) -> None:
    database = root / "institution_finder/data/institutions.json"
    data = json.loads(database.read_text())
    next(value for value in data["institutions"] if value["name"] == institution)["alt_names"].append(alt_name)
    database.write_text(json.dumps(data, indent=2))


def test_institution_change_reruns_only_what_it_affects():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        copy_repository(root)
        assert stale_stages(root) == []
        downstream = ["performance_calculator", "score_calculator", "rating_calculator", "contestant_rating"]

        # A name no team uses leaves the performances unchanged, so the
        # stages after it are not rerun.
        add_alt_name_to_copy(root, "UNIVERSITY OF DHAKA", "UNUSED ALTERNATE NAME")
        assert stale_stages(root) == downstream
        assert update(root, log=lambda message: None) == ["performance_calculator"]

        # A misspelling used in UU 2025 now counts toward the ratings.
        add_alt_name_to_copy(
            root,
            "INTERNATIONAL ISLAMIC UNIVERSITY CHITTAGONG",
            "INTERNATIONAL ISLMAIC UNIVERSITY CHITTAGONG",
        )
        assert update(root, log=lambda message: None) == downstream
        assert stale_stages(root) == []


def test_validation_catches_inconsistent_data():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        copy_repository(root)
        credits_path = root / "rating_calculator/input/credits.json"
        credits = json.loads(credits_path.read_text())
        credits["UNKNOWN 2030"] = 1
        credits_path.write_text(json.dumps(credits))
        (root / "parser/input/contest_files/unused.html").write_text("<table></table>")
        errors = validate(root)
        assert any("UNKNOWN 2030" in error for error in errors)
        assert any("unused.html" in error for error in errors)
        with pytest.raises(ValueError, match="Data validation failed"):
            update(root)


def test_add_contest_registers_parser_input_and_credit():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "parser/input/contest_files").mkdir(parents=True)
        (root / "parser/input/contests.json").write_text('{"contests": []}')
        (root / "rating_calculator/input").mkdir(parents=True)
        (root / "rating_calculator/input/credits.json").write_text("{}")
        pages = [root / "page1.html", root / "page2.html"]
        for page in pages:
            page.write_text("<!-- saved from url=(0036)https://toph.co/c/test/standings -->\n<table></table>")
        add_contest(root, pages, "Test Contest", "2026-06-01", "toph", 1.5)
        contest = json.loads((root / "parser/input/contests.json").read_text())["contests"][0]
        assert contest == {
            "name": "TEST CONTEST",
            "filenames": ["page1.html", "page2.html"],
            "parser": "TOPH",
            "date": "2026-06-01",
            "standings": "https://toph.co/c/test/standings",
        }
        assert json.loads((root / "rating_calculator/input/credits.json").read_text()) == {"TEST CONTEST": 1.5}
        assert (root / "parser/input/contest_files/page2.html").exists()
        with pytest.raises(ValueError, match="already exists"):
            add_contest(root, [root / "page1.html"], "test contest", "2026-06-01", "TOPH")


def test_unresolved_institutions_lists_unknown_names_per_contest():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "contests").mkdir()
        team = {"rank": 1, "name": "T", "solved": 1, "penalty": 0, "first_solve_count": 0}
        (root / "contests/test.json").write_text(json.dumps({
            "name": "TEST 2026",
            "date": "2026-01-01",
            "parser": "TOPH",
            "teams": [
                {**team, "institution": "KNOWN UNIVERSITY"},
                {**team, "institution": "UNKNOWN COLLEGE"},
                {**team, "institution": ""},
            ],
        }))
        database = root / "institutions.json"
        database.write_text('{"institutions": [{"name": "KNOWN UNIVERSITY", "alt_names": []}]}')
        assert unresolved_institutions(root, database) == {"UNKNOWN COLLEGE": ["TEST 2026"]}
        assert unresolved_institutions(root, database, ["test 2026"]) == {"UNKNOWN COLLEGE": ["TEST 2026"]}
        with pytest.raises(ValueError, match="OTHER 2026"):
            unresolved_institutions(root, database, ["OTHER 2026"])


def test_cli_check_and_errors(capsys):
    main(["--root", str(ROOT), "update", "--check"])
    assert "up to date" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="Example inputs"):
        main(["--root", str(ROOT), "distribute", "--input", "slot_distributor/input/example"])
