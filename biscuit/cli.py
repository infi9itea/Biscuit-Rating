import argparse
import sys
from pathlib import Path

import codeforces
import institution_finder
import members
import website
import slot_distributor
from institution_finder import InstitutionFinder
from parser import PARSERS

from .maintenance import (
    add_contest,
    complete_members,
    import_form_responses,
    unresolved_institutions,
)
from .pipeline import mermaid, stale_stages, update
from .validate import validate

DATABASE = Path("institution_finder/data/institutions.json")
MEMBERS = Path("members/data/members.csv")
CODEFORCES_CACHE = Path("codeforces/data/users.json")


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
    add_contest(
        arguments.root, arguments.html, arguments.name, arguments.date, arguments.parser, arguments.credit, arguments.standings
    )
    print(f"Added contest {arguments.name.upper()}. Run `biscuit update` to regenerate the data.")


def _add_institution(arguments) -> None:
    institution_finder.add_institution(arguments.name, arguments.root / DATABASE)
    print(f"Added institution {arguments.name.upper()}. Run `biscuit update` to regenerate the data.")


def _add_alt_name(arguments) -> None:
    institution_finder.add_alt_name(arguments.institution, arguments.alt_name, arguments.root / DATABASE)
    print(f"Added alternate name {arguments.alt_name.upper()}. Run `biscuit update` to regenerate the data.")


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


def _fetch_codeforces(arguments) -> None:
    root = arguments.root
    # Codeforces handles are case-insensitive; each is fetched once.
    listed = [membership.handle for membership in members.load_members(root / MEMBERS)]
    handles = list({handle.lower(): handle for handle in reversed(listed)}.values())
    cache, renamed = codeforces.update_cache(root / CODEFORCES_CACHE, handles, arguments.refresh)
    # One handle per person: renamed accounts and every other spelling become the current handle.
    renames = {**codeforces.current_handles(cache, listed), **{
        spelling: new for old, new in renamed.items() for spelling in listed if spelling.lower() == old.lower()
    }}
    for old, new in sorted(renames.items(), key=lambda item: item[0].lower()):
        print(f"{old} is now {new}")
    changed = members.rename_handles(root / MEMBERS, renames)
    if changed:
        print(f"Updated {changed} handle(s) in {MEMBERS}. Run `biscuit update` next.")
    print(f"{len(cache['users'])} Codeforces profile(s) cached; {len(cache['missing'])} handle(s) unknown.")


def _complete_members(arguments) -> None:
    root = arguments.root
    added = complete_members(root / MEMBERS, root / "parser/output", root / DATABASE)
    print(f"Added {added} team(s) with NULL members to {MEMBERS}.")


def _import_form(arguments) -> None:
    changes, problems = import_form_responses(arguments.root / MEMBERS, arguments.files, arguments.apply)
    for change in changes:
        print(change)
    if problems:
        print(f"\n{len(problems)} answer(s) need a look:")
        for problem in problems:
            print(f"  {problem}")
    if not arguments.apply:
        print(f"\n{len(changes)} handle(s) would be added. Run again with --apply to write them.")
    else:
        print(f"\nAdded {len(changes)} handle(s). Run `biscuit fetch-codeforces` and `biscuit update` next.")


def _site(arguments) -> None:
    root = arguments.root
    output = website.build(
        root / "website/output",
        root / "contestant_rating/output",
        root / CODEFORCES_CACHE,
        root / "rating_calculator/input/credits.json",
        root / MEMBERS,
        root / "parser/input/contests.json",
        root / "website/input/form.json",
        root / "rating_calculator/output",
        root / "score_calculator/output",
        root / "performance_calculator/output/performances.csv",
        root / "parser/output",
    )
    print(f"Built the site in {output}.")
    if arguments.serve:
        import functools
        import http.server

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(output))
        with http.server.ThreadingHTTPServer(("127.0.0.1", arguments.port), handler) as server:
            print(f"Previewing at http://127.0.0.1:{arguments.port}/ (Ctrl+C to stop)")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


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
    command = argparse.ArgumentParser(prog="biscuit", description="Contest ratings and slot distribution.")
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
    contest_command.add_argument("--standings", default="", help="standings URL (default: where the HTML was saved from)")
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

    codeforces_command = commands.add_parser("fetch-codeforces", help="cache Codeforces profiles of listed members")
    codeforces_command.add_argument("--refresh", action="store_true", help="fetch every profile again")
    codeforces_command.set_defaults(handler=_fetch_codeforces)

    complete_command = commands.add_parser(
        "complete-members", help="add a NULL row for every team missing from members.csv, and sort it"
    )
    complete_command.set_defaults(handler=_complete_members)

    form_command = commands.add_parser("import-form", help="add handles from \"Get listed\" form responses (a CSV)")
    form_command.add_argument("files", type=Path, nargs="+")
    form_command.add_argument("--apply", action="store_true", help="write the changes (default: only show them)")
    form_command.set_defaults(handler=_import_form)

    site_command = commands.add_parser("site", help="build the rating website")
    site_command.add_argument("--serve", action="store_true", help="preview it in a local web server")
    site_command.add_argument("--port", type=int, default=8000)
    site_command.set_defaults(handler=_site)

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
