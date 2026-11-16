# Decision log

Status as of 2026-11-15. Nothing is built, so every decision is a design decision, not something proven by running code.

**Status values**
- **Decided**: I chose it, or it follows directly from a goal I stated.
- **Proposed**: recommended by the assistant, I have not confirmed it. Cheap to change now.
- **Open**: not decided; needs an answer before the milestone named.

## Decided

| ID | Decision | Why | Alternatives rejected | What would change it |
|----|----------|-----|-----------------------|----------------------|
| D01 | New project **learning-rts** in its own repo (`code/learning-rts/`), isolated from deep-rts | Analysis of deep-rts must stay reproducible and never mix with my own code | Developing inside the deep-rts clone | n/a |
| D02 | **learning-rts is my own design; deep-rts is inspiration and a starting reference**, not a base I fix or port | Me (2026-11-15): the design will keep changing and diverging as I redesign it; the goal is to learn game AI with my own game, "even if we completely change the technology"; paper fidelity is explicitly not a goal. Separately, deep-rts does not build and has silent RL-contract defects ([findings](../architecture-docs/reports/findings-summary.md)), which would make it a poor base anyway | Fixing deep-rts in place; porting it | Needing exact DeepRTS rules (for example to reproduce the paper) |
| D03 | Goal: an **arena** where parametrized agents play each other, rated, with scripted → search → learned agents as a ladder | My stated end goal: insert parameters/instructions and run models against each other | Building an RL environment first and treating the arena as an add-on | n/a |
| D04 | Games can be **watched live and as replays**, in a browser | My requirement | Headless-only | n/a |
| D05 | **DeepRTS sprites** from the start and for the foreseeable future | My requirement. Caveat: **provenance is unknown**. The repo's MIT licence covers code; unit names (peasant, footman, grunt, peon, axethrower, town hall) match Warcraft II; no file records the art's origin. Treat as possibly third-party until shown otherwise. Fine for local use; do not publish them. My project **ejaj-boj** uses Pixel Frog's Tiny Swords packs, **CC0 per its `CREDITS.md`**, which is a sprite source with a known licence (Q10). | n/a | Learning the real licence |
| D06 | Resources: **gold first, wood and stone later** | Me: start with one for the proof of concept. deep-rts already has Gold, Lumber and Stone tile types and yields, so maps and art cover all three (the maps themselves were not checked for stone tiles). | All three from day one | n/a |
| D07 | Simulation core in **Rust** | I chose it after the assistant recommended it; I am willing to learn it. Reasons: safe Rust has no undefined behaviour (deep-rts's worst defects were pointer and copy bugs); `#[derive(Clone)]` makes snapshots nearly free; first-class WASM target. | C++ (my past language; reuses deep-rts knowledge but brings undefined behaviour and the build-system pain that killed deep-rts); Python/numba first (fastest to the arena, but hits a wall at evolution and tree search and has no WASM path) | The Rust learning curve making early milestones too slow. **Timing of the Rust work is proposed separately in D26** (Python reference sim first, Rust from M4b/M4c); the language choice itself stays decided |
| D08 | **Teaching mode**: explain choices, show code, explain Rust concepts | I am learning Rust; stated 2026-11-15 | n/a | n/a |
| D09 | Docs live in the **metarepo** (`docs/general/`, `docs/roadmap/`) | My instruction | In the `learning-rts` repo | n/a |

## Proposed (not yet confirmed by me)

| ID | Decision | Why | Alternatives | What would change it |
|----|----------|-----|--------------|----------------------|
| D10 | **Python** for agents, arena, research, and (per D26) the **reference sim** for M1-M4b | PyTorch, numpy, CMA-ES libraries are all Python; fastest iteration on bots; ejaj-boj's concepts and 18-parameter agent are Python and port directly | Bots in Rust (faster, slower to write) | A bot becoming the bottleneck: port that one |
| D11 | **Python match server** (WebSocket), not a Rust server | The server only calls `step()`, paces and pushes snapshots; Python handles that at a small game's snapshot size. Fewer languages. It is the vehicle for the real-time-systems track (D27): pacing, backpressure, reconnect, load tests. | Rust server (axum/tokio): more code for no early gain | Measured pacing problems with many spectators |
| D12 | **TypeScript + Canvas 2D** viewer, no framework | Runs in any browser, supports spectators, `drawImage` handles sprite sheets | Python viewer (pygame): simpler, but no browser or spectators; Godot/Unity: heavy and awkward for headless batch runs | n/a |
| D13 | **TOML** for rulesets and agent specs; **JSON** for maps and replays | Maps are already Tiled JSON; TOML reads well for hand-edited config | YAML (indentation pitfalls), RON (Rust-only) | n/a |
| D14 | **Tick-based core, no wall clock**; pacing belongs to the match runner | Determinism, and it removes deep-rts's wall-clock step gate (60 steps/s default) | Real-time loop inside the engine | n/a |
| D15 | **No floating point in the sim**: integer or fixed-point math | Float results can differ across machines or compilers, which would break the determinism contract | Floats with strict flags: fragile | Proof that floats are deterministic enough on the machines used |
| D16 | The core mutates only via `step(commands)` and returns **events**; observations are computed on demand; rewards are functions over events | Fixes the root cause of deep-rts's stale-observation and boolean-reward defects | Writing observations inside entity methods (deep-rts) | n/a |
| D17 | **Struct-of-arrays storage with generational ids**; no pointers to entities | Removes the dangling-pointer class; makes snapshots a copy | Entities as heap objects with pointers | Profiling showing SoA is awkward for a specific system |
| D18 | **Snapshot/restore** is a core feature | MCTS and the viewer depend on it | Re-simulating from the start (too slow for search) | n/a |
| D19 | **Command-level actions** ("train X", "send group G to P"), not per-unit-per-tick steering | Readable bots; tractable RL on a CPU-only machine | Per-unit low-level actions | Wanting micro-management research |
| D20 | **Replay = header + per-tick snapshots** first (static map once, then per-tick deltas); later a command log + WASM re-simulation | Viewer then needs no sim; the WASM upgrade gives exact backward scrubbing. ejaj-boj sent the full map every tick (97% of each frame), which deltas avoid | Command log from the start (needs the sim in the browser immediately) | n/a |
| D21 | **Small game**: about 32x32 maps, 3-4 unit types with counters, no fog of war at first | Engine complexity should not drown the AI work; counters make non-transitive results visible | Full DeepRTS-sized game | n/a |
| D22 | **A\*** pathfinding first; JPS only if profiling asks | Simplest correct thing | Port deep-rts's JPS | Profiling |
| D23 | **Skins**: sprites are **not committed** to `learning-rts`; the viewer loads them through a manifest from a configurable path; a flat-colour placeholder skin always works | Provenance caveat in D05 | Committing the sprites | Resolving D05 |
| D24 | **M3b** (add wood and stone) comes **before** parameter optimization (M4); ratings from before M3b are discarded | Avoid tuning bots on a game that then changes | Adding resources late | n/a |
| D25 | Arena results in **SQLite** | Built into Python, queryable, one file | JSON lines (simpler, harder to query) | n/a |
| D26 | **Three tracks (AI, real-time systems, Rust); Rust enters late and bounded.** Python reference sim at M1; PyO3 leaf module at M4b (the function profiling picks, likely A*); full Rust core port at M4c, checked by per-tick state-hash equality against the Python sim | Goal 1 (game AI) gets a playable arena at M3 instead of after a full Rust core; Goal 2 (Rust) is served by a real, measured port rather than a speculative first draft; the Python sim becomes the test oracle, which makes the port learnable (a failing hash shows exactly which rule differs) | Rust core first (M1, as D07 originally implied): most Rust learning early, but the rules are not yet known, so the core would be rewritten as they change; Python only: never learns Rust | The Python sim not being deterministic or not matching its own design principles (then no oracle: write the Rust core first); Rust learning-by-doing being preferred over a smaller first win |
| D27 | **Real-time systems is a named track** with its own gates (M1c, M3c): pacing, slow-client backpressure that never blocks the sim, snapshot plus delta, reconnect with resume, fog as interest management (M7), load tests with recorded bytes/s | Goal 3. These are the parts of ejaj-boj that were weakest (full map every tick, no reconnect story, tick exception wedging the engine) and are skills that carry beyond games | Treating the server as plumbing | n/a |

## Deviations made while building (2026-11-15 overnight session)

I was asleep, so these were the assistant's calls. Each is reversible; tell me if you disagree.

| Decision affected | What was done | Why | Cost |
|-------------------|---------------|-----|------|
| D24 (M3b before M4) | M4 evolution was built on the **gold-only** game | M3b changes costs and bots; doing M4 first gave a working optimiser sooner | All ratings and the evolved agent are thrown away when wood/stone land, as D24 already says |
| D12 (TypeScript viewer) | Viewer is **plain JavaScript** (`viewer/viewer.js`) | No TypeScript compiler on this machine; the rendering logic is the same | A port later; types would catch the frame-format drift the notes-merge bug showed |
| D17 (struct-of-arrays) | Python reference sim stores entities as **dicts keyed by id** | Readability; SoA matters for the Rust core, where snapshots must be cheap | The Rust port will have to re-derive the layout; the state hash is defined on the dict form |
| D23 (sprites not committed) | Sprites come from **ejaj-boj's CC0 Tiny Swords** via `scripts/setup_skin.py`, still gitignored; DeepRTS sprites **not used yet** | Known licence, files already local; DeepRTS sheets are unmapped (Q04) | D05 asks for DeepRTS sprites "from the start"; that is not met. Q10 is effectively answered "ejaj-boj first" |
| D14/D16 (no RNG in sim) | `step` uses **no RNG at all**; seeded RNG lives in map generation only | Ties are broken by fixed order, so determinism is simpler to prove | Combat has no variance; add a seeded RNG owned by the world if I want it |
| Time-limit rule (not a numbered decision) | At tick 3000 the side with more hall hp, then more army value, wins | A game needs an end | **The first evolved agent exploits it**: it never attacks and wins every match on the tiebreak. Open: draw at the time limit, or score by damage dealt (Q11 below) |
| D20 (replay) | Replay = header + **full entity rows per tick** (650 KB for 1,271 ticks), no deltas yet | Simplest thing that works | Larger files; deltas are an M3c item |

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
| Q08 | Rust toolchain setup and project layout (crates/workspace); PyO3/maturin build for the M4b leaf module | M0 | Rust is **not installed** on this machine as of 2026-11-15 |
| Q09 | LLM-driven agents: which interface, decision interval, cost | M7 | Optional |
| Q10 | Sprites from my project **ejaj-boj**: use them as the default skin instead of, or next to, the DeepRTS sprites? | M1b | Analysed 2026-11-15 ([ejaj-boj docs](../ejaj-boj/architecture-docs/index.md)): 34 PNGs under `code/ejaj-boj/client/assets/`; `CREDITS.md` names two Pixel Frog packs (Tiny Swords Free and Enemy), both CC0 with source URL. Not every PNG's origin is recorded, and ejaj-boj has no LICENSE file for its own code. Frame layouts are in `client/lib/tile-coords.mjs`, `sprites.mjs`, `anim-config.mjs` and `scripts/setup_assets.py` (not yet mapped to a skin manifest). The skin manifest (D23) makes a second source cheap |
| Q11 | How should a game that hits the time limit be scored, so passivity does not win? | next session | Found 2026-11-16: the evolved agent wins every match by hoarding. Options: draw (simple, kills the exploit, many draws), damage dealt, resources spent on army. I recommend draw first |
| Q12 | Animated sprites: which sheets give walk, attack and death frames for each unit, and how does the skin manifest describe per-state animations? | after M3b (not scheduled) | Idle frames only today. ejaj-boj's `client/lib/anim-config.mjs` and the `Factions/Knights/Troops/` sheets are the first places to look; not inspected yet |

## Known unknowns

- **Throughput** (measured 2026-11-16, Python reference sim): about 5,200 ticks/s per core, 0.58 s per match, 6 processes gave roughly 6 matches/s in the arena. Two-machine determinism and larger games are unmeasured. It decides how far self-play can go on this machine (i7-1065G7, 8 threads, 15 GB, no GPU).
- **Sprite licence** (D05).
- **Whether the Rust learning curve is acceptable for M1** (D07). The fallback is in that row.

## Evidence that bears on the proposed decisions (ejaj-boj analysis, 2026-11-15)

Inputs only: no status above changed. ejaj-boj is my earlier parametric-RTS project (Python server, JavaScript canvas client); full analysis in [../ejaj-boj/architecture-docs/](../ejaj-boj/architecture-docs/index.md). Everything below was measured on this machine (i7-1065G7) unless marked *read*.

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

