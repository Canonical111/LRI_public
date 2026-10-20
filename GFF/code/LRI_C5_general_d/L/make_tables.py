#!/usr/bin/env python3
"""LaTeX tables for L_general_d.tex from the validation runs (session L).  Writes tables.tex and results/summary.json."""
import os
import sys
import json
import glob
import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze  # noqa: E402

mp.mp.dps = 90


def load(fn):
    return json.load(open(os.path.join(HERE, 'results', fn)))


def sci(x, floor=None):
    x = mp.mpf(x)
    if x == 0:
        return '$<10^{-%d}$' % (floor or 60)
    e = int(mp.floor(mp.log10(x)))
    m = x / mp.mpf(10) ** e
    return '$%s\\cdot10^{%d}$' % (mp.nstr(m, 2), e)


def sci1(x, floor=60):
    x = mp.mpf(x)
    if x == 0:
        return '$<10^{-%d}$' % floor
    e = int(mp.floor(mp.log10(x)))
    m = int(mp.nint(x / mp.mpf(10) ** e))
    if m == 10:
        m, e = 1, e + 1
    return '$%d{\\cdot}10^{%d}$' % (m, e)


def main():
    R = analyze.refs()
    runs = {'val50.json': 50, 'val70.json': 70, 'val50x.json': 50, 'val50s.json': 50}
    best = {}
    for fn, dps in runs.items():
        res = load(fn)
        for k, o in res['results'].items():
            if not k.startswith('center_r4_d'):
                continue
            dstr = k[len('center_r4_d'):]
            cv = res['results']['conv_r4_d' + dstr]
            ent = dict(dps=dps, P4=o['W'], L=o['dW'], convP4=analyze.rel(o['W'], cv['W']), convL=analyze.rel(o['dW'], cv['dW']),
                       funcs=o['funcs'])
            c3 = res['results'].get('center_r3_d' + dstr)
            if c3:
                ent['threeQ'] = c3['W']
                ent['dW3'] = abs(mp.mpf(c3['dW'])) / mp.mpf(c3['W'])
            if dstr not in best or dps > best[dstr]['dps']:
                best[dstr] = ent
    order = sorted(best, key=lambda z: float(mp.mpmathify(z)))
    src = {'1': 'closed form (proved)', '2': '$-2\\log2\\,P_4(2)$ (proved)', '3': 'C63d (160 d.)'}
    lines = []
    lines.append('\\begin{table}[ht]\\centering\\footnotesize')
    lines.append('\\begin{tabular}{@{}l l l l l l@{}}\\toprule')
    lines.append('$d$ & $\\mathcal L_d$ (five-Horn formula) & reference & dev.\\ $P_4$ & dev.\\ $\\mathcal L_d$ & conv.\\ $\\mathcal L_d$\\\\\\midrule')
    summary = {}
    for dstr in order:
        e = best[dstr]
        ref = R.get(dstr)
        if dstr in src:
            s = src[dstr]
        elif ref and ref.get('source'):
            s = 'spectral, our run (%s d.)' % ref['source'].split()[-1]
        else:
            s = 'C63d spectral (%d d.)' % ref['digits']['L']
        dP = analyze.rel(e['P4'], ref['P4'])
        dL = analyze.rel(e['L'], ref['L'])
        dlab = dstr.replace('4/3', '$4/3$').replace('8/3', '$8/3$')
        lines.append('%s & $%s$ & %s & %s & %s & %s\\\\' % (dlab, mp.nstr(mp.mpf(e['L']), 22), s, sci(dP), sci(dL), sci(e['convL'], e['dps'] + 10)))
        summary[dstr] = dict(dps=e['dps'], P4=mp.nstr(mp.mpf(e['P4']), 45), L=mp.nstr(mp.mpf(e['L']), 45),
                             dev_P4_vs_ref=mp.nstr(dP, 3), dev_L_vs_ref=mp.nstr(dL, 3), internal_conv_L=mp.nstr(e['convL'], 3),
                             internal_conv_P4=mp.nstr(e['convP4'], 3), reference=s,
                             threeQ=e.get('threeQ'), dW3_over_W3=mp.nstr(e['dW3'], 3) if 'dW3' in e else None,
                             funcs=e['funcs'])
    lines.append('\\bottomrule\\end{tabular}')
    lines.append('\\caption{$\\mathcal L_d$ from the five-Horn formula \\eqref{eq:Lfinal} (exact jet derivative), at the working '
                 "precision of the run (50 digits; 70 digits at $d=1,1.5,2,2.5,3$). ``dev.'' is the relative deviation from the "
                 "reference, ``conv.'' the relative change when all truncation parameters $(M,K,N)$ are enlarged by $1.4$. "
                 'For non-integer $d$ the references come from an independent spectral code; at $d=0.6,4/3,8/3,3.5$ '
                 'we ran that code ourselves at 32 digits (\\texttt{refcheck\\_r4.py}).}')
    lines.append('\\label{tab:L}\\end{table}')
    # off-diagonal table
    od = []
    od.append('\\begin{table}[ht]\\centering\\footnotesize')
    od.append('\\begin{tabular}{@{}l l l l@{}}\\toprule')
    od.append('$d$ & $b$ & $W_4(d;b)$ dev. & $W_3(d;b)$ dev.\\\\\\midrule')
    for fn in ('val70.json', 'val50.json'):
        res = load(fn)
        for k in sorted(res['results'], key=lambda z: z):
            if not k.startswith('offdiag_r4_d'):
                continue
            dstr, bstr = k[len('offdiag_r4_d'):].split('_b')
            if fn == 'val50.json' and ('offdiag_r4_d%s_b%s' % (dstr, bstr)) in load('val70.json')['results']:
                continue
            ref = R.get(dstr)
            w4 = mp.mpf(res['results'][k]['W'])
            w3 = mp.mpf(res['results']['offdiag_r3_d%s_b%s' % (dstr, bstr)]['W'])
            if ref and 'offdiag' in ref and bstr in ref['offdiag']:
                r3, r4 = ref['offdiag'][bstr]
                od.append('%s & %s & %s & %s\\\\' % (dstr, bstr, sci(analyze.rel(w4, r4)), sci(analyze.rel(w3, r3))))
            elif dstr == '2':
                bb = mp.mpf(bstr)
                ex3 = analyze.gC(bb / 4) ** 3 / (2 * analyze.gC(3 * bb / 4))
                od.append('%s & %s & (reflection, below) & %s (exact \\texttt{gs:W3d2})\\\\' % (dstr, bstr, sci(analyze.rel(w3, ex3))))
    res70 = load('val70.json')['results']
    ratio = mp.mpf(res70['offdiag_r4_d2_b1.05']['W']) / mp.mpf(res70['offdiag_r4_d2_b0.95']['W'])
    bb = mp.mpf('1.05')
    exact = 2 ** (4 - 4 * bb) * analyze.gC(bb / 2) ** 2 / analyze.gC(bb - mp.mpf(1) / 2)
    od.append('2 & $1.05/0.95$ & %s & ratio vs.\\ proved reflection (\\texttt{gc:L2second})\\\\' % sci(analyze.rel(ratio, exact)))
    od.append('\\bottomrule\\end{tabular}')
    od.append('\\caption{The three-node formula away from $b=d/2$: relative deviation of $W_4(d;b)$ and of the $r=3$ two-node formula '
              'from C63d\'s 56-digit spectral values, from the exact $W_3(2;b)$, and from the proved $d=2$ rim--spoke reflection. '
              'Rows at 70 digits for $d=1.5,2,2.5$, otherwise 50.}')
    od.append('\\label{tab:offdiag}\\end{table}')
    # test data table
    td = []
    td.append('\\begin{table}[ht]\\centering\\scriptsize')
    td.append('\\begin{tabular}{@{}l l l l@{}}\\toprule')
    td.append('$d$ & $\\mathfrak f$ & value at $b=d/2$ & $\\partial_b$ at $b=d/2$\\\\\\midrule')
    names = [('hx', '\\mathfrak h_x'), ('h1', '\\mathfrak h_1'), ('hh', '\\mathfrak h_{1/2}'), ('s0', '\\mathfrak s_0'),
             ('s1', '\\mathfrak s_{1/2}')]
    for dstr in ('1', '1.5', '2', '2.5', '3'):
        f = best[dstr]['funcs']
        for i, (k, tex) in enumerate(names):
            td.append('%s & $%s$ & $%s$ & $%s$\\\\' % (dstr if i == 0 else '', tex, mp.nstr(mp.mpf(f[k][0]), 32),
                                                     mp.nstr(mp.mpf(f[k][1]), 32)))
        if dstr != '3':
            td.append('\\addlinespace')
    td.append('\\bottomrule\\end{tabular}')
    td.append('\\caption{Test data: the five Horn values and their first $b$-derivatives (total derivative, $u=x$ moving for '
              '$\\mathfrak h_x$) at $b=d/2$, 32 of the $\\ge 55$ digits computed (70-digit runs). At $d=1$, '
              '$\\mathfrak s_0=83/81$, $\\mathfrak s_0^\\prime=64/243$ and $\\mathfrak s_{1/2}=1$ exactly.}')
    td.append('\\label{tab:testdata}\\end{table}')
    open(os.path.join(HERE, 'tables.tex'), 'w').write('\n'.join(lines + [''] + od + [''] + td) + '\n')
    json.dump(summary, open(os.path.join(HERE, 'results', 'summary.json'), 'w'), indent=1)
    print('wrote tables.tex and results/summary.json')
    for dstr in order:
        print(dstr, summary[dstr]['dev_L_vs_ref'], summary[dstr]['internal_conv_L'], summary[dstr]['L'][:40])


def cfd_table():
    fn = os.path.join(HERE, 'results', 'cfd40.json')
    out = os.path.join(HERE, 'cfd_table.tex')
    if not os.path.exists(fn):
        open(out, 'w').write('\\subsection{Per-function derivative check}\\label{sec:cfd}\nPending.\n')
        return
    res = json.load(open(fn))
    L = ['\\subsection{Per-function derivative check}\\label{sec:cfd}',
         'For each of the five Horn functions, the jet value and derivative at $b=d/2$ were compared with the mean and the '
         'first Fourier coefficient of its plain (non-jet) values on a %d-point circle $|b-d/2|=\\rho$, '
         '$\\rho=%s\\min(d/2,\\bmax-d/2)$, at %d digits (\\texttt{check\\_func\\_derivs.py}). This checks the jet '
         'implementation for every function separately; it is not an independent evaluation. Deviations are relative, '
         'and relative to $\\max(|f\'|,1)$ for the derivative (at $d=1$, $\\fs_{1/2}=1$ has $f\'=0$).' % (
             res['M'], mp.nstr(mp.mpf(res['rho_frac']), 3), res['dps']),
         '\\begin{center}\\scriptsize\\begin{tabular}{@{}l l l l l l@{}}\\toprule',
         '$d$ & $\\fh_x$ & $\\fh_1$ & $\\fh_{1/2}$ & $\\fs_0$ & $\\fs_{1/2}$\\\\\\midrule']
    for dstr, ent in res['results'].items():
        cells = []
        for k in ('hx', 'h1', 'hh', 's0', 's1'):
            cells.append('%s / %s' % (sci1(ent[k]['value_dev'], 60), sci1(ent[k]['deriv_dev'], 60)))
        L.append('%s & %s\\\\' % (dstr, ' & '.join(cells)))
    L.append('\\bottomrule\\end{tabular}\\end{center}')
    L.append('Each cell gives value deviation / derivative deviation.')
    open(out, 'w').write('\n'.join(L) + '\n')
    print('wrote cfd_table.tex')


if __name__ == '__main__':
    main()
    cfd_table()
