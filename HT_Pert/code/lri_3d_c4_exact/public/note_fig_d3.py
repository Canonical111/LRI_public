#!/usr/bin/env python3
"""Figure d3:fig:c4 of the HT_Pert note: C4(L) of the d = 3 truncation in each window scheme, from C4_by_L.csv.

Schemes (README Sec. 1): raw; consistent (vacuum window D_L, the production package's scheme); + diagonal zero-mode
window; + full zero-mode window; W = + chi-attached sunset window (the complete window of d = 2). Horizontal line:
C4(3) = 1.2280635453. Needs numpy and matplotlib.

Run from code/lri_3d_c4_exact:  python3 -B public/note_fig_d3.py --out <dir>   (writes <dir>/fig_d3_c4.pdf)
"""
import argparse, csv
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
C4_EXACT = 1.22806354532762307997


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(PKG / '.work/note'))
    a = ap.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows = list(csv.DictReader(open(PKG / 'C4_by_L.csv')))
    L = [int(r['L']) for r in rows]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.6, 3.6))
    for key, label, style in (('C4_raw', 'raw', ':'), ('C4_consistent', r'vacuum window $D_L$ (package)', '--'),
                              ('C4_zm', r'+ diagonal zero-mode window', '-.'), ('C4_zmfull', r'+ full zero-mode window', '-'),
                              ('C4_W', r'complete window $W$ (+ $\chi$ sunset)', '-')):
        y = [float(r[key]) for r in rows]
        ax.plot(L, y, style, lw=2.0 if key == 'C4_W' else 1.2, label=label)
        if key in ('C4_zmfull', 'C4_W', 'C4_zm'):
            bx.loglog(L[5:], [abs(v - C4_EXACT) for v in y[5:]], style, lw=2.0 if key == 'C4_W' else 1.2,
                      color=ax.lines[-1].get_color(), label=label)
    ax.axhline(C4_EXACT, color='k', lw=0.8)
    ax.text(600, C4_EXACT + 0.06, r'$C_4(3)$', ha='right', va='bottom', fontsize=9)
    ax.set_xlim(0, 600)
    ax.set_ylim(-1.5, 1.6)
    ax.set_xlabel('level cutoff $L$')
    ax.set_ylabel('$C_4(L)$')
    ax.legend(fontsize=8, loc='lower left', frameon=False)
    ref = [0.5 * 10 / l for l in L[5:]]
    bx.loglog(L[5:], ref, color='0.6', lw=0.8)
    bx.text(200, 0.5 * 10 / 200 * 0.75, r'$\propto 1/L$', ha='center', va='top', fontsize=8, color='0.4')
    bx.set_xlabel('level cutoff $L$')
    bx.set_ylabel(r'$|C_4(L)-C_4(3)|$')
    bx.legend(fontsize=8, loc='lower left', frameon=False)
    fig.tight_layout()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / 'fig_d3_c4.pdf', metadata={'CreationDate': None, 'Creator': None, 'Producer': None})
    print(f'wrote {out / "fig_d3_c4.pdf"}')


if __name__ == '__main__':
    main()
