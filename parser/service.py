import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from contests import ParsedContest, contest_path, save_contest

from .parsers import get_parser


def run(input_directory: Path, output_directory: Path, force: bool = False) -> dict[str, int]:
    """Parse every configured contest whose sources, parser, or date changed."""
    with (input_directory / "contests.json").open() as file:
        contests = json.load(file)["contests"]
    with (input_directory / "options.json").open() as file:
        options = json.load(file)
    manifest_path = output_directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"contests": {}}
    parsed_count = 0
    skipped_count = 0

    for configuration in contests:
        parser = get_parser(configuration["parser"])
        files = [input_directory / "contest_files" / name for name in configuration["filenames"]]
        path = contest_path(output_directory, configuration["name"])
        key = path.stem
        signature = {
            "source_files": configuration["filenames"],
            "source_hashes": [hashlib.sha256(source.read_bytes()).hexdigest() for source in files],
            "parser": configuration["parser"].upper(),
            "parser_version": parser.version,
            "date": configuration["date"],
        }
        prior = manifest["contests"].get(key, {})
        if not force and path.exists() and all(prior.get(field) == value for field, value in signature.items()):
            skipped_count += 1
            continue

        teams, warnings, problems = parser.parse(files)
        if not teams:
            raise ValueError(f"No teams parsed for {configuration['name']}")
        if warnings and options["fail_on_warnings"]:
            raise ValueError(f"Parser warnings for {configuration['name']}: {warnings}")
        save_contest(output_directory, ParsedContest(
            name=configuration["name"].upper(),
            date=configuration["date"],
            parser=configuration["parser"].upper(),
            teams=teams,
            warnings=warnings,
            problems=problems,
        ))
        manifest["contests"][key] = {
            **signature,
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "team_count": len(teams),
            "warning_count": len(warnings),
        }
        parsed_count += 1

    output_directory.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w") as file:
        json.dump(manifest, file, indent=4)
    return {"parsed": parsed_count, "skipped": skipped_count}
