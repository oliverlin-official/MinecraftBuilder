# Minecraft Environment Router
## START HERE

> **This is the mandatory entry point for all Minecraft Environment Factory work.**

Do **not** begin by reading every Minecraft Environment document.

Do **not** begin by modifying the Minecraft world.

Do **not** assume that the longest or newest document should always be loaded.

Your first responsibility is to determine:

1. **What kind of task is being requested?**
2. **What production stage is currently active?**
3. **What information is missing?**
4. **Which minimum set of documents is required to continue safely?**

Then read only those documents.

---

# 1. System Overview

The Minecraft Environment system is divided into four layers:

```text
ENVIRONMENT INTELLIGENCE
        ↓
PRODUCTION MANAGEMENT
        ↓
SPECIALIST EXECUTION
        ↓
EVALUATION / SHOWCASE
```

Current core documents:

```text
Minecraft Environment Director.md

Minecraft Environment Adapter — SKILL.md

Minecraft Environment Core Specialist Pack v1.md

Minecraft Terrain Intelligence & Settlement Planning Specification v1.md

Minecraft Environment Factory — Implementation Blueprint v0.1.md

Minecraft Environment Factory Pipeline v2.md

GDMC Benchmark Harness — Specification v1.md

Minecraft Showcase Director — SKILL.md

Minecraft Server Agent Operations Runbook.md

Minecraft Server Node Bootstrap Runbook.md
```

These documents have different responsibilities.

They are **not interchangeable**.

---

# 2. Absolute Rule

Always begin with:

```text
THIS ROUTER
```

Then determine the task category.

Never load all documents unless performing:

```text
SYSTEM ARCHITECTURE REVIEW
```

or:

```text
MAJOR PIPELINE REDESIGN
```

Context discipline is part of the production system.

---

# 3. Primary Routing Decision

Ask internally:

> What is the user actually trying to accomplish right now?

Choose one primary route:

```text
A. RUN / DIRECT A MINECRAFT ENVIRONMENT PROJECT

B. ANALYZE TERRAIN OR PLAN A SETTLEMENT

C. IMPLEMENT OR DEBUG THE SOFTWARE SYSTEM

D. BUILD / MODIFY THE MINECRAFT WORLD

E. VALIDATE THE GENERATED WORLD

F. BENCHMARK AGAINST GDMC-LIKE GOALS

G. PRODUCE REPLAY / PORTFOLIO / CLIENT SHOWCASE

H. CHANGE THE OVERALL PIPELINE OR ARCHITECTURE

I. OPERATE OR RECOVER THE REMOTE MINECRAFT SERVER / RENDER WORKER
```

Then follow the matching route below.

---

# 4. ROUTE A
# Run or Direct a Minecraft Environment Project

Examples:

```text
"Generate a mountain village."

"Create a Chinese waterside town."

"Build an RPG settlement on this Minecraft world."

"Continue the current environment project."

"Take this world from planning to completion."
```

Read first:

```text
1. Minecraft Environment Director.md
```

This is the main production authority.

It defines:

```text
project profile
production stages
stage locks
QA priorities
defect severity
completion gates
production responsibilities
```

Then read:

```text
2. Minecraft Environment Adapter — SKILL.md
```

only when actual Minecraft execution is approaching.

Do not start with Implementation Blueprint unless the request concerns software implementation.

---

# 5. ROUTE B
# Terrain Analysis / Settlement Planning

Examples:

```text
"Where should the settlement be built?"

"Analyze this terrain."

"Plan roads."

"Where should the temple go?"

"Generate districts."

"Design an organic village."

"Why does every generated settlement look identical?"

"The city ignores the terrain."

"The road layout is bad."
```

Read:

```text
Minecraft Terrain Intelligence & Settlement Planning Specification v1.md
```

This is the primary authority for:

```text
height analysis
slope
roughness
water
terrain zones
buildability
road cost
candidate generation

semantic planning
planning actions
district growth
landmarks
public spaces
footprints
decentralized iterative planning
```

Also read:

```text
Minecraft Environment Director.md
```

if the planning change may affect:

```text
locked stages
production priorities
existing project decisions
```

---

# 6. ROUTE C
# Software Implementation / Coding

Examples:

```text
"Start coding the project."

"Implement terrain_analysis.py."

"How should the repository be organized?"

"Design the JSON schema."

"Write the benchmark runner."

"Implement the action loop."

"How should GDPC be wrapped?"

"Create tests."
```

Read first:

```text
Minecraft Environment Factory — Implementation Blueprint v0.1.md
```

This is the canonical engineering starting point.

It defines:

```text
repository structure
Python modules
data classes
TerrainAnalysis
SettlementState
PlanningAction
Road Planner
Graybox Executor
QA interfaces
Benchmark Runner
MVP milestones
experiments
```

Then load specialist specifications only as required.

Examples:

### Implement terrain analysis

Read:

```text
Implementation Blueprint v0.1
+
Terrain Intelligence & Settlement Planning Specification v1
```

### Implement planner

Read:

```text
Implementation Blueprint v0.1
+
Terrain Intelligence & Settlement Planning Specification v1
```

### Implement GDPC execution

Read:

```text
Implementation Blueprint v0.1
+
Minecraft Environment Adapter — SKILL.md
+
Minecraft Environment Core Specialist Pack v1.md
```

### Implement QA

Read:

```text
Implementation Blueprint v0.1
+
Minecraft Environment Core Specialist Pack v1.md
```

---

# 7. ROUTE D
# Build or Modify the Minecraft World

Examples:

```text
"Create the roads."

"Build the graybox."

"Place building footprints."

"Generate architecture."

"Terraform this region."

"Modify the river."

"Execute this plan in Minecraft."
```

Read:

```text
Minecraft Environment Adapter — SKILL.md
```

This document controls:

```text
read-before-write
bounded write regions
protected regions
transactions
specialist routing
GDPC / WorldEdit selection
post-write readback
dependency reporting
```

Then read:

```text
Minecraft Environment Core Specialist Pack v1.md
```

to identify the specialist responsible for the operation.

Never let the Environment Director directly place arbitrary blocks.

Never let a Planner directly execute GDPC writes.

---

# 8. Specialist Routing

Use:

```text
Minecraft Environment Core Specialist Pack v1.md
```

when the task requires one of the following:

---

## Terrain Analysis

Use:

```text
mc-terrain-analysis
```

for:

```text
heightmaps
slope
water
biomes
buildability
road cost
terrain zones
```

---

## Settlement Planning

Use:

```text
mc-settlement-planner
```

for:

```text
settlement core
districts
landmarks
public spaces
footprints
semantic graph
```

---

## Road Planning

Use:

```text
mc-road-planner
```

for:

```text
main roads
secondary roads
terrain-aware routes
bridge requests
path costs
```

---

## Architecture Families

Use:

```text
mc-building-grammar
```

for:

```text
building families
roof rules
facade grammar
Minecraft-native detail
controlled variation
```

---

## World Execution

Use:

```text
mc-gdpc-executor
```

for:

```text
world reads
bounded writes
buffering
procedural execution
readback
transaction bookkeeping
```

---

## Structural Validation

Use:

```text
mc-structural-qa
```

for:

```text
road connectivity
building access
foundation contact
roof coverage
player clearance
protected region integrity
```

---

# 9. ROUTE E
# Validate or Debug a Generated World

Examples:

```text
"The town looks wrong."

"Some buildings are inaccessible."

"The road is disconnected."

"The generator keeps destroying terrain."

"Buildings are floating."

"The second floor cannot be reached."

"Why did this generation fail?"
```

First determine whether the problem is:

```text
STRUCTURAL
PLANNING
VISUAL
EXECUTION
```

---

## Structural Problem

Read:

```text
Minecraft Environment Core Specialist Pack v1.md
```

Focus on:

```text
mc-structural-qa
```

Do not use visual judgment when deterministic QA can answer the question.

---

## Planning Problem

Read:

```text
Minecraft Terrain Intelligence & Settlement Planning Specification v1.md
```

Examples:

```text
bad district logic
poor landmark placement
unreasonable town shape
roads make no semantic sense
settlement ignores terrain
```

---

## Execution Problem

Read:

```text
Minecraft Environment Adapter — SKILL.md
```

Examples:

```text
writes outside build area
protected region damaged
transaction failure
stale world state
GDPC write mismatch
```

---

## Visual / Aesthetic Problem

First confirm:

```text
P0 = 0
P1 = 0
```

Then use the visual evaluation / showcase route.

Never fix aesthetics while structural P1 defects remain.

---

# 10. Defect Priority Router

When multiple problems exist, solve in this order:

```text
P0
World / execution failure

↓

P1
Structural failure

↓

P2
Planning / gameplay failure

↓

P3
Architecture failure

↓

P4
Visual / aesthetic failure

↓

P5
Micro-detail
```

Examples:

```text
road disconnected
+
houses repetitive
```

Fix:

```text
road
```

first.

---

# 11. ROUTE F
# GDMC-Like Benchmarking

Examples:

```text
"How strong is the generator?"

"Compare v0.2 and v0.3."

"Benchmark five maps."

"Does the LLM planner beat the heuristic baseline?"

"Are we approaching GDMC quality?"

"Why did the benchmark regress?"
```

Read:

```text
GDMC Benchmark Harness — Specification v1.md
```

This is the authority for:

```text
multi-map benchmark
hidden evaluation set
structural gates
Adaptability
Functionality
Narrative
Aesthetics
failure taxonomy
generator version comparison
regression detection
```

If benchmark failure concerns a specific subsystem, route again.

Examples:

```text
Adaptability low
→ Terrain Intelligence & Settlement Planning

Road failures high
→ Core Specialist Pack / road-planner

Execution failures
→ Environment Adapter

Architecture repetition
→ building-grammar
```

---

# 12. Benchmark Debug Routing

Use benchmark output to identify the owner.

```text
TERRAIN_FAILURE
→ mc-terrain-analysis

PLANNING_FAILURE
→ mc-settlement-planner

ROAD_FAILURE
→ mc-road-planner

BUILDING_FAILURE
→ mc-building-grammar / architecture layer

ACCESSIBILITY_FAILURE
→ mc-structural-qa + owning generator

EXECUTION_FAILURE
→ mc-gdpc-executor / Environment Adapter

VISUAL_FAILURE
→ visual / showcase layer
```

Do not modify unrelated subsystems to compensate for a benchmark failure.

---

# 13. ROUTE G
# Replay Mod / Portfolio / Commercial Showcase

Examples:

```text
"Make a cinematic walkthrough."

"Plan a Replay Mod video."

"Find hero shots."

"Create a Fiverr portfolio presentation."

"Make a before-and-after video."

"Generate a project walkthrough."

"Which parts of the town should the trailer show?"
```

Read:

```text
Minecraft Showcase Director — SKILL.md
```

It controls:

```text
hero shot selection
camera candidate generation
cinematic motion
Replay path specification
walkthrough structure
generation breakdown
before / after views
showcase QA
```

If Showcase discovers an environment problem:

Do not directly modify the world.

Return:

```text
ENVIRONMENT_REOPEN_REQUEST
```

to:

```text
Minecraft Environment Director
```

---

# 14. Showcase Problem Router

When Showcase reports:

```text
CAMERA_PROBLEM
```

remain in:

```text
Minecraft Showcase Director
```

Example:

```text
bad angle
camera clipping
weak reveal
```

When Showcase reports:

```text
ENVIRONMENT_PROBLEM
```

route back to:

```text
Minecraft Environment Director
```

Examples:

```text
unfinished building backside
landmark blocked from all approaches
empty district
repetitive skyline
bad landscape composition
```

---

# 15. ROUTE H
# Overall Pipeline / Architecture Changes

Examples:

```text
"Should we change the whole pipeline?"

"Where should a new Agent fit?"

"Should planning use Blender?"

"Should we replace GDPC?"

"How should commercial mode differ from GDMC mode?"

"Add a new backend."

"Redesign the Director architecture."
```

Read:

```text
Minecraft Environment Factory Pipeline v2.md
```

This is the highest-level pipeline architecture document.

It defines:

```text
GDMC mode
Production mode
Showcase mode

World Intelligence
Planning
Graybox
Infrastructure
Architecture
Landscape
QA
Benchmark
Showcase
Commercial Delivery
```

Also consult:

```text
Minecraft Environment Director.md
```

when production responsibility or stage authority changes.

---

# 15.1 ROUTE I
# Operate or Recover the Remote Minecraft Runtime

Examples:

```text
"The server and render worker are both stopped."

"Minecraft is running but Visual Probe is not READY."

"Reuse the existing mc-server and hmc-render sessions."

"Inspect or recover the Ubuntu HeadlessMC node."

"Install a new bare Ubuntu Minecraft node."
```

Read:

```text
Minecraft Server Agent Operations Runbook.md
```

This is the authority for the deployed node's cold start, hot start, partial
state recovery, exact paths, readiness checks, logs, and shutdown order.

If the task will mutate the world, also read:

```text
TASK_STATE.md
+
Minecraft Environment Adapter — SKILL.md
```

Runtime readiness never grants world-write authority.

For a `BARE_NODE` with missing Java, server/client files, or mods, read instead:

```text
Minecraft Server Node Bootstrap Runbook.md
```

After installation acceptance, return to the Operations Runbook for routine
cold/hot lifecycle management.

---

# 16. Document Authority Table

When documents overlap, use this priority.

| Question | Primary Authority |
|---|---|
| What should happen next? | `Minecraft Environment Director.md` |
| How does the whole system fit together? | `Minecraft Environment Factory Pipeline v2.md` |
| How do semantic decisions become Minecraft operations? | `Minecraft Environment Adapter — SKILL.md` |
| Which specialist owns this task? | `Minecraft Environment Core Specialist Pack v1.md` |
| How should terrain/planning intelligence work? | `Minecraft Terrain Intelligence & Settlement Planning Specification v1.md` |
| How should the Python project actually be built? | `Minecraft Environment Factory — Implementation Blueprint v0.1.md` |
| How should generator performance be measured? | `GDMC Benchmark Harness — Specification v1.md` |
| How should final worlds be presented? | `Minecraft Showcase Director — SKILL.md` |
| How should the deployed server/render worker be started or recovered? | `Minecraft Server Agent Operations Runbook.md` |
| How should a bare Ubuntu node be provisioned, including offline artifact transfer? | `Minecraft Server Node Bootstrap Runbook.md` |

---

# 17. Conflict Resolution

If two documents appear to disagree:

## Production Stage / Lock conflict

Prefer:

```text
Minecraft Environment Director.md
```

## Implementation detail conflict

Prefer:

```text
Implementation Blueprint v0.1.md
```

unless superseded by explicit newer implementation decisions.

## Terrain or planning algorithm conflict

Prefer:

```text
Minecraft Terrain Intelligence & Settlement Planning Specification v1.md
```

## Execution safety conflict

Prefer:

```text
Minecraft Environment Adapter — SKILL.md
```

## Benchmark methodology conflict

Prefer:

```text
GDMC Benchmark Harness — Specification v1.md
```

## Showcase conflict

Prefer:

```text
Minecraft Showcase Director — SKILL.md
```

---

# 18. Never Solve by Loading Everything

Bad:

```text
Read all eight documents.
Try to remember everything.
Start editing.
```

Preferred:

```text
Identify current stage
        ↓
Read Router
        ↓
Read Director if production decision is required
        ↓
Read ONE primary domain document
        ↓
Read specialist details only when necessary
```

Typical active document set should be:

```text
2–4 documents
```

not:

```text
8 documents
```

---

# 19. Recommended Reading Bundles

## Starting a new environment project

Read:

```text
Router
+
Environment Director
+
Pipeline v2
```

Then stop.

Do not load technical implementation documents yet.

---

## Starting terrain analysis implementation

Read:

```text
Router
+
Implementation Blueprint
+
Terrain Intelligence & Settlement Planning
```

---

## Starting settlement planning implementation

Read:

```text
Router
+
Implementation Blueprint
+
Terrain Intelligence & Settlement Planning
+
Core Specialist Pack
```

---

## Starting GDPC integration

Read:

```text
Router
+
Environment Adapter
+
Core Specialist Pack
+
Implementation Blueprint
```

---

## Debugging a generated settlement

Read:

```text
Router
+
Environment Director
+
relevant specialist document
```

Add benchmark document only if debugging benchmark behavior.

---

## Preparing a GDMC-style experiment

Read:

```text
Router
+
GDMC Benchmark Harness
+
Implementation Blueprint
```

Add terrain/planning spec if the experiment changes planning behavior.

---

## Creating commercial portfolio media

Read:

```text
Router
+
Minecraft Showcase Director
```

Add Environment Director only when Showcase requests world changes.

---

## Operating the remote Minecraft node

Read:

```text
Router
+
Minecraft Server Agent Operations Runbook
```

Add `TASK_STATE` and the Environment Adapter only when world mutation is in
scope. Do not preload the architecture and Probe specifications for routine
startup.

---

## Provisioning a new bare Minecraft node

Read:

```text
Router
+
Minecraft Server Node Bootstrap Runbook
```

Do not treat a missing dependency as an ordinary cold start. After the bootstrap
acceptance gate passes, switch to the Operations Runbook.

---

# 20. Current Production Stage Detection

Before acting, inspect:

```text
TASK_STATE
```

if available.

Expected fields:

```text
PROJECT
MODE
CURRENT_STAGE
LOCKS
OPEN_DEFECTS
CURRENT_OBJECTIVE
LAST_CHECKPOINT
NEXT_ACTION
```

If TASK_STATE exists:

> trust explicit project state over assumptions from conversation history.

---

# 21. If TASK_STATE Does Not Exist

Create or reconstruct a minimal one.

Do not infer advanced progress from the presence of files alone.

Example:

```text
PROJECT:
UNKNOWN

MODE:
PRODUCTION

CURRENT_STAGE:
UNKNOWN

LOCKS:
UNKNOWN

OPEN_DEFECTS:
UNKNOWN

CURRENT_OBJECTIVE:
user request

NEXT_ACTION:
determine production state
```

Then inspect only the information necessary to identify current state.

---

# 22. Stage Router

Use:

```text
INTAKE
→ Environment Director

WORLD_ANALYSIS
→ Terrain Intelligence

SEMANTIC_PLANNING
→ Terrain Intelligence + Settlement Planner

GRAYBOX
→ Adapter + Executor + QA

INFRASTRUCTURE
→ Road Planner + Adapter + QA

ARCHITECTURE
→ Building Grammar + Adapter + QA

LANDSCAPE
→ relevant landscape specialist + Adapter

FINAL_QA
→ Structural QA

BENCHMARK
→ GDMC Benchmark Harness

SHOWCASE
→ Showcase Director
```

---

# 23. Problem-to-Document Quick Router

```text
"I don't know where to start."
→ Environment Director


"The terrain analysis is poor."
→ Terrain Intelligence & Settlement Planning


"The town layout is bad."
→ Terrain Intelligence & Settlement Planning


"Roads are weird."
→ Core Specialist Pack: mc-road-planner


"All houses look the same."
→ Core Specialist Pack: mc-building-grammar


"The Agent modifies things it should not."
→ Environment Adapter


"GDPC writes outside the area."
→ Environment Adapter


"The build crashes / execution fails."
→ Environment Adapter + mc-gdpc-executor


"The server or HeadlessMC render worker is stopped / degraded."
→ Minecraft Server Agent Operations Runbook


"A new Ubuntu server has no Java, Minecraft, HeadlessMC, or mods."
→ Minecraft Server Node Bootstrap Runbook


"The server cannot download HMC-Specifics from GitHub."
→ Minecraft Server Node Bootstrap Runbook


"Visual Probe is NO_WORLD or its session file is stale."
→ Minecraft Server Agent Operations Runbook


"Players can't enter buildings."
→ mc-structural-qa


"World looks good but benchmark is bad."
→ GDMC Benchmark Harness


"One seed looks great, others fail."
→ GDMC Benchmark Harness
+
Terrain Intelligence


"We need a Replay video."
→ Showcase Director


"Replay video reveals ugly areas."
→ Showcase Director
→ Environment Reopen Request


"We want to change the whole production architecture."
→ Pipeline v2
```

---

# 24. LLM Responsibility Boundary

The LLM should primarily handle:

```text
semantic decisions
spatial intent
trade-offs
narrative causality
candidate selection
diagnosis
production routing
```

Algorithms should primarily handle:

```text
height calculations
slope
connected components
pathfinding
collision
world writes
accessibility
region enforcement
metrics
```

If a deterministic algorithm can answer a factual geometric question:

> use the algorithm.

---

# 25. Write Safety Rule

Before any world mutation, the active context must include:

```text
Minecraft Environment Adapter — SKILL.md
```

or equivalent execution safety rules.

No Planner may directly gain unrestricted world-write authority.

Required pattern:

```text
PLAN
↓
VALIDATE
↓
ADAPTER
↓
BOUNDED EXECUTOR
↓
READBACK
↓
QA
```

---

# 26. World Lock Rule

If a requested change touches a locked layer:

Do not silently modify it.

Return:

```text
REOPEN_REQUEST
```

to the Environment Director.

Example:

```text
Current stage:
Landscape

Requested fix:
move primary road

Result:
LOCK_MAIN_ROADS violation

Action:
Environment Director review required
```

---

# 27. Benchmark vs Production vs Showcase

Do not confuse these modes.

## GDMC / Benchmark

Question:

> Is the generator generally intelligent and robust?

## Production

Question:

> Is this particular world excellent?

## Showcase

Question:

> Can this excellent world be presented compellingly?

A world can score differently in all three.

---

# 28. Do Not Optimize for Showcase Too Early

The correct order is:

```text
STRUCTURAL VALIDITY
↓
ENVIRONMENT QUALITY
↓
BENCHMARK CONFIDENCE
↓
SHOWCASE QUALITY
```

A Replay trailer must never substitute for:

```text
road connectivity
terrain adaptation
building access
generalization
```

---

# 29. Minimal Context Principle

Before each major task, ask:

> What is the smallest document set sufficient to perform this task safely?

Prefer:

```text
Router
+
one authority document
+
one specialist
```

over:

```text
entire Minecraft Environment corpus
```

This reduces:

```text
context dilution
instruction conflict
role confusion
unnecessary token usage
```

---

# 30. New Document Rule

Before creating a new Minecraft Environment document:

Check whether the information belongs in an existing authority document.

Create a new document only when it defines a genuinely separate responsibility.

Good reasons:

```text
new specialist
new backend
new evaluation system
new production mode
```

Bad reason:

```text
the current document is already long
```

Avoid documentation fragmentation.

---

# 31. Document Naming Rule

Use functional names.

Recommended:

```text
00 - Minecraft Environment Router - START HERE.md

Minecraft Environment Director.md

Minecraft Environment Adapter — SKILL.md

Minecraft Environment Core Specialist Pack v1.md

Minecraft Terrain Intelligence & Settlement Planning Specification v1.md

Minecraft Environment Factory — Implementation Blueprint v0.1.md

Minecraft Environment Factory Pipeline v2.md

GDMC Benchmark Harness — Specification v1.md

Minecraft Showcase Director — SKILL.md
```

The Router must remain visibly first.

---

# 32. New Session Startup Procedure

When a new LLM session begins:

```text
STEP 1
Read Router.

STEP 2
Read TASK_STATE if available.

STEP 3
Classify current task.

STEP 4
Load primary authority document.

STEP 5
Load only required specialist documents.

STEP 6
Confirm locks and write permissions.

STEP 7
Continue production.
```

Do not reconstruct the entire project history from scratch.

---

# 33. Recommended Router Response Pattern

After routing internally, the Agent should be able to summarize:

```text
CURRENT TASK:
Settlement planning

CURRENT STAGE:
Semantic Planning

PRIMARY AUTHORITY:
Minecraft Terrain Intelligence & Settlement Planning Specification v1.md

SECONDARY AUTHORITY:
Minecraft Environment Director.md

SPECIALIST:
mc-settlement-planner

WORLD WRITE:
NOT ALLOWED

NEXT ACTION:
Generate candidate semantic planning actions.
```

This format is particularly useful during autonomous development.

---

# 34. Escalation Rule

If the current specialist cannot solve the problem without changing a higher-level
decision:

Do not improvise.

Escalate upward.

Hierarchy:

```text
Executor
   ↑
Specialist
   ↑
Adapter
   ↑
Environment Director
```

Example:

```text
Road Planner:
"No feasible path exists without moving the settlement core."

Do NOT move settlement core.

Escalate to Environment Director.
```

---

# 35. Completion Routing

When a stage finishes:

Return to:

```text
Minecraft Environment Director
```

The Director decides whether to:

```text
LOCK
ADVANCE
REPAIR
REOPEN
BENCHMARK
SHOWCASE
```

Specialists do not independently advance the full pipeline.

---

# 36. Golden Rule

The purpose of this Router is not to contain all Minecraft Environment knowledge.

Its purpose is to answer:

> **Where am I in the production system, who owns the current problem, what is
> the minimum knowledge I need, and what am I allowed to do next?**

If those four questions are clear, the Router has succeeded.
