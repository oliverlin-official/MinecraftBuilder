# WORLD_CONTRACT — Sea Breeze Coffee

Status: **ACTIVE**

## Confirmed runtime

| Field | Value |
|---|---|
| Minecraft | Java 1.21.11, Fabric Loader 0.19.5 |
| World | `/home/ubuntu/world` — superflat |
| GDMC area | `SEA_BREEZE_COFFEE` -20,-16,40 → 107,16,221 |
| View origin | 44, -9, 62 (café porch) |
| Sea start | z=190 (8 chunks / 128 blocks south of origin) |
| Sea materials | glass, stained glass, wool, concrete — no water |
| Sea body | x -20..107, z 190..221 |
| Facing | Open south (+Z) toward beach/ocean |
| Ground Y | -10 |
| Café footprint (locked) | 34,-10,50 → 53,-10,61 |
| West context chunk | x 16–31 (forest + cottages) |
| East context chunk | x 60–75 (forest + cottages) |
| Runtime | `mc-server` + `hmc-render` HOT_READY |

## Design constraints

| Field | Value |
|---|---|
| Terrain | Local coastal terraform only inside build area |
| Preserve | Café interior/porch; prior cabin (~185,0) |
| Context | Beach south; forest north/flanks; houses on west and east |
| Style | Cream walls, dark timber, blue accents, coastal cottages |
| Clearance | Doorways ≥2; aisles ≥2 |

## Reference binding

- Panorama: `testProject/reference asset (not included in public repository)`
- Style: `testProject/STYLE_BIBLE.md`
- Café generator: `testProject/cafe.py`
- Context generator: `testProject/context.py`
- Edit report: `testProject/runs/sea_breeze_v3/edit_report.json`
