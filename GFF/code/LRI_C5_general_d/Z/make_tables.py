#!/usr/bin/env python3
"""Generate z_validation.tex (tables of the numerical validation) from the JSON results in results/ and
spectral_ref/spec_refs.json.  Every number in the tables is read from those files (no transcription)."""
import json
import os

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
mp.mp.dps = 120


def load(p):
    return json.load(open(os.path.join(HERE, p)))


def tex_num(x, n):
    s = mp.nstr(x, n, min_fixed=-mp.inf, max_fixed=mp.inf)
    return s


def tex_sci(x):
    x = mp.mpf(x)
    if x == 0:
        return '$0$'
    e = int(mp.floor(mp.log10(abs(x))))
    m = x / mp.mpf(10) ** e
    return '$%s{\\cdot}10^{%d}$' % (mp.nstr(m, 2), e)


def dlabel(d):
    return {'4/3': '$4/3$', '8/3': '$8/3$'}.get(d, '$%s$' % d)


def main():
    import compare_refs as cr
    refs = cr.references()
    j90 = load('results/zj90.json')['results']
    j60 = load('results/zj60.json')['results']
    j60.update(load('results/zj60x.json')['results'])
    c60 = load('results/zc60.json')['results']
    c60.update(load('results/zc60x.json')['results'])
    order = ['1', '2', '3', '0.8', '1.25', '1.5', '2.5', '2.75', '4/3', '1.75', '8/3', '3.5', '3.75', '0.7']
    rows = []
    for d in order:
        if d in j90:
            r, eng = j90[d], 'jets, 90'
        elif d in c60:
            r, eng = c60[d], 'Cauchy, 60'
        else:
            continue
        Z = mp.re(mp.mpmathify(r['Z']))
        dW = abs(mp.mpmathify(r['dW']))
        ref = refs.get(d)
        if ref is not None:
            dev = abs(Z - ref['Z']) / abs(ref['Z'])
            src = ref['src']
            if src.startswith('closed form Q1'):
                src = '$Q_1(2\\pi^2/3+8\\Cat)$, note'
            elif src.startswith('closed form 4G'):
                src = '$4\\Cat Q_2$, note'
            elif src.startswith('C63d wf_Z3'):
                src = 'C63d, 250 digits'
            elif src.startswith('C63d spectral'):
                src = 'C63d spectral, %d dig.' % ref['digits']
            elif src.startswith('new spectral'):
                src = 'new spectral run'
            devs = tex_sci(dev)
        else:
            fdc = load('results/fdcirc.json')['results'] if os.path.exists(os.path.join(HERE, 'results', 'fdcirc.json')) else {}
            if d in fdc:
                zf = mp.re(mp.mpmathify(fdc[d]['Z']))
                src, devs = 'fixed-node circle$^\\ast$', tex_sci(abs(Z - zf) / abs(zf))
            else:
                src, devs = 'none', '--'
        rows.append('%s & \\texttt{%s} & %s & %s & %s & %s\\\\' % (
            dlabel(d), tex_num(Z, 36), src, devs, tex_sci(dW), eng))
    t1 = ['\\begin{table}[ht]\\centering\\scriptsize',
          '\\begin{tabular}{@{}l l l l l l@{}}\\toprule',
          '$d$ & $Z_d$ (two-node formula, 36 digits shown) & reference & rel.\\ dev. & $|\\partial_bW_3|$ & engine, dps\\\\\\midrule']
    t1 += rows
    t1 += ['\\bottomrule\\end{tabular}',
           '\\caption{$Z_d$ from Theorem~\\ref{th:jets} against the references. ``rel.\\ dev.\'\' is relative to the '
           'reference; the generic-$d$ references are good to the number of digits stated (C63d) or to about '
           '$10^{-39}$ (new runs of the same independent spectral code at 45 digits, $64$ circle points). '
           '$|\\partial_bW_3|$ is the first rim derivative at $b=d/2$ computed from the same jets; it must vanish. '
           'At the resonant dimensions $d=4/3,8/3$ the Cauchy engine is used. $^\\ast$At $d=0.7$ the spectral run '
           'failed (its own $\\partial_bW_3$ came out as $-83$; the circle passes within $0.013$ of the spectral '
           'convergence bound $b_{\\rm spec}=0.367$), so only a consistency check is shown: a $b$-circle of the '
           'foundation\'s fixed-node formula (five complex nodes, all blocks; it shares the Horn summation code, so it '
           'is not independent).}',
           '\\label{tab:Z}', '\\end{table}']
    # engine cross-check / self-convergence
    rows2 = []
    for d in order:
        if d not in j90:
            continue
        Z9 = mp.re(mp.mpmathify(j90[d]['Z']))
        e1 = abs(mp.re(mp.mpmathify(j60[d]['Z'])) - Z9) / Z9 if d in j60 else None
        e2 = abs(mp.re(mp.mpmathify(c60[d]['Z'])) - Z9) / Z9 if d in c60 else None
        rows2.append('%s & %s & %s\\\\' % (dlabel(d), tex_sci(e1) if e1 is not None else '--',
                                            tex_sci(e2) if e2 is not None else '--'))
    t2 = ['\\begin{table}[ht]\\centering\\small',
          '\\begin{tabular}{@{}lll@{}}\\toprule',
          '$d$ & $|Z^{\\rm jets}_{60}-Z^{\\rm jets}_{90}|/Z$ & $|Z^{\\rm Cauchy}_{60}-Z^{\\rm jets}_{90}|/Z$\\\\\\midrule']
    t2 += rows2
    t2 += ['\\bottomrule\\end{tabular}',
           '\\caption{Internal convergence: exact-jet engine at 60 and 90 working digits, and the Cauchy-circle engine '
           '(64 points; its error is the aliasing $(\\rho/R_f)^{64}$) against the 90-digit jets.}',
           '\\label{tab:conv}', '\\end{table}']
    # off-diagonal identity
    od = load('results/offdiag60.json')
    rows3 = []
    for r in od:
        b = r['b'].replace('j', '\\,i')
        src = 'C63d spectral' if r['src'].startswith('C63d') else 'foundation, fixed nodes'
        rows3.append('%s & $%s$ & \\texttt{%s} & %s & %s\\\\' % (
            dlabel(r['d']), b, tex_num(mp.re(mp.mpmathify(r['W_two_node'])), 24), src, tex_sci(r['rel'])))
    t3 = ['\\begin{table}[ht]\\centering\\scriptsize',
          '\\begin{tabular}{@{}l l l l l@{}}\\toprule',
          '$d$ & $b$ & $\\operatorname{Re}W_3=\\operatorname{Re}(uR+v\\hat M)$ (24 digits) & independent value & rel.\\ dev.\\\\\\midrule']
    t3 += rows3
    t3 += ['\\bottomrule\\end{tabular}',
           '\\caption{The two-node identity (Theorem~\\ref{th:twonode}) away from $b=d/2$, including complex $b$, '
           'against C63d\'s 56-digit spectral values (evaluated here at 50 digits) and against the foundation\'s '
           'fixed-node finite-sample formula with five complex nodes (60 digits).}',
           '\\label{tab:offdiag}', '\\end{table}']
    # block checks
    import io
    import contextlib
    import check_blocks as cb
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        o = cb.main(os.path.join(HERE, 'results', 'zj90.json'))
    mp.mp.dps = 120
    t4 = ['\\begin{table}[ht]\\centering\\small',
          '\\begin{tabular}{@{}lll@{}}\\toprule',
          'dimension & check (value, first, second $b$-derivative at $b=d/2$) & rel.\\ deviation\\\\\\midrule',
          '$d=1$ & $R$ vs Dixon closed form \\eqref{eq:Dixon} & %s\\\\' % ', '.join(tex_sci(x) for x in o['d1']['R_vs_Dixon']),
          '$d=1$ & $\\hat c_0$ (must vanish; absolute) & %s\\\\' % ', '.join(tex_sci(x) for x in o['d1']['c0hat']),
          '$d=2$ & $R$ vs Selberg closed form \\eqref{eq:R2} & %s\\\\' % ', '.join(tex_sci(x) for x in o['d2']['R_vs_Selberg']),
          '$d=2$ & $\\hat M$ (must vanish; absolute) & %s\\\\' % ', '.join(tex_sci(x) for x in o['d2']['Mh']),
          '$d=3$ & $R$ vs C63d\'s $S(3/2)$, $S\'(3/2)$, $S\'\'(3/2)$ & %s\\\\' % ', '.join(tex_sci(x) for x in o['d3']['R_vs_S']),
          '$d=3$ & $\\hat c_0$ vs $-N_b^3\\pi^5\\Gamma(3g-2)/\\Gamma(g)^9$ & %s\\\\' % ', '.join(tex_sci(x) for x in o['d3']['c0hat_vs_gamma']),
          'all $d$ & $u,v$ jets \\eqref{eq:uvjets} vs numerical differentiation & %s\\\\' % tex_sci(o['uv_worst']),
          '\\bottomrule\\end{tabular}',
          '\\caption{Block-level checks with the 90-digit exact jets.}', '\\label{tab:blocks}', '\\end{table}']
    out = '\n'.join(['% generated by make_tables.py from results/*.json; do not edit by hand', ''] + t1 + [''] + t2 +
                    [''] + t3 + [''] + t4) + '\n'
    open(os.path.join(HERE, 'z_validation.tex'), 'w').write(out)
    print(out)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, HERE)
    main()
