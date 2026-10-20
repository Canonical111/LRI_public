"""Independent fresh and saved checks; no high-order thermal targets are read."""
from pathlib import Path
from fractions import Fraction as F
import sys,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'code'),str(ROOT/'vendor')]
from response import solve
from exact_response import solve as exact_solve
from phase_response_shell import Engine
from mixing_asymptotics import derive

def C2_exact(L):
    c=F(1);ans=F(34,81)
    for n in range(1,L-1):
        c*=F(2*n-1,2*n)
        if n%2==0:ans+=c*(F(2,9)/(n-F(1,2))+F(2)/(n+F(1,2))+F(2,9)/(n+1)+F(2,n))/9
    return ans

def main():
    out={};mx=0;fresh=0
    for L in [2,4]:
      for ch in ['phi6','phase','number','full']:
        r=solve(L,8,'dconn',ch);e=exact_solve(L,8,'dconn',ch)
        for k in ['C','response']:
            vv=np.array([float(F(z)) for z in e[k]]);diff=float(np.max(abs(np.array(r[k])-vv)/np.maximum(1,abs(vv))))
            mx=max(mx,diff)
        saved=json.loads((ROOT/f'results/dconn_{ch}_L{L}_d8.json').read_text())
        fresh=max(fresh,float(np.max(abs(np.array(r['response'])-saved['response'])/np.maximum(1,abs(np.array(saved['response']))))))
    assert mx<2e-11
    out.update(exact_rational_scaled_error=mx,fresh_saved_scaled_error=fresh)
    line=0;asource=0;cs=0;phase=0;max_base=0
    for f in (ROOT/'results').glob('dconn_phi6_L*_d8.json'):
        a=json.loads(f.read_text());L=a['low_cutoff'];p=json.loads((ROOT/f'results/dconn_phase_L{L}_d8.json').read_text());n=json.loads((ROOT/f'results/dconn_number_L{L}_d8.json').read_text());v=json.loads((ROOT/f'results/dconn_full_L{L}_d8.json').read_text())
        line=max(line,float(np.max(abs(np.array(v['response'])-np.array(p['response'])-n['response'])/np.maximum(1,abs(np.array(v['response']))))))
        cs=max(cs,abs(a['C'][2]-float(C2_exact(L))))
        X=sum(F(240,n+1)+F(720)/(n+F(1,2))+(F(240,n) if n else 0) for n in range(0,L,2))
        pred=float(X)/27-80*(a['g'][2]+a['C'][2])/3
        asource=max(asource,abs(a['response'][3]-pred))
        shell=Engine(L,direct=True).calc()['response4'];phase=max(phase,abs(shell-p['response'][4]))
        max_base=max(max_base,float(np.max(abs(np.array(a['C'])-v['C']))))
    assert line<2e-11 and cs<2e-13 and asource<2e-11 and phase<2e-11
    out.update(source_linearity_scaled_error=line,base_channel_agreement=max_base,C2_finite_error=cs,phi6_response3_identity_error=asource,phase_response4_shell_error=phase)
    regauge=0
    for L in [4,8]:
      for ch in ['mass','quartic']:
        r=solve(L,8,'dconn',ch);regauge=max(regauge,max(abs(z) for z in r['response']))
    assert regauge<1e-8;out['mass_quartic_reparameterization_error']=regauge
    fft=0
    for L in [64,128,256]:
        a=Engine(L,direct=True).calc();b=Engine(L,direct=False).calc();fft=max(fft,abs(a['response4']-b['response4']))
    assert fft<1e-12;out['convolution_backend_error']=fft
    a=json.loads((ROOT/'results/phase_finite_part_N256_O6.json').read_text());b=json.loads((ROOT/'results/phase_finite_part_N512_O6.json').read_text())
    import mpmath as mp
    mp.mp.dps=60;out['finite_part_convergence_difference']=str(abs(mp.mpf(a['finite_part'])-mp.mpf(b['finite_part'])))
    assert mp.mpf(out['finite_part_convergence_difference'])<mp.mpf('1e-15')
    d=derive();out['analytic_A_Q_B']=d['numeric'];out['scope']='Numerical identities and specific subkernel convergence, not complete C6/C7/C8 tail certification.'
    (ROOT/'results/validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
