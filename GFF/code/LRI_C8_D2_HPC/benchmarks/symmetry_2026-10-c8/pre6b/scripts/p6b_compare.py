#!/usr/bin/env python3
"""pre-Stage-6b (symmetry, in the job): one freeze of the fixed tools/design.py (77fab71) against the older bundles of the
same target (no package import; files only).

  p6b_compare.py NEW_BUNDLE --out FILE.json [--ref NAME=BUNDLE ...]

Records the new bundle's design (predicted SE and its target, the freeze's core-hours at its own eta_node, K, r, s,
the counts' sha256, the bundle's cap record), its optimizer record (the start kept; per start: greedy and final cost
and SE, prune steps, lattice boxes and moves, caps) and, for a route-(b) bundle, route_b_choice (chosen branch, the
re-optimized and the kept-exact designs' cost, SE and feasibility). Each --ref bundle (pre6's 570241 bundle of the same
name, J-DES-5's s5des5 bundle) is recorded with the same design fields and compared: counts, r, s equal, cost and SE
ratios (new / ref)."""
import argparse, hashlib, json
from pathlib import Path


def load(b: Path) -> dict:
    d = json.loads((b / 'design.json').read_bytes()); m = json.loads((b / 'design_meta.json').read_bytes())
    pr = d['predicted']
    return {'bundle': str(b), 'design_sha256': hashlib.sha256((b / 'design.json').read_bytes()).hexdigest(),
            'design_meta_sha256': hashlib.sha256((b / 'design_meta.json').read_bytes()).hexdigest(),
            'numerics': m.get('numerics'), 'target_se': (m.get('target') or {}).get('se'), 'se_total': pr['se_total'],
            'cost_total_core_hours': pr['cost_total_core_hours'], 'eta_node': d['eta_node'], 'batches': d['batches'],
            'batches_minimum': d['batches_minimum'], 'replicates': d['replicates'], 's': {k: v['s'] for k, v in d['strata'].items()},
            'counts_sha256': m['counts_sha256'], 'caps': d['caps'], 'caps_ok': bool(d['caps'].get('ok') and d['caps'].get('task_ok')),
            'optimizer': m.get('optimizer'), 'route_b_choice': m.get('route_b_choice'),
            'profile_recost': None if not m.get('profile_recost') else
            {k: m['profile_recost'].get(k) for k in ('route', 'profile', 'cost_model', 'gates', 'exact_pilot')}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('bundle', type=Path); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--ref', action='append', default=[], help='NAME=BUNDLE')
    a = ap.parse_args()
    new = load(a.bundle); rec = {'schema': 'c8-d2-pre6b-compare-1', 'new': new, 'refs': {}}
    tgt = new['target_se']
    new['meets_target'] = new['se_total'] <= tgt * (1 + 1e-12)
    for spec in a.ref:
        name, path = spec.split('=', 1); p = Path(path)
        if not (p / 'design.json').exists():
            rec['refs'][name] = {'bundle': path, 'missing': True}; continue
        o = load(p)
        rec['refs'][name] = {'design': {k: o[k] for k in ('bundle', 'design_sha256', 'numerics', 'target_se', 'se_total', 'cost_total_core_hours', 'eta_node',
                                                          'batches', 'replicates', 's', 'caps_ok')},
                             'design_json_bytes_equal': (p / 'design.json').read_bytes() == (a.bundle / 'design.json').read_bytes(),
                             'counts_equal': o['counts_sha256'] == new['counts_sha256'], 'replicates_equal': o['replicates'] == new['replicates'],
                             's_equal': o['s'] == new['s'], 'batches_equal': o['batches'] == new['batches'],
                             'eta_node_equal': o['eta_node'] == new['eta_node'],
                             'cost_ratio_new_over_ref': new['cost_total_core_hours'] / o['cost_total_core_hours'],
                             'se_ratio_new_over_ref': new['se_total'] / o['se_total']}
    a.out.write_text(json.dumps(rec, indent=1, default=float) + '\n')
    ch = (new['route_b_choice'] or {}).get('chosen')
    print(json.dumps({'se': round(new['se_total'], 4), 'target': tgt, 'meets': new['meets_target'], 'core_h_freeze': round(new['cost_total_core_hours'], 1),
                      'K': new['batches'], 'caps_ok': new['caps_ok'], 'optimizer_kept': (new['optimizer'] or {}).get('kept'), 'route_b_chosen': ch,
                      'vs': {n: (round(r['cost_ratio_new_over_ref'], 4), r['counts_equal'], r['s_equal']) for n, r in rec['refs'].items() if not r.get('missing')}}))
    return 0 if new['meets_target'] and new['caps_ok'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
