# Findings Summary

**Project**: deep-rts (old engine, pinned `6bfbfd5` + `patches/deep-rts/`)
**Generated**: 2026-11-14
**Active Views**: 01 technology, 02 interfaces, 03 diagrams, 04 documentation audit, 05 dependency health, 06 data flow, 07 error handling, 09 code graph (SQLite)
**SQLite Cookbook:** [reports/sqlite-cookbook.md](sqlite-cookbook.md)

How to read the "verified" column: **ran** = reproduced by executing code; **graph** = from the code-graph database; **read** = from source reading only (C++ semantics, not executed); **fetched** = from an external API.

---

## Priority Action List

| # | Priority | Category | Finding | Verified | View | Location |
|---|----------|----------|---------|----------|------|----------|
| 1 | P0 | Build | The project does not build: configure fails at `find_package(xtensor)`; `setup.py` path clones unpinned vcpkg master and needs root for `apt-get` | ran (`build.log`) | [05](../analysis/05-dependency-health.md), [01](../analysis/01-technology-manifest.md) | `vcpkg_install.sh`, `CMakeLists.txt:139-144` |
| 2 | P0 | Correctness | `import DeepRTS.python` fails (`ImportError`); `DeepRTSPlayer`, `RectangleManager`, `util` are never defined; `LimitedDiscrete` is used but undefined. 11 of 28 internal imports broken | ran (stubbed import), graph | [04](../analysis/04-documentation-audit.md) DISC-001 | `game.py:4,72`, `gui.py:3,5` |
| 3 | P0 | Security | Discord webhook URL with token committed since 2017-04-06 | read, `git log -S` | [05](../analysis/05-dependency-health.md) | `.travis.yml:28` |
| 4 | P1 | RL contract | `Scenario::reward` is a boolean AND (`all_of`), so rewards are 0/1 and negative rewards count as 1 | read | [04](../analysis/04-documentation-audit.md) DISC-012 | `Scenario.cpp:44-46` |
| 5 | P1 | RL contract | Observation channels 5 (health), 6 (unit state), 7 (carry) are only written on `setPosition`: stale while a unit fights or harvests in place | read (exhaustive writer grep) | DISC-013 | `Unit.cpp:95-96, 595-607` |
| 6 | P1 | RL contract | `isTerminal()` calls `_onEpisodeEnd()` on every non-terminal check, and is never true if two players are defeated at once | read | DISC-011 | `Game.cpp:182-187` |
| 7 | P1 | RL / perf | Stepping is gated by the wall clock and the default is 60 steps/s; "6,000,000 steps/s" is unmeasured and only possible with `set_max_fps(0)` | read | DISC-007 | `Game.cpp:45,61-64,112` |
| 8 | P1 | Correctness | `insert_player` copies a `std::vector<Player>` element: Python subclass overrides are sliced away; `selectedPlayer` aliases the caller's object | read | DISC-014 | `Game.h:82`, `Game.cpp:208-216` |
| 9 | P1 | Documentation | Documented action IDs (0-15) and tensor channels are wrong; the example passes an invalid action ~1 in 15 | ran/read | DISC-002, 003 | AGENTS.md, QUICKSTART |
| 10 | P2 | Architecture | Ten classes (`Game, Player, Unit, Tile, Tilemap, Pathfinder, StateManager, State*, UnitManager, Blend2DGUI`) form one strongly connected component; `Unit`↔`State*` 54/50 calls | graph | [03](../analysis/03-architecture-diagrams.md) §2 | `src/` |
| 11 | P2 | Memory safety | Pointers into `std::vector<Unit>` are stored (`unitsNameMap`, tile occupants); capacity 8,000 is reserved but never enforced; dead units are never erased | read | [06](../analysis/06-data-flow-map.md), [07](../analysis/07-error-handling.md) E2 | `Game.cpp:42-43`, `Player.cpp:261-264` |
| 12 | P2 | Correctness | `spawn_unit` spawns a *copy* of the unit (`auto unit = addUnit(...)`); `getScore` trampoline truncates to `int` | read | DISC-015, 016 | `Player.cpp:125`, `PyPlayer.h:20` |
| 13 | P2 | Robustness | UB/crash paths: `players.back()` on empty vector; `ticks / tickModifier` with 0; uninitialised `GoldCollect::isValid`; asserts compile out in Release | read | [07](../analysis/07-error-handling.md) E1, E3, E5, E6 | see E-table |
| 14 | P2 | Dependencies | Our patch uses `xtensor/containers/` (≥0.26) but the pinned baseline has 0.24.3; two dependency-resolution paths disagree; `xtensor-python` on `master` | fetched/read | [05](../analysis/05-dependency-health.md) | `Game.h:19`, `CMakeLists.txt:107-117,152-156` |
| 15 | P2 | Tooling | CI workflow, Dockerfile, Travis config are stale/broken | read | DISC-018 | `.github/`, `Dockerfile`, `.travis.yml` |
| 16 | P2 | Docs/Examples | 4 of 6 example directories import modules that do not exist; `LavaMaze` is documented for Python but unbound; `PyGUI` advertised but unimplemented; `main.cpp` likely throws on its first frame (`imshow` of an empty `Mat`) | ran (imports), read | DISC-010, 019, 020 | `examples/`, `Game.cpp:53`, `main.cpp` |
| 17 | P3 | Maintenance | Upstream dormant since 2023-05-16; dependencies 1-7 minor versions behind; `gym`/`tensorflow-gpu` unmaintained | fetched | [05](../analysis/05-dependency-health.md) | n/a |

---

## Per-View Summary

### 01 Technology Manifest
| Status | Key Findings |
|--------|-------------|
| ✅ | C++17 engine (~8,970 own lines) + pybind11 + small Python layer; no runtime services or persistence; build has two disagreeing dependency paths. |

### 02 Interface Specification
| Status | Key Findings |
|--------|-------------|
| ✅ | 222 pybind registrations, 28 classes; 1-indexed 16-action space; real tensor channels documented; callback table shows 4 hooks C++ expects that Python never defines. |

### 03 Architecture Diagrams
| Status | Key Findings |
|--------|-------------|
| ✅ | `Scenario` is-a `Game`; states are shared flyweights; class-level monolith; no function-level cycles. |

### 04 Documentation Audit
| Status | Key Findings |
|--------|-------------|
| ⚠️ Issues Found | 50% claim accuracy (13 correct / 6 partly / 13 incorrect / 2 unverifiable); structure well documented, usage wrongly. 21 discrepancies. |

### 05 Dependency Health
| Status | Key Findings |
|--------|-------------|
| ⚠️ Issues Found | Unreproducible build; leaked webhook; C++ vulnerabilities not assessed (no scanner). |

### 06 Data Flow
| Status | Key Findings |
|--------|-------------|
| ✅ | No persistence; all state in one `Game`; observation updated incrementally and incompletely. |

### 07 Error Handling
| Status | Key Findings |
|--------|-------------|
| ⚠️ Issues Found | No strategy; 19 throws, 11 active asserts, 3 log calls; 11 gaps incl. UB paths. |

### 09 Code Graph
| Status | Key Findings |
|--------|-------------|
| ✅ with named gaps | 502 nodes, 732 edges, 0 cycles; C++ project-internal resolution 97.4%, Python 37.0%; pyan3 cross-check disagrees on 53% of its edges. |

---

## Metrics Dashboard

| Metric | Value | Status |
|--------|-------|--------|
| Dead code candidates | 100 (19.9%); mostly public API and example code, see caveats in [dead-code.md](dead-code.md) | 🔴 by template threshold (>50), 🟡 in context |
| Complexity hotspots (cc > 10) | 11 | 🔴 (>10) |
| Circular dependencies (function level) | 0 | 🟢 |
| Circular dependencies (class level) | 1 component of 10 classes | 🔴 |
| Outdated dependencies | 9 of 9 checked are behind | 🟡 |
| Vulnerable dependencies | not assessed (C++), 0 for `pygame==2.0.0` | ⚪ |
| Documentation accuracy | 50% | 🔴 |
| Builds | no | 🔴 |

---

## Facts relevant to "fix deep-rts vs. build learning-rts"

Inputs only; the decision is a separate discussion.

**What a fix would consist of** (all items confirmed above):
1. A reproducible build: one dependency path with a baseline providing xtensor ≥ 0.26, no root requirement, `xtensor-python` pinned. Feasible; unknown number of follow-on compile errors after xtensor (the build has never got past configure here).
2. Repair or delete the Python wrapper (≥ 4 missing symbols; stale `Config.Map`; 3 broken example groups).
3. Fix six RL-contract defects (#4-#8, #12) that silently corrupt rewards, observations and episode boundaries.
4. Decouple stepping from the wall clock if deterministic, high-throughput RL is the goal.

**What is structurally hard to fix in place:** the class-level monolith (#10) and the fact that observation writes live inside entity methods (#5): any change to what the agent observes touches `Unit`, `Tile` and the states.

**What is reusable regardless:** the 10 maps and 27 sprites (4.8 MB of assets), the Tiled-JSON + `tile_properties.json` content pipeline, the state-flyweight idea, JPS pathfinding use, the scenario/criteria concept, the pybind trampoline pattern. The graph database (`code/deep-rts/code_graph.sqlite`) is queryable for any of these.

**Not known:** actual throughput (no build), C++ dependency vulnerabilities, and whether the engine plays a sensible game (never run in this analysis).
