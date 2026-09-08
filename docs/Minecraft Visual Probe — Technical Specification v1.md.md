继续的话，我会把 `mc-visual-probe` 直接定成一个**独立客户端传感器模块**，而不是把截图能力塞进 GDPC 或 Replay Mod。它应该像“摄像头设备”一样，被 Python Orchestrator 或 Agent 调用。

下面这份可以直接作为新的正式文档：

# `Minecraft Visual Probe — Technical Specification v1.md`

> **Implementation status note (2026-09-08):** This specification includes the
> target V0.2+ design. The deployed Ubuntu S0/V0.1 implementation currently uses
> combined `POST /v1/observe`, read-only `GET /v1/camera/pose`, the
> `PLAYER_SPECTATOR` backend, and a non-functional synchronization revision of
> `0`. For cold/hot startup, live paths, and readiness checks, read
> `Minecraft Server Agent Operations Runbook.md`.

## 1. 目标

`mc-visual-probe` 只负责一件事：

> **让外部 Agent 能把真实 Minecraft 客户端相机移动到指定 Pose，并获得对应的真实游戏截图与可靠元数据。**

它不是：

- World Builder
- GDPC wrapper
- Replay editor
- Visual Critic
- Camera planner

它只是：

> **visual sensor backend**

------

## 2. 系统位置

```text
                 ENVIRONMENT DIRECTOR
                         │
                Python Orchestrator
                  /             \
                 /               \
         WORLD BACKEND        VISUAL BACKEND
              │                    │
             GDPC             mc-visual-probe
              │                    │
       Minecraft Server      Minecraft Client
```

两者职责严格分离：

```text
GDPC
→ 改世界

Visual Probe
→ 看世界
```

------

## 3. 为什么必须是实际 Minecraft Client

最终 Production QA 要看到的是玩家真正会看到的结果，而不是：

- top-down map
- block database
- Prismarine approximation
- schematic preview

Minecraft 1.21.11 的客户端渲染由 `MinecraftClient → GameRenderer → WorldRenderer` 管理；客户端拥有实际 `Camera`、Framebuffer 和游戏设置，因此这里就是最可靠的视觉证据来源。([Maven FabricMC](https://maven.fabricmc.net/docs/yarn-1.21.11%2Bbuild.1/net/minecraft/client/MinecraftClient.html?utm_source=chatgpt.com))

Minecraft 自身的 `ScreenshotRecorder` 已经可以直接从 `Framebuffer` 获取截图，并把 framebuffer 转成 `NativeImage`，所以 MVP 不需要自己写 OpenGL framebuffer 读取逻辑。([Maven FabricMC](https://maven.fabricmc.net/docs/yarn-1.21.11%2Bbuild.1/net/minecraft/client/util/ScreenshotRecorder.html?utm_source=chatgpt.com))

------

# 4. 最小功能集

V1 只做：

```text
GET STATUS

SET CAMERA POSE

SET VISUAL PROFILE

CAPTURE SCREENSHOT

GET CURRENT POSE
```

不要一开始实现：

```text
Replay timeline
camera spline
automatic cinematography
video encoding
vision critique
```

------

# 5. 推荐实现

做一个：

> **Fabric client-side mod**

建议结构：

```text
mc-visual-probe/
├── VisualProbeClient.java
├── api/
│   ├── LocalHttpServer.java
│   ├── ApiRouter.java
│   └── JsonCodec.java
│
├── camera/
│   ├── ProbeCameraController.java
│   ├── CameraPose.java
│   └── CameraBackend.java
│
├── capture/
│   ├── ScreenshotService.java
│   └── CaptureMetadata.java
│
├── render/
│   ├── RenderReadiness.java
│   ├── VisualProfile.java
│   └── ChunkReadiness.java
│
└── sync/
    ├── WorldRevisionFence.java
    └── BlockSyncProbe.java
```

------

# 6. HTTP API

只绑定：

```text
127.0.0.1
```

不要默认暴露局域网。

推荐：

```text
http://127.0.0.1:8765/v1/
```

至少有一个 session token，防止其他本地进程随意控制客户端。

------

# 7. `/v1/status`

### GET

返回：

```json
{
  "status": "READY",
  "minecraft_version": "1.21.11",
  "world_loaded": true,
  "dimension": "minecraft:overworld",
  "camera_backend": "CLIENT_CAMERA_ENTITY",
  "render_profile": "PRODUCTION",
  "world_revision": 23
}
```

可能状态：

```text
NO_WORLD
LOADING
READY
CAPTURING
ERROR
```

------

# 8. `/v1/camera/pose`

### POST

```json
{
  "x": 184.5,
  "y": 79.2,
  "z": -93.5,
  "yaw": 135.0,
  "pitch": -8.0,
  "fov": 70,
  "observation_id": "OBS_MARKET_ENTRY"
}
```

返回实际应用后的：

```json
{
  "status": "OK",
  "requested_pose": {...},
  "actual_pose": {
    "x": 184.5,
    "y": 79.2,
    "z": -93.5,
    "yaw": 135.0,
    "pitch": -8.0,
    "fov": 70
  }
}
```

不能只返回：

```text
camera moved
```

必须 readback。

------

# 9. Camera 实现不要直接操作 `Camera` 私有状态

当前 1.21.11 的 `Camera` 虽然提供 `getCameraPos()`、`getYaw()`、`getPitch()`，但 `setPos()` 和 `setRotation()` 是 protected；而 `GameRenderer#setCameraOverride()` 当前只提供 forward-vector override，不是完整 XYZ pose API。([Maven FabricMC](https://maven.fabricmc.net/docs/yarn-1.21.11%2Bbuild.3/net/minecraft/client/render/Camera.html?utm_source=chatgpt.com))

所以我不建议 V1 直接：

```text
Mixin 修改 Camera.pos/yaw/pitch
```

这种方案容易跟 `GameRenderer.updateCamera()` 每帧状态更新打架。

------

# 10. 推荐 Camera Backend：Client Camera Entity

MinecraftClient 1.21.11 本身提供：

```text
getCameraEntity()
setCameraEntity(...)
```

因此最干净的实现是维护一个专门的 client-side camera entity，并让客户端把它作为 camera source。([Maven FabricMC](https://maven.fabricmc.net/docs/yarn-1.21.11%2Bbuild.1/net/minecraft/client/MinecraftClient.html))

这个 entity：

```text
不碰撞
不渲染
无重力
不参与 gameplay
只存在于 client
```

然后每次设置：

```text
entity.setPosition(x,y,z)
entity.setYaw(yaw)
entity.setPitch(pitch)
```

当前 1.21.11 的 `Entity` 公共 API 本身就暴露了 `setPosition`、`setYaw`、`setPitch`。([Maven FabricMC](https://maven.fabricmc.net/docs/yarn-1.21.11%2Bbuild.1/net/minecraft/entity/Entity.html?utm_source=chatgpt.com))

这是我目前最推荐的 Gold Path。

------

# 11. 为什么比 Player Teleport 好

Player teleport 可以作为 fallback，但不建议作为主方案。

因为它会：

- 改玩家实际位置；
- 触发服务器同步；
- 可能影响实体加载；
- 可能有 eye-height 偏移；
- 可能被服务器 correction；
- 干扰正常玩家状态。

Client camera entity 则可以做到：

```text
player stays here
camera goes there
```

更接近 Replay Mod 的自由相机。

------

# 12. Fallback Backend

保留：

```text
PLAYER_SPECTATOR
```

用于最早 MVP。

工作方式：

```text
set spectator
teleport player
set yaw/pitch
capture
```

优点：

```text
简单
chunks 自动围绕玩家加载
```

缺点：

```text
污染 player state
远程服务器需要权限
不是纯 client-side
```

所以：

```text
MVP-A:
PLAYER_SPECTATOR

MVP-B:
CLIENT_CAMERA_ENTITY
```

是合理路线。

------

# 13. FOV

当前 1.21.11 `GameOptions` 提供 `getFov()`，它返回可设置的 `SimpleOption<Integer>`；`SimpleOption#setValue()` 可以修改选项值。([Maven FabricMC](https://maven.fabricmc.net/docs/yarn-1.21.11%2Bbuild.1/net/minecraft/client/option/GameOptions.html?utm_source=chatgpt.com))

所以 Probe 可以：

```text
client.options.getFov().setValue(70)
```

概念上实现固定 FOV。

生产 QA 必须锁定 FOV。

不能：

```text
V21 = 70°
V22 = 90°
```

还拿来比较。

------

# 14. HUD

Production screenshot 默认：

```text
HUD hidden = true
```

当前 1.21.11 `GameOptions` 有公开的 `hudHidden` 状态。([Maven FabricMC](https://maven.fabricmc.net/docs/yarn-1.21.11%2Bbuild.3/net/minecraft/client/option/GameOptions.html?utm_source=chatgpt.com))

但要保存和恢复之前状态：

```text
oldHudState
↓
hide
↓
capture
↓
restore
```

Probe 不应该永久改用户配置。

------

# 15. `/v1/profile`

### POST

```json
{
  "profile": "PRODUCTION",
  "fov": 70,
  "hide_hud": true,
  "view_distance": 20,
  "freeze_time": true,
  "freeze_weather": true
}
```

建议三个 profile。

### DEBUG

```text
低成本
shader off
低 render distance
低 resolution
```

### PRODUCTION

```text
最终正常玩家视觉
稳定时间/天气
固定 FOV
```

### SHOWCASE

```text
shader allowed
高 render distance
更高 resolution
```

------

# 16. 不要用 Showcase Profile 做 QA

QA 的目标是：

> 可重复比较。

而 Showcase 的目标是：

> 漂亮。

所以：

```text
PRODUCTION PROFILE
= QA truth
SHOWCASE PROFILE
= marketing truth
```

必须分开。

------

# 17. `/v1/capture`

### POST

```json
{
  "observation_id": "OBS_MARKET_ENTRY",
  "expected_world_revision": 24,
  "resolution": [1280, 720],
  "render_profile": "PRODUCTION",
  "wait_until_ready": true
}
```

返回：

```json
{
  "status": "OK",
  "capture_id": "cap_000421",
  "file": "observations/OBS_MARKET_ENTRY/v024.png",
  "metadata_file": "observations/OBS_MARKET_ENTRY/v024.json"
}
```

------

# 18. Screenshot 获取

Current Minecraft 1.21.11 提供：

```text
MinecraftClient.getFramebuffer()
```

而：

```text
ScreenshotRecorder.takeScreenshot(framebuffer, callback)
```

可以从当前 framebuffer 得到 `NativeImage`。([Maven FabricMC](https://maven.fabricmc.net/docs/yarn-1.21.11%2Bbuild.1/net/minecraft/client/gl/class-use/Framebuffer.html?utm_source=chatgpt.com))

因此核心逻辑可以非常直接：

```text
Framebuffer
↓
ScreenshotRecorder
↓
NativeImage
↓
PNG
```

比模拟 F2 按键稳定。

------

# 19. Render Readiness 是整个 Probe 最容易被低估的部分

不能：

```text
set camera
↓
立即 screenshot
```

否则很容易得到：

- chunks 未加载；
- mesh 尚未编译；
- 半透明资源还在更新；
- shader 尚未稳定；
- 地形 pop-in。

所以 Capture 必须有 readiness state machine。

------

# 20. 推荐 Readiness 流程

```text
SET POSE
   ↓
CHECK TARGET CHUNK LOADED
   ↓
CHECK REQUIRED CHUNK RADIUS
   ↓
CHECK WORLD SYNC FENCE
   ↓
WAIT MINIMUM STABLE FRAMES
   ↓
CAPTURE
```

------

# 21. Chunk Readiness

例如：

```json
{
  "required_chunk_radius": 3,
  "timeout_ticks": 100
}
```

也就是至少确认 camera 周围：

```text
7 × 7 chunks
```

已经存在于客户端。

对于远景：

```text
required_chunk_radius
```

可以由 observation 定义。

------

# 22. Visual Probe 必须知道“我看到的是不是最新世界”

这是最重要的同步问题之一。

GDPC 修改发生在 world backend。

Minecraft Client 可能还没有收到 block updates。

所以仅仅：

```text
world_revision = 24
```

还不够。

------

# 23. World Revision 由 Orchestrator 管理

定义：

```text
WORLD_REVISION
```

不是 Minecraft 原生字段。

由 Environment Factory 自己维护。

每次事务成功：

```text
GDPC PATCH
↓
POST-WRITE READBACK
↓
COMMIT
↓
WORLD_REVISION += 1
```

例如：

```text
23 → 24
```

------

# 24. 视觉捕获要做 Sync Fence

每个 world transaction 可以返回少量：

```text
SYNC_ANCHORS
```

例如这次修改：

```text
MARKET_STALLS patch
```

Executor 返回：

```json
{
  "world_revision": 24,
  "sync_anchors": [
    {
      "pos": [181,74,-91],
      "block": "minecraft:spruce_planks"
    },
    {
      "pos": [185,74,-94],
      "block": "minecraft:air"
    }
  ]
}
```

然后 Visual Probe 在 client world 上检查：

```text
这些 block state 已经出现了吗？
```

只有都匹配：

```text
WORLD_SYNC = READY
```

才允许截图。

这个机制比“sleep 2 秒”可靠得多。

------

# 25. 所以 capture request 最终应该带 Sync Fence

```json
{
  "expected_world_revision": 24,

  "sync_anchors": [
    {
      "x": 181,
      "y": 74,
      "z": -91,
      "expected_block": "minecraft:spruce_planks"
    }
  ],

  "timeout_ms": 5000
}
```

如果没有同步：

```text
409 WORLD_NOT_SYNCED
```

而不是偷偷截旧图。

------

# 26. Capture Metadata

每张图必须带：

```json
{
  "capture_id": "cap_421",

  "observation_id": "OBS_MARKET_ENTRY",

  "world_revision": 24,

  "camera": {
    "x": 184.5,
    "y": 79.2,
    "z": -93.5,
    "yaw": 135,
    "pitch": -8,
    "fov": 70
  },

  "render": {
    "profile": "PRODUCTION",
    "resolution": [1280,720],
    "view_distance": 20,
    "hud_hidden": true
  },

  "environment": {
    "dimension": "minecraft:overworld",
    "time": 6000,
    "weather": "clear"
  }
}
```

------

# 27. Observation ID 必须稳定

不要用：

```text
screenshot_1
screenshot_2
```

而用：

```text
OBS_MARKET_ENTRY
OBS_TEMPLE_REVEAL
OBS_BRIDGE_APPROACH
```

文件：

```text
OBS_MARKET_ENTRY/
├── v021.png
├── v022.png
├── v024.png
└── observation.json
```

------

# 28. Combined API：`/v1/observe`

最实用的是再提供一个高层接口。

### POST

```json
{
  "observation_id": "OBS_MARKET_ENTRY",

  "pose": {
    "x": 184.5,
    "y": 79.2,
    "z": -93.5,
    "yaw": 135,
    "pitch": -8,
    "fov": 70
  },

  "expected_world_revision": 24,

  "render_profile": "PRODUCTION",

  "wait_for_chunks": true,

  "sync_anchors": [...]
}
```

它内部完成：

```text
set pose
↓
wait chunks
↓
wait world sync
↓
wait stable frames
↓
capture
↓
return PNG + metadata
```

外部 Agent 大多数时候只调用这一个 endpoint。

------

# 29. Python Client

Environment Factory 只需要一个很简单的 client：

```python
probe.observe(
    observation_id="OBS_MARKET_ENTRY",
    pose=pose,
    world_revision=24,
    profile="PRODUCTION",
)
```

返回：

```python
VisualEvidence(
    image_path=...,
    metadata=...,
)
```

Agent 不需要知道 Fabric 内部细节。

------

# 30. Thread Safety

HTTP server 的 worker thread 不能直接随便修改 Minecraft 客户端状态。

所有：

```text
camera entity
FOV
HUD
framebuffer capture
```

操作都应该调度到 Minecraft client thread 上。

`MinecraftClient` 本身就是 `ThreadExecutor`/`Executor` 类型，因此这类工作应通过客户端执行队列完成，而不是直接从 HTTP handler 操作 render state。([Maven FabricMC](https://maven.fabricmc.net/docs/yarn-1.21.11%2Bbuild.1/net/minecraft/client/MinecraftClient.html?utm_source=chatgpt.com))

架构：

```text
HTTP THREAD
   ↓
request queue
   ↓
MINECRAFT CLIENT THREAD
   ↓
camera/capture
   ↓
CompletableFuture
   ↓
HTTP RESPONSE
```

------

# 31. HTTP Handler 不要卡死客户端

建议：

```text
POST /observe
↓
202 Accepted
capture_job_id
```

然后：

```text
GET /capture/{id}
```

返回：

```text
PENDING
READY
FAILED
```

这样比一个 15 秒长连接更健壮。

MVP 也可以先 synchronous，但要有超时。

------

# 32. 视觉闭环和 Probe 的关系

Probe 不负责 Critic。

流程应该是：

```text
Environment Director
        ↓
mc-visual-probe
        ↓
PNG
        ↓
Vision Critic
        ↓
Visual Defect Report
        ↓
Environment Director
        ↓
Specialist Patch
```

保持：

> sensor ≠ judgment

------

# 33. Critic 使用时必须检查 Evidence Freshness

例如：

```text
CURRENT WORLD = 27
SCREENSHOT = 24
```

如果修改涉及该 Observation 可见区域：

```text
STALE
```

不允许继续判断。

如果修改完全无关：

```text
still valid
```

由 Dependency Graph 决定。

------

# 34. Observation Dependency

例如：

```text
HOUSE_17
visible_from:
- OBS_MAIN_STREET_03
- OBS_MARKET_NORTH
```

修改 `HOUSE_17`：

```text
invalidate:
OBS_MAIN_STREET_03
OBS_MARKET_NORTH
```

其他 observation 不需要重拍。

------

# 35. Same-Pose Enforcement

Before/After comparison API 应当直接验证：

```text
camera pose hash
```

例如：

```text
POSE_HASH =
hash(
x,y,z,yaw,pitch,fov,profile
)
```

如果 V23 与 V24 hash 不一样：

```text
COMPARISON_INVALID
```

除非明确允许。

------

# 36. 这比“相机锁定”更可靠

因为不是靠 Agent 记得：

> 用原来的 camera。

而是工具验证：

```text
same pose?
YES / NO
```

这正是整个系统应该不断推进的方向：

> **把规则从 prompt 迁移到工具层。**

------

# 37. Camera Search 也应该复用 Probe

以后：

```text
Temple
↓
Candidate Generator
↓
20 poses
↓
Probe captures 20 cheap previews
↓
VLM ranks
↓
winner becomes OBS_TEMPLE_REVEAL
↓
LOCK
```

不需要单独再写 screenshot 工具。

------

# 38. Exploration Probe

同样是：

```text
route graph
↓
sample player eye positions
↓
convert tangent to yaw
↓
capture forward / ±60°
```

例如：

```text
every 12 blocks
```

自动产生：

```text
EXP_MAINROAD_001_F
EXP_MAINROAD_001_L
EXP_MAINROAD_001_R
```

------

# 39. Exploration Probe 不是全部进大模型

先通过 cheap filters：

```text
capture invalid?
chunk missing?
mostly sky?
mostly solid wall?
large black area?
```

再决定是否送 VLM。

以后还可以做：

```text
embedding similarity
```

过滤大量重复街景。

------

# 40. Production Visual Profile 必须冻结环境变量

为了 before/after 更稳定，QA 最好固定：

```text
time of day
weather
FOV
shader
resource pack
view distance
cloud settings
HUD
camera pose
```

否则：

```text
阴天 V21
晴天 V22
```

Critic 很容易把光照变化误认为设计变化。

------

# 41. 动态实体最好在 QA 时受控

例如：

```text
villagers
animals
players
particles
```

可能挡住画面。

DEBUG / PRODUCTION QA profile 可以：

```text
disable nonessential entities
or
freeze simulation
```

如果技术上不便，至少记录动态因素。

SHOWCASE 可以恢复。

------

# 42. Replay Mod 与 Probe 的关系

不要把 Replay Mod 放进 Production QA 主路径。

两者职责：

```text
mc-visual-probe
→ exact repeatable still observation

Replay Mod
→ continuous cinematic camera path
```

但是 pose schema 可以共享。

Replay Mod 的 Position Keyframe 本身保存：

```text
x y z yaw pitch roll
```

所以：

```text
ObservationPose
```

未来完全可以转成：

```text
Replay Keyframe
```

而不用再定义第二套相机坐标格式。([Minecraft ReplayMod](https://www.replaymod.com/docs/?utm_source=chatgpt.com))

------

# 43. 统一 Camera Pose Schema

建议整个项目只有这一份：

```json
{
  "position": {
    "x": 0,
    "y": 0,
    "z": 0
  },

  "rotation": {
    "yaw": 0,
    "pitch": 0,
    "roll": 0
  },

  "fov": 70
}
```

被：

```text
Visual Probe
Observation Contract
Camera Search
Showcase Director
Replay Adapter
```

共同使用。

------

# 44. Error Codes

Probe 不要只返回 500。

至少定义：

```text
NO_WORLD

CAMERA_BACKEND_UNAVAILABLE

CAMERA_POSE_INVALID

TARGET_CHUNK_TIMEOUT

WORLD_NOT_SYNCED

CAPTURE_TIMEOUT

FRAMEBUFFER_UNAVAILABLE

SCREENSHOT_FAILED

PROFILE_INVALID
```

这样 Director 才能真正诊断。

------

# 45. Capture Result

例如：

```json
{
  "status": "FAILED",

  "code": "TARGET_CHUNK_TIMEOUT",

  "observation_id": "OBS_TEMPLE",

  "details": {
    "loaded_radius": 1,
    "required_radius": 4
  }
}
```

这比：

```text
screenshot failed
```

有价值得多。

------

# 46. 安全边界

Visual Probe 默认：

```text
bind = 127.0.0.1
remote connections = false
```

并生成：

```text
session token
```

因为它可以控制客户端摄像头和游戏设置。

不要默认：

```text
0.0.0.0
```

------

# 47. Fabric Mod 不应该拥有 World Write API

非常重要。

`mc-visual-probe`：

```text
READ + CAMERA + CAPTURE
```

而不是：

```text
/setblock
/worldedit
```

写入继续走：

```text
GDPC / Environment Adapter
```

这样即使 Probe 出问题，也不会破坏世界。

------

# 48. Probe V0.1 的成功标准

第一阶段只要求：

```text
Minecraft Client running

Python:
observe(
 x,y,z,
 yaw,pitch,
 fov
)

↓

PNG returned
```

然后重复同 pose：

```text
capture A
capture B
```

几何 framing 基本一致。

------

# 49. Probe V0.2

加入：

```text
world sync anchors
chunk readiness
metadata
observation IDs
profiles
```

------

# 50. Probe V0.3

加入：

```text
camera entity backend
exploration sampling
candidate camera batch capture
```

------

# 51. First Closed-Loop Demo

我会把项目第一个真正有说服力的 demo 定成：

```text
1. Agent builds graybox market.

2. Visual Probe:
   OBS_MARKET_ENTRY
   v001.png

3. Vision Critic:
   "Temple is obscured by market mass."

4. Director:
   refuses to move locked temple.
   routes problem to market massing.

5. Agent reduces one building height.

6. Structural QA:
   PASS.

7. Visual Probe:
   same exact pose
   v002.png

8. Vision Critic:
   Temple visibility improved.
   No new regression.

9. Stage:
   PASS.
```

这个 demo 比：

> AI 自动生成一个漂亮村子

更能证明系统的独特性。

因为它证明：

> **Agent 真的能看见自己做的东西，并基于实际玩家画面修正设计。**

------

# 52. Project Brief 也要因此稍微升级

`Observation Contract` 不应该最后才写。

比如 Project Definition 阶段用户确认：

```text
玩家从市场入口第一次看到寺院
```

那么 Brief 立即产生：

```text
OBS_TEMPLE_REVEAL_REQUIRED
```

等道路规划出来以后，系统自动把语义要求解析成具体 pose。

所以：

```text
Narrative / Spatial Intent
↓
Observation Requirement
↓
Concrete Camera Pose
↓
Visual Gate
```

这一条链非常关键。

------

# 53. 甚至 Adjacency 可以产生视觉验收

例如：

```text
Temple visible from market approach
```

不是只写在 Markdown。

最终应编译成：

```text
SPATIAL CONSTRAINT
+
VISUAL CONSTRAINT
```

空间层：

```text
market connected to temple path
```

视觉层：

```text
temple silhouette occupies sufficient visible region
from OBS_TEMPLE_REVEAL
```

以后甚至可以算法 + VLM 双验收。

------

# 54. 最终 Project Brief 应该变成“可编译 Brief”

这可能是我们目前最值得发展的概念。

不是：

```text
Brief = 给 LLM 看的一篇文章
```

而是：

```text
Brief
↓
Compiler
↓
Project Constraints
```

例如：

```text
Project Objective
→ evaluation rubric

Spatial Scope
→ regions

Adjacency & Circulation
→ semantic graph

Minimum Content
→ asset counts

Construction Detail
→ grammar constraints

Surface Language
→ block palette rules

Observation Contract
→ camera requirements
```

这样 Project Brief 就真正成为 Production Contract。

------

# 55. 整个系统因此开始有一个非常清楚的闭环

```text
                  USER
                   │
             DESIGN DIALOGUE
                   │
              PROJECT BRIEF
                   │
               BRIEF COMPILER
                   │
       ┌───────────┼────────────┐
       ▼           ▼            ▼
   Spatial       Content       Visual
 Constraints   Requirements   Requirements
       │           │            │
       └───────────┼────────────┘
                   ▼
                DIRECTOR
                   │
                BUILD
                   │
        ┌──────────┴───────────┐
        ▼                      ▼
     WORLD QA              VISUAL PROBE
        │                      │
        ▼                      ▼
 deterministic             real pixels
        │                      │
        └──────────┬───────────┘
                   ▼
                CRITIC
                   │
                 PATCH
                   │
              REGRESSION
                   │
                 LOCK
```

我认为这才是真正接近你想要的 **Minecraft 版 Skyline**。

不是“LLM 能不能造 MC 建筑”，而是：

> **用户与 Agent 共同定义目标 → Agent 施工 → Agent 在真实游戏里观察 → 根据实际视觉证据自评 → 修正 → 用同机位证明自己确实变好了。**

现在这套体系里，`mc-visual-probe` 已经应该被提升到和 **GDPC Executor** 同级：**一个是手，一个是眼睛。** 没有其中任何一个，Environment Director 都不完整。
