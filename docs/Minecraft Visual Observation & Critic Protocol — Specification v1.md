---
name: minecraft-visual-observation-critic-protocol
description: >
  Defines the in-game visual observation system for autonomous Minecraft
  environment production. Covers fixed camera poses, real Minecraft client
  screenshots, visual probe APIs, observation discovery, exploration sampling,
  vision critique, stale evidence, before/after comparison, visual regression,
  and repair loops.
version: 1.0
---

# 1. Core Requirement

A Minecraft Environment system is not visually autonomous unless it can perform:

```text
BUILD
↓
CAPTURE REAL GAME VIEW
↓
VISION ANALYSIS
↓
DIAGNOSIS
↓
PATCH
↓
CAPTURE SAME VIEW
↓
COMPARE
```

This loop is mandatory.

---

# 2. Visual Backend Separation

World manipulation and rendering are separate systems.

```text
WORLD BACKEND
GDPC / WorldEdit

VISUAL BACKEND
Minecraft Client
```

Do not use the world API as a renderer.

---

# 3. Gold Standard Visual Source

Final visual QA should use:

> actual Minecraft client rendering.

The capture must reflect the intended:

```text
resource pack
shader profile
FOV
render distance
Minecraft version
time/weather
```

---

# 4. Visual Probe Interface

Required conceptual API:

```text
set_camera_pose()

capture_view()

get_camera_pose()

get_visual_status()
```

---

# 5. Observation Pose

Canonical schema:

```json
{
  "observation_id": "OBS_MARKET_ENTRY",

  "position": {
    "x": 182.5,
    "y": 74.6,
    "z": -91.5
  },

  "rotation": {
    "yaw": 132.0,
    "pitch": -7.0,
    "roll": 0.0
  },

  "fov": 70.0,

  "purpose":
    "Evaluate market arrival and temple visibility."
}
```

---

# 6. Capture Metadata

Every screenshot must store:

```text
observation_id
world_version
x
y
z
yaw
pitch
roll
fov
resolution
render_profile
resource_pack
shader_profile
time
weather
timestamp
```

Without metadata, the image is not reliable regression evidence.

---

# 7. Capture Stability

Before capture:

```text
teleport / move camera

wait for chunks

wait for terrain rendering

wait for N stable frames

hide HUD

apply target FOV

capture
```

Do not capture immediately before the world is visually stable.

---

# 8. Visual Profiles

Suggested:

```text
DEBUG
PRODUCTION
SHOWCASE
```

## DEBUG

```text
fast
no expensive shader
low screenshot cost
```

## PRODUCTION

```text
actual intended gameplay appearance
```

## SHOWCASE

```text
cinematic presentation settings
```

QA should normally use:

```text
PRODUCTION
```

not SHOWCASE.

---

# 9. Observation Categories

Maintain four categories.

## CONTRACT OBSERVATIONS

Required by Project Brief.

## DISCOVERED OBSERVATIONS

Created during environment production.

## EXPLORATION PROBES

Automatically sampled player viewpoints.

## SHOWCASE CAMERAS

Cinematic portfolio views.

Do not confuse their purposes.

---

# 10. Contract Observations

Defined before or during planning.

Examples:

```text
OBS_MAIN_GATE

OBS_MARKET_ENTRY

OBS_BRIDGE_APPROACH

OBS_TEMPLE_REVEAL

OBS_MAIN_STREET
```

These should remain stable across iterations.

---

# 11. Observation Lock

Once an observation becomes a regression anchor:

```text
LOCK_OBSERVATION_POSE
```

Do not move it just because the new world looks worse from that view.

Moving the camera destroys comparison validity.

---

# 12. Discovered Observation

Agent may create new observations when:

```text
new vista appears

new important route is built

new public space appears

important architecture requires inspection
```

A discovered observation must include:

```text
purpose
subject
reason for creation
```

---

# 13. Camera Search

For important visual subjects:

```text
generate candidate poses
↓
capture previews
↓
score
↓
select best
↓
lock
```

Candidate sources may include:

```text
road nodes
public-space edges
opposite riverbank
ridge
entrance approach
aerial points
```

---

# 14. Exploration Probe

Fixed cameras cannot cover the entire explorable world.

Sample important routes.

Example:

```text
MAIN_ROUTE
every 12 blocks

for each sample:
forward
left
right
```

Use player eye height.

---

# 15. Exploration Coverage

Track:

```text
reachable route coverage

reachable district coverage

landmark approach coverage

interior coverage
```

Goal is not exhaustive pixel coverage.

Goal is to reduce unseen production regions.

---

# 16. Cheap Probe First

Exploration screenshots may use:

```text
low resolution
fast render profile
```

Only suspicious or important frames proceed to expensive visual critique.

---

# 17. Visual Critic Inputs

Critic receives:

```text
relevant Project Brief section

Observation purpose

reference image if applicable

current screenshot

previous screenshot if regression task

relevant locked constraints
```

Do not include:

```text
builder self-praise
previous reasoning
claims that the work is complete
```

---

# 18. Visual Critic Output

Required format:

```text
OBSERVATION_ID:

WORLD_VERSION:

PASS:
-

FAIL:
-

SEVERITY:

ROOT_CAUSE_HYPOTHESIS:

PATCH_OWNER:

DO_NOT_MODIFY:

RETEST:
```

---

# 19. Visual Severity

Recommended:

```text
V0
capture invalid

V1
major spatial / visibility problem

V2
composition / architectural hierarchy

V3
style / surface inconsistency

V4
minor detail
```

Structural defects discovered visually must also be sent to Structural QA.

---

# 20. Root Cause Routing

Example:

```text
Temple hidden
```

Possible root causes:

```text
landmark placement
road approach
vegetation
building height
camera
```

Critic should not immediately prescribe:

```text
move temple
```

It should identify likely owner.

---

# 21. Patch Scope

The Director chooses minimal scope.

Example:

```text
DEFECT:
Temple obscured from market entry.

ROOT CAUSE:
bamboo cluster

PATCH:
reduce bamboo density

LOCKED:
temple position
road
market footprint
```

---

# 22. Same-Pose Comparison

After patch:

```text
same XYZ
same yaw
same pitch
same roll
same FOV
same visual profile
```

Capture:

```text
BEFORE
AFTER
```

Do not choose a more flattering camera.

---

# 23. Comparison Output

Return:

```text
IMPROVED
UNCHANGED
REGRESSED
```

per criterion.

Example:

```text
Temple readability:
IMPROVED

Street depth:
UNCHANGED

Foreground composition:
IMPROVED

New regression:
NONE
```

---

# 24. Visual Regression

A patch may improve one observation and damage another.

Use dependency mapping.

Example:

```text
BAMBOO_CLUSTER_04
visible_from:
OBS_MARKET_ENTRY
OBS_BRIDGE
OBS_RIVER
```

After modification:

```text
retest all three
```

---

# 25. Stale Evidence

Every screenshot is bound to:

```text
WORLD_VERSION
```

If a relevant object changed afterward:

```text
SCREENSHOT = STALE
```

Do not use it as current evidence.

---

# 26. Screenshot Repository

Recommended:

```text
observations/
├── OBS_MARKET_ENTRY/
│   ├── v021.png
│   ├── v022.png
│   ├── v023.png
│   └── metadata.json
│
├── OBS_TEMPLE_APPROACH/
└── OBS_AERIAL_01/
```

---

# 27. Visual Iteration Record

Store:

```text
DEFECT_ID
BEFORE_VERSION
PATCH
AFTER_VERSION
OBSERVATIONS
RESULT
```

Example:

```json
{
  "defect": "VIS_023",
  "before": 21,
  "after": 22,
  "patch": "Reduce bamboo density near temple approach.",
  "result": "IMPROVED"
}
```

---

# 28. Stage-Specific Visual Rubrics

## GRAYBOX

Check:

```text
scale
spatial readability
circulation
landmark visibility
negative space
```

## ARCHITECTURE MASSING

Check:

```text
skyline
height hierarchy
roof rhythm
street enclosure
```

## ARCHITECTURAL DETAIL

Check:

```text
construction logic
facade rhythm
Minecraft-native craftsmanship
repetition
```

## SURFACE

Check:

```text
palette
visual frequency
contrast
weathering
```

## LANDSCAPE

Check:

```text
naturalness
clustering
foreground/background
landmark obstruction
terrain transition
```

---

# 29. Stage Visual Gate

A production stage may not lock until:

```text
required structural QA = PASS

required observations = PASS
```

unless explicit waiver is granted.

---

# 30. Visual Loop

Canonical production loop:

```text
BUILD
 ↓
STRUCTURAL QA
 ↓
CAPTURE
 ↓
VISION CRITIC
 ↓
DIAGNOSE
 ↓
PATCH
 ↓
STRUCTURAL REGRESSION
 ↓
SAME-POSE CAPTURE
 ↓
BEFORE/AFTER CRITIC
 ↓
PASS?
 ├─ NO → PATCH
 └─ YES → LOCK
```

---

# 31. Success Demonstration

The system cannot claim visual autonomy until it has demonstrated:

```text
Version A
↓
real game screenshot
↓
critic identifies real defect
↓
agent changes Minecraft world
↓
Version B
↓
same-pose real game screenshot
↓
critic confirms improvement
```

This is a mandatory milestone.

---

# 32. Visual Probe Implementation Target

Recommended architecture:

```text
Fabric Client Mod

localhost API
    ↓
camera control
    ↓
frame capture
    ↓
PNG + metadata
```

World API and visual API remain independent.

---

# 33. Visual Probe MVP

MVP only requires:

```text
SET POSE
CAPTURE PNG
RETURN METADATA
```

Do not initially implement:

```text
automatic Replay Mod editing
advanced path animation
camera AI
cinematic rendering
```

First give the Agent reliable eyes.

---

# 34. Final Principle

A world-state model tells the Agent:

> what exists.

A screenshot tells the Agent:

> what the player actually sees.

Both are required.

Neither can replace the other.