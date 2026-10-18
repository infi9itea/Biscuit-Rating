# Codeforces

Fetches public Codeforces profiles (name, photo, rank, rating) for the handles
in `members/data/members.csv` and caches them in `data/users.json`.

The cache is committed, so building the site never calls the API. Only
uncached handles are fetched, in batches of 300 with a pause between
requests; `--refresh` fetches everyone again. Profiles of handles that are no
longer listed are removed from the cache. Handles Codeforces does not
know are listed under `missing`. A handle that Codeforces now spells
differently (renamed, or in other letter case) is reported to
`biscuit fetch-codeforces`, which writes the current handle into
`members/data/members.csv`, so each person keeps one handle and one page.

## Files

- `client.py`: `fetch()`, `load_cache()`, and `update_cache()`
- `data/users.json`: the cache
