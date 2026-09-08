"""Sea Breeze context — two flanking chunks of forest, cottages, and beach.

Viewpoint: 44, -9, 62 (café porch). Does not rewrite the locked café footprint.
"""

from __future__ import annotations

from dataclasses import dataclass

from cafe import Bounds


@dataclass(frozen=True)
class ContextPlan:
    semantic_id: str = "SEA_BREEZE_CONTEXT_001"
    ground_y: int = -10
    seed: int = 20260908
    view_x: int = 44
    view_z: int = 62

    # Two context chunks flanking the view: west 16-31, east 60-75
    # plus beach/forest corridor. Matches GDMC SEA_BREEZE_COFFEE expanded area.
    @property
    def bounds(self) -> Bounds:
        return Bounds(16, -16, 40, 75, 16, 87)

    @property
    def cafe_protect(self) -> Bounds:
        # Locked café + porch; context may still terraform beach south of this.
        return Bounds(33, -12, 48, 54, 8, 63)


def generate_context(plan: ContextPlan) -> dict[tuple[int, int, int], str]:
    ops: dict[tuple[int, int, int], str] = {}
    gy = plan.ground_y
    b = plan.bounds
    prot = plan.cafe_protect

    def in_protect(x: int, y: int, z: int) -> bool:
        return prot.contains((x, y, z))

    def put(x: int, y: int, z: int, block: str) -> None:
        pos = (x, y, z)
        if not b.contains(pos):
            return
        if in_protect(x, y, z):
            return
        ops[pos] = block

    def occupied_footprint(x: int, z: int) -> bool:
        return (x, gy, z) in ops and not str(ops[(x, gy, z)]).startswith(
            ("grass", "dirt", "sand", "podzol", "moss", "water", "stone", "sandstone")
        )

    house_pads: set[tuple[int, int]] = set()

    def mark_pad(x0: int, z0: int, w: int, d: int) -> None:
        for x in range(x0 - 1, x0 + w + 1):
            for z in range(z0 - 1, z0 + d + 1):
                house_pads.add((x, z))

    def place_cottage(
        x0: int,
        z0: int,
        w: int,
        d: int,
        door_face: str,
        wall: str,
        log: str,
        roof: str,
        floor: str,
    ) -> None:
        mark_pad(x0, z0, w, d)
        x1, z1 = x0 + w - 1, z0 + d - 1
        # clear interior air
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                for y in range(gy + 1, gy + 8):
                    put(x, y, z, "air")
                put(x, gy, z, floor)
                put(x, gy - 1, z, "cobblestone")
        # walls
        for y in range(gy + 1, gy + 5):
            for x in range(x0, x1 + 1):
                put(x, y, z0, log if x in (x0, x1) else wall)
                put(x, y, z1, log if x in (x0, x1) else wall)
            for z in range(z0 + 1, z1):
                put(x0, y, z, log if z in (z0, z1) else wall)
                put(x1, y, z, log if z in (z0, z1) else wall)
        # door
        dx = x0 + w // 2
        dz = z0 + d // 2
        if door_face == "east":
            put(x1, gy + 1, dz, f"oak_door[half=lower,facing=east,hinge=left]")
            put(x1, gy + 2, dz, f"oak_door[half=upper,facing=east,hinge=left]")
            put(x1, gy + 3, dz, "glass_pane")
        elif door_face == "west":
            put(x0, gy + 1, dz, f"oak_door[half=lower,facing=west,hinge=left]")
            put(x0, gy + 2, dz, f"oak_door[half=upper,facing=west,hinge=left]")
            put(x0, gy + 3, dz, "glass_pane")
        elif door_face == "south":
            put(dx, gy + 1, z1, f"oak_door[half=lower,facing=south,hinge=left]")
            put(dx, gy + 2, z1, f"oak_door[half=upper,facing=south,hinge=left]")
        # windows
        put(x0 + 2, gy + 3, z0, "glass_pane")
        put(x1 - 2, gy + 3, z0, "glass_pane")
        if d > 4:
            put(x0, gy + 3, z0 + 2, "glass_pane")
            put(x1, gy + 3, z0 + 2, "glass_pane")
        # gable roof along X
        for level in range(4):
            za = z0 - 1 + level
            zb = z1 + 1 - level
            y = gy + 5 + level
            if za > zb:
                break
            for x in range(x0 - 1, x1 + 2):
                if za == zb:
                    put(x, y, za, f"{roof}_slab[type=bottom]")
                else:
                    put(x, y, za, f"{roof}_stairs[facing=south]")
                    put(x, y, zb, f"{roof}_stairs[facing=north]")
        # chimney
        put(x0 + 1, gy + 6, z0 + 1, "cobblestone")
        put(x0 + 1, gy + 7, z0 + 1, "cobblestone")
        put(x0 + 1, gy + 8, z0 + 1, "campfire[lit=true]")
        # porch lantern
        if door_face == "east":
            put(x1 + 1, gy + 1, dz, "oak_fence")
            put(x1 + 1, gy + 2, dz, "lantern[hanging=false]")
        elif door_face == "west":
            put(x0 - 1, gy + 1, dz, "oak_fence")
            put(x0 - 1, gy + 2, dz, "lantern[hanging=false]")
        # tiny garden
        put(x0 + 1, gy + 1, z0 + 1, "potted_azalea_bush")
        put(x1 - 1, gy + 1, z0 + 1, "crafting_table")
        put(x1 - 1, gy + 1, z1 - 1, "white_bed[part=foot,facing=north]")
        put(x1 - 1, gy + 1, z1 - 2, "white_bed[part=head,facing=north]")

    def oak_tree(tx: int, tz: int, height: int = 5, leaf: str = "oak_leaves[persistent=true]") -> None:
        if (tx, tz) in house_pads:
            return
        if in_protect(tx, gy + 1, tz):
            return
        put(tx, gy, tz, "dirt")
        for dy in range(height):
            put(tx, gy + 1 + dy, tz, "oak_log[axis=y]")
        top = gy + height
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in range(-1, 3):
                    if dx == 0 and dz == 0 and dy < 1:
                        continue
                    if abs(dx) == 2 and abs(dz) == 2 and dy != 0:
                        continue
                    put(tx + dx, top + dy, tz + dz, leaf)

    # --- Expanded scalloped bay across full width (before cottages) ---
    for x in range(b.min_x, b.max_x + 1):
        base = 68 + ((x * 7 + 3) % 5)
        lobe = 3 if ((x // 4) % 2 == 0) else 0
        sand_end = min(b.max_z - 4, base + lobe)
        if x % 6 == 0:
            sand_end = min(b.max_z - 3, sand_end + 2)
        if x % 5 == 0:
            sand_end = max(66, sand_end - 2)
        for z in range(64, b.max_z + 1):
            if z <= sand_end:
                top = "sandstone" if z == sand_end and (x + z) % 2 == 0 else "sand"
                put(x, gy, z, top)
                put(x, gy - 1, z, "sand")
                put(x, gy - 2, z, "stone")
                put(x, gy + 1, z, "air")
            elif z == sand_end + 1:
                put(x, gy, z, "water")
                put(x, gy - 1, z, "sand")
                put(x, gy - 2, z, "stone")
                put(x, gy + 1, z, "air")
            else:
                put(x, gy, z, "water")
                put(x, gy - 1, z, "water")
                put(x, gy - 2, z, "water")
                put(x, gy - 3, z, "sand")
                put(x, gy + 1, z, "air")

    # --- Cottages on west and east sides of the vista ---
    place_cottage(18, 50, 7, 6, "east", "white_terracotta", "oak_log[axis=y]", "oak", "oak_planks")
    place_cottage(17, 60, 6, 6, "east", "stripped_oak_log[axis=y]", "spruce_log[axis=y]", "spruce", "spruce_planks")
    place_cottage(19, 70, 6, 5, "south", "birch_planks", "oak_log[axis=y]", "birch", "birch_planks")

    place_cottage(63, 50, 7, 6, "west", "white_terracotta", "oak_log[axis=y]", "oak", "oak_planks")
    place_cottage(65, 61, 6, 6, "west", "spruce_planks", "dark_oak_log[axis=y]", "spruce", "spruce_planks")
    place_cottage(64, 71, 6, 5, "west", "birch_planks", "oak_log[axis=y]", "birch", "birch_planks")

    # dirt paths from cottages toward café / beach view
    for x in range(25, 33):
        put(x, gy, 56, "dirt_path")
        put(x, gy, 63, "dirt_path")
    for x in range(55, 63):
        put(x, gy, 56, "dirt_path")
        put(x, gy, 63, "dirt_path")
    for z in range(56, 64):
        put(25, gy, z, "dirt_path")
        put(62, gy, z, "dirt_path")

    # beach flowers (skip pads)
    flowers = [
        "dandelion",
        "oxeye_daisy",
        "cornflower",
        "pink_petals",
        "azure_bluet",
        "poppy",
        "allium",
    ]
    for x in range(b.min_x, b.max_x + 1, 2):
        for z in (65, 67, 69):
            if (x, z) in house_pads or in_protect(x, gy + 1, z):
                continue
            if (x * 3 + z + plan.seed) % 7 == 0:
                put(x, gy + 1, z, flowers[(x + z) % len(flowers)])

    # --- Forest on west + east + north buffer ---
    tree_sites: list[tuple[int, int, int, str]] = []
    # west forest chunk
    for x in range(16, 32):
        for z in range(40, 74):
            if (x, z) in house_pads or z >= 66:
                continue
            h = 4 + ((x * 5 + z * 3) % 3)
            if (x * 7 + z * 11 + plan.seed) % 11 == 0:
                leaf = "azalea_leaves[persistent=true]" if (x + z) % 5 == 0 else "oak_leaves[persistent=true]"
                tree_sites.append((x, z, h, leaf))
    # east forest chunk
    for x in range(60, 76):
        for z in range(40, 74):
            if (x, z) in house_pads or z >= 66:
                continue
            h = 4 + ((x * 5 + z * 3) % 3)
            if (x * 7 + z * 11 + plan.seed) % 11 == 0:
                leaf = "flowering_azalea_leaves[persistent=true]" if (x + z) % 4 == 0 else "oak_leaves[persistent=true]"
                tree_sites.append((x, z, h, leaf))
    # north forest behind café (not through the building)
    for x in range(16, 76):
        for z in range(40, 48):
            if 33 <= x <= 54:
                continue
            if (x * 7 + z * 11 + plan.seed) % 9 == 0:
                tree_sites.append((x, z, 5, "oak_leaves[persistent=true]"))

    # guaranteed vista trees so the porch always reads forest on both sides
    tree_sites.append((22, 44, 6, "oak_leaves[persistent=true]"))
    tree_sites.append((70, 44, 6, "flowering_azalea_leaves[persistent=true]"))
    tree_sites.append((24, 54, 5, "azalea_leaves[persistent=true]"))
    tree_sites.append((68, 54, 5, "oak_leaves[persistent=true]"))

    for tx, tz, h, leaf in tree_sites:
        oak_tree(tx, tz, h, leaf)

    # undergrowth
    for x in range(16, 32):
        for z in range(42, 70):
            if (x, z) in house_pads or in_protect(x, gy + 1, z):
                continue
            r = (x * 13 + z * 17 + plan.seed) % 8
            if r == 0:
                put(x, gy, z, "podzol")
                put(x, gy + 1, z, "fern")
            elif r == 1:
                put(x, gy + 1, z, "short_grass")
            elif r == 2:
                put(x, gy + 1, z, "azalea")
    for x in range(60, 76):
        for z in range(42, 70):
            if (x, z) in house_pads or in_protect(x, gy + 1, z):
                continue
            r = (x * 13 + z * 17 + plan.seed) % 8
            if r == 0:
                put(x, gy, z, "podzol")
                put(x, gy + 1, z, "fern")
            elif r == 1:
                put(x, gy + 1, z, "short_grass")
            elif r == 2:
                put(x, gy + 1, z, "flowering_azalea")

    return ops


def anchor_expectations(plan: ContextPlan) -> dict[tuple[int, int, int], str]:
    gy = plan.ground_y
    return {
        (18, gy, 50): "minecraft:oak_planks",
        (63, gy, 50): "minecraft:oak_planks",
        (21, gy + 1, 50): "minecraft:white_terracotta",
        (22, gy + 1, 44): "minecraft:oak_log",
        (70, gy, 80): "minecraft:water",
        (20, gy, 80): "minecraft:water",
    }
