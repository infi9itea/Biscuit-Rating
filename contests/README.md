# Contests

Owns the contest data: the `Team` and `ParsedContest` records and their JSON
file format. The parser writes contests through it, and every other module
reads them through it, so no one else depends on the file format.

## Files

- `records.py`: `Team` and `ParsedContest` records; a contest records its
  number of problems
- `store.py`: `save_contest()`, `load_contests()` (oldest first),
  `contest_dates()`, and `contest_path()`

The files live in `parser/output/contests/`, one JSON document per contest,
because the parser produces them.

```python
from pathlib import Path
from contests import contest_dates, load_contests

contests = load_contests(Path("parser/output"))
dates = contest_dates(Path("parser/output"))
```
