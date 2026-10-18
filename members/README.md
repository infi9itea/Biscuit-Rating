# Members

Owns `data/members.csv`: which Codeforces handles were on which team.

```csv
contest,institution,team_name,member1,member2,member3
ICPC 2025,UNIVERSITY OF DHAKA,DU_Team,handle_a,handle_b,handle_c
```

- `contest`, `institution` and `team_name` must match a team in the parsed
  standings. The institution only matters when two teams share a name.
- An empty member cell means the handle was not provided:
  a team listed with one or two handles is fine, and people without a
  Codeforces handle are left out.
- `biscuit complete-members` adds a row with empty members for every team of a
  known institution that has none, and sorts the file by institution,
  contest date, and team name. Run it after adding a contest to get rows to
  fill in.
- `biscuit import-form FILE... [--apply]` adds handles from the site's "Get
  listed" form responses (a CSV from the Google Sheet). It only shows the
  changes and problems unless given `--apply`.
- More member columns (`member4`, ...) are allowed.

## One handle per person

Each person is listed under one Codeforces handle everywhere. Someone with
several accounts is listed under their main one only. `biscuit fetch-codeforces`
rewrites every handle that Codeforces spells differently, after a rename or in
other letter case, to the current handle throughout this file.

## Files

- `roster.py`: `load_members()` reads the file; `validate()` checks every row
  against the parsed contests and suggests close team names;
  `rename_handles()` rewrites handles throughout the file
- `data/members.csv`: the data
