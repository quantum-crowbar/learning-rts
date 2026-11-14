# Development Context

Current project context and state information for AI agents.

> **Skill-first rule**: Before starting any task, check `.quantum-toolbox/skills/_index.md` for a skill that covers the work. Load and follow the matching skill — it encodes the preferred approach, templates, and quality bar.

## Project Overview

**Name:** deep-rts-playground (metarepo)

**Description:** Knowledge, analysis and orchestration for building **learning-rts**, our own RTS + deep-learning research platform, using the DeepRTS engine as a reference base. Holds no application source; source lives in gitignored clones under `code/`.

**Goals:**
- Understand DeepRTS accurately (generated code graph and architecture analysis, not hand-written docs)
- Decide, on evidence, between fixing DeepRTS and building learning-rts fresh
- Build learning-rts as a separate repo with deep-learning research features
- Keep old and new code, and their analyses, strictly isolated

## Tech Stack

| Category | Technology |
|----------|------------|
| Metarepo | Markdown, shell, JSON; git submodule `.quantum-toolbox` (v3.3.1) |
| deep-rts (old) | C++17, pybind11, xtensor/xsimd, Blend2D, OpenCV, spdlog, nlohmann_json; CMake + vcpkg + setuptools; Python 3.8+ wrapper |
| learning-rts (new) | **TBD** (decided after fix-vs-rebuild) |
| Testing | none yet |
| CI/CD | none |

## Current State

**Version:** 0.0.1

**Status:** Consolidated; deep-rts analysed (arch-analysis + code-graph, 2026-11-14); no working build of deep-rts; fix-vs-rebuild not decided.

### Implemented

- Metarepo layout: old/new split, patches, pinned sources, bootstrap script (`scripts/bootstrap-sources.sh`, idempotent, verified)
- `.quantum-toolbox` adopted at v3.3.1 (replaces the old `.aiagent-config`/agents-setup submodule)
- Harness-agnostic `AGENTS.md` + `CONTEXT.md`; `CLAUDE.md` only imports `AGENTS.md`
- Upstream check (2026-11-14): nothing newer than `6bfbfd5`
- Full analysis of `code/deep-rts`: 7 architecture views + View 09 + 4 reports in `docs/architecture-docs/` (start at `index.md`, then `reports/findings-summary.md`)
- Code graph in `code/deep-rts/code_graph.sqlite` (502 nodes, 732 edges, 0 function-level cycles); regenerate with the commands in `specs/analysis-manifest.json`
- Legacy docs audited: 50% claim accuracy (`docs/architecture-docs/analysis/04-documentation-audit.md`)

### In Progress

- Nothing.

### Planned

1. Revoke the Discord webhook committed in `.travis.yml:28` (owner action; token is in the public upstream history)
2. Fix-vs-rebuild decision for deep-rts → learning-rts (use `tech-stack-decisions`; inputs in `reports/findings-summary.md`)
3. Add a remote for `code/learning-rts`, then list it in `sources/urls.md`
4. If deep-rts is kept: a build that gets past configure (one pinned dependency path, xtensor ≥ 0.26), then re-extract with a clang-based graph
5. Eventually: squash/delete pre-0.0.1 history (owner's stated intent; **do not do it unasked**)

## Key Components

| Path | Purpose |
|------|---------|
| `AGENTS.md` / `CONTEXT.md` | Agent instructions / project state (canonical, harness-agnostic) |
| `CLAUDE.md` | One-line pointer: `@AGENTS.md` |
| `.quantum-toolbox/` | Toolbox submodule, pinned v3.3.1 |
| `sources/urls.md`, `sources/pins.env` | Source registry; pinned revisions |
| `scripts/bootstrap-sources.sh` | Clone sources into `code/`, apply patches |
| `patches/deep-rts/` | Our changes to upstream (build-fix attempts from 2026-01) |
| `code/deep-rts/` | OLD engine, pinned `6bfbfd5` + patches (gitignored, read-only reference) |
| `code/learning-rts/` | NEW project, own git repo, scaffold only (gitignored here, no remote yet) |
| `docs/legacy/deep-rts/` | Hand-written pre-toolbox docs. **Unverified baseline**, not truth |
| `docs/architecture-docs/index.md` | Entry point of the generated analysis |
| `docs/architecture-docs/analysis/` | Views 01-07 and 09 (code graph) |
| `docs/architecture-docs/reports/` | `findings-summary`, `entry-point-map`, `dead-code`, `sqlite-cookbook` |
| `docs/update-logs/` | One log per analysis session |
| `specs/analysis-manifest.json` | Analysis manifest (toolbox schema, validated) |
| `scripts/cg-extract.py`, `cg-pyan-crosscheck.py`, `cg-reports.py` | Code-graph extraction and report generation (`scripts/requirements-analysis.txt`) |
| `code/deep-rts/code_graph.sqlite` | Queryable code graph (gitignored, regenerable) |

## Known Issues

- **deep-rts does not build.** Last attempt (January 2026; log kept untracked at the repo root as `build.log`) failed at CMake configure: `Could not find xtensor`. In that run vcpkg rejected the spec `xtensor[xsimd]@0.24.7`; the origin of the `@0.24.7` suffix is **not** in the current tree (the log predates later edits), so the root cause is not established. The pip path installs unpinned vcpkg master and runs `apt-get` (needs root). `patches/deep-rts/0001` changes the xtensor include to `xtensor/containers/` (xtensor ≥ 0.26), which the pinned PMM baseline (0.24.3) does not provide. Details: `docs/architecture-docs/analysis/05-dependency-health.md`.
- **Legacy docs are 50% accurate** (21 discrepancies in `04-documentation-audit.md`). Examples: action IDs are 1–16 (docs say 0–15), the documented tensor channels are wrong, the Python wrapper cannot be imported. The 6M steps/sec figure is upstream's claim; unmeasured (and the engine defaults to a 60 steps/s wall-clock gate).
- **Code graph is tier 2 (tree-sitter + class-hierarchy analysis), not type-aware.** Measured: C++ project-internal call resolution 97.4%, Python 37.0%; templates, overloads beyond arity and `auto` expression chains are unresolved. Virtual dispatch (state machine) and the pybind boundary *are* modelled. A configurable build would allow a clang-based graph. Scorecard and named gaps: `docs/architecture-docs/analysis/09-code-graph.md`.
- Upstream moved: `cair/DeepRTS` → `pa-research/deep-rts`. Dormant since 2023-05-16; 14 open items on GitHub (3 are dependabot PRs; the rest unread).
- Commit `6b17326` carries a `Co-Authored-By` AI trailer. Violates the no-attribution rule; fix only when history is squashed (see Planned 5).

## Dependencies

Metarepo has no runtime dependencies. Analysis scripts need `venv/bin/pip install -r scripts/requirements-analysis.txt` (tree-sitter, tree-sitter-cpp, tree-sitter-python, pyan3, pyflakes, jsonschema).

## Environment Setup

### Prerequisites

- git, bash, cmake, ninja, g++ (present); python 3.12
- Root `venv/` exists (numpy, opencv-python); gitignored

### Local Development

1. `git clone --recurse-submodules <this repo> && cd deep-rts-playground`
2. `scripts/bootstrap-sources.sh`
3. `python3 -m venv venv && venv/bin/pip install -r scripts/requirements-analysis.txt` (only to regenerate the code graph)
4. Start an agent session in this directory and run `/start`

### Running Tests

None yet. Bootstrap check: run `scripts/bootstrap-sources.sh` twice; second run must print `already` for each patch.

## Architecture Notes

### Important Conventions

- Old code is never edited in place; changes go through `patches/deep-rts/*.patch`.
- New code only in `code/learning-rts/`.
- Claims about deep-rts are verified against source or a real run, not `docs/legacy/`.

---

## Analysis Preferences

| Setting | Value |
|---------|-------|
| SQLite-first | `enabled` |
| Last extraction | 2026-11-14 (`deep-rts` @ `6bfbfd5`; tier 2; 502 nodes, 732 edges) |
| Extraction scope | `deep-rts` (single repo, unified SQLite; `learning-rts` untracked) |

---

## Update Log

| Date | Changes |
|------|---------|
| 2026-11-14 | Consolidated into metarepo (v0.0.1): old/new split, toolbox v3.3.1, harness-agnostic AGENTS/CONTEXT; arch-analysis complete (7 views + View 09, 4 reports); code-graph extracted: 502 nodes, 732 edges, 0 cross-repo calls |
