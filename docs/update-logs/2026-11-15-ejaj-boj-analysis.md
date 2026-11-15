# Update: ejaj-boj added as a third source and analysed

**Date**: 2026-11-15
**Changed by**: AI agent (Claude), on behalf of the repo owner
**Topic**: `ejaj-boj` (the owner's earlier parametric-RTS project) registered in the metarepo and analysed
**Trigger**: owner request: "add ejaj-boj as a third thing in the metarepo and analyze it"
**Method**: quantum-toolbox `arch-analysis` + `code-graph` skills v1.0 (toolbox v3.3.1). The skills' interactive dialogue was answered by the analyst: single repo, docs dir `docs/ejaj-boj/`, Mermaid, unified SQLite, all outputs.

---

## Files Changed

| File | Change |
|------|--------|
| `sources/pins.env`, `sources/urls.md` | ejaj-boj registered (SSH URL, pinned `fde9d3c`) |
| `scripts/bootstrap-sources.sh` | clones and pins ejaj-boj (no patches; its submodules are not initialised); verified idempotent (two consecutive runs) |
| `scripts/cg-ejaj-boj.py`, `scripts/cg-ejaj-boj-reports.py` | created: Python (`ast`) + JavaScript (tree-sitter) extraction; View 09 and three reports |
| `scripts/cg-pyan-crosscheck.py` | unchanged; run with the repo argument `ejaj-boj` |
| `scripts/requirements-analysis.txt` | added `tree-sitter-javascript==0.25.0` |
| `docs/ejaj-boj/architecture-docs/` | created: `index.md`, `analysis/01-07`, `09-code-graph.md`, `reports/{findings-summary,entry-point-map,dead-code,sqlite-cookbook}.md` |
| `specs/analysis-manifest.json` | extended with `perRepo.ejaj-boj` under `arch-analysis` and `code-graph`, two history entries; validated against the toolbox schema |
| `code/ejaj-boj/` | gitignored clone at `fde9d3c`; `code_graph.sqlite` generated inside it and excluded locally via `.git/info/exclude` |
| `AGENTS.md`, `CONTEXT.md`, `README.md` | synced (three codebases) |
| `docs/general/*`, `docs/roadmap/ROADMAP.md` | ejaj-boj evidence recorded; Q10 updated |
| git tag `END-OF-deep-rts-RESEARCH` | created locally on `8c13321`, the commit before the metarepo consolidation (not pushed) |

---

## Key Findings

- **It runs**: 456 tests pass in 3.2 s from a fresh clone with current unpinned dependencies; a match plays headless at about 2,670 ticks/s per core.
- Real defects: a tick exception leaves the engine permanently `running`; the fog protocol breaks for late-joining player views; tie goes to player 1; the full map is sent every tick (97% of each frame); four client libraries are never imported by the page.
- Docs: 54% claim accuracy (36 claims), right about structure, wrong about counts and defaults.
- Code graph: 271 nodes, 326 edges, 0 cycles, 29 dead-code candidates; project-internal resolution 85.5% typed, 97.2% including unique-name matches; pyan3 cross-check 85.6% agreement (all 20 pyan3-only edges are false).
- CC0 sprite provenance (Tiny Swords, Pixel Frog) recorded in ejaj-boj's `CREDITS.md`.

## Deviations from the skills

- Python graph built with `ast` + own resolution (tier 2), pyan3 run as a cross-check only; the JavaScript graph uses tree-sitter. No type checker (pyright) was run.
- A heuristic `name-match` edge type (unique method names) is used where bare `list` annotations hide element types; it is reported separately in the scorecard.
- Tests are outside the graph; the dead-code report lists test references per candidate.
- `sre-hot-paths.md` not generated (needs SRE view 08).
- Mermaid diagrams were not rendered or validated (no renderer available).
- No browser run: Playwright e2e, the visual client and `file://` behaviour were not tested.
- The manifest schema has one entry per artifact type, so the second repo is recorded under `perRepo` (the schema allows additional properties).
