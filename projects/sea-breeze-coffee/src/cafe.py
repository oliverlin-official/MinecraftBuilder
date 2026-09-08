"""Sea Breeze Coffee — bounded seaside café generator for GDPC.

PROFILE_A single architecture. Open south face toward artificial ocean.
All writes must stay inside plan.bounds.
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
class CafePlan:
    semantic_id: str = "SEA_BREEZE_COFFEE_001"
    # Interior footprint (inclusive)
    x0: int = 34
    ground_y: int = -10
    z0: int = 50
    width: int = 20
    depth: int = 12
    seed: int = 20260908

    @property
    def x1(self) -> int:
        return self.x0 + self.width - 1

    @property
    def z1(self) -> int:
        return self.z0 + self.depth - 1

    @property
    def bounds(self) -> Bounds:
        # Matches GDMC named area SEA_BREEZE_COFFEE
        return Bounds(28, -16, 45, 58, 8, 86)


def generate_cafe(plan: CafePlan) -> dict[tuple[int, int, int], str]:
    ops: dict[tuple[int, int, int], str] = {}

    def put(x: int, y: int, z: int, block: str) -> None:
        pos = (x, y, z)
        if not plan.bounds.contains(pos):
            raise ValueError(f"Cafe generator escaped write bounds: {pos}")
        ops[pos] = block

    gy = plan.ground_y
    wall_bottom = gy + 1
    wall_top = gy + 5  # interior clear height ~4, roof deck at +5
    bx0, bx1 = plan.bounds.min_x, plan.bounds.max_x
    bz0, bz1 = plan.bounds.min_z, plan.bounds.max_z

    # --- Clear owned air volume (building + porch + beach + water) ---
    for x in range(bx0, bx1 + 1):
        for z in range(bz0, bz1 + 1):
            for y in range(gy + 1, gy + 12):
                put(x, y, z, "air")

    # --- Soft bay: scalloped shoreline (sand fingers + shallow lip) ---
    for x in range(bx0, bx1 + 1):
        base = plan.z1 + 4 + ((x * 7 + 3) % 5)  # 4..8 past porch
        lobe = 2 if ((x // 3) % 2 == 0) else 0
        sand_end = min(bz1 - 3, base + lobe)
        if x % 5 == 0:
            sand_end = min(bz1 - 2, sand_end + 2)
        if x % 7 == 0:
            sand_end = max(plan.z1 + 3, sand_end - 2)

        for z in range(plan.z1 + 1, bz1 + 1):
            if z <= sand_end:
                top = "sandstone" if z == sand_end and (x + z) % 2 == 0 else "sand"
                put(x, gy, z, top)
                put(x, gy - 1, z, "sand")
                put(x, gy - 2, z, "stone")
            elif z == sand_end + 1:
                put(x, gy, z, "water")
                put(x, gy - 1, z, "sand")
                put(x, gy - 2, z, "stone")
            else:
                put(x, gy, z, "water")
                put(x, gy - 1, z, "water")
                put(x, gy - 2, z, "water")
                put(x, gy - 3, z, "sand")
                put(x, gy - 4, z, "stone")

        if x in (bx0, bx0 + 1, bx1 - 1, bx1):
            tip = min(bz1, sand_end + 1 + (x % 2))
            for z in range(sand_end + 1, tip + 1):
                put(x, gy, z, "sand")
                put(x, gy - 1, z, "sand")

    # Land approach north of café stays grass; path from north entry
    for x in range(plan.x0, plan.x1 + 1):
        for z in range(plan.z0 - 3, plan.z0):
            put(x, gy, z, "dirt_path" if abs(x - (plan.x0 + plan.width // 2)) <= 1 else "grass_block")

    # --- Café foundation / floor ---
    for x in range(plan.x0, plan.x1 + 1):
        for z in range(plan.z0, plan.z1 + 1):
            put(x, gy, z, "oak_planks")
            put(x, gy - 1, z, "cobblestone")

    # Porch strip; open vista — no continuous fence (corner posts only)
    for x in range(plan.x0, plan.x1 + 1):
        put(x, gy, plan.z1 + 1, "oak_planks")
        put(x, gy - 1, plan.z1 + 1, "cobblestone")
    for x in (plan.x0, plan.x1):
        put(x, wall_bottom, plan.z1 + 1, "oak_fence")
        put(x, wall_bottom, plan.z1 + 2, "oak_fence")
    # low open edge: trapdoors flush as hint of rail without blocking view
    for x in range(plan.x0 + 2, plan.x1 - 1, 3):
        put(x, gy, plan.z1 + 2, "oak_trapdoor[facing=south,half=top,open=false]")

    # --- Posts / frame ---
    post_xs = [plan.x0, plan.x0 + 5, plan.x0 + 10, plan.x0 + 15, plan.x1]
    for x in post_xs:
        for y in range(wall_bottom, wall_top + 1):
            put(x, y, plan.z0, "dark_oak_log[axis=y]")
            put(x, y, plan.z1, "dark_oak_log[axis=y]")
    for z in (plan.z0, plan.z0 + 4, plan.z0 + 8, plan.z1):
        for y in range(wall_bottom, wall_top + 1):
            put(plan.x0, y, z, "dark_oak_log[axis=y]")
            put(plan.x1, y, z, "dark_oak_log[axis=y]")

    # --- Walls: closed N/E/W, open arched S ---
    for x in range(plan.x0 + 1, plan.x1):
        for y in range(wall_bottom, wall_top + 1):
            if x in post_xs:
                continue
            put(x, y, plan.z0, "white_concrete")
    for x in (plan.x0 + 3, plan.x0 + 8, plan.x0 + 13, plan.x1 - 3):
        put(x, wall_bottom + 2, plan.z0, "glass_pane")
        put(x, wall_bottom + 3, plan.z0, "glass_pane")

    for z in range(plan.z0 + 1, plan.z1):
        for y in range(wall_bottom, wall_top + 1):
            put(plan.x0, y, z, "white_concrete")
            put(plan.x1, y, z, "white_concrete")

    put(plan.x0, wall_bottom, plan.z1 - 2, "birch_door[half=lower,facing=east,hinge=left]")
    put(plan.x0, wall_bottom + 1, plan.z1 - 2, "birch_door[half=upper,facing=east,hinge=left]")
    put(plan.x1, wall_bottom, plan.z1 - 2, "birch_door[half=lower,facing=west,hinge=right]")
    put(plan.x1, wall_bottom + 1, plan.z1 - 2, "birch_door[half=upper,facing=west,hinge=right]")
    put(plan.x0 + 1, wall_bottom, plan.z1 - 2, "blue_carpet")
    put(plan.x1 - 1, wall_bottom, plan.z1 - 2, "blue_carpet")
    put(plan.x0, wall_bottom + 2, plan.z1 - 2, "blue_concrete")
    put(plan.x1, wall_bottom + 2, plan.z1 - 2, "blue_concrete")

    for i in range(len(post_xs) - 1):
        xa, xb = post_xs[i], post_xs[i + 1]
        for x in range(xa + 1, xb):
            for y in range(wall_bottom, wall_top):
                put(x, y, plan.z1, "air")
            put(x, wall_top, plan.z1, "dark_oak_log[axis=x]")
        if xb - xa >= 3:
            put(xa + 1, wall_top - 1, plan.z1, "dark_oak_stairs[facing=east,half=top]")
            put(xb - 1, wall_top - 1, plan.z1, "dark_oak_stairs[facing=west,half=top]")

    # --- Ceiling / vault ribs ---
    for x in range(plan.x0, plan.x1 + 1):
        for z in range(plan.z0, plan.z1 + 1):
            put(x, wall_top + 1, z, "spruce_planks")
    for z in range(plan.z0, plan.z1 + 1):
        put(plan.x0, wall_top + 1, z, "dark_oak_log[axis=z]")
        put(plan.x1, wall_top + 1, z, "dark_oak_log[axis=z]")
    for x in post_xs:
        for z in range(plan.z0, plan.z1 + 1):
            put(x, wall_top, z, "dark_oak_log[axis=z]")
    for x in (plan.x0 + 3, plan.x0 + 8, plan.x0 + 13, plan.x1 - 3):
        put(x, wall_top, plan.z0 + 3, "lantern[hanging=true]")
        put(x, wall_top, plan.z0 + 8, "lantern[hanging=true]")

    for x in range(plan.x0 - 1, plan.x1 + 2):
        put(x, wall_top + 1, plan.z1 + 1, "spruce_stairs[facing=north]")
        put(x, wall_top + 1, plan.z0 - 1, "spruce_stairs[facing=south]")

    # --- Service counter (west / left, L-shaped) ---
    for x in range(plan.x0 + 2, plan.x0 + 8):
        put(x, wall_bottom, plan.z0 + 2, "dark_oak_planks")
        put(x, wall_bottom + 1, plan.z0 + 2, "dark_oak_slab[type=bottom]")
    for z in range(plan.z0 + 2, plan.z0 + 6):
        put(plan.x0 + 2, wall_bottom, z, "dark_oak_planks")
        put(plan.x0 + 2, wall_bottom + 1, z, "dark_oak_slab[type=bottom]")
    put(plan.x0 + 4, wall_bottom + 1, plan.z0 + 2, "iron_block")
    put(plan.x0 + 5, wall_bottom + 1, plan.z0 + 2, "glass")
    put(plan.x0 + 6, wall_bottom + 1, plan.z0 + 2, "glass")
    put(plan.x0 + 3, wall_bottom, plan.z0 + 1, "barrel[facing=south]")
    put(plan.x0 + 4, wall_bottom, plan.z0 + 1, "smoker[facing=south]")

    # Larger chalkboard menu wall + denser signage
    for x in (plan.x0 + 1, plan.x0 + 2, plan.x0 + 3):
        for y in range(wall_bottom + 2, wall_bottom + 5):
            put(x, y, plan.z0 + 1, "black_concrete")
    put(plan.x0 + 1, wall_bottom + 3, plan.z0 + 2, "oak_wall_sign[facing=south]")
    put(plan.x0 + 2, wall_bottom + 3, plan.z0 + 2, "oak_wall_sign[facing=south]")
    put(plan.x0 + 3, wall_bottom + 3, plan.z0 + 2, "oak_wall_sign[facing=south]")
    put(plan.x0 + 2, wall_bottom + 4, plan.z0 + 2, "oak_wall_sign[facing=south]")
    # Today's special A-frame near counter
    put(plan.x0 + 5, wall_bottom, plan.z0 + 4, "dark_oak_fence")
    put(plan.x0 + 5, wall_bottom + 1, plan.z0 + 4, "oak_sign[rotation=4]")
    # Hanging brand signs on south posts
    for x in (plan.x0 + 5, plan.x0 + 10, plan.x0 + 15):
        put(x, wall_top - 1, plan.z1 + 1, "oak_wall_sign[facing=south]")
    # Blue brand banners on side walls
    put(plan.x0 + 1, wall_bottom + 3, plan.z0 + 7, "blue_wall_banner[facing=east]")
    put(plan.x1 - 1, wall_bottom + 3, plan.z0 + 7, "blue_wall_banner[facing=west]")
    # Exterior menu board on beach
    put(plan.x0 + 2, wall_bottom, plan.z1 + 3, "dark_oak_fence")
    put(plan.x0 + 2, wall_bottom + 1, plan.z1 + 3, "black_concrete")
    put(plan.x0 + 2, wall_bottom + 2, plan.z1 + 3, "oak_wall_sign[facing=south]")

    # --- Seating ---
    table_spots = [
        (plan.x0 + 10, plan.z0 + 3),
        (plan.x0 + 14, plan.z0 + 3),
        (plan.x0 + 10, plan.z0 + 7),
        (plan.x0 + 14, plan.z0 + 7),
        (plan.x0 + 17, plan.z0 + 5),
    ]
    for tx, tz in table_spots:
        put(tx, wall_bottom, tz, "oak_fence")
        put(tx, wall_bottom + 1, tz, "oak_pressure_plate")
        for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            cx, cz = tx + dx, tz + dz
            if plan.x0 < cx < plan.x1 and plan.z0 < cz < plan.z1:
                put(
                    cx,
                    wall_bottom,
                    cz,
                    "oak_stairs[facing=south]"
                    if dz == -1
                    else "oak_stairs[facing=north]"
                    if dz == 1
                    else "oak_stairs[facing=east]"
                    if dx == -1
                    else "oak_stairs[facing=west]",
                )
                # cushions on seats only (not table)
                put(cx, wall_bottom + 1, cz, "blue_carpet")

    for x in (plan.x0 + 3, plan.x0 + 7, plan.x0 + 12, plan.x0 + 16):
        put(x, wall_bottom, plan.z1 - 1, "oak_slab[type=bottom]")
        put(x, wall_bottom, plan.z1 - 2, "oak_fence")
        put(x, wall_bottom + 1, plan.z1 - 2, "blue_carpet")

    # --- Dense plants ---
    plant_spots = [
        (plan.x0 + 1, plan.z0 + 3, "potted_azalea_bush"),
        (plan.x0 + 1, plan.z0 + 5, "potted_flowering_azalea_bush"),
        (plan.x0 + 1, plan.z0 + 8, "potted_fern"),
        (plan.x1 - 1, plan.z0 + 3, "potted_flowering_azalea_bush"),
        (plan.x1 - 1, plan.z0 + 5, "potted_azalea_bush"),
        (plan.x1 - 1, plan.z0 + 8, "potted_cornflower"),
        (plan.x0 + 7, plan.z0 + 1, "potted_azalea_bush"),
        (plan.x0 + 9, plan.z0 + 1, "potted_white_tulip"),
        (plan.x0 + 11, plan.z0 + 1, "potted_flowering_azalea_bush"),
        (plan.x0 + 13, plan.z0 + 1, "potted_fern"),
        (plan.x0 + 8, plan.z0 + 5, "potted_bamboo"),
        (plan.x0 + 16, plan.z0 + 3, "potted_oxeye_daisy"),
        (plan.x0 + 3, plan.z0 + 5, "potted_cactus"),
    ]
    for px, pz, plant in plant_spots:
        put(px, wall_bottom, pz, plant)

    # hanging greenery on south lintels / beams
    for x in post_xs:
        put(x, wall_top - 1, plan.z1, "moss_carpet")
        put(x, wall_top - 2, plan.z1, "cave_vines")
    for x in (plan.x0 + 3, plan.x0 + 7, plan.x0 + 12, plan.x1 - 3):
        put(x, wall_top - 1, plan.z0 + 2, "moss_carpet")
        put(x, wall_top, plan.z0 + 6, "hanging_roots")

    # exterior planter clusters on beach / porch corners
    for px, pz, bush in (
        (plan.x0 - 1, plan.z1, "azalea"),
        (plan.x0 - 1, plan.z1 + 2, "flowering_azalea"),
        (plan.x1 + 1, plan.z1, "flowering_azalea"),
        (plan.x1 + 1, plan.z1 + 2, "azalea"),
        (plan.x0 + 8, plan.z1 + 4, "pink_petals"),
        (plan.x0 + 12, plan.z1 + 4, "pink_petals"),
    ):
        if plan.bounds.contains((px, wall_bottom, pz)):
            put(px, gy, pz, "moss_block" if "azalea" in bush else "sand")
            put(px, wall_bottom, pz, bush)
    for px, pz, flower in (
        (plan.x0 + 4, plan.z1 + 3, "lilac"),
        (plan.x1 - 4, plan.z1 + 3, "peony"),
    ):
        if plan.bounds.contains((px, wall_bottom + 1, pz)):
            put(px, gy, pz, "moss_block")
            put(px, wall_bottom, pz, f"{flower}[half=lower]")
            put(px, wall_bottom + 1, pz, f"{flower}[half=upper]")

    # Exterior directional signpost on beach (offset so it does not block center vista)
    sx, sz = plan.x1 - 2, plan.z1 + 4
    put(sx, wall_bottom, sz, "oak_fence")
    put(sx, wall_bottom + 1, sz, "oak_fence")
    put(sx, wall_bottom + 2, sz, "oak_sign[rotation=8]")
    put(sx, wall_bottom + 1, sz - 1, "oak_wall_sign[facing=north]")
    put(sx, wall_bottom + 1, sz + 1, "oak_wall_sign[facing=south]")

    put(plan.x0 + 1, wall_bottom + 3, plan.z0 + 4, "lantern[hanging=false]")
    put(plan.x1 - 1, wall_bottom + 3, plan.z0 + 4, "lantern[hanging=false]")

    return ops


def anchor_expectations(plan: CafePlan) -> dict[tuple[int, int, int], str]:
    gy = plan.ground_y
    return {
        (plan.x0 + 5, gy, plan.z0 + 5): "minecraft:oak_planks",
        (plan.x0, gy + 1, plan.z0): "minecraft:dark_oak_log",
        (plan.x0 + 2, gy + 1, plan.z0 + 2): "minecraft:dark_oak_planks",
        (plan.x0 + 10, gy, plan.z1 + 2): "minecraft:sand",
        (plan.x0 + 10, gy, plan.bounds.max_z - 1): "minecraft:water",
        (plan.x0 + 3, gy + 5, plan.z0 + 3): "minecraft:lantern",
        (plan.x0 + 1, gy + 3, plan.z0 + 1): "minecraft:black_concrete",
    }
