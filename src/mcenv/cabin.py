"""Bounded deterministic cabin generator for edit/render bridge acceptance.

The generator is deliberately small: it produces a Minecraft-native timber
cabin, enforces a hard write boundary, and exposes anchor blocks for post-write
readback.  It makes no assumptions about the project's settlement planner.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bounds:
    min_x: int
    min_y: int
    min_z: int
    max_x: int
    max_y: int
    max_z: int

    def contains(self, pos: tuple[int, int, int]) -> bool:
        x, y, z = pos
        return (
            self.min_x <= x <= self.max_x
            and self.min_y <= y <= self.max_y
            and self.min_z <= z <= self.max_z
        )

    def as_dict(self) -> dict[str, list[int]]:
        return {
            "min": [self.min_x, self.min_y, self.min_z],
            "max": [self.max_x, self.max_y, self.max_z],
        }


@dataclass(frozen=True)
class CabinPlan:
    semantic_id: str
    x0: int
    ground_y: int
    z0: int
    width: int = 11
    depth: int = 9
    seed: int = 20260907

    @property
    def x1(self) -> int:
        return self.x0 + self.width - 1

    @property
    def z1(self) -> int:
        return self.z0 + self.depth - 1

    @property
    def door_x(self) -> int:
        return self.x0 + self.width // 2

    @property
    def bounds(self) -> Bounds:
        # Includes roof overhang, chimney, porch, and approach path.
        return Bounds(
            self.x0 - 1,
            self.ground_y - 1,
            self.z0 - 1,
            self.x1 + 1,
            self.ground_y + 12,
            self.z1 + 5,
        )


def generate_cabin(plan: CabinPlan) -> dict[tuple[int, int, int], str]:
    """Return a deterministic, last-write-wins block patch."""
    ops: dict[tuple[int, int, int], str] = {}

    def put(x: int, y: int, z: int, block: str) -> None:
        pos = (x, y, z)
        if not plan.bounds.contains(pos):
            raise ValueError(f"Cabin generator escaped write bounds: {pos}")
        ops[pos] = block

    # Clear only the owned volume so rerunning the same plan is deterministic.
    for x in range(plan.x0 - 1, plan.x1 + 2):
        for z in range(plan.z0 - 1, plan.z1 + 2):
            for y in range(plan.ground_y + 1, plan.ground_y + 10):
                put(x, y, z, "air")

    # Foundation and wooden interior floor.
    for x in range(plan.x0, plan.x1 + 1):
        for z in range(plan.z0, plan.z1 + 1):
            perimeter = x in (plan.x0, plan.x1) or z in (plan.z0, plan.z1)
            put(x, plan.ground_y, z, "cobblestone" if perimeter else "spruce_planks")

    wall_bottom = plan.ground_y + 1
    wall_top = plan.ground_y + 5
    frame_x = {plan.x0, plan.x0 + 5, plan.x1}
    frame_z = {plan.z0, plan.z0 + 4, plan.z1}

    # Timber-frame shell with horizontal top/bottom beams.
    for y in range(wall_bottom, wall_top + 1):
        for x in range(plan.x0, plan.x1 + 1):
            for z in (plan.z0, plan.z1):
                block = "stripped_spruce_log[axis=y]" if x in frame_x else "spruce_planks"
                if y in (wall_bottom, wall_top) and x not in frame_x:
                    block = "dark_oak_log[axis=x]"
                put(x, y, z, block)
        for z in range(plan.z0 + 1, plan.z1):
            for x in (plan.x0, plan.x1):
                block = "stripped_spruce_log[axis=y]" if z in frame_z else "spruce_planks"
                if y in (wall_bottom, wall_top) and z not in frame_z:
                    block = "dark_oak_log[axis=z]"
                put(x, y, z, block)

    # Door faces south. Windows use shutters for an unmistakable cabin facade.
    put(plan.door_x, wall_bottom, plan.z1, "spruce_door[half=lower,facing=south,hinge=left]")
    put(plan.door_x, wall_bottom + 1, plan.z1, "spruce_door[half=upper,facing=south,hinge=left]")
    for x in (plan.x0 + 2, plan.x1 - 2):
        put(x, wall_bottom + 2, plan.z1, "glass_pane")
        put(x - 1, wall_bottom + 2, plan.z1, "spruce_trapdoor[open=true,facing=west]")
        put(x + 1, wall_bottom + 2, plan.z1, "spruce_trapdoor[open=true,facing=east]")
    for z in (plan.z0 + 2, plan.z1 - 2):
        for x in (plan.x0, plan.x1):
            put(x, wall_bottom + 2, z, "glass_pane")

    # Gable infill on east/west ends and steep spruce stair roof along X.
    roof_base = wall_top + 1
    for level in range(5):
        za = plan.z0 - 1 + level
        zb = plan.z1 + 1 - level
        y = roof_base + level
        for x in range(plan.x0 - 1, plan.x1 + 2):
            if za == zb:
                put(x, y, za, "spruce_slab[type=top]")
            else:
                put(x, y, za, "spruce_stairs[facing=south]")
                put(x, y, zb, "spruce_stairs[facing=north]")
        if level > 0:
            for x in (plan.x0, plan.x1):
                for z in range(za + 1, zb):
                    put(x, y, z, "dark_oak_planks")

    # Chimney crosses the roof and ends in a smoke-producing campfire.
    chimney_x = plan.x0 + 2
    chimney_z = plan.z0 + 3
    for y in range(wall_bottom, plan.ground_y + 11):
        put(chimney_x, y, chimney_z, "cobblestone")
    put(chimney_x, plan.ground_y + 11, chimney_z, "campfire[lit=true]")

    # Porch, path and warm exterior lights.
    for x in range(plan.door_x - 2, plan.door_x + 3):
        for z in range(plan.z1 + 1, plan.z1 + 3):
            put(x, plan.ground_y, z, "spruce_planks")
    for x in (plan.door_x - 2, plan.door_x + 2):
        put(x, wall_bottom, plan.z1 + 2, "spruce_fence")
        put(x, wall_bottom + 1, plan.z1 + 2, "lantern[hanging=false]")
    for z in range(plan.z1 + 3, plan.z1 + 6):
        put(plan.door_x, plan.ground_y, z, "coarse_dirt")

    # Minimal functional interior.
    put(plan.x0 + 2, wall_bottom, plan.z0 + 2, "furnace[facing=south]")
    put(plan.x0 + 3, wall_bottom, plan.z0 + 2, "crafting_table")
    put(plan.x1 - 2, wall_bottom, plan.z0 + 2, "barrel[facing=up]")
    put(plan.x1 - 2, wall_bottom, plan.z1 - 2, "red_bed[part=foot,facing=north]")
    put(plan.x1 - 2, wall_bottom, plan.z1 - 3, "red_bed[part=head,facing=north]")
    put(plan.door_x, wall_top - 1, plan.z0 + 1, "lantern[hanging=true]")

    return ops


def anchor_expectations(plan: CabinPlan) -> dict[tuple[int, int, int], str]:
    """Small deterministic readback set used by structural acceptance."""
    return {
        (plan.x0, plan.ground_y, plan.z0): "minecraft:cobblestone",
        (plan.x0, plan.ground_y + 1, plan.z0): "minecraft:stripped_spruce_log",
        (plan.door_x, plan.ground_y + 1, plan.z1): "minecraft:spruce_door",
        (plan.door_x, plan.ground_y + 2, plan.z1): "minecraft:spruce_door",
        (plan.x0 - 1, plan.ground_y + 6, plan.z0 - 1): "minecraft:spruce_stairs",
        (plan.x0 + 2, plan.ground_y + 11, plan.z0 + 3): "minecraft:campfire",
        (plan.door_x, plan.ground_y, plan.z1 + 5): "minecraft:coarse_dirt",
    }
