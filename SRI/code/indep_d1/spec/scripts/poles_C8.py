#!/usr/bin/env python3
"""Pole-cancellation targets for the normalized jets of C8 (archive-free).

Every vacuum-normalized response (C_n, K_n and their first source derivatives E C_n, E K_n, with any d_v, d_delta) is
free of negative cutoff powers: the power divergences of collapsed neutral pairs factor out with the vacuum Z's
(phase 2 verified this on 702 coefficients of 37 jets, RESULTS.md step 2 (ii)).  For every normalized jet the C8
inputs use, this script lists the coefficients [eps^p l^k], p < 0 (all k), that must vanish, and the raw scalars
[eps^p l^k] (all log powers) needed to form them: for a Leibniz product, a factor needs p from its tight leading power
up to -1 - sum(tight leading powers of the other factors) (Z2, Q2 supports respected).
Imports the helper functions of derive_requirements_C8.py (same definitions).  Output: ../out/C8/poles_C8.json
"""
import json, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import derive_requirements_C8 as D       # noqa: E402  (module level: normalization + helpers only)

OUT = HERE.parent / 'out' / 'C8'
t0 = time.time()
norm = json.load(open(OUT / 'normalized_atoms_C8.json'))
jets = {}
for at, inf in norm.items():
    key = (inf['normalized_response'], inf['d_v_order'], inf['d_delta_order'])
    jets.setdefault(key, {'new': False, 'atoms': []})
    jets[key]['atoms'].append(at)
    jets[key]['new'] |= inf['new_for_C8']


def pole_windows(factors, P):
    info = [D.raw_atom_name(f) for f in factors]
    out = {}
    for j, (atom, base) in enumerate(info):
        others = [b for i, (_, b) in enumerate(info) if i != j]
        hi = P - sum(D.pmin_tight(b) for b in others)
        lo = D.pmin_tight(base)          # targets run over every P <= -1, so the lower end is the factor's own bound
        for p in range(lo, hi + 1):
            if base == 'Z2' and p not in (-1, 0):
                continue
            if base == 'Q2' and p not in (0, 1):
                continue
            out.setdefault(atom, set()).add(p)
    return out


res, total_new, total_all = {}, {}, {}
for (name, i, j), info in sorted(jets.items()):
    terms = D.leibniz_terms(name, i, j)
    pmin_jet = min(sum(D.pmin_tight(D.raw_atom_name(f)[1]) for f in fs) for c, fs in terms)
    win = {}
    for c, fs in terms:
        for atom, ps in pole_windows(fs, -1).items():
            win.setdefault(atom, set()).update(ps)
    tagd = D.dername(i, j)
    entry = {'jet': f'd_v^{i} d_delta^{j} {name}', 'new_for_C8': info['new'],
             'must_vanish': f'[eps^p l^k] for p = {pmin_jet} .. -1, every k' if pmin_jet < 0 else 'no negative power possible',
             'eps_powers_to_check': list(range(pmin_jet, 0)),
             'raw_eps_powers_needed_all_logs': {a: sorted(ps) for a, ps in sorted(win.items())}}
    res[f'{name}[v{i}d{j}]'] = entry
    for a, ps in win.items():
        total_all.setdefault(a, set()).update(ps)
        if info['new']:
            total_new.setdefault(a, set()).update(ps)
json.dump({
    'note': 'ARCHIVE-FREE pole-cancellation targets (scripts/poles_C8.py): every listed coefficient of a normalized jet must '
            'vanish; the raw windows are the coefficients (all log powers) needed to form them. Exactly vanishing two-kink '
            'pieces (out/C8/two_kink_exact_C8.json) may be filled exactly.',
    'n_jets': len(res), 'n_new_jets': sum(e['new_for_C8'] for e in res.values()),
    'jets': res,
    'raw_needed_for_new_jets': {a: sorted(ps) for a, ps in sorted(total_new.items(), key=lambda x: (D.nkinks(x[0]), x[0]))},
    'raw_needed_for_all_jets': {a: sorted(ps) for a, ps in sorted(total_all.items(), key=lambda x: (D.nkinks(x[0]), x[0]))},
}, open(OUT / 'poles_C8.json', 'w'), indent=1)
print('jets', len(res), 'new', sum(e['new_for_C8'] for e in res.values()), 'raw atoms for new-jet pole checks', len(total_new),
      round(time.time() - t0, 1), 's')
