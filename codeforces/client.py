"""Codeforces profiles (name, photo, rank), fetched in batches and cached in the repository."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://codeforces.com/api/user.info"
BATCH = 300
PAUSE_SECONDS = 2.1
FIELDS = ("handle", "firstName", "lastName", "titlePhoto", "avatar", "rank", "rating", "maxRank", "maxRating", "organization", "country")


def _request(handles: list[str]) -> dict:
    query = urllib.parse.urlencode({"handles": ";".join(handles)})
    try:
        with urllib.request.urlopen(f"{API}?{query}", timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # The API reports unknown handles with HTTP 400 and a JSON body.
        return json.load(error)


def fetch(handles: list[str], log=print) -> tuple[dict[str, dict], list[str], dict[str, str]]:
    """Profiles keyed by lower-case current handle, the handles Codeforces does not
    know, and each requested handle written differently from its current one
    (renamed, or in other letter case), mapped to the current handle."""
    profiles, missing, renamed = {}, [], {}
    pending = list(dict.fromkeys(handles))
    while pending:
        batch, pending = pending[:BATCH], pending[BATCH:]
        reply = _request(batch)
        if reply.get("status") == "OK":
            # Results come back in request order, which reveals renamed handles.
            for requested, user in zip(batch, reply["result"]):
                profiles[user["handle"].lower()] = {field: user.get(field) for field in FIELDS}
                if requested != user["handle"]:
                    renamed[requested] = user["handle"]
        else:
            comment = reply.get("comment", "")
            # "handles: User with handle X not found": drop it and retry the rest.
            unknown = next((h for h in batch if f"handle {h} not found".lower() in comment.lower()), None)
            if unknown is None:
                raise RuntimeError(f"Codeforces API error: {comment}")
            log(f"Codeforces does not know {unknown}")
            missing.append(unknown)
            pending = [h for h in batch if h != unknown] + pending
        if pending:
            time.sleep(PAUSE_SECONDS)
    return profiles, missing, renamed


def load_cache(path: Path) -> dict:
    cache = json.loads(path.read_text()) if path.exists() else {}
    return {"users": {}, "missing": [], **cache}


def profile(cache: dict, handle: str) -> dict | None:
    """The cached profile for a handle."""
    return cache["users"].get(handle.lower())


def current_handles(cache: dict, handles: list[str]) -> dict[str, str]:
    """Each handle written differently from its cached profile (letter case), mapped to it."""
    return {
        handle: cache["users"][handle.lower()]["handle"]
        for handle in handles
        if handle.lower() in cache["users"] and cache["users"][handle.lower()]["handle"] != handle
    }


def update_cache(path: Path, handles: list[str], refresh: bool = False, log=print) -> tuple[dict, dict[str, str]]:
    """Fetch handles that are not cached yet (all of them with `refresh`), forget
    profiles of handles that are no longer listed, and save the cache.

    Returns the cache and the renamed handles found while fetching, each mapped
    to its current handle, for the caller to write back to the members file.
    """
    cache = load_cache(path)
    listed = {handle.lower() for handle in handles}
    kept_users = {key: user for key, user in cache["users"].items() if key in listed}
    kept_missing = [handle for handle in cache["missing"] if handle.lower() in listed]
    pruned = len(cache["users"]) - len(kept_users)
    changed = pruned or kept_missing != cache["missing"]
    cache.update(users=kept_users, missing=kept_missing)
    if pruned:
        log(f"Forgetting {pruned} profile(s) of handles no longer listed")
    known = set(cache["users"]) | {handle.lower() for handle in cache["missing"]}
    wanted = handles if refresh else [h for h in handles if h.lower() not in known]
    renamed = {}
    if wanted:
        changed = True
        log(f"Fetching {len(wanted)} Codeforces profile(s)")
        profiles, missing, renamed = fetch(wanted, log)
        cache["users"].update(profiles)
        cache["missing"] = sorted(
            {h for h in cache["missing"] if h.lower() not in profiles} | set(missing),
            key=str.lower,
        )
        cache["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return cache, renamed
