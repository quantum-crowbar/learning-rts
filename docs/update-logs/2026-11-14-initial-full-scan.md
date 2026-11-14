# Update: Initial full scan of deep-rts (old engine)

**Date**: 2026-11-14
**Changed by**: AI agent (Claude), on behalf of the repo owner
**Topic**: `deep-rts` initial full scan
**Trigger**: first analysis after the v0.0.1 metarepo consolidation (old/new split, quantum-toolbox v3.3.1 adopted)
**Method**: quantum-toolbox `arch-analysis` + `code-graph` skills v1.0 (toolbox v3.3.1)

---

## Files Changed

| File | Change |
|------|--------|
| `docs/architecture-docs/index.md` | created |
| `docs/architecture-docs/analysis/01-…07-*.md`, `09-code-graph.md` | created (View 09 generated from SQLite) |
| `docs/architecture-docs/reports/{findings-summary,entry-point-map,dead-code,sqlite-cookbook}.md` | created |
| `specs/analysis-manifest.json` | created: `artifacts.code-graph`, `artifacts.arch-analysis`, history |
| `scripts/cg-extract.py`, `cg-pyan-crosscheck.py`, `cg-reports.py` | created: reproducible extraction and report generation |
| `code/deep-rts/code_graph.sqlite` | generated (gitignored; regenerate with the manifest's command) |
| `CONTEXT.md`, `AGENTS.md`, `README.md` | synced (Post-Work Hook) |

---

## Key Findings

- The project does not build; the Python wrapper cannot be imported; a webhook token is committed (see `reports/findings-summary.md`, P0).
- Six silent RL-contract defects in the C++ engine (boolean reward, stale observation channels, episode-end hook, wall-clock step gate, sliced players, copy-spawn).
- Old documentation is 50% accurate (34-claim ledger); correct about structure, wrong about usage.
- Code graph: 502 nodes, 732 edges, 0 function-level cycles, one 10-class strongly connected cluster; C++ project-internal call resolution 97.4%, Python 37.0%.
- Corrections to earlier statements in this repo: CONTEXT.md claimed the bad vcpkg spec was "generated from `vcpkg_dependencies.txt`" (the log does not support that), and "14 open issues" (GitHub counts 3 PRs in that number).

## Deviations from the skills (and why)

| Skill step | Deviation |
|------------|-----------|
| code-graph 0.1: tier-1 tool first | pyan3 was run first for Python; kept as a cross-check, not merged (47% agreement with tree-sitter, visible false edges). C++ has no tier-1 option here (no clang; project does not configure). |
| code-graph 0.0.x / arch-analysis 0.1, 0.4 interactive prompts | answered by the agent with defaults suited to the metarepo (recorded in `index.md`), because the owner asked for the whole analysis without a dialogue. |
| code-graph 4D: commit SQLite | SQLite stays **gitignored** (it lives under `code/`, which is gitignored; matches the toolbox's own AGENTS template comment); the extractor scripts are committed so it is reproducible. |
| arch-analysis 9.2: `updateHistory` | the manifest schema forbids that key (root `additionalProperties: false`); `history[]` is used, with the update-log path in `notes`. (Toolbox doc/schema inconsistency.) |
| code-graph reports | `sre-hot-paths.md` not generated: requires View 08, which arch-analysis does not produce. |
| Schema superset | extra columns/tables in the SQLite (language, entry_type, class_name, class_hierarchy, pybind tables): documented in the cookbook. |

## Not done / limits

- The engine was never built or run; throughput and runtime behaviour claims are by code reading unless marked *ran*.
- C++ dependency vulnerabilities not assessed (no scanner).
- CMake and Bash files not in the call graph (deliberate; named in the scorecard).
- `learning-rts` not analysed (no code yet).

---

## Repos Examined at HEAD

| Repo | Key files read |
|------|---------------|
| `deep-rts` @ `6bfbfd5` | `Game.h/.cpp`, `Constants.h`, `Unit.cpp`, `Player.cpp`, `Scenario.cpp`, `UnitManager.cpp`, `ResourceLoader.cpp`, `StateManager.cpp`, `main.cpp`, `bindings/*`, `DeepRTS/python/*`, `CMakeLists.txt`, `vcpkg_install.sh`, `setup.py`, `pyproject.toml`, requirements, CI/Docker files, 10 map files |
