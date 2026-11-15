# learning-rts: what we are doing

Status: design phase, 2026-11-15. **Nothing is built yet.** This folder describes intent and decisions; the code will live in `code/learning-rts/`.

## The idea in one paragraph

We are building a small real-time-strategy (RTS) game as a **testbed for game AI**. You write an *agent spec* (which kind of agent, plus its parameters), hand two specs to an *arena*, and the arena plays seeded matches between them and reports a rated result. Every match can be **watched**, live in a browser as the server plays it, or afterwards from a replay file. The point is to learn how game AI is built, from hand-written scripted bots, through parameter tuning and search, up to learned (neural) agents, and to see them fight.

## Where DeepRTS fits

DeepRTS (an existing C++ RTS research environment, cloned read-only at `code/deep-rts/`) is our **inspiration and starting reference**. We study it and take what is useful: its sprites, maps and rule constants, and ideas such as shared unit states and scenarios. We do not fix it, port it or stay compatible with it, and our design will keep diverging from it as we redesign. Matching its rules or its paper is **not** a goal.

**ejaj-boj** is the owner's own earlier project with a very similar idea (parametrized AI agents fighting while you watch) and, unlike DeepRTS, it runs. It is the closest existing prototype; we study it the same way (read-only, pinned, analysed in [../ejaj-boj/architecture-docs/index.md](../ejaj-boj/architecture-docs/index.md)).

DeepRTS also taught us what to avoid. As it stands it does not build, its Python wrapper cannot be imported, and it has several silent defects in what a learning agent sees and is rewarded for. The evidence is in [../architecture-docs/reports/findings-summary.md](../architecture-docs/reports/findings-summary.md).

## What we want at the end

1. Put in a set of parameters or instructions, get an agent.
2. Run agents against each other, many seeded games, with sides swapped, and get ratings.
3. Watch any game, live or replayed, with the agent's reasoning drawn over the map.
4. Climb the standard game-AI ladder: scripted bots, parameter search, tree search (MCTS), learned agents with self-play, and optionally agents driven by natural-language instructions.

## The game, in brief

- Small maps (about 32x32), a few unit types that counter each other (rock-paper-scissors), so strategy matters.
- Resources: **gold first** for the proof of concept; **wood and stone** are added later (roadmap milestone M3b).
- No fog of war at first.
- DeepRTS sprites for the look, loaded through a swappable "skin" (see the sprite caveat in [decisions.md](decisions.md), D05). Sprites from the owner's own project, ejaj-boj (CC0 Tiny Swords art), are a candidate skin source (Q10).

## Technology in brief

| Part | Language | Status |
|------|----------|--------|
| Simulation core | **Rust** | decided by the owner |
| Agents, arena, match server, research | Python | proposed |
| Viewer (browser) | TypeScript + Canvas | proposed |
| Rules, agent specs | TOML; maps and replays JSON | proposed |

"Decided" means the owner chose it; "proposed" means recommended but not yet confirmed. Every decision, with its reasoning, alternatives and status, is in [decisions.md](decisions.md).

## How to work in this project

- **Teaching mode.** The owner is a long-time C++ programmer who has not used it in years and is learning Rust and game AI. Explanations of choices and shown code are part of the work, not extra. See the working agreement in [../../AGENTS.md](../../AGENTS.md).
- **Honesty about verification.** Claims are marked as measured or not. Performance numbers, in particular, are unmeasured until the arena exists. Code sketches in these docs are marked when they have not been compiled.
- **Reference and ours stay separate.** `code/deep-rts/` (inspiration and starting reference) is read-only. Our code goes only in `code/learning-rts/`.

## Map of the docs

| Document | Read it for |
|----------|-------------|
| [architecture.md](architecture.md) | Components, data model (ER diagram), sequence diagrams, how each part works, code sketches |
| [decisions.md](decisions.md) | Every decision with status, reasoning, alternatives, what would change it; open questions |
| [glossary.md](glossary.md) | Every term used in the project, including Rust and game-AI terms |
| [../roadmap/ROADMAP.md](../roadmap/ROADMAP.md) | Milestones with exit gates |
| [../architecture-docs/index.md](../architecture-docs/index.md) | Generated analysis of DeepRTS, our inspiration |
| [../ejaj-boj/architecture-docs/index.md](../ejaj-boj/architecture-docs/index.md) | Generated analysis of ejaj-boj, the owner's earlier project (it runs; measurements and lessons) |
| [../legacy/deep-rts/](../legacy/deep-rts/) | DeepRTS's original hand-written docs; unverified, about 50% accurate |
