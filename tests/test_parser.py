import json
import tempfile
from pathlib import Path

from parser import run
from parser.parsers import Parser


ROOT = Path(__file__).resolve().parents[1]


def test_parser_model_is_abstract():
    try:
        Parser()
    except TypeError:
        return
    raise AssertionError("Parser must be abstract")


def test_parser_generates_and_reuses_contest_database():
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        count = len(json.loads((ROOT / "parser/input/contests.json").read_text())["contests"])
        first = run(ROOT / "parser/input", output)
        second = run(ROOT / "parser/input", output)
        assert first == {"parsed": count, "skipped": 0}
        assert second == {"parsed": 0, "skipped": count}
        assert len(list((output / "contests").glob("*.json"))) == count
        assert not (output / "contests.json").exists()


def test_toph_parser_detects_supported_layouts():
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        run(ROOT / "parser/input", output)
        legacy = (output / "contests" / "cuet-2024.json").read_text()
        current = (output / "contests" / "ndub-2026.json").read_text()
        assert '"parser": "TOPH"' in legacy
        assert '"parser": "TOPH"' in current

