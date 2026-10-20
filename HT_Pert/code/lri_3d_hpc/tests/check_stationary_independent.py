"""Independent Hermitian toy checks of the stationary expansion/window order."""
import argparse
import importlib.util
import json
import pathlib
import sys

import numpy as np
from scipy.sparse import csr_matrix

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'code'))
sys.path.insert(0, str(ROOT/'vendor'))
from optimized_solver import solve_coefficients as optimized
from native_backend import load_backend

spec = importlib.util.spec_from_file_location('unaltered_reference', ROOT/'reference/perturbative.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def numeric_payload(result):
    values = list(result['C']) + list(result['r']) + list(result['g'])
    for key in ('energies_by_seed', 'vacuum_energies_by_subcutoff'):
        for subkey in sorted(result[key], key=int):
            values.extend(result[key][subkey])
    return np.array(values, dtype=np.longdouble)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', '--native-cache', type=pathlib.Path, default=ROOT/'work/native-cache')
    parser.add_argument('--output', type=pathlib.Path, default=ROOT/'results/stationary_independent_validation.json')
    args = parser.parse_args()
    T = np.longdouble
    rng = np.random.default_rng(784016)
    N = np.array([0,2,2,4,4,4], dtype=np.int64)
    P = np.array([0,1,2,1,2,3], dtype=np.int64)
    vertices = []
    for j in range(1,5):
        series = []
        for k in range(11):
            a = rng.integers(-3,4,size=(len(N),len(N))).astype(T) / T(32*(k+1))
            a = (a+a.T)/2
            a[(P[:,None]+P[None,:])%2 != j%2] = 0
            a[0,0] = 0
            series.append(csr_matrix(a))
        vertices.append(series)
    backend = load_backend('native',threads=2,cache_dir=args.cache_dir)
    trials = []
    for order in (2,3,4,5,6,7,8,9,10,12):
        nz = (3+4*(order//2)+2)//2
        for mode in ('raw','consistent'):
            a = reference.solve_coefficients(N,P,vertices,4,order,nz,mode,T)
            b = optimized(N,P,vertices,4,order,nz,mode,T,strategy='stationary',spmm=backend.csr_spmm)
            aa, bb = numeric_payload(a), numeric_payload(b)
            err = np.max(np.abs(aa-bb)/np.maximum(T(1),np.abs(aa)))
            if err > T('5e-13'):
                raise AssertionError((order,mode,str(err)))
            trials.append({'order':order,'scheme':mode,'max_scaled_error':str(err),
                           'values_checked':len(aa), 'stationary_wavefunction_order':order//2})
    payload = {'pass':True, 'trials':trials, 'native_backend':backend.metadata,
               'maximum_scaled_error':str(max(T(t['max_scaled_error']) for t in trials)),
               'independent_test':'New arbitrary real Hermitian Taylor vertices; bath parity and zero vacuum diagonal; L=4 with three nested vacua; unmodified reference versus stationary with two native threads',
               'window_triangularity':'D_n annihilates psi0, so it first enters E_(n+2); all E_n are solved before D_n is constructed from those E_n at common couplings.'}
    path = args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({'pass':True,'trials':len(trials),
                      'maximum_scaled_error':payload['maximum_scaled_error'],'result':str(path)}))


if __name__ == '__main__':
    main()
