import re
from abc import ABC, abstractmethod
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from contests import Team


class Parser(ABC):
    # Bump when a parser's output changes, so stored contests are reparsed.
    version = 2

    def parse(self, filepaths: list[Path]) -> tuple[list[Team], list[str], int]:
        """Teams, warnings, and the number of problems (one column each after
        rank, team, and result)."""
        teams: list[Team] = []
        warnings: list[str] = []
        problems = 0
        for filepath in filepaths:
            for row_number, cells in _standings_rows(filepath):
                problems = max(problems, len(cells) - 3)
                try:
                    teams.append(self.parse_row(cells))
                except Exception as error:
                    warnings.append(f"{filepath.name}: row {row_number}: {type(error).__name__}: {error}")
        return teams, warnings, problems

    @abstractmethod
    def parse_row(self, cells: list[Tag]) -> Team:
        raise NotImplementedError


class BapsParser(Parser):
    def parse_row(self, cells: list[Tag]) -> Team:
        solved_text = cells[2].get_text(strip=True)
        institution = cells[1].find("div")
        return Team(
            rank=_optional_rank(cells[0].get_text(strip=True)),
            name=cells[1].find("strong").get_text(strip=True),
            institution=(institution.get_text(strip=True) if institution else "").upper(),
            solved=int(re.search(r"(\d+)", solved_text).group(1)),
            penalty=int(re.search(r"\((\d+)\)", solved_text).group(1)),
            first_solve_count=sum(
                1 for cell in cells[3:]
                if cell.find("div", style=re.compile(r"animation:.*shine.*"))
            ),
        )


class TophParser(Parser):
    """Detects and parses both the older and the current Toph layouts."""

    def parse_row(self, cells: list[Tag]) -> Team:
        team_cell = cells[1]
        result_cell = cells[2]
        institution = team_cell.find("div", class_="adjunct")
        penalty_element = result_cell.find("div", class_="adjunct")
        penalty_text = penalty_element.get("data-tippy-content", "") if penalty_element else ""
        penalty_match = re.search(r"Penalty:\s*(\d+)", penalty_text)
        current_layout = team_cell.find("div", class_="d-flex") is not None
        return Team(
            rank=_optional_rank(cells[0].get_text(strip=True)),
            name=self._team_name(team_cell, current_layout),
            institution=(institution.get_text(strip=True) if institution else "").upper(),
            solved=int(result_cell.find("strong").get_text(strip=True)),
            penalty=int(penalty_match.group(1)) if penalty_match else 0,
            first_solve_count=self._first_solve_count(cells[3:], current_layout),
        )

    def _team_name(self, team_cell: Tag, current_layout: bool) -> str:
        if not current_layout:
            return team_cell.contents[0].strip()
        container = team_cell.find("div", class_="d-flex")
        name_element = container.find("div") if container else None
        return name_element.contents[0].strip() if name_element else ""

    def _first_solve_count(self, cells: list[Tag], current_layout: bool) -> int:
        if current_layout:
            return sum(
                1 for cell in cells
                if cell.find("use") and "#star" in (
                    cell.find("use").get("href") or cell.find("use").get("xlink:href") or ""
                )
            )
        return sum(
            1 for cell in cells
            if cell.find("img", class_="icon green")
            and cell.find("img", class_="icon green").get("data-tippy-content") == "First to Solve"
        )


PARSERS: dict[str, Parser] = {
    "BAPS": BapsParser(),
    "TOPH": TophParser(),
}


def get_parser(name: str) -> Parser:
    try:
        return PARSERS[name.upper()]
    except KeyError as error:
        raise ValueError(f"Unknown parser: {name}") from error


def _standings_rows(filepath: Path):
    with filepath.open(encoding="utf-8") as file:
        soup = BeautifulSoup(file.read(), "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError(f"No standings table found in {filepath}")
    for row_number, row in enumerate(table.find_all("tr")[1:], start=2):
        cells = row.find_all("td")
        if len(cells) >= 3:
            yield row_number, cells


def _optional_rank(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None
