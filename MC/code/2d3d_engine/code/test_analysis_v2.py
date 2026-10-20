#!/usr/bin/env python3
"""Deterministic tests of MBAR, derivatives, overlap, and CFT quotient normalization."""
from pathlib import Path
import json
import numpy as np
from scipy.special import logsumexp
from multihist import MultiHistogram
from precision_analysis import crossing
ROOT=Path(__file__).resolve().parent

def main():
    K=np.arange(0,121,dtype=float);betas=np.array([.16,.18,.20]);logg=-(K-60)**2/200-K*np.log(.18)
    logp=logg[None,:]+np.log(betas)[:,None]*K;logp-=logsumexp(logp,axis=1)[:,None]
    H=np.array([2e5,3e5,4e5])[:,None]*np.exp(logp)
    m=.07+.004*K;features=np.stack([m,1.5*m*m,3*m**3,8*m**4]);S=features*H.sum(0)
    c=MultiHistogram(K,H,S,betas,2,64,1.4)
    beta=.184
    def exact(b):
        p=np.exp(logg+K*np.log(b)-logsumexp(logg+K*np.log(b)));M=features@p
        return np.r_[64**.6*M[0],1-M[1]/(3*M[0]**2),1-M[2]/(15*M[0]**3),1-M[3]/(105*M[0]**4)]
    pred,ess=c.evaluate(beta);h=1e-5
    deriv=(exact(beta-2*h)-8*exact(beta-h)+8*exact(beta+h)-exact(beta+2*h))/(12*h)
    second=(-exact(beta+2*h)+16*exact(beta+h)-30*exact(beta)+16*exact(beta-h)-exact(beta-2*h))/(12*h*h)
    report={'mbar_value_max_error':float(abs(pred[:,0]-exact(beta)).max()),
            'mbar_first_derivative_max_error':float(abs(pred[:,1]-deriv).max()),
            'mbar_second_derivative_max_error':float(abs(pred[:,2]-second).max()),
            'overlap':c.diagnostics()}
    assert report['mbar_value_max_error']<1e-9
    assert report['mbar_first_derivative_max_error']<2e-7
    assert report['mbar_second_derivative_max_error']<2e-4
    assert abs(c.overlap.sum(1)-1).max()<1e-8
    class Curve:
        def __init__(self,L):self.L=L;self.d=2;self.s=1.4;self.betas=np.array([.195,.205])
        def evaluate(self,b):
            a=self.L**1.07;x=(b-.2)*a
            # Four independently normalized dimensionless observables, exact same y.
            return np.array([[q+.2*x+.01*x*x,.2*a+.02*x*a,.02*a*a] for q in [1.3,.4,.6,.7]]),1.
    v,diag=crossing(Curve(16),Curve(32))
    report['synthetic_Delta_epsilon']=v[1:].tolist();assert np.max(abs(v[1:]-.93))<1e-10
    assert abs(v[0]-.2)<1e-12
    # A disconnected/degenerate fit must not quietly return a tiny error bar.
    try:
        crossing(Curve(16),Curve(16))
        raise AssertionError('degenerate crossing accepted')
    except ValueError:pass
    report['degenerate_crossing_rejected']=True
    (ROOT.parent/'tests/analysis_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
