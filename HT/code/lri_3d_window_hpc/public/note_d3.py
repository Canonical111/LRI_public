#!/usr/bin/env python3
"""The HT note's d = 3 table and figure, from results/HT_3d/finite_L_table.csv.

  python3 public/note_d3.py --table tab_d3_finiteN.tex --figure fig_d3_steps.pdf

Table: Delta_E at N = 14, 16, 18, 20, the last step d20 = Delta_E(20) - Delta_E(18) and the ratio d20/d18, for the 15 Ds.
Figure: |d_N| = |Delta_E(N) - Delta_E(N-2)| against N for every Ds (log scale), filled where d_N > 0.
Needs matplotlib for the figure only.
"""
import argparse, csv
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]

def load(path):
    D = {}
    for row in csv.DictReader(open(path)):
        D[float(row['Delta_sigma']), int(row['L'])] = float(row['Delta_E'])
    return D

def table(D):
    xs = sorted({x for x, _ in D}, reverse=True)
    out = [r'\begin{tabular}{@{}l llll r r@{}}', r'\toprule',
           r'$\Delta_\sigma$ & $N=14$ & $N=16$ & $N=18$ & $N=20$ & $d_{20}$ & $d_{20}/d_{18}$\\', r'\midrule']
    for x in xs:
        d20 = D[x, 20] - D[x, 18]; d18 = D[x, 18] - D[x, 16]
        e = f'{d20:.1e}'; m, p = e.split('e'); p = int(p)
        step = rf'${m}\times10^{{{p}}}$' if not m.startswith('-') else rf'$-{m[1:]}\times10^{{{p}}}$'
        out.append(f'{x:g} & ' + ' & '.join(f'{D[x, L]:.8f}' for L in (14, 16, 18, 20)) + f' & {step} & {d20 / d18:.2f}\\\\')
    out += [r'\bottomrule', r'\end{tabular}']
    return '\n'.join(out) + '\n'

def figure(D, path):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    xs = sorted({x for x, _ in D}, reverse=True)
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    cmap = plt.get_cmap('viridis')
    for i, x in enumerate(xs):
        Ns = [N for N in range(10, 21, 2)]
        d = [D[x, N] - D[x, N - 2] for N in Ns]
        c = cmap(i / (len(xs) - 1))
        ax.plot(Ns, [abs(v) for v in d], '-', color=c, lw=1, label=f'{x:g}')
        ax.plot([N for N, v in zip(Ns, d) if v > 0], [v for v in d if v > 0], 'o', color=c, ms=3.5)
        ax.plot([N for N, v in zip(Ns, d) if v < 0], [-v for v in d if v < 0], 'o', mfc='none', color=c, ms=3.5)
    ax.set_yscale('log'); ax.set_xlabel(r'bath cutoff $N$'); ax.set_ylabel(r'$|\Delta_\varepsilon(N)-\Delta_\varepsilon(N-2)|$')
    ax.legend(title=r'$\Delta_\sigma$', fontsize=6, title_fontsize=7, ncol=1, loc='upper left', bbox_to_anchor=(1.01, 1.0), frameon=False)
    fig.tight_layout(); fig.savefig(path)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--csv', default=str(PKG / '../../results/HT_3d/finite_L_table.csv'))
    ap.add_argument('--table'); ap.add_argument('--figure')
    a = ap.parse_args()
    D = load(a.csv)
    if a.table: Path(a.table).write_text(table(D))
    else: print(table(D))
    if a.figure: figure(D, a.figure)
