"""Rating tiers and Codeforces rank colours shared by the site's pages."""

import json
from functools import cache
from pathlib import Path

INSTITUTIONS = Path(__file__).resolve().parents[1] / "institution_finder/data/institutions.json"

# Codeforces' rating colours, with adjacent ranks of the same colour combined:
# newbie, pupil, specialist, expert, candidate master, master and international
# master (orange), grandmaster and international grandmaster (red), and legendary
# grandmaster (red with a black first letter). Colours are in style.css (.tier-N).
TIERS = [0, 1200, 1400, 1600, 1900, 2100, 2400, 3000]

CODEFORCES_RANKS = {
    "newbie": "cf-gray",
    "pupil": "cf-green",
    "specialist": "cf-cyan",
    "expert": "cf-blue",
    "candidate master": "cf-violet",
    "master": "cf-orange",
    "international master": "cf-orange",
    "grandmaster": "cf-red",
    "international grandmaster": "cf-red",
    "legendary grandmaster": "cf-legend",
}


SMALL_WORDS = {"of", "and", "the", "for", "in", "at", "on", "&"}


def institution_name(name: str) -> str:
    """Title case for upper-case institution names, keeping small words lower case."""
    words = name.title().split(" ")
    return " ".join(
        word.lower() if i and word.lower() in SMALL_WORDS else word
        for i, word in enumerate(words)
    )


@cache
def _alt_names() -> dict[str, list[str]]:
    data = json.loads(INSTITUTIONS.read_text()) if INSTITUTIONS.is_file() else {"institutions": []}
    return {institution["name"]: institution.get("alt_names", []) for institution in data["institutions"]}


def institution_search_text(name: str) -> str:
    """An institution's name, display name, and alternate names (such as "... (BUET)"), lower case,
    so searches match any of them."""
    return " ".join([name, institution_name(name), *_alt_names().get(name, [])]).lower()


def tier(rating: float | None) -> int:
    if rating is None:
        return 0
    return max(i for i, low in enumerate(TIERS) if rating >= low)


def tier_class(rating: float | None) -> str:
    return f"tier-{tier(rating)}"


def codeforces_class(rank: str | None) -> str:
    return CODEFORCES_RANKS.get((rank or "").lower(), "cf-gray")
