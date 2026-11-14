#!/usr/bin/env python3
"""
cg-reports.py - render View 09 + code-graph reports + manifest entry from code/<repo>/code_graph.sqlite
(quantum-toolbox code-graph skill v3.3.1, Phase 4B.5 / 4C / View 09 templates).

Writes:
  docs/architecture-docs/analysis/09-code-graph.md
  docs/architecture-docs/reports/entry-point-map.md
  docs/architecture-docs/reports/dead-code.md
  docs/architecture-docs/reports/sqlite-cookbook.md
  specs/analysis-manifest.json   (artifacts.code-graph only; other artifacts preserved)

Usage: venv/bin/python scripts/cg-reports.py [repo]
"""
import collections
import datetime
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

METAROOT = Path(__file__).resolve().parent.parent
REPO = sys.argv[1] if len(sys.argv) > 1 else "deep-rts"
ROOT = METAROOT / "code" / REPO
DB = ROOT / "code_graph.sqlite"
TOOLBOX = METAROOT / ".quantum-toolbox"
DOCS = METAROOT / "docs" / "architecture-docs"
TODAY = datetime.date.today().isoformat()

db = sqlite3.connect(DB)
q = lambda s, *a: db.execute(s, a).fetchall()
one = lambda s, *a: db.execute(s, a).fetchone()[0]
meta = {k: json.loads(v) for k, v in q("SELECT key, value FROM extraction_meta")}
sc = meta["scorecard"]
COMMIT = meta["commit"]
SQLITE_PATH = f"code/{REPO}/code_graph.sqlite"

N = one("SELECT COUNT(*) FROM nodes")
E = one("SELECT COUNT(*) FROM edges")
ENTRIES = one("SELECT COUNT(*) FROM nodes WHERE is_entry_point=1")
DEAD = one("SELECT COUNT(*) FROM nodes WHERE is_dead_code=1")
CYCLES = one("SELECT COUNT(*) FROM view_cycles")
DYN = one("SELECT COUNT(*) FROM edges WHERE is_dynamic=1")
XL = q("SELECT a.language, b.language, COUNT(*) FROM edges e JOIN nodes a ON a.id=e.from_node "
       "JOIN nodes b ON b.id=e.to_node WHERE a.language!=b.language GROUP BY 1,2")
by_reason = dict(q("SELECT reason, COUNT(*) FROM unresolved_calls GROUP BY reason"))
for r in ("external-package", "missing-repo", "dynamic", "type-alias"):
    by_reason.setdefault(r, 0)

er = sc["edge_resolution"]


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def short(nid):
    # path:Qual.name -> Qual.name   (keep file for disambiguation if '#')
    return nid.split(":", 1)[1] if ":" in nid else nid


def loc_link(loc):
    f, ln = loc.rsplit(":", 1)
    return f"`{f}:{ln}`"


def mlabel(nid):
    return short(nid).replace("<", "").replace(">", "").replace('"', "'")


def sid(nid):
    return "n" + re.sub(r"[^A-Za-z0-9]", "_", nid)


def git_date(path):
    try:
        out = subprocess.check_output(["git", "-C", str(ROOT), "log", "-1", "--format=%cs", "--", path], text=True).strip()
        return out or "unknown"
    except Exception:
        return "unknown"


# ----- coverage numbers carried to the manifest -------------------------------------------------
cpp_pr, py_pr = er["by_language"]["cpp"]["resolution_pct_project_only"], er["by_language"]["python"]["resolution_pct_project_only"]
_bs = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "*.cmake", "CMakeLists.txt", "*.sh"], text=True).split()
gaps = [
    "learning-rts is not tracked yet (no remote; see sources/urls.md), so repoCoverage covers only the one tracked repo",
    f"languageCoverage 2/4: CMake and Bash (build/install scripts, {len(_bs)} files) are deliberately not extracted; tree-sitter-cmake/bash exist but those files are build tooling, not product call graph",
    "crossRepoMechanismCoverage n/a: single repo; the only cross-boundary mechanism (pybind11 Python<->C++) is resolved into call edges, not mechanism_edges",
    "no type-aware tool for C++ (clang absent; project does not configure: xtensor/vcpkg failure). tree-sitter + class-hierarchy analysis only: templates, overloads beyond arity and calls through auto-typed expression chains are not resolved",
    f"edgeResolutionCoverage is strict (all unresolved calls in the denominator). Excluding external-package calls (std/OpenCV/Blend2D/xtensor/pybind/torch/pygame): cpp {cpp_pr}%, python {py_pr}%",
    f"python: {er['by_language']['python']['by_reason']['type-alias']} calls stay type-alias after all 2.1.1 heuristics (untyped parameters in the examples and pygame-facing gui code); pyan3 tier-1 cross-check agrees with only {meta['pyan_crosscheck']['agreement_of_pyan']}% of its own edges (see 09-code-graph.md)",
    "SRE view 08 does not exist (arch-analysis does not produce it): reports/sre-hot-paths.md skipped",
    "vendored code excluded from the graph: include/DeepRTS/util/JPS.h (1538 lines), bindings/utilities/ndarray_converter.* ; calls into them are external-package",
]

# =================================================================================================
# 09-code-graph.md
# =================================================================================================
hot = q("SELECT id, location, fan_in, fan_out FROM view_hot_nodes WHERE fan_in>0 LIMIT 10")
fanout = q("SELECT id, location, fan_out FROM nodes ORDER BY fan_out DESC LIMIT 10")
cc = q("SELECT id, location, cyclomatic_complexity FROM view_complexity_hotspots LIMIT 10")
ncc = one("SELECT COUNT(*) FROM view_complexity_hotspots")
refactor = q("SELECT id, fan_in, cyclomatic_complexity, refactor_score FROM view_refactor_priority LIMIT 8")
dead_by_file_age = collections.Counter()
dead_rows = q("SELECT id, location, language FROM view_dead_code")
file_dates = {}
for _, loc, _ in dead_rows:
    f = loc.rsplit(":", 1)[0]
    file_dates.setdefault(f, git_date(f))
for _, loc, _ in dead_rows:
    d = file_dates[loc.rsplit(":", 1)[0]]
    if d == "unknown":
        dead_by_file_age["unknown"] += 1
    else:
        age = (datetime.date.fromisoformat(TODAY) - datetime.date.fromisoformat(d)).days
        dead_by_file_age[">1y" if age > 365 else ("<6m" if age < 183 else "6m-1y")] += 1

lines = []
w = lines.append
w("# Code Graph Analysis\n")
w(f"**Project**: deep-rts (old engine, pinned `{COMMIT}` + `patches/deep-rts/`)  ")
w(f"**Generated**: {TODAY}  ")
w("**Tool**: tree-sitter-cpp 0.23.4 + tree-sitter-python 0.25.0 (tier 2) with class-hierarchy analysis; pyan3 2.9.0 as tier-1 cross-check (Python)  ")
w(f"**Backend**: sqlite (`{SQLITE_PATH}`, gitignored; regenerate: `venv/bin/python scripts/cg-extract.py && venv/bin/python scripts/cg-reports.py`)\n")
w("---\n")
w("## Extraction Summary\n")
w("| Metric | Value |\n|--------|-------|")
w(f"| Functions / Methods | {N} (C++ {one('SELECT COUNT(*) FROM nodes WHERE language=?','cpp')}, Python {one('SELECT COUNT(*) FROM nodes WHERE language=?','python')}) |")
w(f"| Call Edges | {E} ({one('SELECT COUNT(*) FROM edges WHERE type=?','call')} call, {one('SELECT COUNT(*) FROM edges WHERE type=?','instantiates')} instantiates; {DYN} via virtual dispatch) |")
w(f"| Entry Points | {ENTRIES} |")
w(f"| Dead Code Candidates | {DEAD} ({pct(DEAD, N)}) |")
w(f"| Cycles Detected | {CYCLES} |")
w("| Extraction Method | static (tree-sitter, tier 2) |")
w("| Storage Backend | sqlite |")
w(f"| Source files analysed | {meta['files_cpp']} C++ (.cpp/.h/.hpp) + {meta['files_py']} Python |")
w(f"| Cross-language edges | {', '.join(f'{a}→{b}: {c}' for a, b, c in XL)} |\n")
w("> **Coverage Confidence**: **Medium-High for C++ project-internal calls, Medium for Python.** Static syntax-aware extraction (not AI inference), "
  "but no type checker: see the scorecard and gaps below. Virtual calls are resolved by class-hierarchy analysis (every override of the "
  "static receiver type's method), so `is_dynamic=1` edges are an over-approximation: the real target is one of the listed overrides.\n")
w("> **Scope decisions** (answers to the skill's interactive dialogue, chosen for this run): Targeted single repo `deep-rts`; unified SQLite graph; all outputs; "
  "tests excluded (`DeepRTS/python/tests/`); vendored code excluded (see gaps).\n")
w("---\n")
w("## Tooling (workflow 0.1)\n")
w("| Language | Tool | Tier | Why not tier 1 |\n|---|---|---|---|")
w("| C++ | `tree-sitter-cpp` + custom class-hierarchy / typed-variable / pybind resolution (`scripts/cg-extract.py`) | 2 | No type-aware tool usable: clang/clangd absent; the project does not configure (xtensor/vcpkg failure, see CONTEXT.md), so no `compile_commands.json` |")
pc = meta["pyan_crosscheck"]
w(f"| Python | `tree-sitter-python` + self/typed-variable/import/pybind resolution | 2 | pyan3 2.9.0 **was run first** (tier 1). It cannot see the pybind boundary and was imprecise here (details below), so it is kept as a cross-check, not merged |\n")
w("### pyan3 cross-check (Python, `DeepRTS/python` + examples)\n")
w("| | Count |\n|---|---|")
w(f"| pyan3 edges that map to a known node | {pc['pyan_edges_mapped']} (+{pc['pyan_edges_unmapped']} to external/unmapped targets) |")
w(f"| tree-sitter Python→Python edges | {pc['treesitter_py_to_py_edges']} |")
w(f"| Agree | {pc['agree']} ({pc['agreement_of_pyan']}% of pyan3, {pc['agreement_of_treesitter']}% of tree-sitter) |")
w(f"| pyan3-only | {pc['pyan_only']}, of which {pc['pyan_self_loops']} are self-loops (cause not investigated; `Game.__init__ → Game.__init__` is one, consistent with `super(Game, self).__init__` being resolved to the subclass itself) |")
w(f"| tree-sitter-only | {pc['treesitter_only']} (sampled: `Game → GUI`/`AbstractGUI` calls, `Game.__init__ → Config.__init__`; query `pyan_crosscheck` for all) |\n")
w("Verdict: pyan3's pyan-only edges include ones that are wrong on inspection (e.g. `Game.update`, `Game.view`, `Game.capture`, `Game.set_player` and `Game._render` are each reported as calling `Game.__init__`; none of them do), so treating pyan3 as ground truth would lower precision. All disagreements are in the `pyan_crosscheck` table.\n")
w("---\n")
w("## Coverage Scorecard\n")
w("Any metric below 100% must have a named reason in `stats.gaps`; they are listed under the table.\n")
w("| Metric | Value | Gap Reason (if < 100%) |\n|--------|-------|-------------------------|")
w("| Repo Coverage | 1/1 (100%) | learning-rts untracked (no remote yet), excluded by definition |")
w("| Language Coverage | 2/4 (50%) | CMake and Bash build/install scripts not extracted (deliberate; grammars exist) |")
w("| Cross-Repo Mechanism Coverage | n/a (0/0) | single repo; Python↔C++ pybind boundary resolved in call edges instead |")
w(f"| Edge Resolution Coverage (blended, strict) | {er['overall_pct_all']}% | external-package calls are in the denominator; project-internal only: {er['overall_pct_project_only']}% |\n")
w("### Edge Resolution Coverage — by language\n")
w("| Language | Resolved | Unresolved | external-package | Coverage (strict) | Coverage (project-internal) |\n|---|---|---|---|---|---|")
for lang, name in (("cpp", "C++"), ("python", "Python")):
    v = er["by_language"][lang]
    w(f"| {name} | {v['resolved']} | {v['unresolved']} | {v['external']} | {v['resolution_pct_all']}% | {v['resolution_pct_project_only']}% |")
w("\n### Unresolved Calls — by reason\n")
w("| Reason | Count | Meaning |\n|--------|-------|---------|")
w(f"| `external-package` | {by_reason['external-package']} | stdlib / OpenCV / Blend2D / xtensor / pybind11 / nlohmann / torch / pygame, via namespace allowlist: expected, not a gap |")
w(f"| `missing-repo` | {by_reason['missing-repo']} | none: single repo |")
w(f"| `dynamic` | {by_reason['dynamic']} | callable variables / virtual methods without any concrete definition in scope |")
w(f"| `type-alias` | {by_reason['type-alias']} | genuinely unresolved after the 2.1.1 heuristics: the bucket to investigate |\n")
w("**Gaps (named):**\n")
for g in gaps:
    w(f"- {g}")
w("\n### Top `type-alias` targets (the actionable bucket)\n")
w("| Target | Language | Count |\n|---|---|---|")
for t, l, c in q("SELECT target, language, COUNT(*) c FROM unresolved_calls WHERE reason='type-alias' GROUP BY target, language ORDER BY c DESC LIMIT 10"):
    w(f"| `{t}` | {l} | {c} |")
w("\n---\n")
w("## Complexity Hotspots\n")
w(f"{ncc} functions have cyclomatic complexity > 10 (top 10 shown; McCabe: 1 + branches + `&&`/`||`).\n")
w("| Function | Location | Complexity | Action |\n|----------|----------|------------|--------|")
for nid, loc, c in cc:
    w(f"| `{short(nid)}` | {loc_link(loc)} | {c} | Review / refactor |")
w("\n---\n")
w("## High Fan-in Functions\n")
w("Most-called functions. Changes here have the highest blast radius. (Max fan-in in this codebase is small, so no row reaches the template's High (>20) tier.)\n")
w("| Function | Location | Callers | Risk |\n|----------|----------|---------|------|")
for nid, loc, fi, fo in hot:
    w(f"| `{short(nid)}` | {loc_link(loc)} | {fi} | {'High' if fi > 20 else 'Medium' if fi > 10 else 'Low'} |")
w("\n---\n")
w("## High Fan-out Functions\n")
w("Coordination hubs. Note: virtual calls fan out to every override, which inflates `fan_out` for the state-machine drivers.\n")
w("| Function | Location | Callees | Note |\n|----------|----------|---------|------|")
for nid, loc, fo in fanout:
    w(f"| `{short(nid)}` | {loc_link(loc)} | {fo} | {'High coordination' if fo > 15 else ''} |")
w("\n---\n")
w("## Circular Dependencies\n")
if CYCLES == 0:
    w("No cycles detected (Tarjan SCC over the whole graph, not only entry-reachable; independently re-checked with a bounded recursive CTE: 0 nodes on any cycle). "
      "Caveat: callbacks that re-enter through `std::function`/Python (`PyGame::_update` → Python → `Game.*`) are only partly modelled, and `transitionState` re-entry via virtual `init()/end()` would show here if those bodies called back.\n")
else:
    for cid, nodes in q("SELECT cycle_id, nodes FROM view_cycles"):
        w(f"- Cycle {cid}: " + " → ".join(f"`{short(x)}`" for x in json.loads(nodes)))
w("\n---\n")
w("## Dead Code Summary\n")
w(f"{DEAD} functions have no callers and are not entry points ({pct(DEAD, N)}). C++: {sum(1 for r in dead_rows if r[2]=='cpp')}, Python: {sum(1 for r in dead_rows if r[2]=='python')}. "
  "Destructors are never counted (implicitly invoked).\n")
w("| Category | Count |\n|---|---|")
w(f"| Total dead code candidates | {DEAD} |")
w(f"| File last modified > 1 year ago | {dead_by_file_age.get('>1y', 0)} |")
w(f"| File last modified 6 months - 1 year | {dead_by_file_age.get('6m-1y', 0)} |")
w(f"| File last modified < 6 months | {dead_by_file_age.get('<6m', 0)} |")
w(f"| Unknown | {dead_by_file_age.get('unknown', 0)} |")
w("\n> `last_modified` is the last commit touching the **file**, not the function. See `reports/dead-code.md`.\n")
w("---\n")
w("## Python ↔ C++ Boundary (pybind11)\n")
w(f"The engine is a C++ library exposed to Python through pybind11 (`bindings/`). The graph models both directions:\n")
w(f"- **Python → C++**: {sum(c for a, b, c in XL if a == 'python')} edges, resolved through the `pybind_bindings` table ({one('SELECT COUNT(*) FROM pybind_bindings')} `.def*` registrations; {one('SELECT COUNT(*) FROM nodes WHERE entry_type=?','python-binding')} C++ nodes are entry points because Python can call them).")
w(f"- **C++ → Python** (virtual-method trampolines): {sum(c for a, b, c in XL if a == 'cpp')} edges from `bindings/trampolines/*` overrides to the Python methods that implement them; {one('SELECT COUNT(*) FROM pybind_callbacks')} callback sites.\n")
w("**Callbacks C++ expects from Python but Python does not define.** The trampolines use `PYBIND11_OVERLOAD` (not `_PURE`), so when no Python override exists pybind11 calls the C++ base implementation: no error, but the Python-side hook never fires:\n")
w("| Trampoline | Python name expected | Defined in Python? |\n|---|---|---|")
for node, cls, pyname, cppname in q("SELECT node, cpp_class, py_name, cpp_name FROM pybind_callbacks"):
    if cls != "Game":
        continue
    has = one("SELECT COUNT(*) FROM edges WHERE from_node=? AND to_node LIKE ?", node, "%game.py:%")
    w(f"| `{short(node)}` | `{pyname}` | {'yes' if has else '**no**'} |")
w("\n**Python names the wrapper calls on `self` that neither Python nor the C++ bindings define** (candidate `AttributeError`s at runtime):\n")
w("| Call site | Target |\n|---|---|")
_rows = [r for r in q("SELECT call_site, target FROM unresolved_calls WHERE language='python' AND reason='type-alias' AND call_site LIKE 'DeepRTS/python/game.py:%'") if re.fullmatch(r"self\.[A-Za-z_]\w*", r[1])]
for site, tgt in _rows:
    w(f"| `{site}` | `{tgt}` |")
if not _rows:
    w("| (none) | every direct `self.<name>()` call in `game.py` resolves to a Python method or a pybind binding |")
w("\n---\n")
w("## Entry Point Call Graphs\n")
w("Top 3 entry points by reachable-node count. Diagrams show the first two hops only (full chains: `view_entry_traces`).\n")
top = q("SELECT entry_node, entry_type, path FROM view_entry_traces ORDER BY json_array_length(path) DESC LIMIT 60")
shown = 0
seen_types = collections.Counter()
for e, et, path in top:
    path = json.loads(path)
    if seen_types[et] >= 1 or shown >= 3:
        continue
    seen_types[et] += 1
    shown += 1
    w(f"### {mlabel(e)} ({et}): reaches {len(path)} functions\n")
    w("```mermaid\ngraph TD")
    seen_n, seen_e = set(), set()

    def mnode(x):
        if x not in seen_n:
            seen_n.add(x)
            w(f'  {sid(x)}["{mlabel(x)}"]')

    def medge(a, b, dyn):
        if (a, b) not in seen_e:
            seen_e.add((a, b))
            w(f"  {sid(a)} {'-.->' if dyn else '-->'} {sid(b)}")

    mnode(e)
    for t, dyn in q("SELECT DISTINCT to_node, is_dynamic FROM edges WHERE from_node=? LIMIT 12", e):
        mnode(t)
        medge(e, t, dyn)
        for t2, dyn2 in q("SELECT DISTINCT to_node, is_dynamic FROM edges WHERE from_node=? LIMIT 4", t):
            mnode(t2)
            medge(t, t2, dyn2)
    w("```\n")
    ext = [x for x in json.loads(one("SELECT external_calls FROM view_entry_traces WHERE entry_node=?", e))]
    w(f"**External-touching functions on the path**: {len(ext)} (e.g. {', '.join('`'+short(x)+'`' for x in ext[:4]) or 'none'})  ")
    w("**Data stores touched**: None (no DB; persistence is files via `ResourceLoader`)\n")
w("> Dashed arrows are virtual-dispatch edges (class-hierarchy over-approximation). See `reports/entry-point-map.md`.\n")
open(DOCS / "analysis" / "09-code-graph.md", "w").write("\n".join(lines) + "\n")

# =================================================================================================
# entry-point-map.md
# =================================================================================================
L = []
w = L.append
w("# Entry Point Map\n")
w(f"**Project**: deep-rts (old engine, pinned `{COMMIT}`)  \n**Generated**: {TODAY}  \n**Entry Points**: {ENTRIES}\n")
w("Entry-point rules used (project-specific; the skill's HTTP/cron rules do not apply to a game engine):\n")
w("| Type | Rule | Count |\n|---|---|---|")
for et, c in q("SELECT entry_type, COUNT(*) FROM nodes WHERE is_entry_point=1 GROUP BY 1 ORDER BY 2 DESC"):
    rule = {"python-binding": "C++ method/lambda exposed to Python by a pybind11 `.def*` registration",
            "api": "public (non-underscore) function/method of the `DeepRTS/python` package",
            "script": "module-level code of an example or package script",
            "cli": "`main()` of the standalone C++ executable (`src/main.cpp`)",
            "python-module-init": "`PYBIND11_MODULE` / `PYBIND11_EMBEDDED_MODULE` (runs on `import`)"}.get(et, et)
    w(f"| `{et}` | {rule} | {c} |")
w("\n## Summary (all entry points except individual python-binding methods)\n")
w("| Entry Point | Type | Reachable functions | External-touching | Conditional edges |\n|---|---|---|---|---|")
rows = q("SELECT entry_node, entry_type, path, external_calls FROM view_entry_traces WHERE entry_type != 'python-binding' ORDER BY json_array_length(path) DESC")
for e, et, path, ext in rows:
    p = json.loads(path)
    ph = ",".join("?" * len(p))
    cond = one(f"SELECT COUNT(*) FROM edges WHERE from_node IN ({ph}) AND is_conditional=1", *p) if p else 0
    w(f"| `{short(e)}` | {et} | {len(p)} | {len(json.loads(ext))} | {cond} |")
w("\n## Bound C++ surface by Python class (the `python-binding` entry points)\n")
w("| Python class | Bound C++ nodes | Largest reach | Methods |\n|---|---|---|---|")
bound = q("SELECT n.class_name, n.id, json_array_length(t.path) FROM nodes n JOIN view_entry_traces t ON t.entry_node=n.id WHERE n.entry_type='python-binding'")
grp = collections.defaultdict(list)
for cls, nid, reach in bound:
    grp[cls or "(free)"].append((nid, reach))
for cls, items in sorted(grp.items(), key=lambda kv: -len(kv[1])):
    mx = max(items, key=lambda x: x[1])
    names = ", ".join(short(i[0]).split("::")[-1].split(".")[-1] for i in items[:8]) + (" …" if len(items) > 8 else "")
    w(f"| `{cls}` | {len(items)} | {mx[1]} (`{short(mx[0])}`) | {names} |")
w("\n## Deepest chains (top 8 by reach)\n")
deep = q("SELECT entry_node, entry_type, path FROM view_entry_traces ORDER BY json_array_length(path) DESC LIMIT 8")
for e, et, path in deep:
    p = json.loads(path)
    w(f"### `{short(e)}` ({et}), reaches {len(p)} functions\n")
    w(f"**Handler**: {loc_link(one('SELECT location FROM nodes WHERE id=?', e))}\n")
    w("```")
    for nid in p[:25]:
        w(f"→ {short(nid)}")
    if len(p) > 25:
        w(f"… {len(p) - 25} more (query `view_entry_traces` for the full path)")
    w("```\n")
    w("| Aspect | Detail |\n|---|---|")
    w(f"| Reachable functions | {len(p)} |")
    w("| Data stores accessed | None |")
    ext = json.loads(one("SELECT external_calls FROM view_entry_traces WHERE entry_node=?", e))
    w(f"| External-touching functions | {len(ext)} |")
    w("| Async boundaries | 0 (single-threaded game loop; no async in the engine) |")
    ph = ",".join("?" * len(p))
    w(f"| Conditional edges in reach | {one(f'SELECT COUNT(*) FROM edges WHERE from_node IN ({ph}) AND is_conditional=1', *p)} |")
    w(f"| Virtual-dispatch edges in reach | {one(f'SELECT COUNT(*) FROM edges WHERE from_node IN ({ph}) AND is_dynamic=1', *p)} |\n")
open(DOCS / "reports" / "entry-point-map.md", "w").write("\n".join(L) + "\n")

# =================================================================================================
# dead-code.md
# =================================================================================================
L = []
w = L.append
w("# Dead Code Report\n")
w(f"**Project**: deep-rts (old engine, pinned `{COMMIT}`)  \n**Generated**: {TODAY}  \n**Candidates**: {DEAD}\n")
w("> Candidates have `fan_in = 0` and are not entry points. **This is a library and a game engine**, so many candidates are public API that external C++ "
  "consumers or Python could call: the C++ build also ships as `DeepRTSLib` and as a standalone executable. Python-reachable C++ methods are already excluded "
  "(they are `python-binding` entry points). Virtual overrides count as called when any caller of the base method exists (class-hierarchy edges).\n")


def risk(nid, loc, lang):
    f = loc.rsplit(":", 1)[0]
    if lang == "python":
        return "Review first" if f.startswith("DeepRTS/python/") else "Low (example code)"
    if f.startswith("include/") and one("SELECT type FROM nodes WHERE id=?", nid) in ("method", "constructor") and not f.endswith("Blend2DGUI.h"):
        return "Review first (public header API)"
    if "trampoline" in one("SELECT tags FROM nodes WHERE id=?", nid):
        return "Review first (pybind trampoline)"
    return "Low (internal)"


inv = [(nid, loc, lang, risk(nid, loc, lang), file_dates[loc.rsplit(":", 1)[0]]) for nid, loc, lang in dead_rows]
rc = collections.Counter(r[3].split(" (")[0] for r in inv)
w("## Summary\n")
w("| Risk | Count | Description |\n|---|---|---|")
w(f"| Low | {rc.get('Low', 0)} | internal helpers / example code with no callers: likely removable |")
w(f"| Review first | {rc.get('Review first', 0)} | public header API, Python wrapper API or pybind trampolines: external consumers possible |")
w(f"| Recently orphaned (file < 6 months) | {dead_by_file_age.get('<6m', 0)} | |")
w(f"| `extraction_method = ai` | 0 | all static |\n")
w("Note on dates: `code/deep-rts` is the upstream clone and its last commit is 2023-05-16, so every file is more than a year old. File age carries no signal here. Use `git log -L` on a function before deleting.\n")
w("## Inventory\n")
w("| Function | Location | File last modified | Risk |\n|---|---|---|---|")
for nid, loc, lang, rk, d in sorted(inv, key=lambda r: (r[1].rsplit(':', 1)[0], int(r[1].rsplit(':', 1)[1]))):
    w(f"| `{short(nid)}` | {loc_link(loc)} | {d} | {rk} |")
w("\n## Removal Guidance\n")
w("1. **Confirm with git blame**: check whether call sites were recently removed.")
w("2. **Search for string references**: pybind names and Python `getattr` use strings, which the graph cannot see.")
w("3. **Check the examples**: `examples/` consumers are in the graph, but external user code is not.")
w("4. **Header-only inline getters** (`Player::getGold` etc.) are cheap and API-shaped: removing them is low value.")
open(DOCS / "reports" / "dead-code.md", "w").write("\n".join(L) + "\n")

# =================================================================================================
# sqlite-cookbook.md (Phase 4B.5)
# =================================================================================================
tpl = (TOOLBOX / "skills/optional/code-graph/sqlite-cookbook.template.md").read_text()
subs = {"{extraction_date}": TODAY, "{sqlite_path}": SQLITE_PATH, "{node_count}": str(N), "{edge_count}": str(E),
        "{mechanism_count}": str(one("SELECT COUNT(*) FROM mechanism_edges")), "{repo_count}": "1", "{entry_count}": str(ENTRIES),
        "{dead_count}": str(DEAD), "{dead_pct}": pct(DEAD, N)}
for k, v in subs.items():
    tpl = tpl.replace(k, v)
# template links are relative to the skill directory; re-point them for the metarepo layout
tpl = tpl.replace("](workflows.md)", "](../../../.quantum-toolbox/skills/optional/code-graph/workflows.md)")
tpl = tpl.replace("[reports/sre-hot-paths.md](sre-hot-paths.md)", "`reports/sre-hot-paths.md` (not generated: requires SRE view 08)")
tpl = tpl.replace("[`sre-hot-paths.md`](sre-hot-paths.md)", "`sre-hot-paths.md` (not generated: requires SRE view 08)")
extra = f"""

---

## Project-specific additions (deep-rts extraction)

This database is a **superset** of the toolbox schema. Additions made by `scripts/cg-extract.py`:

| Addition | Purpose |
|----------|---------|
| `nodes.language` (`cpp` \\| `python`) | per-language scorecard and filtering; derive nothing from file extensions |
| `nodes.entry_type` | why a node is an entry point: `python-binding`, `api`, `script`, `cli`, `python-module-init` |
| `nodes.class_name` | owning class (C++ and Python) |
| `unresolved_calls.language` | per-language `edgeResolutionCoverage` |
| `class_hierarchy(class, base, file, line)` | C++ inheritance (single query for "all subclasses of X") |
| `pybind_bindings(py_class, py_name, cpp_class, cpp_member, kind, site, resolved_node)` | every pybind11 `.def*` registration |
| `pybind_callbacks(node, cpp_class, py_name, cpp_name, site)` | trampolines that call back into Python |
| `pyan_crosscheck(from_node, to_node, verdict)` | pyan3 vs tree-sitter edge comparison for Python |
| `excluded_files(path, reason)` | files deliberately outside the graph (tests, vendored, build scripts) |
| `extraction_meta(key, value)` | extraction commit, date, scorecard JSON |

Edge `type` values used: `call`, `instantiates`. `is_dynamic = 1` marks class-hierarchy (virtual dispatch) edges: the real target is one of the listed overrides.

### Queries specific to this project

```sql
-- Every concrete state the state machine can dispatch to
SELECT class FROM class_hierarchy WHERE base = 'BaseState';

-- Python-visible C++ API surface, by Python class
SELECT py_class, COUNT(*) FROM pybind_bindings WHERE resolved_node IS NOT NULL GROUP BY py_class ORDER BY 2 DESC;

-- Bindings that point at fields/ctors with no function node (def_readonly etc.)
SELECT py_class, py_name, kind FROM pybind_bindings WHERE resolved_node IS NULL;

-- Python -> C++ calls (the language boundary)
SELECT a.id, b.id, e.call_site FROM edges e JOIN nodes a ON a.id=e.from_node JOIN nodes b ON b.id=e.to_node
WHERE a.language='python' AND b.language='cpp';

-- C++ -> Python callbacks
SELECT a.id, b.id FROM edges e JOIN nodes a ON a.id=e.from_node JOIN nodes b ON b.id=e.to_node
WHERE a.language='cpp' AND b.language='python';

-- Functions that touch OpenCV / Blend2D / xtensor / pybind (tag 'external')
SELECT id, location FROM nodes WHERE has_external_call = 1;

-- Virtual dispatch fan-out per call site
SELECT call_site, COUNT(*) AS targets FROM edges WHERE is_dynamic=1 GROUP BY call_site ORDER BY targets DESC LIMIT 10;

-- Honest coverage: what could not be resolved, by language and reason
SELECT language, reason, COUNT(*) FROM unresolved_calls GROUP BY 1, 2;
```
"""
(DOCS / "reports" / "sqlite-cookbook.md").write_text(tpl + extra)

# =================================================================================================
# manifest: artifacts.code-graph only (Phase 4C)
# =================================================================================================
mf_path = METAROOT / "specs" / "analysis-manifest.json"
mf = json.loads(mf_path.read_text()) if mf_path.exists() and mf_path.read_text().strip() else {}
mf.setdefault("registryFiles", ["sources/urls.md"])
mf["toolboxVersion"] = "3.3.1"
mf.setdefault("lastAnalysis", {})["date"] = TODAY
mf["lastAnalysis"].setdefault("repositories", {})[REPO] = {"commit": COMMIT}
mf.setdefault("artifacts", {})
skill_ver = "1.0"
mf["artifacts"]["code-graph"] = {
    "lastAnalyzedDate": TODAY,
    "lastAnalyzedCommit": COMMIT,
    "generatedDate": TODAY,
    "generatedWithSkillVersion": skill_ver,
    "method": "tree-sitter-cpp 0.23.4 + tree-sitter-python 0.25.0 (tier 2) + class-hierarchy analysis + pybind boundary model; pyan3 2.9.0 cross-check; sqlite3",
    "regenerate": "venv/bin/python scripts/cg-extract.py && venv/bin/python scripts/cg-pyan-crosscheck.py && venv/bin/python scripts/cg-reports.py",
    "code_graph_mode": "sqlite",
    "sourceRepos": [REPO],
    "files": [SQLITE_PATH],
    "reports": [
        "docs/architecture-docs/analysis/09-code-graph.md",
        "docs/architecture-docs/reports/entry-point-map.md",
        "docs/architecture-docs/reports/dead-code.md",
        "docs/architecture-docs/reports/sqlite-cookbook.md",
    ],
    "stats": {
        "totalNodes": N, "resolvedEdges": E, "crossRepoCalls": 0, "entryPoints": ENTRIES,
        "deadCodeNodes": DEAD, "deadCodeRate": pct(DEAD, N),
        "repoCoverage": "1/1 (100%)", "languageCoverage": "2/4 (50%)", "crossRepoMechanismCoverage": "n/a (0/0, single repo)",
        "edgeResolutionCoverage": {
            "overall": f"{er['overall_pct_all']}%",
            "byLanguage": {"cpp": f"{er['by_language']['cpp']['resolution_pct_all']}%", "python": f"{er['by_language']['python']['resolution_pct_all']}%"},
        },
        "gaps": gaps,
    },
}
mf.setdefault("history", [])
mf["history"] = [h for h in mf["history"] if not (h.get("skill") == "code-graph" and h.get("date") == TODAY)]
mf["history"].append({
    "date": TODAY, "skill": "code-graph", "trigger": "manual (first extraction, v0.0.1 consolidation)", "repos": [REPO],
    "coverage": {"repoCoverage": "1/1 (100%)", "languageCoverage": "2/4 (50%)", "crossRepoMechanismCoverage": "n/a (0/0)",
                 "edgeResolutionCoverage": f"{er['overall_pct_all']}% overall (cpp {er['by_language']['cpp']['resolution_pct_all']}%, python {er['by_language']['python']['resolution_pct_all']}%)"},
    "notes": f"project-internal resolution: cpp {cpp_pr}%, python {py_pr}%",
})
mf_path.parent.mkdir(exist_ok=True)
mf_path.write_text(json.dumps(mf, indent=2) + "\n")
print(f"wrote View 09, 3 reports, manifest. nodes={N} edges={E} entries={ENTRIES} dead={DEAD} cycles={CYCLES}")
