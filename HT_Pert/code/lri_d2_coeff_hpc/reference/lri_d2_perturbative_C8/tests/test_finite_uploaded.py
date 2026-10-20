"""Use the UNMODIFIED uploaded finite-coupling solver as an independent oracle.
No epsilon fit extracts any coefficient. Couplings are the Taylor series already
computed by circle_jets, evaluated at epsilon, without additional tuning.
"""
from pathlib import Path
import sys,json,time,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'upstream/lri_2d_hpc_optimized/code'))
from ht2d.solver import DressedSolver

def val(js,e):return np.polynomial.polynomial.polyval(e,js)

def main():
    start=time.perf_counter();rows=[]
    for L in (2,4):
      for scheme in ('raw','consistent'):
        d=json.loads((ROOT/f'results/coefficients/{scheme}_L{L}_d8.json').read_text())
        for eps in (.08,.04,.02):
            x=.5-eps/4;r=val(d['r'],eps);g=val(d['g'],eps);A=x/4+r-g/2
            scale=(g*x*x/192)**(1/3);theta=[A*x/(4*scale*scale),math.log(scale)]
            s=DressedSolver(L,24,192,window='none' if scheme=='raw' else 'vacuum',backend='tensor',eig_tol=1e-13,window_tol=1e-13)
            s.set_delta(x);res,info,out,_=s.spectrum(theta,k=4,diagnostics=True)
            gap=float(out[0][0][1]-out[0][0][0]);pred=val(d['C'],eps)
            rows.append(dict(L=L,scheme=scheme,epsilon=eps,thermal=gap,polynomial=pred,remainder=gap-pred,remainder_over_epsilon9=(gap-pred)/eps**9,max_eigenvector_residual=info['max_eigenvector_residual'],primary_residual=res.tolist()))
            print(rows[-1],flush=True)
    ratios=[]
    for L in (2,4):
      for scheme in ('raw','consistent'):
        rr=[r for r in rows if r['L']==L and r['scheme']==scheme]
        ratios.append(dict(L=L,scheme=scheme,halving_factors=[abs(a['remainder']/b['remainder']) for a,b in zip(rr,rr[1:])]))
    # C9+ corrections at eps=.08 are appreciable; only broad ninth-order scaling asserted.
    assert all(300<v<800 for r in ratios for v in r['halving_factors']),ratios
    record=dict(rows=rows,halving_tests=ratios,expected_asymptotic_factor=512,seconds=time.perf_counter()-start,scope='Independent unexpanded uploaded solver at fixed Taylor couplings; numerical remainder checks only, no epsilon fitting.')
    (ROOT/'results/finite_uploaded_validation.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(ratios,indent=2))
if __name__=='__main__':main()
