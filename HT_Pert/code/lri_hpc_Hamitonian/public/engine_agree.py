#!/usr/bin/env python3
"""Agreement of the d = 1 vacuum-window engines through eps^5 (HT_Pert/code/lri_hpc_Hamitonian), from shipped records.

(i)   Engine B, full-basis Rayleigh-Schroedinger difference of two complete spectra (analysis/eps5_window/B/
      full5_c<4 Lambda>.json, variants raw and Dconn) against engine B's pipeline of capped row responses and
      closed-form top sums (analysis/eps5_window/B/dC5_table.json, dC5_Dconn): max |Delta C5 difference| over the
      integer cutoffs Lambda <= 60 that both hold (Lambda = 64 is reported separately; the statement in the analysis
      covers Lambda <= 60).
(iii) The independent from-scratch engine analysis/eps5_window/challenge-num/ht5.py (its outputs ht5_out_2_4.json,
      ht5_out_6_8_10_12_14_16.json, big_18_20_22_24_26_28.json; variants raw and Dconn) against the reconciled table
      analysis/eps5_window/reconcile/dC_reconciled.json (dC5_Dconn, dC4_Dconn) at Lambda = 2..28.
(ii)  engine A against engine B on 3808 numbers is the shipped analysis/eps5_window/reconcile/cmp_ident.py; the replay
      runs it on the re-pointed copy.
The analysis printed (i) and (iii) only into a workflow summary that is not shipped; this script recomputes them.
Reads the shipped files only (no re-pointing needed). Writes JSON to --out and prints a summary.
usage: python3 public/engine_agree.py [--pkg .] [--out .work/engine_agree.json]"""
import argparse
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pkg', default=PKG)
    ap.add_argument('--out', default=os.path.join(PKG, '.work', 'engine_agree.json'))
    a = ap.parse_args()
    E5 = os.path.join(a.pkg, 'analysis', 'eps5_window')
    table = {r['L']: r for r in json.load(open(os.path.join(E5, 'B', 'dC5_table.json')))}
    rows_i = []
    for f in sorted(glob.glob(os.path.join(E5, 'B', 'full5_c*.json'))):
        o = json.load(open(f))
        lam = o['Lambda']
        if lam != int(lam) or int(lam) not in table:
            continue
        v = o['variants']
        d5 = v['Dconn']['C'][5] - v['raw']['C'][5]
        rows_i.append(dict(L=int(lam), file=os.path.basename(f), full_basis=d5, pipeline=table[int(lam)]['dC5_Dconn'],
                           absdiff=abs(d5 - table[int(lam)]['dC5_Dconn'])))
    rows_i.sort(key=lambda r: r['L'])
    w60 = max((r for r in rows_i if r['L'] <= 60), key=lambda r: r['absdiff'])
    rest = [r for r in rows_i if r['L'] > 60]
    rec = {int(k): v for k, v in json.load(open(os.path.join(E5, 'reconcile', 'dC_reconciled.json'))).items()}
    rows_iii = []
    for name in ('ht5_out_2_4.json', 'ht5_out_6_8_10_12_14_16.json', 'big_18_20_22_24_26_28.json'):
        for k, v in json.load(open(os.path.join(E5, 'challenge-num', name))).items():
            d5 = v['Dconn']['C'][5] - v['raw']['C'][5]
            d4 = v['Dconn']['C'][4] - v['raw']['C'][4]
            rows_iii.append(dict(L=int(k), file=name, dC5=d5, dC4=d4, absdiff5=abs(d5 - rec[int(k)]['dC5_Dconn']),
                                 absdiff4=abs(d4 - rec[int(k)]['dC4_Dconn'])))
    rows_iii.sort(key=lambda r: r['L'])
    w3 = max(rows_iii, key=lambda r: r['absdiff5'])
    out = dict(about=__doc__.split('\n')[0],
               i=dict(what='engine B full-basis Delta C5 vs engine B pipeline (dC5_table), integer Lambda <= 60',
                      n=len([r for r in rows_i if r['L'] <= 60]), max_absdiff=w60['absdiff'], at_L=w60['L'],
                      beyond_60={r['L']: r['absdiff'] for r in rest}, rows=rows_i),
               iii=dict(what='independent engine ht5.py Delta C5 vs reconciled dC5_Dconn, Lambda 2..28',
                        n=len(rows_iii), max_absdiff=w3['absdiff5'], at_L=w3['L'],
                        max_absdiff_dC4=max(r['absdiff4'] for r in rows_iii), rows=rows_iii))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    print(f"(i)   engine B full basis vs pipeline: {out['i']['n']} cutoffs Lambda <= 60, max |d dC5| "
          f"{w60['absdiff']:.2e} at Lambda {w60['L']}; Lambda > 60: " +
          ', '.join(f"{L}: {d:.1e}" for L, d in out['i']['beyond_60'].items()))
    print(f"(iii) ht5.py vs dC_reconciled: {len(rows_iii)} cutoffs Lambda 2..28, max |d dC5| {w3['absdiff5']:.2e} at "
          f"Lambda {w3['L']}; max |d dC4| {out['iii']['max_absdiff_dC4']:.1e}")


if __name__ == '__main__':
    main()
