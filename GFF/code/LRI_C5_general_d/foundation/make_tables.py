#!/usr/bin/env python3
"""Build validation_section.tex from results/val50.json (+ results/valx.json) and the references."""
import json
import os
import mpmath as mp

mp.mp.dps = 80
HERE = os.path.dirname(os.path.abspath(__file__))
M = mp.mpmathify
ref = json.load(open('<PROJECT>/LRI_C5_general_d/references/reference_values.json'))['values']
val = json.load(open(os.path.join(HERE, 'results/val50.json')))
summ = json.load(open(os.path.join(HERE, 'results/val50_summary.json')))
valx = json.load(open(os.path.join(HERE, 'results/valx.json'))) if os.path.exists(os.path.join(HERE, 'results/valx.json')) else None


def e(x):
    x = M(x)
    if x == 0:
        return '0'
    ex = int(mp.floor(mp.log10(abs(x))))
    mant = mp.nstr(x / mp.mpf(10) ** ex, 2)
    if mant.lstrip('-').startswith('10'):
        ex += 1
        mant = mp.nstr(x / mp.mpf(10) ** ex, 2)
    return r'$%s\cdot10^{%d}$' % (mant, ex)


def num(x, n=30):
    return r'\texttt{%s}' % mp.nstr(M(x), n)


out = []
out.append(r'\section{Validation}\label{sec:validation}')
out.append(r"""All runs: \texttt{run\_validation.py} on \texttt{symmetry} (job 568940, one AMD node, 50 requested digits,
15 guard digits; supplementary job 568959). References: closed forms at $d=1,2$
($P_4(1)=13B_--3B_+$, $Q_1=\Gamma(\frac14)^4/\pi$, $\mathcal L_1$ from \texttt{eq:KLpsiReflected},
$Z_1=Q_1(\frac{2\pi^2}3+8\Cat)$; $P_4(2)=(B_-^2-B_+^2)/(4\pi^3)$, $Q_2=\frac16[\Gamma(\frac14)/\Gamma(\frac34)]^4$,
$\mathcal L_2=-2\log2\,P_4(2)$, $Z_2=4\Cat Q_2$), the archived $d=3$ values ($\ge90$ digits), and for
non-integer $d$ the independent spectral references of session C63d
(\texttt{references/reference\_values.json}, 41--50 digits on the diagonal, 56 digits off it).
Relative deviations are listed.""")

# Table: center
out.append(r'\begin{table}[ht]\centering\small')
out.append(r'\begin{tabular}{@{}rrlccccc@{}}\toprule')
out.append(r'$d$&$r$&$W_r(d;d/2)$&fixed&note&ref.\ dig.&top mode&off-grid\\\midrule')
for c in summ['center']:
    out.append(r'%s&%d&%s&%s&%s&%s&%s&%s\\' % (c['d'], c['r'], num(c['W'], 20), e(c['rel_fixed']), e(c['rel_note']),
                                             c['ref_digits'] if c['ref_digits'] != 80 else r'$\ge80$',
                                             e(c['top_mode_rel']), e(c['trig_check'])))
out.append(r'\bottomrule\end{tabular}')
out.append(r"""\caption{(a) $b=d/2$: $W_4=P_4(d)$, $W_3=3Q_d$. ``Fixed'' are the $b$-independent nodes
\eqref{eq:nodes} with $N=2r-1$ and a full complex DFT; ``note'' are the $b$-dependent nodes with the real cosine
transform of \texttt{fp:cosineTransform}. At $b=d/2$ the latter is literally the note's formula. The last two columns
test Theorems~\ref{th:finite} and \ref{th:top}: the relative size of the top coefficient, and
$|\Xi_r(t_*)-\sum_kc_{r,k}\cos2\pi k(t_*+b/4)|/|\Xi_r(t_*)|$ at the extra point $t_*=0.2371+0.0917\ii$.}""")
out.append(r'\label{tab:center}\end{table}')

# Table: offdiag
out.append(r'\begin{table}[ht]\centering\small')
out.append(r'\begin{tabular}{@{}rrrlccc@{}}\toprule')
out.append(r'$d$&$b$&$r$&$W_r(d;b)$ (finite sample)&fixed vs C63d&note vs C63d&top mode\\\midrule')
for c in summ['offdiag']:
    out.append(r'%s&%s&%d&%s&%s&%s&%s\\' % (c['d'], c['b'], c['r'], num(c['W'], 22), e(c['rel_fixed']), e(c['rel_note']),
                                          e(c['top_mode_rel'])))
xrows = []
if valx:
    pts = {}
    for p in valx['points']:
        pts[(p['kind'],) + tuple(p['payload'])] = p['out']
    for b in ('0.43', '0.37'):
        for r in (3, 4):
            o = pts.get(('point', r, '0.8', b, 'fixed'))
            if o is None:
                continue
            for item in ref['d=0.8']['offdiag']:
                if item['b'] == float(b) or str(item['b']) == b:
                    R = M(item['W%d' % r])
            w = M(o['W'])
            out.append(r'0.8&%s&%d&%s&%s&--&%s\\' % (b, r, num(mp.re(w), 22), e(abs(mp.re(w) - R) / abs(R)), e(M(o['top_mode_rel']))))
out.append(r'\bottomrule\end{tabular}')
out.append(r"""\caption{(b) $b\neq d/2$: the finite-sample formula against the independent spectral evaluation of
C63d (\texttt{hp\_general\_d.py}; quadrature plus exact multiplicity tails). These include the requested points
$d=1.5$, $b=0.70,0.80$ and $d=2.5$, $b=1.20$.}""")
out.append(r'\label{tab:offdiag}\end{table}')

# own spectral
out.append(r'\begin{table}[ht]\centering\small')
out.append(r'\begin{tabular}{@{}rrrlc@{}}\toprule')
out.append(r'$d$&$b$&$r$&$W_r(d;b)$ (own spectral code, \texttt{spectral.py})&rel.\ dev.\ from finite sample\\\midrule')
for c in summ['spectral']:
    if 'rel' in c:
        out.append(r'%s&%s&%d&%s&%s\\' % (c['d'], c['b'], c['r'], num(c['spectral'], 30), e(c['rel'])))
out.append(r'\bottomrule\end{tabular}')
out.append(r"""\caption{(b$'$) A second, independent spectral code (sharing only the Hurwitz-zeta routine) at the
requested points.}""")
out.append(r'\label{tab:ownspectral}\end{table}')

# circles
out.append(r'\begin{table}[ht]\centering\small')
out.append(r'\begin{tabular}{@{}rclccc@{}}\toprule')
out.append(r'$d$&master&value from the $b$-circle&rel.\ dev.&ref.\ digits&$\rho$\\\midrule')
for c in summ['circles']:
    nm = r'$\mathcal L_d$' if c['quantity'] == 'L' else r'$Z_d$'
    out.append(r'%s&%s&%s&%s&%s&%s\\' % (c['d'], nm, num(c['circle'], 28), e(c['rel']),
                                       c['ref_digits'] if c['ref_digits'] != 80 else r'$\ge80$', mp.nstr(M(c['rho']), 4)))
out.append(r'\bottomrule\end{tabular}')
out.append(r"""\caption{(c) End-to-end test of the $b$-dependence: $\mathcal L_d=\partial_bW_4$ and
$Z_d=\frac19\partial_b^2W_3$ at $b=d/2$ from Cauchy integrals of the finite-sample $W_r(d;b)$ over $96$ points of the
circle $|b-d/2|=\rho$ (conjugate symmetry used, phases $2\pi(k+\frac12)/96$). The radius is one third of the
distance to the nearest singularity of $W_r$ or to $\bmax$, so the truncation error is $\lesssim3^{-96}$. The first
derivative $\partial_bW_3(d;d/2)$, which must vanish, comes out between $10^{-44}$ and $10^{-61}$.}""")
out.append(r'\label{tab:circles}\end{table}')

# extra
if valx:
    out.append(r'\begin{table}[ht]\centering\small')
    out.append(r'\begin{tabular}{@{}llrrrlc@{}}\toprule')
    out.append(r'check&$d$&$b$&$r$&&value&rel.\ dev.\\\midrule')
    pts = {}
    for p in valx['points']:
        pts[(p['kind'],) + tuple(p['payload'])] = p['out']
    # reduced nodes vs fixed (from val50 or valx)
    allpts = {}
    for p in val['points']:
        allpts[(p['kind'],) + tuple(p['payload'])] = p['out']
    allpts.update(pts)
    for (r, d, b) in [(4, '1.5', '0.7'), (3, '1.5', '0.8'), (4, '2.5', '1.2'), (3, '2.5', '1.2'), (4, '2', '1'), (3, '3', '1.5')]:
        o = pts.get(('point', r, d, b, 'reduced'))
        f = [allpts[k] for k in allpts if k[0] == 'point' and k[1] == r and k[2] == d and k[4] == 'fixed' and abs(M(k[3]) - M(b)) < 1e-30]
        if o and f:
            w, wf = M(o['W']), M(f[0]['W'])
            out.append(r'reduced nodes&%s&%s&%d&&%s&%s\\' % (d, b, r, num(mp.re(w), 22), e(abs(w - wf) / abs(wf))))
    gC = lambda x: mp.gamma(x) / mp.gamma(1 - x)
    for b in ('0.8', '1.2'):
        o = pts.get(('point', 3, '2', b, 'fixed'))
        if o:
            bb = M(b)
            cf = gC(bb / 4) ** 3 / (2 * gC(3 * bb / 4))
            w = M(o['W'])
            out.append(r'exact $W_3(2;b)$&2&%s&3&&%s&%s\\' % (b, num(mp.re(w), 22), e(abs(w - cf) / abs(cf))))
    for (r, d, b) in [(4, '2.5', '1.8'), (3, '2.5', '1.55'), (4, '2.75', '1.95'), (3, '2.75', '1.65')]:
        o = pts.get(('point', r, d, b, 'fixed'))
        s = pts.get(('spectral', r, d, b, 40))
        if o and s:
            w, ws = M(o['W']), M(s['W'])
            out.append(r'past $\bmax$ vs spectral&%s&%s&%d&&%s&%s\\' % (d, b, r, num(mp.re(w), 22), e(abs(w - ws) / abs(ws))))
    for key, o in pts.items():
        if key[0] == 'point' and o.get('exceptional'):
            r, d, b = key[1], key[2], key[3]
            s = pts.get(('spectral', r, d, b, 40))
            if s:
                w, ws = M(o['W']), M(s['W'])
                out.append(r'resonant, vs spectral&%s&%s&%d&&%s&%s\\' % (
                    mp.nstr(M(d), 5), mp.nstr(M(b), 5), r, num(mp.re(w), 22), e(abs(w - ws) / abs(ws))))
    out.append(r'\bottomrule\end{tabular}')
    out.append(r"""\caption{(d) Supplementary checks at 50 digits. ``Reduced nodes'': $N=2r-3$ $b$-independent nodes
(Theorem~\ref{th:top}) against $N=2r-1$. ``Exact'': $W_3(2;b)=\gamma_C(\frac b4)^3/(2\gamma_C(\frac{3b}4))$,
$\gamma_C(x)=\Gamma(x)/\Gamma(1-x)$ (\texttt{gs:W3d2}), at $b\ne1$. ``Past $\bmax$'': continued Horn values for
$d>2$ (Remark~\ref{rem:continuation}) against \texttt{spectral.py}; here the precision is limited by the cancellation
near the pole of the $c_{r,k}$ at $\bmax$. ``Resonant'': $r(d-b)/2\in\mathbb Z$, circle mean, against
\texttt{spectral.py}.}""")
    out.append(r'\label{tab:extra}\end{table}')

sjp = os.path.join(HERE, 'results/sample_jets.json')
if os.path.exists(sjp):
    sj = json.load(open(sjp))
    out.append(r'\begin{table}[ht]\centering\small')
    out.append(r'\begin{tabular}{@{}rrlcc@{}}\toprule')
    out.append(r'$d$&$r$&jet from \eqref{eq:jets} with sample derivatives&rel.\ dev.&$W_r(d;d/2)$ rel.\ dev.\\\midrule')
    for key, v in sj['results'].items():
        r = int(key[1]); d = key.split('_d')[1]
        def refv(name):
            if d in val.get('refs', {}):
                return M(val['refs'][d][name])
            return M(ref['d=' + d][name]['value'])
        if r == 4:
            jet, R, Wref, nm = mp.re(M(v['dW'])), refv('L'), refv('P4'), r'$\mathcal L_d=$ '
        else:
            jet, R, Wref, nm = mp.re(M(v['d2W'])) / 9, refv('Z'), refv('threeQ'), r'$Z_d=$ '
        out.append(r'%s&%d&%s%s&%s&%s\\' % (d, r, nm, num(jet, 24), e(abs(jet - R) / abs(R)),
                                            e(abs(mp.re(M(v['W'])) - Wref) / abs(Wref))))
    out.append(r'\bottomrule\end{tabular}')
    out.append(r'\caption{(e) The jet formula \eqref{eq:jets} evaluated literally: elementary weights '
               r'$f_j=N_b^r\omega_{r,j}$ and their $b$-derivatives, times the samples $\Xi_r(t_j;b)$ at the reduced '
               r'$b$-independent nodes and their $b$-derivatives at fixed $t_j$ (Cauchy circles of $48$ points, radius one '
               r'sixth of the distance to the nearest singularity of the samples, Remark~\ref{rem:sampleradius}), at 30 '
               r'digits. The per-block values and $b$-derivatives at the nodes are stored in '
               r'\texttt{results/sample\_jets.json} for checking analytic parameter derivatives.}')
    out.append(r'\label{tab:jets}\end{table}')
out.append(r'\FloatBarrier')
out.append(r"""\paragraph{Summary.} (a) At $b=d/2$ the general-$b$ formula reproduces $P_4(d)$ and $3Q_d$ at $d=1,2,3$
to $10^{-63}$--$10^{-66}$ relative (the working precision), and at five non-integer $d$ to the 41--50 digits of
the references. Both node choices agree. (b) At $b\ne d/2$ it agrees with two independent spectral codes to
$10^{-49}$--$10^{-55}$, and at $d=2$ with the exact $W_3(2;b)$. (c) The off-grid sample is reproduced by the
trigonometric polynomial, and $c_{r,r-1}$ vanishes to working precision everywhere: Theorems~\ref{th:finite},
\ref{th:top}. At $d=1$ also $c_{4,1}=c_{4,3}=0$ and $c_{3,0}=c_{3,2}=0$ (Remark~\ref{rem:d1}); at $d=2$,
$c_{3,0}=c_{3,1}$ (one half-integer mode of $\Omega_3$). (d) The Cauchy circles reproduce
$\mathcal L_d$ and $Z_d$ at $d=0.8,1,1.25,1.5,2,2.5,2.75,3$, which tests the analytic $b$-dependence that
Corollary~\ref{cor:nodes} differentiates. (e) The jet formula \eqref{eq:jets} itself, with sample derivatives at the fixed
$b$-independent nodes, reproduces $\mathcal L_d$ and $Z_d$ at $d=1,1.5,2,2.5,3$ (Table~\ref{tab:jets}).""")

open(os.path.join(HERE, 'validation_section.tex'), 'w').write('\n'.join(out) + '\n')
print('wrote validation_section.tex')
