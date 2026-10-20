"""Exact integration of the coefficient delta^2 of the three-kink weight."""
from pathlib import Path
import os,json
import ordered_moments as om
from hyperlog_core import K,clean,addto
BASE=Path(__file__).resolve().parent
old=om.make_initial

def second_tail(n,kind):
    if kind!='Adelta2': return old(n,kind)
    N=n-1
    base=old(n,'Abase')
    s2={};s3={}
    for i in range(n):
        for j in range(i+1,n):
            L=om.log_distance(i,j,N)
            L2=om.multiply(L,L,N)
            L3=om.multiply(L2,L,N)
            for key,co in L2.items():addto(s2,key,(-1)**(i+j)*co)
            for key,co in L3.items():addto(s3,key,(-1)**(i+j)*co)
    weight={}
    for key,co in om.multiply(clean(s2),clean(s2),N).items():addto(weight,key,co/2)
    for key,co in s3.items():addto(weight,key,co/3)
    return om.multiply(base,clean(weight),N)

om.make_initial=second_tail
os.environ['LRI_AUDIT_PRIMITIVES']='1'
rows=om.calc(3,'Adelta2',root=BASE)
from asymptotic_gpl import extract_rows
import sympy as s
co=extract_rows(rows,2,0,1)
V=s.expand(co-4)
(BASE/'Adelta2_3_0_1.expr').write_text(str(co)+'\n')
(BASE/'V_symbolic.expr').write_text(str(V)+'\n')
print('Exact symbolic V:',V,flush=True)
(BASE/'audit_counts.json').write_text(json.dumps(om.AUDIT_COUNTS,indent=2)+'\n')
