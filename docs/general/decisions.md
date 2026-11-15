# Decision log

Status as of 2026-11-15. Nothing is built, so every decision is a design decision, not something proven by running code.

**Status values**
- **Decided**: the owner chose it, or it follows directly from a goal the owner stated.
- **Proposed**: recommended by the assistant, the owner has not confirmed it. Cheap to change now.
- **Open**: not decided; needs an answer before the milestone named.

## Decided

| ID | Decision | Why | Alternatives rejected | What would change it |
|----|----------|-----|-----------------------|----------------------|
| D01 | New project **learning-rts** in its own repo (`code/learning-rts/`), isolated from deep-rts | Analysis of deep-rts must stay reproducible and never mix with our own code | Developing inside the deep-rts clone | n/a |
| D02 | **learning-rts is our own design; deep-rts is inspiration and a starting reference**, not a base we fix or port | Owner (2026-11-15): the design will keep changing and diverging as it is redesigned; the goal is to learn game AI with their own game, "even if we completely change the technology"; paper fidelity is explicitly not a goal. Separately, deep-rts does not build and has silent RL-contract defects ([findings](../architecture-docs/reports/findings-summary.md)), which would make it a poor base anyway | Fixing deep-rts in place; porting it | Needing exact DeepRTS rules (for example to reproduce the paper) |
| D03 | Goal: an **arena** where parametrized agents play each other, rated, with scripted → search → learned agents as a ladder | Owner's stated end goal: insert parameters/instructions and run models against each other | Building an RL environment first and treating the arena as an add-on | n/a |
| D04 | Games can be **watched live and as replays**, in a browser | Owner requirement | Headless-only | n/a |
| D05 | **DeepRTS sprites** from the start and for the foreseeable future | Owner requirement. Caveat: **provenance is unknown**. The repo's MIT licence covers code; unit names (peasant, footman, grunt, peon, axethrower, town hall) match Warcraft II; no file records the art's origin. Treat as possibly third-party until shown otherwise. Fine for local use; do not publish them. The owner's project **ejaj-boj** uses Pixel Frog's Tiny Swords packs, **CC0 per its `CREDITS.md`**, which is a sprite source with a known licence (Q10). | n/a | Learning the real licence |
| D06 | Resources: **gold first, wood and stone later** | Owner: start with one for the proof of concept. deep-rts already has Gold, Lumber and Stone tile types and yields, so maps and art cover all three (the maps themselves were not checked for stone tiles). | All three from day one | n/a |
| D07 | Simulation core in **Rust** | Owner chose it after I recommended it and said they are willing to learn it. Reasons: safe Rust has no undefined behaviour (deep-rts's worst defects were pointer and copy bugs); `#[derive(Clone)]` makes snapshots nearly free; first-class WASM target. | C++ (owner's past language; reuses deep-rts knowledge but brings undefined behaviour and the build-system pain that killed deep-rts); Python/numba first (fastest to the arena, but hits a wall at evolution and tree search and has no WASM path) | The Rust learning curve making early milestones too slow: then prototype the core in Python behind the same interfaces and rewrite when profiling says so |
| D08 | **Teaching mode**: explain choices, show code, explain Rust concepts | Owner is learning Rust; stated 2026-11-15 | n/a | n/a |
| D09 | Docs live in the **metarepo** (`docs/general/`, `docs/roadmap/`) | Owner instruction | In the `learning-rts` repo | n/a |

## Proposed (not yet confirmed by the owner)

| ID | Decision | Why | Alternatives | What would change it |
|----|----------|-----|--------------|----------------------|
| D10 | **Python** for agents, arena, research | PyTorch, numpy, CMA-ES libraries are all Python; fastest iteration on bots | Bots in Rust (faster, slower to write) | A bot becoming the bottleneck: port that one |
| D11 | **Python match server** (WebSocket), not a Rust server | The server only calls `step()`, paces and pushes snapshots; Python handles that at a small game's snapshot size. Fewer languages. | Rust server (axum/tokio): more code for no early gain | Measured pacing problems with many spectators |
| D12 | **TypeScript + Canvas 2D** viewer, no framework | Runs in any browser, supports spectators, `drawImage` handles sprite sheets | Python viewer (pygame): simpler, but no browser or spectators; Godot/Unity: heavy and awkward for headless batch runs | n/a |
| D13 | **TOML** for rulesets and agent specs; **JSON** for maps and replays | Maps are already Tiled JSON; TOML reads well for hand-edited config | YAML (indentation pitfalls), RON (Rust-only) | n/a |
| D14 | **Tick-based core, no wall clock**; pacing belongs to the match runner | Determinism, and it removes deep-rts's wall-clock step gate (60 steps/s default) | Real-time loop inside the engine | n/a |
| D15 | **No floating point in the sim**: integer or fixed-point math | Float results can differ across machines or compilers, which would break the determinism contract | Floats with strict flags: fragile | Proof that floats are deterministic enough on the machines used |
| D16 | The core mutates only via `step(commands)` and returns **events**; observations are computed on demand; rewards are functions over events | Fixes the root cause of deep-rts's stale-observation and boolean-reward defects | Writing observations inside entity methods (deep-rts) | n/a |
| D17 | **Struct-of-arrays storage with generational ids**; no pointers to entities | Removes the dangling-pointer class; makes snapshots a copy | Entities as heap objects with pointers | Profiling showing SoA is awkward for a specific system |
| D18 | **Snapshot/restore** is a core feature | MCTS and the viewer depend on it | Re-simulating from the start (too slow for search) | n/a |
| D19 | **Command-level actions** ("train X", "send group G to P"), not per-unit-per-tick steering | Readable bots; tractable RL on a CPU-only machine | Per-unit low-level actions | Wanting micro-management research |
| D20 | **Replay = header + per-tick snapshots** first; later a command log + WASM re-simulation | Viewer then needs no sim; the WASM upgrade gives exact backward scrubbing | Command log from the start (needs the sim in the browser immediately) | n/a |
| D21 | **Small game**: about 32x32 maps, 3-4 unit types with counters, no fog of war at first | Engine complexity should not drown the AI work; counters make non-transitive results visible | Full DeepRTS-sized game | n/a |
| D22 | **A\*** pathfinding first; JPS only if profiling asks | Simplest correct thing | Port deep-rts's JPS | Profiling |
| D23 | **Skins**: sprites are **not committed** to `learning-rts`; the viewer loads them through a manifest from a configurable path; a flat-colour placeholder skin always works | Provenance caveat in D05 | Committing the sprites | Resolving D05 |
| D24 | **M3b** (add wood and stone) comes **before** parameter optimization (M4); ratings from before M3b are discarded | Avoid tuning bots on a game that then changes | Adding resources late | n/a |
| D25 | Arena results in **SQLite** | Built into Python, queryable, one file | JSON lines (simpler, harder to query) | n/a |

## Open (decide by the milestone shown)

| ID | Question | Decide by | Notes |
|----|----------|-----------|-------|
| Q01 | Exact v1 unit list, costs, counters, win condition | M0 | Start from the constants in deep-rts; extraction is an M0 task |
| Q02 | Agent spec format: fields, how weights are referenced | M0 | TOML (D13) is the assumption |
| Q03 | Replay file layout (JSON vs binary, snapshot size, compression) | M1b | Measure snapshot size first |
| Q04 | Sprite sheet mapping: frame size, directions, animation frames | M1b | The sheets have not been inspected yet |
| Q05 | Rating system: Elo, Bradley-Terry or TrueSkill | M3 | Bradley-Terry fits a fixed pool of agents; Elo is simpler to explain |
| Q06 | Observation format for learned agents (entity list vs spatial tensor) | M6 | Depends on the learning approach |
| Q07 | How agents attach annotations to decisions (schema) | M3 | Viewer draws them |
| Q08 | Rust toolchain setup and project layout (crates/workspace) | M0 | Rust is **not installed** on this machine as of 2026-11-15 |
| Q09 | LLM-driven agents: which interface, decision interval, cost | M7 | Optional |
| Q10 | Sprites from the owner's project **ejaj-boj**: use them as the default skin instead of, or next to, the DeepRTS sprites? | M1b | Analysed 2026-11-15 ([ejaj-boj docs](../ejaj-boj/architecture-docs/index.md)): 34 PNGs under `code/ejaj-boj/client/assets/`; `CREDITS.md` names two Pixel Frog packs (Tiny Swords Free and Enemy), both CC0 with source URL. Not every PNG's origin is recorded, and ejaj-boj has no LICENSE file for its own code. Frame layouts are in `client/lib/tile-coords.mjs`, `sprites.mjs`, `anim-config.mjs` and `scripts/setup_assets.py` (not yet mapped to a skin manifest). The skin manifest (D23) makes a second source cheap |

## Known unknowns

- **Throughput is unmeasured.** The first real games-per-second figure comes with the arena (M3). It decides how far self-play can go on this machine (i7-1065G7, 8 threads, 15 GB, no GPU).
- **Sprite licence** (D05).
- **Whether the Rust learning curve is acceptable for M1** (D07). The fallback is in that row.

## Evidence that bears on the proposed decisions (ejaj-boj analysis, 2026-11-15)

Inputs only: no status above changed. ejaj-boj is the owner's earlier parametric-RTS project (Python server, JavaScript canvas client); full analysis in [../ejaj-boj/architecture-docs/](../ejaj-boj/architecture-docs/index.md). Everything below was measured on this machine (i7-1065G7) unless marked *read*.

| Bears on | Evidence |
|----------|----------|
| D07 (Rust), D10 (Python agents), the fallback in D07 | A pure-Python simulation of a similar game ran **about 2,670 ticks/s per core, both agents included (0.375 ms/tick)**; 20 matches had a median of 699 ticks, so **about 0.26 s per match, roughly 3.8 matches/s per core**. Parallel scaling was not measured. An arena and parameter evolution are plausible in Python at this game size; unit counts there are small (dozens), so this does not show that a larger game stays fast. |
| D18 (snapshot/restore) | A deepcopy of that Python match state costs **8.3 ms, about 22 ticks' worth**. Copy-based tree search would be slow with ordinary Python objects; struct-of-arrays state (D17) was not tested. |
| D14, D15, D17 (tick-based, no floats, no pointers) | ejaj-boj shows the failure modes these target: a **process-global entity-id counter** and the **global `random`** make runs reproducible only after resetting the counter; pacing is wall-clock (`asyncio.sleep`) in the server path although a synchronous `_run_tick()` exists; its state is plain objects mutated directly by agents. |
| D12, D20 (viewer, replay) | Its live and replay viewers share one renderer and worked end to end. Lessons: it sent the **full map every tick (97% of a 57 KB frame, about 574 KB/s per viewer)**, its replay has **no seed, parameters or version**, keeps only the last 3,600 ticks and is deleted on reset. D20 should store header metadata and send static data once. |
| D13, Q02 (agent spec) | Its agent parameter dict has 18 keys with **no validation**; one wrong type froze the engine in a permanent "running" state, and one parameter (`return_threshold`) is read nowhere. A spec should be validated against a schema. |
| D06, D21 (game scope) | Its game: 40×30 map, wood and stone (no gold), 4 unit kinds, 2 building kinds, fog of war, 18 agent parameters; rush vs default won 2 of 20 matches, so the parameter space has structure. |
| D05, D23 (sprites) | Tiny Swords art, CC0 per its `CREDITS.md` (Q10). |
| D16 (events, observations) | No event layer: agents read and mutate world objects directly, and receive the whole enemy object (fairness depends on agent discipline). |

