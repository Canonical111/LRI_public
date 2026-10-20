#!/usr/bin/env python3
"""Independent finite-cutoff integration after elementary first-position integration."""
import numpy as np
from scipy.special import roots_jacobi
from pathlib import Path
import json,time,argparse
def F1(x):
 out=np.zeros_like(x); nz=x>0
 out[nz]=x[nz]*(np.log(x[nz])-1)
 return out
def F2(x):
 out=np.zeros_like(x);nz=x>0
 l=np.log(x[nz]);out[nz]=x[nz]*(l*l-2*l+2)
 return out
def run(N,eps=.1):
 L=1-3*eps
 nodes=[];weights=[]
 for alpha in (2,1,0):
  u,w=roots_jacobi(N,alpha,0)
  nodes.append((1+u)/2);weights.append(w/(2**(alpha+1)))
 a,b,c=np.meshgrid(*nodes,indexing='ij')
 wa,wb,wc=np.meshgrid(*weights,indexing='ij')
 g1=eps+L*a;g2=eps+L*(1-a)*b;g3=eps+L*(1-a)*(1-b)*c
 R=g1+g2+g3;D=g1+g3
 l1=np.log(g1);l2=np.log(g2);l3=np.log(g3);l4=np.log(R)
 l5=np.log(g1+g2);l6=np.log(g2+g3)
 S1=l5+l6-l1-l2-l3-l4
 S2=l5*l5+l6*l6-l1*l1-l2*l2-l3*l3-l4*l4
 W=np.exp(2*S1)
 measure=L**3*wa*wb*wc
 Q=np.sum(measure*(1-R)*D*W*(4*S1*S1*S2+4*S1*S2))
 I0=np.zeros_like(R);I1=np.zeros_like(R)
 for i,pre in enumerate((np.zeros_like(R),g1,g1+g2,R)):
  upper=pre+1-R;sgn=(-1)**i
  I0+=2*sgn*(F1(upper)-F1(pre))
  I1+=sgn*(F2(upper)-F2(pre))
 EQ=np.sum(measure*D*W*(I0*(S2+2*S1*S2)+2*S1*I1))
 return {'N':N,'epsilon':eps,'Q4_vvd':float(Q),'EQ4_vd':float(EQ)}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--orders',default='12,20,32,48,64')
 ar=ap.parse_args();res=[run(int(N)) for N in ar.orders.split(',')]
 for r in res:print(r,flush=True)
 out=Path(__file__).resolve().parents[1]/'verification'/'direct_cutoff.json'
 out.write_text(json.dumps({'method':'Gauss-Jacobi simplex quadrature of original gap kernels with elementary endpoint integrals','runs':res,'interval_certified':False},indent=2))
if __name__=='__main__':main()
