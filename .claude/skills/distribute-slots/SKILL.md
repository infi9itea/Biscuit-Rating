---
name: distribute-slots
description: Run the slot distributor for an upcoming contest. Use when the user has a list of registered institutions (with the number of slots each asked for) and wants slots allocated. Builds the registration CSV, fixes misspelled or unknown institution names with the user's confirmation, and produces the slots workbook.
---

# Distribute slots

Every step below is a plain CLI command, so a person can do the same without an
agent: `iupc distribute --interactive` prompts for each unknown name.

Run everything from the repository root inside the project environment
(`source .venv/bin/activate` or `conda activate iupc-rating`).

## 1. Prepare the inputs

The distributor reads `slot_distributor/input/` (git-ignored, so real
registration data is never committed):

- `registered.csv` with exactly the header `Institution,Max Slots`. One row per
  institution; `Max Slots` is the positive whole number of teams it registered.
  If the organizers want a cap per institution, apply it to this column.
  The distributor never gives an institution more slots than this, including
  waiting-list entries. Quote names that contain commas.
- `options.json`: copy `slot_distributor/input/example/options.json` and set
  the values for this contest:
  - `total_slots`: slots available
  - `waiting_list_size`: length of the waiting list
  - `min_unique`: minimum distinct institutions guaranteed a slot
  - `absence_bonus` (default 200) and `max_missed_contests` (default 5): an
    institution that missed the latest `x` contests in a row gets
    `absence_bonus * min(x, max_missed_contests)` added to the priority of its
    first slot only; later slots use its rating alone

If the user gives the registrations in another shape (a spreadsheet export, a
pasted list, a form dump), convert it to `registered.csv`. If the number of
teams per institution is missing, ask; do not guess. Ask for any option the
user has not given, in one question, offering the previous `options.json`
values as defaults when the file exists.

## 2. Make sure the ratings are current

```bash
iupc update --check || iupc update
```

## 3. Run and fix names

```bash
iupc distribute
```

If it stops with `Registered institutions were not found`, read
`slot_distributor/output/missing.csv` (`Missing Institution`,
`Best Possible Match`, `Probability`). For more candidates, use:

```bash
python -c "from pathlib import Path; from institution_finder import InstitutionFinder; \
print(InstitutionFinder(Path('institution_finder/data/institutions.json')).best_matches('NAME', 5))"
```

Classify every missing name and present all proposals to the user in one batch:

- **One-off typo** in the registration: propose correcting the row in
  `registered.csv` to the canonical name.
- **Legitimate variant** that will appear again (an abbreviation, `&` versus
  `AND`, a campus suffix): propose
  `iupc add-alt-name "CANONICAL NAME" "NAME AS WRITTEN"`.
- **New institution** that has never been in the database: propose
  `iupc add-institution "FULL OFFICIAL NAME"`. It needs no special
  handling: with no rating and no participation history it is treated as having
  missed the maximum number of contests.

Apply only what the user confirms. If the institution database changed, run
`iupc update` before rerunning the distributor, since ratings depend on it.

The distributor also stops if two rows resolve to the same institution or a
`Max Slots` value is not a positive integer. Show the rows to the user and ask
how to merge or fix them.

Repeat until it prints `Generated slot distribution sheet at ...`.

## 4. Report

Summarize from `slot_distributor/output/slots.csv` and
`slot_distributor/output/waiting_list.csv` (the same data as `slots.xlsx`,
which is the file to hand to organizers; `Slots` there is `General Slots`):
the total allocated, institutions that got fewer slots than they registered,
institutions with an absence bonus, and the first few waiting-list entries.
Mention any institution database changes; those belong in a commit (ask
before committing), while the files under `slot_distributor/input/` and
`slot_distributor/output/` stay local.
