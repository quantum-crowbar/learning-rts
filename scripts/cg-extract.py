#!/usr/bin/env python3
"""
cg-extract.py - code-graph extraction for the deep-rts metarepo (quantum-toolbox code-graph skill, v3.3.1).

Reads  : code/<repo>/            (default repo: deep-rts)
Writes : code/<repo>/code_graph.sqlite   (gitignored; fully reproducible from this script)

Tooling tier (skill workflow 0.1):
  C++    tier 2  tree-sitter-cpp  + class-hierarchy analysis (CHA) for virtual dispatch,
                 typed-variable / field tracking, arity-based overload selection.
                 No type-aware tool (clang) is usable: project does not configure (see CONTEXT.md).
  Python tier 2  tree-sitter-python + self/typed-variable/import resolution + pybind boundary.
                 (pyan3 was tried as the tier-1 tool first; see docs/architecture-docs/ for the outcome.)

Regenerate:  venv/bin/python scripts/cg-extract.py [repo]
"""
import collections
import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import tree_sitter_cpp
import tree_sitter_python
from tree_sitter import Language, Parser

METAROOT = Path(__file__).resolve().parent.parent
REPO = sys.argv[1] if len(sys.argv) > 1 else "deep-rts"
ROOT = METAROOT / "code" / REPO
OUT = ROOT / "code_graph.sqlite"

CPP = Parser(Language(tree_sitter_cpp.language()))
PY = Parser(Language(tree_sitter_python.language()))

# ----------------------------------------------------------------------------
# Scope: what is analysed and what is excluded (recorded in extraction_meta)
# ----------------------------------------------------------------------------
VENDORED = {
    "include/DeepRTS/util/JPS.h": "vendored: Jump Point Search (public domain, fgenesis/tinypile)",
    "bindings/utilities/ndarray_converter.cpp": "vendored: pybind11 numpy<->cv::Mat converter",
    "bindings/utilities/ndarray_converter.h": "vendored: pybind11 numpy<->cv::Mat converter",
}
EXCLUDE_PREFIX = ("DeepRTS/python/tests/",)  # tests: excluded per skill 1.1
EXCLUDE_FILES = {"setup.py"}  # build script, not product code

CPP_EXT = {".cpp", ".h", ".hpp"}
PY_EXT = {".py"}
CPP_ROOTS = ("src/", "include/", "bindings/")
PY_ROOTS = ("DeepRTS/", "examples/")

# Namespaces / identifiers that denote third-party or stdlib code (heuristic 2: framework allowlist)
EXT_NS = {"std", "cv", "spdlog", "xt", "xtensor", "py", "pybind11", "nlohmann", "JPS", "Random",
          "effolkronium", "cmrc", "fs", "filesystem", "chrono", "BLContext", "BLImage", "BLFont",
          "BLPath", "BLRgba32", "BLGradient", "BLPattern", "BLFontFace", "BLMatrix2D", "BLPoint", "BLBox"}
EXT_PREFIX = ("BL", "cv", "xt", "py")  # identifier prefixes: Blend2D BL*, OpenCV, xtensor, pybind
SMART = {"shared_ptr", "unique_ptr", "weak_ptr", "optional", "reference_wrapper", "atomic"}
CONTAINERS = {"vector", "deque", "list", "set", "unordered_set", "array", "queue", "stack"}
MAPS = {"map", "unordered_map"}
EXT_MEMBER_ALLOW = {  # std/xtensor/Blend2D-ish member names; used only when receiver type is unknown
    "push_back", "pop_back", "emplace_back", "emplace", "size", "empty", "begin", "end", "at", "front",
    "back", "clear", "insert", "erase", "find", "count", "c_str", "str", "substr", "append", "get",
    "reset", "lock", "first", "second", "data", "resize", "reserve", "swap", "release", "what",
    "length", "value", "has_value", "shape", "fill", "load", "store", "open", "close", "read", "write",
    "is_open", "good", "rows", "cols", "empty", "release", "push", "pop", "top", "format", "join",
    "append", "extend", "items", "keys", "values", "copy", "astype", "reshape", "flatten", "numpy",
    "to_string", "dump", "parse", "contains", "assign", "sort",
}
PY_BUILTINS = {
    "print", "len", "range", "int", "float", "str", "bool", "list", "dict", "set", "tuple", "isinstance",
    "super", "min", "max", "sum", "abs", "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "open", "type", "getattr", "setattr", "hasattr", "any", "all", "round", "next", "iter", "repr",
    "format", "id", "input", "vars", "callable", "property", "staticmethod", "classmethod", "object",
    "Exception", "ValueError", "RuntimeError", "KeyError", "NotImplementedError", "TypeError", "exit",
}
DECISION_CPP = {"if_statement", "for_statement", "for_range_loop", "while_statement", "do_statement",
                "case_statement", "catch_clause", "conditional_expression"}
DECISION_PY = {"if_statement", "elif_clause", "for_statement", "while_statement", "except_clause",
               "conditional_expression", "for_in_clause", "if_clause", "match_statement", "case_clause"}
COND_CPP = {"if_statement", "for_statement", "for_range_loop", "while_statement", "do_statement",
            "case_statement", "catch_clause", "conditional_expression"}
COND_PY = {"if_statement", "elif_clause", "else_clause", "for_statement", "while_statement",
           "except_clause", "conditional_expression", "case_clause"}


def T(n):
    return n.text.decode("utf8", "replace") if n is not None else ""


def strip_templates(s):
    out, d = [], 0
    for ch in s:
        if ch == "<":
            d += 1
        elif ch == ">":
            d = max(0, d - 1)
        elif d == 0:
            out.append(ch)
    return "".join(out)


# ----------------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------------
class Ty:
    __slots__ = ("name", "ext", "container", "ptr")

    def __init__(self, name, ext=False, container=False, ptr=False):
        self.name, self.ext, self.container, self.ptr = name, ext, container, ptr

    def elem(self):
        return Ty(self.name, self.ext, False, self.ptr)

    def __repr__(self):
        return f"Ty({self.name}{'[]' if self.container else ''}{'*' if self.ptr else ''}{' ext' if self.ext else ''})"


class MethodDecl:
    def __init__(self, cls, name, ret, virtual, pure, override, static, amin, amax, has_body):
        self.cls, self.name, self.ret = cls, name, ret
        self.virtual, self.pure, self.override, self.static = virtual, pure, override, static
        self.amin, self.amax, self.has_body = amin, amax, has_body


class ClassInfo:
    def __init__(self, name, file, line):
        self.name, self.file, self.line = name, file, line
        self.bases = []
        self.fields = {}      # name -> Ty
        self.methods = collections.defaultdict(list)  # name -> [MethodDecl]


class Func:
    def __init__(self):
        self.id = ""
        self.file = ""
        self.line = 0
        self.lang = ""
        self.cls = None
        self.name = ""
        self.qname = ""
        self.type = "function"
        self.sig = ""
        self.node = None
        self.params = {}
        self.amin = 0
        self.amax = 0
        self.cc = 1
        self.entry_type = None
        self.tags = set()
        self.ret = None
        self.implicit = False  # called implicitly (destructor etc.) -> never dead


classes = {}                                  # cpp class name -> ClassInfo
aliases = {}                                  # using X = T  /  typedef T X
funcs = []                                    # all Func
funcs_by_key = collections.defaultdict(list)  # (cls,name) -> [Func]   (cpp)
free_by_name = collections.defaultdict(list)  # name -> [Func]         (cpp free)
edges = {}                                    # (from,to,type,site) -> flags dict
unresolved = []                               # (from, site, target, reason, lang)
bindings = []                                 # dict rows (pybind)
callbacks = []                                # trampoline rows
lambda_nodes = {}                             # (py_class, py_name) -> Func
func_ids = set()
excluded = []                                 # (path, reason)
file_langs = {}                               # path -> lang
parsed = {}                                   # path -> (tree, src)


def add_edge(frm, to, etype, site, dynamic=False, cond=False):
    k = (frm, to, etype, site)
    if k in edges:
        edges[k]["dyn"] |= dynamic
        return
    edges[k] = {"dyn": dynamic, "cond": cond}


def add_unres(frm, site, target, reason, lang):
    assert reason in ("external-package", "missing-repo", "dynamic", "type-alias")
    unresolved.append((frm, site, target[:160], reason, lang))


# ----------------------------------------------------------------------------
# File discovery
# ----------------------------------------------------------------------------
def discover():
    files = subprocess.check_output(["git", "-C", str(ROOT), "ls-files"], text=True).splitlines()
    # untracked-but-patched files (install.sh) are not source; we only analyse tracked source.
    cpp_files, py_files = [], []
    for f in files:
        p = Path(f)
        if f in EXCLUDE_FILES:
            excluded.append((f, "build script"))
            continue
        if f.startswith(EXCLUDE_PREFIX):
            excluded.append((f, "test file"))
            continue
        if f in VENDORED:
            excluded.append((f, VENDORED[f]))
            continue
        if p.suffix in CPP_EXT and f.startswith(CPP_ROOTS):
            cpp_files.append(f)
        elif p.suffix in PY_EXT and f.startswith(PY_ROOTS):
            py_files.append(f)
    return sorted(cpp_files), sorted(py_files)


# ----------------------------------------------------------------------------
# C++ type helpers
# ----------------------------------------------------------------------------
def type_from_node(n, ptr=False):
    """Normalize a type-specifier node into Ty (or None for primitives/auto)."""
    if n is None:
        return None
    k = n.type
    if k == "type_identifier":
        a = aliases.get(T(n))
        if a is not None:
            return Ty(a.name, a.ext, a.container, ptr or a.ptr)
        return Ty(T(n), False, False, ptr)
    if k in ("primitive_type", "sized_type_specifier", "placeholder_type_specifier", "auto"):
        return None
    if k in ("struct_specifier", "class_specifier", "enum_specifier", "union_specifier"):
        for c in n.children:
            if c.type == "type_identifier":
                return Ty(T(c), False, False, ptr)
        return None
    if k == "qualified_identifier":
        scope = n.child_by_field_name("scope")
        name = n.child_by_field_name("name")
        root = T(scope).split("::")[0] if scope is not None else ""
        if name is not None and name.type == "template_type":
            inner = type_from_template(name, ptr, root in EXT_NS)
            if inner is not None:
                return inner
        if root in EXT_NS:
            return Ty(strip_templates(T(n)), True, False, ptr)
        return type_from_node(name, ptr)
    if k == "template_type":
        return type_from_template(n, ptr, False)
    if k == "type_descriptor":
        for c in n.children:
            if c.type not in ("type_qualifier",):
                t = type_from_node(c, ptr)
                if t is not None or c.type in ("primitive_type",):
                    return t
        return None
    if k == "dependent_type":
        return None
    return None


def type_from_template(n, ptr, std_scope):
    nm = T(n.child_by_field_name("name"))
    args = n.child_by_field_name("arguments")
    arg_nodes = [c for c in args.children if c.type == "type_descriptor"] if args is not None else []
    if nm in SMART and arg_nodes:
        t = type_from_node(arg_nodes[0], True)
        return t
    if nm in CONTAINERS and arg_nodes:
        t = type_from_node(arg_nodes[0], ptr)
        if t is not None:
            t.container = True
        else:
            t = Ty("<prim>", True, True)
        return t
    if nm in MAPS and len(arg_nodes) >= 2:
        t = type_from_node(arg_nodes[1], ptr)
        if t is not None:
            t.container = True
        else:
            t = Ty("<prim>", True, True)
        return t
    if std_scope or nm in EXT_NS:
        return Ty("std::" + nm, True, False, ptr)
    return Ty(nm, False, False, ptr)


def declarator_info(d):
    """Return (name, is_ptr, is_ref, is_func) from a (possibly wrapped) declarator."""
    ptr = False
    while d is not None:
        k = d.type
        if k in ("pointer_declarator",):
            ptr = True
            d = d.child_by_field_name("declarator") or next((c for c in d.children if c.is_named and c.type != "type_qualifier"), None)
        elif k in ("reference_declarator", "parenthesized_declarator", "array_declarator", "init_declarator"):
            if k == "reference_declarator":
                ptr = True  # references are indirection too: no by-value construction
            d = d.child_by_field_name("declarator") or next((c for c in d.children if c.is_named), None)
        elif k in ("identifier", "field_identifier"):
            return T(d), ptr
        elif k == "function_declarator":
            return None, ptr
        else:
            return None, ptr
    return None, ptr


def find_func_declarator(d):
    while d is not None:
        if d.type == "function_declarator":
            return d
        if d.type in ("pointer_declarator", "reference_declarator", "parenthesized_declarator", "array_declarator"):
            d = d.child_by_field_name("declarator") or next((c for c in d.children if c.is_named), None)
        else:
            return None
    return None


def param_list(fd):
    """Return ([(name, Ty)], amin, amax)."""
    params = {}
    amin = amax = 0
    pl = fd.child_by_field_name("parameters")
    if pl is None:
        return params, 0, 0
    for c in pl.children:
        if c.type in ("parameter_declaration", "optional_parameter_declaration"):
            tnode = c.child_by_field_name("type")
            dnode = c.child_by_field_name("declarator")
            nm, ptr = declarator_info(dnode)
            ty = type_from_node(tnode, ptr)
            if T(tnode) == "void" and dnode is None:
                continue
            amax += 1
            if c.type != "optional_parameter_declaration":
                amin += 1
            if nm:
                params[nm] = ty
        elif c.type == "variadic_parameter_declaration":
            amax += 99
    return params, amin, amax


def decl_type_node(decl):
    return decl.child_by_field_name("type")


# ----------------------------------------------------------------------------
# PASS 1 (C++): classes, bases, fields, method declarations
# ----------------------------------------------------------------------------
def pass1_aliases(tree):
    def walk(n):
        if n.type == "alias_declaration":
            nm = n.child_by_field_name("name")
            ty = n.child_by_field_name("type")
            if nm is not None and ty is not None:
                t = type_from_node(ty)
                if t is not None:
                    aliases[T(nm)] = t
        for c in n.children:
            walk(c)

    walk(tree.root_node)


def pass1_cpp(path, tree, src):
    def walk(n):
        if n.type in ("class_specifier", "struct_specifier"):
            nm = n.child_by_field_name("name")
            body = n.child_by_field_name("body")
            if nm is not None and body is not None:
                name = T(nm).split("::")[-1]
                ci = classes.get(name) or ClassInfo(name, path, n.start_point[0] + 1)
                classes[name] = ci
                for c in n.children:
                    if c.type == "base_class_clause":
                        for b in c.children:
                            if b.type in ("type_identifier", "qualified_identifier", "template_type"):
                                bn = strip_templates(T(b)).split("::")[-1]
                                ci.bases.append(bn)
                for m in body.children:
                    collect_member(ci, m, path)
        for c in n.children:
            walk(c)

    walk(tree.root_node)


def collect_member(ci, m, path):
    k = m.type
    if k == "template_declaration":
        for c in m.children:
            collect_member(ci, c, path)
        return
    if k not in ("field_declaration", "function_definition", "declaration"):
        return
    spec_text = " ".join(T(c) for c in m.children if c.type in ("virtual", "storage_class_specifier", "virtual_specifier"))
    virtual = any(c.type == "virtual" for c in m.children)
    static = any(c.type == "storage_class_specifier" and T(c) == "static" for c in m.children)
    tnode = m.child_by_field_name("type")
    dnodes = [c for c in m.children_by_field_name("declarator")] if k != "function_definition" else [m.child_by_field_name("declarator")]
    pure = False
    for i, c in enumerate(m.children):
        if c.type == "number_literal" and T(c) == "0" and k == "field_declaration":
            pure = True
    for d in dnodes:
        if d is None:
            continue
        fd = find_func_declarator(d)
        if fd is not None:
            name_n = fd.child_by_field_name("declarator")
            if name_n is None:
                continue
            nm = T(name_n)
            if name_n.type == "destructor_name":
                nm = "~" + T(name_n).lstrip("~")
            override = any(c.type == "virtual_specifier" and T(c) in ("override",) for c in fd.children)
            params, amin, amax = param_list(fd)
            ptrret = d.type == "pointer_declarator"
            ret = type_from_node(tnode, ptrret) if tnode is not None else None
            ci.methods[nm].append(MethodDecl(ci.name, nm, ret, virtual or override, pure, override, static,
                                             amin, amax, k == "function_definition"))
        elif k == "field_declaration":
            nm, ptr = declarator_info(d)
            if nm:
                ty = type_from_node(tnode, ptr)
                if ty is not None:
                    ci.fields[nm] = ty


def mro(cls):
    seen, order = set(), []

    def go(c):
        if c in seen or c not in classes:
            return
        seen.add(c)
        order.append(c)
        for b in classes[c].bases:
            go(b)

    go(cls)
    return order


def descendants(cls):
    out = []
    for c, ci in classes.items():
        if c != cls and cls in mro(c):
            out.append(c)
    return out


def method_decl_chain(cls, name):
    for c in mro(cls):
        if name in classes[c].methods:
            return [(c, d) for d in classes[c].methods[name]]
    return []


def is_virtual(cls, name):
    for c in mro(cls):
        for d in classes[c].methods.get(name, []):
            if d.virtual or d.override:
                return True
    return False


def field_type(cls, name):
    for c in mro(cls):
        if name in classes[c].fields:
            return classes[c].fields[name]
    return None


# ----------------------------------------------------------------------------
# PASS 2 (C++): function nodes
# ----------------------------------------------------------------------------
def dup_id(base, line):
    if base not in func_ids:
        return base
    cand = f"{base}#L{line}"
    return cand


def cc_cpp(node):
    n = 1
    stack = [node]
    while stack:
        x = stack.pop()
        if x.type in DECISION_CPP:
            n += 1
        elif x.type == "binary_expression":
            op = x.child_by_field_name("operator")
            if op is not None and T(op) in ("&&", "||"):
                n += 1
        stack.extend(x.children)
    return n


def pass2_cpp(path, tree, src):
    def walk(n, cls_stack):
        k = n.type
        if k in ("class_specifier", "struct_specifier"):
            nm = n.child_by_field_name("name")
            body = n.child_by_field_name("body")
            if nm is not None and body is not None:
                cls_stack = cls_stack + [T(nm).split("::")[-1]]
                for c in body.children:
                    walk(c, cls_stack)
                return
        if k == "function_definition":
            make_func_cpp(path, n, cls_stack)
            # do not return: nested lambdas/classes inside are handled in body walk
            return
        for c in n.children:
            walk(c, cls_stack)

    walk(tree.root_node, [])


def make_func_cpp(path, n, cls_stack):
    d = n.child_by_field_name("declarator")
    fd = find_func_declarator(d)
    if fd is None:
        # macro-style definitions e.g. PYBIND11_MODULE(libdeeprts, m) { ... } parse oddly; handled below
        name_text = T(n.children[0]) if n.children else ""
        body = n.child_by_field_name("body")
        if body is not None and re.match(r"PYBIND11_(EMBEDDED_)?MODULE", T(d) if d is not None else name_text):
            f = Func()
            f.lang, f.file, f.line = "cpp", path, n.start_point[0] + 1
            f.name = "PYBIND11_MODULE"
            f.qname = "PYBIND11_MODULE" + ("_EMBEDDED" if "EMBEDDED" in T(d) else "")
            f.type = "function"
            f.sig = re.sub(r"\s+", " ", T(d))[:160]
            f.node, f.cc = body, cc_cpp(body)
            f.entry_type = "python-module-init"
            f.id = dup_id(f"{path}:{f.qname}", f.line)
            func_ids.add(f.id)
            funcs.append(f)
            free_by_name[f.name].append(f)
        return
    name_n = fd.child_by_field_name("declarator")
    nm_text = T(name_n)
    body = n.child_by_field_name("body")
    if body is None:
        return
    cls = None
    comps = [c for c in strip_templates(nm_text).split("::") if c]
    if name_n.type == "qualified_identifier":
        name = comps[-1]
        if len(comps) >= 2 and comps[-2] in classes:
            cls = comps[-2]
    elif name_n.type == "destructor_name":
        name = "~" + T(name_n).lstrip("~")
        cls = cls_stack[-1] if cls_stack else None
    else:
        name = comps[-1] if comps else nm_text
        cls = cls_stack[-1] if cls_stack else None
    if name.startswith("~") is False and name_n.type == "qualified_identifier":
        # destructor out-of-class: D::~D
        if "~" in nm_text.split("::")[-1]:
            name = "~" + nm_text.split("::")[-1].lstrip("~")
    f = Func()
    f.lang, f.file, f.line = "cpp", path, n.start_point[0] + 1
    f.cls, f.name = cls, name
    f.qname = f"{cls}::{name}" if cls else name
    if cls and name == cls:
        f.type = "constructor"
    elif name.startswith("~"):
        f.type = "destructor"
        f.implicit = True
    elif cls:
        f.type = "method"
    else:
        f.type = "function"
    params, amin, amax = param_list(fd)
    f.params, f.amin, f.amax = params, amin, amax
    tnode = n.child_by_field_name("type")
    f.ret = type_from_node(tnode, d is not None and d.type == "pointer_declarator") if tnode is not None else None
    header = parsed[path][1][n.start_byte:body.start_byte].decode("utf8", "replace")
    f.sig = re.sub(r"\s+", " ", header).strip()[:200]
    f.node = n
    f.cc = cc_cpp(n)
    f.id = dup_id(f"{path}:{f.qname}", f.line)
    func_ids.add(f.id)
    if cls:
        for c in mro(cls):
            for dd in classes[c].methods.get(name, []):
                if dd.virtual or dd.override:
                    f.tags.add("virtual")
        if path.startswith("bindings/trampolines"):
            f.tags.add("trampoline")
    if f.name == "main" and not cls:
        f.entry_type = "cli"
    if f.name.startswith("PYBIND11_") and not cls:
        f.entry_type = "python-module-init"
    funcs.append(f)
    if cls:
        funcs_by_key[(cls, name)].append(f)
    else:
        free_by_name[name].append(f)


# ----------------------------------------------------------------------------
# C++ call resolution
# ----------------------------------------------------------------------------
def arity_filter(cands, nargs):
    ok = [f for f in cands if f.amin <= nargs <= f.amax]
    return ok if ok else cands


def defs_for(cls, name, nargs):
    """Concrete definitions of cls::name via MRO, filtered by arity."""
    for c in mro(cls):
        fs = funcs_by_key.get((c, name))
        if fs:
            return arity_filter(fs, nargs)
    return []


def dispatch_targets(cls, name, nargs):
    """(targets, dynamic) via CHA."""
    targets = list(defs_for(cls, name, nargs))
    virt = is_virtual(cls, name)
    if virt:
        for d in descendants(cls):
            fs = funcs_by_key.get((d, name))
            if fs:
                for x in arity_filter(fs, nargs):
                    if x not in targets:
                        targets.append(x)
    return targets, virt


def count_args(call):
    args = call.child_by_field_name("arguments")
    if args is None:
        return 0
    return len([c for c in args.children if c.is_named and c.type != "comment"])


class Ctx:
    def __init__(self, f):
        self.f = f
        self.cls = f.cls
        self.locals = dict(f.params)
        self.lambda_depth = 0


def lookup_var(ctx, name):
    if name in ctx.locals:
        return ctx.locals[name], "local"
    if ctx.cls:
        ft = field_type(ctx.cls, name)
        if ft is not None:
            return ft, "field"
        # declared (e.g. primitive) field -> not a callable var
    return None, None


def is_known_var(ctx, name):
    if name in ctx.locals:
        return True
    if ctx.cls:
        for c in mro(ctx.cls):
            if name in classes[c].fields:
                return True
    return False


def expr_type(n, ctx):
    """Best-effort static type of an expression -> Ty | None."""
    if n is None:
        return None
    k = n.type
    if k == "identifier":
        t, _ = lookup_var(ctx, T(n))
        return t
    if k == "this":
        return Ty(ctx.cls, False, False, True) if ctx.cls else None
    if k in ("parenthesized_expression",):
        for c in n.children:
            if c.is_named:
                return expr_type(c, ctx)
    if k == "pointer_expression":
        a = n.child_by_field_name("argument")
        t = expr_type(a, ctx)
        if t is not None and T(n).startswith("*") and t.container:
            return t.elem()
        return t
    if k == "field_expression":
        a = n.child_by_field_name("argument")
        fld = n.child_by_field_name("field")
        at = expr_type(a, ctx)
        if at is not None and not at.ext and not at.container and at.name in classes:
            return field_type(at.name, T(fld))
        return None
    if k == "subscript_expression":
        a = n.child_by_field_name("argument")
        t = expr_type(a, ctx)
        if t is not None and t.container:
            return t.elem()
        return t
    if k == "cast_expression":
        return type_from_node(n.child_by_field_name("type"))
    if k == "new_expression":
        return type_from_node(n.child_by_field_name("type"), True)
    if k == "call_expression":
        return call_ret_type(n, ctx)
    return None


def call_ret_type(call, ctx):
    fn = call.child_by_field_name("function")
    if fn is None:
        return None
    nargs = count_args(call)
    if fn.type == "identifier":
        name = T(fn)
        if ctx.cls:
            for c, d in method_decl_chain(ctx.cls, name):
                return d.ret
        fs = free_by_name.get(name)
        if fs:
            return fs[0].ret
        if name in classes:
            return Ty(name)
        return None
    if fn.type == "field_expression":
        at = expr_type(fn.child_by_field_name("argument"), ctx)
        fld = T(fn.child_by_field_name("field"))
        if at is not None and at.container:
            if fld in ("at", "front", "back", "top"):
                return at.elem()
            return None
        if at is not None and not at.ext and at.name in classes:
            for c, d in method_decl_chain(at.name, fld):
                return d.ret
            return None
        return None
    if fn.type in ("qualified_identifier", "template_function"):
        txt = strip_templates(T(fn))
        comps = txt.split("::")
        if comps[-1] in ("make_shared", "make_unique"):
            tf = fn if fn.type == "template_function" else fn.child_by_field_name("name")
            if tf is not None and tf.type == "template_function":
                args = tf.child_by_field_name("arguments")
                for c in args.children if args is not None else []:
                    if c.type == "type_descriptor":
                        t = type_from_node(c, True)
                        return t
        if len(comps) >= 2 and comps[-2] in classes:
            for c, d in method_decl_chain(comps[-2], comps[-1]):
                return d.ret
        if comps and comps[-1] in classes:
            return Ty(comps[-1])
    return None


def in_cond(n, root):
    """True if call is conditionally executed relative to its function."""
    p = n.parent
    child = n
    while p is not None and p != root:
        if p.type in COND_CPP:
            # the if/while condition itself always executes
            cond = p.child_by_field_name("condition")
            if cond is not None and (child == cond or (cond.start_byte <= child.start_byte and child.end_byte <= cond.end_byte)):
                pass
            else:
                return True
        if p.type == "binary_expression":
            op = p.child_by_field_name("operator")
            right = p.child_by_field_name("right")
            if op is not None and T(op) in ("&&", "||") and right is not None and right.start_byte <= child.start_byte and child.end_byte <= right.end_byte:
                return True
        child, p = p, p.parent
    return False


def chain_root_text(n):
    """Root callee text of a method-chain (a.b(c).d(e) -> a / py::class_<..>)."""
    while n is not None:
        if n.type == "call_expression":
            n = n.child_by_field_name("function")
        elif n.type == "field_expression":
            n = n.child_by_field_name("argument")
        elif n.type == "template_function":
            n = n.child_by_field_name("name")
        else:
            return T(n)
    return ""


def ext_target_class(name):
    return name in EXT_NS or name.startswith(EXT_PREFIX) and name not in classes


def record_ext(ctx, site, target, tag=True):
    add_unres(ctx.f.id, site, target, "external-package", "cpp")
    if tag:
        ctx.f.tags.add("external")


def emit_targets(ctx, targets, etype, site, dynamic, cond):
    for t in targets:
        add_edge(ctx.f.id, t.id, etype, site, dynamic, cond)


def resolve_call_cpp(call, ctx, site, cond):
    fn = call.child_by_field_name("function")
    nargs = count_args(call)
    if fn is None:
        return
    k = fn.type
    f = ctx.f
    if k in ("primitive_type", "sized_type_specifier") or "::*" in T(fn):
        return  # functional cast / pointer-to-member type, not a call
    # ---------------- bare identifier ----------------
    if k == "identifier":
        name = T(fn)
        if ctx.cls and any(True for _ in method_decl_chain(ctx.cls, name)):
            targets, virt = dispatch_targets(ctx.cls, name, nargs)
            if targets:
                emit_targets(ctx, targets, "call", site, virt, cond)
                return
            add_unres(f.id, site, f"{ctx.cls}::{name}", "type-alias", "cpp")
            return
        if name in free_by_name:
            cands = arity_filter(free_by_name[name], nargs)
            same_file = [c for c in cands if c.file == f.file]
            emit_targets(ctx, same_file or cands, "call", site, False, cond)
            return
        if name in classes:
            ctors = arity_filter(funcs_by_key.get((name, name), []), nargs)
            if ctors:
                emit_targets(ctx, ctors, "instantiates", site, False, cond)
            else:
                add_unres(f.id, site, f"{name}(implicit ctor)", "external-package", "cpp") if False else None
            return
        if is_known_var(ctx, name):
            add_unres(f.id, site, name + "(...)", "dynamic", "cpp")  # callable variable
            return
        if name.startswith(("PYBIND11_", "SPDLOG_", "BL")) or name.isupper():
            record_ext(ctx, site, name, tag=name.startswith("BL"))
            return
        record_ext(ctx, site, name)  # free function not defined in project => library/macro
        return
    # ---------------- qualified / template -------------
    if k in ("qualified_identifier", "template_function"):
        txt = strip_templates(T(fn))
        comps = [c for c in txt.split("::") if c]
        last = comps[-1] if comps else txt
        if last in ("make_shared", "make_unique"):
            tf = fn if fn.type == "template_function" else fn.child_by_field_name("name")
            if tf is not None and tf.type == "template_function":
                args = tf.child_by_field_name("arguments")
                for c in args.children if args is not None else []:
                    if c.type == "type_descriptor":
                        t = type_from_node(c, True)
                        if t is not None and not t.ext and t.name in classes:
                            ctors = arity_filter(funcs_by_key.get((t.name, t.name), []), nargs)
                            emit_targets(ctx, ctors, "instantiates", site, False, cond)
                            return
            record_ext(ctx, site, txt, tag=False)
            return
        root = comps[0] if comps else ""
        if root in EXT_NS or (len(comps) >= 2 and comps[-2] in EXT_NS):
            record_ext(ctx, site, txt)
            return
        if len(comps) >= 2 and comps[-2] in classes:
            cls = comps[-2]
            # explicit (non-virtual) call to Class::method, ctor call, or static call
            if last == cls:
                ctors = arity_filter(funcs_by_key.get((cls, cls), []), nargs)
                emit_targets(ctx, ctors, "instantiates", site, False, cond)
                return
            targets = defs_for(cls, last, nargs)
            if targets:
                emit_targets(ctx, targets, "call", site, False, cond)
                return
            add_unres(f.id, site, txt, "type-alias", "cpp")
            return
        if len(comps) >= 1 and last in free_by_name:
            emit_targets(ctx, arity_filter(free_by_name[last], nargs), "call", site, False, cond)
            return
        if last in classes:
            ctors = arity_filter(funcs_by_key.get((last, last), []), nargs)
            emit_targets(ctx, ctors, "instantiates", site, False, cond)
            return
        record_ext(ctx, site, txt)
        return
    # ---------------- member call ----------------------
    if k == "field_expression":
        recv = fn.child_by_field_name("argument")
        fld_n = fn.child_by_field_name("field")
        fld = T(fld_n)
        if fld_n is not None and fld_n.type == "template_method":
            fld = strip_templates(T(fld_n))
        rt = expr_type(recv, ctx)
        if recv is not None and recv.type == "this":
            rt = Ty(ctx.cls) if ctx.cls else None
        if rt is None and recv is not None and recv.type in ("call_expression", "field_expression"):
            root = chain_root_text(recv)
            if root.startswith(("py::", "pybind11::")):
                record_ext(ctx, site, f"{root}...{fld}", tag=False)
                return
        if rt is None:
            if fld in EXT_MEMBER_ALLOW:
                record_ext(ctx, site, f"?.{fld}", tag=False)
            else:
                add_unres(f.id, site, f"?.{fld}", "type-alias", "cpp")
            return
        if rt.ext or rt.container or rt.name not in classes:
            record_ext(ctx, site, f"{rt.name}.{fld}", tag=rt.name.startswith(("cv::", "std::vector")) is False and rt.ext and rt.name.split("::")[0] in ("cv", "xt", "py", "pybind11"))
            return
        targets, virt = dispatch_targets(rt.name, fld, nargs)
        if targets:
            emit_targets(ctx, targets, "call", site, virt, cond)
            return
        if any(True for _ in method_decl_chain(rt.name, fld)):
            # declared (pure virtual / header-only decl) but no concrete definition in scope
            add_unres(f.id, site, f"{rt.name}::{fld}", "dynamic", "cpp")
            return
        fty = field_type(rt.name, fld)
        if fty is not None:  # calling a field: operator() on a stored callable / xtensor array
            if fty.ext or fty.container:
                record_ext(ctx, site, f"{rt.name}.{fld}(...)", tag=False)
            elif fty.name in classes:
                targets = defs_for(fty.name, "operator()", nargs)
                if targets:
                    emit_targets(ctx, targets, "call", site, False, cond)
                else:
                    add_unres(f.id, site, f"{rt.name}.{fld}(...)", "dynamic", "cpp")
            else:
                record_ext(ctx, site, f"{rt.name}.{fld}(...)", tag=False)
            return
        # inherited from external base or field-of-callable
        add_unres(f.id, site, f"{rt.name}.{fld}", "type-alias", "cpp")
        return
    # ---------------- anything else (lambda call, fn pointer, etc.) --------------
    add_unres(f.id, site, T(fn)[:80], "dynamic", "cpp")


def handle_decl_cpp(n, ctx, site, cond):
    """declaration / for_range_loop typing and ctor edges for `T x(args)`."""
    k = n.type
    if k == "declaration":
        tnode = n.child_by_field_name("type")
        for c in n.children:
            if c.type in ("init_declarator", "identifier", "pointer_declarator", "reference_declarator", "array_declarator"):
                d = c
                value = None
                if c.type == "init_declarator":
                    d = c.child_by_field_name("declarator")
                    value = c.child_by_field_name("value")
                nm, ptr = declarator_info(d)
                if not nm:
                    continue
                ty = type_from_node(tnode, ptr)
                if tnode is not None and tnode.type == "placeholder_type_specifier":
                    ty = expr_type(value, ctx) if value is not None else None
                    if ty is not None and value is not None and value.type in ("pointer_expression",) and T(value).startswith("&"):
                        ty = Ty(ty.name, ty.ext, ty.container, True)
                if ty is not None:
                    ctx.locals[nm] = ty
                # by-value construction `Foo x(args)` / `Foo x{args}`
                if ty is not None and not ty.ext and not ty.ptr and ty.name in classes and c.type == "init_declarator":
                    if value is not None and value.type in ("argument_list", "initializer_list"):
                        na = len([a for a in value.children if a.is_named])
                        ctors = arity_filter(funcs_by_key.get((ty.name, ty.name), []), na)
                        emit_targets(ctx, ctors, "instantiates", site, False, cond)
            elif c.type == "function_declarator":
                # `BLContext ctx(img);` / `Tile t(x, y);` parse as a function declaration (vexing parse): it is a variable
                dn = c.child_by_field_name("declarator")
                if dn is not None and dn.type == "identifier" and tnode is not None and tnode.type != "primitive_type":
                    ty = type_from_node(tnode)
                    if ty is not None:
                        ctx.locals[T(dn)] = ty
                        if not ty.ext and ty.name in classes:
                            pl = c.child_by_field_name("parameters")
                            na = len([a for a in pl.children if a.is_named]) if pl is not None else 0
                            ctors = arity_filter(funcs_by_key.get((ty.name, ty.name), []), na)
                            emit_targets(ctx, ctors, "instantiates", site, False, cond)
    elif k == "for_range_loop":
        tnode = n.child_by_field_name("type")
        d = n.child_by_field_name("declarator")
        rng = n.child_by_field_name("right")
        nm, ptr = declarator_info(d)
        if nm:
            ty = type_from_node(tnode, ptr)
            if tnode is not None and tnode.type == "placeholder_type_specifier":
                rt = expr_type(rng, ctx)
                ty = rt.elem() if rt is not None and rt.container else rt
            if ty is not None:
                ctx.locals[nm] = ty


def scan_body_cpp(f):
    ctx = Ctx(f)
    if f.entry_type == "python-module-init":
        ctx.locals["m"] = Ty("py::module", True)
    root = f.node
    stack = [root]
    order = []
    # iterative pre-order
    while stack:
        x = stack.pop()
        order.append(x)
        stack.extend(reversed(x.children))
    for x in order:
        k = x.type
        site = f"{f.file}:{x.start_point[0] + 1}"
        if k in ("declaration", "for_range_loop"):
            handle_decl_cpp(x, ctx, site, in_cond(x, root))
        elif k == "parameter_declaration" and x.parent is not None and x.parent.type == "parameter_list" and f.node.start_byte < x.start_byte and in_lambda(x, f.node):
            tnode = x.child_by_field_name("type")
            nm, ptr = declarator_info(x.child_by_field_name("declarator"))
            ty = type_from_node(tnode, ptr)
            if nm and ty is not None and nm not in ctx.locals:
                ctx.locals[nm] = ty
        elif k == "call_expression":
            cond = in_cond(x, root)
            infer_algorithm_lambda_params(x, ctx)
            resolve_call_cpp(x, ctx, site, cond)
        elif k == "new_expression":
            ty = type_from_node(x.child_by_field_name("type"), True)
            if ty is not None and not ty.ext and ty.name in classes:
                al = x.child_by_field_name("arguments")
                na = len([a for a in al.children if a.is_named]) if al is not None else 0
                ctors = arity_filter(funcs_by_key.get((ty.name, ty.name), []), na)
                emit_targets(ctx, ctors, "instantiates", site, False, in_cond(x, root))
        elif k == "field_initializer":
            nm = T(x.children[0]) if x.children else ""
            al = x.child_by_field_name("arguments") or next((c for c in x.children if c.type in ("argument_list", "initializer_list")), None)
            na = len([a for a in al.children if a.is_named]) if al is not None else 0
            target_cls = None
            if nm in classes and f.cls and nm in mro(f.cls):
                target_cls = nm
            elif f.cls:
                ft = field_type(f.cls, nm)
                if ft is not None and not ft.ext and not ft.ptr and not ft.container and ft.name in classes:
                    target_cls = ft.name
            if target_cls:
                ctors = arity_filter(funcs_by_key.get((target_cls, target_cls), []), na)
                emit_targets(ctx, ctors, "instantiates", site, False, False)
    # exercise: calls inside field_initializer arguments are walked by order as call_expressions already


TRAMPOLINE_DIR = "bindings/trampolines/"


def balanced(text, start, open_ch="{", close_ch="}"):
    depth, i = 0, start
    while i < len(text):
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(text) - 1


def process_trampoline(path, src):
    """tree-sitter cannot parse PYBIND11_OVERLOAD/OVERRIDE macro arguments (types in expression position), so the
    trampoline headers get a dedicated regex pass: class + overriding-method nodes + callback records."""
    text = src.decode("utf8", "replace")
    out = []
    for cm in re.finditer(r"class\s+(\w+)\s*:\s*public\s+([\w:]+)\s*\{", text):
        cname, base = cm.group(1), cm.group(2).split("::")[-1]
        ci = classes.get(cname) or ClassInfo(cname, path, text[:cm.start()].count("\n") + 1)
        classes[cname] = ci
        if base not in ci.bases:
            ci.bases.append(base)
        end = balanced(text, cm.end() - 1)
        body = text[cm.end():end]
        for mm in re.finditer(r"([\w:<>&\s\*\[\];]+?)\s+(\w+)\s*\(([^)]*)\)\s*(const)?\s*override\s*\{", body):
            name = mm.group(2)
            bstart = cm.end() + mm.end() - 1
            bend = balanced(text, bstart)
            fbody = text[bstart:bend + 1]
            f = Func()
            f.lang, f.file = "cpp", path
            f.line = text[:cm.end() + mm.start()].count("\n") + 1
            f.cls, f.name, f.qname, f.type = cname, name, f"{cname}::{name}", "method"
            f.sig = re.sub(r"\s+", " ", text[cm.end() + mm.start():bstart]).strip()[:200]
            f.params, f.amin, f.amax = {}, 0, 99
            f.cc = 1
            f.node = None
            f.id = dup_id(f"{path}:{f.qname}", f.line)
            func_ids.add(f.id)
            f.tags.update({"trampoline", "virtual"})
            funcs.append(f)
            funcs_by_key[(cname, name)].append(f)
            ci.methods[name].append(MethodDecl(cname, name, None, True, False, True, False, 0, 99, True))
            for om in re.finditer(r"PYBIND11_(?:OVERLOAD|OVERRIDE)(?:_PURE)?(_NAME)?\s*\(", fbody):
                i, depth, args, cur = om.end(), 1, [], []
                while i < len(fbody) and depth:
                    ch = fbody[i]
                    if ch in "(<[":
                        depth += 1
                    elif ch in ")>]":
                        depth -= 1
                        if depth == 0:
                            break
                    if ch == "," and depth == 1:
                        args.append("".join(cur).strip())
                        cur = []
                    else:
                        cur.append(ch)
                    i += 1
                args.append("".join(cur).strip())
                if om.group(1) and len(args) >= 4:
                    pyname, cppname = args[2].strip('"'), args[3]
                elif len(args) >= 3:
                    pyname = cppname = args[2]
                else:
                    pyname = cppname = name
                line = f.line + fbody[:om.start()].count("\n")
                callbacks.append({"node": f.id, "cls": base, "py_name": pyname, "cpp_name": cppname, "site": f"{path}:{line}"})
                f.tags.add("python-callback")


def find_callbacks(f, src):
    text = src[f.node.start_byte:f.node.end_byte].decode("utf8", "replace")
    for m in re.finditer(r"(PYBIND11_OVERLOAD(?:_PURE)?(?:_NAME)?)\s*\(", text):
        i, depth, args, cur = m.end(), 1, [], []
        while i < len(text) and depth:
            ch = text[i]
            if ch in "(<[":
                depth += 1
            elif ch in ")>]":
                depth -= 1
                if depth == 0:
                    break
            if ch == "," and depth == 1:
                args.append("".join(cur).strip())
                cur = []
            else:
                cur.append(ch)
            i += 1
        args.append("".join(cur).strip())
        macro = m.group(1)
        line = f.line + text[:m.start()].count("\n")
        pyname = cppname = None
        if "_NAME" in macro and len(args) >= 4:
            pyname, cppname = args[2].strip('"'), args[3]
        elif len(args) >= 3:
            pyname = cppname = args[2]
        callbacks.append({"node": f.id, "cls": args[1] if len(args) > 1 else None, "py_name": pyname, "cpp_name": cppname,
                          "site": f"{f.file}:{line}"})
        f.tags.add("python-callback")


ALGOS = {"all_of", "any_of", "none_of", "for_each", "find_if", "count_if", "remove_if", "transform", "sort", "copy_if"}


def in_lambda(n, root):
    p = n.parent
    while p is not None and p != root:
        if p.type == "lambda_expression":
            return True
        p = p.parent
    return False


def infer_algorithm_lambda_params(call, ctx):
    """std::all_of(c.begin(), c.end(), [](auto& x){...}): give `auto` lambda params the container element type."""
    fn = call.child_by_field_name("function")
    if fn is None or strip_templates(T(fn)).split("::")[-1] not in ALGOS:
        return
    args = call.child_by_field_name("arguments")
    if args is None:
        return
    vals = [c for c in args.children if c.is_named]
    if not vals or vals[0].type != "call_expression":
        return
    first_fn = vals[0].child_by_field_name("function")
    if first_fn is None or first_fn.type != "field_expression" or T(first_fn.child_by_field_name("field")) not in ("begin", "cbegin"):
        return
    ct = expr_type(first_fn.child_by_field_name("argument"), ctx)
    if ct is None or not ct.container:
        return
    el = ct.elem()
    for v in vals:
        if v.type == "lambda_expression":
            for pd in find_nodes(v, "parameter_declaration"):
                nm, ptr = declarator_info(pd.child_by_field_name("declarator"))
                tnode = pd.child_by_field_name("type")
                if nm and tnode is not None and tnode.type == "placeholder_type_specifier":
                    ctx.locals[nm] = el


def find_nodes(n, typ):
    out, st = [], [n]
    while st:
        x = st.pop()
        if x.type == typ:
            out.append(x)
        st.extend(x.children)
    return out


def record_callback_unused(f, call, site):
    args = call.child_by_field_name("arguments")
    vals = [c for c in args.children if c.is_named] if args is not None else []
    macro = T(call.child_by_field_name("function"))
    pyname = cppname = None
    if "_NAME" in macro and len(vals) >= 4:
        pyname = T(vals[2]).strip('"')
        cppname = T(vals[3])
    elif len(vals) >= 3:
        pyname = cppname = T(vals[2])
    cls = T(vals[1]) if len(vals) >= 2 else None
    callbacks.append({"node": f.id, "cls": cls, "py_name": pyname, "cpp_name": cppname, "site": site})
    f.tags.add("python-callback")


# ----------------------------------------------------------------------------
# pybind bindings extraction (bindings/*.cpp)
# ----------------------------------------------------------------------------
PYBIND_DEFS = {"def", "def_static", "def_readonly", "def_readwrite", "def_property", "def_property_readonly",
               "def_property_readonly_static", "def_readonly_static", "def_readwrite_static"}


def extract_bindings(path, tree, src):
    def root_class(call):
        cur = call
        while cur is not None and cur.type == "call_expression":
            fn = cur.child_by_field_name("function")
            if fn is None:
                return None
            if fn.type == "field_expression":
                cur = fn.child_by_field_name("argument")
                continue
            txt = T(fn)
            if "class_" in txt:
                args = cur.child_by_field_name("arguments")
                strs = [c for c in args.children if c.type == "string_literal"]
                pyname = T(strs[0]).strip('"') if strs else None
                m = re.search(r"class_<\s*([A-Za-z_:0-9]+)", txt)
                cppname = m.group(1).split("::")[-1] if m else None
                return pyname, cppname
            return None
        return None

    def walk(n):
        if n.type == "call_expression":
            fn = n.child_by_field_name("function")
            if fn is not None and fn.type == "field_expression":
                meth = T(fn.child_by_field_name("field"))
                if meth in PYBIND_DEFS or meth == "def":
                    rc = root_class(fn.child_by_field_name("argument"))
                    args = n.child_by_field_name("arguments")
                    if rc and args is not None:
                        strs = [c for c in args.children if c.type == "string_literal"]
                        pyname = T(strs[0]).strip('"') if strs else None
                        targets = []
                        for c in args.children:
                            if c.type == "pointer_expression":
                                q = c.child_by_field_name("argument")
                                if q is not None and q.type == "qualified_identifier":
                                    comps = [x for x in strip_templates(T(q)).split("::") if x]
                                    if len(comps) >= 2:
                                        targets.append((comps[-2], comps[-1]))
                        # py::init<...>() is a template_function inside def(...)
                        for c in args.children:
                            if c.type == "call_expression" and "init" in T(c.child_by_field_name("function")):
                                targets.append((rc[1], rc[1]))
                                pyname = "__init__"
                        for c in args.children:
                            if c.type == "lambda_expression":
                                lf = Func()
                                lf.lang, lf.file, lf.line = "cpp", path, c.start_point[0] + 1
                                lf.cls, lf.name, lf.type = None, f"<lambda {pyname}>", "lambda"
                                lf.qname = f"{rc[0]}.{pyname}"
                                lf.sig = f"lambda bound as {rc[0]}.{pyname}"
                                lf.node, lf.cc = c, cc_cpp(c)
                                lf.entry_type = "python-binding"
                                lf.tags.add("bound")
                                lf.id = dup_id(f"{path}:{rc[0]}.{pyname}<lambda>", lf.line)
                                func_ids.add(lf.id)
                                funcs.append(lf)
                                lambda_nodes[(rc[0], pyname)] = lf
                                targets.append(("<lambda>", pyname))
                        for cc, mm in targets:
                            bindings.append({"py_class": rc[0], "py_name": pyname or mm, "cpp_class": cc,
                                             "cpp_member": mm, "kind": meth, "site": f"{path}:{n.start_point[0] + 1}"})
        for c in n.children:
            walk(c)

    walk(tree.root_node)


# ----------------------------------------------------------------------------
# Python extraction
# ----------------------------------------------------------------------------
class PyClass:
    def __init__(self, name, file, bases):
        self.name, self.file, self.bases = name, file, bases
        self.methods = {}   # name -> Func
        self.fields = {}    # attr -> class name


py_classes = {}                              # simple name -> PyClass (first definition wins)
py_classes_by_file = {}                      # (file, name) -> PyClass
py_funcs_by_name = collections.defaultdict(list)  # module-level function simple name -> [Func]
py_imports = {}                               # file -> {alias: dotted}
py_modfunc = {}                               # file -> module Func


def decorated(n):
    return n.child_by_field_name("definition") if n.type == "decorated_definition" else n


def py_cc(node):
    n = 1
    stack = [node]
    while stack:
        x = stack.pop()
        if x.type in DECISION_PY:
            n += 1
        elif x.type == "boolean_operator":
            n += 1
        stack.extend(x.children)
    return n


def pass_py_collect(path, tree, src):
    imports = {}
    py_imports[path] = imports

    def collect_imports(n):
        for c in n.children:
            if c.type == "import_statement":
                for nm in c.children:
                    if nm.type == "dotted_name":
                        imports[T(nm).split(".")[0]] = T(nm)
                    elif nm.type == "aliased_import":
                        imports[T(nm.child_by_field_name("alias"))] = T(nm.child_by_field_name("name"))
            elif c.type == "import_from_statement":
                mod = T(c.child_by_field_name("module_name"))
                for nm in c.children_by_field_name("name"):
                    if nm.type == "dotted_name":
                        imports[T(nm)] = mod + "." + T(nm)
                    elif nm.type == "aliased_import":
                        imports[T(nm.child_by_field_name("alias"))] = mod + "." + T(nm.child_by_field_name("name"))
            elif c.type in ("try_statement", "if_statement", "else_clause", "block", "except_clause"):
                collect_imports(c)

    def collect_all(n):
        if n.type in ("import_statement", "import_from_statement"):
            holder = type("H", (), {})()
            holder.children = [n]
            collect_imports(holder)
        for c in n.children:
            collect_all(c)

    collect_all(tree.root_node)
    stem = Path(path).with_suffix("").as_posix()

    def make(fnode, cls, name, node_for_cc):
        f = Func()
        f.lang, f.file, f.line = "python", path, fnode.start_point[0] + 1
        f.cls, f.name = cls, name
        f.qname = f"{cls}.{name}" if cls else name
        f.type = "method" if cls else "function"
        if cls and name == "__init__":
            f.type = "constructor"
        params = fnode.child_by_field_name("parameters")
        f.sig = re.sub(r"\s+", " ", f"def {name}{T(params)}")[:200]
        f.node, f.cc = fnode.child_by_field_name("body"), py_cc(fnode)
        f.id = dup_id(f"{path}:{f.qname}", f.line)
        func_ids.add(f.id)
        funcs.append(f)
        return f

    for c in tree.root_node.children:
        d = decorated(c)
        if d is None:
            continue
        if d.type == "function_definition":
            f = make(d, None, T(d.child_by_field_name("name")), d)
            py_funcs_by_name[f.name].append(f)
        elif d.type == "class_definition":
            cname = T(d.child_by_field_name("name"))
            sup = d.child_by_field_name("superclasses")
            bases = [T(b) for b in sup.children if b.is_named] if sup is not None else []
            pc = PyClass(cname, path, bases)
            py_classes.setdefault(cname, pc)
            py_classes_by_file[(path, cname)] = pc
            body = d.child_by_field_name("body")
            for m in body.children:
                dm = decorated(m)
                if dm is not None and dm.type == "function_definition":
                    mf = make(dm, cname, T(dm.child_by_field_name("name")), dm)
                    pc.methods[mf.name] = mf
    # module-level pseudo node for scripts (calls at module scope)
    has_top_calls = False
    for c in tree.root_node.children:
        if c.type in ("expression_statement", "if_statement", "for_statement", "while_statement", "try_statement", "with_statement", "assignment"):
            stack = [c]
            while stack:
                x = stack.pop()
                if x.type == "call":
                    has_top_calls = True
                    break
                stack.extend(x.children)
        if has_top_calls:
            break
    if has_top_calls and not path.endswith("__init__.py"):
        f = Func()
        f.lang, f.file, f.line = "python", path, 1
        f.name, f.qname, f.type = "<module>", "<module>", "function"
        f.sig = f"<module-level code of {path}>"
        f.node = tree.root_node
        f.cc = 1
        f.id = f"{path}:<module>"
        func_ids.add(f.id)
        funcs.append(f)
        py_modfunc[path] = f


def py_mro(cname, seen=None):
    seen = seen or set()
    if cname in seen or cname not in py_classes:
        return []
    seen.add(cname)
    out = [cname]
    for b in py_classes[cname].bases:
        if b.startswith(("Engine.", "libdeeprts.")):
            continue  # C++ (pybind) base: a python class of the same simple name is a different class
        out += py_mro(b.split(".")[-1], seen)
    return out


def py_bound_base(cname):
    """If a python class derives (transitively) from a pybind class (Engine.X), return X, else None."""
    for c in py_mro(cname):
        for b in py_classes[c].bases:
            if b.startswith(("Engine.", "libdeeprts.")):
                return b.split(".")[-1]
    return None


def lookup_class(name, path, imports):
    """A class name is visible from `path` only if defined there or imported there (no global simple-name guessing)."""
    pc = py_classes_by_file.get((path, name))
    if pc is not None:
        return pc
    if name in imports and name in py_classes:
        return py_classes[name]
    return None


def func_candidates(name, path, imports):
    cands = py_funcs_by_name.get(name, [])
    same = [c for c in cands if c.file == path]
    if same:
        return same
    return cands if name in imports else []


def py_has_external_base(cname):
    for c in py_mro(cname):
        for b in py_classes[c].bases:
            bn = b.split(".")[-1]
            if b.startswith(("Engine.", "libdeeprts.")) or bn in py_classes or bn in ("object",):
                continue
            return True
    return False


def py_find_method(cname, name):
    for c in py_mro(cname):
        if name in py_classes[c].methods:
            return py_classes[c].methods[name]
    return None


def binding_lookup(py_class, py_name):
    return [b for b in bindings if b["py_class"] == py_class and b["py_name"] == py_name]


def cpp_target_for_binding(b):
    if b["cpp_class"] == "<lambda>":
        lf = lambda_nodes.get((b["py_class"], b["py_name"]))
        return [lf] if lf else []
    fs = funcs_by_key.get((b["cpp_class"], b["cpp_member"]), [])
    if fs:
        return fs
    # method defined in a base class or declared only in a header without def: try MRO
    return defs_for(b["cpp_class"], b["cpp_member"], 99) if b["cpp_class"] in classes else []


def py_calls_in(f):
    out = []
    stack = [f.node]
    while stack:
        x = stack.pop()
        if x.type == "call":
            out.append(x)
        # skip nested class bodies? keep nested functions (attribute to outer)
        stack.extend(x.children)
    return sorted(out, key=lambda a: a.start_byte)


def py_in_cond(n, root):
    p = n.parent
    while p is not None and p != root:
        if p.type in COND_PY:
            return True
        p = p.parent
    return False


def scan_py(f):
    path = f.file
    imports = py_imports.get(path, {})
    cls = f.cls
    locals_ = {}  # name -> ("py", classname) | ("bound", pyclass) | ("ext",)
    body = f.node
    # first pass: typed locals from simple assignments  x = Foo(...)  / x = Engine.Foo(...)
    stack = [body]
    assigns = []
    while stack:
        x = stack.pop()
        if x.type == "assignment":
            assigns.append(x)
        if f.name == "<module>" and x.type in ("function_definition", "class_definition"):
            continue  # module-level: don't descend into defs (they have their own nodes)
        stack.extend(x.children)
    fors = []
    stack = [body]
    while stack:
        x = stack.pop()
        if x.type == "for_statement":
            fors.append(x)
        if f.name == "<module>" and x.type in ("function_definition", "class_definition"):
            continue
        stack.extend(x.children)
    items = [(a.start_byte, "a", a) for a in assigns] + [(a.start_byte, "f", a) for a in fors]
    for _, kind, a in sorted(items, key=lambda t: t[0]):
        if kind == "f":
            left, right = a.child_by_field_name("left"), a.child_by_field_name("right")
            t = py_expr_type(right, f, imports, locals_)
            if t is not None and left is not None and left.type == "identifier":
                locals_[T(left)] = (t[0], t[1], False) if t[2] else t
            continue
        left = a.child_by_field_name("left")
        right = a.child_by_field_name("right")
        if right is None:
            continue
        t = py_expr_type(right, f, imports, locals_)
        if t is None:
            continue
        if left.type == "identifier":
            locals_[T(left)] = t
        elif left.type == "attribute" and T(left.child_by_field_name("object")) == "self" and cls:
            py_classes[cls].fields[T(left.child_by_field_name("attribute"))] = t
    calls = []
    stack = [body]
    while stack:
        x = stack.pop()
        if x.type == "call":
            calls.append(x)
        if f.name == "<module>" and x.type in ("function_definition", "class_definition"):
            continue
        stack.extend(x.children)
    for call in sorted(calls, key=lambda a: a.start_byte):
        resolve_call_py(call, f, imports, locals_)


def py_is_external_root(root, imports, path):
    if root in PY_BUILTINS:
        return True
    if root in imports:
        mod = imports[root]
        if mod.startswith("DeepRTS"):
            return False
        top = mod.split(".")[0]
        return local_module_file(path, top) is None
    return False


def local_module_file(path, modname):
    cand = (Path(path).parent / f"{modname}.py").as_posix()
    return cand if cand in parsed else None


CPP2PY = {}


def cpp_to_py_class(cpp):
    if not CPP2PY:
        for b in bindings:
            CPP2PY.setdefault(b["cpp_class"], b["py_class"])
    return CPP2PY.get(cpp)


def ty_to_py(ty):
    """Convert a C++ Ty into a python typing tuple (kind, name, container)."""
    if ty is None:
        return None
    if ty.ext:
        return ("ext", ty.name, ty.container)
    pc = cpp_to_py_class(ty.name)
    if pc:
        return ("bound", pc, ty.container)
    return None


def py_expr_type(n, f, imports, locals_):
    if n is None:
        return None
    k = n.type
    cls = f.cls
    if k == "identifier":
        nm = T(n)
        if nm == "self" and cls:
            return ("py", cls, False)
        if nm in locals_:
            t = locals_[nm]
            return t if len(t) == 3 else (t[0], t[1], False)
        if nm in PY_BUILTINS:
            return ("ext", nm, False)
        if nm in imports and py_is_external_root(nm, imports, f.file):
            return ("ext", nm, False)
        return None
    if k == "attribute":
        obj, attr = n.child_by_field_name("object"), T(n.child_by_field_name("attribute"))
        if T(obj).split(".")[0] in ("Engine", "libdeeprts"):
            return None
        t = py_expr_type(obj, f, imports, locals_)
        if t is None:
            return None
        kind, name, cont = t
        if kind == "ext":
            return ("ext", name, False)
        if kind == "py":
            for c in py_mro(name):
                if attr in py_classes[c].fields:
                    ft = py_classes[c].fields[attr]
                    return ft if len(ft) == 3 else (ft[0], ft[1], False)
            bb = py_bound_base(name)
            if bb:
                kind, name = "bound", bb
            else:
                return None
        if kind == "bound":
            for b in binding_lookup(name, attr):
                if b["kind"] in ("def_readonly", "def_readwrite", "def_property", "def_property_readonly", "def_readonly_static"):
                    ci = classes.get(b["cpp_class"])
                    if ci and b["cpp_member"] in ci.fields:
                        return ty_to_py(ci.fields[b["cpp_member"]])
        return None
    if k == "subscript":
        t = py_expr_type(n.child_by_field_name("value"), f, imports, locals_)
        if t and t[2]:
            return (t[0], t[1], False)
        return t
    if k == "call":
        fn = n.child_by_field_name("function")
        base = py_call_result_type(n, imports, f.file)
        if base is not None:
            return base if len(base) == 3 else (base[0], base[1], False)
        if fn.type == "attribute":
            obj, attr = fn.child_by_field_name("object"), T(fn.child_by_field_name("attribute"))
            t = py_expr_type(obj, f, imports, locals_)
            if t is None:
                return None
            kind, name, cont = t
            if kind == "ext":
                return ("ext", name, False)
            if kind == "py" and py_find_method(name, attr) is None:
                bb = py_bound_base(name)
                if bb:
                    kind, name = "bound", bb
            if kind == "bound":
                for b in binding_lookup(name, attr):
                    if b["cpp_class"] in classes:
                        for c, d in method_decl_chain(b["cpp_class"], b["cpp_member"]):
                            return ty_to_py(d.ret)
        return None
    return None


def py_call_result_type(call, imports, path=""):
    fn = call.child_by_field_name("function")
    if fn is None:
        return None
    txt = T(fn)
    root = txt.split(".")[0]
    if root in imports and py_is_external_root(root, imports, path):
        return ("ext", root)
    if txt.startswith(("Engine.", "libdeeprts.")) and txt.count(".") == 1:
        return ("bound", txt.split(".")[-1])
    if fn.type == "identifier" and lookup_class(T(fn), path, imports) is not None:
        return ("py", T(fn))
    return None


def resolve_call_py(call, f, imports, locals_):
    fn = call.child_by_field_name("function")
    site = f"{f.file}:{call.start_point[0] + 1}"
    cond = py_in_cond(call, f.node)
    cls = f.cls
    if fn is None:
        return
    nargs = len([c for c in call.child_by_field_name("arguments").children if c.is_named]) if call.child_by_field_name("arguments") is not None else 0

    def to_cpp(py_class, py_name):
        bs = binding_lookup(py_class, py_name)
        done = False
        for b in bs:
            for t in cpp_target_for_binding(b):
                add_edge(f.id, t.id, "call", site, False, cond)
                done = True
        return done

    if fn.type == "identifier":
        name = T(fn)
        pcls = lookup_class(name, f.file, imports)
        if pcls is not None:
            init = pcls.methods.get("__init__") or py_find_method(name, "__init__")
            if init is not None:
                add_edge(f.id, init.id, "instantiates", site, False, cond)
                return
            bb = py_bound_base(name)
            if bb and to_cpp(bb, "__init__"):
                return
            add_unres(f.id, site, name, "type-alias", "python")
            return
        cands = func_candidates(name, f.file, imports)
        if cands:
            for c in cands:
                add_edge(f.id, c.id, "call", site, False, cond)
            return
        if name in PY_BUILTINS:
            add_unres(f.id, site, name, "external-package", "python")
            return
        if name in imports:
            root = imports[name]
            if not root.startswith("DeepRTS") and py_is_external_root(name, imports, f.file):
                add_unres(f.id, site, name, "external-package", "python")
                return
            lm = local_module_file(f.file, root.split(".")[0])
            if lm:
                cands = [c for c in py_funcs_by_name.get(name, []) if c.file == lm]
                for c in cands:
                    add_edge(f.id, c.id, "call", site, False, cond)
                if cands:
                    return
        add_unres(f.id, site, name, "dynamic" if name in locals_ else "type-alias", "python")
        return
    if fn.type == "attribute":
        obj = fn.child_by_field_name("object")
        attr = T(fn.child_by_field_name("attribute"))
        otxt = T(obj)
        # super().m() / super(Cls, self).m()
        if obj.type == "call" and T(obj.child_by_field_name("function")) == "super" and cls:
            for b in py_classes[cls].bases:
                bn = b.split(".")[-1]
                m = py_find_method(bn, attr) if (bn in py_classes and not b.startswith(("Engine.", "libdeeprts."))) else None
                if m:
                    add_edge(f.id, m.id, "call", site, False, cond)
                    return
                if b.startswith(("Engine.", "libdeeprts.")) and to_cpp(bn, attr):
                    return
            if py_has_external_base(cls):
                add_unres(f.id, site, f"super().{attr}", "external-package", "python")
                return
            add_unres(f.id, site, f"super().{attr}", "type-alias", "python")
            return
        # self.m()
        if otxt == "self" and cls:
            m = py_find_method(cls, attr)
            if m:
                add_edge(f.id, m.id, "call", site, False, cond)
                return
            bb = py_bound_base(cls)
            if bb and to_cpp(bb, attr):
                return
            fld = None
            for c in py_mro(cls):
                if attr in py_classes[c].fields:
                    fld = py_classes[c].fields[attr]
            if fld is not None and fld[0] == "ext":
                add_unres(f.id, site, f"self.{attr}", "external-package", "python")
                return
            if py_has_external_base(cls):
                add_unres(f.id, site, f"self.{attr}", "external-package", "python")
                return
            add_unres(f.id, site, f"self.{attr}", "type-alias", "python")
            return
        # self.attr.m()
        if obj.type == "attribute" and T(obj.child_by_field_name("object")) == "self" and cls:
            fieldname = T(obj.child_by_field_name("attribute"))
            t = None
            for c in py_mro(cls):
                if fieldname in py_classes[c].fields:
                    t = py_classes[c].fields[fieldname]
                    break
            if t:
                kind, cn = t[0], t[1]
                if kind == "ext":
                    add_unres(f.id, site, f"self.{fieldname}.{attr}", "external-package", "python")
                    return
                if kind == "py":
                    m = py_find_method(cn, attr)
                    if m:
                        add_edge(f.id, m.id, "call", site, False, cond)
                        return
                if kind == "bound" and to_cpp(cn, attr):
                    return
            add_unres(f.id, site, f"self.{fieldname}.{attr}", "type-alias", "python")
            return
        # Engine.Cls.meth()  /  Engine.Cls()
        root = otxt.split(".")[0]
        if root in ("Engine", "libdeeprts") and obj.type == "attribute":
            pycls = otxt.split(".")[-1]
            if to_cpp(pycls, attr):
                return
            add_unres(f.id, site, f"{otxt}.{attr}", "type-alias", "python")
            return
        if root in ("Engine", "libdeeprts") and obj.type == "identifier":
            # Engine.Foo(...) -> constructor
            if to_cpp(attr, "__init__"):
                return
            add_unres(f.id, site, f"{otxt}.{attr}", "type-alias", "python")
            return
        # general typed receiver (locals, self.fields, bound-class fields/returns, subscripts)
        gt = py_expr_type(obj, f, imports, locals_)
        if gt is not None:
            kind, name, cont = gt
            if kind == "ext" or cont:
                add_unres(f.id, site, f"{otxt}.{attr}"[:100], "external-package", "python")
                return
            if kind == "py":
                m = py_find_method(name, attr)
                if m:
                    add_edge(f.id, m.id, "call", site, False, cond)
                    return
                bb = py_bound_base(name)
                if bb and to_cpp(bb, attr):
                    return
            if kind == "bound" and to_cpp(name, attr):
                return
            add_unres(f.id, site, f"{otxt}.{attr}"[:100], "type-alias", "python")
            return
        # typed local: x.m()
        if obj.type == "identifier" and otxt in locals_:
            kind, cn = locals_[otxt][0], locals_[otxt][1]
            if kind == "ext":
                add_unres(f.id, site, f"{otxt}.{attr}", "external-package", "python")
                return
            if kind == "py":
                m = py_find_method(cn, attr)
                if m:
                    add_edge(f.id, m.id, "call", site, False, cond)
                    return
                bb = py_bound_base(cn)
                if bb and to_cpp(bb, attr):
                    return
            if kind == "bound" and to_cpp(cn, attr):
                return
            add_unres(f.id, site, f"{otxt}.{attr}", "type-alias", "python")
            return
        # project-local sibling module (examples/old/util.py): util.func()
        if root in imports:
            lm = local_module_file(f.file, imports[root].split(".")[0])
            if lm:
                cands = [c for c in py_funcs_by_name.get(attr, []) if c.file == lm]
                if cands:
                    for c in cands:
                        add_edge(f.id, c.id, "call", site, False, cond)
                    return
        # module attribute of an external import: np.zeros, cv2.imshow, random.random, ...
        if py_is_external_root(root, imports, f.file):
            add_unres(f.id, site, f"{otxt}.{attr}", "external-package", "python")
            return
        if root in imports and imports[root].startswith("DeepRTS"):
            cands = py_funcs_by_name.get(attr, [])
            if cands:
                for c in cands:
                    add_edge(f.id, c.id, "call", site, False, cond)
                return
        if attr in EXT_MEMBER_ALLOW:
            add_unres(f.id, site, f"?.{attr}", "external-package", "python")
            return
        add_unres(f.id, site, f"{otxt}.{attr}"[:100], "type-alias", "python")
        return
    add_unres(f.id, site, T(fn)[:80], "dynamic", "python")


# ----------------------------------------------------------------------------
# Entry points, cross-language callbacks, tags
# ----------------------------------------------------------------------------
def mark_entries_and_boundaries():
    # (1) pybind-bound C++ methods are entry points from Python
    bound_ids = set()
    for b in bindings:
        for t in cpp_target_for_binding(b):
            if t.entry_type is None:
                t.entry_type = "python-binding"
            t.tags.add("bound")
            bound_ids.add(t.id)
    # (2) trampolines call into Python: link trampoline -> python override of the same name
    for cb in callbacks:
        tn = next((x for x in funcs if x.id == cb["node"]), None)
        pyname = cb["py_name"]
        if not tn or not pyname:
            continue
        pycls = tn.cls
        # the python-visible class (py name) that maps to cb["cls"] (cpp class)
        pynames = {b["py_class"] for b in bindings if b["cpp_class"] == cb["cls"]} or {cb["cls"]}
        for pcname, pc in py_classes.items():
            base = py_bound_base(pcname)
            if base in pynames and pyname in pc.methods:
                add_edge(tn.id, pc.methods[pyname].id, "call", cb["site"], True, False)
    # (3) python public API entry points & scripts
    for f in funcs:
        if f.lang != "python":
            continue
        if f.file.startswith("DeepRTS/python/") and f.name != "<module>":
            pub = not f.name.startswith("_") or f.name == "__init__"
            owner_pub = f.cls is None or not f.cls.startswith("_")
            if pub and owner_pub:
                f.entry_type = "api"
        if f.name == "<module>" and f.file.startswith("examples/"):
            f.entry_type = "script"
        if f.name == "<module>" and f.file.startswith("DeepRTS/python/"):
            f.entry_type = "script"
        if f.name == "main" and f.cls is None and f.file.startswith("examples/"):
            f.entry_type = f.entry_type or "script"


# ----------------------------------------------------------------------------
# Persistence + Phase 3 views + scorecard
# ----------------------------------------------------------------------------
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
CREATE TABLE pybind_bindings (py_class TEXT, py_name TEXT, cpp_class TEXT, cpp_member TEXT, kind TEXT, site TEXT, resolved_node TEXT);
CREATE TABLE pybind_callbacks (node TEXT, cpp_class TEXT, py_name TEXT, cpp_name TEXT, site TEXT);
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
        db.execute(
            "INSERT INTO nodes (id,type,name,qualified_name,signature,location,repo,cyclomatic_complexity,is_entry_point,"
            "extraction_method,tags,repo_path,language,entry_type,class_name) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f.id, f.type, f.name, f.qname, f.sig, f"{f.file}:{f.line}", REPO, f.cc,
             1 if f.entry_type else 0, "static", json.dumps(sorted(f.tags)), f.file, f.lang, f.entry_type, f.cls))
    for (frm, to, etype, site), fl in edges.items():
        if frm in ids and to in ids:
            db.execute("INSERT INTO edges (from_node,to_node,type,call_site,is_dynamic,is_conditional,is_async) VALUES (?,?,?,?,?,?,0)",
                       (frm, to, etype, site, int(fl["dyn"]), int(fl["cond"])))
    for u in unresolved:
        db.execute("INSERT INTO unresolved_calls VALUES (?,?,?,?,?)", u)
    for c, ci in classes.items():
        for b in ci.bases:
            db.execute("INSERT INTO class_hierarchy VALUES (?,?,?,?)", (c, b, ci.file, ci.line))
        if not ci.bases:
            db.execute("INSERT INTO class_hierarchy VALUES (?,?,?,?)", (c, None, ci.file, ci.line))
    for b in bindings:
        tg = cpp_target_for_binding(b)
        db.execute("INSERT INTO pybind_bindings VALUES (?,?,?,?,?,?,?)",
                   (b["py_class"], b["py_name"], b["cpp_class"], b["cpp_member"], b["kind"], b["site"], tg[0].id if tg else None))
    for cb in callbacks:
        db.execute("INSERT INTO pybind_callbacks VALUES (?,?,?,?,?)", (cb["node"], cb["cls"], cb["py_name"], cb["cpp_name"], cb["site"]))
    for p, r in excluded:
        db.execute("INSERT INTO excluded_files VALUES (?,?)", (p, r))
    db.commit()
    return db


def derive(db):
    # Phase 2.2 / 2.3
    db.execute("UPDATE nodes SET fan_in = (SELECT COUNT(*) FROM edges WHERE to_node = nodes.id)")
    db.execute("UPDATE nodes SET fan_out = (SELECT COUNT(*) FROM edges WHERE from_node = nodes.id)")
    # implicit-call nodes (destructors) are never dead: invoked by scope exit / delete, not by call sites
    impl = {f.id for f in funcs if f.implicit}
    db.execute("UPDATE nodes SET is_dead_code = CASE WHEN fan_in = 0 AND is_entry_point = 0 THEN 1 ELSE 0 END")
    for i in impl:
        db.execute("UPDATE nodes SET is_dead_code = 0 WHERE id = ?", (i,))
    db.execute("UPDATE nodes SET has_db_call = 1 WHERE tags LIKE '%\"db\"%'")
    db.execute("UPDATE nodes SET has_external_call = 1 WHERE tags LIKE '%\"external\"%'")
    db.execute("UPDATE edges SET from_repo = (SELECT repo FROM nodes WHERE nodes.id = edges.from_node), "
               "to_repo = (SELECT repo FROM nodes WHERE nodes.id = edges.to_node)")
    db.executescript("""
    CREATE TABLE view_hot_nodes AS SELECT id, repo, fan_in, fan_out, location FROM nodes ORDER BY fan_in DESC;
    CREATE TABLE view_dead_code AS SELECT id, repo, location, extraction_method, language FROM nodes WHERE is_dead_code = 1;
    CREATE TABLE view_complexity_hotspots AS SELECT id, repo, cyclomatic_complexity, location FROM nodes WHERE cyclomatic_complexity > 10 ORDER BY cyclomatic_complexity DESC;
    CREATE TABLE view_refactor_priority AS SELECT id, repo, fan_in, cyclomatic_complexity, fan_in * cyclomatic_complexity AS refactor_score, location FROM nodes WHERE is_dead_code = 0 ORDER BY refactor_score DESC;
    CREATE TABLE view_cross_repo_edges AS
      SELECT e.from_node, e.to_node, e.from_repo, e.to_repo, e.type, e.call_site, e.is_async, e.is_conditional, NULL AS mechanism, NULL AS evidence
      FROM edges e WHERE e.from_repo != e.to_repo
      UNION ALL
      SELECT NULL, NULL, m.from_repo, m.to_repo, m.type, m.location, 0, 0, m.mechanism, m.evidence FROM mechanism_edges m;
    """)
    db.commit()


def phase3_traces(db):
    out_adj = collections.defaultdict(list)
    for f, t in db.execute("SELECT from_node, to_node FROM edges"):
        out_adj[f].append(t)
    nodes = {r[0]: (r[1], r[2], r[3]) for r in db.execute("SELECT id, tags, entry_type, location FROM nodes")}
    entries = [(r[0], r[1]) for r in db.execute("SELECT id, entry_type FROM nodes WHERE is_entry_point = 1")]
    cycles_seen = set()
    cycles = []
    for e, et in entries:
        visited, order = set(), []
        # iterative DFS for traces
        stack = [e]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            order.append(n)
            for t in reversed(out_adj.get(n, [])):
                if t not in visited:
                    stack.append(t)
        ext = [n for n in order if '"external"' in nodes[n][0]]
        db.execute("INSERT INTO view_entry_traces VALUES (?,?,?,?,?)", (e, et, json.dumps(order), json.dumps(ext), "[]"))
        db.execute("INSERT INTO view_db_entry_paths VALUES (?,?,?)", (e, et, "[]")) if False else None
    # cycle detection: Tarjan SCC over whole graph (complete, not entry-limited) - cycles = SCCs of size>1 or self-loop
    index, low, onstack, S, sccs, counter = {}, {}, set(), [], [], [0]
    sys.setrecursionlimit(20000)

    def strong(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        S.append(v)
        onstack.add(v)
        for w in out_adj.get(v, []):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in onstack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = S.pop()
                onstack.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1 or v in out_adj.get(v, []):
                sccs.append(comp)

    for v in nodes:
        if v not in index:
            strong(v)
    for comp in sccs:
        db.execute("INSERT INTO view_cycles (nodes) VALUES (?)", (json.dumps(sorted(comp)),))
    db.commit()


def scorecard(db, langs_present, tooling):
    q = lambda s: db.execute(s).fetchall()
    res = {}
    by_lang = {}
    for lang in ("cpp", "python"):
        r = q(f"SELECT COUNT(*) FROM edges e JOIN nodes n ON n.id = e.from_node WHERE n.language='{lang}'")[0][0]
        u = q(f"SELECT COUNT(*) FROM unresolved_calls WHERE language='{lang}'")[0][0]
        ext = q(f"SELECT COUNT(*) FROM unresolved_calls WHERE language='{lang}' AND reason='external-package'")[0][0]
        by_lang[lang] = {"resolved": r, "unresolved": u, "external": ext,
                         "resolution_pct_all": round(100 * r / (r + u), 1) if r + u else None,
                         "resolution_pct_project_only": round(100 * r / (r + (u - ext)), 1) if r + (u - ext) else None,
                         "by_reason": dict(q(f"SELECT reason, COUNT(*) FROM unresolved_calls WHERE language='{lang}' GROUP BY reason"))}
    R = sum(v["resolved"] for v in by_lang.values())
    U = sum(v["unresolved"] for v in by_lang.values())
    EX = sum(v["external"] for v in by_lang.values())
    res["edge_resolution"] = {"overall_pct_all": round(100 * R / (R + U), 1), "overall_pct_project_only": round(100 * R / (R + U - EX), 1),
                              "by_language": by_lang}
    res["tooling"] = tooling
    return res


def main():
    cpp_files, py_files = discover()
    for f in cpp_files:
        src = (ROOT / f).read_bytes()
        parsed[f] = (CPP.parse(src), src)
        file_langs[f] = "cpp"
    for f in py_files:
        src = (ROOT / f).read_bytes()
        parsed[f] = (PY.parse(src), src)
        file_langs[f] = "python"
    for _ in range(2):  # aliases may reference other aliases
        for f in cpp_files:
            pass1_aliases(parsed[f][0])
    ts_files = [f for f in cpp_files if not f.startswith(TRAMPOLINE_DIR)]
    for f in ts_files:
        pass1_cpp(f, *parsed[f])
    for f in cpp_files:
        if f.startswith(TRAMPOLINE_DIR):
            process_trampoline(f, parsed[f][1])
    for f in ts_files:
        pass2_cpp(f, *parsed[f])
    for f in py_files:
        pass_py_collect(f, *parsed[f])
    for f in cpp_files:
        if f.startswith("bindings/"):
            extract_bindings(f, *parsed[f])
    for f in list(funcs):
        if f.lang == "cpp":
            if f.node is not None:
                scan_body_cpp(f)
    mark_entries_and_boundaries()
    # python bodies after bindings are known
    for f in list(funcs):
        if f.lang == "python":
            scan_py(f)
    mark_entries_and_boundaries()  # re-run (python entries / callbacks needing py classes)
    db = persist()
    derive(db)
    phase3_traces(db)
    tooling = [
        {"language": "cpp", "tool": f"tree-sitter-cpp + CHA/typed-var heuristics", "tier": 2, "fallback": True,
         "reason": "no type-aware tool: clang absent and project does not configure (xtensor/vcpkg failure)"},
        {"language": "python", "tool": "tree-sitter-python + self/import/pybind resolution", "tier": 2, "fallback": True,
         "reason": "pyan3 tier-1 attempt recorded in docs/architecture-docs (see 09-code-graph.md)"},
    ]
    sc = scorecard(db, {"cpp", "python"}, tooling)
    sha = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
    nodes_n = db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    edges_n = db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    meta = {
        "repo": REPO, "commit": sha, "generated": datetime.date.today().isoformat(),
        "nodes": nodes_n, "edges": edges_n,
        "files_cpp": len(cpp_files), "files_py": len(py_files),
        "scorecard": sc,
    }
    for k, v in meta.items():
        db.execute("INSERT INTO extraction_meta VALUES (?,?)", (k, json.dumps(v)))
    db.commit()
    print(json.dumps({"nodes": nodes_n, "edges": edges_n, "files": [len(cpp_files), len(py_files)],
                      "edge_resolution": sc["edge_resolution"]}, indent=1))


if __name__ == "__main__":
    main()
