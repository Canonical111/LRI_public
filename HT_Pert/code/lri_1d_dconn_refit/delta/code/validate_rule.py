"""Validate the ensemble rule on sequences whose large-L values are known exactly and calibrate KAPPA.
V1: complete Dconn dC4, dC5 (train L<=44, test every exact L to 152).
V2: isolated g2D shifts k=4..7 (train <=44, test to 90/118), k=8 (train on L=4j<=44, test 48..92).
V3: remainders R4, R5 = Dconn - g2D (test to 118).
V4 (internal stress): dC6, dC7, dC8 themselves with hi=30 and hi=36 (test up to 44)."""
import sys, json, time
sys.path.insert(0, '<TMP>/scratchpad/dconn_fit/delta/code')
import numpy as np
from load import *
from ensemble import ensemble, RULE

t0 = time.time()
rc = load_recon(); g = load_g2d(); s10 = load_s10()
cases = []
cases.append(('V1 Dconn4', {L: rc[L][4] for L in rc}, 44, 2))
cases.append(('V1 Dconn5', {L: rc[L][5] for L in rc}, 44, 2))
for k in (4, 5, 6, 7):
    cases.append(('V2 g2D%d' % k, dict(g[k]), 44, 2))
cases.append(('V2 g2D8', {L: v for L, v in g[8].items() if L % 4 == 0 or L > 44}, 44, 2))
for k in (4, 5):
    cases.append(('V3 R%d' % k, {L: rc[L][k] - g[k][L] for L in rc if L in g[k]}, 44, 2))
for k in (6, 7, 8):
    for hi in (30, 36):
        cases.append(('V4 dC%d hi%d' % (k, hi), {L: s10[L][k] for L in s10}, hi, 2))

rule = dict(RULE)
if len(sys.argv) > 1:
    rule.update(json.loads(sys.argv[1]))
rep = {}
for name, seq, hi, step in cases:
    Lt = [L for L in sorted(seq) if L > hi and L <= 152]
    r = dict(rule)
    if name == 'V2 g2D8':   # only L = 4j below 48: 10 points from L=8; use low edges 4, 8 and 3 dof
        r.update(LOS=(4, 8), DOFMIN=3)
    e = ensemble(seq, hi, Lt, rule=r, step=step)
    if e is None:
        print(name, 'no admissible fits'); continue
    truth = np.array([seq[L] for L in Lt])
    err = e['median'] - truth
    ratio = np.abs(err) / np.maximum(e['spread'], 1e-300)
    change = np.abs(truth - seq[hi])
    rep[name] = dict(L=Lt, err=err.tolist(), spread=e['spread'].tolist(), ratio=ratio.tolist(),
                     inside=bool(np.all((truth >= e['lo']) & (truth <= e['hi']))), n_kept=e['n_kept'],
                     rel_err=(np.abs(err) / np.maximum(change, 1e-300)).tolist())
    sel = [i for i, L in enumerate(Lt) if L in (46, 60, 72, 92, 90, 118, 152, 32, 38, 44)]
    print('%-14s kept %3d/%3d  max ratio |err|/spread = %6.2f  in-envelope %s' % (
        name, e['n_kept'], e['n_all'], ratio.max(), rep[name]['inside']))
    for i in sel:
        print('      L=%3d err=%+.3e spread=%.3e ratio=%5.2f  |err|/|change|=%.2e' % (
            Lt[i], err[i], e['spread'][i], ratio[i], rep[name]['rel_err'][i]))
tag = 'default' if len(sys.argv) < 3 else sys.argv[2]
json.dump(dict(rule={k: list(v) if isinstance(v, tuple) else v for k, v in rule.items()}, rep=rep),
          open('../out/validation/validate_rule_%s.json' % tag, 'w'), indent=1)
print('time', time.time() - t0)
