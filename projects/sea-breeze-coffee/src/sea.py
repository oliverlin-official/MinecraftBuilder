"""Stylized distant sea: glass / wool / concrete, ≥8 chunks from view origin.

Replaces nearby water with beach. Does not rewrite the locked café.
"""

from __future__ import annotations

from cafe import Bounds


CENTER_X = 44
CENTER_Z = 62
CHUNK = 16
SEA_DISTANCE = 8 * CHUNK  # 128
SEA_Z0 = CENTER_Z + SEA_DISTANCE  # 190
SEA_Z1 = SEA_Z0 + 2 * CHUNK - 1  # 221
SEA_X0 = CENTER_X - 4 * CHUNK  # -20
SEA_X1 = CENTER_X + 4 * CHUNK - 1  # 107
GROUND_Y = -10


def write_bounds() -> Bounds:
    return Bounds(SEA_X0, -16, 40, SEA_X1, 16, SEA_Z1)


def cafe_protect() -> Bounds:
    return Bounds(33, -12, 48, 54, 8, 63)


HOUSE_PADS = (
    (16, 48, 26, 57),
    (16, 58, 24, 67),
    (17, 68, 26, 76),
    (61, 48, 72, 57),
    (63, 59, 73, 68),
    (62, 69, 72, 77),
)


def in_house_pad(x: int, z: int) -> bool:
    for x0, z0, x1, z1 in HOUSE_PADS:
        if x0 <= x <= x1 and z0 <= z <= z1:
            return True
    return False


def beach_half_width(z: int) -> int:
    """Widen from café front (~30) to 8-chunk sea (64)."""
    if z <= 64:
        return 30
    if z >= SEA_Z0:
        return 64
    t = (z - 64) / float(SEA_Z0 - 64)
    return int(30 + t * (64 - 30))


def sea_palette(x: int, z: int, layer: int) -> str:
    """layer 0 = surface, 1 = mid, 2 = deep. Glass / wool / concrete only."""
    dist = z - SEA_Z0
    n = (x * 3 + z * 7 + layer) % 6
    if dist <= 2:
        foam = (
            "white_wool",
            "white_concrete",
            "white_stained_glass",
            "light_blue_wool",
            "light_blue_stained_glass",
            "white_concrete",
        )
        return foam[n]
    if dist <= 10:
        shallow = (
            (
                "light_blue_wool",
                "light_blue_concrete",
                "light_blue_stained_glass",
                "cyan_wool",
                "glass",
                "light_blue_wool",
            ),
            (
                "light_blue_concrete",
                "cyan_concrete",
                "light_blue_wool",
                "cyan_wool",
                "light_blue_concrete",
                "cyan_concrete",
            ),
            (
                "cyan_concrete",
                "light_blue_concrete",
                "cyan_wool",
                "blue_concrete",
                "cyan_concrete",
                "light_blue_concrete",
            ),
        )
        return shallow[layer][n]
    deep = (
        (
            "blue_wool",
            "cyan_wool",
            "blue_stained_glass",
            "light_blue_stained_glass",
            "cyan_concrete",
            "blue_wool",
        ),
        (
            "blue_concrete",
            "cyan_concrete",
            "blue_wool",
            "cyan_wool",
            "blue_concrete",
            "cyan_concrete",
        ),
        (
            "blue_concrete",
            "blue_concrete",
            "cyan_concrete",
            "blue_wool",
            "blue_concrete",
            "cyan_concrete",
        ),
    )
    return deep[layer][n]


def generate_stylized_sea() -> dict[tuple[int, int, int], str]:
    ops: dict[tuple[int, int, int], str] = {}
    b = write_bounds()
    prot = cafe_protect()
    gy = GROUND_Y

    def put(x: int, y: int, z: int, block: str) -> None:
        if not b.contains((x, y, z)):
            return
        if prot.contains((x, y, z)):
            return
        if in_house_pad(x, z) and y >= gy:
            return
        ops[(x, y, z)] = block

    # 1) Near water → sand beach (do not keep a bay at the café)
    for x in range(16, 76):
        for z in range(64, 88):
            half = beach_half_width(z)
            if abs(x - CENTER_X) > half:
                continue
            put(x, gy, z, "sand")
            put(x, gy - 1, z, "sand")
            put(x, gy - 2, z, "stone")
            put(x, gy - 3, z, "stone")

    # 2) Long sand approach out to 8 chunks
    for z in range(88, SEA_Z0):
        half = beach_half_width(z)
        for x in range(CENTER_X - half, CENTER_X + half + 1):
            edge = abs(abs(x - CENTER_X) - half) <= 1
            put(x, gy, z, "sandstone" if edge and (x + z) % 3 == 0 else "sand")
            put(x, gy - 1, z, "sand")
            put(x, gy - 2, z, "stone")
            if (x + z * 3) % 17 == 0 and abs(x - CENTER_X) < half - 2:
                put(x, gy + 1, z, "dandelion" if (x + z) % 2 == 0 else "oxeye_daisy")

    # 3) Stylized sea ≥8 chunks from center
    for z in range(SEA_Z0, SEA_Z1 + 1):
        for x in range(SEA_X0, SEA_X1 + 1):
            put(x, gy, z, sea_palette(x, z, 0))
            put(x, gy - 1, z, sea_palette(x, z, 1))
            put(x, gy - 2, z, sea_palette(x, z, 2))
            put(x, gy + 1, z, "air")

    return ops


def anchor_expectations() -> dict[tuple[int, int, int], str]:
    gy = GROUND_Y
    return {
        (44, gy, 80): "minecraft:sand",
        (44, gy, 55): "minecraft:oak_planks",
    }


SEA_SURFACE_OK = {
    "minecraft:white_wool",
    "minecraft:white_concrete",
    "minecraft:white_stained_glass",
    "minecraft:light_blue_wool",
    "minecraft:light_blue_concrete",
    "minecraft:light_blue_stained_glass",
    "minecraft:cyan_wool",
    "minecraft:cyan_concrete",
    "minecraft:blue_wool",
    "minecraft:blue_concrete",
    "minecraft:blue_stained_glass",
    "minecraft:glass",
}
