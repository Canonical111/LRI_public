#!/usr/bin/env python3
"""Differential soundness fuzz of tests/ast_scan.py's unbound-name check (Stage-6 fix round 2, G4, Y14; evidence only).

The fix-round-1 generator (benchmarks/mac_2026-10-c8/fx1g4/ast_scan_fuzz.py: the function-scope statements over the
locals x, y and the except-as name e) plus the scopes Y14 is about:
- lambda bodies, called in place: random expressions over the lambda-only names p and r (reads, walrus targets, `and`,
  `or`, conditional expressions, chained comparisons, dict displays, comprehensions whose walrus binds the lambda, and
  nested lambdas, called in place);
- comprehensions in the function, in lambda bodies and in a class body inside the function, whose targets (q, w) may
  be read before the clause that binds them (in an earlier condition or a later iterable).
Names are disjoint per scope kind (x, y, e: the function; p, r: lambdas; q, w: comprehension targets), so a runtime
UnboundLocalError names the scope it comes from. Each function is compiled and run on every input combination; each
name that raises UnboundLocalError must be reported by the scanner (no false negatives). Reports caused by correlated
conditions or by comprehensions that always run (false positives) are counted, not failed. A NameError (a free or
global name) is out of the scanner's scope.
Usage: python3 -B ast_scan_fuzz.py [--scanner tests/ast_scan.py] [--cases 1500] [--seeds 1 2 3] [--output FILE]"""
from __future__ import annotations
import argparse,ast,importlib.util,json,random,re,sys,warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
V=['x','y','e']
INPUTS=[dict(a=a,b=b,s=s)for a in(0,1)for b in(0,1)for s in([],[0],[1,0],{'k':5})]

def lexpr(R:random.Random,d:int)->str:
    """An expression for a lambda body over the lambda's own names p, r (and the function's a, b, s)."""
    if d>=3 or R.random()<0.35:return R.choice(['p','r','(p := 1)','(r := 2)','(p := a)','a','b','1'])
    k=R.choice(['tuple','and','or','ifexp','cmp','dict','comp','lambda'])
    f=lambda:lexpr(R,d+1)
    if k=='tuple':return f'({f()}, {f()})'
    if k=='and':return f'({f()} and {f()})'
    if k=='or':return f'({f()} or {f()})'
    if k=='ifexp':return f'({f()} if {f()} else {f()})'
    if k=='cmp':return f'({f()} < {f()} < {f()})'
    if k=='dict':return f'{{{f()}: {f()}, {f()}: 0}}'
    if k=='comp':return R.choice([f'[{f()} for w in s if {f()}]',f'[{f()} for _ in s if w for w in s]',f'[w for _ in s for w in w]'])
    return f'(lambda: {f()})()'  # a nested lambda: a walrus there binds the nested lambda

def cexpr(R:random.Random,walrus:bool=True)->str:
    """A comprehension in the function scope: its target q may be read before it is bound; x and y are the function's
    (walrus=False in a class body, where a walrus in a comprehension is a SyntaxError)."""
    a=lambda:R.choice(['q','x','y','a']+(['(x := 1)']if walrus else[]))
    return R.choice([f'[{a()} for q in s if {a()}]',f'[{a()} for _ in s if {a()} for q in s]',f'[0 for _ in s for q in q]',
                     f'{{{a()}: {a()} for q in s}}',f'list({a()} for _ in s if {a()} for q in s)',f'[(lambda: q)() for q in s]',
                     f'[(lambda: (q, (q := 1)))() for q in s]',f'[q for q in q]'])

def gen(R:random.Random)->str:
    def simple(loop):
        v=lambda:R.choice(['x','y'])
        c=[f'{v()} = {R.choice(["1","a","b"])}',f'_ = {R.choice(V)}',f'del {v()}','if b: raise ValueError()','pass',
           f'_ = {R.choice(V)} + 1',f'_ = a < b < ({v()} := 1)',f'_ = (a and ({v()} := 2))',
           f'_ = {{1: {R.choice(V)}, ({v()} := 3): 0}}',f'{v()} += 1',f'assert ({v()} := 1)',
           f'_ = (lambda: {lexpr(R,0)})()',f'_ = (lambda p=1: {lexpr(R,1)})()',f'_ = {cexpr(R)}']
        if loop:c+=['break','continue','if a: break','if b: continue']
        return R.choice(c)
    def block(d,loop,ind):
        out=[]
        for _ in range(R.randint(1,3)):
            if d>=3 or R.random()<0.45:out.append(ind+simple(loop));continue
            t=R.choice(['if','for','while','try','match','tryf','handlerloop','class']);i2=ind+'    '
            sub=lambda l=loop:block(d+1,l,i2)
            if t=='if':out+=[ind+f'if {R.choice(["a","b","not a"])}:']+sub()+([ind+'else:']+sub()if R.random()<0.5 else[])
            elif t=='for':out+=[ind+'for i in s:']+block(d+1,True,i2)+([ind+'else:']+sub()if R.random()<0.3 else[])
            elif t=='while':out+=[ind+f'n{d} = len(s)',ind+f'while n{d} > 0:',i2+f'n{d} -= 1']+block(d+1,True,i2)
            elif t=='try':out+=[ind+'try:']+sub()+[ind+'except ValueError as e:']+sub()+([ind+'else:']+sub()if R.random()<0.3 else[])
            elif t=='tryf':out+=[ind+'try:']+sub()+([ind+'except ValueError as e:']+sub()if R.random()<0.6 else[])+[ind+'finally:']+sub()
            elif t=='class':out+=[ind+'class K:',i2+f'v = {cexpr(R,False)}',i2+f'u = (lambda: {lexpr(R,1)})()']
            elif t=='handlerloop':out+=[ind+'for i in s:',i2+'try:',i2+'    if a: raise ValueError()',i2+'except ValueError as e:']+block(d+2,True,i2+'    ')
            else:
                out+=[ind+'match s:',i2+f'case [{R.choice(["x","y"])}]:']+block(d+2,loop,i2+'    ')
                if R.random()<0.5:out+=[i2+f'case {{"k": {R.choice(["x","y"])}}}:']+block(d+2,loop,i2+'    ')
                if R.random()<0.3:out+=[i2+'case _:']+block(d+2,loop,i2+'    ')
        return out
    return 'def f(a, b, s):\n'+'\n'.join(block(0,False,'    ')+['    return '+R.choice(V)])+'\n'

def run(scanner:Path,cases:int,seed:int)->dict:
    spec=importlib.util.spec_from_file_location(f'scan_{seed}',scanner);A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
    R=random.Random(seed);checked=fn=fp=0;examples=[];missed_names={};raised={}
    for _ in range(cases):
        src=gen(R)
        try:code=compile(src,'<fuzz>','exec')
        except SyntaxError:continue
        ns={};exec(code,ns);rt=set()
        for inp in INPUTS:
            try:ns['f'](**inp)
            except UnboundLocalError as ex:rt.add(re.search(r"variable '(\w+)'",str(ex)).group(1))
            except(NameError,ValueError,TypeError,AssertionError):pass  # a free or global NameError is out of scope
        rep={x['detail'].split()[0]for x in A.unbound(ast.parse(src),'fuzz')};checked+=1
        for n in rt:raised[n]=raised.get(n,0)+1
        if rt-rep:
            fn+=1
            for n in rt-rep:missed_names[n]=missed_names.get(n,0)+1
            if len(examples)<3:examples.append(dict(missed=sorted(rt-rep),source=src))
        fp+=bool(rep-rt)
    return dict(seed=seed,checked=checked,false_negatives=fn,missed_by_name=dict(sorted(missed_names.items())),
                functions_raising_by_name=dict(sorted(raised.items())),cases_with_false_positives=fp,examples=examples)

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--scanner',type=Path,default=ROOT/'tests/ast_scan.py');ap.add_argument('--cases',type=int,default=1500)
    ap.add_argument('--seeds',type=int,nargs='+',default=[1,2,3]);ap.add_argument('--label');ap.add_argument('--output',type=Path);a=ap.parse_args()
    warnings.simplefilter('ignore',SyntaxWarning)  # Python 3.14 warns on break/continue in finally
    runs=[run(a.scanner,a.cases,s)for s in a.seeds]
    sc=a.scanner.resolve()
    rec=dict(schema='c8-d2-ast-scan-fuzz-2',python=sys.version.split()[0],scanner=a.label or(str(sc.relative_to(ROOT))if sc.is_relative_to(ROOT)else sc.name),
             runs=runs,passed=all(r['false_negatives']==0 for r in runs))
    s=json.dumps(rec,indent=1)+'\n'
    if a.output:a.output.write_text(s)
    for r in runs:print(f"seed {r['seed']}: {r['checked']} functions, {r['false_negatives']} false negatives {r['missed_by_name']}, {r['cases_with_false_positives']} with false positives")
    return 0 if rec['passed']else 1

if __name__=='__main__':sys.exit(main())
