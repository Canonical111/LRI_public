#!/usr/bin/env python3
"""ARCHIVE-FREE regression test of the strict window modes of assemble_from_raw.py.

Added by the spec gate reviewer (2026-10-02).  Uses SYNTHETIC random raw coefficients (fixed
seed), so it reads no archive file and checks only the assembler's bookkeeping:
  1. exactly the documented required set (every tight scalar + the 6 below-bound scalars, the
     latter = 0, NO genuine positive-power extra) passes --windows both/safe/tight, and the three
     modes give identical inputs and invariants;
  2. adding the 3 genuine extras changes nothing;
  3. a non-zero below-bound scalar makes --windows both fail (exit-code path), with or without
     the genuine extras supplied, and never crashes;
  4. a missing tight or below-bound scalar raises MissingCoefficient listing every missing one;
  5. --fill-two-kink-exact supplies every absent Z2_*/Q2_* scalar;
  6. the archive layout is refused.
Runs in about 2 s.  Exit code 0 on success.
"""
import copy, json, random, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble_from_raw as asm  # noqa: E402

random.seed(20261002)
tight, below, genuine = asm.requirements()
assert (len(tight), len(below), len(genuine)) == (195, 6, 3), (len(tight), len(below), len(genuine))


def build(keys, below_value='0'):
    raw = {}
    for a, p, k in keys:
        val = below_value if (a, p, k) in below else repr(random.uniform(-3, 3))
        raw.setdefault(a, {}).setdefault(str(p), {})[str(k)] = val
    return raw


fails = []
def check(cond, what):
    print(('ok    ' if cond else 'FAIL  ') + what)
    if not cond:
        fails.append(what)


base = build(tight + below)
res = {}
for mode in ('both', 'safe', 'tight'):
    try:
        r, ok = asm.run(copy.deepcopy(base), mode, 40)
        res[mode] = r
        check(ok, f'documented required set (no genuine extras) passes --windows {mode}')
    except asm.MissingCoefficient as e:
        check(False, f'documented required set passes --windows {mode}: {e}')
if len(res) == 3:
    check(res['both']['inputs'] == res['safe']['inputs'] == res['tight']['inputs']
          and res['both']['invariants'] == res['safe']['invariants'] == res['tight']['invariants'],
          'tight, safe and both give identical inputs and invariants')
    check(res['both']['checks'].get('tight_vs_safe_max_abs_diff') == '0.0', 'tight vs safe difference is exactly 0')

with_extras = copy.deepcopy(base)
for a, p, k in genuine:
    with_extras.setdefault(a, {}).setdefault(str(p), {})[str(k)] = repr(random.uniform(-3, 3))
r2, ok2 = asm.run(copy.deepcopy(with_extras), 'both', 40)
check(ok2 and 'both' in res and r2['invariants'] == res['both']['invariants'], 'supplying the genuine extras changes nothing')

for a, p, k in below:
    for src, lab in ((base, 'without'), (with_extras, 'with')):
        raw = copy.deepcopy(src)
        raw[a][str(p)][str(k)] = '1e-3'
        try:
            r3, ok3 = asm.run(raw, 'both', 40)
            check(not ok3 and r3['checks']['below_tight_bound_all_vanish'] is False,
                  f'non-zero {a} [eps^{p} l^{k}] ({lab} genuine extras) -> --windows both fails cleanly')
        except Exception as e:  # noqa: BLE001
            check(False, f'non-zero {a} [eps^{p} l^{k}] ({lab} genuine extras) crashed: {type(e).__name__} {e}')

raw = copy.deepcopy(base)
del raw['A7_v']['0']['1']
del raw[below[0][0]][str(below[0][1])][str(below[0][2])]
try:
    asm.run(raw, 'both', 40)
    check(False, 'missing scalars raise MissingCoefficient')
except asm.MissingCoefficient as e:
    check('A7_v [eps^0 l^1]' in str(e) and f'{below[0][0]} [eps^{below[0][1]} l^{below[0][2]}]' in str(e),
          'missing scalars raise MissingCoefficient listing all of them')

raw = {a: v for a, v in copy.deepcopy(base).items() if not a.startswith(('Z2_', 'Q2_'))}
r5, ok5 = asm.run(raw, 'both', 40, fill_exact=True)
check(ok5 and len(r5['checks']['two_kink_filled_from_exact']) > 0, '--fill-two-kink-exact supplies the absent Z2_*/Q2_* scalars')

with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh:
    json.dump({'raw': {'A3_base': {}}}, fh)
try:
    asm.load_raw(fh.name)
    check(False, 'archive layout refused')
except ValueError:
    check(True, 'archive layout refused')
Path(fh.name).unlink()

print('ALL PASS' if not fails else f'{len(fails)} FAILURES')
sys.exit(1 if fails else 0)
