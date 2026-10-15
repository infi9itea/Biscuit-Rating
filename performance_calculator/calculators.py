from abc import ABC, abstractmethod


class PerformanceCalculator(ABC):
    @abstractmethod
    def calculate(self, rank: int, solved: int, maximum_solved: int) -> float:
        raise NotImplementedError


class ShongPerformanceCalculator(PerformanceCalculator):
    def __init__(self, maximum_team_rating: float, rank_decay_rate: float, solved_ratio_exponent: float):
        self.maximum_team_rating = maximum_team_rating
        self.rank_decay_rate = rank_decay_rate
        self.solved_ratio_exponent = solved_ratio_exponent

    def calculate(self, rank: int, solved: int, maximum_solved: int) -> float:
        if maximum_solved == 0:
            return 0
        rank_factor = (1 - self.rank_decay_rate) ** (rank - 1)
        solved_factor = (solved / maximum_solved) ** self.solved_ratio_exponent
        return self.maximum_team_rating * rank_factor * solved_factor


CALCULATORS = {"SHONG": ShongPerformanceCalculator}


def create(name: str, parameters: dict) -> PerformanceCalculator:
    if name.upper() not in CALCULATORS:
        raise ValueError(f"Unknown performance calculator: {name}")
    return CALCULATORS[name.upper()](**parameters)
