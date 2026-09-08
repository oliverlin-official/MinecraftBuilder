"""Run the bounded cabin edit acceptance against a GDMC HTTP endpoint.

The caller must create and verify a matching GDMC build area and save a
pre-write block snapshot before invoking this script.  On an exception after
writing starts, the snapshot is replayed through GDPC as a best-effort
rollback.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from gdpc import Block, Editor


AIR_IDS = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def parse_block_spec(spec: str) -> Block:
    """Convert ``id[state=value,...]`` into a GDPC Block."""
    identifier, separator, state_text = spec.partition("[")
    identifier = identifier if ":" in identifier else f"minecraft:{identifier}"
    states: dict[str, str] = {}
    if separator:
        if not state_text.endswith("]"):
            raise ValueError(f"Malformed block state: {spec}")
        for entry in state_text[:-1].split(","):
            key, value = entry.split("=", 1)
            states[key] = value
    return Block(identifier, states)


def block_from_snapshot(entry: dict[str, object]) -> Block:
    return Block(
        str(entry["id"]),
        {str(key): str(value) for key, value in dict(entry.get("state", {})).items()},
        str(entry["data"]) if "data" in entry else None,
    )


def coords(vector: object) -> tuple[int, int, int]:
    return tuple(int(value) for value in vector)  # type: ignore[arg-type,return-value]


def restore_snapshot(editor: Editor, snapshot: list[dict[str, object]]) -> None:
    for entry in snapshot:
        position = (int(entry["x"]), int(entry["y"]), int(entry["z"]))
        editor.placeBlock(position, block_from_snapshot(entry))
    editor.flushBuffer()
    editor.awaitBufferFlushes(timeout=120)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1:9000")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--project-src", type=Path, required=True)
    parser.add_argument("--x", type=int, default=180)
    parser.add_argument("--ground-y", type=int, default=-10)
    parser.add_argument("--z", type=int, default=0)
    args = parser.parse_args()

    sys.path.insert(0, str(args.project_src))
    from mcenv.cabin import CabinPlan, anchor_expectations, generate_cabin

    output_dir: Path = args.output_dir
    snapshot_path = output_dir / "prewrite_blocks.json"
    preflight_path = output_dir / "prewrite_check.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if not preflight.get("prewrite_pass"):
        raise RuntimeError("Pre-write inspection did not pass")

    plan = CabinPlan(
        semantic_id="CABIN_SERVER_001",
        x0=args.x,
        ground_y=args.ground_y,
        z0=args.z,
    )
    patch = generate_cabin(plan)
    expected_bounds = (
        (plan.bounds.min_x, plan.bounds.min_y, plan.bounds.min_z),
        (plan.bounds.max_x, plan.bounds.max_y, plan.bounds.max_z),
    )
    escaped = [position for position in patch if not plan.bounds.contains(position)]
    if escaped:
        raise RuntimeError(f"Generator escaped its write boundary: {escaped[:5]}")

    control = Editor(host=args.host, buffering=False, retries=4, timeout=15)
    build_area = control.getBuildArea()
    actual_bounds = (coords(build_area.begin), coords(build_area.last))
    if actual_bounds != expected_bounds:
        raise RuntimeError(
            f"GDMC build area {actual_bounds} does not match cabin bounds {expected_bounds}"
        )

    manifest = {
        "task_id": "SERVER_CABIN_EDIT_001",
        "semantic_id": plan.semantic_id,
        "seed": plan.seed,
        "host": args.host,
        "bounds": plan.bounds.as_dict(),
        "operation_count": len(patch),
        "operations": [
            {"position": list(position), "block": block_spec}
            for position, block_spec in patch.items()
        ],
    }
    (output_dir / "patch_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    editor = Editor(
        host=args.host,
        buffering=True,
        bufferLimit=1024,
        multithreading=False,
        retries=4,
        timeout=30,
    )
    started = time.monotonic()
    writing_started = False
    try:
        writing_started = True
        for position, block_spec in patch.items():
            editor.placeBlock(position, parse_block_spec(block_spec))
        editor.flushBuffer()
        editor.awaitBufferFlushes(timeout=120)

        readback: dict[str, dict[str, object]] = {}
        for position, expected in anchor_expectations(plan).items():
            actual_block = control.getBlock(position)
            actual = actual_block.id
            passed = actual == expected
            readback[",".join(map(str, position))] = {
                "expected": expected,
                "actual": actual,
                "states": dict(actual_block.states),
                "pass": passed,
            }
        if not all(entry["pass"] for entry in readback.values()):
            raise RuntimeError("Anchor readback failed")
    except BaseException:
        if writing_started:
            rollback_editor = Editor(
                host=args.host,
                buffering=True,
                bufferLimit=1024,
                multithreading=False,
                retries=4,
                timeout=30,
            )
            restore_snapshot(rollback_editor, snapshot)
        raise

    duration = time.monotonic() - started
    report = {
        "task_id": "SERVER_CABIN_EDIT_001",
        "status": "COMMITTED",
        "semantic_objects_created": [plan.semantic_id],
        "backend": "GDPC 8.1.0 via GDMC HTTP Interface 1.8.4",
        "generator": "mcenv.cabin.generate_cabin",
        "seed": plan.seed,
        "allowed_region": plan.bounds.as_dict(),
        "operation_count": len(patch),
        "duration_seconds": round(duration, 3),
        "rollback_source": str(snapshot_path),
        "readback": readback,
        "qa": {"write_boundary": "PASS", "anchor_readback": "PASS"},
    }
    (output_dir / "edit_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
