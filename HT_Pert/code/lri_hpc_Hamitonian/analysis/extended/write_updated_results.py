#!/usr/bin/env python3
"""Write analysis/UPDATED_RESULTS.md from the current snapshot (PLAN G6; review IR-005).

Inputs: analysis/extended/extended_summary.json (run_extended.py), analysis/diagnosis_extended.json
(diagnose_systematic.py with the new rows) and, if present, the campaign plan snapshot
results/expanse/campaign/plan.json (fetch_results.sh) to separate completed cutoffs from pending targets.
All ranges are model spreads, not confidence intervals. Exact C4, C5 and diagrammatic C6, C7 are comparisons only.
The automatic criteria use the thresholds below; the interpretation is in analysis/DIAGNOSIS.md.
"""
import json, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
EXACT = {4: 45.42488010356, 5: -731.13947662454}
DIAG = {6: (14331.8, 0.5), 7: (-322550.0, 41.0)}
# Criteria (PLAN G3 / review LRI-007), set when this generator was written on 2026-09-29, after only the first new
# thermal cutoff (L = 84) had been seen and before any extended summary was computed:
STABLE = {4: 2e-4, 5: 5e-4}       # |C_k(hi=max) - C_k(hi=50)| / |C_k|, every reference basis
HELDOUT = 1e-3                    # max |frozen prediction error| / |C_k(L) - C_k(inf)| over the new cutoffs, k = 4..7


def main():
    ex = json.loads((HERE / 'extended_summary.json').read_text())
    dg = json.loads((ROOT / 'analysis' / 'diagnosis_extended.json').read_text())
    plan_f = ROOT / 'results' / 'expanse' / 'campaign' / 'plan.json'
    plan = json.loads(plan_f.read_text()) if plan_f.exists() else None
    d = ex['data']
    L = []
    w = L.append
    w('# Updated results with the extended cutoffs (PLAN G6)\n')
    w(f"Snapshot generated {time.strftime('%Y-%m-%d %H:%M %Z')} from `analysis/extended/extended_summary.json` and "
      '`analysis/diagnosis_extended.json`. The campaign may still be running, so these numbers are for the cutoffs '
      'completed at the snapshot. Ranges are model spreads, not confidence intervals. The exact C4 and C5 and the '
      'diagrammatic C6 and C7 are after-the-fact comparisons only.\n')
    w('## 1. Data in this snapshot\n')
    done = {'thermal_d7': d['thermal_new'], 'phi6_d5': d['gap5_new'], 'phi6_d3': d['gap3_new']}
    w('| task | new cutoffs completed | largest | planned, not run | memory-rejected |')
    w('|---|---|---|---|---|')
    for task in ('thermal_d7', 'phi6_d5', 'phi6_d3'):
        t, deg = task.split('_d')
        new = sorted(done[task])
        if plan:
            planned = sorted(it['cutoff'] for it in plan['items'] if (it['task'], it['degree']) == (t, int(deg)))
            pend = [x for x in planned if x not in new]
            rej = sorted(r['cutoff'] for r in plan['rejected'] if (r['task'], r['degree']) == (t, int(deg)))
            pend_s = f"{len(pend)}: {pend[:6]}{' …' if len(pend) > 6 else ''}"
            rej_s = f'≥ {rej[0]}' if rej else '–'
        else:
            pend_s = rej_s = 'plan snapshot not available'
        w(f"| {task} | {len(new)} | {max(new) if new else '–'} | {pend_s} | {rej_s} |")
    w(f"\nOverlapping cutoffs checked against saved rows (kept): {ex['overlap_checked']}. New-row solver source: "
      f"{sorted({s for v in ex['new_row_sources'].values() for s in v})}.\n")

    w('## 2. Gap inputs\n')
    w('| cubic-gap window hi | points | ω3 |')
    w('|---|---|---|')
    for h, v in ex['omega3_vs_hi'].items():
        w(f"| {h} | {v['points']} | {v['omega3']:.6f} |")
    w('\n| fifth-order window hi | points | ω4 | ω5 |')
    w('|---|---|---|---|')
    for h, v in ex['omega45_vs_hi'].items():
        w(f"| {h} | {v['points']} | {v['omega']['4']:.4f} | {v['omega']['5']:.2f} |")

    w('\n## 3. Thermal intercepts versus the thermal window (lo = 16, shift 0)\n')
    w('| gap input | basis | hi | points | C4 (rel. to exact) | C5 (rel. to exact) | C6 (σ to diagrammatic) | C7 (σ to diagrammatic) | max cond |')
    w('|---|---|---|---|---|---|---|---|---|')
    for r in ex['thermal_vs_hi']:
        w(f"| {r['gap']} | {r['model']} | {r['hi']} | {r['points']} | {r['C4']:.6f} ({r['C4'] / EXACT[4] - 1:+.2e}) | "
          f"{r['C5']:.4f} ({r['C5'] / EXACT[5] - 1:+.2e}) | {r['C6']:.2f} ({(r['C6'] - DIAG[6][0]) / DIAG[6][1]:+.0f}) | "
          f"{r['C7']:.1f} ({(r['C7'] - DIAG[7][0]) / DIAG[7][1]:+.1f}) | {r['cond']:.1e} |")
    w('\nModel spreads at the extended window (all bases, lo ∈ {12, 16, 20, 24}, shift ∈ {−2, 0, 2}, extended gap input):\n')
    w('| set | C4 | C5 | C6 | C7 |')
    w('|---|---|---|---|---|')
    for label, rg in ex['ranges_extended'].items():
        w(f"| {label} | " + ' | '.join(f"{rg[str(k)][0]:.4f} … {rg[str(k)][1]:.4f}" if k < 6 else f"{rg[str(k)][0]:.1f} … {rg[str(k)][1]:.1f}"
                                     for k in range(4, 8)) + ' |')

    w('\n## 4. Held-out test: frozen Λ ≤ 50 reference models predicting the new thermal cutoffs\n')
    held = {}
    if d['thermal_new']:
        w('| basis | max abs error C4 | C5 | C6 | C7 | max error / distance to the limit |')
        w('|---|---|---|---|---|---|')
        for name, rec in ex['frozen_original_reference'].items():
            mx = {k: max(abs(h[f'C{k}']['err']) for h in rec['heldout']) for k in range(4, 8)}
            rel = max(abs(h[f'C{k}']['err_over_distance']) for h in rec['heldout'] for k in range(4, 8))
            held[name] = rel
            w(f"| {name} | {mx[4]:.2e} | {mx[5]:.2e} | {mx[6]:.2e} | {mx[7]:.2e} | {rel:.1e} |")
    else:
        w('No new thermal cutoffs in this snapshot.')

    w('\n## 5. Diagnosis update (diagnose_systematic.py with the new rows)\n')
    Lmax = dg['data']['thermal_max']
    w(f'Thermal data to Λ = {Lmax}.\n')
    w('Calibration check (labelled; exact C4 and C5 imposed), max residual free → imposed:\n')
    w('| basis | hi | C4 order | C5 order | C6, C7 with exact C4, C5 imposed |')
    w('|---|---|---|---|---|')
    for c in dg['calibration_check']:
        w(f"| {c['model']} | {c['hi']} | {c['max_residual_free']['4']:.2e} → {c['max_residual_exact_imposed']['4']:.2e} | "
          f"{c['max_residual_free']['5']:.2e} → {c['max_residual_exact_imposed']['5']:.2e} | "
          f"{c['C6_C7_with_exact_C4_C5_imposed']['6']:.1f}, {c['C6_C7_with_exact_C4_C5_imposed']['7']:.0f} |")
    rr = [r for r in dg['residual_ratio'] if r['L'] >= 42 and (r['L'] % 8 == 2 or r['L'] == Lmax)]
    w('\nResidual ratios R4, R5 (exact limits; see DIAGNOSIS.md §6):\n')
    w('| Λ | ' + ' | '.join(str(r['L']) for r in rr) + ' |')
    w('|---|' + '---|' * len(rr))
    w('| R4 | ' + ' | '.join(f"{r['R4']:.3f}" for r in rr) + ' |')
    w('| R5 | ' + ' | '.join(f"{r['R5']:.1f}" for r in rr) + ' |')
    d3 = [r for r in dg['D3'] if r.get('hi') == Lmax and 'C4' in r]
    if d3:
        spread4 = max(r['rel4'] for r in d3) - min(r['rel4'] for r in d3)
        spread5 = max(r['rel5'] for r in d3) - min(r['rel5'] for r in d3)
        w(f'\nTail-structure variants at hi = {Lmax} (D3): relative C4 from {min(r["rel4"] for r in d3):+.2e} to '
          f'{max(r["rel4"] for r in d3):+.2e}; C5 from {min(r["rel5"] for r in d3):+.2e} to {max(r["rel5"] for r in d3):+.2e}.\n')

    w('## 6. Automatic criteria\n')
    w('Thresholds were set when the generator was written, after only the first new thermal cutoff (Λ = 84) had been '
      'seen and before any extended summary existed.\n')
    tv = {(r['gap'], r['model'], r['hi']): r for r in ex['thermal_vs_hi']}
    his = sorted({r['hi'] for r in ex['thermal_vs_hi']})
    if his[-1] > 50:
        drift = {m: {k: abs(tv[('extended', m, his[-1])][f'C{k}'] / tv[('extended', m, 50)][f'C{k}'] - 1) for k in (4, 5)}
                 for m in ('A', 'B', 'C')}
        stable = all(drift[m][k] < STABLE[k] for m in drift for k in (4, 5))
        w(f'- Window stability (|ΔC4|/C4 < {STABLE[4]:g}, |ΔC5|/C5 < {STABLE[5]:g} from hi = 50 to {his[-1]}): '
          f"{'yes' if stable else 'no'}; drifts {json.dumps({m: {k: float(f'{v:.2e}') for k, v in dd.items()} for m, dd in drift.items()})}.")
    else:
        w('- Window stability: no new thermal data.')
    if held:
        ok = all(v < HELDOUT for v in held.values())
        w(f"- Held-out prediction (max error / distance < {HELDOUT:g}): {'yes' if ok else 'no'}; {json.dumps({k: float(f'{v:.1e}') for k, v in held.items()})}.")
    if d3:   # both C4 and C5 must be tail-insensitive (review IR2-001)
        off = {k: min(abs(tv[('extended', m, his[-1])][f'C{k}'] / EXACT[k] - 1) for m in ('A', 'B', 'C')) for k in (4, 5)}
        spr = {4: spread4, 5: spread5}
        ins = {k: spr[k] < off[k] / 3 for k in (4, 5)}
        for k in (4, 5):
            w(f"- Tail insensitivity of C{k} (D3 spread < one third of the smallest |offset|): {'yes' if ins[k] else 'no'}; "
              f'spread {spr[k]:.2e}, offset {off[k]:.2e}.')
        w(f"- Tail insensitivity overall (C4 and C5): {'yes' if all(ins.values()) else 'no'}.")
    w('\nA matching offset is claimed only if all three hold (PLAN G3). See DIAGNOSIS.md for the interpretation.')
    (ROOT / 'analysis' / 'UPDATED_RESULTS.md').write_text('\n'.join(L) + '\n')
    print('wrote analysis/UPDATED_RESULTS.md')


if __name__ == '__main__':
    main()
