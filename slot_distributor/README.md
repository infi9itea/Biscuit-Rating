# Slot Distributor

Allocates a contest's slots among the registered institutions.

```text
input/registered.csv + input/options.json
+ rating_calculator/output/latest_ratings.csv
+ contests (participation history) + institution_finder
-> output/slots.xlsx + output/slots.csv + output/waiting_list.csv
```

## Inputs

`input/` is git-ignored, so registrations are never committed. Copy the format
from `input/example/`, which the distributor refuses to run on.

`registered.csv` lists each institution and the most slots it registered for.
Quote names that contain commas.

```csv
Institution,Max Slots
UNIVERSITY OF DHAKA,5
"BEGUM ROKEYA UNIVERSITY, RANGPUR",2
```

`options.json` selects the distributor and its parameters (see below).

Names are resolved through the institution finder, so alternate names work.
The distributor stops and writes `output/missing.csv` (each unknown name with
its best match) if a name is unknown. It also stops if two rows resolve to the
same institution, or a `Max Slots` value is not a positive whole number.

## Files

- `distributors.py`: the `SlotDistributor` interface, the `PRIORITY`
  distributor, and the registry
- `service.py`: `run()` plus registration and participation-history helpers
- `exporter.py`: the Excel workbook (Read Me, Slots, Waiting List, and Ratings
  sheets)

## PRIORITY

Each slot goes to the institution with the highest priority for its next slot:

```text
first slot:  priority = rating + absence_bonus * min(missed_contests, max_missed_contests)
later slots: priority = rating / next slot number
```

`missed_contests` is how many of the latest parsed contests in a row the
institution did not take part in. The bonus helps an institution get back in;
later slots depend only on its rating. A never-rated institution has rating
`0` and has missed every contest, so it needs no special handling.

Ties go to the institution holding fewer slots. No institution gets more than
its `Max Slots`, including waiting-list entries.

1. The `min_unique` institutions with the highest first-slot priority are each
   guaranteed a slot.
2. The remaining slots follow priority.
3. The waiting list continues the same sequence, but institutions with no slot
   come first. If organizers add `k` slots, the first `k` entries get them.

Parameters: `total_slots`, `waiting_list_size`, `min_unique`,
`absence_bonus` (default `200`), and `max_missed_contests` (default `5`).

In the workbook, organizers can add Reserved Slots by hand, with a reason.
Total Slots updates automatically.
