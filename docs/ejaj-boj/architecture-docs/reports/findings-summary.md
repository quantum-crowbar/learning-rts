# Findings Summary

**Project**: ejaj-boj (the owner's earlier parametric-RTS project, pinned `fde9d3c`)
**Generated**: 2026-11-15
**Active views**: 01 technology, 02 interfaces, 03 diagrams, 04 documentation audit, 05 dependency health, 06 data flow, 07 error handling, 09 code graph (SQLite)
**SQLite cookbook**: [sqlite-cookbook.md](sqlite-cookbook.md)

How to read the "verified" column: **ran** = reproduced by executing code (the 456-test suite, headless matches, small experiments); **graph** = from the code-graph database; **read** = from source reading only; **fetched** = from an external API.

**Headline**: unlike deep-rts, **ejaj-boj works**: it installs from a fresh clone, passes 456 tests, plays complete matches headless at about 2,700 ticks/s on one core, and serves a browser client with live view, replay and fog. Its problems are robustness (one silent-failure mode), a partly broken fog protocol, unvalidated inputs, drifting docs, and design choices (global engine, global RNG and ids, wall-clock-only pacing in the server) that matter if it is used as a base for something else.

---

## Priority Action List

| # | Priority | Category | Finding | Verified | View | Location |
|---|----------|----------|---------|----------|------|----------|
| 1 | P1 | Robustness | **An exception inside a tick leaves the engine `running` with a dead loop**: frozen game, `POST /start` answers 409 until `/reset`. One bad parameter value (`worker_ratio:"high"`) triggers it | ran | [07](../analysis/07-error-handling.md) E1/E2 | `game_engine.py:260-274`, `main.py:94-112` |
| 2 | P1 | Protocol | **A player-view client that connects after the fog baseline was taken gets a delta with no full grid** and renders no fog for the rest of the match (refresh, second tab, auto-reconnect) | ran (server), read (client) | [02](../analysis/02-interface-specification.md), [03](../analysis/03-architecture-diagrams.md) §5 | `main.py:147-150`, `fog.py:99-116`, `index.html:668-678` |
| 3 | P1 | Correctness | Simultaneous town-hall destruction declares **player 1 the winner** | ran | [06](../analysis/06-data-flow-map.md) Q5 | `game_engine.py:174-187` |
| 4 | P2 | Information hiding | Fog contract broken: enemy buildings in *explored* tiles are sent with live HP and queue; tile resource amounts (they fall as the enemy harvests) and `agent_goals` go to every client | read, ran (payload) | [02](../analysis/02-interface-specification.md) | `game_engine.py:229-236`, `:243-252` |
| 5 | P2 | Validation | `/start` accepts any dict; unknown keys ignored, wrong types crash the loop (#1). `return_threshold` is read nowhere, yet the UI slider and all presets set it | ran, graph | [02](../analysis/02-interface-specification.md) §3 | `main.py:72-77`, `constants.py:108` |
| 6 | P2 | Wiring | **Four client modules are unreachable from the page**: `anim.mjs`, `anim-config.mjs`, `fx.mjs`, `camera-helpers.mjs` (about 490 lines; animations are an open request in `specs/phase16.md`) | graph, read (import list) | [04](../analysis/04-documentation-audit.md) claim 23 | `client/index.html:375-380` |
| 7 | P2 | Performance | The full tile map is sent every tick: **97% of a 57 KB frame, about 574 KB/s per viewer**; the replay stores the same frames (up to about 41 MB per match) | ran | [02](../analysis/02-interface-specification.md), [06](../analysis/06-data-flow-map.md) Q3/Q4 | `game_engine.py:207-212` |
| 8 | P2 | Reproducibility | Runs are reproducible only if the **process-global entity-id counter** is reset; the agent AI and map use the **global `random`** | ran | [06](../analysis/06-data-flow-map.md) Q1/Q2 | `entities.py:21-27`, `agent.py:211,466` |
| 9 | P2 | Replay | Replays carry **no seed, parameters or version**; only the last 3,600 ticks (every 5th) survive; `/reset` or a new `/start` deletes them | read | [02](../analysis/02-interface-specification.md) §5 | `game_engine.py:266-269` |
| 10 | P2 | Documentation | 54% claim accuracy: stale counts (13/17 vs 18 params), wrong defaults, wrong architecture tree, stale 80×60 comments, a docstring for a function nobody calls | ran, read | [04](../analysis/04-documentation-audit.md) | `AGENTS.md`, `CONTEXT.md`, docstrings |
| 11 | P2 | Maintainability | `Agent._manage_production` has cyclomatic complexity **58** (`_manage_combat` 32, `_manage_scouting` 26); the whole policy lives in procedural methods; the attack rule exists twice (`Knight/Archer.try_attack` unused) | graph | [09](../analysis/09-code-graph.md) | `agent.py:316,688,524` |
| 12 | P2 | Security | No authentication; CORS `*`; any page can start/reset a reachable instance | read | [05](../analysis/05-dependency-health.md) S1-S4 | `main.py:54-59` |
| 13 | P3 | Robustness | One slow WebSocket client delays every tick (sequential awaited sends, no timeout) | read | [07](../analysis/07-error-handling.md) E4 | `game_engine.py:291-304` |
| 14 | P3 | Process | No licence file, no lockfile, no CI; pytest/httpx in the production image; Railway documented but not configured | read | [01](../analysis/01-technology-manifest.md), [05](../analysis/05-dependency-health.md) | repo root |
| 15 | P3 | Dead code | 29 candidates (10.7%): an unused import shim with an incompatible stub class, 18 client-library functions, unused helpers | graph | [dead-code.md](dead-code.md) | see report |

---

## Per-View Summary

| View | Status | Key findings |
|------|--------|--------------|
| 01 Technology | ✅ | Python 3.12 + FastAPI + asyncio server (2,767 lines), vanilla-JS canvas client; no persistence; 456 tests pass |
| 02 Interfaces | ⚠️ | 6 routes, WebSocket frame protocol, 18-key parameter contract; fog protocol and validation gaps |
| 03 Diagrams | ✅ | three layers (transport, orchestration, synchronous simulation); no function-level cycles |
| 04 Documentation audit | ⚠️ | 54% accuracy; right about structure, wrong about details |
| 05 Dependency health | 🟡 | unpinned but works with current releases; 0 advisories at resolved versions; no licence |
| 06 Data flow | ✅ | all in memory, one match; determinism depends on id reset |
| 07 Error handling | ⚠️ | one serious silent-failure mode (E1) |
| 09 Code graph | ✅ with named gaps | 271 nodes, 326 edges, 0 cycles; project-internal resolution 85.5% typed / 97.2% with name-match; pyan3 cross-check 85.6% agreement |

## Metrics Dashboard

| Metric | Value | Status |
|--------|-------|--------|
| Server tests | 456 pass, 1 skipped (3.2 s) | 🟢 |
| Client pure-JS tests | 142 pass, 1 fail (known) | 🟡 |
| `tests/fe/test-pure.mjs` | 55 failures, run by no runner (known) | 🟡 |
| Complexity hotspots (CC > 10) | 20 | 🔴 (top: 58, 36, 32) |
| Circular dependencies (function level) | 0 | 🟢 |
| Dead-code candidates | 29 of 271 (10.7%) | 🟡 |
| Documentation accuracy | 54% | 🟡 |
| Known vulnerabilities (8 Python packages) | 0 | 🟢 |
| Builds / runs | yes | 🟢 |

---

## Facts relevant to the learning-rts decisions

Inputs only; the decisions are in `docs/general/decisions.md`.

**What ejaj-boj already demonstrates (measured or read):**
- A **headless, synchronous simulation core**: the match can be driven by `GameEngine._run_tick()` with no server and no clock; tests do exactly that. *Measured*: 14,606 ticks in 5.48 s = **about 2,670 ticks/s per core in pure Python including both agents (0.375 ms/tick)**; 20 default-vs-default matches had a median of 699 ticks, so about **0.26 s per match, roughly 3.8 matches/s on one core**. Parallel scaling was not measured.
- A **parametric agent** with an 18-key parameter dict, and a parameter space with structure (rush vs default: 2 of 20 wins, *ran*).
- **Live browser viewer and replay viewer** sharing one renderer, fog of war, minimap, speed controls, parameter UI with presets.
- **CC0 sprite art with recorded provenance** (Tiny Swords, Pixel Frog), 34 PNGs, plus a working tile/sprite/animation configuration in `client/lib` (partly unwired, see #6).
- 40×30 maps generated from a seed with a balance check (298 of 300 seeds balanced).

**What it does not have, relative to `docs/roadmap/ROADMAP.md`:**
- No **agent interface**: agents are a hard-wired `Agent` class that receives the whole world objects; no spec loading beyond the parameter dict; no way to plug in a different agent type.
- No **arena, ratings, tournaments, or multi-match runner**; one global engine, one match at a time.
- No **snapshot/restore**: a deepcopy of the match state costs about **8.3 ms (about 22 ticks' worth)** at tick 300, so copy-based search would be slow without redesign.
- No **determinism contract**: global `random`, global id counter, unreset between matches (#8).
- **Resources are wood and stone; there is no gold.**
- No command/event layer: agents mutate world objects directly, so there are no events to compute rewards from.
- Pacing is wall-clock (10 ticks/s via `asyncio.sleep`) in the server path; the synchronous path exists but is not exposed as an API.

**Reuse candidates**: the sprites (licence known), the sprite/tile configuration modules, the renderer and replay controller idea, the map generator, the fog model, the parameter-driven bot as the first agent type, the 456-test suite as a behavioural reference.

**Not known**: parallel throughput; how the client behaves in a real browser (Playwright e2e was not run; the page was not opened); the licence of any `client/assets` PNG not covered by `CREDITS.md`; whether the owner intends to continue this project.
