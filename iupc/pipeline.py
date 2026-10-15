"""The dependency graph of generated data, and incremental updates over it."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import parser
import performance_calculator
import rating_calculator
import score_calculator

from .validate import validate

INSTITUTIONS = "institution_finder/data/institutions.json"
STATE_PATH = Path("iupc/state.json")


@dataclass(frozen=True)
class Stage:
    name: str
    dependencies: tuple[str, ...]
    # Glob patterns relative to the repository root. Upstream outputs are
    # inputs too, so a change anywhere upstream invalidates this stage.
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    run: Callable[[Path], object]


CONTESTS = "parser/output/contests/*.json"
CONTESTS_CODE = "contests/*.py"

STAGES = (
    Stage(
        name="parser",
        dependencies=(),
        inputs=("parser/*.py", CONTESTS_CODE, "parser/input/*.json", "parser/input/contest_files/*.html"),
        outputs=(CONTESTS,),
        run=lambda root: parser.run(root / "parser/input", root / "parser/output"),
    ),
    Stage(
        name="performance_calculator",
        dependencies=("parser",),
        inputs=(
            "performance_calculator/*.py",
            "performance_calculator/input/*.json",
            CONTESTS,
            CONTESTS_CODE,
            INSTITUTIONS,
            "institution_finder/*.py",
        ),
        outputs=("performance_calculator/output/*.csv",),
        run=lambda root: performance_calculator.run(
            root / "performance_calculator/input",
            root / "parser/output",
            root / "performance_calculator/output",
            root / INSTITUTIONS,
        ),
    ),
    Stage(
        name="score_calculator",
        dependencies=("parser", "performance_calculator"),
        inputs=(
            "score_calculator/*.py",
            "score_calculator/input/*.json",
            "performance_calculator/output/*.csv",
            CONTESTS,
            CONTESTS_CODE,
        ),
        outputs=("score_calculator/output/*.csv",),
        run=lambda root: score_calculator.run(
            root / "score_calculator/input",
            root / "performance_calculator/output",
            root / "parser/output",
            root / "score_calculator/output",
        ),
    ),
    Stage(
        name="rating_calculator",
        dependencies=("parser", "score_calculator"),
        inputs=(
            "rating_calculator/*.py",
            "rating_calculator/input/*.json",
            "score_calculator/output/*.csv",
            CONTESTS,
            CONTESTS_CODE,
        ),
        outputs=("rating_calculator/output/*.csv",),
        run=lambda root: rating_calculator.run(
            root / "rating_calculator/input",
            root / "score_calculator/output",
            root / "parser/output",
            root / "rating_calculator/output",
        ),
    ),
)


def fingerprint(root: Path, patterns: tuple[str, ...]) -> str:
    files = sorted({path for pattern in patterns for path in root.glob(pattern) if path.is_file()})
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        # Normalize line endings so checkouts on any platform hash the same.
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()


def _load_state(root: Path) -> dict:
    path = root / STATE_PATH
    return json.loads(path.read_text()) if path.exists() else {}


def _is_current(root: Path, stage: Stage, state: dict) -> bool:
    recorded = state.get(stage.name, {})
    return (
        recorded.get("inputs") == fingerprint(root, stage.inputs)
        and recorded.get("outputs") == fingerprint(root, stage.outputs)
    )


def stale_stages(root: Path) -> list[str]:
    state = _load_state(root)
    stale = []
    for stage in STAGES:
        if any(dependency in stale for dependency in stage.dependencies) or not _is_current(root, stage, state):
            stale.append(stage.name)
    return stale


def update(root: Path, force: bool = False, log: Callable[[str], None] = print) -> list[str]:
    """Validate the data, then rerun every stage whose inputs or outputs changed."""
    errors = validate(root)
    if errors:
        raise ValueError("Data validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    state = _load_state(root)
    ran = []
    for stage in STAGES:
        # Upstream stages have already run, so their new outputs are hashed here.
        if not force and _is_current(root, stage, state):
            log(f"{stage.name}: up to date")
            continue
        log(f"{stage.name}: running")
        stage.run(root)
        state[stage.name] = {
            "inputs": fingerprint(root, stage.inputs),
            "outputs": fingerprint(root, stage.outputs),
        }
        (root / STATE_PATH).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
        ran.append(stage.name)
    return ran


def mermaid() -> str:
    lines = [
        "flowchart TD",
        '    contest_data[("contest data")]',
        '    institutions[("institutions.json")]',
        "    parser --> contest_data",
    ]
    for stage in STAGES[1:]:
        for dependency in stage.dependencies:
            source = "contest_data" if dependency == "parser" else dependency
            lines.append(f"    {source} --> {stage.name}")
        if INSTITUTIONS in stage.inputs:
            lines.append(f"    institutions --> {stage.name}")
    lines += [
        "    rating_calculator -. ratings .-> slot_distributor",
        "    contest_data -. participation .-> slot_distributor",
        "    institutions -.-> slot_distributor",
    ]
    return "\n".join(lines)
