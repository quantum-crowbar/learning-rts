# Interface Specification: deep-rts

**Analysis Date**: 2026-11-14 · **Commit**: `6bfbfd5` · Generated from `code_graph.sqlite` tables `pybind_bindings`, `pybind_callbacks`, `class_hierarchy` plus source reads. Names are the **Python-visible** names.

> deep-rts has no network APIs. Its interfaces are: (1) the native Python module, (2) the C++ library API, (3) callbacks into Python, (4) file formats, (5) build entry points. Section 6 covers the Python wrapper, which is **not importable** (DISC-001).

## 1. Native Python module `libdeeprts` (`from DeepRTS import Engine`)

222 `.def*` registrations across 28 Python classes (`bindings/*.cpp`). `DeepRTS/__init__.py` re-exports `Engine, Map, UnitManager, Constants, Player` and falls back to a top-level `Engine` module if the package import fails.

| Class | Methods (`def`) | Fields (`def_readonly/readwrite`) | Source |
|-------|-----------------|-----------------------------------|--------|
| `Game` | 34 (`__init__`×2, `start`, `stop`, `reset`, `update`, `tick`, `render`, `caption`, `is_terminal`, `add_player`, `insert_player`, `set_max_fps`, `set_selected_player`, `get_*`×11, `_update`, `_render`, `_caption`, `_on_*`×7) | 7: `config, map, state, tilemap, units, _players, selected_player` | `bindings/Game.cpp` |
| `Player` | 14: `do_action`, `do_manual_action`, `add_unit`, `spawn_unit`, `left_click`, `get_score`, `evaluate_player_state`, `get_id/name`, `set_name/state`, `get/set_targeted_unit*` | 17: resources (`gold, lumber, stone, food, food_consumption`), `num_*` unit counts ×6, `statistic_*` ×6 | `bindings/Player.cpp` |
| `Unit` | 5: `spawn`, `right_click`, `get_player`, `get_next_tile`, `__init__` | 40: combat/economy stats, `state`, `tile`, `direction`, `walking_path` (rw), `animation_counter` (rw) | `bindings/Unit.cpp` |
| `Tile` | 12: `is_walkable/buildable/harvestable/attackable/depleted`, `get_occupant(_id)`, `has_occupant`, `get_resources`, `get_type_id`, `get_name` | 8: `x, y, id, width, height, gold/lumber/stone_yield` | `bindings/Tile.cpp` |
| `Tilemap` | 2: `get_tile` | 1: `tiles` | |
| `Map` | 1 | 4: `map_width/height`, `tile_width/height` | |
| `Config` | 19 setters + `defaults` (static) | 17 properties | `bindings/Config.cpp` |
| `Random` | `get` (static, **a lambda**: `Random.get(a, b)`) | | `bindings/Random.cpp:15` |
| `UnitManager` | `construct_unit` | | |
| `BaseState` | | 2 | |
| `scenario.Scenario`, `GoldCollectFifteen`, `GeneralAIOneVersusOne` | 7 each: `update, evaluate, reward, optimal_strategy, compute_optimal_strategy, optimal_play_game_step` | | `bindings/Scenarios.cpp:58-90` |
| `scenario.criteria.*`: 14 criteria + `ScenarioCriteria` base | 1 each (constructor) | | `bindings/Scenarios.cpp` |
| `LavaMaze` | **declared in C++, not bound** (not in `Scenarios.cpp` binding list; present only as C++ class and used by `main.cpp`) | | verified: `SELECT * FROM pybind_bindings WHERE py_class='LavaMaze'` → 0 rows |

Notes on behaviour that callers must know:

- `Game.update()` advances the simulation **only if wall-clock `now >= _update_next`** (`src/Game.cpp:112`). `_internalInit()` sets `setMaxFPS(60)` (`:45`), so a freshly created game steps at most 60 times per second. Call `set_max_fps(0)` for unthrottled stepping (interval becomes 0, `:61-64`).
- `Game.get_state()` does **not** exist natively; the observation is the read-only field `Game.state` (a numpy view of an `xt::xarray<double>`).
- `Player.do_action(a)` raises `RuntimeError` for `a` outside `[1,16]` (`src/Player.cpp:403`) and silently returns if the player has no units (`:408`).
- `Game.insert_player(p)` **copies** `p` into `std::vector<Player>` (`src/Game.cpp:208-216`); see DISC-014 (object slicing).

## 2. RL contract (action, observation, reward, termination)

### Action space: 16 discrete, **1-indexed** (`include/DeepRTS/Constants.h:97-116`)

| ID | Name | ID | Name |
|----|------|----|------|
| 1 | PreviousUnit | 9 | MoveDownLeft |
| 2 | NextUnit | 10 | MoveDownRight |
| 3 | MoveLeft | 11 | Attack |
| 4 | MoveRight | 12 | Harvest |
| 5 | MoveUp | 13 | Build0 |
| 6 | MoveDown | 14 | Build1 |
| 7 | MoveUpLeft | 15 | Build2 |
| 8 | MoveUpRight | 16 | NoAction |

`BuildN` is an **index into the selected unit's `buildInventory`**, not a fixed building (`src/Unit.cpp:135-141`, `src/UnitManager.cpp:299-306`):

| Selected unit | `buildInventory` |
|---------------|------------------|
| Peasant | `[TownHall, Farm if farmEnabled, Barracks if barracksEnabled]`: indices shift with config |
| Town hall | `[Peasant]` |
| Barracks | `[Footman if footmanEnabled, Archer if archerEnabled]` |
| others | `[]` |

Actions apply to the **currently targeted unit** of the player; `PreviousUnit/NextUnit` cycle it (`do_action`, `src/Player.cpp:400+`). A single agent therefore controls many units through one selector action.

### Observation: `Game.state`, shape `(W, H, 10)`, `float64`, initialised to `-1`

Channels, from `src/Unit.cpp:588-607` and `src/Tile.cpp:101,197,216`:

| Ch | Content | Written by |
|----|---------|-----------|
| 0 | tile type id (`TypeToID`: Spawn 1, Grass 2, Wall 3, Desert 4, Water 5, Lumber 6, Gold 7, Stone 8, Lava 9) | `Tile` |
| 1 | owning player id | `Unit::setStateForTile` |
| 2 | 1 if structure | |
| 3 | 1 if mobile unit | |
| 4 | unit type id | |
| 5 | health / max health (0-1) | |
| 6 | unit state id (`Constants::State`) | |
| 7 | total carried resources | |
| 8 | attack score (min+max+piercing damage) | |
| 9 | armor | |

Gotchas: `clearStateForTile` writes `0` to channels 1-9, and player ids start at **0**, so channel 1 cannot distinguish "player 0" from "empty": use channels 2/3. **Remaining tile resources are not observable.** Channels 1-9 are written **only** when a unit is positioned (`Unit::setPosition`, from `Walking`, `Spawning`, `Building`, `Unit::build`), so health (5), unit state (6) and carry (7) go stale while a unit fights or harvests in place (DISC-013; by exhaustive grep of writers, not executed).

### Reward and termination

- Base `Game` has **no reward**. Rewards exist only in `Scenario` subclasses.
- `Scenario.reward(player)` returns `std::all_of(criteria, c->reward())`: a **bool** (0 or 1), not the sum, and any non-zero criterion value (including a negative one) counts as true (`src/scenario/Scenario.cpp:44-46`). See DISC-012.
- `Game.is_terminal()` is true only when `config.terminalSignal` (default `true`, `Config.h:44`) **and exactly one** player is `Defeat` (`src/Game.cpp:164-188`). It also invokes `_onEpisodeEnd()` on every non-terminal evaluation (`:182-187`); DISC-011.
- `Scenario.update()` additionally ends the episode when all criteria are satisfied (`src/scenario/Scenario.cpp:115-123`).

## 3. Callback interface (C++ → Python)

`bindings/trampolines/*` define subclasses whose virtuals forward to Python with `PYBIND11_OVERLOAD`/`OVERRIDE` (16 sites). Non-`_PURE` forms fall back to the C++ base implementation when no Python override exists.

| C++ virtual | Python name looked up | Defined by Python wrapper `game.py`? |
|-------------|-----------------------|--------------------------------------|
| `Game::_update` | `_update` | no |
| `Game::_reset` | `_reset` | no |
| `Game::_render` / `_caption` | `_render`, `_caption` | yes |
| `Game::_onUnitCreate/Destroy` | `_on_unit_create`, `_on_unit_destroy` | yes |
| `Game::_onTileChange` | `_on_tile_change` | yes |
| `Game::_onEpisodeStart/End` | `_on_episode_start`, `_on_episode_end` | yes |
| `Game::_onResourceGather` | `_on_resource_gather` | **no**: wrapper defines `_on_tile_deplete` instead |
| `Game::_onResourceDepleted` | `_on_resource_depleted` | **no** (same) |
| `Player::evaluatePlayerState`, `getScore` | same | n/a (see DISC-014/015) |
| `ScenarioCriteria::clone/evaluate/reward` | `_PURE` | user-supplied |

## 4. C++ library API

- Public classes: `Game, Player, Unit, Tile, Tilemap, Map, Config, UnitManager, ResourceLoader`, state machine (`BaseState` + 8 states), scenarios and 15 criteria. Namespace `DeepRTS`, scenarios in `DeepRTS::Scenarios`, criteria in `DeepRTS::Criteria`.
- Extension points: subclass `Game`/`Scenario` and override the virtuals above; implement `ScenarioCriteria` (`clone`, `evaluate`, `reward`); add a `BaseState` subclass (but `StateManager::getByID` is a closed `switch`, `src/state/StateManager.cpp:25-42`, so new states need a core edit).
- Standalone executable `DeepRTSGame` (`src/main.cpp`): builds `LavaMaze` with `setGUI("")` (no GUI), runs up to 100,000 episodes of two players taking random actions, and calls `cv::imshow(g.render())` every step. With no GUI, `render()` returns the empty `renderPlaceholder` (`src/Game.cpp:324-329`), and `cv::imshow` on an empty `cv::Mat` throws in OpenCV (by library semantics; **not run**), so this demo likely fails on its first iteration. `main.cpp` itself does not use Python; the library is compiled with `EMBEDDED=1` and linked to `pybind11::embed` (`CMakeLists.txt:~258-263`).

## 5. File formats

| Format | Location | Spec |
|--------|----------|------|
| Map | `assets/maps/*.json` | Tiled (mapeditor.org) JSON: `width, height, tilewidth, tileheight, layers[0].data` (tile ids), `tilesets[]`. Loaded by `Map`/`ResourceLoader` (`src/Map.cpp:23-77`) |
| Tile properties | `assets/tile_properties.json` | `tile_types` (type → tile-id ranges, e.g. `"Wall": ["17-86", 87]`) and `tile_metadata` (walkable, harvestable, yields, `deplete_tile`, …). Missing keys only print to stdout (`src/Map.cpp:38-43`) |
| Spawn | tile id 16 | the tile type `Spawn`; number of spawn tiles bounds the player count (`src/Tilemap.cpp:208`) |
| Shipped maps | 10 files: 10x10, 15x15 (×2), 21x21 (×3), 30x30, 31x31 (×3: 2p, 4p, 6p) | listed in `Constants.h:118-131`; **no 8-player map exists** though `MAX_PLAYERS = 8` |

## 6. Python wrapper `DeepRTS.python` (`Game`, `GUI`, `Config`, `Tournament`, `BaseAgent`)

Intended as the Gym-style layer. **`import DeepRTS.python` fails** with `ImportError: cannot import name 'RectangleManager'` (`gui.py:3`), reproduced with stubs for the native and third-party modules. Also missing: `DeepRTSPlayer` (`game.py:4`), `util` (`gui.py:5`), and `LimitedDiscrete` is used but never defined or imported (`game.py:72`). `Config.Map.*` names (`config.py:17-24`) refer to files that do not exist (`"15x15-2v2.json"` etc.; real: `15x15-2p-ffa-Cresal.json`). Everything in this section should be treated as **non-functional**; the working Python surface is the native `Engine`.

## 7. Build/entry interfaces

| Entry | Command | Status |
|-------|---------|--------|
| pip | `pip install .` / `-e .` | fails at CMake configure (xtensor not found) |
| CMake (C++ only) | `cmake .. -DPYTHON_BUILD=OFF` (docs); actually "not defined" selects static lib + executable | unverified |
| Tests | `pytest --pyargs DeepRTS` → `DeepRTS/python/tests/test_deeprts.py` | 1 test, builds `python.Game(...)` → cannot pass (import error) |
