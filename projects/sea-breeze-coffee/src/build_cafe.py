#!/usr/bin/env python3
"""Bounded Sea Breeze Coffee build against live GDMC HTTP."""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

from gdpc import Block, Editor

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from cafe import CafePlan, anchor_expectations, generate_cafe  # noqa: E402

HOST = "http://127.0.0.1:9000"
OUT = ROOT / "runs" / "sea_breeze_v2"
OUT.mkdir(parents=True, exist_ok=True)


def parse_block_spec(spec: str) -> Block:
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


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode())


def snapshot_patch_cells(editor: Editor, patch: dict[tuple[int, int, int], str]) -> list[dict]:
    blocks: list[dict] = []
    for x, y, z in sorted(patch):
        block = editor.getBlock((x, y, z))
        entry = {"x": x, "y": y, "z": z, "id": block.id, "state": dict(block.states)}
        if block.data is not None:
            entry["data"] = block.data
        blocks.append(entry)
    return blocks


def main() -> int:
    plan = CafePlan()
    patch = generate_cafe(plan)
    escaped = [p for p in patch if not plan.bounds.contains(p)]
    if escaped:
        raise RuntimeError(f"Generator escaped bounds: {escaped[:5]}")

    control = Editor(host=HOST, buffering=False, retries=4, timeout=20)
    build_area = control.getBuildArea()
    begin = tuple(int(v) for v in build_area.begin)
    last = tuple(int(v) for v in build_area.last)
    expected = (
        (plan.bounds.min_x, plan.bounds.min_y, plan.bounds.min_z),
        (plan.bounds.max_x, plan.bounds.max_y, plan.bounds.max_z),
    )
    if (begin, last) != expected:
        raise RuntimeError(f"Build area {begin}->{last} != expected {expected}")

    print(f"prewrite snapshot of {len(patch)} cells ...")
    snapshot = snapshot_patch_cells(control, patch)
    (OUT / "prewrite_blocks.json").write_text(json.dumps(snapshot), encoding="utf-8")
    (OUT / "prewrite_check.json").write_text(
        json.dumps(
            {
                "prewrite_pass": True,
                "build_area": {"begin": list(begin), "last": list(last)},
                "operation_count": len(patch),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    editor = Editor(
        host=HOST,
        buffering=True,
        bufferLimit=1024,
        multithreading=False,
        retries=4,
        timeout=30,
    )
    started = time.monotonic()
    for position, block_spec in patch.items():
        editor.placeBlock(position, parse_block_spec(block_spec))
    editor.flushBuffer()
    editor.awaitBufferFlushes(timeout=180)

    readback = {}
    for position, expected_id in anchor_expectations(plan).items():
        actual = control.getBlock(position)
        readback[",".join(map(str, position))] = {
            "expected": expected_id,
            "actual": actual.id,
            "states": dict(actual.states),
            "pass": actual.id == expected_id,
        }
    ok = all(v["pass"] for v in readback.values())
    report = {
        "task_id": "SEA_BREEZE_COFFEE_EDIT_002",
        "status": "COMMITTED" if ok else "READBACK_FAIL",
        "semantic_objects_created": [plan.semantic_id],
        "polish": [
            "open_ocean_vista_less_fence",
            "denser_plants_menu_signage",
            "softer_bay_edge",
        ],
        "backend": "GDPC 8.1.0 via GDMC HTTP Interface 1.8.4",
        "allowed_region": plan.bounds.as_dict(),
        "operation_count": len(patch),
        "duration_seconds": round(time.monotonic() - started, 3),
        "readback": readback,
    }
    (OUT / "edit_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
