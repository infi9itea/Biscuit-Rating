---
name: add-contest
description: Add a finished contest's standings to the rating data. Use when the user gives saved standings HTML (Toph or BAPS) for a new contest, or asks to add/import a contest. Registers the contest, regenerates every output through the dependency graph, and resolves unknown institution names with the user's confirmation.
---

# Add a contest

Every step below is a plain CLI command, so a person can follow the same steps
without an agent (see `README.md`).

Run everything from the repository root inside the project environment
(`source .venv/bin/activate` or `conda activate biscuit-rating`).

## 1. Collect the contest details

You need:

- **HTML files**: the saved standings page(s). A contest may span several pages;
  keep them in page order.
- **Name**: uppercase `<HOST> <YEAR>`, for example `IUT 2026`. Look at
  `parser/input/contests.json` for the convention and make sure the name is new.
- **Date**: the contest day, `YYYY-MM-DD`.
- **Parser**: `TOPH` or `BAPS`. Detect it from the HTML instead of asking: Toph
  pages mention `toph`; BAPS pages link to `bapsoj.org`
  (`grep -ci 'toph\|bapsoj' file.html`). Ask the
  user only if the page is ambiguous.
- **Credit**: `1` unless the user says otherwise. ICPC regionals use
  `3`, so for an ICPC regional suggest `3` and confirm.

Ask the user for anything you cannot infer, in a single question. Confirm the
details before writing anything.

## 2. Register the contest

```bash
biscuit add-contest --html "path/to/page 1.html" "path/to/page 2.html" \
  --name "HOST 2026" --date 2026-06-01 --parser TOPH --credit 1
```

This copies the HTML into `parser/input/contest_files/`, appends the contest to
`parser/input/contests.json`, and adds its credit to
`rating_calculator/input/credits.json`. The contest's public standings link,
shown on the site's "Get listed" form, is read from the saved HTML; if the
file does not say where it was saved from, pass `--standings URL`. If an HTML file name already exists,
rename the copy (for example `HOST26.html`) and retry.

## 3. Regenerate the data

```bash
biscuit update
```

It validates the data, then reruns only the stages whose inputs changed. If
the parser reports no teams or the validation fails, show the error to the
user and fix the cause; do not edit generated outputs by hand.

## 4. Resolve unknown institutions

```bash
biscuit check-institutions --contest "HOST 2026"
```

It prints tab-separated `Unresolved Name`, `Contests`, `Best Match`,
`Probability`. Teams whose institution does not resolve are left out of the
ratings, so every row needs a decision. Classify each one and present all of
them to the user in one batch for confirmation:

- **Spelling variant / typo of a known institution** (high probability, the
  same institution): propose adding it as an alternate name.
  `biscuit add-alt-name "CANONICAL NAME" "NAME AS WRITTEN"`
  The standings HTML is never edited; alternate names are how typos are fixed.
- **New institution**: propose adding it.
  `biscuit add-institution "FULL OFFICIAL NAME"`
  If the standings used an abbreviation or a variant, add the official name
  and then add the written form as an alternate name.
- **Not an institution** (placeholders such as `IOI`, `TEMP UNIVERSITY`,
  `RESERVE1`, or an empty name): propose leaving it unresolved.

Never add a name without the user's confirmation. Group the proposals so the
user can approve them all at once or correct individual ones.

After applying the decisions, run `biscuit update` again, then
`biscuit check-institutions --contest "HOST 2026"` to confirm that only the
names the user chose to leave remain.

## 5. Verify and report

```bash
python -m pytest
biscuit update --check
```

Report the contest that was added, the institution changes made, any names
left unresolved, and the institutions whose rating moved the most (compare
`rating_calculator/output/latest_ratings.csv` with `git diff`). Do not commit
unless the user asks. When pushed to the default branch, CI regenerates the
data anyway, so a forgotten `biscuit update` is never left inconsistent.
