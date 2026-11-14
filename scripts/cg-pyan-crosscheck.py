#!/usr/bin/env python3
"""
cg-pyan-crosscheck.py - run pyan3 (tier-1 Python tool, code-graph skill 0.1) over the Python sources and compare its
call edges with the tree-sitter edges in code/<repo>/code_graph.sqlite. Writes table `pyan_crosscheck`.

pyan3 is name-based static analysis (no type inference, no knowledge of the pybind boundary). It is used as an
independent cross-check, not merged into `edges`: see docs/architecture-docs/analysis/09-code-graph.md.

Usage: venv/bin/python scripts/cg-pyan-crosscheck.py [repo]
"""
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

db = sqlite3.connect(DB)
py_nodes = {r[0]: r[1] for r in db.execute("SELECT id, location FROM nodes WHERE language='python'")}
loc_to_id = {}
for nid, loc in py_nodes.items():
    f, line = loc.rsplit(":", 1)
    loc_to_id[(f, int(line))] = nid
files = sorted({loc.rsplit(":", 1)[0] for loc in py_nodes.values()})

dot = subprocess.run([sys.executable, "-m", "pyan", *files, "--uses", "--no-defines", "--dot"], cwd=ROOT,
                     capture_output=True, text=True, timeout=300)
if dot.returncode != 0:
    print("pyan3 failed:", dot.stderr[-500:])
    sys.exit(1)

# node declarations: "ID" [label=..., tooltip="dotted\n/abs/path/file.py:LINE\nkind in ..."]
decl = {}
for m in re.finditer(r'"([^"]+)" \[label="([^"]*)".*?tooltip="([^"]*)"\];', dot.stdout):
    key, label, tip = m.groups()
    mm = re.search(r"/code/" + re.escape(REPO) + r"/([^:\\]+):(\d+)", tip)
    if mm:
        decl[key] = (mm.group(1), int(mm.group(2)))

pyan_edges = set()
unmapped = 0
for m in re.finditer(r'"([^"]+)" -> "([^"]+)"', dot.stdout):
    a, b = m.groups()
    ia = loc_to_id.get(decl.get(a, (None, 0)))
    ib = loc_to_id.get(decl.get(b, (None, 0)))
    if ia and ib:
        pyan_edges.add((ia, ib))
    else:
        unmapped += 1

mine = {(f, t) for f, t in db.execute(
    "SELECT e.from_node, e.to_node FROM edges e JOIN nodes a ON a.id=e.from_node JOIN nodes b ON b.id=e.to_node "
    "WHERE a.language='python' AND b.language='python'")}
# restrict the comparison to caller files pyan3 was able to model
both = pyan_edges & mine
only_pyan = pyan_edges - mine
only_mine = mine - pyan_edges
self_loops = sum(1 for a, b in pyan_edges if a == b)

db.execute("DROP TABLE IF EXISTS pyan_crosscheck")
db.execute("CREATE TABLE pyan_crosscheck (from_node TEXT, to_node TEXT, verdict TEXT)")
for a, b in sorted(both):
    db.execute("INSERT INTO pyan_crosscheck VALUES (?,?,?)", (a, b, "both"))
for a, b in sorted(only_pyan):
    db.execute("INSERT INTO pyan_crosscheck VALUES (?,?,?)", (a, b, "pyan-only"))
for a, b in sorted(only_mine):
    db.execute("INSERT INTO pyan_crosscheck VALUES (?,?,?)", (a, b, "treesitter-only"))
stats = {
    "pyan3_version": subprocess.run([sys.executable, "-c", "import pyan;print(pyan.__version__)"], capture_output=True, text=True).stdout.strip() or "2.x",
    "pyan_edges_mapped": len(pyan_edges), "pyan_edges_unmapped": unmapped,
    "treesitter_py_to_py_edges": len(mine), "agree": len(both), "pyan_only": len(only_pyan),
    "treesitter_only": len(only_mine), "pyan_self_loops": self_loops,
    "agreement_of_pyan": round(100 * len(both) / len(pyan_edges), 1) if pyan_edges else None,
    "agreement_of_treesitter": round(100 * len(both) / len(mine), 1) if mine else None,
}
db.execute("INSERT OR REPLACE INTO extraction_meta VALUES ('pyan_crosscheck', ?)", (json.dumps(stats),))
db.commit()
print(json.dumps(stats, indent=1))
