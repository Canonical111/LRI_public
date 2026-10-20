"""Common data loading for the delta (window-shift) model. Read-only on repositories."""
import json, csv, os
import numpy as np

DATA_JSON = '<PROJECT>/lri_ht_c8_symmetry/results/2026-10_symmetry/extrapolation/data.json'
RECON_CSV = '<PROJECT>/lri_hpc_Hamitonian/analysis/eps5_window/reconcile/dC_reconciled.csv'
RECON_JSON = '<PROJECT>/lri_hpc_Hamitonian/analysis/eps5_window/reconcile/dC_reconciled.json'
S10_CSV = '<PROJECT>/lri_1d_coefficient_flow_review/lri_d1_full_coefficient_flow/results/whole_model_coefficients.csv'
D5_JSON = '<PROJECT>/lri_hpc_Hamitonian/analysis/eh_review/physics-impact/d5_all.json'
D7_JSON = '<PROJECT>/lri_hpc_Hamitonian/analysis/eh_review/physics-impact/d7_all.json'


def load_ht():
    d = json.load(open(DATA_JSON))
    out = {}
    for key in ('raw', 'vacuum_only', 'thermal_d7'):
        out[key] = {int(L): np.array(v, dtype=float) for L, v in d[key].items()}
    out['known'] = d['known']
    return out


def load_recon():
    """Exact complete Dconn shifts dC4, dC5 (every even L<=128, 136,144,152), full float precision from
    dC_reconciled.json (the CSV has the same numbers rounded to 13 decimals)."""
    d = json.load(open(RECON_JSON))
    dc = {}
    for Ls, r in d.items():
        L = int(Ls)
        dc[L] = {4: float(r['dC4_Dconn']), 5: float(r['dC5_Dconn']),
                 'g2D4': float(r['dC4_g2D']), 'g2D5': float(r['dC5_g2D']), 'source': r.get('source', '')}
    return dc


def load_s10(extra_csv=None):
    """Exact complete Dconn shifts dC4..dC8 from the S10 archive (L=2..44), optionally
    extended/overridden by an extra CSV with the same columns (Lambda, scheme=dconn,
    dconn_minus_raw_C4..C8) or the simple columns (L, dC4..dC8)."""
    dc = {}
    for r in csv.DictReader(open(S10_CSV)):
        if r['scheme'] != 'dconn':
            continue
        L = int(r['Lambda'])
        dc[L] = {k: float(r['dconn_minus_raw_C%d' % k]) for k in range(4, 9)}
        dc[L]['C'] = np.array([float(r['C%d' % k]) for k in range(9)])
    if extra_csv:
        for r in csv.DictReader(open(extra_csv)):
            if 'scheme' in r and r['scheme'] and r['scheme'] != 'dconn':
                continue
            L = int(float(r.get('Lambda') or r.get('L')))
            ent = {}
            for k in range(4, 9):
                for col in ('dconn_minus_raw_C%d' % k, 'dC%d' % k):
                    if col in r and r[col] not in (None, ''):
                        ent[k] = float(r[col])
                        break
            dc.setdefault(L, {}).update(ent)
            dc[L]['extra'] = True
    return dc


def load_g2d():
    """Isolated g^2 D shifts. k=4,5 at every even L 4..118 (d5_all); k=4..7 at every even L 4..90
    (d7_all); k=4..8 from vacuum_only - raw (L=4,8,..,48,50..92)."""
    ht = load_ht()
    g = {k: {} for k in range(4, 9)}
    d5 = json.load(open(D5_JSON))
    for L, v in d5.items():
        for k in (4, 5):
            g[k][int(L)] = v['delta_C'][k]
    d7 = json.load(open(D7_JSON))
    for L, v in d7.items():
        for k in (4, 5, 6, 7):
            g[k].setdefault(int(L), v['delta_C'][k])
    for L, v in ht['vacuum_only'].items():
        r = ht['raw'][L]
        for k in range(4, 9):
            g[k].setdefault(L, v[k] - r[k])
    return g
