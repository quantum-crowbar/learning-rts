# Technology Manifest: ejaj-boj

**Analysis date**: 2026-11-15 · **Commit**: `fde9d3c` (branch `master`, 111 commits, 2026-03-06 to 2026-03-21, two author names for the same person) · Labels: *ran* = executed, *graph* = code graph, *read* = source reading.

## Summary

| Item | Value |
|------|-------|
| What it is | "Parametric RTS": two AI agents, each configured by a parameter dict, fight autonomously; the human only tunes parameters and watches (`AGENTS.md`, `CONTEXT.md`) |
| Server | Python 3.12, FastAPI + asyncio, one in-memory game, 10 ticks/s game loop, WebSocket broadcast |
| Client | Vanilla JavaScript ES modules + HTML5 Canvas 2D, no build step, no framework; `client/index.html` (1,894 lines) + 10 `client/lib/*.mjs` |
| Persistence / auth / external services | none / none / none |
| Own code size | 2,767 lines server Python, 98 lines scripts, 1,894 lines `index.html`, 1,203 lines client libs (plus 543 in `test-pure.mjs`); 5,434 lines Python tests and 471 lines JS tests *(counted with `wc`)* |
| Game content | 40×30 map, 4 unit kinds (worker, knight, archer, scout), 2 building kinds (town hall, barracks), 2 resources (**wood and stone; no gold**), fog of war, win by destroying the enemy town hall |
| Tests | 456 pytest tests pass, 1 skipped (3.2 s, *ran*); 142 of 143 client pure-JS tests pass (*ran*); Playwright e2e not run (needs a browser) |
| Runs | **Yes**: imports cleanly from a fresh clone and plays complete matches headless (*ran*) |

## Languages

| Language | Where | Lines | Notes |
|----------|-------|-------|-------|
| Python 3.12 | `server/` (16 files), `scripts/setup_assets.py`, `tests/` | 2,865 prod / 5,434 tests | `pyproject.toml` requires `>=3.12`; run with 3.12.3 here |
| JavaScript (ES modules) | inline `<script type="module">` in `client/index.html`, `client/lib/*.mjs`, Playwright specs | ~3,100 / 471 tests | 134 call-graph nodes (*graph*) |
| HTML/CSS | `client/index.html` (the same file) | within the 1,894 lines | markup and styles are inline |
| Bash | `run-crew.sh` | 7.5 KB | AI-crew runner, not game code; not analysed |
| Markdown | 53 files | n/a | specs, phase specs, roadmap, AI-crew logs: the project is documentation-heavy |

## Frameworks and libraries

| Name | Role | Declared in | Version constraint |
|------|------|-------------|--------------------|
| FastAPI | HTTP + WebSocket app | `server/requirements.txt` | none |
| uvicorn | ASGI server | same | none |
| websockets | WS transport for uvicorn | same | none |
| pydantic | `StartRequest` body model (comes with FastAPI) | transitive | n/a |
| httpx | HTTP client for API tests | same file (**test dependency in the runtime file**) | none |
| pytest, pytest-asyncio | test runner | same file | `pytest-asyncio>=0.23` |
| @playwright/test | browser e2e | `package.json` (devDependency) | `^1.44.0` |

Resolved today in a scratch environment (*ran*): fastapi 0.163.0, starlette 1.10.0, uvicorn 0.54.0, httpx 0.28.1, websockets 17.4, pydantic 2.14.3, pytest 9.2.0, pytest-asyncio 1.5.0. Nothing is pinned, so these are not necessarily what it was developed against; the test suite passes with them.

## Infrastructure and build

| Item | State |
|------|-------|
| Dockerfile | `python:3.12-slim`, copies `server/` and `client/`, `pip install -r server/requirements.txt` (so **pytest and httpx ship in the image**), serves on 8080 |
| CI | none (`CONTEXT.md`: "CI/CD: None"; no `.github`, no pipeline files) |
| Deployment | `CONTEXT.md` recommends Railway; no Railway configuration is in the repo |
| Lockfiles | none for Python; `package-lock.json` exists locally but is **untracked** |
| Licence | **no LICENSE file** in the repository |
| AI tooling (out of scope) | submodules `.quantum-toolbox` (v2.5.0-27, older than this metarepo's 3.3.1) and `.quantum-crew` (v1.0.0-69), plus `crew/`, `.local-skills/`, `run-crew.sh` |

## Assets

34 PNG files under `client/assets/` (Tiny Swords terrain, knights, trees, plus `sprites/black|yellow`). `CREDITS.md` credits two packs by Pixel Frog, **both CC0** ("Tiny Swords Free Pack" and "Enemy Pack"). Whether every PNG under `client/assets/` comes from those packs is not recorded; the source packs (`specs/sprite/`) are gitignored.

## Documentation gaps

- No licence, no CI, no lockfile, no deployment configuration despite the documented Railway target.
- `server/requirements.txt` mixes runtime and test dependencies.
- See [04](04-documentation-audit.md) for the accuracy of the existing docs.
