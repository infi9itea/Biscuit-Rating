from pathlib import Path
from typing import Callable

from .database import add_alt_name, add_institution
from .finder import InstitutionFinder


SUGGESTION_COUNT = 3


def resolve_interactively(
    names: list[str],
    database_path: Path,
    allow_typo_fix: bool = False,
    ask: Callable[[str], str] = input,
    show: Callable[[str], None] = print,
) -> tuple[dict[str, str], bool]:
    """Ask a human how to resolve each unknown institution name.

    Returns `(typo_fixes, database_changed)`. `typo_fixes` maps an input name to
    the canonical name it should be replaced with in the input file; it is only
    filled when `allow_typo_fix` is true. Every other decision is saved to the
    institution database right away.
    """
    typo_fixes = {}
    database_changed = False
    for name in names:
        finder = InstitutionFinder(database_path)
        suggestions = finder.best_matches(name, SUGGESTION_COUNT)
        show(f'\nUnknown institution: "{name}"')
        for number, (canonical, probability) in enumerate(suggestions, start=1):
            show(f"  {number}) {canonical} ({probability}%)")
        show("  <number>   same institution; save the name as an alternate name")
        if allow_typo_fix:
            show("  t<number>  same institution; the name is a typo, fix the input file only")
        show("  o          same as another institution; type its name")
        show("  n          new institution; add it to the database")
        show("  s          skip; leave it unresolved")
        while True:
            answer = ask("Choice: ").strip().lower()
            if answer == "s":
                break
            if answer == "n":
                add_institution(name, database_path)
                database_changed = True
                break
            if answer == "o":
                other = ask("Institution name: ").strip()
                canonical = finder.resolve(other)
                if canonical is None:
                    show(f'"{other}" is not in the database.')
                    continue
                add_alt_name(canonical, name, database_path)
                database_changed = True
                break
            typo = allow_typo_fix and answer.startswith("t")
            number = answer[1:] if typo else answer
            if number.isdigit() and 1 <= int(number) <= len(suggestions):
                canonical = suggestions[int(number) - 1][0]
                if typo:
                    typo_fixes[name] = canonical
                else:
                    add_alt_name(canonical, name, database_path)
                    database_changed = True
                break
            show("Invalid choice.")
    return typo_fixes, database_changed
