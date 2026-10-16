import math
from abc import ABC, abstractmethod
from datetime import date


class RatingCalculator(ABC):
    @abstractmethod
    def calculate(
        self,
        scores: dict[str, float],
        credits: dict[str, float],
        dates: dict[str, date],
        latest_contest: str,
    ) -> float | None:
        """Rate an institution from its contest scores as of `latest_contest`."""
        raise NotImplementedError

    @abstractmethod
    def weight(self, credit: float, contest_date: date, latest_date: date) -> float:
        """How much a contest with this credit counts as of `latest_date`."""
        raise NotImplementedError


class BiscuitRatingCalculator(RatingCalculator):
    def __init__(self, time_decay_rate: float, time_decay_pulse_days: float):
        self.time_decay_rate = time_decay_rate
        self.time_decay_pulse_days = time_decay_pulse_days

    def weight(self, credit: float, contest_date: date, latest_date: date) -> float:
        # Credit and time decay are both plain weights: a contest with credit 3
        # counts three times as much, and one with half its weight left half as much.
        periods = (latest_date - contest_date).days / self.time_decay_pulse_days
        return credit * (1 - self.time_decay_rate) ** periods

    def calculate(
        self,
        scores: dict[str, float],
        credits: dict[str, float],
        dates: dict[str, date],
        latest_contest: str,
    ) -> float | None:
        weighted_squares = 0.0
        total_weight = 0.0
        for contest, score in scores.items():
            weight = self.weight(credits[contest], dates[contest], dates[latest_contest])
            weighted_squares += weight * score ** 2
            total_weight += weight
        return math.sqrt(weighted_squares / total_weight) if total_weight else None


CALCULATORS = {"BISCUIT": BiscuitRatingCalculator}


def create(name: str, parameters: dict) -> RatingCalculator:
    if name.upper() not in CALCULATORS:
        raise ValueError(f"Unknown rating calculator: {name}")
    return CALCULATORS[name.upper()](**parameters)
