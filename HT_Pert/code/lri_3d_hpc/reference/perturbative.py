"""Primary-tuned formal epsilon expansion of the supplied 3D HT Hamiltonian.

This is an order-by-order Rayleigh--Schrodinger calculation, with analytic
operator derivatives. No finite-epsilon or cutoff fit enters any coefficient.
The bath cutoff is the archive's N_b <= L product regulator. The free zero
oscillator is kept to an order-complete occupation ceiling (19 for order 8).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
from taylor_vertices import build_taylor_vertices


def normal_powers(nz, dtype):
    """Normal powers in a padded free oscillator; even states precede odd."""
    dim = 2 * nz
    a = np.diag(np.sqrt(np.arange(1, dim + 4, dtype=dtype)), 1)
    creations, annihilations = [np.eye(dim + 4, dtype=dtype)], [np.eye(dim + 4, dtype=dtype)]
    for _ in range(4):
        creations.append(a.T @ creations[-1])
        annihilations.append(a @ annihilations[-1])
    ix = np.r_[np.arange(0, dim, 2), np.arange(1, dim, 2)]
    ans = []
    for k in range(5):
        q = sum((math.comb(k, j) * creations[j] @ annihilations[k-j]
                 for j in range(k+1)), np.zeros_like(a))
        ans.append(q[np.ix_(ix, ix)])
    return ans


class BareSeries:
    """Hamiltonian Taylor coefficients shared by all vacuum subcutoffs."""
    def __init__(self, N, P, W, nz, order=8, dtype=np.longdouble):
        self.N, self.P, self.W = np.asarray(N), np.asarray(P), W
        self.nz, self.order, self.dtype = int(nz), int(order), np.dtype(dtype)
        self.T = self.dtype.type
        self.q = normal_powers(nz, self.dtype)
        self.r = np.zeros(order+1, dtype=dtype)
        self.g = np.zeros(order+1, dtype=dtype)
        self.terms = {}

    def build(self, n):
        """Store complete nth coefficient once its current couplings are set."""
        terms = []
        for degree, couplings, norm in ((2, self.r, self.T(1)),
                                        (4, self.g, self.T(1)/12)):
            for j in range(1, degree+1):
                matrix = None
                for i in range(1, n+1):
                    if couplings[i] == 0:
                        continue
                    val = self.W[j-1][n-i] * (norm * math.comb(degree,j) * couplings[i])
                    matrix = val if matrix is None else matrix + val
                if matrix is not None:
                    matrix = matrix.tocsr()
                    matrix.eliminate_zeros()
                    if matrix.nnz:
                        terms.append((j, degree-j, matrix))
        self.terms[n] = terms

    def apply(self, n, X, field, N, P):
        """Apply H_n without the vacuum window on a scalar subcutoff."""
        nb, nz = X.shape
        out = np.zeros_like(X)
        qlocal = self.r[n] * self.q[2] + self.g[n] / 12 * self.q[4]
        rows = [np.flatnonzero(P % 2 == p) for p in (0,1)]
        for bpar, selected in enumerate(rows):
            f = field ^ bpar
            block = qlocal[f*nz:(f+1)*nz, f*nz:(f+1)*nz]
            out[selected] += X[selected] @ block.T
            if n == 1:
                total_particles = P[selected,None] + f + 2*np.arange(nz)[None,:]
                out[selected] -= self.T(1)/4 * total_particles * X[selected]
        for bath_degree, local_degree, W in self.terms[n]:
            mat = W if nb == W.shape[0] else W[:nb,:nb]
            image = mat @ X
            for bpar, selected in enumerate(rows):
                f = field ^ bpar
                pin = f ^ (bath_degree % 2)
                block = self.q[local_degree][f*nz:(f+1)*nz, pin*nz:(pin+1)*nz]
                out[selected] += image[selected] @ block.T
        return out


class SeedSeries:
    """A nondegenerate seed with intermediate normalization <p|psi>=1."""
    def __init__(self, bare, cutoff, seed, mode):
        self.bare, self.cutoff, self.seed, self.mode = bare, int(cutoff), int(seed), mode
        keep = bare.N <= cutoff
        self.nb = int(np.sum(keep))
        if not np.array_equal(np.flatnonzero(keep), np.arange(self.nb)):
            raise ValueError('Scalar bath basis is not ordered by level')
        self.N, self.P = bare.N[:self.nb], bare.P[:self.nb]
        if self.N[0] != 0 or self.P[0] != 0:
            raise ValueError('Expected bath vacuum in first scalar column')
        self.field = seed % 2
        localp = self.field ^ (self.P % 2)
        self.totalp = self.P[:,None] + localp[:,None] + 2*np.arange(bare.nz)[None,:]
        self.h0 = self.N[:,None] + bare.T(3)/4*self.totalp
        self.E = np.zeros(bare.order+1, dtype=bare.dtype)
        self.E[0] = bare.T(3)*seed/4
        self.denominator = self.E[0] - self.h0
        self.index = (0, seed//2)
        self.denominator[self.index] = 1
        if np.any(self.denominator == 0):
            raise ValueError('Seed is degenerate in retained symmetry sector')
        v = np.zeros_like(self.h0, dtype=bare.dtype)
        v[self.index] = 1
        self.psi = [v]
        self.windows = [np.zeros(self.nb, dtype=bare.dtype)
                        for _ in range(bare.order+1)]
        self.max_recursion_residual = bare.T(0)

    def apply(self, n, X):
        out = self.bare.apply(n, X, self.field, self.N, self.P)
        if self.mode == 'consistent':
            out += self.windows[n][:,None] * X
        return out

    def provisional(self, n):
        """Current energy without r_n,g_n (its D_n expectation is zero)."""
        value = self.bare.T(0)
        for k in range(1,n):
            value += self.apply(k, self.psi[n-k])[self.index]
        if n == 1:
            value -= self.bare.T(self.seed)/4
        return value

    def advance(self, n):
        accum = np.zeros_like(self.psi[0])
        for k in range(1,n+1):
            accum += self.apply(k,self.psi[n-k]) - self.E[k]*self.psi[n-k]
        seed_residual = abs(accum[self.index])
        scale = max(self.bare.T(1), abs(self.E[n]))
        self.max_recursion_residual = max(self.max_recursion_residual, seed_residual/scale)
        accum[self.index] = 0
        new = accum / self.denominator
        new[self.index] = 0
        self.psi.append(new)


def solve_coefficients(N,P,W,cutoff,order=8,nz=10,mode='consistent',dtype=np.longdouble,
                       keep_states=False,progress=False):
    """Return tuned coefficients for one bath cutoff and one window scheme.

    All lower vacua in the consistent scheme use *the top cutoff's couplings*;
    they are never separately retuned. Absolute vacuum energies can be used:
    the archive's common local-ground subtraction cancels from every D.
    """
    if mode not in ('raw','consistent'):
        raise ValueError('mode must be raw or consistent')
    if cutoff < 0 or cutoff % 2:
        raise ValueError('Require an even nonnegative bath cutoff')
    required = 3 + 4*(order//2)
    if 2*nz-1 < required:
        raise ValueError(f'Local occupation cap must be at least {required} at order {order}')
    if len(W[0]) < order-1:
        raise ValueError('Need bath vertex derivatives through order-2')
    nb = int(np.sum(N <= cutoff))
    N, P = np.asarray(N[:nb]), np.asarray(P[:nb])
    W = [[a[:nb,:nb].astype(dtype) for a in s] for s in W]
    bare = BareSeries(N,P,W,nz,order,dtype)
    roots = {p:SeedSeries(bare,cutoff,p,mode) for p in range(4)}
    vacua = ({ell:SeedSeries(bare,ell,0,mode) for ell in range(0,cutoff,2)}
             if mode == 'consistent' else {})
    vacua[cutoff] = roots[0]
    all_states = list(vacua.values()) + [roots[p] for p in (1,2,3)]
    C = np.zeros(order+1,dtype=dtype)
    C[0] = bare.T(3)/2
    started = time.perf_counter()
    tuning = []
    for n in range(1,order+1):
        provisional = {p:roots[p].provisional(n) for p in range(4)}
        # Vacuum has zero Gaussian-normal-ordered mass/quartic diagonal.
        for ell, state in vacua.items():
            state.E[n] = provisional[0] if ell == cutoff else state.provisional(n)
        target_sigma = -bare.T(1)/4 if n == 1 else bare.T(0)
        target_chi = bare.T(1)/4 if n == 1 else bare.T(0)
        bare.r[n] = (target_sigma-provisional[1]+provisional[0])/2
        bare.g[n] = (target_chi-provisional[3]+provisional[0]-6*bare.r[n])/3
        for p in (1,2,3):
            roots[p].E[n] = provisional[p] + 2*p*bare.r[n] + bare.T(p*(p-1))/2*bare.g[n]
        C[n] = roots[2].E[n] - roots[0].E[n]
        tuning.append({'order':n,
          'sigma_residual':float(roots[1].E[n]-roots[0].E[n]-target_sigma),
          'chi_residual':float(roots[3].E[n]-roots[0].E[n]-target_chi)})
        if mode == 'consistent':
            for state in all_states:
                state.windows[n] = np.array([
                    vacua[state.cutoff].E[n]-vacua[state.cutoff-int(lev)].E[n]
                    if lev else 0 for lev in state.N],dtype=dtype)
        if n < order:
            bare.build(n)
            for state in all_states:
                state.advance(n)
        if progress:
            print(json.dumps({'cutoff':cutoff,'mode':mode,'order':n,
                    'C':float(C[n]),'r':float(bare.r[n]),'g':float(bare.g[n]),
                    'seconds':time.perf_counter()-started}),flush=True)
    result = {
      'dimension':3,'cutoff':cutoff,'cutoff_definition':'bath N_b=sum(2n+l) occupancy <= L',
      'epsilon':'2s-3','x':'(3-epsilon)/4',
      'thermal_expansion':'Delta_thermal = sum_n C[n] epsilon^n; C0=3/2, C1=-1/6',
      'scheme':mode,'order':order,'arithmetic':str(np.dtype(dtype)),
      'scalar_bath_states':nb,'local_occupation_max':2*nz-1,
      'dimension_per_field_parity':nb*nz,
      'C':[str(x) for x in C],'r':[str(x) for x in bare.r],'g':[str(x) for x in bare.g],
      'energies_by_seed':{str(p):[str(x) for x in roots[p].E] for p in range(4)},
      'vacuum_energies_by_subcutoff':{str(ell):[str(x) for x in st.E] for ell,st in vacua.items()},
      'tuning_residuals':tuning,
      'max_scaled_seed_recursion_residual':float(max(st.max_recursion_residual for st in all_states)),
      'seconds':time.perf_counter()-started,
      'scope':'finite-cutoff formal coefficients; no continuum extrapolation or complete connected matching',
    }
    return (result,bare,roots,vacua) if keep_states else result


def source_hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('code','vendor/ht3d') for p in sorted((ROOT/folder).glob('*.py'))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cutoffs',type=int,nargs='+',default=[0,2,4,6,8])
    p.add_argument('--order',type=int,default=8)
    p.add_argument('--nz',type=int,default=10)
    p.add_argument('--schemes',nargs='+',choices=['raw','consistent'],default=['raw','consistent'])
    p.add_argument('--dtype',choices=['float64','longdouble'],default='longdouble')
    p.add_argument('--cache',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'results'/'coefficients.json')
    p.add_argument('--max-states',type=int,default=2_000_000)
    args=p.parse_args()
    order=args.order
    cutoffs=sorted(set(args.cutoffs))
    if order < 2 or any(x<0 or x%2 for x in cutoffs):
        raise ValueError('Require order>=2 and nonnegative even cutoffs')
    dtype=np.longdouble if args.dtype=='longdouble' else np.float64
    started=time.perf_counter()
    hashes=source_hashes()
    # Pickle cache is strictly local generated numerical data, never an upload.
    if args.cache is not None and args.cache.exists():
        with args.cache.open('rb') as f:
            data=pickle.load(f)
        if data['cutoff']!=max(cutoffs) or data['degree']<order-2 or data['dtype']!=str(np.dtype(dtype)):
            raise ValueError('Local vertex cache parameter mismatch')
        N,P,W,metadata=data['N'],data['P'],data['W'],data['metadata']
        if data['vertex_source_hash']!=hashes['code/taylor_vertices.py']:
            raise ValueError('Local vertex cache source mismatch')
    else:
        print(json.dumps({'event':'build_vertices','cutoff':max(cutoffs),'degree':order-2}),flush=True)
        N,P,W,metadata=build_taylor_vertices(max(cutoffs),degree=order-2,dtype=dtype,
                         max_states=args.max_states,return_metadata=True)
        if args.cache is not None:
            args.cache.parent.mkdir(parents=True,exist_ok=True)
            with args.cache.open('wb') as f:
                pickle.dump({'cutoff':max(cutoffs),'degree':order-2,'dtype':str(np.dtype(dtype)),
                            'vertex_source_hash':hashes['code/taylor_vertices.py'],
                            'N':N,'P':P,'W':W,'metadata':metadata},f,protocol=5)
    print(json.dumps({'event':'vertices_ready',**{k:metadata[k] for k in ('scalar_bath_states','vertex_array_bytes','vertex_seconds')}}),flush=True)
    results=[]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for L in cutoffs:
        for scheme in args.schemes:
            results.append(solve_coefficients(N,P,W,L,order,args.nz,scheme,dtype,progress=True))
            payload={'source_hashes':hashes,'vertex_metadata':metadata,'results':results,
                     'elapsed_seconds':time.perf_counter()-started}
            tmp=args.output.with_suffix('.tmp')
            tmp.write_text(json.dumps(payload,indent=2,default=lambda x:x.item())+'\n')
            os.replace(tmp,args.output)
    csvfile=args.output.with_suffix('.csv')
    with csvfile.open('w',newline='') as f:
        fields=['cutoff','scheme','scalar_bath_states']+[f'C{n}' for n in range(2,order+1)]
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for result in results:
            writer.writerow({**{k:result[k] for k in fields[:3]},
                             **{f'C{n}':result['C'][n] for n in range(2,order+1)}})


if __name__=='__main__':
    main()
