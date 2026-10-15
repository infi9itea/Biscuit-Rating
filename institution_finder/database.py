import json
from pathlib import Path


def _load(database_path: Path) -> dict:
    with database_path.open() as file:
        return json.load(file)


def _save(database_path: Path, data: dict) -> None:
    with database_path.open("w") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def _known_names(data: dict) -> set[str]:
    return {
        name.upper()
        for institution in data["institutions"]
        for name in [institution["name"], *institution.get("alt_names", [])]
    }


def add_institution(name: str, database_path: Path) -> None:
    name = name.strip().upper()
    data = _load(database_path)
    if name in _known_names(data):
        raise ValueError(f"Institution name already exists: {name}")
    data["institutions"].append({"name": name, "alt_names": []})
    data["institutions"].sort(key=lambda institution: institution["name"])
    _save(database_path, data)


def add_alt_name(institution_name: str, alt_name: str, database_path: Path) -> None:
    canonical = institution_name.strip().upper()
    alternate = alt_name.strip().upper()
    data = _load(database_path)
    if alternate in _known_names(data):
        raise ValueError(f"Institution name already exists: {alternate}")
    institution = next((value for value in data["institutions"] if value["name"].upper() == canonical), None)
    if institution is None:
        raise ValueError(f"Canonical institution not found: {canonical}")
    institution.setdefault("alt_names", []).append(alternate)
    institution["alt_names"].sort()
    _save(database_path, data)


def validate(database_path: Path) -> list[str]:
    """Return every inconsistency in the institution database."""
    errors = []
    owners = {}
    for institution in _load(database_path)["institutions"]:
        canonical = institution["name"]
        for name in [canonical, *institution.get("alt_names", [])]:
            if not name.strip():
                errors.append(f"Institution {canonical!r} has an empty name.")
            elif name != name.upper() or name != name.strip():
                errors.append(f"Institution name must be uppercase and trimmed: {name!r}")
            if name.upper() in owners:
                errors.append(f"Institution name {name!r} belongs to both {owners[name.upper()]} and {canonical}.")
            owners[name.upper()] = canonical
    return errors
