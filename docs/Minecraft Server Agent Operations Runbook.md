# Minecraft Server Agent Operations Runbook

## 1. Purpose and authority

This runbook is the operational entry point for an Agent working on the current
Ubuntu Minecraft node. It covers:

- cold start: both `minecraft-server` and `hmc-render` are stopped;
- hot start: both are already running;
- partial and conflicting states between those two cases;
- readiness checks, log access, graceful shutdown, and common failures.

This runbook assumes the node is already provisioned. If Java, Xvfb,
HeadlessMC, the Fabric server, the client cache, or required mods are absent,
classify the host as `BARE_NODE` and read
`Minecraft Server Node Bootstrap Runbook.md`. `BARE_NODE` is not a cold start.

This document authorizes service inspection and lifecycle operations only. It
does **not** authorize a Minecraft world write. Before any GDPC, WorldEdit, or
custom-generator mutation, the Agent must also read:

1. `TASK_STATE.md`;
2. `Minecraft Environment Adapter — SKILL.md`;
3. the active task's allowed region, protected regions, locks, rollback plan,
   and acceptance criteria.

Service readiness is not world-write permission.

## 2. Operational baseline

The following deployment facts were verified on 2026-09-08. Paths and versions
are the current implementation, not a generic example.

| Item | Current value |
|---|---|
| Host OS/user | Ubuntu 24.04, user `ubuntu` |
| Minecraft/Fabric | Minecraft 1.21.11, Fabric Loader 0.19.5 |
| Server directory | `/home/ubuntu` |
| Server JAR | `/home/ubuntu/fabric-server-mc.1.21.11-loader.0.19.5-launcher.1.1.2.jar` |
| Minecraft port | `59916` |
| GDMC port | `9000` |
| HeadlessMC root | `/home/ubuntu/headlessMC` |
| Launcher | `/home/ubuntu/headlessMC/headlessmc-launcher.jar` |
| Linux launcher script | `/home/ubuntu/headlessMC/connect.bash` |
| Render-worker game directory | `/home/ubuntu/headlessMC/srv/hmc-client/.minecraft` |
| Visual Probe endpoint | `127.0.0.1:8766` |
| Java | OpenJDK 21 |
| Session mechanism | GNU Screen; no systemd units were installed at verification time |

Terminology mapping:

- logical `minecraft-server` = GNU Screen session `mc-server`;
- logical/render service `hmc-render` = GNU Screen session `hmc-render`.

The verified remote identity is `ubuntu@<SERVER_HOSTNAME>`, home
`/home/ubuntu`. From the currently authorized Windows operator machine, the
entry command is:

```powershell
ssh -i <SSH_KEY_PATH> ubuntu@<SERVER_PUBLIC_IP>
```

Do not copy the private key onto the server or embed its contents in this
repository.

The game directory is intentionally the nested path under the HeadlessMC root.
Do not replace it with `/srv/hmc-client/.minecraft`, `$HOME/.minecraft`, or a
Windows PCL game directory.

### Required server mods

Under `/home/ubuntu/mods`:

```text
fabric-api-0.141.6+1.21.11.jar
gdmc_http_interface-1.8.4-1.21.11.jar
worldedit-mod-7.4.2.jar
```

### Required render-worker client mods

Under `/home/ubuntu/headlessMC/srv/hmc-client/.minecraft/mods`:

```text
fabric-api-0.141.6+1.21.11.jar
gdmc_http_interface-1.8.4-1.21.11.jar
hmc-specifics-1.21.11-2.4.0-fabric-release.jar
mc-visual-probe-0.1.0.jar
```

WorldEdit is currently server-only and is disabled in the render-worker game
directory. The matching GDMC mod is nevertheless required on the client because
Fabric synchronizes the custom registry entry
`gdmc_http_interface:saved_build_area_name_argument`. Removing it causes a
registry-remapping disconnect.

## 3. Non-negotiable runtime rules

1. Do not launch a local/PCL Minecraft client for this workflow.
2. Do not launch a duplicate server or render worker. Inspect first.
3. Start the Minecraft server before the render worker during a cold start.
4. HeadlessMC/HMC-Specifics needs a pseudo-TTY. Use GNU Screen; plain
   `nohup ... </dev/null` fails during JLine initialization.
5. Use real LWJGL/OpenGL under Xvfb for PNG capture. Do not use HeadlessMC
   `-lwjgl`, `--stub-renderer`, or another no-render stub for acceptance images.
6. The render worker connects to `127.0.0.1:59916`, not the public server IP.
7. Never print or persist the Visual Probe bearer token in logs, chat, or
   acceptance artifacts.
8. Do not trust a config's bind address without checking the live socket. The
   current GDMC config says `localhost`, but the verified process listened on
   `*:9000`.
9. Do not treat Screen's `Attached` label as a failure. Use sockets, owning
   processes, and authenticated health checks as runtime truth.
10. Screen survives SSH disconnects but not a host reboot. Until managed
    services are actually installed, a reboot leads to a cold start.

## 4. First-minute state audit

Run this audit before choosing a startup path:

```bash
screen -ls 2>&1 || true

ss -ltnp | awk 'NR == 1 || /:59916|:9000|:8766/'

ps -eo pid,ppid,stat,etime,rss,args \
  | grep -E '[f]abric-server-mc|[h]eadlessmc-launcher'

free -h
```

Avoid a broad `pgrep -f` test as the only signal; its pattern can match the
inspection shell itself.

Then check service APIs without exposing credentials:

```bash
curl -fsS --max-time 3 http://127.0.0.1:9000/version
curl -sS --max-time 3 http://127.0.0.1:9000/buildarea

python3 - <<'PY'
import json
import pathlib
import urllib.request

session_path = pathlib.Path(
    "/home/ubuntu/headlessMC/srv/hmc-client/.minecraft/visual-probe/session.json"
)
session = json.loads(session_path.read_text())
request = urllib.request.Request(
    session["base_url"] + "/v1/status",
    headers={"Authorization": "Bearer " + session["token"]},
)
with urllib.request.urlopen(request, timeout=3) as response:
    status = json.load(response)
print(json.dumps({
    "status": status.get("status"),
    "world_loaded": status.get("world_loaded"),
    "dimension": status.get("dimension"),
    "camera_backend": status.get("camera_backend"),
    "render_profile": status.get("render_profile"),
    "world_revision": status.get("world_revision"),
}, ensure_ascii=False))
PY
```

The existence of `session.json` alone proves nothing; it can be stale. A healthy
render worker must return `status=READY` and `world_loaded=true` from the current
authenticated endpoint.

## 5. State classification

| State | Evidence | Action |
|---|---|---|
| `BARE_NODE` | Java/runtime dependencies or required server/client artifacts are absent | Stop daily startup and follow `Minecraft Server Node Bootstrap Runbook.md` |
| `COLD` | No expected Screen sessions, processes, or listeners | Follow the cold-start procedure |
| `HOT_READY` | Server owns `59916` and `9000`; render worker owns loopback `8766`; Probe is `READY` | Reuse both processes; do not restart |
| `SERVER_ONLY` | `59916`/`9000` healthy, no healthy Probe | Validate and start only `hmc-render` |
| `RENDER_WITHOUT_SERVER` | HeadlessMC exists, server is absent, Probe is `NO_WORLD` or unreachable | Start server first; then confirm reconnection or restart only the worker |
| `STALE_SCREEN` | Screen socket exists but expected child/listener does not | Inspect its log; remove only a dead socket with `screen -wipe`, then start the missing service |
| `PORT_CONFLICT` | Expected port is owned by an unexpected process | Stop and diagnose; never start another copy over it |
| `DEGRADED_HOT` | Both Java processes exist but one required API/readiness check fails | Preserve logs and repair only the failing layer |

If systemd units are added later, inspect them with
`systemctl list-unit-files | grep -E 'minecraft|headless|hmc'` and update this
runbook before using systemd as the source of truth. Do not run both systemd and
Screen copies of the same service.

## 6. Cold-start procedure

### 6.1 Preflight

Verify files, dependencies, mods, and memory:

```bash
test -r /home/ubuntu/fabric-server-mc.1.21.11-loader.0.19.5-launcher.1.1.2.jar
test -x /home/ubuntu/headlessMC/connect.bash
test -r /home/ubuntu/headlessMC/headlessmc-launcher.jar
test -d /home/ubuntu/headlessMC/srv/hmc-client/.minecraft/mods

command -v java
command -v screen
command -v Xvfb
command -v xvfb-run
command -v xauth
java -version
free -h

find /home/ubuntu/mods -maxdepth 1 -type f -printf '%f\n' | sort
find /home/ubuntu/headlessMC/srv/hmc-client/.minecraft/mods \
  -maxdepth 1 -type f -printf '%f\n' | sort
```

`connect.bash --validate-only` checks Java, Xvfb, the game directory, Fabric API,
HMC-Specifics, and Visual Probe. At the time of writing it does **not** enforce
the client GDMC dependency, so verify that JAR separately.

```bash
test -n "$(find /home/ubuntu/headlessMC/srv/hmc-client/.minecraft/mods \
  -maxdepth 1 -type f -name 'gdmc_http_interface-1.8.4-1.21.11.jar' -print -quit)"

cd /home/ubuntu/headlessMC
./connect.bash \
  --game-dir /home/ubuntu/headlessMC/srv/hmc-client/.minecraft \
  --server 127.0.0.1:59916 \
  --validate-only
```

Do not proceed if another process already owns one of the expected ports.

### 6.2 Start the Minecraft server

```bash
run_stamp="$(date +%Y%m%d_%H%M%S)"
mc_log="/home/ubuntu/headlessMC/server-tests/mc_server_${run_stamp}.log"

printf '%s\n' "$mc_log" \
  > /home/ubuntu/headlessMC/server-tests/current_mc_server_log.txt

screen -L -Logfile "$mc_log" -dmS mc-server bash -lc \
  'cd /home/ubuntu && exec java -Xmx2G -jar fabric-server-mc.1.21.11-loader.0.19.5-launcher.1.1.2.jar nogui'
```

Wait for both the listener and the completed-startup log marker:

```bash
mc_log="$(sed -n '1p' /home/ubuntu/headlessMC/server-tests/current_mc_server_log.txt)"
ss -ltnp | grep ':59916'
grep -F 'Done (' "$mc_log" | tail -n 1
curl -fsS --max-time 3 http://127.0.0.1:9000/version
```

Do not start the render worker merely because the Java PID exists. The server
must have completed world loading.

### 6.3 Start the render worker

```bash
run_stamp="$(date +%Y%m%d_%H%M%S)"
hmc_log="/home/ubuntu/headlessMC/server-tests/hmc_screen_${run_stamp}.log"

printf '%s\n' "$hmc_log" \
  > /home/ubuntu/headlessMC/server-tests/current_hmc_log.txt

screen -L -Logfile "$hmc_log" -dmS hmc-render bash -lc \
  'cd /home/ubuntu/headlessMC && exec ./connect.bash --game-dir /home/ubuntu/headlessMC/srv/hmc-client/.minecraft --server 127.0.0.1:59916'
```

The client can take more than two minutes to initialize under software OpenGL.
Follow the current log instead of starting a duplicate:

```bash
hmc_log="$(sed -n '1p' /home/ubuntu/headlessMC/server-tests/current_hmc_log.txt)"
tail -F "$hmc_log"
```

Exit `tail` with `Ctrl+C`; this does not stop the worker. Re-run the authenticated
Probe check from section 4. Cold start is complete only when it returns
`READY`, `world_loaded=true`, and the expected dimension.

### 6.4 Restore and verify edit context

GDMC named build areas may persist while the active selection may need to be
loaded again. Inspect; do not guess:

```bash
curl -sS --max-time 3 http://127.0.0.1:9000/buildarea

curl -sS --max-time 5 \
  -X POST --data 'buildarea list' \
  http://127.0.0.1:9000/command
```

If the task explicitly authorizes a named area and `/buildarea` is absent or
wrong, load that exact approved name through `/command`, then re-read it. Do not
automatically load `SERVER_CABIN_001` for unrelated work.

The workspace `TASK_STATE.md` build area and the server's live GDMC build area
serve different scopes and can differ. The live endpoint is runtime state;
`TASK_STATE.md` plus the Adapter is write authority. Both must agree with the
specific operation before mutation.

## 7. Hot-start procedure

For `HOT_READY`, preserve the warm processes:

1. Run the first-minute state audit.
2. Confirm that the expected Java process owns each listener.
3. Re-read the current Probe `session.json`; never reuse a token copied from an
   earlier launch.
4. Require authenticated Probe `READY` and `world_loaded=true`.
5. Inspect `/buildarea` and `buildarea list` before any authorized edit.
6. Read the current log pointers and recent errors.
7. Check available memory before increasing render distance or starting a large
   generator.

Useful log commands:

```bash
tail -n 120 "$(sed -n '1p' /home/ubuntu/headlessMC/server-tests/current_mc_server_log.txt)"
tail -n 160 "$(sed -n '1p' /home/ubuntu/headlessMC/server-tests/current_hmc_log.txt)"
```

Do not restart a healthy worker to “refresh” it. A warm worker is the intended
operating mode and avoids expensive client initialization.

## 8. Entering and leaving Screen sessions

List sessions:

```bash
screen -ls
```

Attach when detached:

```bash
screen -r mc-server
screen -r hmc-render
```

If a session is genuinely attached elsewhere and the operator intends to take
control of it:

```bash
screen -d -r mc-server
screen -d -r hmc-render
```

Detach without stopping the process with `Ctrl+A`, then `D`.

WorldEdit commands that depend on a real player session should be sent through
the `hmc-render` HMC-Specifics command channel. The GDMC `/command` route using
`execute as HeadlessBuilderExample` can report successful command status without
preserving the WorldEdit selection session. Any WorldEdit mutation still needs
Adapter authorization, bounded coordinates, snapshot, readback, and restore or
commit evidence.

## 9. Graceful shutdown

Stop the render worker first, then the authoritative server.

1. Attach to `hmc-render`, enter `quit`, and wait for port `8766` to close and
   the player to disconnect.
2. Attach to `mc-server`, enter `stop`, and wait for ports `59916` and `9000` to
   close.
3. Preserve the logs and their pointer files.

After shutdown:

```bash
screen -ls 2>&1 || true
ss -ltnp | awk 'NR == 1 || /:59916|:9000|:8766/'
```

Do not use `kill -9` for routine shutdown. If a process is hung, capture the
logs and process state before escalation.

## 10. Failure routing

| Symptom | Likely cause | Correct response |
|---|---|---|
| `Minecraft game directory does not exist: /srv/...` | Absolute path was copied without the `/home/ubuntu/headlessMC` prefix | Use the verified nested game directory |
| `Failed to start JLineCommandLineReader` or `Failed to call new JLineProviders` | HeadlessMC started without a pseudo-TTY | Relaunch in GNU Screen after confirming the failed copy is gone |
| Fabric registry remapping rejects `gdmc_http_interface:saved_build_area_name_argument` | Matching GDMC mod missing from client | Restore the exact 1.8.4 client JAR and validate version parity |
| PNG capture fails under `-lwjgl`/stub renderer | No real framebuffer/render stack | Use default real renderer under Xvfb + Mesa llvmpipe |
| `session.json` exists but Probe refuses connection | Stale session file or worker still starting | Inspect port/process/log; wait or repair the worker, then re-read the session file |
| Probe reports `NO_WORLD` | Client has not joined or lost the server world | Verify server readiness and client connection; do not capture yet |
| Probe returns `SCREENSHOT_FAILED` for a custom profile label | `render_profile` is a strict enum | Use current accepted profile `PRODUCTION` |
| WorldEdit command status looks successful but no block changes | Command did not use the real player's persistent WorldEdit session | Use the HMC terminal command bridge and verify by readback |
| `GET /buildarea` returns 404 or the wrong coordinates | No active selection or a different named area is loaded | List names, load only the task-approved area, and re-read |
| `9000` unavailable while `59916` is healthy | GDMC mod failed or is not ready | Inspect server log and server mod set |
| Same-pose images differ in lighting/clouds | Environment is not frozen; Probe V0.2 sync is not implemented | Freeze time/weather for strict comparisons and record the limitation |
| Host becomes memory constrained | Two Java processes plus software rendering exceed headroom | Stop new work, inspect `free -h`/RSS, and reduce scope before retrying |

The currently deployed Probe V0.1 reports `world_revision=0`; this is not a
working synchronization fence. Do not claim deterministic revision matching or
S1 readiness from that value.

## 11. Security boundary

Current server properties intentionally use `online-mode=false`. That makes
network restriction especially important:

- expose Minecraft `59916` only to explicitly approved source IPs at the cloud
  security group and, when configured, the host firewall;
- never expose GDMC `9000` or Visual Probe `8766` to the public Internet;
- verify listeners with `ss -ltnp` after every configuration change;
- do not assume `http_host=localhost` has taken effect merely because the JSON
  file contains it;
- do not guess an operator's public IP from a LAN address or one HTTP lookup;
  have the operator verify the actual raw TCP source before changing allowlists.

Port `9000` can execute Minecraft commands. A wildcard listener is a hardening
defect even when a cloud security group happens to block it externally.

## 12. Current implementation versus design documents

This audit prevents design targets from being mistaken for deployed behavior.

| Document or artifact | Alignment with the live node | How a future Agent should use it |
|---|---|---|
| `Headless Minecraft Server + Render Worker Architecture Specification v1.md.md` | The ownership split, warm worker, Xvfb, and rejection of `-lwjgl` for rendering are accurate. Its `/server`, `/editor`, `/renderer`, `/orchestrator` tree is conceptual, not the live filesystem. Revision anchors and worker orchestration remain later-stage design. | Use for architecture; use this runbook for commands and paths. |
| `Minecraft Visual Probe — Technical Specification v1.md.md` | The sensor boundary and real-client requirement are accurate. The deployed V0.1 uses combined `POST /v1/observe`, read-only `GET /v1/camera/pose`, `PLAYER_SPECTATOR`, and static revision `0`; several separate endpoints and the camera entity are target design. | Do not infer current API behavior solely from proposed sections. |
| `Minecraft Environment Adapter — SKILL.md` | Closely aligned with actual safe execution: read-before-write, bounded region, transaction, rollback, readback, structural QA, then visual evidence. | Primary authority for every world mutation. |
| `headless mc/connect.bash` | Canonical Ubuntu launcher. It correctly defaults to the real renderer and validates most client prerequisites. It does not currently validate the required client GDMC JAR. | Use on the server, with the explicit game directory in this runbook. |
| `headless mc/connect.ps1` | Appropriate for the Windows/local route, not the deployed Ubuntu node. | Do not use for server cold/hot start. |
| `runs/server_cabin_20260908/acceptance_report.md` | Best evidence for the S0 cabin edit/render acceptance and deployment discoveries. Its “Current remote state” is a dated snapshot, not a permanent health guarantee. | Use as test evidence; always run a fresh state audit. |
| `TASK_STATE.md` | Correctly marks Visual Probe M0 and server S0 complete and identifies hardening as next work. Its project build area is not automatically the active live GDMC selection. | Use for stage, locks, objectives, and permission context. |

## 13. Definition of ready

The node is ready for server-side visual observation only when all of these are
true:

- exactly one expected Minecraft server process is healthy;
- `59916` and `9000` are owned by that process;
- exactly one expected HeadlessMC render worker is healthy;
- Probe `8766` is loopback-only and authenticated status is `READY`;
- `world_loaded=true` in the intended dimension;
- the current render profile is accepted (`PRODUCTION` for the present S0 flow);
- current logs contain no unresolved registry, JLine, join, or rendering error;
- memory headroom is adequate for the requested job;
- for a write task, the separate Adapter/TASK_STATE authorization checks also
  pass.

Anything less is cold, partial, degraded, or unauthorized—not ready.
