"""Full-constant six-kink mixed boundary kernel. Derivatives are exact; no pi_0."""
from full_boundary import *
import full_boundary as fb
_oldsetup=fb.setup

def mixed_setup(n,face,deriv='vd'):
 fac,_,N,ids=_oldsetup(n,face,'base')
 lv={};ld={}
 for i in range(n):
  for j in range(i+1,n):
   ia,ib=ids[i],ids[j]; cc=j-i;sgn=(-1)**(i+j)
   ww=[()]*N; ll={}
   if ia!=ib:
    if ia:
     ww[ia-1]=(GEN[ib]+cc,);addto(ll,(tuple(ww),()),K.one);ww[ia-1]=()
    ww[ib-1]=(K(-cc),);addto(ll,(tuple(ww),()),K.one);ww[ib-1]=()
   if cc!=1:addto(ll,(tuple([()]*N),(cc,)),K.one)
   for key,co in ll.items():addto(lv,key,2*sgn*co)
   if 'd' in deriv:
    for key,co in om.multiply(ll,ll,N).items():addto(ld,key,sgn*co)
 lv=clean(lv);ld=clean(ld)
 if deriv=='v':ins=lv
 elif deriv=='d':ins=ld
 elif deriv=='vd':
  ins=ld.copy()
  for key,co in om.multiply(lv,ld,N).items():addto(ins,key,co)
  ins=clean(ins)
 else:ins={(tuple([()]*N),()):K.one}
 print('INSERTION',n,face,deriv,len(lv),len(ld),len(ins),flush=True)
 return fac,ins,N,ids
fb.setup=mixed_setup
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=6);p.add_argument('--face',type=int);p.add_argument('--deriv',default='vd');p.add_argument('--sources',action='store_true');p.add_argument('--tag');p.add_argument('--block');p.add_argument('--stop',type=int);a=p.parse_args()
 if a.sources:fb.sources_boundary(a.n,a.face,a.deriv)
 else:fb.worker_boundary(a.tag,a.block,a.stop)
