#!/usr/bin/env python3
"""
cg-ejaj-boj-reports.py - render View 09 + code-graph reports from code/ejaj-boj/code_graph.sqlite
(quantum-toolbox code-graph skill v3.3.1: View 09, entry-point-map, dead-code, sqlite-cookbook).

Writes (all under docs/ejaj-boj/architecture-docs/):
  analysis/09-code-graph.md
  reports/entry-point-map.md
  reports/dead-code.md
  reports/sqlite-cookbook.md

Usage: venv/bin/python scripts/cg-ejaj-boj-reports.py   (run scripts/cg-ejaj-boj.py and cg-pyan-crosscheck.py ejaj-boj first)
"""
import collections
import datetime
import json
import re
import sqlite3
from pathlib import Path

METAROOT = Path(__file__).resolve().parent.parent
REPO = "ejaj-boj"
ROOT = METAROOT / "code" / REPO
DB = ROOT / "code_graph.sqlite"
DOCS = METAROOT / "docs" / "ejaj-boj" / "architecture-docs"
TEMPLATE = METAROOT / ".quantum-toolbox/skills/optional/code-graph/sqlite-cookbook.template.md"
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
pyan = meta.get("pyan_crosscheck", {})


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def short(nid):
    f, _, rest = nid.partition(":")
    return rest if rest else nid


def mlabel(nid):
    return short(nid).replace('"', "'")


def loc_of(nid):
    return one("SELECT location FROM nodes WHERE id=?", nid)


# ---- tests reference scan (the graph excludes tests; this tells which candidates they still use) ----
test_files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in (".py", ".mjs", ".js") and
              ("tests/" in p.as_posix() or p.name == "test-pure.mjs") and "node_modules" not in p.as_posix()
              and ".venv" not in p.as_posix() and ".crew-venv" not in p.as_posix()]
test_text = "\n".join(p.read_text(errors="ignore") for p in test_files)


def test_refs(name):
    base = name.split(".")[-1]
    if len(base) < 4 or base.startswith("<"):
        return None
    return len(re.findall(r"\b" + re.escape(base) + r"\b", test_text))


out = []


def w(s):
    out.append(s)


# =============================================================================
# 09-code-graph.md
# =============================================================================
by_lang = sc["by_language"]
w("# View 09: Code Graph\n")
w(f"**Project**: ejaj-boj (the owner's earlier parametric-RTS project, pinned `{COMMIT}`)  \n**Generated**: {TODAY}  \n**Backend**: SQLite (`{SQLITE_PATH}`, gitignored, regenerate with the commands below)\n")
w("## Executive Summary\n")
w("| Metric | Value |\n|---|---|")
w(f"| Functions / methods / module bodies | {N} (Python {one('SELECT COUNT(*) FROM nodes WHERE language=?','python')}, JavaScript {one('SELECT COUNT(*) FROM nodes WHERE language=?','javascript')}) |")
w(f"| Call edges | {E} ({', '.join(f'{t} {c}' for t, c in q('SELECT type, COUNT(*) FROM edges GROUP BY 1 ORDER BY 2 DESC'))}) |")
w(f"| Entry points | {ENTRIES} ({', '.join(f'{t} {c}' for t, c in q('SELECT entry_type, COUNT(*) FROM nodes WHERE is_entry_point=1 GROUP BY 1 ORDER BY 2 DESC'))}) |")
w(f"| Dead-code candidates | {DEAD} ({pct(DEAD, N)}); see [dead-code.md](../reports/dead-code.md) |")
w(f"| Circular dependencies (function level) | {CYCLES} |")
BOUNDARY = one("SELECT COUNT(*) FROM edges WHERE type IN ('http','websocket')")
w(f"| Browser → server edges | {BOUNDARY} (HTTP/WebSocket calls resolved to the FastAPI handlers) |")
w(f"| Source files | {meta['files_py']} Python + {meta['files_js']} JavaScript (the inline scripts of `client/index.html` plus 10 `client/lib/*.mjs`) |\n")
w("> **Coverage confidence: Medium-High for project-internal calls, with named gaps.** Static, syntax-aware extraction (stdlib `ast` for Python, tree-sitter for JavaScript) with project-local type resolution; no type checker was run. "
  "Tests are outside the graph by design; the dead-code report shows which candidates tests still use.\n")
w("> **Scope decisions** (the skill's interactive dialogue was answered by the analyst, as for deep-rts): single repo `ejaj-boj` at the pinned SHA; unified SQLite graph; all outputs; tests, the AI-crew tooling (`crew/`, `.quantum-*`, `.local-skills/`) and `run-crew.sh` excluded.\n")
w("## Extraction Summary\n")
w("| Language | Tool | Tier | Note |\n|---|---|---|---|")
w("| Python | stdlib `ast` + project-local resolution (annotations, constructor calls, `self` fields, MRO, class-hierarchy dispatch, properties, unique-method-name fallback) (`scripts/cg-ejaj-boj.py`) | 2 | No type checker run. pyan3 2.9.0 is the skill's tier-1 tool; it **was run** as a cross-check (below), not merged |")
w("| JavaScript | `tree-sitter-javascript` 0.25.0 on `client/lib/*.mjs` and the inline `<script>` blocks of `client/index.html` (line numbers preserved) | 2 | Classes, object-literal methods, arrow functions and event/timer callbacks are nodes; `this`, global-instance and import resolution; DOM/Canvas/builtin calls are `external-package` by an allowlist of names |")
w("| Browser → server | `fetch('/path')` and `new WebSocket(.../ws)` matched to FastAPI route decorators | n/a | edge types `http` / `websocket`; table `routes` |\n")
w("### Resolution heuristics worth knowing\n")
w("- **Flow-insensitive typing**: the last typed assignment to a local wins; no `isinstance` narrowing.")
w("- **Bare `list` annotations lose element types.** `Player.units` and `Player.buildings` are annotated `list`, so loops over them have untyped elements. The extractor falls back to **unique-method-name matching** (`name-match` edges, `is_dynamic=1`) when a method name has 1-3 definers in the project (`move_towards`, `step_path`, `distance_to`, `take_damage`). Names with more definers (`to_dict`) stay unresolved. These edges are real calls in the source I read but are heuristic; the scorecard reports them separately.")
w("- A method whose name appears in an unresolved call site is **not** reported as dead (it may be the target): see the dead-code report.\n")
w("## Coverage Scorecard\n")
w("| Metric | Value | Reason for any gap |\n|---|---|---|")
w("| repoCoverage | 1/1 (100%) | `learning-rts` has no code to analyse |")
w("| languageCoverage | 2/3 (67%) | Python and JavaScript extracted; **Bash** (`run-crew.sh`, the AI-crew runner) is not game code and was not extracted. HTML/CSS are markup, not call graph |")
w("| crossRepoMechanismCoverage | n/a (0/0) | single repo; the one cross-boundary mechanism (browser → server HTTP/WebSocket) is resolved into edges inside the repo |")
w(f"| edgeResolutionCoverage (blended, strict: every external call in the denominator) | {sc['overall_pct_all']}% | dominated by builtin/stdlib/DOM calls, expected |")
w(f"| edgeResolutionCoverage (project-internal only, typed) | {sc['overall_pct_project_only']}% | see per language |")
w(f"| edgeResolutionCoverage (project-internal, incl. unique-name matches) | {sc['overall_pct_project_only_incl_name_match']}% | |\n")
w("| Language | Resolved (typed) | Name-match call sites | Unresolved | of which external | Strict % | Project-only % | Project-only % incl. name-match |\n|---|---|---|---|---|---|---|---|")
for lang in ("python", "javascript"):
    v = by_lang[lang]
    w(f"| {lang} | {v['resolved']} | {v['name_match_call_sites']} | {v['unresolved']} | {v['external']} | {v['resolution_pct_all']}% | {v['resolution_pct_project_only']}% | {v['resolution_pct_project_only_incl_name_match']}% |")
w("")
w("| Unresolved reason | Python | JavaScript | Meaning |\n|---|---|---|---|")
byr = {lang: by_lang[lang]["by_reason"] for lang in by_lang}
for r, mean in (("external-package", "stdlib, builtins, FastAPI/uvicorn, DOM, Canvas, `Math`/`JSON`; expected, not a gap"),
                ("type-alias", "receiver type unknown and the method name is ambiguous or builtin-like"),
                ("dynamic", "callbacks passed as parameters (`onZoom`, `resolve`) or non-name callees"),
                ("missing-repo", "none")):
    w(f"| `{r}` | {byr['python'].get(r, 0)} | {byr['javascript'].get(r, 0)} | {mean} |")
w("")
w("### pyan3 cross-check (Python)\n")
if pyan:
    w(f"pyan3 {pyan['pyan3_version']} was run on the same files and compared with this graph's Python→Python edges: **{pyan['agree']} edges agree**, "
      f"{pyan['pyan_only']} are pyan3-only, {pyan['treesitter_only']} are only in this graph. Agreement: {pyan['agreement_of_pyan']}% of pyan3's edges, {pyan['agreement_of_treesitter']}% of this graph's. "
      "(The column name `treesitter_only` in table `pyan_crosscheck` is inherited from the deep-rts script; the Python side here uses `ast`.)\n")
    w("What I checked by reading the source for the disagreements (`SELECT * FROM pyan_crosscheck WHERE verdict != 'both'`):\n")
    w("- **All 20 pyan3-only edges are false or non-calls** (I read each caller). 16 are `Method → Class.__init__` edges from methods that neither construct their own class nor call `__init__` (the likely cause is pyan3's attribute-use tracking; not verified), 2 are self-loops (`Agent.__init__`, `create_placeholder_assets`), and `Entity.to_dict → _new_id` and `Unit.step_path → Unit.move_towards` do not exist in the code.")
    w("- The 26 graph-only edges are mostly the `name-match` edges and calls pyan3 cannot type (`for agent in self.agents: agent.tick(...)` → `Agent.tick`, which is a real edge pyan3 misses).")
    w("- Conclusion: for this codebase the in-house extractor is at least as accurate as pyan3; pyan3 stays a cross-check.\n")
w("## Complexity Hotspots (cyclomatic complexity > 10)\n")
w("| # | Function | CC | Location |\n|---|---|---|---|")
for i, (nid, cc, loc) in enumerate(q("SELECT id, cyclomatic_complexity, location FROM nodes WHERE cyclomatic_complexity > 10 ORDER BY cyclomatic_complexity DESC"), 1):
    w(f"| {i} | `{mlabel(nid)}` | {cc} | `{loc}` |")
w("\nCC counts `if`, ternary, loops, `except`, `assert`, boolean operators and comprehension clauses (Python) or the tree-sitter equivalents (JavaScript). `Agent._manage_production` at 58 is the outlier: the whole build/scout/train policy is one method.\n")
w("## High Fan-in (most-called)\n")
w("| # | Function | Fan-in | Fan-out | Note |\n|---|---|---|---|---|")
for i, (nid, fi, fo) in enumerate(q("SELECT id, fan_in, fan_out FROM nodes WHERE fan_in > 0 ORDER BY fan_in DESC LIMIT 10"), 1):
    nm = one("SELECT COUNT(*) FROM edges WHERE to_node=? AND type='name-match'", nid)
    w(f"| {i} | `{mlabel(nid)}` | {fi} | {fo} | {'includes ' + str(nm) + ' name-match edges' if nm else ''} |")
w("\n## High Fan-out (coordination)\n")
w("| # | Function | Fan-out | CC |\n|---|---|---|---|")
for i, (nid, fo, cc) in enumerate(q("SELECT id, fan_out, cyclomatic_complexity FROM nodes ORDER BY fan_out DESC LIMIT 8"), 1):
    w(f"| {i} | `{mlabel(nid)}` | {fo} | {cc} |")
w("\n## Circular Dependencies\n")
w(f"{CYCLES} cycles at function level (Tarjan SCC over all edge types; checked on the whole graph, not only from entry points). " + ("No recursion, no mutual recursion." if CYCLES == 0 else ""))
w("\n## Browser ↔ Server Boundary\n")
w("| Client node | Edge | Server handler |\n|---|---|---|")
for a, b, t in q("SELECT from_node, to_node, type FROM edges WHERE type IN ('http','websocket') ORDER BY 3, 1"):
    w(f"| `{mlabel(a)}` | {t} | `{mlabel(b)}` |")
w("\nRoutes: " + "; ".join(f"`{m} {p}`" for m, p, _ in q("SELECT * FROM routes")) + ". The server also mounts static directories `/lib` and `/assets` (not call edges). There is no client → server message over the WebSocket: the handler reads and discards every received frame.\n")
w("## Dead Code Summary\n")
w(f"{DEAD} candidates ({pct(DEAD, N)}): Python {one('SELECT COUNT(*) FROM nodes WHERE is_dead_code=1 AND language=?','python')}, JavaScript {one('SELECT COUNT(*) FROM nodes WHERE is_dead_code=1 AND language=?','javascript')}. "
  f"{len(meta['dead_code_excluded_by_unresolved_name'])} further methods were **not** counted because their name appears at an unresolved call site. Full inventory with test references: [dead-code.md](../reports/dead-code.md).\n")

# call-graph diagrams for three entry points
w("## Call Graph Diagrams (entry traces, depth 3)\n")
adj = collections.defaultdict(list)
for a, b, t in q("SELECT from_node, to_node, type FROM edges WHERE type IN ('call','instantiates','virtual-dispatch','http','websocket','name-match','property')"):
    adj[a].append((b, t))
traces = {r[0]: json.loads(r[2]) for r in q("SELECT entry_node, entry_type, path FROM view_entry_traces")}
want = [("server/main.py:start", "POST /start"), ("server/core/game_engine.py:GameEngine._game_loop", "Game loop (asyncio task started by GameEngine.start)"),
        ("server/main.py:ws_endpoint", "WS /ws")]
for nid, title in want:
    if nid not in traces and one("SELECT COUNT(*) FROM nodes WHERE id=?", nid) == 0:
        continue
    w(f"### {title}\n")
    w("```mermaid\nflowchart LR")
    ids = {}
    seen_edges = set()
    frontier = [(nid, 0)]
    visited = {nid}
    def nid_of(x):
        if x not in ids:
            ids[x] = f"n{len(ids)}"
        return ids[x]
    lines = []
    while frontier:
        cur, d = frontier.pop(0)
        if d >= 3:
            continue
        for tgt, t in adj.get(cur, []):
            if (cur, tgt) in seen_edges:
                continue
            seen_edges.add((cur, tgt))
            arrow = "-.->" if t in ("name-match", "virtual-dispatch") else "-->"
            lines.append(f'    {nid_of(cur)}["{mlabel(cur)}"] {arrow} {nid_of(tgt)}["{mlabel(tgt)}"]')
            if tgt not in visited:
                visited.add(tgt)
                frontier.append((tgt, d + 1))
    for ln in lines[:40]:
        w(ln)
    if len(lines) > 40:
        w(f"    %% {len(lines) - 40} more edges omitted")
    w("```\n")
    w("Dotted arrows are heuristic (`name-match`) or virtual-dispatch edges.\n")
w("## Regeneration\n")
w("```bash\nvenv/bin/python scripts/cg-ejaj-boj.py && venv/bin/python scripts/cg-pyan-crosscheck.py ejaj-boj && venv/bin/python scripts/cg-ejaj-boj-reports.py\n```\n")
(DOCS / "analysis").mkdir(parents=True, exist_ok=True)
(DOCS / "analysis" / "09-code-graph.md").write_text("\n".join(out) + "\n")

# =============================================================================
# entry-point-map.md
# =============================================================================
out = []
w(f"# Entry Point Map\n\n**Project**: ejaj-boj (pinned `{COMMIT}`)  \n**Generated**: {TODAY}  \n**Entry points**: {ENTRIES}\n")
w("Entry types: `http` / `websocket` = FastAPI route handlers; `framework` = callbacks given to FastAPI; `script` = a `__main__` module; `browser-load` = the inline script that runs when the page loads; "
  "`event` = DOM / WebSocket event handlers (`addEventListener`, `ws.onmessage = ...`); `timer` = `setTimeout`/`setInterval`/`requestAnimationFrame` callbacks. "
  "**The game loop is not an entry type here**: `GameEngine._game_loop` is reached through `GameEngine.start` (an `asyncio` task created there), so it appears in the traces of `POST /start`.\n")
w("| Entry | Type | Location | Reach (functions) | External-call functions | Max CC on path |\n|---|---|---|---|---|---|")
rows = []
for nid, et, path, ext in q("SELECT entry_node, entry_type, path, external_calls FROM view_entry_traces"):
    p = json.loads(path)
    ccs = [one("SELECT cyclomatic_complexity FROM nodes WHERE id=?", n) for n in p]
    rows.append((len(p), nid, et, loc_of(nid), len(json.loads(ext)), max(ccs)))
for reach, nid, et, loc, ne, mcc in sorted(rows, key=lambda r: (-r[0], r[1])):
    w(f"| `{mlabel(nid)}` | {et} | `{loc}` | {reach} | {ne} | {mcc} |")
w("\n## Server entry points in detail\n")
for nid in [r[1] for r in rows if r[2] in ("http", "websocket", "framework", "script")]:
    p = json.loads(one("SELECT path FROM view_entry_traces WHERE entry_node=?", nid))
    et = one("SELECT entry_type FROM nodes WHERE id=?", nid)
    route = q("SELECT method, path FROM routes WHERE node=?", nid)
    w(f"### `{mlabel(nid)}`" + (f" ({route[0][0]} `{route[0][1]}`)" if route else "") + f"\n\nType `{et}`; reaches {len(p)} functions.\n")
    w("Reached: " + ", ".join(f"`{mlabel(x)}`" for x in p[:25]) + (" ..." if len(p) > 25 else "") + "\n")
(DOCS / "reports").mkdir(parents=True, exist_ok=True)
(DOCS / "reports" / "entry-point-map.md").write_text("\n".join(out) + "\n")

# =============================================================================
# dead-code.md
# =============================================================================
out = []
w(f"# Dead Code Candidates\n\n**Project**: ejaj-boj (pinned `{COMMIT}`)  \n**Generated**: {TODAY}  \n**Candidates**: {DEAD} ({pct(DEAD, N)})\n")
w("> A candidate has `fan_in = 0` in the **production** graph and is not an entry point. The graph excludes tests, so the **Test refs** column counts word-boundary matches of the function name in `tests/` and `client/lib/test-pure.mjs`: "
  "a function used only by tests is not dead for the project's own test suite but is dead for the running game. Reflection, string dispatch and calls through untyped receivers are invisible to the graph (see the excluded list below).\n")
w("| Language | Function | Location | CC | Test refs | Assessment |\n|---|---|---|---|---|---|")
assess_notes = {
    "server/game_engine.py": "Dead import shim: nothing imports it. Its fallback stub class has a different API (`start(agent0, agent1)` without a seed). If the real import ever failed it would silently serve the stub",
}
for nid, loc, lang, cc in q("SELECT id, location, language, cyclomatic_complexity FROM nodes WHERE is_dead_code=1 ORDER BY language, id"):
    tr = test_refs(short(nid))
    note = ""
    f = nid.split(":")[0]
    if f in assess_notes:
        tr = None   # name collisions with live code make the test-reference count meaningless for the shim
    if f in assess_notes:
        note = assess_notes[f]
    elif tr and tr > 0:
        note = "Used only by tests: dead in the game, alive in the suite"
    elif tr == 0:
        note = "No reference anywhere in tests: remove, or wire up if intended"
    else:
        note = "Check usage manually"
    w(f"| {lang} | `{mlabel(nid)}` | `{loc}` | {cc} | {tr if tr is not None else 'n/a'} | {note} |")
w("\n## Not counted as dead because the name appears at an unresolved call site\n")
w("These methods have no resolved caller, but an unresolved call (receiver type unknown) uses the same method name, so they may be the target. Typical case: `to_dict` overrides, called as `u.to_dict()` over untyped lists.\n")
for nid in meta["dead_code_excluded_by_unresolved_name"]:
    w(f"- `{mlabel(nid)}` (`{loc_of(nid)}`)")
w("\n## Findings from reading the candidates\n")
w("- `Knight.try_attack` / `Archer.try_attack` (and `can_attack`) are unused by the game: `Agent._manage_combat` applies damage itself with `take_damage`, duplicating the cooldown logic. Two implementations of the attack rule exist; only the agent's one runs.")
w("- `FogOfWar.reset_wire_state` is documented as \"called when a new match starts or POST /reset fires\"; nothing calls it. It is harmless only because `GameEngine.start` builds fresh `FogOfWar` objects.")
w("- The `return_threshold` agent parameter is also **dead** in the sense that no server code reads it (see [02](../analysis/02-interface-specification.md)); this is a parameter, not a function, so it does not appear in the graph.\n")
(DOCS / "reports" / "dead-code.md").write_text("\n".join(out) + "\n")

# =============================================================================
# sqlite-cookbook.md
# =============================================================================
tpl = TEMPLATE.read_text()
mech = one("SELECT COUNT(*) FROM mechanism_edges")
repl = {"{extraction_date}": TODAY, "{sqlite_path}": SQLITE_PATH, "{node_count}": str(N), "{edge_count}": str(E),
        "{mechanism_count}": str(mech), "{repo_count}": "1", "{entry_count}": str(ENTRIES), "{dead_count}": str(DEAD), "{dead_pct}": pct(DEAD, N)}
for k, v in repl.items():
    tpl = tpl.replace(k, v)
tpl = tpl.replace("](workflows.md)", "](../../../../.quantum-toolbox/skills/optional/code-graph/workflows.md)")
tpl = tpl.replace("| [`sre-hot-paths.md`](sre-hot-paths.md) |", "| `sre-hot-paths.md` (not generated: needs SRE view 08) |")
tpl = tpl.replace("file.ts:line", "file:line").replace("file.ts:ClassName.methodName", "file:ClassName.methodName")
extra = f"""
---

## Project-specific additions (ejaj-boj extraction)

Superset of the toolbox schema. The graph has two languages (`nodes.language` = `python` | `javascript`) and one repo (`{REPO}`).

| Addition | Meaning |
|---|---|
| `nodes.language`, `nodes.entry_type`, `nodes.class_name` | language, entry kind (`http`, `websocket`, `framework`, `script`, `browser-load`, `event`, `timer`), owning class or object literal |
| `nodes.type = 'module'` | the module/script body (`<module>`): top-level statements, decorators, `app = FastAPI(...)` |
| `edges.type` | `call`, `instantiates`, `virtual-dispatch` (class-hierarchy), `name-match` (heuristic: unique method name), `property` (attribute read of a `@property`), `reference` (function passed as a value), `http`, `websocket` (browser → server) |
| `routes(method, path, node)` | FastAPI route table |
| `class_hierarchy(class, base, file, line)` | Python inheritance, incl. external bases |
| `pyan_crosscheck(from_node, to_node, verdict)` | pyan3 vs this graph (`both` / `pyan-only` / `treesitter-only`) |
| `excluded_files(path, reason)` | what is outside the graph and why |
| `extraction_meta(key, value)` | scorecard, commit, `dead_code_excluded_by_unresolved_name` |

```sql
-- the browser -> server boundary
SELECT a.id, e.type, b.id FROM edges e JOIN nodes a ON a.id=e.from_node JOIN nodes b ON b.id=e.to_node WHERE e.type IN ('http','websocket');

-- what the agent code touches in the world model (callees of Agent methods in core/)
SELECT DISTINCT a.name, b.id FROM edges e JOIN nodes a ON a.id=e.from_node JOIN nodes b ON b.id=e.to_node
WHERE a.class_name='Agent' AND b.repo_path LIKE 'server/core/%';

-- heuristic edges only (verify before relying on them)
SELECT from_node, to_node, call_site FROM edges WHERE type='name-match';

-- every class and its bases
SELECT class, base FROM class_hierarchy ORDER BY base, class;
```
"""
(DOCS / "reports" / "sqlite-cookbook.md").write_text(tpl + extra)
print("wrote 09-code-graph.md, entry-point-map.md, dead-code.md, sqlite-cookbook.md")
