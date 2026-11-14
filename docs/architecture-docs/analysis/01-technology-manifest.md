# Technology Manifest: deep-rts

**Analysis Date**: 2026-11-14 · **Commit**: `6bfbfd5` (upstream HEAD, 2023-05-16) + `patches/deep-rts/0001` · **Source**: `code/deep-rts/`

## Summary

| Metric | Value |
|--------|-------|
| Primary language | C++17 (engine), ~8,970 own lines in 113 files |
| Secondary language | Python (wrapper + examples), 1,479 package lines + 1,175 example lines |
| Vendored code (excluded from graph) | `JPS.h` 1,538 lines, `ndarray_converter.cpp` 364 lines |
| Binding layer | pybind11 → native module `libdeeprts`, exposed as `DeepRTS.Engine` |
| Build | CMake ≥ 3.17 + vcpkg (two disagreeing mechanisms) + setuptools |
| Runtime services | **none**: no DB, no network, no threads in the engine |
| Persistence | **none**: all state in memory; assets embedded in the binary |
| Builds today | **No** (see [05](05-dependency-health.md) and CONTEXT.md) |

## Languages

| Language | Version | Where | Lines (own) | Evidence |
|----------|---------|-------|-------------|----------|
| C++ | C++17 (`CMAKE_CXX_STANDARD 17`, required) | `src/`, `include/DeepRTS/`, `bindings/` | 8,974 | `CMakeLists.txt:29-31` |
| Python | `>=3.8` declared; CI matrix 3.5-3.8; README says 3.9.1 (three different answers) | `DeepRTS/python/`, `examples/` | 2,654 | `pyproject.toml:4`, `.travis.yml:11-14`, README |
| CMake | 3.17+ | `CMakeLists.txt`, `cmake/*.cmake` | n/a | `CMakeLists.txt:1` |
| Bash | n/a | `vcpkg_install.sh`, `build.sh` (macOS-only: calls `sw_vers`), `install.sh` (added by our patch) | n/a | |
| JSON | Tiled map format | `DeepRTS/python/assets/maps/*.json` (10 maps), `tile_properties.json` | n/a | |

## Frameworks

| Framework | Role | Version (pinned baseline → current vcpkg) | Notes |
|-----------|------|-------------------------------------------|-------|
| pybind11 | C++↔Python bindings, trampolines | 2.10.3 → 3.1.0 | also `pybind11::embed` for the C++ executable (`EMBEDDED=1`) |
| xtensor (+xsimd) | observation tensor `StateType = xt::xarray<double>` shape `(W,H,10)` | 0.24.3 → 0.27.2 (xsimd 9.0.1 → 14.3.0) | header layout changed between these (`xtensor/containers/`); see [05](05-dependency-health.md) |
| xtensor-python | numpy bridge for the state tensor | fetched via CPM, `GIT_TAG master` (patched; upstream used `0.25.3`) | unpinned in our patch |
| Blend2D | native 2D rendering | 2022-12-31 → 2025-03-08 | no vcpkg version pin in the manifest |
| OpenCV | `cv::Mat` as the frame type (25 uses), `imencode/imdecode`, `inRange`, `Scalar`; `highgui` for demo windows | 4.7.0 → 4.14.0 | CMake marks `opencv_core`/`opencv_highgui` "todo remove" (`CMakeLists.txt:~165`) |
| pygame | Python-side GUI (`gui.py`) | `==2.0.0` pinned (2020-10-28); latest 2.6.1 | **dual GUI**: Blend2D (C++) and pygame (Python) |
| gym | `observation_space`/`action_space` in `game.py` | unpinned; last release 0.26.2 (2022-10-04), unmaintained | |

## Libraries

### Core (C++, via vcpkg: `vcpkg_dependencies.txt`)

| Library | Purpose | Pinned baseline (2023.04.15) | vcpkg master (2026-11-14) |
|---------|---------|------------------------------|---------------------------|
| spdlog | logging (3 call sites) | 1.11.0 | 1.17.0 |
| effolkronium-random | RNG (`Random::get`) | 1.4.1 | 1.5.0 |
| xtensor[xsimd] | tensors | 0.24.3 | 0.27.2 |
| nlohmann-json | map/tile JSON parsing | 3.11.2 | 3.12.0 |
| opencv | frames | 4.7.0 | 4.14.0 |
| blend2d | rendering | 2022-12-31 | 2025-03-08 |
| pybind11 | bindings (added by our patch) | 2.10.3 | 3.1.0 |

### Embedded assets

| Asset | Mechanism | Evidence |
|-------|-----------|----------|
| maps, textures (27 PNG, 6 XCF sources), fonts, audio (4.8 MB total) | CMRC resource library `DeepRTSAssets`, **embedded in the binary** | `CMakeLists.txt:174-181` |
| runtime lookup | embedded first, then falls back to the filesystem next to the package | `src/ResourceLoader.cpp:47-85` |

### Python (declared)

| File | Packages |
|------|----------|
| `requirements.txt` | pybind11, `pygame==2.0.0`, numpy, cython, gym |
| `examples/requirements.txt` | ray[rllib], torch, requests, setproctitle, psutil, **tensorflow-gpu**, tensorboard, plotly, **`git+https://github.com/vitchyr/viskit.git`**, aiohttp, tensorboardX, pygments, pandas, uvicorn, pygame |

## Infrastructure Dependencies

None. The engine is a single-process, single-thread library. No database, cache, queue or network I/O. Of the 15 packages in `examples/requirements.txt`, `requests`, `aiohttp`, `uvicorn`, `psutil`, `setproctitle`, `plotly`, `pandas`, `ray` and `viskit` are not imported by any file in the repo (grep over all `*.py`); the only TensorFlow reference is a fallback import in `examples/old/util.py:9`.

## Build & DevOps Tools

| Tool | Role | State |
|------|------|-------|
| CMake ≥ 3.17 + CPM | configure; fetches xtensor-python | works up to `find_package(xtensor)` |
| PMM + vcpkg `REVISION 2023.04.15` | pinned dependency resolution **inside CMake** (`CMakeLists.txt:107-117`) | used **only when no vcpkg toolchain file is passed** (`if(NOT (CMAKE_TOOLCHAIN_FILE MATCHES "vcpkg"))`); `setup.py` always passes one, so pip builds never use the pin |
| `vcpkg_install.sh` (called by `setup.py`) | clones **vcpkg master**, `git pull`s on re-run, installs `vcpkg_dependencies.txt` unpinned; also runs `apt-get install` (needs root) | non-reproducible; this is the path that failed in `build.log` |
| setuptools + `setup.py` `CMakeBuild` | `pip install .` | fails (above) |
| cibuildwheel | `cp3{8,9,10,11}-musl*`, manylinux_2_28; macOS x86_64/arm64 | config present; no workflow runs it |
| Travis CI | `.travis.yml`: Python 3.5-3.8, `pytest --pyargs DeepRTS` | stale; Python 3.5-3.7 are below `requires-python`; also embeds a webhook secret (see [05](05-dependency-health.md)) |
| GitHub Actions | `test_vcpkg_install.yaml` | **broken**: runs `./vcpkg/vcpkg_install.sh`, but the script is at the repo root (`.github/workflows/test_vcpkg_install.yaml:23-24`); uses `actions/checkout@v2` |
| Docker | `Dockerfile` | **stale**: `ubuntu:18.04` (EOL), clones `UIA-CAIR/DeepRTS`, runs `drts/coding/main.py` which does not exist (`Dockerfile:5,15`) |
| Doxygen | `Doxyfile.in`, `BUILD_DOCS=ON` | never generated in CI |
| Compiler flags | Release: `-Ofast -ffast-math -Wall -Wno-class-memaccess` | `-ffast-math` relaxes IEEE semantics (NaN/inf checks may be optimised away) |

### CMake targets

| Target | Description |
|--------|-------------|
| `libdeeprts` | pybind11 module (when `PYTHON_BUILD` defined) |
| `DeepRTSLib` | static library (when `PYTHON_BUILD` **not** defined) |
| `DeepRTSGame` | executable from `src/main.cpp` (embedded Python) |
| `DeepRTSAssets` | CMRC asset library |
| `doc_doxygen` | docs |

## Documentation Gaps

- No document states which of the **two** dependency-resolution paths is canonical (PMM-pinned vs `vcpkg_install.sh` master).
- Python version support is stated three different ways.
- The Python wrapper's real status (cannot be imported) is documented nowhere; see [04](04-documentation-audit.md) DISC-001.
- The vendored files are not marked as vendored (`ndarray_converter` has no provenance note in-tree).
