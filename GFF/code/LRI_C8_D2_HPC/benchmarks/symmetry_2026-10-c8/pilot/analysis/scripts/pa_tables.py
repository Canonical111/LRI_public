#!/usr/bin/env python3
"""The post-pilot cost table (Mac, seconds) from the committed evidence of jobs 570669 (pa.slurm) and 570672 (pa2.slurm).

  pa_tables.py [--analysis DIR] [--out cost_table.json] [--markdown cost_table.md]

Inputs, all under DIR (default: this script's parent folder): pa.570669.0/design_<N>.json, design_meta_<N>.json,
accounting.json, pa_analysis.json, report_exact.json.gz; pa2.570672.0/pa_tails.json; the stand-in tables
../../pre6b/p6b_tables.json (J-DES-5's strata through the Stage-6 design.py, lane core-hours at J-SMK-4's eta_node 0.9146).
N = pilot1-20261006-<exact|ddmp256>-<target>.

Columns: core-hours are the freeze's own (lane core-hours at the pilot's measured eta_node, design.py); the walls are
pa_analysis.py's lane schedules on 4 / 8 / 16 amdq nodes of 8 x 8 lanes ("steady": the pilot's in-index efficiency
and the schedule's own tail; "design": the pilot's eta_node, pessimistic); Expanse SU = core-hours x the bundle's
Expanse/symmetry exact cost-model ratio (same eta_node assumed; exact path only)."""
from __future__ import annotations
import argparse, json
from pathlib import Path

TARGETS = ['1e-3', '5e-4', '2.5e-4', '1.35e-4']
C8_PILOT = 45620.18147564831


def main() -> int:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--analysis', type=Path, default=here); ap.add_argument('--out', type=Path, default=here / 'cost_table.json')
    ap.add_argument('--markdown', type=Path, default=here / 'cost_table.md'); a = ap.parse_args()
    E = a.analysis / 'pa.570669.0'; E2 = a.analysis / 'pa2.570672.0'
    pa = json.loads((E / 'pa_analysis.json').read_bytes()); acc = json.loads((E / 'accounting.json').read_bytes())
    tails = json.loads((E2 / 'pa_tails.json').read_bytes())
    p6b = json.loads((a.analysis / '../../pre6b/p6b_tables.json').resolve().read_bytes())['targets']
    rows = []
    for R, key in (('exact', 'x'), ('ddmp256', 'b')):
        for T in TARGETS:
            N = f'pilot1-20261006-{R}-{T}'
            d = json.loads((E / f'design_{N}.json').read_bytes()); m = json.loads((E / f'design_meta_{N}.json').read_bytes()); b = pa['bundles'][N]
            ch = d['predicted']['cost_total_core_hours']; se = d['predicted']['se_total']; st = p6b[T][key]['core_hours_lane']
            rows.append(dict(route=R, target_rel=float(T), bundle=N, design_meta_sha256=b['design_meta_sha256'], target_se=m['target']['se'], predicted_se=se,
                             predicted_se_raw=d['predicted']['se_raw_total'], relative_se=se / m['target']['c8_magnitude'], relative_se_measured_c8=se / C8_PILOT,
                             core_hours=ch, batches=d['batches'], batches_minimum=d['batches_minimum'], replicates=d['replicates'],
                             s={k: v['s'] for k, v in d['strata'].items()}, points=b['points'], indices=b['indices'],
                             tasks=sum(d['caps']['tasks_per_campaign'].values()), checkpoints=d['caps']['checkpoints'],
                             walls={N_: dict(steady_h=w['wall_h_steady'], design_h=w['wall_h_design_eta'], allocated_core_hours_steady=w['allocated_core_hours_steady'])
                                    for N_, w in b['walls'].items()},
                             expanse_ratio=b['expanse_over_symmetry_cost_model'], expanse_su=(ch * b['expanse_over_symmetry_cost_model'] if R == 'exact' else None),
                             route_b_choice=b['route_b_choice'], standin_core_hours=st, ratio_to_standin=ch / st,
                             confirm_points=tails['bundles'][N]))
    m0 = json.loads((E / f'design_meta_{rows[0]["bundle"]}.json').read_bytes())
    rec = {'schema': 'c8-d2-pilot-cost-table-1', 'rule': __doc__, 'eta_node': acc['eta_node'], 'spent_core_hours': m0['spent_core_hours'], 'total_cap': m0['total_cap'], 'rows': rows,
           'standin_factors': pa['standin']['factors'], 'standin_jensen': pa['standin']['jensen'], 'standin_bounds': pa['standin']['targets']}
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    f = lambda x: f'{x:,.0f}'
    L = ['| Route | Target (SE) | Predicted SE (rel. to 4.6e4; to the pilot\'s 45,620) | Lane core-h (eta_node %.3f) | K | Replicates r (free L8, power L8; others) | Points | Indices | Tasks | Wall 4 / 8 / 16 nodes, h (steady; design-eta) | Expanse SU (x ratio) | Stand-in core-h (ratio) |' % acc['eta_node'],
         '|---|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|']
    for r in rows:
        rr = r['replicates']; oth = sorted({v for k, v in rr.items() if k not in ('free_L8', 'power_L8')})
        w = r['walls']
        L.append(f'| {"exact" if r["route"] == "exact" else "dd+mp256 (b: " + ("kept exact allocation" if r["route_b_choice"] == "kept_exact_allocation" else "re-optimized") + ")"} '
                 f'| {r["target_rel"]:g} ({r["target_se"]:.2f}) | {r["predicted_se"]:.2f} ({r["relative_se"]:.3g}; {r["relative_se_measured_c8"]:.3g}) | **{f(r["core_hours"])}** | {r["batches"]} '
                 f'| {rr["free_L8"]}, {rr["power_L8"]}; {"/".join(map(str, oth))} | {r["points"]:.3g} | {f(r["indices"])} | {r["tasks"]:.3g} '
                 f'| {w["4"]["steady_h"]:.1f} / {w["8"]["steady_h"]:.1f} / {w["16"]["steady_h"]:.1f} ({w["4"]["design_h"]:.1f} / {w["8"]["design_h"]:.1f} / {w["16"]["design_h"]:.1f}) '
                 f'| {f(r["expanse_su"]) + " (x%.3f)" % r["expanse_ratio"] if r["expanse_su"] else "n/a (gated on symmetry only)"} | {f(r["standin_core_hours"])} (x{r["ratio_to_standin"]:.2f}) |')
    a.markdown.write_text('\n'.join(L) + '\n')
    print('\n'.join(L)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
