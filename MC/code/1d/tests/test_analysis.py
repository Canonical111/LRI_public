#!/usr/bin/env python3
"""Synthetic multi-temperature regression and algebraic derivative tests."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fit_fss import ProfileFit
from quotients import LocalCurve,crossing

def main():
    entries=[]
    scales=np.array([.001,.01,.3,.0005,.006,.2])
    for n in [1024,2048,4096,8192,16384,32768]:
        for beta in [.4739,.4749,.4759]:
            entries.append(dict(N=n,s=.875,beta=beta,data=[1]*6,cov=np.diag(scales**2).tolist()))
    m=ProfileFit(entries);p=np.array([.004,.587,.37])
    amplitudes=np.array([1.2,.34,.08,-.04,-.16,.03,-.02,.44,.10,-.03,.01,.04,-.02,.015])
    exact=m.design(p)@amplitudes
    for e,v in zip(entries,exact):e['data']=v.tolist()
    test=ProfileFit(entries);f=test.fit()
    assert abs(f['Delta_epsilon']-p[1])<2e-6,(f['Delta_epsilon'],f['flags'])
    assert abs(f['omega_correction']-p[2])<2e-5
    beta_saved=m.beta.copy();h=1e-6
    m.beta=beta_saved+h;plus=m.design(p)@amplitudes
    m.beta=beta_saved-h;minus=m.design(p)@amplitudes
    m.beta=beta_saved
    for j in [0,3]:
        assert np.allclose((plus[:,j]-minus[:,j])/(2*h),exact[:,j+1],rtol=2e-6,atol=1e-6)
        assert np.allclose((plus[:,j]-2*exact[:,j]+minus[:,j])/h**2,exact[:,j+2],rtol=2e-4,atol=.002)
    # With corrections switched off, crossings are at beta_c and slope ratios
    # return the generating Delta_epsilon, at every finite size in synthetic data.
    amp=amplitudes.copy();amp[4:7]=0;amp[11:14]=0
    vals=m.design(p)@amp;curves={};coeffs={}
    for e,v in zip(entries,vals):e['data']=v.tolist()
    for n in sorted({e['N'] for e in entries}):
        c=LocalCurve([e for e in entries if e['N']==n],m.ref,3);curves[n]=c;coeffs[n]=c.fit()[0]
    outputs=[]
    for n in [1024,2048,4096,8192,16384]:
        for j in [0,1]:
            v=crossing(curves[n],curves[2*n],coeffs[n],coeffs[2*n],j)
            assert np.max(np.abs(v[1:]-p[1]))<1e-7,v
            assert abs(v[0]-(m.ref+p[0]/100))<1e-10
            outputs.append(v.tolist())
    result=dict(multi_temperature_fit=f,analytic_temperature_derivative_check=True,
                synthetic_crossing_quotients=outputs,warning='Synthetic regression tests, not measured CFT dimensions.')
    (ROOT/'tests/analysis_test_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Synthetic fit, derivative, and crossing regression tests passed.')
if __name__=='__main__':main()
