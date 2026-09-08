下面这份我建议正式作为 **SaaS 化前的服务端/后台渲染基础设施总规范**。它的重点不是“怎么截图”本身，而是把 **Server、编辑能力、Headless Render Worker、资源包/Shader/CTM/Modded Profile、世界版本同步**放进同一套可落地架构。

# `Headless Minecraft Server + Render Worker Architecture Specification v1.md`

> **Deployment status note (2026-09-08):** This document is the target
> architecture, not the command-level runbook. The current Ubuntu S0 deployment
> uses GNU Screen, `/home/ubuntu/headlessMC/srv/hmc-client/.minecraft`, a warm
> HeadlessMC client under Xvfb/Mesa llvmpipe, and Visual Probe V0.1. Its
> synchronization revision/anchor model is not yet implemented. For cold/hot
> startup and live paths, read `Minecraft Server Agent Operations Runbook.md`.
> For provisioning a bare Ubuntu node and offline artifact transfer, read
> `Minecraft Server Node Bootstrap Runbook.md`.

## 1. System Goal

目标系统必须同时满足：

- Minecraft 服务端保持权威世界状态；
- 保留现有 GDPC / WorldEdit / 自定义生成器编辑能力；
- 后台能够从任意指定坐标和角度获得真实 Minecraft 渲染图像；
- 支持 Resource Pack；
- 支持 Custom Block Models；
- 支持 Connected Textures；
- 支持 Shader；
- 支持 Modded Minecraft；
- 未来能够水平扩展为多用户 SaaS；
- Environment Agent 不依赖用户本地运行 Minecraft Client。

核心原则：

> **Server owns the world.
> Render Worker owns the pixels.
> Orchestrator owns synchronization.**

------

# 2. Canonical Deployment Architecture

```text
                         USER / AGENT
                              │
                              ▼
                        ORCHESTRATOR
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
   WORLD INTELLIGENCE     EDIT SERVICE       VISUAL SERVICE
          │                   │                   │
          │            GDPC / WorldEdit           │
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                     MINECRAFT SERVER
                              ▲
                              │
                        Minecraft Protocol
                              │
                              ▼
                     HEADLESS RENDER WORKER
                              │
                  Real Minecraft Client Renderer
                              │
                              ▼
                       PNG / VIDEO / META
```

Dedicated Server 不负责最终像素渲染。

Render Worker 是一个真正的客户端运行环境，只是：

```text
no human
no physical monitor
no normal desktop interaction
```

Fabric Loom 当前明确支持在 Linux 通过 Xvfb 启动 production client，用途就是 headless CI，因此“后台真实客户端”是一个现实的部署路径。([Fabric Documentation](https://docs.fabricmc.net/develop/loom/production-run-tasks?utm_source=chatgpt.com))

------

# 3. Service Responsibilities

## 3.1 Minecraft Server

唯一权威：

```text
blocks
block entities
entities
dimensions
game rules
server-side mods
world saves
```

它不负责：

```text
shader rendering
client resource interpretation
framebuffer capture
cinematic camera
```

------

## 3.2 Edit Service

负责：

```text
terrain changes
block placement
WorldEdit operations
GDPC operations
schematic placement
server-side procedural generation
```

任何修改都必须成为：

```text
WORLD TRANSACTION
```

并最终产生新的：

```text
WORLD_REVISION
```

------

## 3.3 Render Worker

负责：

```text
connect to server
load correct client profile
move camera
load chunks
wait visual stability
capture framebuffer
return visual evidence
```

Render Worker 永远不是主要 world-write backend。

------

## 3.4 Orchestrator

负责协调：

```text
brief
planning
edit job
commit
revision
render request
vision critic
repair
```

它是服务之间的唯一协调者。

------

# 4. World Revision Model

必须从一开始加入逻辑世界版本。

例如：

```text
WORLD_REVISION = 42
```

Agent 执行：

```text
remove building
add market canopy
change bamboo cluster
```

全部完成并通过 server readback 后：

```text
COMMIT
WORLD_REVISION = 43
```

所有后续 visual evidence 都绑定：

```text
43
```

------

# 5. Transaction Lifecycle

```text
PATCH REQUEST
    ↓
VALIDATE REGION
    ↓
WORLD WRITE
    ↓
SERVER READBACK
    ↓
STRUCTURAL QA
    ↓
COMMIT
    ↓
REVISION++
    ↓
RENDER ELIGIBLE
```

如果失败：

```text
ROLLBACK
```

则：

```text
WORLD_REVISION
```

不能增加。

------

# 6. Visual Synchronization Problem

这是整个架构最关键的工程问题之一。

Server 已经变成：

```text
revision 43
```

并不代表 Render Worker 已经看到 revision 43。

网络、chunk update、mesh rebuilding 都可能延迟。

所以绝不能：

```text
edit complete
↓
sleep(2)
↓
screenshot
```

------

# 7. Sync Anchor Protocol

每个事务在 commit 后产生少量：

```text
SYNC_ANCHORS
```

例如：

```json
{
  "revision": 43,
  "anchors": [
    {
      "position": [181, 74, -91],
      "expected_state": "minecraft:spruce_planks"
    },
    {
      "position": [184, 76, -92],
      "expected_state": "minecraft:air"
    }
  ]
}
```

Render Worker 在客户端世界里读取这些位置。

全部满足：

```text
CLIENT_SYNC_READY
```

才可以截图。

------

# 8. Anchor Selection

不要把所有修改块发送给 Render Worker。

事务执行器选择少量具有辨识度的锚点：

```text
changed solid block
removed block
distinct block state
important boundary block
```

建议：

```text
3–12 anchors / patch
```

大型修改可按 chunk 分布。

------

# 9. Render Job Contract

标准请求：

```json
{
  "job_id": "render_4381",

  "project_id": "project_21",

  "world_revision": 43,

  "dimension": "minecraft:overworld",

  "observation_id": "OBS_MARKET_ENTRY",

  "pose": {
    "x": 184.5,
    "y": 79.2,
    "z": -93.5,
    "yaw": 135.0,
    "pitch": -8.0,
    "roll": 0.0,
    "fov": 70
  },

  "renderer_profile": "song-town-production-v3",

  "sync_anchors": [],

  "output": {
    "width": 1280,
    "height": 720,
    "format": "png"
  }
}
```

------

# 10. Render Result

```json
{
  "status": "SUCCESS",

  "job_id": "render_4381",

  "world_revision": 43,

  "image": "object://project_21/render_4381.png",

  "actual_pose": {},

  "renderer_profile_hash": "sha256:...",

  "capture_metadata": {
    "minecraft_version": "1.21.11",
    "dimension": "minecraft:overworld",
    "resource_pack": "...",
    "shader_pack": "...",
    "mods_hash": "...",
    "view_distance": 20
  }
}
```

------

# 11. Renderer Profile

这是整个多模组、多材质、多 Shader 系统的核心抽象。

不要让 Agent 每次自己拼：

```text
Minecraft + mods + pack + shader
```

而定义：

```text
RENDERER_PROFILE
```

------

# 12. Renderer Profile Schema

概念结构：

```json
{
  "id": "song-town-production-v3",

  "minecraft": {
    "version": "1.21.11",
    "loader": "fabric"
  },

  "client_mods": [
    "fabric-api",
    "sodium",
    "continuity"
  ],

  "resource_packs": [
    "song-town-base.zip"
  ],

  "shader": {
    "enabled": false,
    "pack": null
  },

  "render": {
    "view_distance": 20,
    "simulation_distance": 8,
    "fov": 70,
    "entity_distance": 100,
    "particles": "minimal"
  }
}
```

------

# 13. Profile Immutability

一旦 Profile 被用于 regression test：

```text
PROFILE HASH
```

必须固定。

例如：

```text
song-town-production-v3
sha256:AA91...
```

如果修改 Resource Pack：

```text
v4
```

而不是静默替换 v3。

否则 before / after 比较失去意义。

------

# 14. Resource Pack Support

Resource Pack 是最应该第一阶段支持的高级视觉功能。

Render Worker 必须能够：

```text
install pack
activate pack
reload resources
verify successful reload
```

capture metadata 记录：

```text
pack name
pack hash
pack order
```

多资源包时顺序也属于 Profile。

------

# 15. Custom Block Model Support

Resource-pack-based custom block/item models自然属于：

```text
Resource Pack Profile
```

如果模型来自：

```text
modded block renderer
```

则必须通过对应 client mod profile 加载。

所以系统不单独实现：

```text
custom model renderer
```

而是保证：

> Render Worker 运行和目标玩家一致的 Minecraft rendering stack。

------

# 16. Connected Texture Support

对于 1.21.11，Continuity 当前确实提供 Fabric 客户端版本，并支持 OptiFine 风格 connected textures、部分 emissive textures 和 custom block layers。([Modrinth](https://modrinth.com/mod/continuity?hl=en-US&utm_source=chatgpt.com))

因此可以定义：

```text
CTM_PROFILE
```

例如：

```text
Fabric
+ Sodium
+ Continuity
+ target resource pack
```

也可以以后支持 Fusion 等其他 connected-texture renderer；Fusion 当前也有 1.21.11 Fabric 版本。([Modrinth](https://modrinth.com/mod/fusion-connected-textures/version/1.3.8-fabric-mc1.21.11?utm_source=chatgpt.com))

------

# 17. CTM 是客户端视觉能力

这意味着：

Server：

```text
stone_bricks
stone_bricks
stone_bricks
```

可能不关心 connected appearance。

Client：

```text
Continuity
+
resource pack
```

才决定最终边缘如何连接。

所以：

> CTM validation 必须发生在 Render Worker。

------

# 18. Shader Support

Shader 应作为独立 render capability。

对于 Fabric 1.21.11，Iris 当前有对应版本，并作为 client-side shader loader 使用。([Modrinth](https://modrinth.com/mod/iris/version/1.10.4%2B1.21.11-fabric?utm_source=chatgpt.com))

推荐 Profile：

```text
minecraft 1.21.11
Fabric
Sodium
Iris
Shader Pack
Resource Pack
```

------

# 19. Shader Worker 需要真实图形环境

这里要特别区分两种“headless”。

## A. Virtual-display headless

例如：

```text
Xvfb
+
actual OpenGL/GPU
```

没有显示器，但仍然真实渲染。

这是你要做 Shader 的推荐方向。

Fabric 自身对 production client 的 Xvfb 支持正是这一类。([Fabric Documentation](https://docs.fabricmc.net/develop/loom/production-run-tasks?utm_source=chatgpt.com))

------

## B. No-render headless

例如 HeadlessMc 的某些 headless 模式可以通过修改 LWJGL 让客户端在没有图形设备的服务器上运行，但这种模式的目标是“运行客户端逻辑而不渲染 GUI”，不适合作为我们需要 framebuffer PNG 的最终 renderer。([HeadlessHQ](https://headlesshq.github.io/headlessmc/launch/?utm_source=chatgpt.com))

因此：

> **Headless client 能运行 ≠ Headless client 能产出真实 Shader 截图。**

我们的 Render Worker 必须保留实际图形 rendering path。

------

# 20. 推荐部署方式

生产渲染：

```text
Linux
↓
GPU Driver
↓
Xorg/Xvfb or equivalent virtual display
↓
Minecraft Client
↓
Fabric
↓
Visual Probe Mod
↓
Framebuffer
```

用户不看到窗口。

但 GPU 真正在渲染。

------

# 21. Render Capability Levels

定义明确的 capability tier。

## `R0_FAST`

```text
no shader
basic resource pack
low resolution
```

用于：

```text
camera search
exploration probes
graybox
```

------

## `R1_PRODUCTION`

```text
real vanilla client
production resource pack
CTM if required
custom models
```

用于：

```text
stage QA
before/after critic
```

------

## `R2_CINEMATIC`

```text
Iris
shader pack
high render distance
higher resolution
```

用于：

```text
hero image
Replay
portfolio video
```

------

# 22. Do Not Make R2 the QA Truth

核心 QA 应优先：

```text
R1_PRODUCTION
```

因为 Shader 会改变：

```text
visibility
contrast
shadow
atmosphere
```

可能把结构问题掩盖。

R2 是：

> presentation evidence

而不是：

> structural/art-design truth

------

# 23. Modded Minecraft Support

这里不要试图建立：

```text
one universal client that loads arbitrary mods dynamically
```

这会非常痛苦。

应该建立：

# **Profile-bound Worker Image**

例如：

```text
workers/
├── vanilla-fabric-1.21.11/
├── fantasy-modpack-v4/
├── create-server-v2/
└── client-project-X/
```

------

# 24. Client/Server Compatibility Manifest

每个 profile 保存：

```text
minecraft version
loader
server mods
client mods
required shared mods
resource packs
shader
config files
```

生成：

```text
PROFILE_MANIFEST.lock
```

其 hash 成为：

```text
renderer_profile_hash
```

------

# 25. Worker Cannot Render Unknown Mod Content

如果服务端拥有：

```text
CUSTOM_BLOCK_X
```

但 worker profile 缺少对应 client mod：

必须：

```text
PROFILE_INCOMPATIBLE
```

而不是继续截图缺失纹理。

------

# 26. Missing Texture Gate

截图前自动检查客户端日志/资源状态是否出现：

```text
missing model
missing texture
failed resource reload
unknown registry
```

如果存在重大错误：

```text
VISUAL_PROFILE_FAIL
```

不能把紫黑块截图交给 Critic。

------

# 27. Profile Validation Job

每个新 Profile 第一次启用时执行：

```text
BOOT
↓
CONNECT
↓
RESOURCE RELOAD
↓
TEST WORLD
↓
TEST SCREENSHOT
↓
LOG SCAN
↓
PROFILE READY
```

只有通过：

```text
PROFILE_CERTIFIED
```

才进入生产池。

------

# 28. Server Architecture

初期完全可以保留：

```text
GDMC HTTP Interface / GDPC
+
WorldEdit
+
Fabric Server
```

不必马上统一。

在上层创建：

```text
EditService
```

适配不同 backend：

```text
GDPCBackend
WorldEditBackend
FutureFabricEditBackend
```

------

# 29. Unified Edit API

上层只看：

```python
apply_patch(...)
place_structure(...)
terraform(...)
read_region(...)
```

不要让 Environment Director 直接关心：

```text
GDPC command details
WorldEdit syntax
```

------

# 30. Read/Write Isolation

对于 Agent：

```text
WorldReader
WorldWriter
VisualProbe
```

三个权限面分开。

这样某个 critic agent 可以只获得：

```text
WorldReader + VisualProbe
```

而没有：

```text
WorldWriter
```

这非常适合独立 Critic。

------

# 31. Initial Single-Server Deployment

The directory tree in this section is a conceptual service boundary. It is not
the literal filesystem layout of the current Ubuntu node; the operational
mapping is maintained in `Minecraft Server Agent Operations Runbook.md`.

第一阶段无需 SaaS 集群。

一台 Linux 服务器：

```text
minecraft-host/
│
├── server/
│   └── Minecraft Server
│
├── editor/
│   └── GDPC + adapters
│
├── renderer/
│   └── Minecraft Client + Xvfb
│
└── orchestrator/
```

推荐先证明：

```text
Edit → Sync → Render
```

------

# 32. First End-to-End Acceptance Test

这是系统真正的 S0 Gate。

准备一个普通测试世界。

执行：

```text
STEP 1

Render:
OBS_A
```

保存：

```text
A_v1.png
```

------

然后 Agent/API：

```text
STEP 2

Place obvious structure:
5×5 red wool wall
```

server commit：

```text
revision 1 → 2
```

------

然后：

```text
STEP 3

Render exact same OBS_A
```

Render Worker 必须等待 sync anchor。

得到：

```text
A_v2.png
```

------

验收：

```text
Pose identical
Profile identical
World revision changed
Red wall visible
```

这意味着：

> Server editing 与 background real-client rendering 已经真正贯通。

------

# 33. Second Acceptance Test — Resource Pack

切换：

```text
vanilla
→ custom resource pack
```

同一 world revision、同一 pose：

```text
capture vanilla
capture resource pack
```

验证确实发生模型/纹理变化。

------

# 34. Third Acceptance Test — Connected Texture

准备支持 CTM 的资源。

Profile：

```text
Fabric
Sodium
Continuity
Resource Pack
```

验证同一结构出现正确 connected appearance。

Continuity 当前支持 1.21.11 Fabric 客户端，因此这个测试可以直接列入目标。([Modrinth](https://modrinth.com/mod/continuity/version/mX1iknM1?utm_source=chatgpt.com))

------

# 35. Fourth Acceptance Test — Shader

Profile：

```text
Fabric
Sodium
Iris
test shader pack
```

同 pose：

```text
PRODUCTION no shader
SHOWCASE shader
```

确认：

```text
both valid
profile hashes differ
```

Iris 当前存在 1.21.11 Fabric 版本，因此技术栈至少在版本层面是可对齐的。([Modrinth](https://modrinth.com/mod/iris/version/1.10.4%2B1.21.11-fabric?utm_source=chatgpt.com))

------

# 36. Fifth Acceptance Test — Modded Block

Server + Client 都安装测试 mod。

放置：

```text
MOD_BLOCK_A
```

Render Worker：

```text
correct profile
→ image correct
```

错误 profile：

```text
must reject
```

不能偷偷 fallback。

------

# 37. Render Worker Session State

Worker 状态机：

```text
STOPPED
↓
BOOTING
↓
CLIENT_READY
↓
CONNECTING
↓
WORLD_READY
↓
PROFILE_READY
↓
IDLE
↓
RENDERING
↓
IDLE
```

错误：

```text
CRASHED
PROFILE_ERROR
SYNC_ERROR
```

------

# 38. Warm Worker

未来 SaaS 不要每次：

```text
new JVM
new Minecraft
```

建议 worker 启动后：

```text
remain warm
```

新的 render job 只需要：

```text
connect / switch project
set pose
capture
```

------

# 39. Worker Leasing

未来：

```text
PROJECT A
```

连续视觉迭代：

```text
build
capture
build
capture
```

可以临时 lease：

```text
worker_03
```

例如：

```text
10 min
```

避免重复初始化。

------

# 40. Isolation

SaaS 多用户必须防止：

```text
User A resource pack
leaks into
User B
```

每个 session 后要 reset：

```text
profile
resource pack
shader
server connection
camera
screenshots
temporary cache
```

对于不可信 modpack，则最好：

> one isolated container/VM per worker profile/session.

------

# 41. User Upload Support

以后用户可以上传：

```text
world.zip
resourcepack.zip
modpack
schematic
reference files
```

但不要直接把上传的任意 mod 放进长期共享 worker。

需要：

```text
security scan
isolated profile build
```

特别是 JVM mod 本质上可执行代码。

------

# 42. World Storage

未来 SaaS 推荐：

```text
Project World
↓
versioned snapshot
```

例如：

```text
world/
├── rev_0041
├── rev_0042
└── rev_0043
```

不一定每个版本完整复制整个 world，可以使用：

```text
filesystem snapshots
copy-on-write
incremental patches
```

但逻辑上必须可定位 revision。

------

# 43. Render Against Snapshot vs Live Server

开发阶段：

```text
live server
```

最简单。

未来大规模 SaaS 可以有两种模式：

### Interactive Iteration

Render Worker 直接连接当前 project server。

速度快。

### Immutable Validation

把 revision snapshot 启动成临时 server，然后 renderer 连接。

更严格。

最终 GDMC benchmark / final QA 可采用后者。

------

# 44. Visual Evidence Object

所有 renderer 最终统一返回：

```python
VisualEvidence(
    project_id,
    world_revision,
    observation_id,
    pose,
    renderer_profile,
    renderer_profile_hash,
    image_uri,
    metadata,
)
```

Environment Director 不需要知道：

```text
Xvfb
Iris
Continuity
Fabric
```

------

# 45. Camera Pose Remains Renderer-Agnostic

继续使用统一：

```json
{
  "x": 0,
  "y": 0,
  "z": 0,
  "yaw": 0,
  "pitch": 0,
  "roll": 0,
  "fov": 70
}
```

供：

```text
Visual Observation
Camera Search
Replay Showcase
```

共用。

------

# 46. Render Worker API

第一版至少：

```text
GET  /status

POST /session/connect

POST /profile/load

POST /camera/set

POST /observe

GET  /jobs/{id}

POST /session/reset
```

------

# 47. `/observe` High-Level Behavior

```text
validate profile
↓
validate project
↓
connect world
↓
wait server state
↓
set camera
↓
wait chunks
↓
wait sync anchors
↓
wait stable frames
↓
capture framebuffer
↓
save PNG
↓
return metadata
```

这是 Agent 的默认调用。

------

# 48. Failure Codes

至少：

```text
WORKER_UNAVAILABLE
SERVER_UNREACHABLE
PROFILE_NOT_FOUND
PROFILE_INCOMPATIBLE
RESOURCE_RELOAD_FAILED
MOD_MISMATCH
MISSING_MODEL
TARGET_CHUNK_TIMEOUT
WORLD_SYNC_TIMEOUT
CAMERA_ERROR
FRAMEBUFFER_ERROR
CAPTURE_ERROR
```

------

# 49. Logging

每次 render 记录：

```text
worker id
job id
project
revision
profile
startup time
connection time
chunk wait time
render wait time
capture time
memory
GPU memory
```

这对未来 SaaS 成本模型非常重要。

------

# 50. Performance Metrics

以后应该知道：

```text
median observe latency
P95 observe latency
worker startup time
world load time
profile load time
screenshots/minute
GPU utilization
VRAM/project
```

例如：

```text
first screenshot = expensive
next 20 screenshots = cheap
```

这会决定 warm pool 是否值得。

------

# 51. Two-Tier Render Architecture

当系统成熟后：

```text
FAST PROBE
+
TRUE GAME PROBE
```

仍然值得保留。

Fast Probe 用于：

```text
100–500 exploration views
camera candidate search
```

True Game Probe 用于：

```text
selected views
stage gates
before/after
final QA
```

但第一阶段可以完全只实现真实 Render Worker。

------

# 52. Recommended First Stack

如果现在马上开工，我会先固定：

```text
Minecraft Java 1.21.11

Server:
Fabric

Editor:
existing GDPC
WorldEdit optional

Render:
Fabric Minecraft Client

Headless environment:
Linux + Xvfb

Basic rendering:
Vanilla first

Later:
Sodium
Continuity
Iris
```

Fabric 官方当前对 Xvfb production client 有直接支持，而 Continuity 与 Iris 都存在 1.21.11 Fabric 客户端版本，所以这条目标技术栈在当前版本上是连得起来的。([Fabric Documentation](https://docs.fabricmc.net/develop/loom/production-run-tasks?utm_source=chatgpt.com))

------

# 53. Do Not Start with HeadlessMc `-lwjgl` for Renderer

HeadlessMc 很有价值，可以帮助自动安装、启动 Fabric/Forge/NeoForge 客户端，并提供完全 headless launch；但其 `-lwjgl` 模式本质上强调“不需要 graphics device”，因此它更适合 bot/automation 场景，而不是我们依赖真实 framebuffer 的最终 renderer。([HeadlessHQ](https://headlesshq.github.io/headlessmc/launch/?utm_source=chatgpt.com))

可以借用：

```text
launcher/session management
```

思想，

但渲染 worker 推荐：

```text
actual LWJGL/OpenGL rendering
+
virtual display
```

------

# 54. Development Phases

## S0 — Server Render Bridge

实现：

```text
server
+
existing editing
+
headless client
+
pose screenshot
```

不做高级视觉。

------

## S1 — Deterministic Observation

增加：

```text
observation ID
same pose
world revision
sync anchors
metadata
```

------

## S2 — Resource Profile

增加：

```text
resource packs
custom models
profile hash
```

------

## S3 — Connected Texture Profile

增加：

```text
Continuity / alternative CTM
```

------

## S4 — Shader Profile

增加：

```text
Iris
GPU worker
showcase rendering
```

------

## S5 — Modpack Profile

增加：

```text
server/client manifests
isolated workers
mod compatibility validation
```

------

## S6 — Worker Pool

增加：

```text
queue
leasing
warm workers
reset
```

------

## S7 — SaaS

增加：

```text
multi-user isolation
object storage
autoscaling
billing metrics
```

------

# 55. First Coding Ticket

第一张真正工单应该非常克制：

```text
MILESTONE S0

Create one Minecraft 1.21.11 Fabric server.

Keep existing GDPC editing access.

Create one Linux headless Fabric client with actual rendering
under Xvfb.

Create a minimal render-probe Fabric mod.

Expose:

GET /status

POST /observe

POST /observe receives:

x
y
z
yaw
pitch
fov

The worker connects to the local Minecraft server and returns a
PNG rendered by the actual Minecraft client.

Acceptance:

1. Render pose A.
2. Modify the world through the existing editor.
3. Render exactly pose A again.
4. The edit is visible.
5. No manual client interaction occurs.
```

**S0 通过以前，不要碰 Iris、Continuity、Replay 或多用户调度。**

------

# 56. Second Coding Ticket

S1：

```text
Introduce:

WORLD_REVISION

SYNC_ANCHORS

OBSERVATION_ID

RENDERER_PROFILE_HASH

same-pose validation
```

这时才能开始真正给 Vision Critic 使用。

------

# 57. 第一次真正闭环

等 S1 完成后，我们的最小 Environment Agent 可以第一次这样运行：

```text
Agent:
place market facade

↓

GDPC:
commit revision 18

↓

Render Worker:
OBS_MARKET
revision 18

↓

real Minecraft PNG

↓

Vision Critic:
roof silhouette weak

↓

Agent patch

↓

commit revision 19

↓

Render Worker:
same OBS_MARKET pose
revision 19

↓

before / after critic
```

这里已经不需要任何用户客户端。

------

## 这会对整个 SaaS 设计产生一个很好的结果

以后网页端其实根本不需要“远程操作 Minecraft”。

Web 用户看到的是：

```text
PROJECT
│
├─ Brief
├─ Planning Map
├─ Current Preview
├─ Revision History
├─ Agent Critiques
└─ Final Interactive / Video Preview
```

Minecraft Server 和后台 Clients 都只是生产基础设施。

这和你之前类比的 Architectural VR / Tripo 式服务会非常接近：

> 用户提交需求 → Agent 在后台真正搭建 → Renderer 在后台真正观察 → Agent自评与返工 → 用户只看阶段性成果。

所以我认为现在可以正式把开发入口从 `mc-visual-probe` 再升级一级，叫做：

# **`Headless Minecraft Production Node`**

节点内部包含：

```text
Minecraft Server      ← 世界
Edit Backend          ← 手
Render Worker         ← 眼睛
Orchestrator Adapter  ← 神经接口
```

而未来 SaaS 只是在横向复制这种 Production Node。

这比“以后再想办法把一个桌面 Minecraft 自动化项目改成 SaaS”要干净得多。
