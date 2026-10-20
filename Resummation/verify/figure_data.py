#!/usr/bin/env python3
"""The data behind the two comparison figures of the paper, as CSV (new tool, 2026-10-14). Run from Resummation/.

fig:cmp1d = results/figures/01_methods_clean.pdf (code/resum_d1/plot_lri_comparisons.wl) and fig:cmp2d3d =
results/figures/06_curves_2d3d_clean.pdf (code/resum_d23/plot_lri_2d3d.wl) are drawn by Wolfram Language scripts.
This tool writes, from exactly the files those scripts read, the plotted curves and points:
  results/figures/fig_cmp1d_curves.csv    Delta_sigma, CB8 K=8 baseline (purple), GFF-only CB8 and CB3 (blue)
  results/figures/fig_cmp1d_points.csv    the 48 displayed reference points: value and bars (left panel), residual
                                          10^3 (y - CB8) (right panel, Delta_sigma >= 0.02; frame -25..20), marker, fill
  results/figures/fig_cmp2d3d_curves.csv  d, Delta_sigma, baseline CB8 (2d curvature, 3d slope), GFF-only CB8 and CB3
  results/figures/fig_cmp2d3d_points.csv  HT at finite cutoff, published MC (true and displayed Delta_sigma), the new 3d
                                          MC point, the short-range Ising points (stars)
Fill and marker rules are those of the scripts (see the caption of each figure). With --check (the default) the four
files are regenerated in memory and must equal the shipped ones byte for byte; --write rewrites them.
Usage: python3 verify/figure_data.py [--check | --write]
"""
import argparse, csv, io, json, sys
from pathlib import Path

RS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RS/'verify'))
import rsum_lib as L

D1 = RS/'code'/'resum_d1'
D23 = RS/'code'/'resum_d23'
OUT = RS/'results'/'figures'
FRAME_RIGHT = (-25.0, 20.0)


def text(rows):
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
    return s.getvalue()


def fig1d():
    P = json.loads((D1/'update_2026-10-13'/'C8_1_ext'/'pipeline_K8'/'plot_data_1d_K8.json').read_text())
    curves = [{'Delta_sigma': repr(c['x']), 'CB8_K8_baseline': repr(c['CB8_K8']), 'GFF_only_CB8': repr(c['direct_CB8']),
               'GFF_only_CB3': repr(c['direct_CB3'])} for c in P['curve']]
    pts = []
    for r in P['references']:
        if not r['displayed']:
            continue
        m, st = r['method'], r['status']
        x = float(r['x'])
        filled = {'HT': st in ('final', 'one_sided'), 'NRG': st not in ('flagged', 'not_converged'),
                  'MC': st.startswith('ACCEPTED')}.get(m, False)
        marker = {'HT': 'square', 'NRG': 'circle', 'MC': 'diamond'}.get(m) or (
            'inverted triangle' if r['source'].startswith('Uzelac') else 'triangle')
        e = max(float(r['error'] or 0), float(r['stat'] or 0))
        extra = 5e-4 if st == 'one_sided' else 0.0
        res = 1000*r['method_minus_K8']
        right = x >= 0.02
        cut = right and (res - 1000*(e + extra) < FRAME_RIGHT[0] or res + 1000*e > FRAME_RIGHT[1])
        pts.append({'method': m, 'source': r['source'], 'Delta_sigma': r['x'], 'value': r['y'], 'bar_outer': r['error'],
                    'bar_inner': r['stat'], 'one_sided_extra': repr(extra) if extra else '', 'status': st, 'marker': marker,
                    'filled': 'yes' if filled else 'no', 'residual_1e3': repr(res), 'right_panel': 'yes' if right else 'no',
                    'right_bar_cut_at_frame': 'yes' if cut else 'no'})
    return curves, pts


def fig2d3d():
    curves, pts = [], []
    cb3 = [r for r in csv.DictReader((D23/'combined'/'cb3_gff_only.csv').open())]
    for d, base in ((2, 'curvature_CB8'), (3, 'slope_CB8')):
        P = json.loads((D23/('%dd' % d)/'inputs'/'plot_data.json').read_text())
        c3 = [r for r in cb3 if r['d'] == str(d)]
        assert len(c3) == len(P['curves'])
        for c, b in zip(P['curves'], c3):
            assert abs(float(b['Delta_sigma']) - c['Delta_sigma']) < 1e-12
            curves.append({'d': d, 'Delta_sigma': repr(c['Delta_sigma']), 'baseline_CB8': repr(c[base]),
                           'GFF_only_CB8': repr(c['direct_CB8']), 'GFF_only_CB3': b['CB3_direct']})
        if d == 2:
            for h in P['ht_latest']:
                pts.append({'d': 2, 'kind': 'HT finite cutoff', 'key': 'N=%d' % h['L'], 'Delta_sigma': repr(h['x']),
                            'plot_Delta_sigma': repr(h['x']), 'value': repr(h['Delta_thermal']), 'error': '', 'stat': '',
                            'filled': 'yes' if h['L'] == 24 else 'no'})
        else:
            for h in P['ht_l20']:
                pts.append({'d': 3, 'kind': 'HT finite cutoff', 'key': 'N=20', 'Delta_sigma': repr(h['Delta_sigma']),
                            'plot_Delta_sigma': repr(h['Delta_sigma']), 'value': repr(h['HT_L20']), 'error': '', 'stat': '',
                            'filled': 'yes'})
    for r in csv.DictReader((D23/'combined'/'literature_mc_2d3d.csv').open()):
        if r['plotted'] != 'yes':
            continue
        pts.append({'d': int(r['dimension']), 'kind': 'published MC', 'key': r['source_key'], 'Delta_sigma': r['Delta_sigma'],
                    'plot_Delta_sigma': r['plot_Delta_sigma'], 'value': r['Delta_epsilon'], 'error': r['Delta_epsilon_err'],
                    'stat': '', 'filled': 'yes' if r['source_key'] == 'luijten1997_Q' else 'no'})
    for m in json.loads((D23/'3d'/'inputs'/'mc_accepted.json').read_text()):
        pts.append({'d': 3, 'kind': 'MC (this work; accepted under P1)', 'key': 's=%s' % m['s'], 'Delta_sigma': repr(m['Delta_sigma']),
                    'plot_Delta_sigma': repr(m['Delta_sigma']), 'value': repr(m['Delta_epsilon']), 'error': repr(m['sigma_sys']),
                    'stat': repr(m['sigma_stat']), 'filled': 'yes'})
    pr = json.loads((D23/'3d'/'inputs'/'protocol.json').read_text())
    pts.append({'d': 2, 'kind': 'short-range Ising point', 'key': 'exact', 'Delta_sigma': '0.125', 'plot_Delta_sigma': '0.125',
                'value': '1', 'error': '', 'stat': '', 'filled': 'yes'})
    pts.append({'d': 3, 'kind': 'short-range Ising point', 'key': 'bootstrap', 'Delta_sigma': pr['S'], 'plot_Delta_sigma': pr['S'],
                'value': pr['E_SR'], 'error': '', 'stat': '', 'filled': 'yes'})
    return curves, pts


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--write', action='store_true')
    g.add_argument('--check', action='store_true')
    a = ap.parse_args()
    c1, p1 = fig1d()
    c2, p2 = fig2d3d()
    files = {'fig_cmp1d_curves.csv': c1, 'fig_cmp1d_points.csv': p1, 'fig_cmp2d3d_curves.csv': c2, 'fig_cmp2d3d_points.csv': p2}
    T = L.Table('figure data')
    for name, rows in files.items():
        t = text(rows)
        if a.write:
            OUT.mkdir(parents=True, exist_ok=True); (OUT/name).write_text(t)
        ok = (OUT/name).exists() and (OUT/name).read_text() == t
        T.check('results/figures/' + name, ok, '%d rows' % len(rows), 'identical to the shipped file', 'regenerated from the figure inputs')
    T.check('1d displayed points', len(p1) == 48, '%d' % len(p1), '48', 'HT at Delta_sigma = 0.001 not displayed')
    cut = [p for p in p1 if p['right_bar_cut_at_frame'] == 'yes']
    T.check('1d right panel: cut bars', sorted((p['source'][:6], p['Delta_sigma']) for p in cut) ==
            [('Angeli', '0.1727335'), ('Uzelac', '0.05'), ('Uzelac', '0.2')], ', '.join('%s %s' % (p['source'][:6], p['Delta_sigma']) for p in cut),
            'Uzelac 0.05, 0.2; Angelini 0.1727335', 'caption: three published-MC bars cut at the frame -25..20; all other bars inside')
    T.check('2d/3d points', sum(p['kind'] == 'published MC' for p in p2) == 14 and sum(p['kind'] == 'HT finite cutoff' for p in p2) == 28,
            '%d published MC, %d HT' % (sum(p['kind'] == 'published MC' for p in p2), sum(p['kind'] == 'HT finite cutoff' for p in p2)),
            '14 published MC (12 in 2d, 2 in 3d), 28 HT (13 + 15)', 'counts asserted by the figure script')
    return T.report(RS/'.work'/'figure_data.txt')


if __name__ == '__main__':
    sys.exit(main())
