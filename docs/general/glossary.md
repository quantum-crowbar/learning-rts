# Glossary

Terms used across the project. Sections: project, game, simulation, AI, Rust, tooling, deep-rts (our inspiration). Rust entries relate to C++ where that helps. Add a term here the first time a doc uses it.

## Project

| Term | Meaning |
|------|---------|
| **ADR** | Architecture Decision Record: a short note recording one decision, why, and what was rejected. Our log is [decisions.md](decisions.md). |
| **Arena** | The program that loads agent specs, runs many seeded matches between them in parallel, swaps sides, and computes ratings. |
| **deep-rts** | Upstream DeepRTS, a C++ RTS research environment: our **inspiration and starting reference**, cloned read-only at `code/deep-rts/`. Hyphenated in the repo, "DeepRTS" as a product name. We do not fix or port it. |
| **ejaj-boj** | The owner's earlier parametric-RTS project (Python server, JavaScript canvas client): two AI agents configured by a parameter dict fight while you watch. Read-only in the metarepo at `code/ejaj-boj/`, analysed in `docs/ejaj-boj/`. Its sprites (Tiny Swords, CC0) are a candidate skin source (decisions.md, Q10). |
| **learning-rts** | Our project: our own game and AI arena, inspired by deep-rts, in its own git repo at `code/learning-rts/`. |
| **Metarepo** | This repository: docs, analysis and orchestration for both codebases. It holds no application source; source lives in gitignored clones under `code/`. |
| **M0 ... M7** | Roadmap milestones. Each has an exit gate that a run can fail. See [../roadmap/ROADMAP.md](../roadmap/ROADMAP.md). |
| **Teaching mode** | The working agreement that the assistant explains choices and shows code, because the owner is learning Rust. See [../../AGENTS.md](../../AGENTS.md). |
| **Provenance labels** | `ran` / `graph` / `read` / `fetched`: how a claim in the generated analysis was verified. |

## Game

| Term | Meaning |
|------|---------|
| **Building** | A non-moving entity that produces units or stores resources. |
| **Counter (unit counter)** | Rock-paper-scissors design: unit type A beats B beats C beats A, so no single unit is best. |
| **Entity** | Anything in the world with state: a unit, building or resource node. |
| **Fog of war** | Players only see what their units can see. Not in v1. |
| **Gold / wood / stone** | The three resource kinds. Gold first; wood (called *lumber* in deep-rts) and stone at milestone M3b. |
| **Map** | A tile grid with terrain, resource nodes and spawn points. Format: Tiled JSON (deep-rts maps are reused). |
| **Order** | What a unit is currently doing (moving, attacking, gathering). A *command* sets an order. |
| **Ruleset** | The data that defines the game: unit types, costs, damage, resources. Stored as TOML, versioned. |
| **Tech tree** | Which units/buildings unlock which others. Later milestone. |
| **Tile** | One grid cell. |
| **Win / lose** | A player is defeated when it has no units or buildings left (exact condition is an open rule). |

## Simulation

| Term | Meaning |
|------|---------|
| **Annotation** | Extra drawing instructions an agent attaches to its decisions (for example "target = unit 14"), shown in the viewer so you see why it acted. |
| **Command** | A request from an agent to the sim ("train a footman", "send these units to tile P"). Commands are data; the sim validates and executes them. |
| **Core (sim core)** | The Rust library holding all game logic. No clock, no IO, no global state. |
| **Decision interval** | How many ticks pass between an agent's decisions. Slow agents (search, LLM) use a larger interval. |
| **Determinism** | Same seed plus same commands gives exactly the same game, on any machine. A tested contract here. |
| **Event** | A fact the sim reports after a step (`UnitKilled`, `ResourceDelivered`, `PlayerDefeated`). Rewards are computed from events. |
| **Fixed-point** | Representing fractions as integers (for example 1/256 of a tile as the unit). Avoids floating-point differences between machines, which would break determinism. |
| **Generational id** | An entity handle made of (row index, generation). When a row is reused its generation changes, so an old handle is detected as stale instead of silently pointing at a different unit. |
| **Live mode** | The match server plays a match in front of you, streaming each tick to the viewer. |
| **Pacing** | How fast ticks are produced in real time (1x, 4x, as fast as possible). Owned by the match runner, never by the core. |
| **Replay** | A file that records a match so it can be watched later: header (rules version, map, seed, agent specs) plus per-tick snapshots. |
| **RNG (seeded)** | A random-number generator started from a fixed seed so runs are reproducible. |
| **SoA (struct of arrays)** | Storing each entity field in its own array (`x[]`, `y[]`, `hp[]`) instead of one struct per entity. Cache-friendly, and makes snapshots a plain copy. |
| **Snapshot** | A full copy of the world state at one tick. Used by the viewer, by replays and by search agents. |
| **Spectator** | A viewer attached to a live match. Several can attach to one match. |
| **State hash** | A single number summarising the whole world state at a tick; two runs are identical if their hashes match at every tick. The determinism test compares them. |
| **Step** | Advance the world by one tick, given the commands issued for that tick. |
| **Tick** | The sim's unit of time. There is no wall clock in the core; time is the tick counter. |
| **Trampoline** | (deep-rts) A C++ class that forwards virtual calls to Python so Python can override C++ behaviour. We do not need one: agents call into the core, not the reverse. |

## AI

| Term | Meaning |
|------|---------|
| **A\*** | A shortest-path search on a grid using a distance estimate. Our first pathfinder. |
| **Agent** | Whatever chooses commands for one player: a script, a search procedure, a neural network, an LLM. |
| **Agent spec** | A file naming an agent type and its parameters (and optionally weights). The unit of exchange in the arena. |
| **Behaviour tree / utility AI** | Two common ways to structure scripted game bots. |
| **Bradley-Terry / Elo / TrueSkill** | Rating systems that turn win/loss results into a strength number. Which one we use is an open decision. |
| **CMA-ES** | An evolutionary optimiser for continuous parameters; used to tune bot parameters (M4). |
| **Curriculum** | Training on easy scenarios first, then harder ones. |
| **Exploitability** | How badly the best counter-strategy beats an agent; a measure of how robust it is. |
| **Gymnasium / PettingZoo** | Standard Python interfaces for single-agent and multi-agent reinforcement-learning environments. We expose the game through them when learning starts (M6). |
| **JPS (jump point search)** | A faster variant of A\* for uniform grids. Used in deep-rts; we start with plain A\*. |
| **LLM agent** | An agent whose decisions come from a language model following natural-language instructions. Slow, so it uses a large decision interval. |
| **MCTS (Monte-Carlo tree search)** | Search that plays out many simulated games from the current state to pick a command. Needs a fast, exact snapshot/restore. |
| **Non-transitive** | A beats B, B beats C, C beats A. Visible in tournament results when units counter each other. |
| **Observation** | What an agent sees of the world, computed from state on demand. |
| **Observer** | A pluggable function that turns state into an observation (a tensor, an entity list). |
| **PPO** | Proximal Policy Optimization, a standard reinforcement-learning algorithm; our first learned agent (M6). |
| **Population / league** | Training many agents against each other so none overfits to one opponent. |
| **Reward** | A number telling a learning agent how well it did, computed from events. Ours are real-valued and composable. |
| **Self-play** | A learning agent trains by playing copies of itself or past versions. |

## Rust

| Term | Meaning |
|------|---------|
| **Borrow / `&T` / `&mut T`** | Temporary access to a value without taking it. Many shared `&T` borrows *or* exactly one exclusive `&mut T`, never both at once; the compiler enforces it. Closest C++ idea: references, but checked. |
| **Cargo** | Rust's build tool and package manager (like CMake + a package manager in one). |
| **Clone** | Make a deep copy. `#[derive(Clone)]` on the world struct gives us snapshots almost for free. |
| **Crate** | A Rust package or library (like a CMake target). |
| **`enum`** | A type that is one of several variants, each able to carry data. Much stronger than a C++ `enum`; we use it for `Command` and `Event`. |
| **`impl` / method** | Where functions of a type are defined. `&self` borrows it, `&mut self` borrows it exclusively. |
| **Ownership** | Every value has exactly one owner; when the owner goes away the value is freed. No manual `delete`, no garbage collector. |
| **`Option<T>`** | Either `Some(value)` or `None`. Replaces null pointers; the compiler forces you to handle `None`. |
| **Panic** | A Rust crash with a message (for example indexing out of range). Not an exception you normally catch. |
| **`Result<T, E>`** | Either `Ok(value)` or `Err(error)`. How Rust reports recoverable errors. |
| **Slice (`&[T]`)** | A borrowed view of a contiguous run of elements. |
| **Trait** | A set of methods a type promises to provide (like an interface or a C++ concept). |
| **`unsafe`** | Marks code where the compiler cannot prove safety. We aim to have none in the core. |
| **`Vec<T>`** | A growable array (like `std::vector`). |

## Tooling

| Term | Meaning |
|------|---------|
| **Canvas 2D** | The browser's drawing API; draws sprites with `drawImage`. |
| **esbuild / Vite** | Tools that bundle TypeScript for the browser. |
| **maturin** | Builds a Rust library into an installable Python package. |
| **PyO3** | The Rust library that lets Python call Rust code in-process (no network, no serialization). |
| **Skin** | A swappable set of images plus a manifest mapping unit/tile ids to frames. The viewer always works with a flat-colour placeholder skin. |
| **SQLite** | Single-file database; proposed for storing arena results. |
| **Tiled** | A map editor; its JSON format is what deep-rts maps use. |
| **TOML** | A simple config file format; used for rulesets and agent specs. |
| **TypeScript** | JavaScript with types; the viewer language. |
| **WASM (WebAssembly)** | A compact format that lets compiled code (here, the Rust core) run in the browser. Lets the viewer re-simulate exactly from a command log. |
| **WebSocket** | A persistent browser-server connection; carries live snapshots. |

## deep-rts (our inspiration)

| Term | Meaning |
|------|---------|
| **Blend2D** | The 2D graphics library deep-rts uses to render. |
| **CMRC** | A tool that embeds asset files into the compiled binary. |
| **Flyweight state** | Unit behaviour states (Walking, Attacking, ...) shared between all units instead of one object per unit. |
| **pybind11** | C++ library that exposes C++ classes to Python; deep-rts's binding layer. |
| **Scenario** | A deep-rts `Game` subclass with criteria that define a reward. |
| **vcpkg / CPM / PMM** | C++ dependency tools; the reason deep-rts does not build reproducibly. |
| **xtensor** | C++ n-dimensional array library; holds deep-rts's `(W, H, 10)` state tensor. |
