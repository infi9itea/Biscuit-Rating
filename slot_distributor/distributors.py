import heapq
from abc import ABC, abstractmethod

import pandas as pd


class SlotDistributor(ABC):
    @abstractmethod
    def distribute(self, institutions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Distribute slots among registered institutions.

        `institutions` has the columns `Institution`, `Rating` (NaN when never
        rated), `Registered Slots` (the most slots the institution asked for)
        and `Missed Contests` (how many of the most recent contests in a row the
        institution did not participate in).
        """
        raise NotImplementedError


class PrioritySlotDistributor(SlotDistributor):
    def __init__(
        self,
        total_slots: int,
        waiting_list_size: int,
        min_unique: int,
        absence_bonus: float = 200,
        max_missed_contests: int = 5,
    ):
        self.total_slots = total_slots
        self.waiting_list_size = waiting_list_size
        self.min_unique = min_unique
        self.absence_bonus = absence_bonus
        self.max_missed_contests = max_missed_contests

    def distribute(self, institutions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        names = list(institutions["Institution"])
        original = dict(zip(names, institutions["Rating"]))
        missed = {
            name: min(int(value), self.max_missed_contests)
            for name, value in zip(names, institutions["Missed Contests"])
        }
        bonus = {name: self.absence_bonus * missed[name] for name in names}
        # A never-rated institution starts from zero; the absence bonus on its
        # first slot is what lifts it, so it needs no special handling.
        rating_of = {name: 0 if pd.isna(rating) else float(rating) for name, rating in original.items()}
        # Nobody gets more slots than it registered for, waiting list included.
        limit = dict(zip(names, institutions["Registered Slots"].astype(int)))
        allocated = {name: 0 for name in names}

        def priority(name: str) -> float:
            # Priority of granting the next slot, given how many are already held.
            # The absence bonus only applies to the first slot.
            next_slot = allocated[name] + 1
            if next_slot == 1:
                return rating_of[name] + bonus[name]
            return rating_of[name] / next_slot

        def entry(name: str) -> tuple[float, int, str]:
            # Min-heap ordering: highest priority first, then fewest slots held, then name.
            return (-priority(name), allocated[name], name)

        # Guarantee a first slot to the top `min_unique` institutions by priority.
        eligible = [name for name in names if limit[name] > 0]
        guarantee = min(self.min_unique, self.total_slots, len(eligible))
        first_choice = [(-priority(name), name) for name in eligible]
        heapq.heapify(first_choice)
        for _ in range(guarantee):
            _, name = heapq.heappop(first_choice)
            allocated[name] = 1
        total_allocated = guarantee

        # Distribute the remaining slots by priority; institutions without a slot
        # still compete for their first one.
        heap = [entry(name) for name in names if allocated[name] < limit[name]]
        heapq.heapify(heap)
        while total_allocated < self.total_slots and heap:
            _, _, name = heapq.heappop(heap)
            allocated[name] += 1
            total_allocated += 1
            if allocated[name] < limit[name]:
                heapq.heappush(heap, entry(name))

        slots = pd.DataFrame({
            "Institution": names,
            "Rating": [original[name] for name in names],
            "Missed Contests": [missed[name] for name in names],
            "Absence Bonus": [bonus[name] for name in names],
            "Registered Slots": [int(registered) for registered in institutions["Registered Slots"]],
            "Slots": [allocated[name] for name in names],
        })

        waiting = []

        def record(name: str, value: float) -> None:
            waiting.append({
                "Position": len(waiting) + 1,
                "Institution": name,
                "Rating": original[name],
                "Potential Slot Number": allocated[name],
                "Priority": value,
            })

        # Waiting list first serves institutions still without any slot.
        first_slot = [(-priority(name), name) for name in names if allocated[name] == 0 and limit[name] > 0]
        heapq.heapify(first_slot)
        while len(waiting) < self.waiting_list_size and first_slot:
            negative_priority, name = heapq.heappop(first_slot)
            allocated[name] += 1
            record(name, -negative_priority)

        # Once everyone has a (potential) first slot, continue by normal priority.
        heap = [entry(name) for name in names if allocated[name] < limit[name]]
        heapq.heapify(heap)
        while len(waiting) < self.waiting_list_size and heap:
            negative_priority, _, name = heapq.heappop(heap)
            allocated[name] += 1
            record(name, -negative_priority)
            if allocated[name] < limit[name]:
                heapq.heappush(heap, entry(name))

        return slots, pd.DataFrame(waiting, columns=[
            "Position",
            "Institution",
            "Rating",
            "Potential Slot Number",
            "Priority",
        ])


DISTRIBUTORS = {"PRIORITY": PrioritySlotDistributor}


def create(name: str, parameters: dict) -> SlotDistributor:
    if name.upper() not in DISTRIBUTORS:
        raise ValueError(f"Unknown slot distributor: {name}")
    return DISTRIBUTORS[name.upper()](**parameters)
