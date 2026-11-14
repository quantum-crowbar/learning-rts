# Error Handling: deep-rts

**Analysis Date**: 2026-11-14 · **Commit**: `6bfbfd5` · counts from grep over `src/ include/ bindings/ DeepRTS/python` excluding vendored files. *(not executed)* marks conclusions from code reading.

## Executive Summary

The engine has **no error-handling strategy**, only local reactions: 19 active `throw std::runtime_error` sites, 11 active `assert`s, 4 `catch` blocks (all in `ResourceLoader`), 3 `spdlog` calls and 12 ad-hoc `std::cout`/`std::cerr` prints. There are no error types, no codes, no log levels, no recovery beyond a filesystem fallback for assets, and several undefined-behaviour paths that no check guards.

| Mechanism | Count | Where |
|-----------|-------|-------|
| `throw std::runtime_error` | 19 (+2 commented out) | `ResourceLoader` ×4, `UnitManager` ×4, `Game` ×1, `Player` ×1, `Tilemap` ×1, `Unit` ×1, `StateManager` ×1, `Scenario` ×1, criteria ×2, `Blend2DGUI.h` ×3 |
| `try/catch` | 4 | all `ResourceLoader.cpp:61-133` (`nlohmann::json::exception`, `std::exception`) |
| `assert` (active) | 11 (+5 commented out) | `Player.cpp:49`, `Tilemap.cpp:130`, `Game.cpp:222`, `Walking.cpp:23`, `Unit.cpp:116,188,526,538,543`, `Pathfinder.cpp:128,147` |
| `SPDLOG_WARN` | 3 | `Game.cpp:193`, `Config.h:17,20` |
| `std::cout`/`cerr` diagnostics | 12 | `Map.cpp:38-43`, `Player.cpp:120`, `Game.cpp:144`, the unused `DEBUG(x)` macro (`Constants.h:11`) |
| Python `except` | 2 (`gui.py:191` specific `KeyError`; `game.py:40` **bare `except:`**) | |

## Error Sources

| Source | Trigger | Reaction |
|--------|---------|----------|
| Bad action id | outside 1-16 | `RuntimeError("The action ... is out of bounds")` (`Player.cpp:403`) |
| Unknown GUI | `config.gui` not `""`/`"Blend2DGui"` | `runtime_error` (message wrongly lists `PyGUI`, DISC-019) (`Game.cpp:53`) |
| Map/asset missing or unparsable | bad file name, bad JSON | embedded load fails → filesystem fallback → `runtime_error("File Error: Could not find ...")` (`ResourceLoader.cpp:84`) |
| Too few spawn tiles | players > spawns when spawning | `runtime_error` (`Tilemap.cpp:208`); but `Game::addPlayer` instead **warns and returns the last player** (`Game.cpp:192-195`) |
| Unknown unit/state id | factory / `StateManager::getByID` default | `runtime_error("Should never happen")` / `"Incorrect id of State"` |
| Scenario misuse | unknown unit name in optimal strategy | `runtime_error` (`Scenario.cpp:69`) |
| Missing tile-property keys | malformed `tile_properties.json` | **stdout print, then continue** (`Map.cpp:38-43`) |

## Error Propagation

C++ `std::runtime_error` thrown inside the engine propagates to the pybind11 boundary and becomes a Python `RuntimeError` (pybind11's default translation). Nothing in the engine catches exceptions raised inside `update()`: a throw mid-tick leaves units, tensor and clocks partially updated (`Game::update` has no rollback) *(not executed)*. Python callbacks that raise propagate back through the trampoline into `Game::update`.

```mermaid
flowchart LR
    T["throw runtime_error (engine)"] --> B["pybind11 translation"]
    B --> P["Python RuntimeError"]
    P --> A["agent code"]
    R["ResourceLoader catch"] -. "only recovery: embedded to filesystem asset fallback" .-> T
```

## Error Response Formats

None: no structured errors, codes or machine-readable categories; only message strings. There is no error-code registry.

## Error Observability

| Aspect | State |
|--------|-------|
| Logging library | spdlog is a dependency but used at **3 sites**; no logger setup, no level control, no sinks |
| Console diagnostics | `std::cout` without prefix or level; `Game::caption` prints FPS only if `consoleCaptionEnabled` |
| `DEBUG(x)` macro | defined (`Constants.h:11`, writes to `std::cerr`); all uses are commented out |
| Metrics/tracing | none |
| Message quality | `Config::_boundLimits` warns "can not be below 10.0" for the lower bound (`Config.h:20`): the text is wrong |

## Recovery Mechanisms

| Mechanism | Where | Verdict |
|-----------|-------|---------|
| Embedded → filesystem asset fallback | `ResourceLoader.cpp:47-85` | works as designed, but the `catch (const std::exception&)` also swallows JSON errors from the embedded file and retries the filesystem silently |
| `addPlayer` returns last player when no spawn tile | `Game.cpp:192-195` | **undefined behaviour if `players` is empty** (`players.back()` on an empty vector) |
| `do_action` no-op when the player has no units | `Player.cpp:408` | silent; the agent cannot tell a no-op from a successful action |
| `Python game.py` bare `except: pass` around `argparse` | `game.py:32-40` | hides every error, including `SystemExit` from unrelated `sys.argv` |

## Error Handling Gaps

| # | Gap | Evidence | Consequence |
|---|-----|----------|-------------|
| E1 | `players.back()` on empty vector | `Game.cpp:194` | UB when a map has zero spawn tiles and no player yet |
| E2 | Unit capacity never checked; pointers into `vector<Unit>` stored | `Game.cpp:42-43`, `Player.cpp:261-264` | dangling `unitsNameMap` and tile-occupant pointers after > 8000 units |
| E3 | Division by zero | `Game::getGameDuration` divides by `tickModifier` (`Game.cpp:262`), and `setTickModifier` accepts 0 (`Config.h:88`) | `SIGFPE` (integer division) |
| E4 | `Game::isTerminal` fires `_onEpisodeEnd` every call; never terminal if two players are defeated at once | `Game.cpp:182-187` | wrong episode boundaries (DISC-011) |
| E5 | Uninitialised member | `GoldCollect::isValid` (`GoldCollect.h:11`) | `reward()` before `evaluate()` reads an indeterminate `bool` |
| E6 | `assert`s are the only guard for several invariants | list above; `Game::getUnit` bounds (`Game.cpp:222`); `Unit.cpp:188 assert(firstWalkable)` | CMake's default Release flags define `NDEBUG` (`CMAKE_BUILD_TYPE=Release` is what `setup.py` requests, see `build.log`), so these checks are compiled out. The nearest-walkable-tile search returns `nullptr` when nothing is found (`Pathfinder.cpp:145`; its `assert(false)` at `:147` is after the `return` and unreachable), so in Release a caller that dereferences the result does so unchecked *(not verified by building or running)* |
| E7 | Copy instead of reference | `auto unit = addUnit(...)` (`Player.cpp:125`), `players.push_back(player)` slicing (`Game.cpp:210`) | silent wrong behaviour, no error (DISC-014, 016) |
| E8 | Missing-key map errors only print | `Map.cpp:38-43` | a malformed tile file yields a half-initialised map with no exception |
| E9 | Config lacks validation | `Config.h` setters (only yield modifiers bounded) | invalid configs accepted silently (E3) |
| E10 | `-Ofast -ffast-math` | `CMakeLists.txt:55` | NaN/inf checks may be optimised out; error paths relying on them are unreliable |
| E11 | Callback truncation | `PyPlayer.h:20` | `getScore` overrides silently truncated to `int` (DISC-015) |

Not a gap (checked): the `throw` at the end of `Unit::setDirection` (`Unit.cpp:440`) is unreachable: the preceding `if/else` chain covers every integer combination of `(dx, dy)`.
