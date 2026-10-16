from abc import ABC, abstractmethod


class ScoreCalculator(ABC):
    @abstractmethod
    def calculate(self, performances: list[float]) -> float | None:
        """Combine an institution's team performances, best team first."""
        raise NotImplementedError


class BiscuitScoreCalculator(ScoreCalculator):
    def __init__(self, institution_team_limit: int, rating_degree: float):
        self.institution_team_limit = institution_team_limit
        self.rating_degree = rating_degree

    def calculate(self, performances: list[float]) -> float | None:
        selected = performances[:self.institution_team_limit]
        if not selected:
            return None
        powered_mean = sum(value ** self.rating_degree for value in selected) / len(selected)
        return powered_mean ** (1 / self.rating_degree)


CALCULATORS = {"BISCUIT": BiscuitScoreCalculator}


def create(name: str, parameters: dict) -> ScoreCalculator:
    if name.upper() not in CALCULATORS:
        raise ValueError(f"Unknown score calculator: {name}")
    return CALCULATORS[name.upper()](**parameters)
