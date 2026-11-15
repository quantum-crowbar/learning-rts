# Documentation Audit: ejaj-boj

**Analysis date**: 2026-11-15 · **Commit**: `fde9d3c` · Method: claims extracted from `CONTEXT.md` (CTX), `AGENTS.md` (AGT) and code docstrings (DOC), each checked against the code or by running it. *ran* = executed; *graph* = code graph; *read* = source reading; *U* = unverifiable here.

## Executive summary

ejaj-boj's docs get the big picture right and are wrong in the details: the **API, constants, structure and test counts are accurate** and the project documents its own invariants and known failures, but **counts and defaults drifted** (parameters, file sizes), the **architecture tree in `AGENTS.md` predates the move to `server/core/`**, comments went stale when the map shrank from 80×60 to 40×30, and **two fog invariants are only partly honoured by the code**. Overall accuracy is 54% on the claims checked, similar to deep-rts's 50% but not directly comparable (different claim selection); the difference that matters is that the code **runs, passes its tests, and its core documents describe it correctly in outline**, whereas deep-rts's usage docs described something that did not work.

| Verdict | Count |
|---------|-------|
| Correct | 15 |
| Partly correct | 7 |
| Incorrect | 12 |
| Unverifiable here | 2 |
| **Total** | **36** |

Accuracy = (correct + 0.5 × partly correct) / verifiable claims = (15 + 3.5) / 34 = **54%**. The Verdict column below is the authority for the counts. The weak spots are docstrings and numbers that changed later; the documents a newcomer reads first (`CONTEXT.md` summary, API table, constants, test counts) are mostly right.

## Claim ledger

| # | Source | Claim | Verdict | Evidence |
|---|--------|-------|---------|----------|
| 1 | CTX | 456 server tests pass (1 skipped) | Correct | *ran*: `456 passed, 1 skipped` (with current, unpinned dependencies) |
| 2 | CTX | "All server tests (451 pass, 1 skipped)" (Running Tests) | Incorrect | contradicts claim 1 in the same file; *ran*: 456 |
| 3 | CTX | 48 FE static tests pass (1 skipped) | Correct | *ran*: `48 passed, 1 skipped` |
| 4 | CTX | 142 client pure-JS tests pass (1 pre-existing fail) | Correct | *ran*: `142 passed, 1 failed` |
| 5 | CTX | `tests/fe/test-pure.mjs` has 55 failures | Correct | *ran*: `Failed: 55` |
| 6 | CTX | `spritePathForTile("UNKNOWN_TYPE")` returns `"undefined"` (known failure) | Correct | the failing test's message matches |
| 7 | CTX | `DEFAULT_PARAMS` has 13 keys (Key Components table) | Incorrect | *ran*: 18 |
| 8 | CTX | `DEFAULT_PARAMS` has 17 keys (AI Parameters section) | Incorrect | 18; the listing omits `unit_spawn_behavior` |
| 9 | CTX | `defend_percent` 0.3, `defend_radius` 8 | Incorrect | `constants.py`: 0.5 and 12 |
| 10 | CTX | `client/index.html` is "~1412 lines" | Incorrect | 1,894 lines |
| 11 | CTX | 40×30 map, 10 ticks/s, spawns (6,6) and (33,23), starting wood 200 / stone 100, town hall HP 1000 | Correct | `constants.py` |
| 12 | CTX | API surface: `GET /`, `/health`, `POST /start` (409 if running), `/reset`, `GET /replay` (404 if none), `WS /ws?player=0\|1\|spectator` | Correct | *graph*: `routes` table matches |
| 13 | CTX | "Fog at the wire: server filters entities to FOG_VISIBLE before serializing" | Partly correct | units yes; enemy buildings are also sent when only `FOG_EXPLORED`, with live HP/queue; map resources and `agent_goals` are unfiltered ([02](02-interface-specification.md)) |
| 14 | CTX | "Full grid on first WebSocket message, delta thereafter" | Partly correct | true for the first connection only; a later connection for the same player gets a delta with no baseline (*ran*) |
| 15 | CTX | `FogOfWar.to_wire()` called once per player per broadcast | Partly correct | true in `_broadcast`; `ws_endpoint` also calls it on connect |
| 16 | CTX/AGT | single match; `/start` returns 409 if running | Correct | `main.py:107`; tests |
| 17 | CTX/AGT | asyncio loop, `await asyncio.sleep`, never `time.sleep` | Correct | *grep*: no `time.sleep` in `server/` |
| 18 | CTX | `GameEngine.serialize()` does not call `to_wire()` | Correct | `game_engine.py:193-254` |
| 19 | CTX | `kind` class attribute on all entity subclasses | Correct | `entities.py` |
| 20 | CTX | `Player(player_id, spawn_x, spawn_y)`, no `params` kwarg | Correct | `player.py:11` |
| 21 | CTX | "Zero-dependency client: works opened directly from filesystem during dev" | Unverifiable here | not tested in a browser. The client uses ES module imports and relative `fetch('/start')`, which browsers generally block or cannot resolve under `file://`; probably false |
| 22 | CTX | Deployment: Railway "(recommended)" | Unverifiable here | no Railway configuration in the repo (only a Dockerfile) |
| 23 | CTX | Key Components list `anim.mjs`, `anim-config.mjs`, `fx.mjs`, `camera-helpers.mjs` as client libraries | Partly correct | the files exist, but **`index.html` imports none of them** (it imports `fog`, `camera`, `tile-coords`, `presets`, `sprites`, `trees`); their functions are dead in the page (*graph*, *grep*). `AGENTS.md`/`CONTEXT.md` state the rule that unwired libraries are unreachable; these are |
| 24 | CTX | "Phase 15: replay recording + viewer" | Partly correct | exists; frames carry no seed/params, only the last 3,600 ticks, deleted on reset (not mentioned) |
| 25 | AGT | tree: `server/game_engine.py # Game loop` | Incorrect | the loop is in `server/core/game_engine.py`; the top-level file is an unused shim |
| 26 | AGT | tree: `server/fog_of_war.py` | Incorrect | it is `server/core/fog.py` |
| 27 | AGT | tree omits `server/core/pathfinding.py` | Partly correct | file exists (Phase 13), not in the tree |
| 28 | AGT | "Single-file vanilla JS frontend" / `client/index.html # Single-file client` | Partly correct | `index.html` plus 10 library modules (1,203 non-test lines), four of them unused |
| 29 | AGT | no pygame imports; entities have `to_dict()` with coordinates rounded to 2 dp | Correct | *grep*, `entities.py` |
| 30 | DOC | `agent.py`: "Holds a player reference and 13-param dict" | Incorrect | holds `player_id`, and there are 18 params |
| 31 | DOC | `build_planner.py`: constructed "with a params dict and a reference to the owning Player" | Incorrect | `BuildPlanner(params)` only |
| 32 | DOC | `game_map.py`: 80×60 map, spawns (6,6) and (73,53), "40 clusters" of forest | Incorrect | map is 40×30, spawn (33,23); the formula gives 1200 // 120 = **10** forest and 6 quarry clusters |
| 33 | DOC | `fog.py`: `reset_wire_state` "called when a new match starts or POST /reset fires" | Incorrect | never called (*graph*); fresh `FogOfWar` objects make it unnecessary |
| 34 | DOC | `game_engine.py` header: `agent_goals` broadcast unfiltered to all connections | Correct | `serialize` |
| 35 | DOC | `main.py`: agent params are merged with `DEFAULT_PARAMS` by `Agent.__init__` | Correct | `agent.py:232` |
| 36 | DOC | `economy`/`agent` docs: workers return at `return_threshold` ("carry amount before returning to base") | Incorrect | the parameter is read nowhere (*grep*, [02](02-interface-specification.md)) |

## Not audited claim by claim

`specs/` (20 phase/spec files), `crew/` (AI-crew sessions and logs), `roadmaps/master-roadmap.md` and `core-architecture/` were read for context but not verified line by line. The roadmap says phases 8-11 are "future" while `CONTEXT.md` lists phases 11-15 as merged, so the roadmap is at least partly stale; `specs/phase16.md` (animations) is unimplemented, consistent with claim 23.

## Discrepancies worth fixing first

1. **DISC-001 Fog baseline** (claim 14): serve a full grid to every new connection (or reset `_prev_grid` per connection). Server-side fix is small; client already handles `full`.
2. **DISC-002 Unwired client libraries** (claim 23): either import `anim`, `fx`, `camera-helpers` into `index.html` or delete them; the animation work in `specs/phase16.md` is probably what they were meant for.
3. **DISC-003 Parameter docs** (claims 7-9, 30, 36): one source of truth for the parameter list (the constants file) and remove or implement `return_threshold`.
4. **DISC-004 Architecture tree** (claims 25-27): update `AGENTS.md`.
5. **DISC-005 Stale comments** (claims 32, 33): map size and `reset_wire_state`.
