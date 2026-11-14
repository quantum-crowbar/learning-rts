# deep-rts-playground

Metarepo for building **learning-rts**, an RTS and deep-learning research platform, using
[DeepRTS](https://github.com/pa-research/deep-rts) as a reference base.

| | |
|---|---|
| Old: `code/deep-rts/` | Upstream engine pinned at `6bfbfd5` + `patches/`. Read-only reference. |
| New: `code/learning-rts/` | Our own project, separate git repo. |
| Knowledge | `docs/architecture-docs/` (generated), `specs/analysis-manifest.json` |

`code/` is gitignored. Set up a fresh clone with:

```bash
git clone --recurse-submodules <this repo>
cd deep-rts-playground
scripts/bootstrap-sources.sh
```

For AI agents (any harness): start at [AGENTS.md](AGENTS.md) and [CONTEXT.md](CONTEXT.md), then run `/start`.

Upstream DeepRTS is MIT-licensed; see [LICENCE.md](LICENCE.md). Its original paper: Andersen, Goodwin, Granmo, *Deep RTS: A Game Environment for Deep Reinforcement Learning in Real-Time Strategy Games*, IEEE CIG 2018. The original README is kept at `docs/legacy/deep-rts/README.md`.
