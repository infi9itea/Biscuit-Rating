import json
from difflib import SequenceMatcher
from pathlib import Path


class InstitutionFinder:
    def __init__(self, database_path: Path):
        with database_path.open() as file:
            institutions = json.load(file)["institutions"]
        self.names = {
            candidate.upper(): institution["name"].upper()
            for institution in institutions
            for candidate in [institution["name"], *institution.get("alt_names", [])]
        }

    def resolve(self, name: str) -> str | None:
        return self.names.get(name.upper())

    def best_match(self, name: str) -> tuple[str, float]:
        matches = self.best_matches(name, 1)
        return matches[0] if matches else ("", 0)

    def best_matches(self, name: str, limit: int) -> list[tuple[str, float]]:
        """The `limit` most similar institutions, with a similarity percentage."""
        best = {}
        for candidate, canonical in self.names.items():
            probability = SequenceMatcher(None, name.upper(), candidate).ratio()
            best[canonical] = max(best.get(canonical, 0), probability)
        ranked = sorted(best.items(), key=lambda item: (-item[1], item[0]))[:limit]
        return [(canonical, round(probability * 100, 2)) for canonical, probability in ranked]
