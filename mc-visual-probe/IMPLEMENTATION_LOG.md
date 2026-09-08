# mc-visual-probe implementation log

Milestone: **M0 — mc-visual-probe** COMPLETE (2026-09-07 live Fabric capture)

Date: 2026-09-07

## Routing

```text
CURRENT TASK:
Implement Fabric client visual probe + Python observe client

CURRENT STAGE:
Software implementation (Environment Factory M0)

PRIMARY AUTHORITY:
Minecraft Visual Probe — Technical Specification v1.md

SECONDARY AUTHORITY:
Minecraft Visual Observation & Critic Protocol — Specification v1.md

SPECIALIST:
mc-visual-probe (visual sensor backend)

WORLD WRITE:
NOT ALLOWED
```

## What was built

Fabric client-only mod `mc-visual-probe/` exposing a localhost HTTP sensor:

- `GET /v1/status`
- `GET /v1/camera/pose` (readback)
- `POST /v1/observe`

Python client: `src/mcenv/visual_probe.py`
Acceptance driver: `tools/m0_visual_probe_acceptance.py`

HTTP is bound to `127.0.0.1:8765` only. A session token is written to:

- `<gameDir>/visual-probe/session.json`
- `%TEMP%/mc-visual-probe-session.json`

All camera / FOV / HUD / framebuffer work is queued onto the Minecraft client thread. Observe waits for chunk radius + stable ticks before `ScreenshotRecorder.takeScreenshot`.

## Deviations from the V1 technical spec

| Spec | M0 behavior |
|---|---|
| Gold-path `CLIENT_CAMERA_ENTITY` (Probe V0.3) | Not implemented. M0 uses spec MVP-A `PLAYER_SPECTATOR` so chunks load around the camera. Documented as `camera_backend: PLAYER_SPECTATOR`. |
| Async `202 Accepted` + `GET /capture/{id}` | Synchronous `POST /v1/observe` with timeout (spec-allowed MVP). |
| `/v1/profile` as its own endpoint | Observe applies PRODUCTION defaults (hide HUD, first person, requested FOV) and restores them. DEBUG/SHOWCASE profiles are not separate APIs. |
| Freeze time / weather / entities | Not frozen. Metadata records time and weather. Before/after lighting stability is a later QA profile concern. |
| Requested capture resolution | Reports actual framebuffer size. Does not resize the Minecraft window. |
| World revision / sync anchors | Optional. If `sync_anchors` is omitted, fence is skipped (Probe V0.2 work). Empty anchors never return `WORLD_NOT_SYNCED`. |
| Restore player after capture | After PNG write, player position/gamemode are restored so the local player is not left in spectator at the last pose. |
| Combined observe request shape | Accepts the user-required flat `{x,y,z,yaw,pitch,fov,observation_id}` and the spec nested `pose` object. |
| `ScreenshotRecorder.takeScreenshot` | 1.21.11 copies the color attachment asynchronously via `CommandEncoder.copyTextureToBuffer`. Observe waits for that callback instead of treating takeScreenshot as synchronous. |
| Pause / lost-focus | Observe disables `pauseOnLostFocus`, closes `currentScreen`, and refuses to capture while `client.isPaused()`. Otherwise background-agent runs freeze the framebuffer on the ESC menu. |

## Safety

- No world-write API, no `/setblock`, no WorldEdit, no GDPC.
- No Replay Mod automation.
- Localhost bind only.
- Session token required on every `/v1` call.

## Build

`gradle 9.5.1` + Loom `1.17.20` (`net.fabricmc.fabric-loom-remap`) compiled Yarn 1.21.11+build.6 sources and remapped:

```text
mc-visual-probe/build/libs/mc-visual-probe-0.1.0.jar
```

The jar was copied into the PCL Fabric 1.21.11 `mods/` folder. Fabric API 0.141.4 is already present.

Loom printed `Cannot remap modifiers because it does not exist in any of the targets []` during configuration; the build still succeeded.

## Live acceptance

PASS on 2026-09-07 against a real Fabric 1.21.11 client (superflat test world).

```text
py -3.12 tools/m0_visual_probe_acceptance.py
```

Saved outputs: `runs/m0_visual_probe/`

| Shot | Pose (actual) | Notes |
|---|---|---|
| A.png | x 10.72, y -58.38, z -1.63, yaw 318.45, pitch 14.70, fov 70 | HUD-off grass horizon + slimes |
| B.png | same xz, y -54.38, yaw 78.45, pitch -10.30, fov 70 | Distinct sky/ground framing |
| A2.png | identical to A | Same camera pose; MAE vs A = 0.69 |

`acceptance_report.json`: pose_A_matches_A2 true, pose_A_distinct_from_B true, resolution 854×480, dimension `minecraft:overworld`, minecraft_version `1.21.11-Fabric 0.19.2`.

Earlier false PASS captured the ESC pause menu (lost-focus pause). That is fixed by disabling `pauseOnLostFocus` for the duration of observe.
