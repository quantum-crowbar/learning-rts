# learning-rts roadmap

Status: draft, 2026-11-14. Nothing below is built yet. Decisions marked **open** are not made.

## Goal

A small deterministic RTS in which **parametrized agents play each other**: you supply an agent spec (type, parameters, optional weights), the arena runs seeded matches and reports rated results, and **you can watch every game**, live or as a replay. The purpose is to learn how game AI is built, from scripted bots up to search and learned agents. Matching the original DeepRTS rules or paper is explicitly **not** a goal.

## Requirements (fixed by the user)

1. **Watch games live**: a server plays the match in front of you.
2. **Watch games afterwards**: replay with scrubbing, from a file.
3. **DeepRTS sprites are used from the start and for the foreseeable future** (see "Sprites" for the caveat).
4. Agents are specs: one file in, rated result out.

## Design principles

- Time is a tick counter. The core has no wall clock; pacing (real time, 4x, flat out) belongs to the match runner.
- The core mutates only through `step(commands)` and emits events. It never writes observations.
- Observations are computed from state on demand, so they cannot go stale. Rewards are functions over events. Termination is a pure function of state.
- Entities are rows in fixed-capacity arrays with generational ids: no pointers to units, and exceeding capacity is a defined error.
- Rules are data (TOML), not code. Resources are a table of kinds (`gold`, later `wood`, `stone`), not hard-coded fields, so adding one is a content change.
- Determinism is a tested contract: same seed plus same commands gives the same per-tick state hash.
- Snapshot/restore is a core feature (search agents and the viewer depend on it).
- Agents issue command-level actions ("train X", "send group G to P"), not per-unit-per-tick steering.
- Players are symmetric; single-agent is a wrapper around a scripted opponent.

## Architecture

```
research (Python): baselines, self-play, evaluation
arena: spec loader, parallel seeded matches, side swap, ratings (Elo / Bradley-Terry)
match server: owns pacing, streams snapshots over WebSocket, writes replay
agent API: observation + legal commands in, commands (+ optional annotations) out
rl layer: observers, reward functions, action codec, scenarios
sim core (Rust, no IO/clock/globals): SoA world, tile grid, seeded RNG, step(), state_hash(), snapshot/restore
content: units/buildings/tiles/rules (TOML), maps
viewer (browser, static HTML+JS): live mode and replay mode share one renderer
```

Game scope for v1: about 32x32 maps, 3-4 unit types with counters (rock-paper-scissors), **gold only for the proof of concept**, no fog of war. The target economy is **gold, wood and stone**, added at M3b (below); deep-rts already has gold, lumber and stone tile types and yields, so the maps and sprites cover all three.

## Milestones

Each milestone has an exit gate that a run can fail.

| # | Milestone | Exit gate |
|---|-----------|-----------|
| M0 | One-page game design; ADRs (language, action space, agent spec, replay format); skin manifest format; extract rule constants from deep-rts into a TOML draft | You can describe the full game and one winning strategy per matchup; constants table diffed against deep-rts source |
| M1 | Core sim: map loader, one mobile unit, pathfinding, tick loop, RNG, state hash, snapshot/restore | Determinism test: many seeds with random command streams give identical hashes across runs and across two machines |
| M1b | Replay writer and **viewer with DeepRTS sprites**: replay file = header (rules version, map, seed, agent specs) + per-tick snapshots; play, pause, step, speed, scrubber, click-to-inspect | You open a replay file of sprite units moving on a tile map and scrub through it |
| M1c | **Live viewing**: match server streams ticks over WebSocket to the same viewer; pause/step/speed controls honoured by the runner; every live match also writes a replay | You watch a match in the browser in real time and can rewatch it from the file |
| M2 | Full rules with a **gold-only** economy: production, combat, win/lose | A scripted bot plays a complete game you can watch |
| M3 | Agent API, spec loader, arena, ratings, first parametrized bots (rush, boom, turtle); agent annotations drawn in the viewer | Two spec files in, a rated result out; you can see why an agent acted |
| M3b | **Multi-resource economy: add wood and stone** (data-driven resource table, new costs and tech/unit requirements, bots gain resource-allocation parameters). Done before M4 so bots are not tuned on a game that then changes; ratings from before M3b are discarded. | Existing gold-only bots still run unmodified; a bot that ignores wood or stone is measurably beaten by one that balances them |
| M4 | Parameter optimization (CMA-ES or genetic) over bot parameters against a pool | Evolved bot beats the hand-tuned ones; non-transitive matchups visible in ratings |
| M5 | Search agents (MCTS using snapshot/restore) | MCTS beats scripted bots at a fixed time budget |
| M6 | Learned agents: small-network PPO, then self-play and a population | Beats the scripted pool on the small game; training reproducible from config + seed |
| M7 | Optional: LLM-instruction agents (coarse decision interval), fog of war, bigger game, human player over the same socket | Driven by what M3-M6 taught |

## Viewer

- Same page for live and replay. Live = the replay format streamed as it is produced.
- Slow agents (MCTS, LLM): the sim waits for each decision, so wall-clock watching is only smooth for fast agents. This is inherent.
- Later upgrade: compile the core to WASM so the viewer can re-simulate from seed + commands, which shrinks replays to a command log and gives exact backward scrubbing.
- Multiple spectators can attach to one live match.

## Sprites

Decision: the viewer uses the DeepRTS sprites (human and orc units, buildings, tiles; source `code/deep-rts/DeepRTS/python/assets/textures/`).

- **Provenance is unknown.** The repo's MIT licence covers its code; no file records where the art came from, and the unit names (peasant, footman, archer, grunt, peon, axethrower, town hall) match Warcraft II. Treat the art as possibly third-party copyrighted until shown otherwise. This is a flag, not a verified finding.
- Consequence: fine for local use. Do not publish a repository or release containing the sprites without resolving this.
- Therefore: **sprites are not committed to learning-rts.** The viewer loads them through a skin manifest (unit/tile id -> atlas file + frame rectangle) from a configurable path, and a setup script copies them from the metarepo clone. A placeholder skin (flat colours) must always work, so the project never depends on the art.
- Open: sprite sheet layout (frame size, directions, animation frames) has not been inspected yet. Mapping it is part of M0/M1b.
- The owner's own project **ejaj-boj** has CC0 sprites (Pixel Frog's Tiny Swords, per its `CREDITS.md`; 34 PNGs in `code/ejaj-boj/client/assets/`), a candidate second or default skin source whose licence is known, unlike DeepRTS's (decisions.md, Q10). Frame layouts are not yet mapped.

## Compute

This machine: i7-1065G7 (4 cores / 8 threads, laptop part), 15 GB RAM, no GPU. A small deterministic sim should be cheap here, but throughput is **unmeasured**; the first real games-per-second figure comes with M3's arena. Small-MLP learning is feasible; large or image-based networks and large-scale self-play are not, short of renting a GPU for M6.

## Using deep-rts (inspiration and starting reference, read-only)

deep-rts inspires this project; nothing obliges us to stay close to it as the design diverges.

- Reuse: sprites (per the section above), maps and `tile_properties.json` as seed content, rule constants as a draft.
- Do not port code. Record the reason in the commit message if any is copied.
- The six RL-contract defects found in the analysis become tests: negative rewards stay negative, `is_terminal` called twice changes nothing, observations never go stale, step rate is independent of wall time, subclassed players are not sliced, spawning returns the real unit.

## Open decisions

- **Language**: Rust core is **decided** (owner, 2026-11-15; fallback if the learning curve blocks M1: prototype in Python behind the same interfaces). Python agents/arena/match server and the TypeScript viewer are proposed. Rust is not installed yet: M0 includes installing the toolchain.
- **No floating point in the sim** (integer/fixed-point): proposed, decide in M0.
- Every decision with status and reasoning: [../general/decisions.md](../general/decisions.md). Architecture, ER and sequence diagrams: [../general/architecture.md](../general/architecture.md).
- **Rules/map scope** of the v1 game (exact unit list, costs, counters).
- **Replay format**: per-tick snapshots first, command log + WASM later.
- **Sprite sheet mapping** and the skin manifest format.

## Using ejaj-boj (read-only sibling, analysed 2026-11-15)

The owner's earlier parametric-RTS project. Analysis: [../ejaj-boj/architecture-docs/index.md](../ejaj-boj/architecture-docs/index.md). Inputs for the milestones above, not decisions:

- **Evidence for M3 and the language question**: a pure-Python sim of a similar game ran about 2,670 ticks/s per core (about 0.26 s per match); see the table in [decisions.md](../general/decisions.md) ("Evidence that bears on the proposed decisions").
- **M0 / M3 constants and the first agent type**: its 18-key parameter dict (`server/core/constants.py`) and parametric agent (`server/ai/`) are a ready-made first bot to port or re-express as an agent spec; its rush-vs-default result shows the space has structure.
- **M1b / M1c viewer**: its renderer, replay controller, fog overlay and sprite/tile configuration (`client/`) are the nearest working example; its flaws (full map every tick, replay without seed/params, fog baseline for late joiners) are listed in its findings summary.
- **What it lacks relative to this roadmap**: an agent interface, arena and ratings, snapshot/restore, a determinism contract, gold, a command/event layer.

