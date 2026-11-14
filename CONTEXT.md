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

**Status:** Consolidation done; no analysis run yet; no working build of deep-rts.

### Implemented

- Metarepo layout: old/new split, patches, pinned sources, bootstrap script (`scripts/bootstrap-sources.sh`, idempotent, verified)
- `.quantum-toolbox` adopted at v3.3.1 (replaces the old `.aiagent-config`/agents-setup submodule)
- Harness-agnostic `AGENTS.md` + `CONTEXT.md`; `CLAUDE.md` only imports `AGENTS.md`
- Upstream check (2026-11-14): nothing newer than `6bfbfd5`

### In Progress

- Nothing.

### Planned

1. Run `/start` setup validation, then arch-analysis + code-graph on `code/deep-rts`
2. Diff regenerated analysis against `docs/legacy/deep-rts/` (doc-accuracy baseline)
3. Fix-vs-rebuild decision for deep-rts → learning-rts (use `tech-stack-decisions`)
4. Add a remote for `code/learning-rts`, then list it in `sources/urls.md`
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
| `docs/architecture-docs/` | Generated analysis (empty until first run) |
| `specs/analysis-manifest.json` | Analysis manifest (created by first run) |

## Known Issues

- **deep-rts does not build.** Last attempt (January 2026; log kept untracked at the repo root as `build.log`) failed at CMake configure: `Could not find xtensor`. Root cause: vcpkg rejects the spec `xtensor[xsimd]@0.24.7` generated from `vcpkg_dependencies.txt`. `patches/deep-rts/0001` fixes the xtensor header move, the xtensor-python pin and CMake policy, **not** the vcpkg spec. Install script also tries `sudo apt`.
- **Legacy docs contain errors.** Example: action IDs are 1–16 in `Constants.h`, legacy docs say 0–15. The 6M steps/sec figure is upstream's claim; unmeasured here.
- **Code-graph on C++ will be approximate.** C++ is not in the toolbox's language table; expect tree-sitter (syntax-only, no type resolution) or AI extraction. Misses virtual dispatch (state machine), templates (xtensor) and pybind trampolines. A working CMake configure yields `compile_commands.json` for a clang-based graph. Record per-language `edgeResolutionCoverage` after the run.
- Upstream moved: `cair/DeepRTS` → `pa-research/deep-rts`. Dormant since 2023-05-16; 14 open issues (unread).
- Commit `6b17326` carries a `Co-Authored-By` AI trailer. Violates the no-attribution rule; fix only when history is squashed (see Planned 5).

## Dependencies

Metarepo has no runtime dependencies. Analysis tooling (tree-sitter grammars, etc.) is installed per the code-graph skill at run time.

## Environment Setup

### Prerequisites

- git, bash, cmake, ninja, g++ (present); python 3.12
- Root `venv/` exists (numpy, opencv-python); gitignored

### Local Development

1. `git clone --recurse-submodules <this repo> && cd deep-rts-playground`
2. `scripts/bootstrap-sources.sh`
3. Start an agent session in this directory and run `/start`

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
| SQLite-first | `disabled` (enabled once extraction has run) |
| Last extraction | not run |
| Extraction scope | not run (intended: `deep-rts`) |

---

## Update Log

| Date | Changes |
|------|---------|
| 2026-11-14 | Consolidated into metarepo (v0.0.1): old/new split, toolbox v3.3.1, harness-agnostic AGENTS/CONTEXT |
