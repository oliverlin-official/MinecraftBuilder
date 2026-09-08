#!/usr/bin/env python3
"""Expand Sea Breeze build area and place two flanking context chunks."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from gdpc import Block, Editor

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from context import ContextPlan, anchor_expectations, generate_context  # noqa: E402

HOST = "http://127.0.0.1:9000"
OUT = ROOT / "runs" / "sea_breeze_v3"
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


def main() -> int:
    plan = ContextPlan()
    patch = generate_context(plan)
    escaped = [
        p
        for p in patch
        if not (
            plan.bounds.min_x <= p[0] <= plan.bounds.max_x
            and plan.bounds.min_y <= p[1] <= plan.bounds.max_y
            and plan.bounds.min_z <= p[2] <= plan.bounds.max_z
        )
    ]
    if escaped:
        raise RuntimeError(f"Generator escaped bounds: {escaped[:5]}")
    leaked = [p for p in patch if plan.cafe_protect.contains(p)]
    if leaked:
        raise RuntimeError(f"Generator wrote locked café: {leaked[:5]}")

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

    # Café still present (lock check)
    cafe_floor = control.getBlock((44, -10, 55))
    if cafe_floor.id != "minecraft:oak_planks":
        raise RuntimeError(f"Café lock precheck failed: {cafe_floor.id}")

    print(f"context ops {len(patch)}")
    (OUT / "prewrite_check.json").write_text(
        json.dumps(
            {
                "prewrite_pass": True,
                "build_area": {"begin": list(begin), "last": list(last)},
                "operation_count": len(patch),
                "cafe_floor": cafe_floor.id,
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
    cafe_after = control.getBlock((44, -10, 55))
    readback["44,-10,55"] = {
        "expected": "minecraft:oak_planks",
        "actual": cafe_after.id,
        "states": dict(cafe_after.states),
        "pass": cafe_after.id == "minecraft:oak_planks",
    }
    ok = all(v["pass"] for v in readback.values())
    report = {
        "task_id": "SEA_BREEZE_CONTEXT_001",
        "status": "COMMITTED" if ok else "READBACK_FAIL",
        "semantic_objects_created": [plan.semantic_id],
        "allowed_region": plan.bounds.as_dict(),
        "protected_cafe": plan.cafe_protect.as_dict(),
        "operation_count": len(patch),
        "duration_seconds": round(time.monotonic() - started, 3),
        "readback": readback,
    }
    (OUT / "edit_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
