import argparse
import sys
from pathlib import Path

import institution_finder
import slot_distributor
from institution_finder import InstitutionFinder
from parser import PARSERS

from .maintenance import add_contest, unresolved_institutions
from .pipeline import mermaid, stale_stages, update
from .validate import validate

DATABASE = Path("institution_finder/data/institutions.json")


def _update(arguments) -> None:
    root = arguments.root
    if arguments.graph:
        print(mermaid())
    elif arguments.check:
        problems = [f"invalid: {error}" for error in validate(root)]
        problems += [f"stale: {name}" for name in stale_stages(root)]
        print("\n".join(problems) or "All outputs are up to date.")
        if problems:
            sys.exit(1)
    else:
        print(f"Updated {len(update(root, arguments.force))} stage(s).")


def _add_contest(arguments) -> None:
    add_contest(arguments.root, arguments.html, arguments.name, arguments.date, arguments.parser, arguments.credit)
    print(f"Added contest {arguments.name.upper()}. Run `iupc update` to regenerate the data.")


def _add_institution(arguments) -> None:
    institution_finder.add_institution(arguments.name, arguments.root / DATABASE)
    print(f"Added institution {arguments.name.upper()}. Run `iupc update` to regenerate the data.")


def _add_alt_name(arguments) -> None:
    institution_finder.add_alt_name(arguments.institution, arguments.alt_name, arguments.root / DATABASE)
    print(f"Added alternate name {arguments.alt_name.upper()}. Run `iupc update` to regenerate the data.")


def _check_institutions(arguments) -> None:
    root = arguments.root
    unresolved = unresolved_institutions(root / "parser/output", root / DATABASE, arguments.contest)
    if not unresolved:
        print("Every institution name resolves.")
    elif arguments.interactive:
        _, changed = institution_finder.resolve_interactively(list(unresolved), root / DATABASE)
        if changed:
            update(root)
    else:
        finder = InstitutionFinder(root / DATABASE)
        print("Unresolved Name\tContests\tBest Match\tProbability")
        for name, contests in unresolved.items():
            print("\t".join([name, ", ".join(contests), *map(str, finder.best_match(name))]))


def _distribute(arguments) -> None:
    root = arguments.root
    input_directory = root / arguments.input
    if arguments.interactive:
        registered_path = input_directory / "registered.csv"
        names = slot_distributor.unresolved_registrations(registered_path, root / DATABASE)
        typo_fixes, changed = institution_finder.resolve_interactively(
            names,
            root / DATABASE,
            allow_typo_fix=True,
        )
        if typo_fixes:
            slot_distributor.rename_registrations(registered_path, typo_fixes)
            print(f"Fixed {len(typo_fixes)} name(s) in {registered_path}.")
        if changed:
            # Ratings depend on the institution database.
            update(root)
    output = slot_distributor.run(
        input_directory,
        root / "rating_calculator/output",
        root / arguments.output,
        root / DATABASE,
        root / "parser/output",
    )
    print(f"Generated slot distribution sheet at {output}.")


def main(argv: list[str] | None = None) -> None:
    command = argparse.ArgumentParser(prog="iupc", description="Contest ratings and slot distribution.")
    command.add_argument("--root", type=Path, default=Path("."), help="repository root (default: .)")
    commands = command.add_subparsers(dest="command", required=True)

    update_command = commands.add_parser("update", help="validate the data and regenerate stale outputs")
    mode = update_command.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="only list stale stages; exit 1 if any")
    mode.add_argument("--force", action="store_true", help="rerun every stage")
    mode.add_argument("--graph", action="store_true", help="print the dependency graph as Mermaid")
    update_command.set_defaults(handler=_update)

    contest_command = commands.add_parser("add-contest", help="add a contest's standings")
    contest_command.add_argument("--html", required=True, type=Path, nargs="+", help="standings pages, in order")
    contest_command.add_argument("--name", required=True, help='for example "IUT 2026"')
    contest_command.add_argument("--date", required=True, help="YYYY-MM-DD")
    contest_command.add_argument("--parser", required=True, type=str.upper, choices=sorted(PARSERS))
    contest_command.add_argument("--credit", type=float, default=1)
    contest_command.set_defaults(handler=_add_contest)

    institution_command = commands.add_parser("add-institution", help="add a canonical institution")
    institution_command.add_argument("name")
    institution_command.set_defaults(handler=_add_institution)

    alt_name_command = commands.add_parser("add-alt-name", help="add an alternate name to an institution")
    alt_name_command.add_argument("institution")
    alt_name_command.add_argument("alt_name")
    alt_name_command.set_defaults(handler=_add_alt_name)

    check_command = commands.add_parser("check-institutions", help="list unknown names in parsed standings")
    check_command.add_argument("--contest", action="append", help="limit to this contest; repeatable")
    check_command.add_argument("--interactive", action="store_true", help="resolve each name by prompting")
    check_command.set_defaults(handler=_check_institutions)

    distribute_command = commands.add_parser("distribute", help="distribute slots for a contest")
    distribute_command.add_argument("--input", type=Path, default=Path("slot_distributor/input"))
    distribute_command.add_argument("--output", type=Path, default=Path("slot_distributor/output"))
    distribute_command.add_argument("--interactive", action="store_true", help="resolve unknown names by prompting")
    distribute_command.set_defaults(handler=_distribute)

    arguments = command.parse_args(argv)
    try:
        arguments.handler(arguments)
    except (ValueError, FileNotFoundError, FileExistsError) as error:
        sys.exit(f"error: {error}")


if __name__ == "__main__":
    main()
