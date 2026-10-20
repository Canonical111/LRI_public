#!/usr/bin/env python3
"""Static scan of tools/*.py (PLAN component F; C8(1) R22/R25): no unreachable statement after raise, return, continue
or break in the same block, and no possibly unbound local name.

The unbound-name check is a definite-assignment analysis per function (parameters, assignments, imports, for and
with targets, except-as names, walrus targets, including those in the defaults and decorators of nested defs and
lambdas and in class bases and keywords, match-pattern captures, nested def/class names): a load (or a del) of a name
that the function assigns somewhere is reported unless every path from the function's entry assigns it first, and a
del unbinds. Paths: both arms of an if (an arm that always leaves the block does not count); a loop body may run zero
times (`while True` leaves through its breaks), and its head state is the entry state intersected with every back
edge (the end of the body and every continue), iterated to a fixed point, so a deletion in the body reaches the next
iteration and the exit; a try body may stop at any statement, so each handler starts from the state before the try
minus every name the body may delete, and a handler's except-as name is unbound on every way out of the handler (its
end, a break or a continue) before any finally block runs; a finally block is checked against the weakest state that
can reach it (the state before the try minus everything the try, its else and its handlers may delete) and its
assignments and deletions are carried to the normal exit and to every break and continue that leaves through it; a
match statement without an irrefutable case may match nothing, and a case's captures are bound only in its guard and
body. Expressions follow Python's evaluation order: only the first operand of `and`/`or` and the left operand and
first comparator of a chained comparison always run; a dict display evaluates key, value, key, value; an augmented
assignment loads its target before its value; decorators run before defaults, and class keywords count. An assert's
test may not run (python -O), so it binds nothing. Context managers are assumed not to swallow exceptions. Lambdas and
nested functions are scanned separately, each as its own scope; their free names are not checked against the enclosing
function's flow (they run later). A lambda's locals are its parameters and the walrus targets of its body (also those
inside a comprehension there, and in the defaults of a lambda nested in it), and its body is one expression checked in
evaluation order, like a function's. Comprehensions run in place, each with its own scope: its first iterable runs in
the enclosing scope; its targets are its locals, so a target read before the clause that binds it on the first pass
(in an earlier condition or a later iterable) is unbound, also where the target shadows a bound name of the enclosing
scope; its other names, and its walrus targets, belong to the enclosing function. A comprehension in the module or in
a class body (also one nested in a function) is checked for its own targets; a class body's other code is not (a read
of an unbound name there is a NameError, not an unbound local). Annotations are not checked (in a
function only a nested def's annotations run, at its definition, and not under postponed evaluation). Correlated
conditions are not modelled, so a finding is either fixed in the code or listed, with its reason, in ALLOW below (none
at present). The self-test probes include deletion in finally blocks, loop bodies, continue and break paths, handlers
and match cases (checkpoint review T-05), and reads after unmatched captures, chained comparisons and handler exits by
break and continue (Stage-6 X17-X19), the loads of an annotated attribute or subscript target without a value (`a[i]:
int` evaluates a and i), and lambda bodies and comprehension scopes (Stage-6 Y14).
Usage: python3 -B tests/ast_scan.py [--output FILE] [PATH ...] (default: tools/*.py)"""
from __future__ import annotations
import argparse,ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALLOW:dict[str,str]={}  # 'file:line:name' -> reason

TERMINAL=(ast.Raise,ast.Return,ast.Continue,ast.Break)

def unreachable(tree:ast.AST,fname:str)->list[dict]:
    out=[]
    for node in ast.walk(tree):  # every statement list: ast.walk reaches except handlers and match cases too
        for field in ('body','orelse','finalbody'):
            stmts=getattr(node,field,None)
            if not isinstance(stmts,list):continue
            for i,st in enumerate(stmts[:-1]):
                if isinstance(st,TERMINAL):
                    nxt=stmts[i+1];out.append(dict(file=fname,line=nxt.lineno,kind='unreachable',detail=f'statement after {type(st).__name__.lower()} at line {st.lineno}'));break
    return out

def target_names(t)->set:
    if isinstance(t,ast.Name):return {t.id}
    if isinstance(t,(ast.Tuple,ast.List)):return set().union(*(target_names(e)for e in t.elts))if t.elts else set()
    if isinstance(t,ast.Starred):return target_names(t.value)
    return set()

class LocalNames(ast.NodeVisitor):
    """Names a function binds in its own scope (excluding nested scopes), and its global/nonlocal declarations."""
    def __init__(self):self.bound=set();self.decl=set()
    def visit_FunctionDef(self,n):  # decorators and defaults run in this scope (a walrus there binds here); the body does not
        self.bound.add(n.name)
        for e in n.decorator_list+n.args.defaults+[x for x in n.args.kw_defaults if x is not None]:self.visit(e)
    visit_AsyncFunctionDef=visit_FunctionDef
    def visit_ClassDef(self,n):
        self.bound.add(n.name)
        for e in n.decorator_list+n.bases+[k.value for k in n.keywords]:self.visit(e)
    def visit_Lambda(self,n):
        for e in n.args.defaults+[x for x in n.args.kw_defaults if x is not None]:self.visit(e)
    # match-pattern captures are plain strings in the AST, not Name(Store) nodes
    def visit_MatchAs(self,n):
        if n.name:self.bound.add(n.name)
        self.generic_visit(n)
    def visit_MatchStar(self,n):
        if n.name:self.bound.add(n.name)
    def visit_MatchMapping(self,n):
        if n.rest:self.bound.add(n.rest)
        self.generic_visit(n)
    def visit_ListComp(self,n):self._comp(n)
    visit_SetComp=visit_GeneratorExp=visit_DictComp=visit_ListComp
    def _comp(self,n):
        # a walrus in a comprehension binds the enclosing scope (this one), also in a nested comprehension and in the
        # defaults of a lambda there, but not inside a lambda's body (that binds the lambda); targets stay inside
        for g in n.generators:
            self.visit(g.iter)
            for c in g.ifs:self.visit(c)
        for f in ('elt','key','value'):
            if getattr(n,f,None)is not None:self.visit(getattr(n,f))
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
        self.fname=fname;self.fn=fn;self.locals=locals_;self.out=[];self.seen=set();self.where=SCOPE_NAME.get(type(fn))or fn.name
        self.loops=[]  # per enclosing loop: ([break states], [continue states])
    def report(self,node,name):
        key=f'{self.fname}:{node.lineno}:{name}'
        if key in ALLOW or key in self.seen:return  # a statement may be analysed more than once (loops, finally)
        self.seen.add(key);self.out.append(dict(file=self.fname,line=node.lineno,kind='possibly-unbound',detail=f'{name} in {self.where}()'))
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
        if isinstance(e,COMPS):
            # the first iterable runs in the enclosing scope; the rest runs in the comprehension's own scope, whose
            # locals are its targets (unbound until the clause that binds them, whatever the enclosing scope holds)
            gens=e.generators;self.expr(gens[0].iter,D)
            own=set().union(*(target_names(g.target)for g in gens));outer=self.locals;self.locals=outer|own
            try:
                inner=set(D)-own
                for i,g in enumerate(gens):
                    if i:inner=self.expr(g.iter,inner)
                    inner=self.store(g.target,inner)
                    for c in g.ifs:inner=self.expr(c,inner)
                for f in ('elt','key','value'):
                    if getattr(e,f,None)is not None:inner=self.expr(getattr(e,f),inner)
            finally:self.locals=outer
            return D  # comprehension targets stay inside; walrus inside a comprehension is conditional
        if isinstance(e,ast.BoolOp):
            D=self.expr(e.values[0],D)
            for v in e.values[1:]:self.expr(v,D)  # later operands may not run: their walrus targets are not definite
            return D
        if isinstance(e,ast.Compare):  # a chain stops at its first false link: only its first two operands always run
            D=self.expr(e.comparators[0],self.expr(e.left,D));c=D
            for v in e.comparators[1:]:c=self.expr(v,c)
            return D
        if isinstance(e,ast.Dict):  # key, value, key, value, ... (a None key is a ** unpacking)
            for k,v in zip(e.keys,e.values):D=self.expr(v,self.expr(k,D))
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
        if isinstance(st,(ast.FunctionDef,ast.AsyncFunctionDef)):  # the decorators run first, then the defaults
            for d in st.decorator_list+st.args.defaults+[x for x in st.args.kw_defaults if x is not None]:D=E(d,D)
            return D|{st.name}
        if isinstance(st,ast.ClassDef):
            for d in st.decorator_list+st.bases+[k.value for k in st.keywords]:D=E(d,D)
            return D|{st.name}
        if isinstance(st,ast.Assign):
            D=E(st.value,D)
            for t in st.targets:D=self.store(t,D)
            return D
        if isinstance(st,ast.AugAssign):  # the target loads first (a name, or a base and an index), then the value
            if isinstance(st.target,ast.Name):
                if st.target.id in self.locals and st.target.id not in D:self.report(st.target,st.target.id)
                return E(st.value,D)|{st.target.id}
            return E(st.value,self.expr(st.target,D))
        if isinstance(st,ast.AnnAssign):  # without a value, a name target binds and loads nothing; an attribute or
            # subscript target still evaluates its base (and index), only the final store is skipped
            if st.value is None:return D if isinstance(st.target,ast.Name)else E(st.target,D)
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
        if isinstance(st,ast.Assert):E(st.msg,E(st.test,D));return D  # python -O skips the test: it binds nothing
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
                m=(len(fr[0]),len(fr[1]))if fr else(0,0)
                r=self.block(h.body,hd)
                if h.name:  # Python unbinds the target on every way out of the handler, a break or continue included
                    if fr is not None:
                        for lst,n0 in zip(fr,m):lst[n0:]=[x-{h.name}for x in lst[n0:]]
                    if r is not None:r=r-{h.name}
                if r is not None:outs.append(r)
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

COMPS=(ast.ListComp,ast.SetComp,ast.GeneratorExp,ast.DictComp)
SCOPE_NAME={ast.Lambda:'<lambda>',ast.ListComp:'<listcomp>',ast.SetComp:'<setcomp>',ast.GeneratorExp:'<genexpr>',ast.DictComp:'<dictcomp>'}

def parameters(args:ast.arguments)->set:
    return {a.arg for a in args.posonlyargs+args.args+args.kwonlyargs}|({args.vararg.arg}if args.vararg else set())|({args.kwarg.arg}if args.kwarg else set())

def outer_comprehensions(tree:ast.AST)->list:
    """The comprehensions no function or lambda flow reaches: those whose nearest enclosing scope is the module or a
    class body (a class body nested in a function too), including the decorators, defaults, bases and keywords
    evaluated there; nested comprehensions are reached through them."""
    out=[]
    def walk(n,flow:bool):  # flow: a function's or lambda's flow analysis evaluates n
        if isinstance(n,COMPS):
            if not flow:out.append(n)
            return
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):
            for e in getattr(n,'decorator_list',[])+n.args.defaults+[x for x in n.args.kw_defaults if x is not None]:walk(e,flow)
            for b in (n.body if isinstance(n.body,list)else[n.body]):walk(b,True)
            return
        if isinstance(n,ast.ClassDef):
            for e in n.decorator_list+n.bases+[k.value for k in n.keywords]:walk(e,flow)
            for b in n.body:walk(b,False)
            return
        for c in ast.iter_child_nodes(n):walk(c,flow)
    walk(tree,False);return out

def unbound(tree:ast.AST,fname:str)->list[dict]:
    out=[]
    for fn in ast.walk(tree):
        if not isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):continue
        ln=LocalNames();params=parameters(fn.args)
        if isinstance(fn,ast.Lambda):  # Y14: a lambda is a scope of its own; its body is one expression
            ln.visit(fn.body);f=Flow(fname,fn,ln.bound|params);f.expr(fn.body,set(params));out+=f.out;continue
        for st in fn.body:ln.visit(st)
        locals_=(ln.bound|params)-ln.decl
        f=Flow(fname,fn,locals_);f.block(fn.body,set(params));out+=f.out
    for c in outer_comprehensions(tree):  # their own targets only: a module or class name read there is not a local
        f=Flow(fname,c,set());f.expr(c,set());out+=f.out
    return out

def scan(paths:list[Path])->dict:
    findings=[];files=0
    for p in paths:
        src=p.read_text();tree=ast.parse(src,str(p));files+=1;rel=str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p)
        findings+=unreachable(tree,rel)+unbound(tree,rel)
    return dict(files=files,findings=findings)

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
            'match_capture':('def f(v):\n    match v:\n        case [a, *rest]:\n            return a, rest\n    return None\n',0),
            # Stage-6 X17 (S6E-01): a capture is a binding of the function; after an unmatched case it is unbound
            'match_capture_after_unmatched_sequence':('def f(v):\n    match v:\n        case [x]:\n            pass\n    return x\n',1),
            'match_capture_after_unmatched_mapping':("def f(v):\n    match v:\n        case {'k': y, **rest}:\n            pass\n    return y, rest\n",2),
            'match_star_after_unmatched':('def f(v):\n    match v:\n        case [1, *s]:\n            pass\n    return s\n',1),
            'match_class_capture_after_unmatched':('def f(v):\n    match v:\n        case P(k=z):\n            pass\n    return z\n',1),
            'match_capture_read_before_match':('def f(v):\n    print(x)\n    match v:\n        case [x]:\n            return x\n',1),
            'match_capture_every_path':('def f(v):\n    match v:\n        case [x]:\n            pass\n        case x:\n            pass\n    return x\n',0),
            'match_capture_in_guard':('def f(v):\n    match v:\n        case [x] if x > 0:\n            return x\n    return 0\n',0),
            # Stage-6 X18 (S6E-02): a chained comparison may stop after its first link
            'compare_chain_later_walrus':('def f(a):\n    a < 0 < (x := 1)\n    return x\n',1),
            'compare_chain_first_link_walrus':('def f(a):\n    a < (x := 1) < 2\n    return x\n',0),
            'compare_chain_left_walrus':('def f(a):\n    (x := a) < 0 < 1\n    return x\n',0),
            'compare_chain_link_reads_earlier_walrus':('def f(a):\n    return a < 0 < (x := 1) < x\n',0),
            # Stage-6 X19 (S6E-03): the except-as name is unbound on a break or continue out of the handler
            'handler_target_after_break':('def f():\n    while True:\n        try: raise ValueError()\n        except ValueError as e: break\n    return e\n',1),
            'handler_target_after_continue':('def f(s):\n    e=0\n    for i in s:\n        print(e)\n        try:\n            g()\n        except ValueError as e:\n            continue\n',1),
            'handler_target_break_through_finally':('def f():\n    while True:\n        try:\n            raise ValueError()\n        except ValueError as e:\n            break\n        finally:\n            pass\n    return e\n',1),
            'handler_other_name_after_break':('def f():\n    while True:\n        try:\n            raise ValueError()\n        except ValueError as e:\n            y=1\n            break\n    return y\n',0),
            # same class, found in the Stage-6 fix round: evaluation order and walrus bindings outside plain statements
            'dict_value_before_later_key':('def f():\n    return {1: x, (x := 2): 3}\n',1),
            'dict_key_before_its_value':('def f():\n    return {(x := 1): x}\n',0),
            'aug_subscript_target_first':('def f(a):\n    a[i] += (i := 0)\n    return a\n',1),
            'aug_name_target_first':('def f():\n    x += (x := 1)\n    return x\n',1),
            'decorator_before_default':('def f():\n    @g(x)\n    def h(a=(x := 1)):\n        pass\n    return h\n',1),
            'lambda_default_walrus_is_local':('def f():\n    print(x)\n    g = lambda a=(x := 1): a\n    return g\n',1),
            'class_keyword_load':('def f(a):\n    if a:\n        M = type\n    class C(metaclass=M):\n        pass\n    return C\n',1),
            'assert_walrus_not_definite':('def f(a):\n    assert (x := a)\n    return x\n',1),
            'unreachable_in_handler_once':('def f():\n    try:\n        g()\n    except OSError:\n        return 0\n        h()\n',1),
            # fix-round-1 residual: an annotated target without a value still loads its base and index
            'annassign_subscript_no_value':('def f(a):\n    a[i]: int\n    i=0\n    return a\n',1),
            'annassign_subscript_base_no_value':('def f():\n    b[0]: int\n    b=[0]\n    return b\n',1),
            'annassign_attribute_no_value':('def f():\n    o.x: int\n    o=1\n    return o\n',1),
            'annassign_name_no_value':('def f():\n    x: int\n    return 0\n',0),
            'annassign_subscript_bound_no_value':('def f(a, i):\n    a[i]: int\n    return a\n',0),
            # Stage-6 Y14 (S6E-R2-02): a lambda body is a scope of its own, read in evaluation order
            'lambda_body_read_before_walrus':('def f():\n    return (lambda: (x, (x := 1)))()\n',1),
            'lambda_body_walrus_then_read':('def f():\n    return (lambda: ((x := 1), x))()\n',0),
            'lambda_body_conditional_walrus':('def f(a):\n    return (lambda: (a and (x := 1), x))()\n',1),
            'lambda_body_shadows_bound_outer':('def f():\n    x=1\n    return (lambda: (x, (x := 2)))()\n',1),
            'lambda_params_bound':('def f():\n    return (lambda a, *b, c=0, **d: (a, b, c, d, (y := a), y))\n',0),
            'lambda_nested_free_name_unchecked':('def f():\n    return (lambda: ((x := 1), (lambda: x)()))()\n',0),
            'lambda_module_level':('g = lambda: (x, (x := 1))\n',1),
            'lambda_class_level':('class C:\n    g = lambda self: (y, (y := 1))\n',1),
            'lambda_in_comprehension':('def f(s):\n    return [lambda: (q, (q := 1)) for q in s]\n',1),
            # same class: a walrus inside a lambda body binds the lambda, not the function around the comprehension
            'lambda_body_walrus_in_comprehension_not_function_local':('def f():\n    print(z)\n    return [(lambda: (z := 1)) for _ in [1]]\n',0),
            'lambda_default_walrus_in_comprehension_function_local':('def f(s):\n    [lambda a=(z := 1): a for _ in s]\n    return z\n',1),
            # same class: a comprehension's targets are its own locals, unbound before the clause that binds them
            'comprehension_target_read_in_earlier_condition':('def f(s, t):\n    return [x for _ in s if x for x in t]\n',1),
            'comprehension_target_shadows_bound_outer':('def f(s, t):\n    x=1\n    return [x for _ in s if x for x in t]\n',1),
            'comprehension_target_read_in_later_iterable':('def f(s):\n    return [0 for _ in s for y in y]\n',1),
            'comprehension_first_iterable_is_enclosing':('def f():\n    y=[1]\n    return [y for y in y]\n',0),
            'comprehension_targets_ordered':('def f(s):\n    return {k: v for k, v in s if k}, (w for _ in s for w in _)\n',0),
            'generator_target_read_first':('def f(s, t):\n    return list(x for _ in s if x for x in t)\n',1),
            'comprehension_subscript_target_loads_base':('def f(s):\n    r=[0 for a[0] in s]\n    a=[0]\n    return r\n',1),
            'comprehension_module_level':('[x for _ in [1] if x for x in [2]]\n',1),
            'comprehension_class_level_names_not_local':('class C:\n    n=2\n    v=[i for i in range(n) if i]\n',0),
            'comprehension_in_class_body_in_function':('def f(t):\n    class C:\n        v=[x for _ in t if x for x in t]\n    return C\n',1),
            'comprehension_in_class_bases_in_function':('def f(t):\n    class C(*[x for _ in t if x for x in t]):\n        pass\n    return C\n',1),
            'comprehension_in_default_at_module_level':('def g(a=[x for _ in [1] if x for x in [2]]):\n    return a\n',1)}
    bad=[]
    for name,(src,want) in probes.items():
        t=ast.parse(src);got=len(unreachable(t,name)+unbound(t,name))
        if got!=want:bad.append(f'{name}: {got} findings, expected {want}')
    return bad

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('paths',nargs='*',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args()
    bad=selftest()
    paths=[p.resolve()for p in a.paths]or sorted((ROOT/'tools').glob('*.py'))
    r=scan(paths);rec=dict(schema='c8-d2-gate-1',gate='ast_scan',selftest_failures=bad,files=r['files'],findings=r['findings'],allowed=ALLOW,passed=not bad and not r['findings'])
    for f in r['findings']:print(f'{f["file"]}:{f["line"]}: {f["kind"]}: {f["detail"]}')
    for b in bad:print('SELFTEST FAIL',b)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(f'ast_scan: {r["files"]} files, {len(r["findings"])} findings, self-test {"passed"if not bad else"FAILED"}')
    return 0 if rec['passed']else 1

if __name__=='__main__':sys.exit(main())
