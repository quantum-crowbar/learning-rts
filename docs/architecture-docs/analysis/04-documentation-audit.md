# Documentation Audit: deep-rts

**Audit Date**: 2026-11-14 · **Auditor**: AI agent (arch-analysis skill) · **Scope**: the documentation shipped with the project plus the hand-written pre-toolbox docs now in `docs/legacy/deep-rts/` (AGENTS.md, QUICKSTART.md, README.md, `ai-context/*`, `architecture-docs/*`). Every claim below was tested against `code/deep-rts` at `6bfbfd5` by source reading, graph queries or running code.

## Executive Summary

**Overall accuracy: 50%** (formula: (correct + 0.5 × partly) ÷ (correct + partly + incorrect), over 32 checkable claims; 2 further claims cannot be verified because the project does not build). **Status: Needs Improvement, with two Critical items.**

| Verdict | Count |
|---|---|
| Correct | 13 |
| Partly correct | 6 |
| Incorrect | 13 |
| Unverifiable here | 2 |
| **Total claims checked** | **34** |

The documents are broadly right about *structure* (components, dependencies, file layout, enums) and wrong where they describe *how to use the project*: the Python wrapper, the action indexing, the observation tensor, installation. A reader following the README or AGENTS.md reaches an `ImportError` or a build failure. The hand-written audit that rated these docs "High accuracy / Current" (`architecture-docs/09-documentation-audit.md`) was a read-through that executed nothing and should not be relied on.

## Coverage Matrix

| Documentation Area | Exists | Accurate | Complete | Notes |
|---|---|---|---|---|
| README / Overview | Yes | Partial | Partial | claims unmeasured; wrapper example broken |
| Architecture | Yes (legacy, hand-written) | Mostly | Partial | structure right; coupling, flyweight states, hierarchy not described |
| API Reference | Yes (legacy) | Partial | Partial | native API names right; wrapper and tensor channels wrong |
| Setup / Installation | Yes | **No** | Partial | none of the documented install paths works |
| Configuration | Partial | Yes | Partial | `Config` options documented in QUICKSTART; defaults (`max_fps=60`, `tickModifier=10`, `terminalSignal=true`) are not |
| Development Guide | No | n/a | No | no contributor/test/debug docs; 1 test, which cannot pass |
| Deployment / CI | No | n/a | No | Dockerfile, Travis and Actions config are stale or broken (see DISC-018) |

## Claims Ledger

| # | Document | Claim | Verdict | Evidence |
|---|---|---|---|---|
| 1 | AGENTS.md | 6,000,000+ steps/s without rendering; 2,000,000+ with | Unverifiable | no benchmark in repo; engine does not build here; default `max_fps=60` throttles stepping (`Game.cpp:45,112`) |
| 2 | AGENTS.md | Hybrid C++/Python via PyBind11 | Correct | `bindings/`, 222 `.def*` |
| 3 | AGENTS.md | Directory structure (`include/DeepRTS/{state,scenario,gui,unit,util}`, `src/`, `bindings/`) | Partly | correct, but omits `gamestate/`, `bindings/trampolines/`, `ResourceLoader` |
| 4 | AGENTS.md | Line counts: Game.cpp 334, Player.cpp 506, Unit.cpp 609, Game.h 229 | Correct | measured: 334 / 506 / 609 / 229 |
| 5 | AGENTS.md | State machine: BaseState + Idle, Walking, Harvesting, Building, Combat, Spawning, Dead | Partly | 8 states exist; `Despawned` is omitted and is a real state (`StateManager.cpp:15`) |
| 6 | AGENTS.md | `GoldCollectFifteen` - collect 1000 gold | **Incorrect** | `GoldCollect(10)` (`GoldCollectFifteen.cpp:14`) |
| 7 | AGENTS.md | Criteria: GoldCollect, DamageDone, DamageTaken, UnitsCreated, FoodConsumption, GameEnd | Correct | all exist among 14 criteria |
| 8 | AGENTS.md | Action space IDs 0-15; `random.randrange(15)` in the example | **Incorrect** | `ACTION_MIN=1, ACTION_MAX=16` (`Constants.h:18-19`); 0 raises RuntimeError (`Player.cpp:403`) |
| 9 | AGENTS.md | Resources: Gold, Lumber, Stone, Food | Correct | `Constants::Resource` |
| 10 | AGENTS.md | Unit types and roles table | Correct | `UnitManager.cpp:9-30` |
| 11 | AGENTS.md | Dependencies via vcpkg: PyBind11, xtensor+xsimd, OpenCV, Blend2D, spdlog, nlohmann_json | Partly | also `effolkronium-random` (omitted); our patch adds pybind11 |
| 12 | AGENTS.md | `pip3 install git+https://github.com/cair/DeepRTS.git` / `pip3 install .` | **Incorrect** | build fails at configure (`build.log`); repo moved to `pa-research/deep-rts` |
| 13 | AGENTS.md | Python usage: `from DeepRTS.python import Config, scenario; scenario.GeneralAI_1v1(...)` | **Incorrect** | `DeepRTS.python` cannot be imported; no `scenario` module; no `GeneralAI_1v1` |
| 14 | AGENTS.md | C++ usage example (LavaMaze, `setMaxFPS(0)`, loop with `render`) | Correct | mirrors `src/main.cpp` (which itself likely fails, see 02 §4) |
| 15 | AGENTS.md | C++17 required | Correct | `CMakeLists.txt:29-31` |
| 16 | AGENTS.md | Assets embedded via CMRC; no external files at runtime | Partly | embedded first, filesystem fallback exists (`ResourceLoader.cpp:47-85`) |
| 17 | AGENTS.md | Supports 2-8 players, maps 10x10 to 31x31 | Partly | size range right; shipped maps have 1, 2, 4 or 6 spawns, never 8; two are 1-player |
| 18 | AGENTS.md | JPS (Jump Point Search) for pathfinding | Correct | `Walking.cpp:102-111`; A* and helper searches also in `Pathfinder.cpp` |
| 19 | AGENTS.md | `gui.py`: GUI rendering (NumPy arrays) | **Incorrect** | `gui.py` is a pygame GUI (and not importable) |
| 20 | QUICKSTART.md | Native API names (`config.set_*` x14, `player.do_action`, `get_score`, `game.is_terminal`, ...) | Correct | all present in `bindings/Config.cpp`, `bindings/Player.cpp` |
| 21 | QUICKSTART.md | `Engine.scenario.GoldCollectFifteen()` / `GeneralAIOneVersusOne()` | Correct | bound (`Scenarios.cpp:70-90`) |
| 22 | QUICKSTART.md | `Engine.scenario.LavaMaze()` | **Incorrect** | not bound (0 rows in `pybind_bindings`) |
| 23 | QUICKSTART.md | Action table 1-16 with names | Correct | matches `Constants.h:97-116` |
| 24 | QUICKSTART.md | Build0 = Farm, Build1 = Barracks, Build2 = Town Hall | **Incorrect** | index into selected unit's inventory; Peasant: `[TownHall, Farm?, Barracks?]` |
| 25 | QUICKSTART.md | State tensor shape `(W, H, 10)` | Correct | `Game.cpp:15-19` |
| 26 | QUICKSTART.md | State tensor channel table (unit present, owner, resources remaining, walkable, harvestable, ...) | **Incorrect** | real channels in 02 §2; no resources/walkable/harvestable channels |
| 27 | QUICKSTART.md | Available maps table (5 maps) | Partly | all 5 exist; 10 ship |
| 28 | QUICKSTART.md | `game.set_max_fps(0)` = unlimited speed | Correct | `Game.cpp:61-64`; but the default of 60 is never mentioned |
| 29 | QUICKSTART.md | Install via `pip install -e .` | **Incorrect** | fails at configure |
| 30 | QUICKSTART.md | Headless training reaches 6,000,000+ steps/s | Unverifiable | not measurable (no build) |
| 31 | README.md | Python >= 3.9.1 | **Incorrect** | `pyproject.toml` says >=3.8; Travis tests 3.5-3.8 |
| 32 | README.md | Usage: `from DeepRTS.python import scenario` | **Incorrect** | no such name |
| 33 | architecture-docs/09-documentation-audit.md | CLAUDE.md accuracy rated High / Current | **Incorrect** | contains the wrong action IDs, wrong scenario goal, non-working Python example |
| 34 | architecture-docs/09-documentation-audit.md | Action 0 vs 1 indexing is Low severity | **Incorrect** | 0 raises RuntimeError; documented example passes 0 |

## Discrepancies

Impact: **Critical** = blocks use; **High** = silently wrong results or crashes in documented usage; **Medium** = misleading; **Low** = cosmetic. DISC-011..016 are **undocumented behaviours that contradict the code's own evident intent**: code defects found while verifying the docs, listed here because no document warns about them.

### DISC-001: Python wrapper cannot be imported

**Type**: Incorrect · **Impact**: Critical · **Location**: README:85-86; AGENTS.md "Python (Recommended)"; QUICKSTART "Gym-style"

**Documentation says**: `from DeepRTS.python import Config, scenario` and `python.Game(...)` work.

**Reality**: `import DeepRTS.python` raises `ImportError: cannot import name 'RectangleManager'` (`gui.py:3`). Also undefined: `DeepRTSPlayer` (`game.py:4`), `util` (`gui.py:5`), `LimitedDiscrete` used at `game.py:72` but never defined or imported. Reproduced by importing with stubs for only the native and third-party modules. 11 of 28 project-internal `DeepRTS` imports are broken.

**Recommendation**: Either delete the wrapper from the docs or restore the missing modules. Until then document the native `Engine` as the only supported Python surface.

### DISC-002: Action IDs documented 0-15, real 1-16

**Type**: Incorrect · **Impact**: High · **Location**: AGENTS.md Action Space table; example `random.randrange(15)`

**Documentation says**: IDs 0-15.

**Reality**: `ACTION_MIN=1`, `ACTION_MAX=16` (`Constants.h:18-19`); `do_action(0)` throws (`Player.cpp:403`). The documented example passes 0 about 1 call in 15.

**Recommendation**: Fix the table and example; point to `Constants.h`.

### DISC-003: Observation tensor channel table is wrong

**Type**: Incorrect · **Impact**: High · **Location**: QUICKSTART "Game State Tensor"

**Documentation says**: ch1 unit present, ch2 unit type, ch3 health, ch4 owner, ch5 resources remaining, ch6 walkable, ch7 harvestable.

**Reality**: ch1 player id, ch2 is-structure, ch3 is-unit, ch4 unit type, ch5 health fraction, ch6 unit state, ch7 carried resources, ch8 attack score, ch9 armor (`Unit.cpp:588-607`). No resources/walkable/harvestable channel. Player id 0 is indistinguishable from empty in ch1. See also DISC-013.

**Recommendation**: Replace the table with the one in [02](02-interface-specification.md#2-rl-contract-action-observation-reward-termination).

### DISC-004: `BuildN` meaning

**Type**: Incorrect · **Impact**: Medium · **Location**: QUICKSTART action table

**Documentation says**: Build0=Farm, Build1=Barracks, Build2=Town Hall.

**Reality**: Index into the selected unit's `buildInventory`; Peasant = `[TownHall, Farm?, Barracks?]`, shifting with config (`UnitManager.cpp:299-306`).

**Recommendation**: Document the inventory rule.

### DISC-005: `GoldCollectFifteen` goal

**Type**: Incorrect · **Impact**: Medium · **Location**: AGENTS.md Scenarios

**Documentation says**: Collect 1000 gold.

**Reality**: `GoldCollect(10)` (`GoldCollectFifteen.cpp:14`); the name says fifteen. `GoldCollect::isValid` is an uninitialised `bool` (`GoldCollect.h:11`).

**Recommendation**: Fix doc; decide whether the code or the name is wrong.

### DISC-006: Documented installation does not work

**Type**: Incorrect · **Impact**: Critical · **Location**: AGENTS.md, README, QUICKSTART

**Documentation says**: `pip3 install git+https://github.com/cair/DeepRTS.git`, `pip3 install .`, `pip install -e .`.

**Reality**: Configure fails: `Could not find xtensor` (`build.log`). `setup.py` runs `vcpkg_install.sh`, which clones vcpkg **master** and needs root for `apt-get` (permission error in `build.log`). In the recorded run vcpkg rejected the spec `xtensor[xsimd]@0.24.7`, so xtensor was never installed; the origin of the `@0.24.7` suffix is not in the current tree (the log predates later edits). The repository is now `pa-research/deep-rts`.

**Recommendation**: Mark the project as not installable until the build is fixed; document the fix path.

### DISC-007: Throughput claims unmeasured and conditional

**Type**: Unverifiable · **Impact**: Medium · **Location**: README:7, AGENTS.md, QUICKSTART "Headless"

**Documentation says**: 6,000,000+ steps/s.

**Reality**: No benchmark in the repo. By default the engine is wall-clock throttled to 60 steps/s (`Game.cpp:45,112`); the figure can only apply after `set_max_fps(0)`. `-Ofast -ffast-math` is used.

**Recommendation**: Add a benchmark script; state the throttle.

### DISC-008: Python version stated three ways

**Type**: Inconsistent · **Impact**: Low · **Location**: README:37; `pyproject.toml:4`; `.travis.yml:11-14`

**Documentation says**: ≥3.9.1 / ≥3.8 / tests 3.5-3.8.

**Reality**: Three different answers; Travis tests versions below the package's own minimum.

**Recommendation**: Pick one.

### DISC-009: Player-count claim

**Type**: Incorrect · **Impact**: Medium · **Location**: AGENTS.md "Supports 2-8 players"

**Documentation says**: 2-8.

**Reality**: Shipped maps have 1, 2, 4 or 6 spawn tiles (counted per map); `Tilemap.cpp:208` throws if there are not enough spawns; `MAX_PLAYERS=8` is only a reserve size.

**Recommendation**: State "1-6 with shipped maps".

### DISC-010: `LavaMaze` is not available from Python

**Type**: Incorrect · **Impact**: Medium · **Location**: QUICKSTART "Available Scenarios"

**Documentation says**: `Engine.scenario.LavaMaze()`.

**Reality**: Not bound (`Scenarios.cpp`); only usable from C++.

**Recommendation**: Bind it or remove it from the doc.

### DISC-011: `_onEpisodeEnd()` fires on every non-terminal check

**Type**: Undocumented defect · **Impact**: High · **Location**: n/a (hook documented as episode end)

**Documentation says**: `_on_episode_end` marks the end of an episode.

**Reality**: `Game::isTerminal` computes `terminal`, then calls `_onEpisodeEnd()` **unconditionally** before returning (`Game.cpp:182-187`): fires on every call while the game runs. Also `terminal` becomes true only when **exactly one** player is `Defeat`: if two players are defeated in the same tick (`c == 2`) the game never terminates.

**Recommendation**: Guard the callback with `if (terminal)`; use `c >= 1` or define the rule.

### DISC-012: Scenario reward is a boolean AND

**Type**: Undocumented defect · **Impact**: High · **Location**: n/a (`reward()` documented as scenario reward)

**Documentation says**: Sum or value of criteria rewards.

**Reality**: `Scenario::reward` returns `std::all_of(..., c->reward())`, i.e. 0 or 1; any non-zero criterion value, **including negative failure rewards**, counts as true (`Scenario.cpp:44-46`). Per-criterion `rewardSuccess/rewardFailure` therefore never reach the agent.

**Recommendation**: Sum the criteria.

### DISC-013: Observation channels 5-7 go stale

**Type**: Undocumented defect · **Impact**: High · **Location**: n/a

**Documentation says**: state tensor reflects the game each step.

**Reality**: Units write channels 1-9 only in `Unit::setPosition` → `setStateForTile` (`Unit.cpp:95-96, 595-607`); callers are `Walking::update`, `Spawning::update`, `Building::update`, `Unit::build`. Health (5), unit state (6) and carried resources (7) change in combat/harvesting without a move and are **not** refreshed; exhaustive grep shows no other writer. Not executed; by code reading.

**Recommendation**: Update channels from `afflictDamage`, state transitions and carry changes, or rebuild the tensor each step.

### DISC-014: `insert_player` slices and aliases

**Type**: Undocumented defect · **Impact**: High · **Location**: QUICKSTART/AGENTS describe Python-subclassed players

**Documentation says**: A Python `Player` subclass participates in the game.

**Reality**: `players` is `std::vector<Player>` by value (`Game.h:82`); `insertPlayer` copies the argument (`Game.cpp:208-216`), so a `PyPlayer` is **sliced** to a `Player`, losing the Python overrides of `evaluatePlayerState/getScore` (called on the stored copy in `isTerminal`). `setSelectedPlayer(player)` then points at the caller's object, not the stored copy. By C++ semantics; not executed.

**Recommendation**: Store `std::unique_ptr<Player>` / `std::deque`.

### DISC-015: Trampoline truncates the score

**Type**: Undocumented defect · **Impact**: Medium · **Location**: n/a

**Documentation says**: `get_score()` returns a float.

**Reality**: `Player::getScore` returns `double` (`Player.h:116`); the trampoline declares `PYBIND11_OVERRIDE(int, Player, getScore, )` (`PyPlayer.h:20`), so Python overrides are truncated to `int`.

**Recommendation**: Use `double`.

### DISC-016: `spawn_unit` spawns a copy

**Type**: Undocumented defect · **Impact**: Medium · **Location**: n/a

**Documentation says**: `player.spawn_unit(type)` spawns a unit.

**Reality**: `auto unit = addUnit(unitType);` copies the `Unit` (`Player.cpp:125`); `spawnUnit` then acts on the copy, so the unit stored in `game.units` is never spawned. Exposed as `spawn_unit` (`bindings/Player.cpp:50`). By C++ semantics; not executed.

**Recommendation**: `auto& unit`.

### DISC-017: Hand-written audit overstated accuracy

**Type**: Incorrect · **Impact**: Medium · **Location**: legacy `architecture-docs/09-documentation-audit.md`

**Documentation says**: Docs "High accuracy / Current"; indexing mismatch "Low severity".

**Reality**: See DISC-001, 002, 006: the audit read docs against docs and executed nothing.

**Recommendation**: Supersede with this audit (done).

### DISC-018: CI, Docker and Travis configuration are stale

**Type**: Incorrect · **Impact**: Medium · **Location**: `.github/workflows/test_vcpkg_install.yaml:23-24`; `Dockerfile:1,5,15`; `.travis.yml`

**Documentation says**: CI validates the install script; Docker image runs the demo.

**Reality**: Workflow runs `./vcpkg/vcpkg_install.sh` (path does not exist; script is at the repo root); Dockerfile uses EOL `ubuntu:18.04`, clones `UIA-CAIR/DeepRTS`, runs the non-existent `drts/coding/main.py`; Travis builds Python 3.5-3.7 (below `requires-python`) and embeds a webhook secret (see [05](05-dependency-health.md)).

**Recommendation**: Remove or repair; rotate the secret.

### DISC-019: `PyGUI` advertised but not implemented

**Type**: Incorrect · **Impact**: Low · **Location**: `Game.cpp:53` error text "Available: Blend2DGui, PyGUI"

**Documentation says**: `PyGUI` is selectable.

**Reality**: `PyGUI` has only a header (`include/DeepRTS/gui/PyGUI.h`); no `.cpp`; `_internalInit` handles only `"Blend2DGui"` and `""` (`Game.cpp:47-54`).

**Recommendation**: Fix the message or implement it.

### DISC-020: Examples reference missing modules

**Type**: Incorrect · **Impact**: Medium · **Location**: `examples/`

**Documentation says**: Five numbered examples.

**Reality**: Working: `example_01`, `example_02` (native only). Broken imports: `example_03` (`DeepRTS.python.scenario.engine`, `util`), `example_04`, `example_05` (`DeepRTS.contrib.agents`), `old/main.py` (`scenario`).

**Recommendation**: Delete or port.

### DISC-021: Python `Config.Map` points at non-existent files

**Type**: Incorrect · **Impact**: Medium · **Location**: `DeepRTS/python/config.py:17-24`

**Documentation says**: `Config.Map.FIFTEEN = "15x15-2v2.json"`, etc.

**Reality**: None of these seven names exist in `assets/maps/` (real names e.g. `15x15-2p-ffa-Cresal.json`).

**Recommendation**: Use `Engine.Constants.Map.*`.

## Missing Documentation

| Area | Priority | Impact | Recommendation |
|---|---|---|---|
| Defaults and timing model (60 fps throttle, `tickModifier=10`, wall-clock stepping) | High | anyone measuring throughput or training RL | document before benchmarking |
| Observation/reward semantics incl. known staleness and boolean reward | High | RL users | document or fix (DISC-012/013) |
| Which dependency path is canonical (PMM pin vs vcpkg master) | High | anyone building | single documented path |
| Callback (trampoline) contract and the names Python must implement | Medium | extension authors | table in [02](02-interface-specification.md#3-callback-interface-c--python) |
| Provenance of vendored code (`JPS.h`, `ndarray_converter`) | Low | licence review | header notes |
| Contributor/test guide | Medium | contributors | none exists |

## Recommendations

### Immediate

1. Replace the Python usage sections in README/AGENTS.md with the native `Engine` usage from `examples/example_01`.
2. Correct the action table (1-16), state-tensor table and `BuildN` rule using [02](02-interface-specification.md).
3. Add a banner that the project does not currently build.

### Short-term

1. Fix or delete the Python wrapper (DISC-001/021/020).
2. Rotate the leaked Travis webhook and remove it (DISC-018).
3. Add a benchmark and state the throttle (DISC-007).

### Long-term

1. Decide the project's direction (fix deep-rts vs. build learning-rts) before investing in docs for either.

## Appendix: Documentation Inventory

| File | Location now | Status |
|---|---|---|
| README.md | `docs/legacy/deep-rts/README.md` | Outdated (DISC-001, 006, 007, 008) |
| AGENTS.md / CLAUDE.md (project) | `docs/legacy/deep-rts/ai-context/deep-rts-AGENTS.md` | Partly incorrect (DISC-001, 002, 005, 009) |
| QUICKSTART.md | `docs/legacy/deep-rts/ai-context/quickstart.md` | Native sections mostly right; tensor/Build/install wrong |
| ai-context/{api-reference,architecture,building,maps-and-tiles,scenarios,state-machine}.md | `docs/legacy/deep-rts/ai-context/` | not individually audited line-by-line; claims about actions, the wrapper and scenario goals are inherited from AGENTS.md and share its errors |
| architecture-docs/01-09 | `docs/legacy/deep-rts/architecture-docs/` | superseded by this directory |

> Not audited line by line: `ai-context/{api-reference,architecture,building,maps-and-tiles,scenarios,state-machine}.md`. They were checked only where they repeat claims from the three audited documents.
