# Interface Specification: ejaj-boj

**Analysis date**: 2026-11-15 · **Commit**: `fde9d3c` · Routes from the code graph (`routes` table, *graph*); payload keys and behaviour from source reading and executed runs (*ran*).

ejaj-boj has no library API for other programs: the interfaces are **an HTTP + WebSocket server consumed by its own browser client** and **the agent parameter dict**, which is the game's main user-facing contract.

## 1. HTTP and WebSocket API (`server/main.py`)

| Method | Path | Handler | Behaviour |
|--------|------|---------|-----------|
| GET | `/` | `index` | serves `client/index.html` |
| GET | `/health` | `health` | `{"status":"ok","state":<waiting|running|finished>,"tick":N}` |
| POST | `/start` | `start` | body optional: `{"seed":int?, "agent0":{...}?, "agent1":{...}?}`; **409** if a match is running; otherwise picks a random seed if none given, starts, returns `{"status":"started","state","seed"}` |
| POST | `/reset` | `reset` | stops the match, clears state **and the replay**, returns `{"status":"ok","state":"waiting"}` |
| GET | `/replay` | `get_replay` | `{"frames":[...],"tick_step":5}`; **404** if no frames |
| WS | `/ws?player=0\|1\|spectator` | `ws_endpoint` | see section 2 |
| static | `/lib`, `/assets` | `StaticFiles` | client modules and sprites |

Notes:
- **No authentication.** `CORSMiddleware` allows every origin, method and header, so any web page can `POST /start` or `POST /reset` against a reachable instance.
- **No input validation beyond "is a dict"**: `StartRequest.agent0/agent1` are `dict[str, Any]`; unknown keys are accepted, wrong types crash the match later (see [07](07-error-handling.md), *ran*).
- Any value of `?player` other than `"0"` or `"1"` silently becomes a spectator.
- There is **one global engine**: a second client cannot run a separate match.

## 2. WebSocket protocol

**Client → server**: nothing is used. The handler loops on `receive_text()` and discards every message (`_ = data`). There are no control messages (no pause, speed, or commands); speed is applied by the client by dropping frames (`_SPEED_BASE_MS / _speedMult`, `client/index.html`).

**Server → client**: one JSON text frame per tick, plus one on connect. `GameEngine.serialize(player_id)`:

| Key | Content | Notes |
|-----|---------|-------|
| `state` | `"waiting"`, `"running"`, `"finished"` | when `waiting`, the payload is only `{"state","tick":0}` |
| `tick`, `winner` | int, int or null | |
| `map` | `{width,height,tiles:[[{type,resource,passable}]]}` | **included in every frame**, 97% of the bytes (*ran*, below) |
| `players` | spectator: both players in full (`id,wood,stone,buildings[],units[]`). Player view: own player in full; the enemy as `{id, units, buildings}` filtered by fog | see "Fog contract" |
| `agent_goals` | `[{player_id, goal, resource_priority}]` | sent **unfiltered to everyone**, deliberately (ADR-003) |
| `fog` | player views only: first message of a baseline `{"full": grid}`, later `{"delta": [{x,y,v}]}` | `v`: 0 unexplored, 1 explored, 2 visible |

Measured (*ran*, tick 200 of a default match): spectator frame 57,399 bytes, of which the map is 55,739 (97%); player-view frame 57,183 bytes. At 10 ticks/s that is **about 574 KB/s per connected client**. The recorded replay stores the same full frames.

### Fog contract: what the docs say vs what is sent

| Statement | Reality |
|-----------|---------|
| "Fog is server-side only. Never send enemy entities unless they are in `FOG_VISIBLE` tiles" (`AGENTS.md`) | Enemy **units** are filtered to `FOG_VISIBLE`. Enemy **buildings** are sent if their tile is `FOG_VISIBLE` **or `FOG_EXPLORED`**, with their *live* `hp` and `train_queue` (`game_engine.py:229-236`). The map's per-tile `resource` amounts (which fall as the enemy harvests) are sent for **all** tiles. `agent_goals` shows the enemy's current goal. |
| "Full grid on first WebSocket message, delta thereafter" | True only for the first connection after a match starts. **Any later connection for the same player gets a delta with no baseline** (*ran*: after a first `to_wire()`, a second returns `delta`). The client then logs "fog.delta received but fogGrid null" and, because no `full` is ever resent, renders **no fog for the rest of the match**. The client auto-reconnects 2 s after any disconnect, so a page refresh or a second tab triggers this (client side *read*; server side *ran*). |
| "`to_wire()` is called once per player per broadcast" | True in `_broadcast`; `ws_endpoint` also calls it on connect, advancing the baseline for the others. |

For an AI-vs-AI spectator game none of this changes the outcome; it matters for the stated invariant and for the planned PvP phase.

## 3. The agent parameter dict (the game's main contract)

`DEFAULT_PARAMS` has **18 keys** (*ran*). Columns "Server refs" count places in `server/` other than `constants.py` that read the key (*grep*).

| Key | Default | Used by | Server refs | Meaning |
|-----|---------|---------|-------------|---------|
| `worker_ratio` | 0.4 | `_manage_economy` | 1 | target workers / total population |
| `max_workers` | 6 | same | 1 | cap |
| `prefer_wood` | true | planner, `resource_priority` | 2 | gather wood first |
| `barracks_wood_threshold` / `barracks_stone_threshold` | 200 / 100 | production, planner | 2 / 2 | build barracks at these stocks |
| `build_second_barracks` | false | production, planner | 2 | |
| `scout_early`, `scout_count` | true, 1 | production, planner | 3, 1 | train scouts before combat units |
| `knight_archer_ratio` | 0.5 | `_choose_unit_type` | 1 | 0 = all archers, 1 = all knights |
| `max_army_size`, `attack_threshold` | 12, 4 | production, combat, planner | 3, 2 | |
| `retreat_hp_fraction` | 0.25 | scouting, combat | 2 | |
| **`return_threshold`** | 40 | **nothing** | **0** | documented as "carry amount before returning"; workers return at the fixed `CARRY_CAPACITY` (50) or when the tile is depleted. The UI slider and all four presets set it; it has **no effect** |
| `unit_spawn_behavior` | `"cluster"` | spawn, combat | 2 | `cluster` / `spread` / `rush` |
| `scout_who`, `scout_followup` | `"scout"`, `"peaceful"` | production, scouting | 2, 1 | who scouts; reaction on seeing enemies |
| `defend_percent`, `defend_radius` | 0.5, 12 | defence, combat | 1, 2 | `CONTEXT.md` documents 0.3 and 8 |

Parameters are merged over the defaults (`{**DEFAULT_PARAMS, **params}`) with **no validation**: unknown keys are kept silently; wrong types or values surface as exceptions inside the game loop (*ran*: `worker_ratio: "high"` leaves the engine permanently "running" with a dead loop).

Behavioural findings from running 20 seeded matches (*ran*): default vs default splits 10/10; a **rush** configuration (`unit_spawn_behavior:"rush"`, `attack_threshold:1`, all knights) as player 0 against the defaults wins only 2 of 20. The parameter space has structure, which is what a parameter-tuning game needs.

## 4. Internal contracts worth knowing

| Contract | Where | Note |
|----------|-------|------|
| `Agent.tick(player, enemy_player, game_map, fog)` | `server/ai/agent.py` | the agent receives the **whole enemy `Player` object**, not a filtered view; "fair play" depends on the agent code calling `fog.get_visible_entities` itself. Documented exception: the enemy town hall position is always known (spec gotcha 11) |
| Entity API | `server/core/entities.py` | classes with `kind` class attributes and `to_dict()`; ids come from a **process-global counter** |
| `GameEngine` | `server/core/game_engine.py` | `start`, `reset`, `_run_tick` (synchronous, used by tests), `serialize`, connection registry |
| `server/game_engine.py` | shim | re-exports `GameEngine`; unused (dead), with an incompatible fallback stub |

## 5. Formats

| Format | Where | Notes |
|--------|-------|-------|
| Replay | `GET /replay`, "Save" button in the client | `{frames:[full spectator frames]}`; **no seed, no agent params, no version**; at most the **last 720 frames, every 5th tick** (so at most 3,600 ticks), buffer ≤ about 41 MB JSON-equivalent |
| Sprites | `client/assets/` | spritesheets with fixed frame layouts (`scripts/setup_assets.py`: e.g. 192×576 for units); tile coordinates in `client/lib/tile-coords.mjs` |
| Presets | `client/lib/presets.mjs` | four named parameter sets |
