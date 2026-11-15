# Dead Code Candidates

**Project**: ejaj-boj (pinned `fde9d3c`)  
**Generated**: 2026-11-15  
**Candidates**: 29 (10.7%)

> A candidate has `fan_in = 0` in the **production** graph and is not an entry point. The graph excludes tests, so the **Test refs** column counts word-boundary matches of the function name in `tests/` and `client/lib/test-pure.mjs`: a function used only by tests is not dead for the project's own test suite but is dead for the running game. Reflection, string dispatch and calls through untyped receivers are invisible to the graph (see the excluded list below).

| Language | Function | Location | CC | Test refs | Assessment |
|---|---|---|---|---|---|
| javascript | `getAnimState` | `client/lib/anim-config.mjs:70` | 3 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `getFrame` | `client/lib/anim.mjs:78` | 3 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `attachZoomButton` | `client/lib/camera-helpers.mjs:87` | 2 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `clampZoom` | `client/lib/camera-helpers.mjs:39` | 2 | 16 | Used only by tests: dead in the game, alive in the suite |
| javascript | `onGameStart` | `client/lib/camera-helpers.mjs:140` | 2 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `screenToWorld` | `client/lib/camera.mjs:10` | 1 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `initFogGrid` | `client/lib/fog.mjs:7` | 1 | 17 | Used only by tests: dead in the game, alive in the suite |
| javascript | `_getParticleCount` | `client/lib/fx.mjs:143` | 1 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `_getParticles` | `client/lib/fx.mjs:151` | 1 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `_resetParticles` | `client/lib/fx.mjs:158` | 1 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `renderFX` | `client/lib/fx.mjs:110` | 4 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `spawnParticles` | `client/lib/fx.mjs:64` | 6 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `updateParticles` | `client/lib/fx.mjs:94` | 1 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `isValidPreset` | `client/lib/presets.mjs:128` | 1 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `listPresets` | `client/lib/presets.mjs:132` | 1 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `_resetForTesting` | `client/lib/sprites.mjs:254` | 1 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `computeDrawPosition` | `client/lib/sprites.mjs:146` | 1 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| javascript | `calcTickInterval` | `client/lib/trees.mjs:175` | 3 | 15 | Used only by tests: dead in the game, alive in the suite |
| python | `asset_url_path` | `scripts/setup_assets.py:85` | 1 | 4 | Used only by tests: dead in the game, alive in the suite |
| python | `Archer.try_attack` | `server/core/entities.py:253` | 3 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| python | `Knight.try_attack` | `server/core/entities.py:221` | 3 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| python | `Worker.is_full` | `server/core/entities.py:196` | 1 | 12 | Used only by tests: dead in the game, alive in the suite |
| python | `FogOfWar.reset_wire_state` | `server/core/fog.py:118` | 1 | 5 | Used only by tests: dead in the game, alive in the suite |
| python | `GameEngine.__init__` | `server/game_engine.py:31` | 1 | n/a | Dead import shim: nothing imports it. Its fallback stub class has a different API (`start(agent0, agent1)` without a seed). If the real import ever failed it would silently serve the stub |
| python | `GameEngine.apply_action` | `server/game_engine.py:46` | 1 | n/a | Dead import shim: nothing imports it. Its fallback stub class has a different API (`start(agent0, agent1)` without a seed). If the real import ever failed it would silently serve the stub |
| python | `GameEngine.get_state` | `server/game_engine.py:43` | 1 | n/a | Dead import shim: nothing imports it. Its fallback stub class has a different API (`start(agent0, agent1)` without a seed). If the real import ever failed it would silently serve the stub |
| python | `GameEngine.start` | `server/game_engine.py:34` | 1 | n/a | Dead import shim: nothing imports it. Its fallback stub class has a different API (`start(agent0, agent1)` without a seed). If the real import ever failed it would silently serve the stub |
| python | `GameMap.get_spawn_positions` | `server/maps/game_map.py:239` | 1 | 0 | No reference anywhere in tests: remove, or wire up if intended |
| python | `GameMap.get_tile` | `server/maps/game_map.py:246` | 3 | 14 | Used only by tests: dead in the game, alive in the suite |

## Not counted as dead because the name appears at an unresolved call site

These methods have no resolved caller, but an unresolved call (receiver type unknown) uses the same method name, so they may be the target. Typical case: `to_dict` overrides, called as `u.to_dict()` over untyped lists.

- `Archer.to_dict` (`server/core/entities.py:264`)
- `Barracks.to_dict` (`server/core/entities.py:115`)
- `Knight.to_dict` (`server/core/entities.py:232`)
- `Scout.to_dict` (`server/core/entities.py:281`)
- `TownHall.to_dict` (`server/core/entities.py:87`)
- `Worker.to_dict` (`server/core/entities.py:199`)

## Findings from reading the candidates

- `Knight.try_attack` / `Archer.try_attack` (and `can_attack`) are unused by the game: `Agent._manage_combat` applies damage itself with `take_damage`, duplicating the cooldown logic. Two implementations of the attack rule exist; only the agent's one runs.
- `FogOfWar.reset_wire_state` is documented as "called when a new match starts or POST /reset fires"; nothing calls it. It is harmless only because `GameEngine.start` builds fresh `FogOfWar` objects.
- The `return_threshold` agent parameter is also **dead** in the sense that no server code reads it (see [02](../analysis/02-interface-specification.md)); this is a parameter, not a function, so it does not appear in the graph.

