# Remote Server Cabin Acceptance — 2026-09-08

## Result

PASS for the requested server-side edit/render bridge. No local Minecraft
client was launched.

## Environment

- Minecraft/Fabric: 1.21.11 / Fabric Loader 0.19.5
- GDMC HTTP Interface: 1.8.4, server port 9000
- GDPC: 8.1.0 in an isolated remote Python virtual environment
- WorldEdit: 7.4.2+7450-eb8e82c, server-side
- Render worker: HeadlessMC + Xvfb + llvmpipe + Visual Probe
- Remote game directory:
  `/home/ubuntu/headlessMC/srv/hmc-client/.minecraft`

## Protected edit transaction

- Semantic object: `CABIN_SERVER_001`
- Cabin origin: `(180, -10, 0)`
- Allowed write bounds: `(179, -11, -1)` through `(191, 2, 13)`
- The cabin is outside the locked town area `x/z = -128..127`.
- Pre-write scan: 2730 blocks read, flat surface, zero non-air blocks in the
  construction airspace.
- Rollback sources: full NBT structure snapshot and state/data-aware block
  snapshot.
- Custom generator: `mcenv.cabin.generate_cabin`, seed `20260907`.
- GDPC write: 1432 operations in 0.578 seconds.
- Structural readback: all 7 anchors passed, including door halves, stair
  orientation, log axis, and lit campfire.
- Persistence: all anchors still passed after an unplanned server-process exit
  and restart.

## WorldEdit smoke test

- Selected exactly one unused block at `(191, -9, 13)` through the real OP
  player's HMC-Specifics command channel.
- `//set minecraft:gold_block`: GDPC readback returned `minecraft:gold_block`.
- `//set minecraft:air`: readback matched the original air block.
- Result: write PASS, restoration PASS; cabin was not touched.

Using GDMC `/command` with `execute as HeadlessBuilderExample` returned successful
command statuses but did not preserve a usable WorldEdit player session. The
working automation path is the persistent HMC terminal's `/` command bridge,
which sends a real player chat command.

## Visual Probe acceptance

Three corrected daytime captures passed at 854x480:

- Front: `(185.5, -1.0, 27.5)`, yaw `180`, pitch `18`, FOV `70`
- Southeast isometric: `(205.5, 2.0, 24.5)`, yaw `142`, pitch `22`, FOV `72`
- Southwest isometric: `(164.5, 2.0, 24.5)`, yaw `-142`, pitch `22`, FOV `72`

Requested and actual poses matched except for harmless floating-point Y
precision. The images visibly confirm the facade, door and windows, gabled
roof, both side elevations, porch lighting, chimney, lit campfire, and smoke.

Visual critic result: the cabin is structurally coherent and readable from all
three views. Its surroundings remain an intentionally empty superflat test
canvas, so settlement integration and landscaping were not evaluated.

## Deployment findings

1. HeadlessMC/HMC-Specifics needs a pseudo-TTY. A plain `nohup` launch with
   stdin redirected fails during JLine initialization; a detached GNU Screen
   session works.
2. The HMC client must retain the same GDMC 1.8.4 mod as the server. Removing it
   causes Fabric registry synchronization to reject
   `gdmc_http_interface:saved_build_area_name_argument`. WorldEdit itself can
   remain server-only for this workflow.
3. The client should not use HeadlessMC `-lwjgl` for PNG capture. The working
   path is real Xvfb plus Mesa llvmpipe.
4. A GDMC named build area persists, but the active/current build-area selection
   was empty after server restart and had to be restored with
   `buildarea load SERVER_CABIN_001`.
5. Visual Probe `render_profile` is a strict enum. `PRODUCTION` works; arbitrary
   labels return `SCREENSHOT_FAILED`.
6. Minecraft yaw signs matter: from the southeast toward northwest uses
   positive yaw; from the southwest toward northeast uses negative yaw.
7. The prior server process exited without a graceful shutdown sequence and
   without a kernel OOM record. Both server and render worker now run in
   detached Screen sessions.
8. Port 9000 currently listens on all interfaces. Because the GDMC command
   endpoint can execute Minecraft commands, bind it to loopback or enforce a
   host/cloud firewall before treating this as a persistent environment.
9. The 3.6 GiB host currently reports about 1.3 GiB available with both Java
   processes active. Large render distances or generators need memory
   monitoring.

## Current remote state

- `mc-server` Screen session: running
- `hmc-render` Screen session: running
- Minecraft `59916`: listening
- GDMC `9000`: listening, owned by the server Java process
- Visual Probe `127.0.0.1:8766`: `READY`
- Active HMC client mods: Fabric API, GDMC HTTP Interface, HMC-Specifics, Visual
  Probe
- Current build area: `SERVER_CABIN_001`
