# TASK_STATE

```text
PROJECT:
MEDIEVAL_WATERSIDE_TOWN
+ ENVIRONMENT FACTORY SOFTWARE

PROFILE:
PROFILE_B — SETTLEMENT (+ terrain creation sub-task)

MINECRAFT_VERSION:
1.21.11 (GDPC HTTP interface 1.8.4 on localhost:9000, live)

BUILD_AREA:
x -128..127, z -128..127 (256×256), y -64..319

CURRENT_STAGE:
SOFTWARE / M0_VISUAL_PROBE COMPLETE
SOFTWARE / SERVER_S0_EDIT_RENDER_BRIDGE COMPLETE
TOWN PRODUCTION: COMPLETE (all stages QA'd; final gate P0=0, P1=0)

LOCKS:
- MACRO_TERRAIN:    TRUE
- RIVERS:           TRUE
- MAIN_ROADS:       TRUE (8 routes + bridge, connectivity PASS)
- BRIDGES:          TRUE (stone bridge x13-33, z-3)
- DISTRICTS:        TRUE (5 districts)
- FOOTPRINTS:       TRUE (18 buildings, 0 defects)
- LANDMARKS:        TRUE (bridge primary; church + mill secondary)
- ARCHITECTURE:     TRUE (building QA PASS)
- PALETTE:          TRUE (medieval: cobble/stone brick/spruce/dark oak/plaster)

OPEN_DEFECTS:
- P4: old town strings along the main road rather than clustering denser at
  the bridgehead (visual iteration candidate)
- P5: WELL_SQUARE (−2,14) has no plaza paving (market square does)

COMPLETION GATE (qa/final_qa.json):
routes connected PASS | buildings accessible PASS | protected regions intact
PASS | landmarks complete PASS | road graph PASS | district logic PASS |
landmark hierarchy PASS | family coverage PASS | terrain/water integrity PASS

RUN DIRECTORY:
runs/2026-09-07_001/ (manifest in qa/, viz/planning_overlay.png,
viz/final_render.png)

PROTECTED_REGIONS:
RIVER corridor, bridge, church pad, market square (enforced via qa corridors
+ road cells registry)

LAST_CHECKPOINT:
Remote server S0 edit/render acceptance PASS. GDPC 8.1 + custom cabin generator
committed 1432 bounded operations; seven structural anchors passed before and
after server restart. WorldEdit one-block write/readback/restore passed through
the real OP player's HMC command channel. HeadlessMC Visual Probe produced
front and two isometric 854x480 renders. Artifacts are under
runs/server_cabin_20260908/.

CURRENT_OBJECTIVE:
Server S0 edit/render bridge complete. Harden the persistent remote runtime
before larger generation jobs.

NEXT_ACTION:
bind GDMC port 9000 to loopback or firewall it; replace Screen sessions with
managed services; then proceed to Probe V0.2 world-sync/camera entity or a
larger bounded generator acceptance.
```

## Operator note

The town is centered on the world spawn area: bridge at x 13..33, z -3;
market square at (6,-6); church on the rise at (55,-75); mill at (35..45, 47..55);
docks east bank z≈20..28; farms south around (-24..21, 78..106).
If the player character was standing near (0,0) during generation they may be
inside blocks — fly out or /tp.

M0 does not write the world. Visual probe only moves the local spectator camera
and captures the framebuffer.
