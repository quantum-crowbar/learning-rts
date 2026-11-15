# Architecture Diagrams: ejaj-boj

**Analysis date**: 2026-11-15 · **Commit**: `fde9d3c` · Mermaid. Structure from the code graph and source reading; claims marked *ran* were executed.

## 1. System overview

A single Python process holds one game; browsers watch it through a WebSocket and control it through three HTTP calls.

```mermaid
flowchart TB
    subgraph BROWSER["Browser: client/index.html + client/lib"]
        UI["Config UI, presets, HUD, minimap"]
        GC["GameClient: WebSocket, renderer, camera, fog overlay"]
        RC["ReplayController: fetch /replay, scrub, save JSON"]
    end
    subgraph SERVER["Python process: FastAPI + asyncio"]
        MAIN["main.py: routes, module-level engine"]
        ENG["GameEngine: state, tick loop, serialize, broadcast"]
        subgraph SIM["Simulation (synchronous, no I/O)"]
            AG["Agent x2 (parametric AI)"]
            BP["BuildPlanner"]
            EC["economy.assign_workers"]
            PL["Player: wood, stone, units, buildings"]
            ENT["Entities: TownHall, Barracks, Worker, Knight, Archer, Scout"]
            MAP["GameMap (seeded generation) + A* pathfinding"]
            FOG["FogOfWar x2"]
        end
    end
    UI -->|"POST /start, /reset"| MAIN
    GC <-->|"WS /ws: JSON frame per tick"| MAIN
    RC -->|"GET /replay"| MAIN
    MAIN --> ENG
    ENG --> AG
    AG --> BP
    AG --> EC
    AG --> PL
    PL --> ENT
    AG --> MAP
    AG --> FOG
    ENG -->|"serialize, to_wire"| GC
```

**Shape (graph, read).** Three layers: transport (`main.py`), orchestration (`GameEngine`), and a synchronous simulation (agents, entities, map, fog) that contains no `await` and no I/O. That separation is why 456 tests run in 3 seconds and why the whole match can be driven by `_run_tick()` without a server (*ran*: about 2,700 ticks/s on one core including both agents).

## 2. Code structure (class hierarchy)

```mermaid
classDiagram
    Entity <|-- Building
    Entity <|-- Unit
    Building <|-- TownHall
    Building <|-- Barracks
    Unit <|-- Worker
    Unit <|-- Knight
    Unit <|-- Archer
    Unit <|-- Scout
    class Entity {
      id
      tx
      ty
      hp
      alive
      take_damage()
      distance_to()
      to_dict()
    }
    class Unit {
      state
      path
      move_towards()
      step_path()
    }
    class Barracks {
      train_queue
      update()
    }
    class Agent {
      params
      planner
      tick()
    }
    class GameEngine {
      players
      agents
      fogs
      game_map
      connections
      start()
      reset()
      serialize()
    }
    GameEngine --> Agent
    GameEngine --> Player
    GameEngine --> FogOfWar
    GameEngine --> GameMap
    Agent --> BuildPlanner
    Player --> Entity
```

Entity ids come from a process-global counter. Inheritance is shallow (2 levels). Behaviour lives in **`Agent`** (835 lines, the biggest file): entities mostly hold data and movement; **combat, production and scouting rules are inside the agent** (`Knight.try_attack` exists but is unused; the agent applies damage itself, see [dead-code](../reports/dead-code.md)). There are **no function-level cycles** (*graph*).

## 3. Sequence: starting and running a match

```mermaid
sequenceDiagram
    actor U as User
    participant B as Browser
    participant M as main.py
    participant E as GameEngine
    participant L as _game_loop (asyncio task)
    U->>B: "Start" with two parameter sets
    B->>M: POST /start {seed?, agent0, agent1}
    M->>M: 409 if state == running
    M->>E: start(params0, params1, seed)
    E->>E: build Players, Agents (params merged over defaults), GameMap.generate(seed), FogOfWar x2
    E->>L: create_task(_game_loop())
    M-->>B: {status, state, seed}
    loop every 100 ms while state == running
        L->>E: _run_tick()
        L->>E: _broadcast()
        E-->>B: JSON frame (one per connection)
        L->>L: every 5th tick append spectator frame to replay buffer
        L->>L: sleep(TICK_MS)
    end
```

## 4. Sequence: one simulation tick

Order is fixed (`GameEngine._run_tick`). Agent 0 acts before agent 1 and both mutate the shared world immediately, so player 0 has a first-mover edge within each tick (default-vs-default came out 10/10 over 20 seeds, *ran*, too few to detect a small bias).

```mermaid
sequenceDiagram
    participant E as GameEngine._run_tick
    participant A as Agent.tick
    participant F as FogOfWar
    participant P as Player
    E->>A: for each agent: tick(player, enemy, map, own fog)
    Note over A: planner.tick, economy, production, scouting, defence, combat (in this order)
    E->>F: update(player, map) for each fog
    E->>P: remove_dead()
    E->>E: _check_win_condition (a player with no live TownHall loses)
    E->>E: tick += 1
```

## 5. Sequence: a player-view client connects mid-match (the fog-baseline problem)

```mermaid
sequenceDiagram
    participant C as Client (player view)
    participant W as ws_endpoint
    participant E as GameEngine
    participant F as FogOfWar
    C->>W: connect /ws?player=0 (match already running, baseline already taken)
    W->>E: serialize(0)
    W->>F: to_wire()
    F-->>W: {"delta": [...]} (baseline exists, so no full grid)
    W-->>C: frame with fog.delta
    Note over C: fogGrid is null: logs a warning and waits for fog.full
    loop every tick
        E-->>C: frame with fog.delta (ignored while fogGrid is null)
    end
    Note over C,F: a full grid is sent only on the first to_wire() after a match starts, so no fog is drawn until the next match
```

*Server side ran; client side read.* Two tabs on the same player, or a refresh (the client reconnects every 2 s after a close), trigger it.

## 6. Sequence: replay

```mermaid
sequenceDiagram
    actor U as User
    participant R as ReplayController
    participant M as main.py
    participant E as GameEngine
    U->>R: "Replay"
    R->>M: GET /replay
    M->>E: _replay_frames (last 720 frames, every 5th tick)
    M-->>R: {frames, tick_step: 5} (tens of MB for a long match)
    U->>R: play / scrub / speed
    R->>R: applyState(frame) through the same renderer as live
```

The replay reuses the live renderer, which is a good design. Its limits: frames carry no seed, parameters or version, so a replay cannot be re-run or attributed; `POST /reset` or a new `/start` deletes it; only the last 3,600 ticks survive.

## 7. Component inventory

| Component | File | Lines | Responsibility |
|-----------|------|-------|----------------|
| Transport | `server/main.py` | 162 | routes, module-level engine, static mounts |
| Orchestrator | `server/core/game_engine.py` | 332 | lifecycle, tick order, serialization, broadcast |
| AI | `server/ai/agent.py`, `build_planner.py`, `economy.py` | 835, 234, 253 | parametric policy |
| World | `server/core/entities.py`, `player.py`, `fog.py`, `pathfinding.py`, `constants.py`; `server/maps/game_map.py` | 284, 38, 126, 75, 124; 257 | state and rules |
| Client | `client/index.html` + `client/lib/*.mjs` | 1,894 + 1,203 | renderer, UI, networking |

## 8. What the docs say vs the code

`AGENTS.md`'s architecture tree places the game loop in `server/game_engine.py` and fog in `server/fog_of_war.py`. In the code the engine is `server/core/game_engine.py` (the top-level file is an unused shim) and fog is `server/core/fog.py`. Details in [04](04-documentation-audit.md).
