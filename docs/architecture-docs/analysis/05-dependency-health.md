# Dependency Health: deep-rts

**Analysis Date**: 2026-11-14 · **Method**: manifests read (`vcpkg_dependencies.txt`, `CMakeLists.txt`, `requirements.txt`, `examples/requirements.txt`, `pyproject.toml`); vcpkg port versions fetched from `microsoft/vcpkg` at tag `2023.04.15` and at `master`; PyPI JSON API for currency; OSV API for the one exactly-pinned package.

## Executive Summary

| Area | Status | Notes |
|------|--------|-------|
| Build reproducibility | 🔴 | two resolution paths that disagree; the one `pip` uses clones **vcpkg master** (unpinned) |
| Currency (C++) | 🔴 | pinned baseline is 3.5 years old; every library is 1-3 minor/major lines behind |
| Currency (Python) | 🟡 | `pygame==2.0.0` pinned 4 years behind; `gym`, `tensorflow-gpu` unmaintained |
| Known vulnerabilities | ⚪ not assessed for C++ | no scanner available for vcpkg ports; Python: 0 advisories for the single exact pin |
| Secrets | 🔴 | a Discord webhook URL (with token) is committed in `.travis.yml:28` |
| Upstream maintenance | 🔴 | `pa-research/deep-rts` has had no commit since 2023-05-16 |

The most consequential finding is an internal inconsistency, not a CVE: **our own build-fix patch targets a different xtensor than the pinned baseline provides** (below).

## Package Inventory

### C++ (vcpkg), from `vcpkg_dependencies.txt`

| Package | Pinned baseline (PMM `2023.04.15`) | vcpkg master (2026-11-14) | Gap |
|---------|-------------------------------------|---------------------------|-----|
| spdlog | 1.11.0 | 1.17.0 | 6 minor |
| effolkronium-random | 1.4.1 | 1.5.0 | 1 minor |
| xtensor | 0.24.3 | 0.27.2 | 3 minor (0.x: breaking) |
| xsimd (via `xtensor[xsimd]`) | 9.0.1 | 14.3.0 | 5 major |
| nlohmann-json | 3.11.2 | 3.12.0 | 1 minor |
| opencv | 4.7.0 | 4.14.0 | 7 minor |
| blend2d | 2022-12-31 | 2025-03-08 | ~26 months |
| pybind11 | 2.10.3 | 3.1.0 | 1 major |

CPM-fetched: `xtensor-python`: upstream tag `0.25.3`, **our patch changed it to `master`** (`patches/deep-rts/0001`).

### Python

| Package | Where | Constraint | Latest (PyPI) | Note |
|---------|-------|------------|---------------|------|
| pygame | both files | `==2.0.0` (2020-10-28) | 2.6.1 (2024-09-29) | OSV: **0 advisories** for 2.0.0 |
| gym | `requirements.txt` | none | 0.26.2 (2022-10-04) | no release in 4 years |
| numpy | both | none | 2.5.4 (requires Python ≥3.12) | build also needs numpy headers |
| cython | `requirements.txt` | none | 3.3.1 | not imported; the only trace is a declared-but-unimplemented `PyGUI::initCython()` (`PyGUI.h:24`) |
| pybind11 | `requirements.txt`, build-system | none | 3.1.0 | also a vcpkg dependency: two sources of truth |
| torch, ray[rllib], tensorflow-gpu, tensorboard(X), plotly, pandas, requests, aiohttp, uvicorn, psutil, setproctitle, pygments | `examples/requirements.txt` | none | current | `tensorflow-gpu` latest is 2.12.0 (2023-01-24); **9 of these are imported by no file** (see [01](01-technology-manifest.md)) |
| viskit | `examples/requirements.txt` | `git+https://github.com/vitchyr/viskit.git` | n/a | **unpinned VCS dependency**; not imported anywhere |

## Version Currency: the xtensor mismatch

`include/DeepRTS/Game.h:19` (patched) includes `<xtensor/containers/xarray.hpp>`. That directory layout is from xtensor ≥ 0.26 (the pinned baseline has 0.24.3, where the header is `<xtensor/xarray.hpp>`). Consequences:

- The patched tree only compiles against the **vcpkg-master** path (xtensor 0.27.2, the path `setup.py` uses).
- The **PMM-pinned** path (xtensor 0.24.3) would fail on that include. Upstream's source used the old header and compiled with 0.24.3; the two states are mutually exclusive.
- `xtensor-python` was moved to `master` to track xtensor; there is no commit or tag recorded for it.

Pick one path and pin it; do not ship both. (Observed in `build.log`: the pip path installed `spdlog 1.17.0`, `fmt 12.1.0`, i.e. vcpkg master.)

## Vulnerability Report

| Scope | Result |
|-------|--------|
| `pygame==2.0.0` | OSV query: 0 advisories |
| Unpinned Python packages | not assessed: the vulnerable surface depends on whichever version resolves at install time |
| C++ libraries (8 above) | **not assessed.** No scanner for vcpkg ports was available; OSV does not index them by vcpkg name. The versions in the table are the input for anyone running a scanner |
| Vendored `JPS.h`, `ndarray_converter` | not assessed; provenance of `ndarray_converter` is not recorded in-tree |

### Secret in source control

`.travis.yml:28` contains `webhooks: https://discordapp.com/api/webhooks/<id>/<token>/travis`. A Discord webhook URL carries its own credential: anyone with the repository can post to that channel. The repository is public (upstream) and the line has been there since 2017-04-06 (first commit containing it, `git log -S`). **Treat it as compromised and delete the webhook in Discord.** (The token is deliberately not reproduced here.)

## Maintenance Status

| Component | Status | Evidence |
|-----------|--------|----------|
| deep-rts upstream | **dormant** | last commit 2023-05-16; 14 open items (GitHub counts PRs among them), of which 3 are dependabot PRs for a webclient directory that does not exist in the tree; repo renamed `cair/DeepRTS` → `pa-research/deep-rts` |
| gym | unmaintained | last release 2022-10-04 (successor project exists; not evaluated here) |
| tensorflow-gpu | no release since 2023-01-24 | PyPI |
| pygame 2.0.0 | 4 releases/years behind | PyPI |
| CI | non-functional | [04](04-documentation-audit.md) DISC-018 |

## License Inventory

| Component | License | Source of this fact |
|-----------|---------|---------------------|
| deep-rts | MIT | `LICENCE.md` |
| spdlog, effolkronium-random | MIT | vcpkg port output in `build.log` |
| `JPS.h` (vendored) | public domain / WTFPL / CC0 | header text (`JPS.h:1-12`) |
| xtensor, nlohmann-json, OpenCV, Blend2D, pybind11 | not re-verified here | read each port's `copyright` before redistributing wheels |
| `ndarray_converter` (vendored) | **unknown**: no licence header, no provenance | file inspection |

## Risk Matrix

| Risk | Likelihood | Impact | Rating |
|------|------------|--------|--------|
| Build cannot be reproduced (vcpkg master + `git pull`, two paths, xtensor mismatch) | Certain | High | 🔴 |
| Leaked webhook token abused | Possible | Low-Medium | 🟡 |
| Unpatched C++ dependency CVEs (3.5-year-old baseline) | Likely | Unknown | 🟡 (unassessed) |
| `numpy` 2.x vs the vendored `ndarray_converter` / xtensor-python C-API usage | Plausible | High | 🟡 (not tested: no build) |
| Abandoned upstream: no fixes will arrive | Certain | Medium | 🟡 |
| `-Ofast -ffast-math` changes numeric semantics (NaN/inf, reassociation) | Certain | Low-Medium | 🟡 |

## Recommended Actions

### Immediate (this week)

1. Delete the Discord webhook and remove `.travis.yml:28`.
2. Decide the one dependency path. If deep-rts is kept: use vcpkg **manifest mode** with a pinned baseline and `vcpkg_dependencies.txt` replaced by `vcpkg.json`; if the patched xtensor include is kept, the baseline must provide xtensor ≥ 0.26.

### Short-term

1. Pin `xtensor-python` to a tag/commit compatible with the chosen xtensor.
2. Drop unused Python dependencies and the `viskit` VCS dependency; pin the rest.
3. Run a C++ SCA scan (e.g. OSV-Scanner on a generated SBOM) on the chosen baseline.

### Long-term

1. Evaluate shrinking the `opencv` dependency: usage is `cv::Mat` (25 sites), `imencode`/`imdecode`, `inRange`, `Scalar`, and `highgui` demo windows; CMake itself marks `opencv_core`/`opencv_highgui` "todo remove".

## Dependency Tree Concerns

- **Duplicate sources of truth**: pybind11 in three places (`vcpkg_dependencies.txt`, `requirements.txt`, `pyproject.toml` build-system); pygame in both requirements files.
- **Unpinned by design**: `vcpkg_install.sh` does `git clone` / `git pull` on vcpkg master, then installs ports at whatever version master has that day.
- **Root-requiring installer**: `vcpkg_install.sh` runs `apt-get install` / `dnf` / `pacman` (permission error in `build.log`); a `pip install` must not need root.
