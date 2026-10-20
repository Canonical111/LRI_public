"""Inspect/evaluate coefficients of a recorded conventional Horn function.

This is not an endpoint analytic-continuation routine. It loads one finite
parameter array, evaluates its scalar prefactor and a selected coefficient,
including /prod n!, but excluding the recorded argument powers. Use the full
master continuation convention from the note when evaluating endpoint values.
"""
from __future__ import annotations
from pathlib import Path
from functools import lru_cache
from typing import Sequence
import argparse,gzip,json
import mpmath as mp
import sympy as sp
ROOT=Path(__file__).resolve().parents[2]
ARRAYS=ROOT/'verification/general_closed/horn_arrays'
Q=sp.Symbol('q')
@lru_cache(None)
def expression(s: str):
    expr=sp.sympify(s,locals={'q':Q})
    syms=sorted(expr.free_symbols,key=str)
    return syms,sp.lambdify(syms,expr,modules='mpmath')
def evaluate(s: str,values: dict):
    syms,fn=expression(s)
    return fn(*(values[str(x)] for x in syms))
def load(master: str):
    if master not in {'Q','P4','L','Z','K','P5a','P5b'}:raise ValueError('Unknown master')
    with gzip.open(ARRAYS/(master+'_horn.json.gz'),'rt') as f:return json.load(f)
def coefficient(master: str,entry: int,qvalue: str,indices: Sequence[int]):
    data=load(master)
    if not 0<=entry<len(data['terms']):raise ValueError('Entry outside the recorded finite list')
    row=data['terms'][entry]
    if len(indices)!=row['dimension'] or any(k<0 for k in indices):raise ValueError('Wrong number of indices or negative index')
    values={'q':mp.mpf(qvalue)}
    if not 0<values['q']<1:raise ValueError('Choose 0<q<1; coefficients do not perform dimensional continuation')
    sc=json.loads((ARRAYS/'scalar_parameters.json').read_text())
    values.update({k:evaluate(v,values) for k,v in sc.items()})
    ans=evaluate(row['prefactor'],values)
    for upper,rows in [(True,row['upper']),(False,row['lower'])]:
        for a,v,multiplicity in rows:
            k=sum(j*t for j,t in zip(indices,v))
            z=mp.rf(evaluate(a,values),k)**multiplicity
            ans=ans*z if upper else ans/z
    for k in indices:ans/=mp.factorial(k)
    return ans,row['arguments']
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--master',default='Q');p.add_argument('--entry',type=int,default=0);p.add_argument('--q',default='.3');p.add_argument('--indices',default=None);p.add_argument('--dps',type=int,default=40)
    a=p.parse_args();mp.mp.dps=a.dps;row=load(a.master)['terms'][a.entry]
    if a.indices is None:print(json.dumps(row,indent=2));return
    value,args=coefficient(a.master,a.entry,a.q,[int(x) for x in a.indices.split(',')]);print('Coefficient including prefactor =',mp.nstr(value,a.dps));print('Argument vector =',args)
if __name__=='__main__':main()
