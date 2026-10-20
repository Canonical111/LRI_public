#!/usr/bin/env python3
"""First-order block, spectrum, crossing and integration diagnostics."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,json
from pathlib import Path
import numpy as np
import mpmath as mp
from scipy.special import eval_legendre
from spectrum import get_rows,as_upstream,LOW,INPUT,S,E
from kernels import Functional,crossing_rows,cb
BASE=Path(__file__).resolve().parent

def block_checks():
 mp.mp.dps=40;errors=[];zerrors=[]
 for de in [E,3.82968]:
  for z in [.1,.5]:
   exact=(z*z/(1-z))**(de/2)*mp.hyper([de/2,de/2,de/2-.5],[(de+1)/2,de-.5],z*z/(4*(z-1)))
   errors.append(abs(float(exact)-float(cb.Block(de,0,24)(z))))
 for de,ell,da,db in [(E,0,0.,0.),(3.,2,0.,0.),(S,0,E-S,S-E),(4.180305,2,E-S,S-E),(4.63804,3,E-S,S-E)]:
  A=cb.zcoefs(de,ell,60,da,db)
  for z in [.17+.12j,.29+.08j]:
   r=abs(z);eta=z.real/r
   exact=sum(r**(de+n)*sum(A[n,j]*eval_legendre(j,eta) for j in range(A.shape[1])) for n in range(len(A)))
   zerrors.append(abs(exact-float(cb.Block(de,ell,24,da,db)(z))))
 if max(errors)>=1e-12 or max(zerrors)>=1e-12:raise RuntimeError('Conformal-block validation failed')
 return dict(diagonal_3F2_max_abs_error=max(errors),independent_z_series_max_abs_error=max(zerrors))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--quick',action='store_true');args=p.parse_args()
 rows=get_rows()
 if rows!=json.loads((INPUT/'retained_spectrum.json').read_text()):raise RuntimeError('Data differ from retained snapshot')
 fn=Functional();central=fn.evaluate(rows);out=dict(validation=block_checks(),central=central)
 raw=json.loads((INPUT/'baseline_selected_spectrum.json').read_text());old=[]
 for sector in ['even','odd']:
  for tup in raw[sector]:
   name,d,l,f,*h=tup;fac=2**(l/2);row=dict(name=name,Delta=d,ell=l,sector=sector,f=f/fac)
   if sector=='even':row['h']=h[0]/fac
   if d==3 and l==2:row.update(f=S*np.sqrt(3/(8*LOW['ct'][0])),h=E*np.sqrt(3/(8*LOW['ct'][0])))
   old.append(row)
 baseline=fn.evaluate(old);out['ward_updated_baseline']=baseline
 t=next(q for q in central['parts'] if q['name']=='even_ss1_l2_d5.50915');out['Tprime']=t
 out['baseline_plus_Tprime_C1']=(baseline['a']+t['contribution_a'])/(baseline['b']+t['contribution_b'])
 out['cutoff']=[]
 for cut in [5.4,6,7,8,9,10,11.1,12,14,16,20,24]:
  b,a=central['constant']
  for row,q in zip(rows,central['parts']):
   if row['Delta']<cut:b+=q['contribution_b'];a+=q['contribution_a']
  out['cutoff'].append(dict(cut=cut,b=b,a=a,C1=a/b))
 z=[.3+.25j,.2+.5j];co=crossing_rows(old,z,28);cn=crossing_rows(rows,z,28)
 out['crossing_comparison']=dict(z=[[x.real,x.imag] for x in z],old_relative=co['mixed']['relative'],expanded_relative=cn['mixed']['relative'])
 if not args.quick:
  checks=[]
  for level,n,r0 in [(20,80,.2),(28,128,.2),(24,100,.15)]:
   q=Functional(level=level,nr=n,na=n,r0=r0).evaluate(rows)
   checks.append(dict(level=level,nr=n,na=n,r0=r0,a=q['a'],b=q['b'],C1=q['C1'],C1_change=q['C1']-central['C1']))
  out['numerical_stability']=checks;cb.EVEN,cb.ODD=as_upstream(rows)
  out['independent_folding']=cb.integrate(level=24,nr=100,na=100,cut=24)
 path=BASE/'diagnostics_results.json';path.write_text(json.dumps(out,indent=2)+'\n')
 print('central',central['a'],central['b'],central['C1']);print(out['validation']);print('saved',path)
if __name__=='__main__':main()
