#!/usr/bin/env python3
"""A-PERF-5: the final binary's speedup over the Stage-3 baseline per (sector, L), default path and each opt-in profile,
per site. Mac, seconds. Inputs (all committed records):
  default, Expanse (GCC 13.3, EPYC 7742): benchmarks/expanse_2026-10-c8/stage5/exp/s5e_summary.json perf5 (J-SWEEP-2E
      54676908 against J-SWEEP-1 54641706; kernel seconds per point summed over every graph of the stratum, both
      campaigns);
  default, symmetry (GCC 11.4, EPYC 7543): benchmarks/symmetry_2026-10-c8/stage5/s5perf5.570098.0/perf5.json (the same
      node, J-SWEEP-3's stratified subset of 2,203 keys, final binary against the symmetry Stage-3 baseline built from
      c8-stage3);
  profiles: the Stage-4c gate records (Expanse), k = exact / profile per (sector, L) over the final default binary (F4
      per sector at L8, F2's pooled task seconds at L <= 7; aflag7_table.py speedups()). A profile over Stage 3 = the
      default's factor x k (two measurements multiplied: an estimate). On symmetry the Expanse k are assumed (F10: not
      measured there). The APPROVED profile dd+mp256 (user check-in 2026-10-05: production after the pilot, pending
      its own J-FLAG build gate) was measured as the dd+mp256+exp1 build; exp1 is inert (code layout only, x1.007).
      exp1 alone and R7 are not approved.
  aperf5_table.py --package PKG --out FILE.json [--markdown FILE.md]"""
import argparse, importlib.util, json
from pathlib import Path
PROFILES = {'dd+mp256': 's4cgate.54673902.0/jflag_dd_mp256_exp1', 'dd': 's4cgate.54673900.0/jflag_dd',
            'mp256': 's4cgate.54673901.0/jflag_mp256', 'exp1': 's4cgate.54673904.0/jflag_exp1'}
STATUS = {'dd+mp256': 'APPROVED after the pilot (build gate pending); k of the dd+mp256+exp1 build',
          'dd': 'measured alone (component of the approved combination)', 'mp256': 'measured alone (component of the approved combination)',
          'exp1': 'not approved (inert)'}
ap = argparse.ArgumentParser(); ap.add_argument('--package', type=Path, required=True); ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--markdown', type=Path); a = ap.parse_args()
pkg = a.package.resolve(); gate = pkg / 'benchmarks/expanse_2026-10-c8/stage4c/gate'
spec = importlib.util.spec_from_file_location('aflag7_table', gate / 'scripts/aflag7_table.py'); af = importlib.util.module_from_spec(spec); spec.loader.exec_module(af)
k = {p: af.speedups(json.loads((gate / d / 'numerics_flags.json').read_text()))['used'] for p, d in PROFILES.items()}
E = json.loads((pkg / 'benchmarks/expanse_2026-10-c8/stage5/exp/s5e_summary.json').read_text())['perf5']
S = json.loads((pkg / 'benchmarks/symmetry_2026-10-c8/stage5/s5perf5.570098.0/perf5.json').read_text())
rows = {}
for s in ('free', 'power'):
    for L in range(3, 9):
        n = f'{s}_L{L}'; e = E['per_sector_L'][n]['speedup']; y = S['by_sector_L'][f'{s}:{L}']['speedup']
        rows[n] = {'default_expanse': e, 'default_symmetry': y, **{f'{p}_expanse': e * k[p][n] for p in k}, **{f'{p}_symmetry': y * k[p][n] for p in k},
                   **{f'{p}_over_final': k[p][n] for p in k}}
doc = {'rule': __doc__, 'status': STATUS, 'totals': {'default_expanse': E['total']['all']['speedup'], 'default_symmetry': S['total']['speedup']},
       'rows': rows}
json.dump(doc, open(a.out, 'w'), indent=1)
lines = ['| Sector, L | default: Expanse | default: symmetry | `dd+mp256` (approved): Expanse | `dd+mp256`: symmetry (assumed k) | `dd`: Expanse | `mp256`: Expanse | `exp1` (not approved): Expanse |',
         '|---|---:|---:|---:|---:|---:|---:|---:|']
for n, r in rows.items():
    lines.append(f'| {n.replace("_L", " L")} | ×{r["default_expanse"]:.3f} | ×{r["default_symmetry"]:.3f} | ×{r["dd+mp256_expanse"]:.2f} | ×{r["dd+mp256_symmetry"]:.2f} | '
                 f'×{r["dd_expanse"]:.2f} | ×{r["mp256_expanse"]:.2f} | ×{r["exp1_expanse"]:.2f} |')
md = '\n'.join(lines) + '\n'
if a.markdown:
    a.markdown.write_text(md)
print(md); print('totals', doc['totals'])
