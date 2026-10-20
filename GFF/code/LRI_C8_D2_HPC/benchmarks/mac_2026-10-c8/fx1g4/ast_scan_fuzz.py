#!/usr/bin/env python3
"""Differential soundness fuzz of tests/ast_scan.py's unbound-name check (Stage-6 fix round 1, G4; evidence only).

Random small functions over the locals x, y and an except-as name e (assignments, del, augmented assignments, walrus
targets in `and`, in chained comparisons, in dict displays and in asserts; if/else, for/else, while, try/except/else,
try/finally, a handler that leaves its loop by break or continue, match with sequence, mapping and wildcard cases) are
compiled and run on every input combination; each name that raises UnboundLocalError must be reported by the scanner
(no false negatives). Reports from correlated conditions (false positives) are counted, not failed.
Usage: python3 -B ast_scan_fuzz.py [--scanner tests/ast_scan.py] [--cases 1500] [--seeds 1 2 3] [--output FILE]"""
from __future__ import annotations
import argparse,ast,importlib.util,json,random,re,sys,warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
V=['x','y','e']
INPUTS=[dict(a=a,b=b,s=s)for a in(0,1)for b in(0,1)for s in([],[0],[1,0],{'k':5})]

def gen(R:random.Random)->str:
    def simple(loop):
        v=lambda:R.choice(['x','y'])
        c=[f'{v()} = {R.choice(["1","a","b"])}',f'_ = {R.choice(V)}',f'del {v()}','if b: raise ValueError()','pass',
           f'_ = {R.choice(V)} + 1',f'_ = a < b < ({v()} := 1)',f'_ = (a and ({v()} := 2))',
           f'_ = {{1: {R.choice(V)}, ({v()} := 3): 0}}',f'{v()} += 1',f'assert ({v()} := 1)']
        if loop:c+=['break','continue','if a: break','if b: continue']
        return R.choice(c)
    def block(d,loop,ind):
        out=[]
        for _ in range(R.randint(1,3)):
            if d>=3 or R.random()<0.45:out.append(ind+simple(loop));continue
            t=R.choice(['if','for','while','try','match','tryf','handlerloop']);i2=ind+'    '
            sub=lambda l=loop:block(d+1,l,i2)
            if t=='if':out+=[ind+f'if {R.choice(["a","b","not a"])}:']+sub()+([ind+'else:']+sub()if R.random()<0.5 else[])
            elif t=='for':out+=[ind+'for i in s:']+block(d+1,True,i2)+([ind+'else:']+sub()if R.random()<0.3 else[])
            elif t=='while':out+=[ind+f'n{d} = len(s)',ind+f'while n{d} > 0:',i2+f'n{d} -= 1']+block(d+1,True,i2)
            elif t=='try':out+=[ind+'try:']+sub()+[ind+'except ValueError as e:']+sub()+([ind+'else:']+sub()if R.random()<0.3 else[])
            elif t=='tryf':out+=[ind+'try:']+sub()+([ind+'except ValueError as e:']+sub()if R.random()<0.6 else[])+[ind+'finally:']+sub()
            elif t=='handlerloop':out+=[ind+'for i in s:',i2+'try:',i2+'    if a: raise ValueError()',i2+'except ValueError as e:']+block(d+2,True,i2+'    ')
            else:
                out+=[ind+'match s:',i2+f'case [{R.choice(["x","y"])}]:']+block(d+2,loop,i2+'    ')
                if R.random()<0.5:out+=[i2+f'case {{"k": {R.choice(["x","y"])}}}:']+block(d+2,loop,i2+'    ')
                if R.random()<0.3:out+=[i2+'case _:']+block(d+2,loop,i2+'    ')
        return out
    return 'def f(a, b, s):\n'+'\n'.join(block(0,False,'    ')+['    return '+R.choice(V)])+'\n'

def run(scanner:Path,cases:int,seed:int)->dict:
    spec=importlib.util.spec_from_file_location(f'scan_{seed}',scanner);A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
    R=random.Random(seed);checked=fn=fp=0;examples=[]
    for _ in range(cases):
        src=gen(R)
        try:code=compile(src,'<fuzz>','exec')
        except SyntaxError:continue
        ns={};exec(code,ns);rt=set()
        for inp in INPUTS:
            try:ns['f'](**inp)
            except UnboundLocalError as ex:rt.add(re.search(r"variable '(\w+)'",str(ex)).group(1))
            except(NameError,ValueError,TypeError,AssertionError):pass  # a global NameError is out of scope
        rep={x['detail'].split()[0]for x in A.unbound(ast.parse(src),'fuzz')};checked+=1
        if rt-rep:
            fn+=1
            if len(examples)<3:examples.append(dict(missed=sorted(rt-rep),source=src))
        fp+=bool(rep-rt)
    return dict(seed=seed,checked=checked,false_negatives=fn,cases_with_false_positives=fp,examples=examples)

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--scanner',type=Path,default=ROOT/'tests/ast_scan.py');ap.add_argument('--cases',type=int,default=1500)
    ap.add_argument('--seeds',type=int,nargs='+',default=[1,2,3]);ap.add_argument('--output',type=Path);a=ap.parse_args()
    warnings.simplefilter('ignore',SyntaxWarning)  # Python 3.14 warns on break/continue in finally
    runs=[run(a.scanner,a.cases,s)for s in a.seeds]
    rec=dict(schema='c8-d2-ast-scan-fuzz-1',python=sys.version.split()[0],scanner=str(a.scanner.resolve().relative_to(ROOT))if a.scanner.resolve().is_relative_to(ROOT)else a.scanner.name,
             runs=runs,passed=all(r['false_negatives']==0 for r in runs))
    s=json.dumps(rec,indent=1)+'\n'
    if a.output:a.output.write_text(s)
    for r in runs:print(f"seed {r['seed']}: {r['checked']} functions, {r['false_negatives']} false negatives, {r['cases_with_false_positives']} with false positives")
    return 0 if rec['passed']else 1

if __name__=='__main__':sys.exit(main())
