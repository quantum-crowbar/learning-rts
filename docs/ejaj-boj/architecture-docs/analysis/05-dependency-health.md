# Dependency Health: ejaj-boj

**Analysis date**: 2026-11-15 · **Method**: manifests read (`server/requirements.txt`, `pyproject.toml`, `package.json`, `Dockerfile`); packages resolved today in a scratch virtual environment outside the repo; advisories queried from OSV (`api.osv.dev`, package names and versions only) (*fetched*).

## Executive summary

| Area | Status | Notes |
|------|--------|-------|
| Build reproducibility | 🟡 | nothing is pinned and there is no lockfile, but the project **installs and passes 456 tests with today's latest versions** (*ran*) |
| Currency | 🟢 | everything resolves to current releases because nothing is pinned |
| Known vulnerabilities | 🟢 for the 8 Python packages at the versions resolved today: 0 advisories each (*fetched*). The npm dev dependency was not scanned (`node_modules` is not part of the clone) |
| Secrets | 🟢 | grep for key/secret/password/token patterns over `server/`, `client/`, `scripts/`, `Dockerfile`, `package.json` found nothing |
| Licence | 🔴 | the repository has **no LICENSE file**; asset licence is documented (CC0) |
| Supply chain / process | 🟡 | test tools in the production image; no CI |

## Package inventory

### Python (`server/requirements.txt`)

| Package | Constraint | Resolved today | Role | Advisories (OSV) |
|---------|------------|----------------|------|------------------|
| fastapi | none | 0.163.0 | runtime | 0 |
| uvicorn | none | 0.54.0 | runtime | 0 |
| websockets | none | 17.4 | runtime (WebSocket transport) | 0 |
| httpx | none | 0.28.1 | **test only** | 0 |
| pytest | none | 9.2.0 | **test only** | 0 |
| pytest-asyncio | `>=0.23` | 1.5.0 | **test only** | 0 |
| starlette, pydantic | transitive | 1.10.0, 2.14.3 | runtime (via FastAPI) | 0 |

`pyproject.toml` declares only `name`, `requires-python = ">=3.12"` and pytest settings; it lists no dependencies, so there are two partial sources of truth.

### JavaScript

| Package | Constraint | Role |
|---------|------------|------|
| @playwright/test | `^1.44.0` | e2e tests (devDependency); `package-lock.json` exists locally but is **untracked** |

The client itself has **no third-party JavaScript** and no build step.

### Compatibility signals (*ran*)

- `tests/api/test_api_3_1.py` imports `starlette.testclient`, which now warns that using it with `httpx` is deprecated ("install `httpx2` instead"). A future Starlette release could break that test file; the suite passes today.
- `pytest-asyncio` 1.5.0 warns that the default fixture loop scope is unset (`PytestDeprecationWarning`); set `asyncio_default_fixture_loop_scope` in `pyproject.toml` to silence it.

## Version currency

Not meaningful for unpinned packages: each resolves to the newest release. The risk is the opposite of staleness: **an upgrade can break a fresh install without any change to the repository**. It did not, as of today.

## Vulnerability report

| Scope | Result |
|-------|--------|
| 8 Python packages at today's resolved versions | 0 advisories in OSV |
| `@playwright/test` and its browsers | not scanned |
| Python base image `python:3.12-slim` | not scanned (no image build was run) |
| Client-side code | no third-party JS to scan |

### Application-level security observations (not CVEs)

| # | Observation | Evidence | Impact |
|---|-------------|----------|--------|
| S1 | **No authentication; CORS allows every origin, method and header** | `main.py:54-59` | any web page can call `POST /start` and `POST /reset` on a reachable instance; if deployed publicly (the docs recommend Railway) anyone can reset or restart the match |
| S2 | **No input validation on agent parameters** | `StartRequest.agent0: dict[str, Any]` | a bad value kills the game loop and leaves the engine stuck in `running` (*ran*, see [07](07-error-handling.md)); an extreme value such as a huge `max_workers` is accepted |
| S3 | One global engine, no per-client isolation | module-level `engine` | all clients share and can interfere with one match |
| S4 | Fog is not a security boundary | see [02](02-interface-specification.md) | player views receive enemy building state in explored tiles, tile resource amounts and enemy goals |

For a local single-user tool S1-S4 are acceptable; they matter the moment the server is exposed or the planned PvP lobbies (Phase 8) are built.

## Maintenance status

| Component | Status |
|-----------|--------|
| ejaj-boj | active: 111 commits in 15 days (2026-03-06 to 2026-03-21), then nothing; owner's own project |
| FastAPI, uvicorn, websockets, pytest | actively maintained upstream projects |

## Licence inventory

| Component | Licence | Source |
|-----------|---------|--------|
| ejaj-boj code | **none declared** (no LICENSE) | file listing |
| Tiny Swords Free Pack, Enemy Pack (Pixel Frog) | CC0 | `CREDITS.md` (author-stated, with source URL) |
| FastAPI, uvicorn, websockets, pydantic, httpx, pytest | not re-verified here (all are permissively licensed projects as far as I know; check before redistributing) | |

## Risk matrix

| Risk | Likelihood | Impact | Rating |
|------|------------|--------|--------|
| A new release of FastAPI/Starlette/pytest breaks a fresh install | Possible | Medium | 🟡 |
| Public deployment without authentication | Possible (Railway is the documented target) | Medium | 🟡 |
| Missing licence blocks reuse or publication | Certain if published | Medium | 🟡 |
| Test dependencies in the production image | Certain | Low | 🟢 |

## Recommended actions

**Immediate**: add a licence; pin Python versions (a `requirements.lock` or `uv`/`pip-tools` output) and split runtime from test dependencies.
**Short-term**: validate `/start` parameters (reject unknown keys and wrong types, return 422); decide the deployment story or drop the Railway claim; add CI that runs the 456 tests.
**Long-term**: if the project is reused as a base, decide what to do about the global engine and unauthenticated control endpoints.
