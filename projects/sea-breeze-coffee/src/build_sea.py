#!/usr/bin/env python3
"""Place stylized distant sea (glass/wool/concrete) ≥8 chunks from center."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from gdpc import Block, Editor

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from sea import (  # noqa: E402
    SEA_SURFACE_OK,
    SEA_Z0,
    SEA_Z1,
    write_bounds,
    anchor_expectations,
    generate_stylized_sea,
)

HOST = "http://127.0.0.1:9000"
OUT = ROOT / "runs" / "sea_breeze_v4"
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
    bounds = write_bounds()
    patch = generate_stylized_sea()
    print(f"stylized sea ops {len(patch)} sea_z {SEA_Z0}..{SEA_Z1}")

    control = Editor(host=HOST, buffering=False, retries=4, timeout=20)
    build_area = control.getBuildArea()
    begin = tuple(int(v) for v in build_area.begin)
    last = tuple(int(v) for v in build_area.last)
    expected = (
        (bounds.min_x, bounds.min_y, bounds.min_z),
        (bounds.max_x, bounds.max_y, bounds.max_z),
    )
    if (begin, last) != expected:
        raise RuntimeError(f"Build area {begin}->{last} != expected {expected}")

    cafe = control.getBlock((44, -10, 55))
    if cafe.id != "minecraft:oak_planks":
        raise RuntimeError(f"Café lock precheck failed: {cafe.id}")

    (OUT / "prewrite_check.json").write_text(
        json.dumps(
            {
                "prewrite_pass": True,
                "build_area": {"begin": list(begin), "last": list(last)},
                "operation_count": len(patch),
                "sea_start_z": SEA_Z0,
                "chunks_from_center": 8,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    editor = Editor(
        host=HOST,
        buffering=True,
        bufferLimit=2048,
        multithreading=False,
        retries=4,
        timeout=30,
    )
    started = time.monotonic()
    for position, block_spec in patch.items():
        editor.placeBlock(position, parse_block_spec(block_spec))
    editor.flushBuffer()
    editor.awaitBufferFlushes(timeout=300)

    readback = {}
    for position, expected_id in anchor_expectations().items():
        actual = control.getBlock(position)
        readback[",".join(map(str, position))] = {
            "expected": expected_id,
            "actual": actual.id,
            "pass": actual.id == expected_id,
        }
    sea_block = control.getBlock((44, -10, SEA_Z0))
    near = control.getBlock((44, -10, 80))
    readback[f"44,-10,{SEA_Z0}"] = {
        "expected": "glass|wool|concrete (not water)",
        "actual": sea_block.id,
        "pass": sea_block.id in SEA_SURFACE_OK,
    }
    readback["44,-10,80_not_water"] = {
        "expected": "not minecraft:water",
        "actual": near.id,
        "pass": near.id != "minecraft:water",
    }
    ok = all(v["pass"] for v in readback.values())
    report = {
        "task_id": "SEA_BREEZE_STYLIZED_SEA_001",
        "status": "COMMITTED" if ok else "READBACK_FAIL",
        "sea_start_z": SEA_Z0,
        "chunks_from_view_origin": 8,
        "materials": ["glass", "wool", "concrete"],
        "operation_count": len(patch),
        "duration_seconds": round(time.monotonic() - started, 3),
        "readback": readback,
    }
    (OUT / "edit_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
