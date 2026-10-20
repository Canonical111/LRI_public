#!/usr/bin/env python3
"""Untuned spin-one and spin-two spectra at accepted scalar couplings."""
from pathlib import Path
import argparse,json,sys,time
import numpy as np
from d3dressed.solver import DressedSolver
from scan import atomic

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--deltas',type=float,nargs='+',default=[.745,.7,.65,.6,.55,.5182]);p.add_argument('--spins',type=int,nargs='+',default=[1]);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=[]
    for x in args.deltas:
        paths=list(args.inputs.glob(f'*x{x:.8f}.json'))
        if len(paths)!=1:raise ValueError(f'Expected one primary record at {x}')
        r=json.loads(paths[0].read_text());zero=None
        for J in args.spins:
            start=time.time();s=DressedSolver(r['bath_cut'],r['nz_per_parity'],r['auxiliary_oscillator_size'],angular=J,backend='tensor',eig_tol=1e-12,ncv=40)
            s.set_delta(x);_,info,levels,U=s.spectrum(r['theta'],k=4,diagnostics=True)
            # Reconstruct scalar vacuum with identical local subtraction convention.
            if zero is None:
                a=DressedSolver(r['bath_cut'],r['nz_per_parity'],r['auxiliary_oscillator_size'],backend='tensor',eig_tol=1e-12,ncv=40,basis=s.basis)
                a.set_delta(x);_,_,prim,_=a.spectrum(r['theta'],k=4,diagnostics=True);zero=prim[0][0][0]
            gaps={str(f):(levels[f][0]-zero).tolist() for f in (0,1)}
            q={'x':x,'bath_cut':r['bath_cut'],'spin':J,'nz':s.nz,'osc':s.osc,'even_gaps':gaps['0'],'odd_gaps':gaps['1'],'tuned_theta':r['theta'],'eigenvector_residual':info['max_eigenvector_residual'],'dimension':2*s.op.dim,'projection_tests':s.op.projection_tests,'seconds':time.time()-start,'scope':'Untuned rotational-sector candidate levels; no independent OPE identification at strong coupling'}
            if J==1:q['spin_descendant_error']=gaps['1'][0]-x-1;q['thermal_descendant_error']=gaps['0'][0]-r['Delta_thermal']-1
            if J==2:q['stress_candidate_minus_three']=gaps['0'][0]-3
            if info['max_eigenvector_residual']>2e-7:raise RuntimeError('Eigenvector gate failed')
            out.append(q);atomic(args.output,out);print(J,x,gaps['0'][0],gaps['1'][0],flush=True)
if __name__=='__main__':main()
