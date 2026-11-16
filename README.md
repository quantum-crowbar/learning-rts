# learning-rts

I am building a small real-time-strategy game as a testbed for game AI: parametrized agents play each other, I can watch every match live or as a replay, and I learn how game AI is built along the way. My goals, in order: game AI in strategy games, then Rust, then polishing my experience building real-time systems.

This repository is my workspace: design docs, roadmap, and analyses of the two projects I study, [DeepRTS](https://github.com/pa-research/deep-rts) (my inspiration and starting reference) and my earlier project ejaj-boj. The game code lives in `code/learning-rts/`, a separate git repo.

| | |
|---|---|
| Inspiration: `code/deep-rts/` | Upstream DeepRTS pinned at `6bfbfd5` + `patches/`. Read-only reference. |
| Mine: `code/learning-rts/` | My own project, separate git repo. |
| Sibling: `code/ejaj-boj/` | My earlier parametric-RTS project, pinned `fde9d3c`. Read-only; sprites (CC0), ideas, measurements. |
| Knowledge | `docs/architecture-docs/` (deep-rts, generated), `docs/ejaj-boj/architecture-docs/` (ejaj-boj, generated), `docs/general/` and `docs/roadmap/` (learning-rts design), `specs/analysis-manifest.json` |

`code/` is gitignored. Set up a fresh clone with:

```bash
git clone --recurse-submodules <this repo>
cd learning-rts
scripts/bootstrap-sources.sh
```

## Analysis of DeepRTS

`docs/architecture-docs/index.md` is the entry point (generated 2026-11-14 from `deep-rts` @ `6bfbfd5`): technology, interfaces, diagrams, documentation audit, dependency health, data flow, error handling and a SQLite code graph (502 functions, 732 edges). Reports: `reports/findings-summary.md`, `entry-point-map.md`, `dead-code.md`, `sqlite-cookbook.md`. Regenerate the graph with the commands listed in `specs/analysis-manifest.json`.

## Analysis of ejaj-boj

`docs/ejaj-boj/architecture-docs/index.md` is the entry point (generated 2026-11-15 from `ejaj-boj` @ `fde9d3c`): the same views plus a SQLite code graph (271 functions, 326 edges; Python and JavaScript). Unlike deep-rts it runs: 456 tests pass and a match plays headless at about 2,700 ticks/s on one core. Regenerate with `scripts/cg-ejaj-boj.py`, `scripts/cg-pyan-crosscheck.py ejaj-boj`, `scripts/cg-ejaj-boj-reports.py`.

For AI agents (any harness): start at [AGENTS.md](AGENTS.md) and [CONTEXT.md](CONTEXT.md), then run `/start`.

Upstream DeepRTS is MIT-licensed; see [LICENCE.md](LICENCE.md). Its original paper: Andersen, Goodwin, Granmo, *Deep RTS: A Game Environment for Deep Reinforcement Learning in Real-Time Strategy Games*, IEEE CIG 2018. The original README is kept at `docs/legacy/deep-rts/README.md`.
