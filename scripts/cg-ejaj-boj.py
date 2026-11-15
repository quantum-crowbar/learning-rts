#!/usr/bin/env python3
"""
cg-ejaj-boj.py - function-level code graph of code/ejaj-boj (Python server + browser JavaScript client)
written to code/ejaj-boj/code_graph.sqlite (quantum-toolbox code-graph skill v3.3.1 schema, SQLite backend).

Tooling (tier 2, see docs/ejaj-boj/architecture-docs/analysis/09-code-graph.md):
  Python      stdlib `ast` + project-local type resolution (annotations, constructor calls, self-fields, MRO,
              class-hierarchy dispatch). No type checker was run: pyan3 is the skill's tier-1 tool and is run by
              scripts/cg-pyan-crosscheck.py as a cross-check, as for deep-rts.
  JavaScript  tree-sitter-javascript on client/lib/*.mjs and the inline <script> blocks of client/index.html.
  Boundary    browser -> server fetch()/WebSocket calls are resolved to the FastAPI route handlers (edge types
              'http' / 'websocket').

Tests (tests/, client/lib/test-pure.mjs, playwright) are deliberately outside the graph; reports note which dead-code
candidates are referenced by tests.

Usage: venv/bin/python scripts/cg-ejaj-boj.py
"""
import ast
import collections
import datetime
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Parser

METAROOT = Path(__file__).resolve().parent.parent
REPO = "ejaj-boj"
ROOT = METAROOT / "code" / REPO
OUT = ROOT / "code_graph.sqlite"
JS = Parser(Language(tsjs.language()))

# ----------------------------------------------------------------------------
# discovery
# ----------------------------------------------------------------------------
tracked = subprocess.check_output(["git", "-C", str(ROOT), "ls-files"], text=True).splitlines()
PY_FILES = sorted(f for f in tracked if f.endswith(".py") and (f.startswith("server/") or f.startswith("scripts/")))
JS_LIBS = sorted(f for f in tracked if f.startswith("client/lib/") and f.endswith(".mjs") and not f.endswith("test-pure.mjs"))
HTML = "client/index.html"
excluded = []
for f in tracked:
    if f.endswith(".py") and f not in PY_FILES:
        excluded.append((f, "tests" if f.startswith("tests/") else "outside scope"))
    elif f.endswith((".mjs", ".js")) and f not in JS_LIBS:
        excluded.append((f, "tests/config (JS)"))
    elif f.endswith(".sh"):
        excluded.append((f, "bash: no extractor (AI-crew runner, not game code)"))

# ----------------------------------------------------------------------------
# model
# ----------------------------------------------------------------------------
class Func:
    def __init__(self, id_, name, qname, file, line, lang, node, cls=None):
        self.id, self.name, self.qname, self.file, self.line = id_, name, qname, file, line
        self.lang, self.node, self.cls = lang, node, cls
        self.sig = ""
        self.cc = 1
        self.entry_type = None
        self.is_async = False
        self.tags = set()
        self.implicit = False
        self.mod = None
        self.localfuncs = {}   # nested function name -> Func


funcs, by_id = [], {}
edges = {}                 # (from, to, type, site) -> flags
unresolved = []
routes = []                # (method, path, node)
classes = {}               # key -> ClassInfo (python)


def new_func(file, qname, line, lang, node, cls=None):
    base = f"{file}:{qname}"
    id_ = base if base not in by_id else f"{base}#{line}"
    f = Func(id_, qname.split(".")[-1], qname, file, line, lang, node, cls)
    funcs.append(f)
    by_id[id_] = f
    return f


def add_edge(frm, to, etype, site, dyn=False, cond=False, is_async=False):
    k = (frm.id, to.id, etype, site)
    fl = edges.setdefault(k, {"dyn": False, "cond": False, "async": False})
    fl["dyn"] |= dyn
    fl["cond"] |= cond
    fl["async"] |= is_async


def add_unres(frm, site, target, reason, lang):
    unresolved.append((frm.id, site, target[:80], reason, lang))


# ============================================================================
# PYTHON
# ============================================================================
BUILTIN_FUNCS = set(dir(__builtins__)) if not isinstance(__builtins__, dict) else set(__builtins__)
BUILTIN_METHODS = {
    "append", "extend", "insert", "pop", "popleft", "appendleft", "remove", "discard", "add", "clear", "copy", "sort",
    "reverse", "index", "count", "get", "items", "keys", "values", "setdefault", "update", "join", "split", "strip",
    "format", "startswith", "endswith", "replace", "lower", "upper", "encode", "decode", "read", "write", "close",
    "send_text", "receive_text", "accept", "is_file", "exists", "mkdir", "write_bytes", "read_text", "resolve",
}
SCALARS = {"int", "str", "float", "bool", "bytes", "dict", "tuple", "set", "list"}


class Mod:
    def __init__(self, file, tree):
        self.file, self.tree = file, tree
        stem = file[:-3].replace("/", ".")
        self.name = stem[:-9] if stem.endswith(".__init__") else stem
        self.is_pkg = file.endswith("__init__.py")
        self.imports = {}       # local name -> ('module', m) | ('from', m, sym)
        self.classes = {}       # name -> class key
        self.funcs = {}         # module-level function name -> Func
        self.var_types = {}     # module-level variable -> type
        self.module_func = None


class ClassInfo:
    def __init__(self, key, name, mod, node):
        self.key, self.name, self.mod, self.node = key, name, mod, node
        self.bases = []          # resolved class keys
        self.ext_bases = []      # unresolved (external) base names
        self.methods = {}        # name -> Func
        self.props = set()
        self.fields = {}         # name -> type


method_index = collections.defaultdict(list)   # method name -> [Func] (for the unique-name fallback)
mods = {}          # file -> Mod
modfile = {}       # module name -> file


def py_cc(fn_node):
    n = 1
    stack = list(ast.iter_child_nodes(fn_node))
    while stack:
        x = stack.pop()
        if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(x, (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.Assert)):
            n += 1
        elif isinstance(x, ast.BoolOp):
            n += len(x.values) - 1
        elif isinstance(x, ast.comprehension):
            n += 1 + len(x.ifs)
        elif hasattr(ast, "match_case") and isinstance(x, ast.match_case):
            n += 1
        stack.extend(ast.iter_child_nodes(x))
    return n


def collect_imports(mod):
    for n in ast.walk(mod.tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.asname:
                    mod.imports[a.asname] = ("module", a.name)
                else:
                    mod.imports[a.name.split(".")[0]] = ("module", a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            base = n.module or ""
            if n.level:
                pkg = mod.name if mod.is_pkg else mod.name.rsplit(".", 1)[0] if "." in mod.name else ""
                for _ in range(n.level - 1):
                    pkg = pkg.rsplit(".", 1)[0] if "." in pkg else ""
                base = f"{pkg}.{base}" if base and pkg else (pkg or base)
            for a in n.names:
                mod.imports[a.asname or a.name] = ("from", base, a.name)


def collect_defs(mod, body, cls_stack, func_stack, parent=None):
    for n in body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qn = ".".join(cls_stack + func_stack + [n.name])
            direct_method = bool(cls_stack) and not func_stack
            ckey = f"{mod.name}.{cls_stack[-1]}" if direct_method else None
            f = new_func(mod.file, qn, n.lineno, "python", n, ckey)
            f.mod = mod
            f.is_async = isinstance(n, ast.AsyncFunctionDef)
            f.cc = py_cc(n)
            f.sig = f"{'async ' if f.is_async else ''}def {n.name}({', '.join(a.arg for a in n.args.args)})"
            if direct_method:
                ci = classes[ckey]
                ci.methods[n.name] = f
                if any(isinstance(d, ast.Name) and d.id == "property" for d in n.decorator_list):
                    ci.props.add(n.name)
                if n.name.startswith("__") and n.name.endswith("__") and n.name != "__init__":
                    f.implicit = True
            elif not cls_stack and not func_stack:
                mod.funcs[n.name] = f
            if parent is not None:
                parent.localfuncs[n.name] = f
            collect_defs(mod, n.body, cls_stack, func_stack + [n.name], parent=f)
        elif isinstance(n, ast.ClassDef):
            key = f"{mod.name}.{n.name}"
            ci = ClassInfo(key, n.name, mod, n)
            classes[key] = ci
            mod.classes[n.name] = key
            collect_defs(mod, n.body, cls_stack + [n.name], [], None)
        elif isinstance(n, (ast.If, ast.Try, ast.With, ast.For, ast.While, ast.AsyncWith, ast.AsyncFor)):
            for attr in ("body", "orelse", "finalbody"):
                collect_defs(mod, getattr(n, attr, []) or [], cls_stack, func_stack, parent)
            for h in getattr(n, "handlers", []) or []:
                collect_defs(mod, h.body, cls_stack, func_stack, parent)


def resolve_import(m, depth=0):
    """follow a ('from', module, sym) / ('module', m) entry to a project symbol; returns tagged tuple"""
    return None


def resolve_name(mod, name, depth=0):
    if name in mod.classes:
        return ("class", mod.classes[name])
    if name in mod.funcs:
        return ("func", mod.funcs[name])
    imp = mod.imports.get(name)
    if imp is None:
        return ("builtin", name) if name in BUILTIN_FUNCS else None
    if imp[0] == "module":
        return ("module", imp[1]) if imp[1] in modfile else ("ext", imp[1])
    _, m, sym = imp
    full = f"{m}.{sym}"
    if full in modfile:
        return ("module", full)
    if m in modfile:
        target = mods[modfile[m]]
        if sym in target.classes:
            return ("class", target.classes[sym])
        if sym in target.funcs:
            return ("func", target.funcs[sym])
        if depth < 4 and sym in target.imports:
            return resolve_name(target, sym, depth + 1)
        return None
    return ("ext", full)


def ty_from_ann(n, mod):
    if n is None:
        return None
    if isinstance(n, ast.Constant):
        if isinstance(n.value, str):
            try:
                return ty_from_ann(ast.parse(n.value, mode="eval").body, mod)
            except SyntaxError:
                return None
        return None
    if isinstance(n, ast.Attribute):
        root = n
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name):
            r = resolve_name(mod, root.id)
            if r and r[0] == "ext":
                return ("ext", ast.unparse(n))
        return None
    if isinstance(n, ast.Name):
        if n.id in ("list", "List", "Sequence", "set", "Set"):
            return ("list", None)
        if n.id in ("dict", "Dict"):
            return ("dict", None, None)
        if n.id in SCALARS:
            return ("b", n.id)
        r = resolve_name(mod, n.id)
        if r and r[0] == "class":
            return ("c", r[1])
        return None
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
        left = ty_from_ann(n.left, mod)
        return left if left is not None and not (isinstance(n.left, ast.Constant)) else ty_from_ann(n.right, mod)
    if isinstance(n, ast.Subscript):
        base = n.value.id if isinstance(n.value, ast.Name) else None
        sl = n.slice
        if base in ("list", "List", "Sequence", "set", "Set"):
            return ("list", ty_from_ann(sl, mod))
        if base in ("dict", "Dict") and isinstance(sl, ast.Tuple) and len(sl.elts) == 2:
            return ("dict", ty_from_ann(sl.elts[0], mod), ty_from_ann(sl.elts[1], mod))
        if base == "Optional":
            return ty_from_ann(sl, mod)
        if base in ("tuple", "Tuple"):
            return ("b", "tuple")
    return None


def mro(key, seen=None):
    seen = seen if seen is not None else []
    if key in seen or key not in classes:
        return seen
    seen.append(key)
    for b in classes[key].bases:
        mro(b, seen)
    return seen


def find_method(key, name, skip_self=False):
    for i, k in enumerate(mro(key)):
        if skip_self and i == 0:
            continue
        m = classes[k].methods.get(name)
        if m:
            return m
    return None


def descendants(key):
    out = []
    for k, ci in classes.items():
        if k != key and key in mro(k):
            out.append(k)
    return out


def field_type(key, name):
    for k in mro(key):
        ci = classes[k]
        if name in ci.fields:
            return ci.fields[name]
        if name in ci.props:
            return ret_type(ci.methods[name])
    return None


_ret_cache = {}


def ret_type(f):
    if f.id not in _ret_cache:
        _ret_cache[f.id] = ty_from_ann(f.node.returns, f.mod) if f.lang == "python" else None
    return _ret_cache[f.id]


def elem_type(t):
    if t and t[0] == "list":
        return t[1]
    if t and t[0] == "dict":
        return t[1]
    return None


class Env:
    def __init__(self, mod, cls, locals_):
        self.mod, self.cls, self.locals = mod, cls, locals_


def ty_expr(n, env):
    if isinstance(n, ast.Name):
        if n.id in env.locals:
            return env.locals[n.id]
        if n.id in env.mod.var_types:
            return env.mod.var_types[n.id]
        r = resolve_name(env.mod, n.id)
        if r and r[0] == "class":
            return ("cls", r[1])
        if r and r[0] in ("module", "ext"):
            return ("mod", r[1]) if r[0] == "module" else ("ext", r[1])
        return None
    if isinstance(n, ast.Attribute):
        t = ty_expr(n.value, env)
        if t and t[0] == "c":
            return field_type(t[1], n.attr)
        if t and t[0] == "mod":
            full = f"{t[1]}.{n.attr}"
            if full in modfile:
                return ("mod", full)
            tm = mods[modfile[t[1]]] if t[1] in modfile else None
            if tm and n.attr in tm.classes:
                return ("cls", tm.classes[n.attr])
        if t and t[0] == "ext":
            return ("ext", f"{t[1]}.{n.attr}")
        return None
    if isinstance(n, ast.Call):
        fn = n.func
        if isinstance(fn, ast.Name):
            r = resolve_name(env.mod, fn.id)
            if fn.id in env.locals and env.locals[fn.id] and env.locals[fn.id][0] == "cls":
                return ("c", env.locals[fn.id][1])
            if r and r[0] == "class":
                return ("c", r[1])
            if r and r[0] == "func":
                return ret_type(r[1])
            if r and r[0] == "ext":
                return ("ext", r[1] + "()")
            if fn.id in ("sorted", "list", "reversed") and n.args:
                return ("list", elem_type(ty_expr(n.args[0], env)))
            if fn.id in ("min", "max") and n.args:
                return elem_type(ty_expr(n.args[0], env))
            if fn.id in ("len", "int", "round", "sum"):
                return ("b", "int")
            return None
        if isinstance(fn, ast.Attribute):
            rt = ty_expr(fn.value, env)
            if rt and rt[0] == "c":
                m = find_method(rt[1], fn.attr)
                return ret_type(m) if m else None
            if rt and rt[0] == "mod" and rt[1] in modfile:
                tm = mods[modfile[rt[1]]]
                if fn.attr in tm.classes:
                    return ("c", tm.classes[fn.attr])
                if fn.attr in tm.funcs:
                    return ret_type(tm.funcs[fn.attr])
            if rt and rt[0] == "ext":
                return ("ext", f"{rt[1]}.{fn.attr}()")
            if fn.attr == "copy":
                return rt
        return None
    if isinstance(n, ast.Subscript):
        t = ty_expr(n.value, env)
        if t and t[0] == "list":
            return t[1]
        if t and t[0] == "dict":
            return t[2]
        return None
    if isinstance(n, (ast.List, ast.Set)) and n.elts:
        return ("list", ty_expr(n.elts[0], env))
    if isinstance(n, (ast.List, ast.Set)):
        return ("list", None)
    if isinstance(n, ast.Dict):
        return ("dict", None, None)
    if isinstance(n, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
        return ("list", ty_expr(n.elt, env))
    if isinstance(n, ast.IfExp):
        return ty_expr(n.body, env) or ty_expr(n.orelse, env)
    if isinstance(n, ast.BoolOp):
        for v in n.values:
            t = ty_expr(v, env)
            if t:
                return t
        return None
    if isinstance(n, ast.Constant):
        return ("b", type(n.value).__name__) if n.value is not None else None
    return None


def assign_types(stmts, env):
    """flow-insensitive, in source order; later typed assignments overwrite earlier ones"""
    for s in stmts:
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(s, ast.Assign):
            t = ty_expr(s.value, env)
            for tg in s.targets:
                if isinstance(tg, ast.Name) and t is not None:
                    env.locals[tg.id] = t
                elif isinstance(tg, ast.Tuple) and isinstance(s.value, ast.Tuple) and len(tg.elts) == len(s.value.elts):
                    for a, b in zip(tg.elts, s.value.elts):
                        if isinstance(a, ast.Name):
                            tt = ty_expr(b, env)
                            if tt is not None:
                                env.locals[a.id] = tt
        elif isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
            t = ty_from_ann(s.annotation, env.mod) or (ty_expr(s.value, env) if s.value else None)
            if t is not None:
                env.locals[s.target.id] = t
        elif isinstance(s, (ast.For, ast.AsyncFor)):
            it = s.iter
            et = None
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "enumerate" and it.args:
                et = elem_type(ty_expr(it.args[0], env))
                if isinstance(s.target, ast.Tuple) and len(s.target.elts) == 2 and isinstance(s.target.elts[1], ast.Name) and et:
                    env.locals[s.target.elts[1].id] = et
                    et = None
                    if isinstance(s.target.elts[0], ast.Name):
                        env.locals[s.target.elts[0].id] = ("b", "int")
            elif isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "list" and it.args:
                et = elem_type(ty_expr(it.args[0], env))
            else:
                et = elem_type(ty_expr(it, env))
            if isinstance(s.target, ast.Name) and et is not None:
                env.locals[s.target.id] = et
        for attr in ("body", "orelse", "finalbody"):
            sub = getattr(s, attr, None)
            if sub:
                assign_types(sub, env)
        for h in getattr(s, "handlers", []) or []:
            assign_types(h.body, env)
    # comprehension variables (after statements so their iterables are typed)


def comp_vars(root, env):
    for n in ast.walk(root):
        if isinstance(n, ast.comprehension) and isinstance(n.target, ast.Name):
            et = elem_type(ty_expr(n.iter, env))
            if et is not None:
                env.locals[n.target.id] = et


def collect_class_fields(ci):
    mod = ci.mod
    base_env = Env(mod, ci.key, {})
    for s in ci.node.body:
        if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
            t = ty_from_ann(s.annotation, mod)
            if t:
                ci.fields[s.target.id] = t
    for m in ci.methods.values():
        env = Env(mod, ci.key, {})
        # make parameter types available for constructor-argument typed fields
        for a in m.node.args.args + m.node.args.kwonlyargs:
            t = ty_from_ann(a.annotation, mod)
            if t:
                env.locals[a.arg] = t
        for n in ast.walk(m.node):
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Attribute) and isinstance(n.target.value, ast.Name) \
                    and n.target.value.id == "self":
                t = ty_from_ann(n.annotation, mod)
                if t and (t[0] != "list" or t[1] is not None or n.target.attr not in ci.fields):
                    ci.fields[n.target.attr] = t
            elif isinstance(n, ast.Assign):
                for tg in n.targets:
                    if isinstance(tg, ast.Attribute) and isinstance(tg.value, ast.Name) and tg.value.id == "self" \
                            and tg.attr not in ci.fields:
                        t = ty_expr(n.value, env)
                        if t and t[0] in ("c", "list", "dict"):
                            ci.fields[tg.attr] = t


def func_env(f):
    mod = f.mod
    env = Env(mod, f.cls, {})
    args = f.node.args
    allargs = args.posonlyargs + args.args + args.kwonlyargs
    for i, a in enumerate(allargs):
        t = ty_from_ann(a.annotation, mod)
        if t:
            env.locals[a.arg] = t
        elif i == 0 and f.cls and a.arg in ("self", "cls"):
            env.locals[a.arg] = ("c", f.cls)
    # enclosing function parameters/locals are visible in nested functions
    parent_chain = f.qname.split(".")
    assign_types(f.node.body, env)
    comp_vars(f.node, env)
    return env


def walk_calls(root, skip_nested=True):
    """yield (node, conditional) for Call / Attribute / Name nodes in a function body, not entering nested defs"""
    stack = [(c, False) for c in ast.iter_child_nodes(root)]
    while stack:
        n, cond = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield n, cond
        c2 = cond or isinstance(n, (ast.If, ast.IfExp, ast.BoolOp, ast.ExceptHandler, ast.Try))
        for ch in ast.iter_child_nodes(n):
            stack.append((ch, c2))


def scan_python(f, nodes_root, env):
    mod = f.mod
    call_funcs = set()
    for n, cond in walk_calls(nodes_root):
        if isinstance(n, ast.Call):
            call_funcs.add(id(n.func))
    for n, cond in walk_calls(nodes_root):
        site = f"{f.file}:{getattr(n, 'lineno', f.line)}"
        if isinstance(n, ast.Call):
            resolve_py_call(f, n, env, site, cond)
        elif isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load):
            t = ty_expr(n.value, env)
            if t and t[0] == "c":
                m = find_method(t[1], n.attr)
                if m:
                    if n.attr in classes[m.cls].props if m.cls in classes else False:
                        add_edge(f, m, "property", site, cond=cond)
                    elif id(n) not in call_funcs:
                        add_edge(f, m, "reference", site, dyn=True, cond=cond)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and id(n) not in call_funcs:
            r = resolve_name(mod, n.id) if n.id not in env.locals else None
            if r and r[0] == "func" and r[1] is not f:
                add_edge(f, r[1], "reference", site, dyn=True, cond=cond)


def resolve_py_call(f, call, env, site, cond):
    mod = f.mod
    fn = call.func
    lang = "python"

    def hit(target, etype="call", dyn=False):
        add_edge(f, target, etype, site, dyn=dyn, cond=cond, is_async=target.is_async)

    def ctor(key):
        init = find_method(key, "__init__")
        if init:
            hit(init, "instantiates")
        return

    if isinstance(fn, ast.Name):
        name = fn.id
        if name in f.localfuncs:
            return hit(f.localfuncs[name])
        # nested function defined in an enclosing function
        if "." in f.qname:
            parts = f.qname.split(".")
            for i in range(len(parts) - 1, 0, -1):
                par = by_id.get(f"{f.file}:{'.'.join(parts[:i])}")
                if par and name in par.localfuncs:
                    return hit(par.localfuncs[name])
        if name in env.locals and env.locals[name] and env.locals[name][0] != "cls":
            return add_unres(f, site, name, "dynamic", lang)
        r = resolve_name(mod, name)
        if r is None:
            return add_unres(f, site, name, "dynamic", lang)
        if r[0] == "class":
            return ctor(r[1])
        if r[0] == "func":
            return hit(r[1])
        return add_unres(f, site, name, "external-package", lang)
    if isinstance(fn, ast.Attribute):
        attr = fn.attr
        base = fn.value
        text = ast.unparse(fn)
        if isinstance(base, ast.Call) and isinstance(base.func, ast.Name) and base.func.id == "super" and f.cls:
            m = find_method(f.cls, attr, skip_self=True)
            return hit(m) if m else add_unres(f, site, text, "external-package", lang)
        t = ty_expr(base, env)
        if t and t[0] in ("c", "cls"):
            key = t[1]
            m = find_method(key, attr)
            if m:
                hit(m)
                if t[0] == "c":
                    for d in descendants(key):
                        dm = classes[d].methods.get(attr)
                        if dm and dm is not m:
                            hit(dm, "virtual-dispatch", dyn=True)
                return
            if attr in field_names(key):
                return add_unres(f, site, text, "dynamic", lang)
            ci = classes[key]
            if any(b for b in ci.ext_bases):
                return add_unres(f, site, text, "external-package", lang)
            return add_unres(f, site, text, "type-alias", lang)
        if t and t[0] == "mod":
            if t[1] in modfile:
                tm = mods[modfile[t[1]]]
                if attr in tm.funcs:
                    return hit(tm.funcs[attr])
                if attr in tm.classes:
                    return ctor(tm.classes[attr])
                return add_unres(f, site, text, "type-alias", lang)
            return add_unres(f, site, text, "external-package", lang)
        if t and t[0] == "ext":
            return add_unres(f, site, text, "external-package", lang)
        if t and t[0] in ("list", "dict", "b"):
            return add_unres(f, site, text, "external-package", lang)
        if attr in BUILTIN_METHODS:
            return add_unres(f, site, text, "external-package", lang)
        cands = method_index.get(attr, [])
        if 1 <= len(cands) <= 3:
            for m in cands:
                hit(m, "name-match", dyn=True)
            return
        return add_unres(f, site, text, "type-alias", lang)
    return add_unres(f, site, ast.unparse(fn), "dynamic", lang)


def field_names(key):
    out = set()
    for k in mro(key):
        out |= set(classes[k].fields)
    return out


def py_entry_points():
    for f in funcs:
        if f.lang != "python" or not isinstance(f.node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for d in f.node.decorator_list:
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and isinstance(d.func.value, ast.Name) \
                    and d.func.value.id == "app" and d.func.attr in ("get", "post", "put", "delete", "websocket"):
                path = d.args[0].value if d.args and isinstance(d.args[0], ast.Constant) else "?"
                meth = "WS" if d.func.attr == "websocket" else d.func.attr.upper()
                f.entry_type = "websocket" if meth == "WS" else "http"
                routes.append((meth, path, f.id))
    # lifespan handed to FastAPI(...)
    for mod in mods.values():
        for n in ast.walk(mod.tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "FastAPI":
                for kw in n.keywords:
                    if kw.arg == "lifespan" and isinstance(kw.value, ast.Name) and kw.value.id in mod.funcs:
                        mod.funcs[kw.value.id].entry_type = "framework"
        if any(isinstance(s, ast.If) and "__name__" in ast.unparse(s.test) for s in mod.tree.body) and mod.module_func:
            mod.module_func.entry_type = "script"


def build_python():
    for f in PY_FILES:
        tree = ast.parse((ROOT / f).read_text(), filename=f)
        m = Mod(f, tree)
        mods[f] = m
        modfile[m.name] = f
    for m in mods.values():
        collect_imports(m)
    for m in mods.values():
        mf = new_func(m.file, "<module>", 1, "python", m.tree)
        mf.mod = m
        mf.sig = f"<module {m.name}>"
        mf.tags.add("module")
        m.module_func = mf
        collect_defs(m, m.tree.body, [], [])
    # class bases
    for ci in classes.values():
        for b in ci.node.bases:
            r = resolve_name(ci.mod, b.id) if isinstance(b, ast.Name) else None
            if r and r[0] == "class":
                ci.bases.append(r[1])
            else:
                ci.ext_bases.append(ast.unparse(b))
    for ci in classes.values():
        collect_class_fields(ci)
    # a second field pass so fields typed from other classes' fields settle
    for ci in classes.values():
        collect_class_fields(ci)
    # module-level variable types
    for m in mods.values():
        env = Env(m, None, {})
        for s in m.tree.body:
            if isinstance(s, ast.Assign):
                t = ty_expr(s.value, env)
                for tg in s.targets:
                    if isinstance(tg, ast.Name) and t:
                        m.var_types[tg.id] = t
            elif isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
                t = ty_from_ann(s.annotation, m) or (ty_expr(s.value, env) if s.value else None)
                if t:
                    m.var_types[s.target.id] = t
    for ci in classes.values():
        for mn, mf_ in ci.methods.items():
            if not (mn.startswith("__") and mn.endswith("__")):
                method_index[mn].append(mf_)
    py_entry_points()
    # bodies
    for f in [x for x in funcs if x.lang == "python"]:
        if f.name == "<module>":
            m = f.mod
            env = Env(m, None, dict())
            top = ast.Module(body=[s for s in m.tree.body if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))], type_ignores=[])
            scan_python(f, top, env)
            # decorator expressions and default args evaluate in module scope
            for s in m.tree.body:
                if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    holder = ast.Module(body=[ast.Expr(value=d) for d in s.decorator_list], type_ignores=[])
                    scan_python(f, holder, env)
            continue
        scan_python(f, f.node, func_env(f))


# ============================================================================
# JAVASCRIPT
# ============================================================================
JS_GLOBALS = {"document", "window", "console", "Math", "JSON", "Object", "Array", "Number", "String", "Promise", "Date",
              "localStorage", "navigator", "URL", "Blob", "performance", "Image", "Set", "Map", "Error", "location",
              "parseInt", "parseFloat", "isNaN", "fetch", "setTimeout", "setInterval", "clearInterval", "clearTimeout",
              "requestAnimationFrame", "cancelAnimationFrame", "WebSocket", "Boolean", "Symbol", "Uint8Array",
              "devicePixelRatio", "alert", "getComputedStyle", "ResizeObserver"}
JS_BUILTIN_METHODS = {
    "push", "pop", "shift", "unshift", "map", "filter", "forEach", "find", "some", "every", "reduce", "join", "slice",
    "splice", "includes", "indexOf", "sort", "concat", "fill", "keys", "values", "entries", "has", "get", "set",
    "add", "delete", "clear", "toFixed", "toString", "padStart", "split", "trim", "replace", "startsWith", "then",
    "catch", "json", "text", "getContext", "drawImage", "fillRect", "strokeRect", "beginPath", "arc", "fill", "stroke",
    "moveTo", "lineTo", "closePath", "save", "restore", "translate", "scale", "clearRect", "fillText", "measureText",
    "setTransform", "createElement", "getElementById", "querySelector", "querySelectorAll", "appendChild", "remove",
    "addEventListener", "removeEventListener", "classList", "contains", "toggle", "setAttribute", "getAttribute",
    "preventDefault", "stopPropagation", "getBoundingClientRect", "click", "focus", "revokeObjectURL",
    "createObjectURL", "setLineDash", "rotate", "createPattern", "clip", "rect", "ellipse", "send", "close",
    "floor", "ceil", "round", "min", "max", "abs", "sqrt", "hypot", "random", "from", "isArray", "assign", "freeze",
    "stringify", "parse", "log", "warn", "error", "now", "toISOString", "slice", "getTime", "imul",
    "quadraticCurveTo", "roundRect", "closest", "match", "dispatchEvent", "bezierCurveTo", "arcTo", "getImageData",
    "putImageData", "drawFocusIfNeeded", "isPointInPath", "resolve", "reject", "all", "setItem", "getItem",
}


def js_cc(node):
    n = 1
    stack = list(node.children)
    while stack:
        x = stack.pop()
        if x.type in ("function_declaration", "method_definition", "class_declaration"):
            continue
        if x.type in ("if_statement", "for_statement", "for_in_statement", "while_statement", "do_statement",
                      "switch_case", "catch_clause", "ternary_expression"):
            n += 1
        elif x.type == "binary_expression":
            op = x.child_by_field_name("operator")
            if op is not None and op.type in ("&&", "||", "??"):
                n += 1
        stack.extend(x.children)
    return n


def jtext(n, src):
    return src[n.start_byte:n.end_byte].decode("utf8", "replace")


class JsFile:
    def __init__(self, file, src, line_pad=0):
        self.file, self.src = file, src
        self.line_pad = line_pad
        self.tree = JS.parse(src)
        self.top = {}          # top-level name -> Func (function / class-as-ctor holder)
        self.classes = {}      # class name -> {method: Func}
        self.objects = {}      # object-literal var -> {method: Func}
        self.gvar = {}         # global var -> class name
        self.imports = {}      # local name -> (file, export name)
        self.modfunc = None


jfiles = []        # JsFile
js_all_top = {}    # (file, name) -> Func


def jline(n):
    return n.start_point[0] + 1


def is_fn(n):
    return n is not None and n.type in ("arrow_function", "function_expression", "function", "generator_function")


def js_define(jf, node, qname, cls=None, entry=None):
    f = new_func(jf.file, qname, jline(node), "javascript", node, cls)
    f.cc = js_cc(node)
    f.entry_type = entry
    f.sig = f"{qname}()"
    body = node.child_by_field_name("body")
    f.is_async = any(c.type == "async" for c in node.children)
    f.jf = jf
    return f


JS_SEPARATE_CB = {"addEventListener": "event", "setTimeout": "timer", "setInterval": "timer", "requestAnimationFrame": "timer"}


def js_collect(jf):
    src = jf.src
    mf = new_func(jf.file, "<module>", 1 + jf.line_pad, "javascript", jf.tree.root_node)
    mf.jf = jf
    mf.sig = "<script>" if jf.file == HTML else "<module>"
    mf.tags.add("module")
    mf.entry_type = "browser-load" if jf.file == HTML else None
    jf.modfunc = mf
    handlers = []      # (Func)

    def visit(n, scope, cls_name, obj_name):
        """scope: qualified prefix for nested functions"""
        t = n.type
        if t == "export_statement":
            for c in n.children:
                visit(c, scope, cls_name, obj_name)
            return
        if t == "import_statement":
            srcn = n.child_by_field_name("source")
            modpath = jtext(srcn, src).strip("'\"") if srcn is not None else ""
            tgt = str((Path(jf.file).parent / modpath)).replace("\\", "/")
            tgt = re.sub(r"/\./", "/", tgt)
            parts = []
            for p in tgt.split("/"):
                if p == "..":
                    if parts:
                        parts.pop()
                elif p != ".":
                    parts.append(p)
            tgt = "/".join(parts)
            for sp in [x for x in walk_js(n) if x.type == "import_specifier"]:
                nm = sp.child_by_field_name("name")
                al = sp.child_by_field_name("alias")
                jf.imports[jtext(al or nm, src)] = (tgt, jtext(nm, src))
            return
        if t == "function_declaration":
            name = jtext(n.child_by_field_name("name"), src)
            q = f"{scope}.{name}" if scope else name
            f = js_define(jf, n, q)
            if not scope:
                jf.top[name] = f
            else:
                par = by_id.get(f"{jf.file}:{scope}")
                if par:
                    par.localfuncs[name] = f
            visit_children_fn(n, q, None, None)
            return
        if t == "class_declaration":
            cname = jtext(n.child_by_field_name("name"), src)
            jf.classes[cname] = {}
            body = n.child_by_field_name("body")
            for m in body.children:
                if m.type == "method_definition":
                    mn = jtext(m.child_by_field_name("name"), src)
                    q = f"{cname}.{mn}"
                    f = js_define(jf, m, q, cls=cname)
                    jf.classes[cname][mn] = f
                    visit_children_fn(m, q, cname, None)
            return
        if t in ("lexical_declaration", "variable_declaration"):
            for d in [c for c in n.children if c.type == "variable_declarator"]:
                nm = d.child_by_field_name("name")
                val = d.child_by_field_name("value")
                if nm is None or nm.type != "identifier":
                    if val is not None:
                        visit_expr(val, scope, cls_name, obj_name)
                    continue
                name = jtext(nm, src)
                if val is None:
                    continue
                if is_fn(val):
                    q = f"{scope}.{name}" if scope else name
                    f = js_define(jf, val, q)
                    if not scope:
                        jf.top[name] = f
                    else:
                        par = by_id.get(f"{jf.file}:{scope}")
                        if par:
                            par.localfuncs[name] = f
                    visit_children_fn(val, q, None, None)
                elif val.type == "object" and not scope:
                    jf.objects[name] = {}
                    for p in val.children:
                        if p.type == "method_definition":
                            mn = jtext(p.child_by_field_name("name"), src)
                            q = f"{name}.{mn}"
                            f = js_define(jf, p, q, cls=name)
                            jf.objects[name][mn] = f
                            visit_children_fn(p, q, None, name)
                        elif p.type == "pair":
                            k = p.child_by_field_name("key")
                            v = p.child_by_field_name("value")
                            if k is not None and is_fn(v):
                                mn = jtext(k, src).strip("'\"")
                                q = f"{name}.{mn}"
                                f = js_define(jf, v, q, cls=name)
                                jf.objects[name][mn] = f
                                visit_children_fn(v, q, None, name)
                elif val.type == "new_expression" and not scope:
                    ctor = val.child_by_field_name("constructor")
                    if ctor is not None and ctor.type == "identifier":
                        jf.gvar[name] = jtext(ctor, src)
                    visit_expr(val, scope, cls_name, obj_name)
                else:
                    visit_expr(val, scope, cls_name, obj_name)
            return
        visit_expr(n, scope, cls_name, obj_name)

    def visit_children_fn(fnode, qname, cls_name, obj_name):
        body = fnode.child_by_field_name("body")
        if body is not None:
            visit_expr(body, qname, cls_name, obj_name)

    def visit_expr(n, scope, cls_name, obj_name):
        """find nested function declarations and separately-tracked callbacks"""
        if n is None:
            return
        t = n.type
        if t in ("function_declaration", "class_declaration", "lexical_declaration", "variable_declaration", "export_statement"):
            if scope or t != "variable_declaration":
                visit(n, scope, cls_name, obj_name)
                return
        if t == "call_expression":
            fn = n.child_by_field_name("function")
            prop = fn.child_by_field_name("property") if fn is not None and fn.type == "member_expression" else None
            pname = jtext(prop, src) if prop is not None else (jtext(fn, src) if fn is not None and fn.type == "identifier" else "")
            if pname in JS_SEPARATE_CB:
                args = n.child_by_field_name("arguments")
                for a in args.children if args is not None else []:
                    if is_fn(a):
                        kind = JS_SEPARATE_CB[pname]
                        label = "<handler"
                        evn = jtext(args.children[1], src).strip("'\"") if pname == "addEventListener" and len(args.children) > 1 else pname
                        q = f"{scope + '.' if scope else ''}{label}:{evn}@{jline(a)}>"
                        f = js_define(jf, a, q, cls=cls_name or obj_name, entry=kind)
                        handlers.append(f)
                        visit_children_fn(a, q, cls_name, obj_name)
        if t == "assignment_expression":
            left = n.child_by_field_name("left")
            right = n.child_by_field_name("right")
            if left is not None and left.type == "member_expression" and is_fn(right):
                prop = jtext(left.child_by_field_name("property"), src)
                if prop.startswith("on"):
                    q = f"{scope + '.' if scope else ''}<handler:{prop}@{jline(right)}>"
                    f = js_define(jf, right, q, cls=cls_name or obj_name, entry="event")
                    handlers.append(f)
                    visit_children_fn(right, q, cls_name, obj_name)
        for c in n.children:
            visit_expr(c, scope, cls_name, obj_name)

    for c in jf.tree.root_node.children:
        visit(c, "", None, None)


def walk_js(n):
    stack = [n]
    while stack:
        x = stack.pop()
        yield x
        stack.extend(reversed(x.children))


def js_nodes_of(jf):
    """all Func nodes of a JS file, for body scanning"""
    return [f for f in funcs if f.lang == "javascript" and getattr(f, "jf", None) is jf]


def own_nodes(f):
    """tree-sitter nodes inside f, not descending into nodes that have their own Func"""
    own_starts = {g.node.id for g in funcs if g.lang == "javascript" and g.jf is f.jf and g is not f and g.name != "<module>"}
    root = f.node
    stack = [(c, False) for c in reversed(root.children)]
    while stack:
        n, cond = stack.pop()
        if n.id in own_starts:
            continue
        if f.name == "<module>" and n.type in ("function_declaration", "class_declaration"):
            continue
        yield n, cond
        c2 = cond or n.type in ("if_statement", "ternary_expression", "switch_case", "catch_clause") or \
            (n.type == "binary_expression" and n.child_by_field_name("operator") is not None
             and n.child_by_field_name("operator").type in ("&&", "||", "??"))
        stack.extend((c, c2) for c in reversed(n.children))


def js_local(f, name):
    """nested function visible from f: search f and every enclosing scope (by qualified-name prefix)"""
    if name in f.localfuncs:
        return f.localfuncs[name]
    parts = f.qname.split(".")
    for i in range(len(parts) - 1, 0, -1):
        par = by_id.get(f"{f.file}:{'.'.join(parts[:i])}")
        if par and name in par.localfuncs:
            return par.localfuncs[name]
    return None


def route_for(path):
    for meth, p, nid in routes:
        if p == path:
            yield meth, by_id[nid]


def js_scan(f):
    jf = f.jf
    src = jf.src
    for n, cond in own_nodes(f):
        site = f"{jf.file}:{jline(n)}"
        if n.type == "call_expression":
            fn = n.child_by_field_name("function")
            args = n.child_by_field_name("arguments")
            argn = [a for a in args.children if a.is_named] if args is not None else []
            text = jtext(fn, src) if fn is not None else "?"
            tgt = None
            if fn is not None and fn.type == "identifier":
                name = jtext(fn, src)
                tgt = js_local(f, name) or jf.top.get(name)
                if tgt is None and name in jf.imports:
                    file_, exp = jf.imports[name]
                    tgt = js_all_top.get((file_, exp))
                if name == "fetch" and argn:
                    lit = js_string_prefix(argn[0], src)
                    for meth, h in route_for(lit):
                        add_edge(f, h, "http", site, cond=cond, is_async=True)
                    add_unres(f, site, "fetch", "external-package", "javascript") if not list(route_for(lit)) else None
                    continue
                if tgt is None:
                    reason = "external-package" if name in JS_GLOBALS else "dynamic"
                    add_unres(f, site, text, reason, "javascript")
                    continue
            elif fn is not None and fn.type == "member_expression":
                obj = fn.child_by_field_name("object")
                prop = jtext(fn.child_by_field_name("property"), src)
                ot = obj.type if obj is not None else ""
                if ot == "this":
                    owner = f.cls
                    tgt = (jf.classes.get(owner) or jf.objects.get(owner) or {}).get(prop)
                elif ot == "identifier":
                    oname = jtext(obj, src)
                    cname = jf.gvar.get(oname)
                    if cname and cname in jf.classes:
                        tgt = jf.classes[cname].get(prop)
                    elif oname in jf.classes:
                        tgt = jf.classes[oname].get(prop)
                    elif oname in jf.objects:
                        tgt = jf.objects[oname].get(prop)
                    elif oname in JS_GLOBALS:
                        add_unres(f, site, text, "external-package", "javascript")
                        continue
                if tgt is None:
                    root = obj
                    while root is not None and root.type in ("member_expression", "call_expression", "subscript_expression", "await_expression"):
                        nxt = root.child_by_field_name("object") or root.child_by_field_name("function") or root.child_by_field_name("argument")
                        if nxt is None:
                            break
                        root = nxt
                    rname = jtext(root, src) if root is not None and root.type == "identifier" else ""
                    if rname in JS_GLOBALS or prop in JS_BUILTIN_METHODS:
                        add_unres(f, site, text, "external-package", "javascript")
                    else:
                        add_unres(f, site, text, "type-alias", "javascript")
                    continue
            else:
                add_unres(f, site, text, "dynamic", "javascript")
                continue
            add_edge(f, tgt, "call", site, cond=cond, is_async=tgt.is_async)
        elif n.type == "new_expression":
            ctor = n.child_by_field_name("constructor")
            name = jtext(ctor, src) if ctor is not None else "?"
            if name in jf.classes and "constructor" in jf.classes[name]:
                add_edge(f, jf.classes[name]["constructor"], "instantiates", site, cond=cond)
            elif name == "WebSocket":
                for meth, h in route_for("/ws"):
                    add_edge(f, h, "websocket", site, cond=cond, is_async=True)
            elif name in jf.classes:
                pass
            else:
                add_unres(f, site, f"new {name}", "external-package", "javascript")
        elif n.type == "identifier":
            # function referenced as a value (callback / handler registration)
            nm = jtext(n, src)
            par = n.parent
            ref = js_local(f, nm) or jf.top.get(nm)
            if par is not None and par.type in ("arguments", "assignment_expression", "pair", "array") and ref is not None and ref is not f:
                add_edge(f, ref, "reference", site, dyn=True, cond=cond)


def js_string_prefix(n, src):
    """literal path of a fetch() first argument: 'x' / "x" / `x...` -> text before first ${ or ?"""
    s = jtext(n, src)
    if len(s) >= 2 and s[0] in "'\"`":
        s = s[1:]
        for stop in ("${", "?", "'", '"', "`"):
            s = s.split(stop)[0]
        return s
    return ""


def build_js():
    # lib modules first so imports resolve
    for f in JS_LIBS:
        src = (ROOT / f).read_bytes()
        jfiles.append(JsFile(f, src))
    html = (ROOT / HTML).read_text()
    for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>", html, re.S):
        if "src=" in m.group(1):
            continue
        pad = html[:m.start(2)].count("\n")
        body = ("\n" * pad + m.group(2)).encode()
        jfiles.append(JsFile(HTML, body, line_pad=pad))
    for jf in jfiles:
        js_collect(jf)
    for jf in jfiles:
        for name, f in jf.top.items():
            js_all_top[(jf.file, name)] = f
    for f in [x for x in funcs if x.lang == "javascript"]:
        js_scan(f)


# ============================================================================
# persistence + views
# ============================================================================
DDL = """
CREATE TABLE nodes (
  id TEXT PRIMARY KEY, type TEXT, name TEXT, qualified_name TEXT, signature TEXT, location TEXT, repo TEXT,
  fan_in INTEGER DEFAULT 0, fan_out INTEGER DEFAULT 0, cyclomatic_complexity INTEGER DEFAULT 0,
  is_entry_point INTEGER DEFAULT 0, is_dead_code INTEGER DEFAULT 0, extraction_method TEXT DEFAULT 'static',
  tags TEXT DEFAULT '[]', has_db_call INTEGER DEFAULT 0, has_external_call INTEGER DEFAULT 0, repo_path TEXT,
  language TEXT, entry_type TEXT, class_name TEXT
);
CREATE TABLE edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT, from_node TEXT NOT NULL REFERENCES nodes(id), to_node TEXT NOT NULL REFERENCES nodes(id),
  from_repo TEXT, to_repo TEXT, type TEXT DEFAULT 'call', call_site TEXT,
  is_dynamic INTEGER DEFAULT 0, is_conditional INTEGER DEFAULT 0, is_async INTEGER DEFAULT 0
);
CREATE INDEX idx_edges_from ON edges(from_node);
CREATE INDEX idx_edges_to ON edges(to_node);
CREATE INDEX idx_edges_from_repo ON edges(from_repo);
CREATE INDEX idx_edges_to_repo ON edges(to_repo);
CREATE INDEX idx_nodes_fan_in ON nodes(fan_in DESC);
CREATE INDEX idx_nodes_dead ON nodes(is_dead_code);
CREATE INDEX idx_nodes_entry ON nodes(is_entry_point);
CREATE INDEX idx_nodes_repo ON nodes(repo);
CREATE TABLE mechanism_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT, from_repo TEXT NOT NULL, to_repo TEXT NOT NULL, type TEXT NOT NULL,
  mechanism TEXT, evidence TEXT, location TEXT
);
CREATE INDEX idx_mech_from_repo ON mechanism_edges(from_repo);
CREATE INDEX idx_mech_to_repo ON mechanism_edges(to_repo);
CREATE INDEX idx_mech_type ON mechanism_edges(type);
CREATE TABLE unresolved_calls (
  from_node TEXT, call_site TEXT, target TEXT,
  reason TEXT NOT NULL CHECK (reason IN ('external-package','missing-repo','dynamic','type-alias')),
  language TEXT
);
CREATE INDEX idx_unres_from ON unresolved_calls(from_node);
CREATE TABLE view_entry_traces (entry_node TEXT NOT NULL, entry_type TEXT, path TEXT NOT NULL, external_calls TEXT DEFAULT '[]', data_stores TEXT DEFAULT '[]');
CREATE TABLE view_cycles (cycle_id INTEGER PRIMARY KEY AUTOINCREMENT, nodes TEXT NOT NULL);
CREATE TABLE view_db_entry_paths (entry_node TEXT NOT NULL, entry_type TEXT, db_nodes TEXT NOT NULL);
-- project-specific additions (superset of the toolbox schema; documented in the cookbook)
CREATE TABLE class_hierarchy (class TEXT, base TEXT, file TEXT, line INTEGER);
CREATE TABLE routes (method TEXT, path TEXT, node TEXT);
CREATE TABLE extraction_meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE excluded_files (path TEXT, reason TEXT);
"""


def persist():
    if OUT.exists():
        OUT.unlink()
    db = sqlite3.connect(OUT)
    db.executescript(DDL)
    ids = {f.id for f in funcs}
    for f in funcs:
        owner = f.cls if f.lang == "javascript" else (classes[f.cls].name if f.cls in classes else None)
        db.execute(
            "INSERT INTO nodes (id,type,name,qualified_name,signature,location,repo,cyclomatic_complexity,is_entry_point,"
            "extraction_method,tags,repo_path,language,entry_type,class_name) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f.id, "module" if f.name == "<module>" else ("method" if owner else "function"), f.name, f.qname, f.sig,
             f"{f.file}:{f.line}", REPO, f.cc, 1 if f.entry_type else 0, "static", json.dumps(sorted(f.tags)), f.file,
             f.lang, f.entry_type, owner))
    for (frm, to, etype, site), fl in edges.items():
        db.execute("INSERT INTO edges (from_node,to_node,type,call_site,is_dynamic,is_conditional,is_async) VALUES (?,?,?,?,?,?,?)",
                   (frm, to, etype, site, int(fl["dyn"]), int(fl["cond"]), int(fl["async"])))
    for u in unresolved:
        db.execute("INSERT INTO unresolved_calls VALUES (?,?,?,?,?)", u)
    for key, ci in classes.items():
        for b in ci.bases:
            db.execute("INSERT INTO class_hierarchy VALUES (?,?,?,?)", (ci.name, classes[b].name, ci.mod.file, ci.node.lineno))
        for b in ci.ext_bases:
            db.execute("INSERT INTO class_hierarchy VALUES (?,?,?,?)", (ci.name, b + " (external)", ci.mod.file, ci.node.lineno))
        if not ci.bases and not ci.ext_bases:
            db.execute("INSERT INTO class_hierarchy VALUES (?,?,?,?)", (ci.name, None, ci.mod.file, ci.node.lineno))
    for r in routes:
        db.execute("INSERT INTO routes VALUES (?,?,?)", r)
    for p, r in excluded:
        db.execute("INSERT INTO excluded_files VALUES (?,?)", (p, r))
    db.commit()
    return db


def derive(db):
    db.execute("UPDATE nodes SET fan_in = (SELECT COUNT(*) FROM edges WHERE to_node = nodes.id)")
    db.execute("UPDATE nodes SET fan_out = (SELECT COUNT(*) FROM edges WHERE from_node = nodes.id)")
    # dunder methods other than __init__ are invoked implicitly (repr, eq, ...), modules run on import
    implicit = [f.id for f in funcs if f.implicit or f.name == "<module>"]
    db.execute("UPDATE nodes SET is_dead_code = CASE WHEN fan_in = 0 AND is_entry_point = 0 THEN 1 ELSE 0 END")
    for i in implicit:
        db.execute("UPDATE nodes SET is_dead_code = 0 WHERE id = ?", (i,))
    # a method whose name appears as the target of an unresolved call site may be called through it: not dead, only unproven
    names = {t.split(".")[-1].split("(")[0] for (t,) in db.execute(
        "SELECT target FROM unresolved_calls WHERE reason IN ('type-alias','dynamic')")}
    maybe = [r[0] for r in db.execute("SELECT id FROM nodes WHERE is_dead_code=1 AND name IN (%s)" % ",".join("?" * len(names)), tuple(names))] if names else []
    for i in maybe:
        db.execute("UPDATE nodes SET is_dead_code = 0, tags = ? WHERE id = ?", (json.dumps(["maybe-called-via-unresolved-site"]), i))
    db.execute("INSERT OR REPLACE INTO extraction_meta VALUES ('dead_code_excluded_by_unresolved_name', ?)", (json.dumps(sorted(maybe)),))
    db.execute("UPDATE nodes SET has_external_call = 1 WHERE id IN (SELECT DISTINCT from_node FROM unresolved_calls WHERE reason='external-package')")
    db.execute("UPDATE edges SET from_repo = ?, to_repo = ?", (REPO, REPO))
    db.executescript("""
    CREATE TABLE view_hot_nodes AS SELECT id, repo, fan_in, fan_out, location FROM nodes ORDER BY fan_in DESC;
    CREATE TABLE view_dead_code AS SELECT id, repo, location, extraction_method, language FROM nodes WHERE is_dead_code = 1;
    CREATE TABLE view_complexity_hotspots AS SELECT id, repo, cyclomatic_complexity, location FROM nodes WHERE cyclomatic_complexity > 10 ORDER BY cyclomatic_complexity DESC;
    CREATE TABLE view_refactor_priority AS SELECT id, repo, fan_in, cyclomatic_complexity, fan_in * cyclomatic_complexity AS refactor_score, location FROM nodes WHERE is_dead_code = 0 ORDER BY refactor_score DESC;
    CREATE TABLE view_cross_repo_edges AS SELECT from_node, to_node, from_repo, to_repo, type, call_site, is_async, is_conditional, NULL AS mechanism, NULL AS evidence FROM edges WHERE from_repo != to_repo;
    """)
    db.commit()


def traces(db):
    adj = collections.defaultdict(list)
    for a, b in db.execute("SELECT from_node, to_node FROM edges"):
        adj[a].append(b)
    ext = {r[0] for r in db.execute("SELECT DISTINCT from_node FROM unresolved_calls WHERE reason='external-package'")}
    for e, et in db.execute("SELECT id, entry_type FROM nodes WHERE is_entry_point=1").fetchall():
        seen, order, st = set(), [], [e]
        while st:
            n = st.pop()
            if n in seen:
                continue
            seen.add(n)
            order.append(n)
            st.extend(reversed(adj.get(n, [])))
        db.execute("INSERT INTO view_entry_traces VALUES (?,?,?,?,?)",
                   (e, et, json.dumps(order), json.dumps([n for n in order if n in ext]), "[]"))
    # cycles: Tarjan SCC over the whole graph
    nodes = [r[0] for r in db.execute("SELECT id FROM nodes")]
    index, low, onst, S, sccs, c = {}, {}, set(), [], [], [0]
    sys.setrecursionlimit(20000)

    def strong(v):
        index[v] = low[v] = c[0]
        c[0] += 1
        S.append(v)
        onst.add(v)
        for w in adj.get(v, []):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in onst:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = S.pop()
                onst.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1 or v in adj.get(v, []):
                sccs.append(comp)

    for v in nodes:
        if v not in index:
            strong(v)
    for comp in sccs:
        db.execute("INSERT INTO view_cycles (nodes) VALUES (?)", (json.dumps(sorted(comp)),))
    db.commit()


def scorecard(db):
    by_lang = {}
    for lang in ("python", "javascript"):
        r = db.execute("SELECT COUNT(*) FROM edges e JOIN nodes n ON n.id=e.from_node WHERE n.language=? AND e.type IN ('call','instantiates','virtual-dispatch','http','websocket')", (lang,)).fetchone()[0]
        nm = db.execute("SELECT COUNT(DISTINCT e.call_site || e.from_node) FROM edges e JOIN nodes n ON n.id=e.from_node WHERE n.language=? AND e.type='name-match'", (lang,)).fetchone()[0]
        u = db.execute("SELECT COUNT(*) FROM unresolved_calls WHERE language=?", (lang,)).fetchone()[0]
        ex = db.execute("SELECT COUNT(*) FROM unresolved_calls WHERE language=? AND reason='external-package'", (lang,)).fetchone()[0]
        by_lang[lang] = {
            "resolved": r, "name_match_call_sites": nm, "unresolved": u, "external": ex,
            "resolution_pct_all": round(100 * r / (r + u + nm), 1) if r + u + nm else None,
            "resolution_pct_project_only": round(100 * r / (r + u + nm - ex), 1) if r + u + nm - ex else None,
            "resolution_pct_project_only_incl_name_match": round(100 * (r + nm) / (r + u + nm - ex), 1) if r + u + nm - ex else None,
            "by_reason": dict(db.execute("SELECT reason, COUNT(*) FROM unresolved_calls WHERE language=? GROUP BY reason", (lang,)).fetchall()),
        }
    R = sum(v["resolved"] for v in by_lang.values())
    NM = sum(v["name_match_call_sites"] for v in by_lang.values())
    U = sum(v["unresolved"] for v in by_lang.values())
    EX = sum(v["external"] for v in by_lang.values())
    return {"by_language": by_lang, "overall_pct_all": round(100 * R / (R + U + NM), 1),
            "overall_pct_project_only": round(100 * R / (R + U + NM - EX), 1),
            "overall_pct_project_only_incl_name_match": round(100 * (R + NM) / (R + U + NM - EX), 1)}


def main():
    build_python()
    build_js()
    db = persist()
    derive(db)
    traces(db)
    sha = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
    nodes_n = db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    edges_n = db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    meta = {"repo": REPO, "commit": sha, "generated": datetime.date.today().isoformat(), "nodes": nodes_n, "edges": edges_n,
            "files_py": len(PY_FILES), "files_js": len(JS_LIBS) + 1, "scorecard": scorecard(db)}
    for k, v in meta.items():
        db.execute("INSERT INTO extraction_meta VALUES (?,?)", (k, json.dumps(v)))
    db.commit()
    print(json.dumps({"nodes": nodes_n, "edges": edges_n, "scorecard": meta["scorecard"]}, indent=1))


if __name__ == "__main__":
    main()
