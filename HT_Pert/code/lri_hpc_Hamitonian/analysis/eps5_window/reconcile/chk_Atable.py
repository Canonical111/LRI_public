import sys, json
sys.dont_write_bytecode = True
import numpy as np
EXT = '<PROJECT>/lri_hpc_Hamitonian/analysis/extended'; AN = '<PROJECT>/lri_hpc_Hamitonian/analysis'
sys.path.insert(0, EXT); sys.path.insert(0, AN)
from analyze_joint import MODELS, load
from diagnose_systematic import thermal_fit, const_terms
S='<TMP>/scratchpad/eps5'
T = {int(k): v for k, v in json.load(open(S + '/reconcile/dC_reconciled.json')).items()}
At = {int(k): v for k, v in json.load(open(S + '/A/dC_table.json'))['table'].items()}
th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'][:6] for r in th])
m = L >= 50
ex = json.load(open(EXT + '/extended_summary.json')); w = {int(k): v for k, v in ex['gap_reference']['extended'].items()}
tk = lambda k, n='D': MODELS[n] + [(1, j) for j in range(1, k - 1) if (1, j) not in MODELS[n]]
for name, src in (('mine', lambda l: (T[l]['dC4_Dconn'], T[l]['dC5_Dconn'])), ('A', lambda l: (At[l]['Dconn']['dC4'], At[l]['Dconn']['dC5'])),
                  ('mine<=100,A>100', lambda l: (T[l]['dC4_Dconn'], T[l]['dC5_Dconn'] if l <= 100 else At[l]['Dconn']['dC5']))):
    X = C.copy()
    for i, l in enumerate(L):
        if l >= 8: d4, d5 = src(int(l)); X[i, 4] += d4; X[i, 5] += d5
    lim, d = thermal_fit(L[m], X[m], w, tk, maxorder=5)
    print(name, 'D+z^j/L lo=50 C5 = %.6f' % lim[5])
