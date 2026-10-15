import json
import tempfile
from pathlib import Path

import pytest

from institution_finder import InstitutionFinder, add_alt_name, add_institution, resolve_interactively, validate


ROOT = Path(__file__).resolve().parents[1]


def test_resolves_canonical_and_alternate_names():
    finder = InstitutionFinder(ROOT / "institution_finder/data/institutions.json")
    canonical = "BANGLADESH UNIVERSITY OF ENGINEERING AND TECHNOLOGY"
    assert finder.resolve(canonical) == canonical
    assert finder.resolve("BANGLADESH UNIVERSITY OF ENGINEERING & TECHNOLOGY") == canonical


def test_add_institution_and_alt_name():
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "institutions.json"
        database.write_text('{"institutions": []}')
        add_institution("Test University", database)
        add_alt_name("Test University", "Test U", database)
        assert json.loads(database.read_text())["institutions"] == [
            {"name": "TEST UNIVERSITY", "alt_names": ["TEST U"]},
        ]
        with pytest.raises(ValueError, match="already exists"):
            add_institution("TEST U", database)
        assert validate(database) == []


def test_validate_reports_shared_names():
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "institutions.json"
        database.write_text(json.dumps({"institutions": [
            {"name": "A UNIVERSITY", "alt_names": ["SHARED"]},
            {"name": "B UNIVERSITY", "alt_names": ["SHARED", "lowercase"]},
        ]}))
        errors = validate(database)
        assert any("belongs to both" in error for error in errors)
        assert any("uppercase" in error for error in errors)


def test_interactive_resolution_updates_database_or_reports_typos():
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "institutions.json"
        database.write_text('{"institutions": [{"name": "TEST UNIVERSITY", "alt_names": []}]}')
        answers = iter(["1", "t1", "n"])
        typo_fixes, changed = resolve_interactively(
            ["TEST UNIV", "TEST UNIVERSTY", "BRAND NEW UNIVERSITY"],
            database,
            allow_typo_fix=True,
            ask=lambda prompt: next(answers),
            show=lambda message: None,
        )
        assert changed
        assert typo_fixes == {"TEST UNIVERSTY": "TEST UNIVERSITY"}
        assert json.loads(database.read_text())["institutions"] == [
            {"name": "BRAND NEW UNIVERSITY", "alt_names": []},
            {"name": "TEST UNIVERSITY", "alt_names": ["TEST UNIV"]},
        ]
