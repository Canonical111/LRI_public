from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
import numpy as np
from d3dressed.solver import DressedSolver
from d3dressed.basis import SphereBathBasis
from d3dressed.operators import ProductOperator
from d3dressed.local import LocalProblem

def main():
    ans=[]
    for x in (.745,.65,.5182):
        seed=next((ROOT/'results/L4').glob(f'*x{x:.8f}.json'));r=json.loads(seed.read_text())
        s=DressedSolver(4,16,128,eig_tol=1e-13);s.set_delta(x);theta=np.array(r['theta'])
        _,_,out,U=s.spectrum(theta,k=3);jac=s.response_jacobian(theta,out,U)
        jd=np.zeros_like(jac)
        for j in range(2):
            h=1e-5*max(1,abs(theta[j]));t=theta.copy();t[j]+=h;fp=s.spectrum(t,k=3)[0]
            t=theta.copy();t[j]-=h;fm=s.spectrum(t,k=3)[0];jd[:,j]=(fp-fm)/(2*h)
        res=float(np.max(abs(jac-jd)));assert res<2e-8
        ans.append({'x':x,'response_vs_full_spectral_difference':res,'jacobian_condition':float(np.linalg.cond(jac))})
    b=SphereBathBasis.build(4);op=ProductOperator(b,.75,8);loc=LocalProblem(8,80)
    w,_,_,_,_,_=loc.local(.75,.75/4,0.)
    ev=[]
    for f in (0,1):
        vals=(op.hb[:,None]+w.reshape(2,8)[op.kpar^f]).ravel();ev.append(np.sort(vals))
    free=max(abs(ev[0][1]-ev[0][0]-1.5),abs(ev[1][0]-ev[0][0]-.75),abs(ev[1][1]-ev[0][0]-2.25))
    assert free<1e-12
    report={'response':ans,'free_endpoint_max_residual':float(free)}
    (ROOT/'reproduced').mkdir(exist_ok=True)
    (ROOT/'reproduced/response_validation.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':main()
