#!/usr/bin/env python3
"""Static scan of tools/*.py (PLAN component F, ast_scan row; ported from C62d's tests/ast_scan.py, C8(1) R22/R25): no unreachable statement after raise, return, continue
or break in the same block, and no possibly unbound local name; and, in tools/, tests/ and gen3/ *.py, no statement
swallowed by a comment (`# text;stmt(...)`, a comment inserted mid-line in front of code) and no read of a global name
the module never binds (symtable; a NameError on that path).

The unbound-name check is a definite-assignment analysis per function (parameters, assignments, imports, for and
with targets, except-as names, walrus targets, nested def/class names): a load (or a del) of a name that the function
assigns somewhere is reported unless every path from the function's entry assigns it first, and a del unbinds. Paths:
both arms of an if (an arm that always leaves the block does not count); a loop body may run zero times (`while True`
leaves through its breaks), and its head state is the entry state intersected with every back edge (the end of the
body and every continue), iterated to a fixed point, so a deletion in the body reaches the next iteration and the
exit; a try body may stop at any statement, so each handler starts from the state before the try minus every name the
body may delete; a finally block is checked against the weakest state that can reach it (the state before the try
minus everything the try, its else and its handlers may delete) and its assignments and deletions are carried to the
normal exit and to every break and continue that leaves through it; a match statement without an irrefutable case may
match nothing. Context managers are assumed not to swallow exceptions. Lambdas and nested functions are scanned
separately; their free names are not checked against the enclosing function's flow (they run later). Comprehensions
run in place. Correlated conditions are not modelled, so a finding is either fixed in the code or listed, with its
reason, in ALLOW below (none at present). The self-test probes include deletion in finally blocks, loop bodies,
continue and break paths, handlers and match cases (checkpoint review T-05).
Usage: python3 -B tests/ast_scan.py [--output FILE] [PATH ...] (default: tools/*.py)"""
from __future__ import annotations
import argparse,ast,io,json,re,sys,tokenize
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALLOW:dict[str,str]={}  # 'file:line:name' -> reason

TERMINAL=(ast.Raise,ast.Return,ast.Continue,ast.Break)

def unreachable(tree:ast.AST,fname:str)->list[dict]:
    out=[]
    for node in ast.walk(tree):
        for field in ('body','orelse','finalbody'):
            stmts=getattr(node,field,None)
            if not isinstance(stmts,list):continue
            for i,st in enumerate(stmts[:-1]):
                if isinstance(st,TERMINAL):
                    nxt=stmts[i+1];out.append(dict(file=fname,line=nxt.lineno,kind='unreachable',detail=f'statement after {type(st).__name__.lower()} at line {st.lineno}'));break
        if isinstance(node,ast.Try)or getattr(ast,'TryStar',None)and isinstance(node,getattr(ast,'TryStar')):
            for h in node.handlers:
                for i,st in enumerate(h.body[:-1]):
                    if isinstance(st,TERMINAL):out.append(dict(file=fname,line=h.body[i+1].lineno,kind='unreachable',detail=f'statement after {type(st).__name__.lower()}'));break
    return out

def target_names(t)->set:
    if isinstance(t,ast.Name):return {t.id}
    if isinstance(t,(ast.Tuple,ast.List)):return set().union(*(target_names(e)for e in t.elts))if t.elts else set()
    if isinstance(t,ast.Starred):return target_names(t.value)
    return set()

class LocalNames(ast.NodeVisitor):
    """Names a function binds in its own scope (excluding nested scopes), and its global/nonlocal declarations."""
    def __init__(self):self.bound=set();self.decl=set()
    def visit_FunctionDef(self,n):self.bound.add(n.name)
    visit_AsyncFunctionDef=visit_FunctionDef
    def visit_ClassDef(self,n):self.bound.add(n.name)
    def visit_Lambda(self,n):pass
    def visit_ListComp(self,n):self._comp(n)
    visit_SetComp=visit_GeneratorExp=visit_DictComp=visit_ListComp
    def _comp(self,n):
        for g in n.generators:
            self.visit(g.iter)  # evaluated in the enclosing scope (only the first strictly; a walrus inside binds outside)
            for c in g.ifs:self._walrus(c)
        for f in ('elt','key','value'):
            if getattr(n,f,None)is not None:self._walrus(getattr(n,f))
    def _walrus(self,e):
        for x in ast.walk(e):
            if isinstance(x,ast.NamedExpr):self.bound.add(x.target.id)
    def visit_Name(self,n):
        if isinstance(n.ctx,(ast.Store,ast.Del)):self.bound.add(n.id)
    def visit_NamedExpr(self,n):self.bound.add(n.target.id);self.visit(n.value)
    def visit_Import(self,n):
        for a in n.names:self.bound.add((a.asname or a.name).split('.')[0])
    visit_ImportFrom=visit_Import
    def visit_ExceptHandler(self,n):
        if n.name:self.bound.add(n.name)
        self.generic_visit(n)
    def visit_Global(self,n):self.decl.update(n.names)
    visit_Nonlocal=visit_Global

def killed(stmts)->set:
    """Names the statements may unbind in this scope: del targets and except-as names (unbound when their handler ends),
    at any depth, nested scopes excluded."""
    out=set()
    def walk(n):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda)):return
        if isinstance(n,ast.Delete):
            for t in n.targets:out.update(target_names(t))
        if isinstance(n,ast.ExceptHandler)and n.name:out.add(n.name)
        for c in ast.iter_child_nodes(n):walk(c)
    for st in stmts:walk(st)
    return out

class Flow:
    def __init__(self,fname:str,fn,locals_:set):
        self.fname=fname;self.fn=fn;self.locals=locals_;self.out=[];self.seen=set()
        self.loops=[]  # per enclosing loop: ([break states], [continue states])
    def report(self,node,name):
        key=f'{self.fname}:{node.lineno}:{name}'
        if key in ALLOW or key in self.seen:return  # a statement may be analysed more than once (loops, finally)
        self.seen.add(key);self.out.append(dict(file=self.fname,line=node.lineno,kind='possibly-unbound',detail=f'{name} in {self.fn.name}()'))
    # ---- expressions (evaluation order; a walrus binds after its value)
    def expr(self,e,D:set)->set:
        if e is None:return D
        if isinstance(e,ast.Name):
            if isinstance(e.ctx,ast.Load)and e.id in self.locals and e.id not in D:self.report(e,e.id)
            return D
        if isinstance(e,ast.NamedExpr):D=self.expr(e.value,D);return D|{e.target.id}
        if isinstance(e,ast.Lambda):
            for d in e.args.defaults+[x for x in e.args.kw_defaults if x is not None]:D=self.expr(d,D)
            return D
        if isinstance(e,(ast.ListComp,ast.SetComp,ast.GeneratorExp,ast.DictComp)):
            inner=set(D)
            for g in e.generators:
                self.expr(g.iter,inner);inner=inner|target_names(g.target)
                for c in g.ifs:inner=self.expr(c,inner)
            for f in ('elt','key','value'):
                if getattr(e,f,None)is not None:inner=self.expr(getattr(e,f),inner)
            return D  # comprehension targets stay inside; walrus inside a comprehension is conditional
        if isinstance(e,ast.BoolOp):
            D=self.expr(e.values[0],D)
            for v in e.values[1:]:self.expr(v,D)  # later operands may not run: their walrus targets are not definite
            return D
        if isinstance(e,ast.IfExp):
            D=self.expr(e.test,D);a=self.expr(e.body,D);b=self.expr(e.orelse,D);return a&b
        for child in ast.iter_child_nodes(e):
            if isinstance(child,ast.expr):D=self.expr(child,D)
            elif isinstance(child,ast.comprehension):pass
            elif isinstance(child,ast.keyword):D=self.expr(child.value,D)
            elif isinstance(child,(ast.arguments,)):pass
        return D
    # ---- statements: return the definite set after the block, or None when it always leaves it
    def block(self,stmts,D:set):
        for st in stmts:
            D=self.stmt(st,D)
            if D is None:return None
        return D
    def stmt(self,st,D:set):
        E=self.expr
        if isinstance(st,(ast.FunctionDef,ast.AsyncFunctionDef)):
            for d in st.args.defaults+[x for x in st.args.kw_defaults if x is not None]+st.decorator_list:D=E(d,D)
            return D|{st.name}
        if isinstance(st,ast.ClassDef):
            for d in st.bases+st.decorator_list:D=E(d,D)
            return D|{st.name}
        if isinstance(st,ast.Assign):
            D=E(st.value,D)
            for t in st.targets:D=self.store(t,D)
            return D
        if isinstance(st,ast.AugAssign):
            D=E(st.value,D)
            if isinstance(st.target,ast.Name):
                if st.target.id in self.locals and st.target.id not in D:self.report(st.target,st.target.id)
                return D|{st.target.id}
            return self.store(st.target,D)
        if isinstance(st,ast.AnnAssign):
            if st.value is None:return D
            D=E(st.value,D);return self.store(st.target,D)
        if isinstance(st,(ast.Expr,)):return E(st.value,D)
        if isinstance(st,(ast.Return,)):E(st.value,D);return None
        if isinstance(st,ast.Raise):E(st.exc,D);E(st.cause,D);return None
        if isinstance(st,ast.Continue):
            if self.loops:self.loops[-1][1].append(set(D))
            return None
        if isinstance(st,ast.Break):
            if self.loops:self.loops[-1][0].append(set(D))
            return None
        if isinstance(st,ast.Pass)or isinstance(st,(ast.Global,ast.Nonlocal)):return D
        if isinstance(st,ast.Assert):D=E(st.test,D);E(st.msg,D);return D
        if isinstance(st,ast.Delete):
            for t in st.targets:D=self.delete(t,D)
            return D
        if isinstance(st,(ast.Import,ast.ImportFrom)):return D|{(a.asname or a.name).split('.')[0]for a in st.names}
        if isinstance(st,ast.If):
            D=E(st.test,D);a=self.block(st.body,set(D));b=self.block(st.orelse,set(D))
            if a is None and b is None:return None
            return a if b is None else(b if a is None else a&b)
        if isinstance(st,(ast.For,ast.AsyncFor,ast.While)):
            # the head state: the entry state intersected with every back edge (the body's end, each continue), to a
            # fixed point (it only shrinks); the loop is left by its else path (the iterator exhausted or the test
            # false; never for `while True`), from the head, or by a break
            loop_for=not isinstance(st,ast.While)
            if loop_for:D=E(st.iter,D)
            forever=not loop_for and isinstance(st.test,ast.Constant)and bool(st.test.value)
            head=set(D)
            while True:
                self.loops.append(([],[]))
                h=set(head)if loop_for else E(st.test,set(head))
                end=self.block(st.body,self.store(st.target,set(h))if loop_for else set(h))
                br,co=self.loops.pop()
                back=co+([end]if end is not None else[])
                new=set.intersection(head,*back)if back else head
                if new==head:break
                head=new
            paths=list(br)
            if not forever:
                after=self.block(st.orelse,set(h))if st.orelse else set(h)
                if after is not None:paths.append(after)
            return set.intersection(*paths)if paths else None
        if isinstance(st,(ast.With,ast.AsyncWith)):
            for it in st.items:
                D=E(it.context_expr,D)
                if it.optional_vars is not None:D=self.store(it.optional_vars,D)
            return self.block(st.body,D)
        if isinstance(st,ast.Try)or (getattr(ast,'TryStar',None)and isinstance(st,getattr(ast,'TryStar'))):
            pre=set(D);fr=self.loops[-1]if self.loops else None;nb,nc=(len(fr[0]),len(fr[1]))if fr else(0,0)
            body=self.block(st.body,set(pre))
            outs=[]
            if body is not None:
                o=self.block(st.orelse,set(body))if st.orelse else body
                if o is not None:outs.append(o)
            entry=pre-killed(st.body)  # an exception may leave the body after any of its deletions
            for h in st.handlers:
                hd=set(entry)
                if h.type is not None:hd=E(h.type,hd)
                if h.name:hd=hd|{h.name}
                r=self.block(h.body,hd)
                if r is not None:outs.append(r-({h.name}if h.name else set()))
            if not st.finalbody:
                return set.intersection(*outs)if outs else None
            # the finally block runs on every path out of the try: its loads are checked against the weakest state
            # that reaches it, and its assignments and deletions apply to each path that continues after it
            kills=killed(st.body)|killed(st.orelse)|{n for h in st.handlers for n in killed(h.body)|({h.name}if h.name else set())}
            fin=self.block(st.finalbody,pre-kills)
            if fr is not None:  # a break or continue leaving the try passes through the finally block first
                for lst,n0 in ((fr[0],nb),(fr[1],nc)):
                    tail=lst[n0:];del lst[n0:]
                    for x in tail:
                        r=self.block(st.finalbody,set(x))
                        if r is not None:lst.append(r)
            if fin is None or not outs:return None
            return self.block(st.finalbody,set.intersection(*outs))
        if getattr(ast,'Match',None)is not None and isinstance(st,ast.Match):
            D=E(st.subject,D);outs=[];irrefutable=False
            for c in st.cases:
                names=set()
                for n in ast.walk(c.pattern):
                    if isinstance(n,(ast.MatchAs,ast.MatchStar))and n.name:names.add(n.name)
                    elif isinstance(n,ast.MatchMapping):
                        if n.rest:names.add(n.rest)
                        for k in n.keys:E(k,D)
                    elif isinstance(n,ast.MatchValue):E(n.value,D)
                    elif isinstance(n,ast.MatchClass):E(n.cls,D)
                cd=D|names
                if c.guard is not None:cd=E(c.guard,cd)
                r=self.block(c.body,cd)
                if r is not None:outs.append(r)
                irrefutable|=c.guard is None and isinstance(c.pattern,ast.MatchAs)and c.pattern.pattern is None
            if not irrefutable:outs.append(set(D))  # no case matched
            return set.intersection(*outs)if outs else None
        for child in ast.iter_child_nodes(st):
            if isinstance(child,ast.expr):D=E(child,D)
        return D
    def store(self,t,D):
        if isinstance(t,ast.Name):return D|{t.id}
        if isinstance(t,(ast.Tuple,ast.List)):
            for e in t.elts:D=self.store(e,D)
            return D
        if isinstance(t,ast.Starred):return self.store(t.value,D)
        return self.expr(t,D)  # attribute/subscript targets load their base
    def delete(self,t,D):
        """del: a possibly unbound local raises UnboundLocalError (reported); the name is unbound afterwards."""
        if isinstance(t,ast.Name):
            if t.id in self.locals and t.id not in D:self.report(t,t.id)
            return D-{t.id}
        if isinstance(t,(ast.Tuple,ast.List)):
            for e in t.elts:D=self.delete(e,D)
            return D
        return self.expr(t,D)  # attribute/subscript targets load their base

def unbound(tree:ast.AST,fname:str)->list[dict]:
    out=[]
    for fn in ast.walk(tree):
        if not isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):continue
        if isinstance(fn,ast.Lambda):continue
        ln=LocalNames()
        for st in fn.body:ln.visit(st)
        args=fn.args;params={a.arg for a in args.posonlyargs+args.args+args.kwonlyargs}|({args.vararg.arg}if args.vararg else set())|({args.kwarg.arg}if args.kwarg else set())
        locals_=(ln.bound|params)-ln.decl
        f=Flow(fname,fn,locals_);f.block(fn.body,set(params));out+=f.out
    return out

SWALLOWED=re.compile(r';[A-Za-z_][A-Za-z0-9_.]*(\(|[-+*/]?=(?!=))')   # `;stmt` with no space, the package's code style

def swallowed(src:str,fname:str)->list[dict]:
    """A comment that holds `; statement` after its text: code that a comment inserted mid-line has swallowed (Stage 3a
    repair round 1: tests/workflow.py and tests/staging.py lost `;e.update(...)` behind `# C8_SITE: ...`)."""
    out=[]
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type==tokenize.COMMENT and SWALLOWED.search(tok.string):
            out.append(dict(file=fname,line=tok.start[0],kind='swallowed',detail=f'a statement inside a comment: {tok.string[:120]}'))
    return out

BUILTINS=set(dir(__import__('builtins')))|{'__file__','__name__','__doc__','__spec__','__loader__','__package__'}

def undefined_globals(src:str,fname:str)->list[dict]:
    """A name a function (or the module) reads as a global that the module never binds (def, class, import, assignment,
    for/with/except targets, global declarations) and that is not a builtin: a NameError waiting on that path (Stage 3a
    repair round 1: tests/validate.py's G-JET record ended up inside another function, reading its caller's locals).
    A module with a star import is skipped."""
    import symtable
    tree=ast.parse(src,fname);bound=set()
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):bound.add(n.name)
        elif isinstance(n,(ast.Import,ast.ImportFrom)):
            for a in n.names:
                if a.name=='*':return []
                bound.add((a.asname or a.name).split('.')[0])
        elif isinstance(n,ast.Global):bound.update(n.names)
        elif isinstance(n,ast.Name)and isinstance(n.ctx,(ast.Store,ast.Del)):bound.add(n.id)
        elif isinstance(n,ast.ExceptHandler)and n.name:bound.add(n.name)
    out=[]
    def visit(s):
        for c in s.get_children():
            for sym in c.get_symbols():
                nm=sym.get_name()
                if sym.is_referenced()and sym.is_global()and not sym.is_declared_global()and nm not in bound and nm not in BUILTINS:
                    out.append(dict(file=fname,line=c.get_lineno(),kind='undefined',detail=f'{c.get_name()} reads the undefined global {nm!r}'))
            visit(c)
    st=symtable.symtable(src,fname,'exec')
    for sym in st.get_symbols():
        nm=sym.get_name()
        if sym.is_referenced()and not sym.is_assigned()and not sym.is_imported()and nm not in bound and nm not in BUILTINS:
            out.append(dict(file=fname,line=0,kind='undefined',detail=f'the module reads the undefined global {nm!r}'))
    visit(st);return out

def scan(paths:list[Path],comment_paths:list[Path]=())->dict:
    findings=[];files=0
    for p in paths:
        src=p.read_text();tree=ast.parse(src,str(p));files+=1;rel=str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p)
        findings+=unreachable(tree,rel)+unbound(tree,rel)+swallowed(src,rel)+undefined_globals(src,rel)
    for p in comment_paths:
        if p in paths:continue
        rel=str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p);src=p.read_text();findings+=swallowed(src,rel)+undefined_globals(src,rel)
    return dict(files=files,comment_files=len(set(comment_paths)-set(paths)),findings=findings)

def selftest()->list[str]:
    """Each probe must be found (and the clean ones must not)."""
    probes={'unreachable':('def f():\n    raise ValueError()\n    x=1\n',1),'if_one_arm':('def f(a):\n    if a:x=1\n    return x\n',1),
            'both_arms':('def f(a):\n    if a:x=1\n    else:x=2\n    return x\n',0),'arm_leaves':('def f(a):\n    if a:x=1\n    else:raise ValueError()\n    return x\n',0),
            'loop_zero':('def f(s):\n    for i in s:y=i\n    return y\n',1),'try_handler':('def f():\n    try:x=g()\n    except OSError:pass\n    return x\n',1),
            'try_handler_raises':('def f():\n    try:x=g()\n    except OSError:raise\n    return x\n',0),'while_true_break':('def f():\n    while True:\n        x=1\n        break\n    return x\n',0),
            'del':('def f():\n    x=1\n    del x\n    return x\n',1),'comprehension':('def f(s):\n    return [i for i in s]\n',0),'with':('def f(p):\n    with open(p) as h:d=h.read()\n    return d\n',0),
            'finally':('def f():\n    try:pass\n    finally:x=1\n    return x\n',0),'aug':('def f():\n    x+=1\n    return x\n',1),'global':('G=0\ndef f():\n    global G\n    G+=1\n',0),
            # T-05: deletions through finally, loop bodies, continue and break paths, handlers and match cases
            'del_in_finally':('def f():\n    x=1\n    try:pass\n    finally:del x\n    return x\n',1),
            'del_in_finally_reassigned':('def f():\n    x=1\n    try:pass\n    finally:\n        del x\n        x=2\n    return x\n',0),
            'finally_entry_after_del':('def f():\n    x=1\n    try:\n        del x\n        return 0\n    finally:\n        print(x)\n',1),
            'handler_entry_after_del':('def f():\n    x=1\n    try:\n        del x\n        g()\n    except OSError:\n        return x\n    return 0\n',1),
            'break_through_finally':('def f(s):\n    x=1\n    for i in s:\n        try:\n            break\n        finally:\n            del x\n    return x\n',1),
            'continue_through_finally':('def f(s):\n    x=1\n    for i in s:\n        try:\n            continue\n        finally:\n            del x\n    return x\n',2),
            'del_in_loop_body':('def f(s):\n    x=1\n    for i in s:\n        print(x)\n        if i:del x\n',2),
            'del_in_loop_reassigned':('def f(s):\n    x=1\n    for i in s:\n        del x\n        x=i\n    return x\n',0),
            'del_on_continue_path':('def f(s):\n    x=1\n    for i in s:\n        if i:\n            del x\n            continue\n        x=2\n    return x\n',2),
            'del_in_while_body':('def f(n):\n    x=1\n    while n:\n        n-=1\n        if n==3:del x\n    return x\n',2),
            'del_in_loop_exit_break':('def f(s):\n    x=1\n    for i in s:\n        if i:\n            del x\n            break\n    return x\n',1),
            'del_tuple':('def f():\n    x=1\n    y=2\n    del (x, y)\n    return y\n',1),
            'del_possibly_unbound':('def f(a):\n    if a:x=1\n    del x\n',1),
            'match_case_del':('def f(v):\n    x=1\n    match v:\n        case 1:\n            del x\n    return x\n',1),
            'match_no_case_matched':('def f(v):\n    match v:\n        case 1:\n            return 0\n    print(y)\n    y=1\n',1),
            'match_irrefutable':('def f(v):\n    match v:\n        case 1:\n            x=1\n        case _:\n            x=2\n    return x\n',0),
            'match_capture':('def f(v):\n    match v:\n        case [a, *rest]:\n            return a, rest\n    return None\n',0)}
    bad=[]
    for name,(src,want) in probes.items():
        t=ast.parse(src);got=len(unreachable(t,name)+unbound(t,name))
        if got!=want:bad.append(f'{name}: {got} findings, expected {want}')
    for name,(src,want) in {'swallowed_call':("e={}   # note;e.update(A='1')\n",1),'swallowed_assign':("x=1  # see y;x=2\n",1),
                            'comment_semicolon_prose':("x=1  # a; b and c; d=1 here; f(x) too\n",0),'comment_compare':("x=1  # a;x==2 holds\n",0),
                            'code_semicolon':("x=1;y=2  # fine\n",0)}.items():
        got=len(swallowed(src,name))
        if got!=want:bad.append(f'{name}: {got} findings, expected {want}')
    for name,(src,want) in {'undefined_in_function':("def f(full):\n    return 1\ndef g():\n    if full:return 2\n",1),
                            'defined_late_global':("def f():\n    return X\nX=1\n",0),'builtin':("def f(s):\n    return len(s)\n",0),
                            'imported':("import os\ndef f():\n    return os.sep\n",0),'star_skipped':("from os import *\ndef f():\n    return sep\n",0),
                            'module_level_undefined':("print(Y)\n",1),'except_name':("try:pass\nexcept OSError as E:pass\ndef f():return E\n",0)}.items():
        got=len(undefined_globals(src,name))
        if got!=want:bad.append(f'{name}: {got} findings, expected {want}')
    return bad

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('paths',nargs='*',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args()
    bad=selftest()
    paths=[p.resolve()for p in a.paths]or sorted((ROOT/'tools').glob('*.py'))
    comments=[]if a.paths else sorted([*(ROOT/'tests').glob('*.py'),*(ROOT/'gen3').glob('*.py')])
    r=scan(paths,comments);rec=dict(schema='c8-d3-gate-1',gate='ast_scan',selftest_failures=bad,files=r['files'],comment_files=r['comment_files'],findings=r['findings'],allowed=ALLOW,passed=not bad and not r['findings'])
    for f in r['findings']:print(f'{f["file"]}:{f["line"]}: {f["kind"]}: {f["detail"]}')
    for b in bad:print('SELFTEST FAIL',b)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(f'ast_scan: {r["files"]} files, {len(r["findings"])} findings, self-test {"passed"if not bad else"FAILED"}')
    return 0 if rec['passed']else 1

if __name__=='__main__':sys.exit(main())
