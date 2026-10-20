"""Run plan for the direct finite-cutoff campaign (shared by driver and analysis)."""
import math

# cutoffs (exact binary-friendly decimals of 1/8, 1/10, ..., 1/500)
EPS = [0.125, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002]
EPS_N7_MIN = 0.005      # seven kinks down to eps = 1/200
EPS_N8_MIN = 0.01       # eight kinks down to eps = 1/100
EPS_QMC = [0.1, 0.05, 0.02, 0.01]
EPS_EXT = [0.005, 0.002, 0.001]   # extension group 'ext'
# dense grid for the residual-offset fits of the engine comparison (groups 'dense', 'dense8')
EPS_DENSE = [float('%.3g' % (10 ** (-3 + (math.log10(0.02) + 3) * i / 15))) for i in range(16)]
EPS_DENSE = [e for e in EPS_DENSE if all(abs(e - x) / x > 0.02 for x in EPS + EPS_EXT)]
EPS_DENSE8 = {'dense8a': [0.003], 'dense8b': [0.004, 0.007, 0.015],
              # phase 2 (mandatory per review): Q8 on the n<=7 dense grid in [0.002, 0.02], three nodes
              'q8xa': [0.00222, 0.011, 0.0164],
              'q8xb': [0.00271, 0.00405, 0.009],
              'q8xc': [0.00331, 0.00603, 0.00737, 0.0134]}


def nhi(eps):
    """Gauss points per nested variable for ~1e-13 relative accuracy (empirical)."""
    return 4 * math.ceil(8.7 * math.log(1.0 / eps) / 4.0)


def gauss_tasks(group):
    """Yield dicts: n, kind, E, form, ord, eps, N (N0 = 2N+16 for form 1)."""
    out = []

    def add(n, kind, E, ordr, eps, Ns, form=None):
        f = 1 if E else (0 if form is None else form)
        for N in Ns:
            out.append(dict(n=n, kind=kind, E=E, form=f, ord=ordr, eps=eps, N=N, N0=2 * N + 16))

    for eps in EPS:
        h = nhi(eps)
        three = [h - 8, h, h + 8]
        two = [h - 8, h]
        if group == 'main':
            add(2, 'Z', 0, 3, eps, three); add(2, 'Q', 0, 3, eps, three)
            add(2, 'Z', 1, 3, eps, three); add(2, 'Q', 1, 3, eps, three)
            add(3, 'A', 0, 3, eps, three); add(3, 'A', 1, 3, eps, three)
            add(4, 'Z', 0, 3, eps, three); add(4, 'Q', 0, 3, eps, three)
            add(4, 'Z', 1, 2, eps, three); add(4, 'Q', 1, 2, eps, three)
            add(5, 'A', 0, 3, eps, three); add(5, 'A', 1, 2, eps, three)
            add(6, 'Z', 0, 2, eps, three); add(6, 'Q', 0, 2, eps, three)
            add(6, 'Z', 1, 1, eps, two); add(6, 'Q', 1, 1, eps, two)
            if eps >= EPS_N7_MIN:
                add(7, 'A', 0, 1, eps, two)
                add(7, 'A', 1, 0, eps, two)
            # cross-parametrization checks (Lambda-outer form for no-source moments)
            if eps in (0.05, 0.01):
                for n, kind in [(3, 'A'), (4, 'Z'), (4, 'Q'), (5, 'A'), (6, 'Z'), (6, 'Q'), (7, 'A')]:
                    add(n, kind, 0, 1, eps, [h], form=1)
        elif group in ('ext', 'ext8', 'dense') or group in EPS_DENSE8:
            pass
        elif group == 'n8':
            if eps >= EPS_N8_MIN:
                o = 2 if eps >= 0.1 else 0
                add(8, 'Q', 0, o, eps, two)
                add(8, 'Z', 0, o, eps, two)
                if eps >= 0.1:
                    add(8, 'Q', 1, 1, eps, two)
    if group == 'dense':
        for eps in EPS_DENSE:
            h = nhi(eps)
            two = [h - 8, h]
            add(2, 'Z', 0, 3, eps, two); add(2, 'Q', 0, 3, eps, two)
            add(2, 'Z', 1, 3, eps, two); add(2, 'Q', 1, 3, eps, two)
            add(3, 'A', 0, 3, eps, two); add(3, 'A', 1, 3, eps, two)
            add(4, 'Z', 0, 3, eps, two); add(4, 'Q', 0, 3, eps, two)
            add(4, 'Z', 1, 2, eps, two); add(4, 'Q', 1, 2, eps, two)
            add(5, 'A', 0, 3, eps, two); add(5, 'A', 1, 2, eps, two)
            add(6, 'Z', 0, 2, eps, two); add(6, 'Q', 0, 2, eps, two)
            add(6, 'Z', 1, 1, eps, two); add(6, 'Q', 1, 1, eps, two)
            add(7, 'A', 0, 1, eps, two)
    if group in EPS_DENSE8:
        for eps in EPS_DENSE8[group]:
            h = nhi(eps)
            add(8, 'Q', 0, 0, eps, [h - 8, h])
    if group in ('ext', 'ext8'):
        # extension to smaller cutoffs (added after the first campaign showed ~1e-15 convergence)
        for eps in EPS_EXT:
            h = nhi(eps)
            three = [h - 8, h, h + 8]
            two = [h - 8, h]
            if group == 'ext' and eps <= 0.001:
                add(2, 'Z', 0, 3, eps, three); add(2, 'Q', 0, 3, eps, three)
                add(2, 'Z', 1, 3, eps, three); add(2, 'Q', 1, 3, eps, three)
                add(3, 'A', 0, 3, eps, three); add(3, 'A', 1, 3, eps, three)
                add(4, 'Z', 0, 3, eps, three); add(4, 'Q', 0, 3, eps, three)
                add(4, 'Z', 1, 2, eps, three); add(4, 'Q', 1, 2, eps, three)
                add(5, 'A', 0, 3, eps, two); add(5, 'A', 1, 2, eps, two)
                add(6, 'Z', 0, 2, eps, two); add(6, 'Q', 0, 2, eps, two)
                add(6, 'Z', 1, 1, eps, two); add(6, 'Q', 1, 1, eps, two)
            if group == 'ext' and eps >= 0.001 and eps < EPS_N7_MIN:
                add(7, 'A', 0, 1, eps, two)
                add(7, 'A', 1, 0, eps, two)
            if group == 'ext8' and eps >= 0.002 and eps < EPS_N8_MIN:
                add(8, 'Q', 0, 0, eps, two)
                add(8, 'Z', 0, 0, eps, two)
    return out


def qmc_tasks():
    out = []
    for eps in EPS_QMC:
        for n, kind, E, o in [(3, 'A', 0, 2), (3, 'A', 1, 2), (4, 'Z', 0, 2), (4, 'Q', 0, 2), (4, 'Z', 1, 1),
                              (4, 'Q', 1, 1), (5, 'A', 0, 2), (5, 'A', 1, 1), (6, 'Z', 0, 1), (6, 'Q', 0, 1),
                              (6, 'Z', 1, 0), (6, 'Q', 1, 0), (7, 'A', 0, 1), (7, 'A', 1, 0), (8, 'Q', 0, 0),
                              (8, 'Z', 0, 0)]:
            for gmap in ('seq', 'box'):
                out.append(dict(n=n, kind=kind, E=E, ord=o, eps=eps, map=gmap))
    return out


def task_key(t):
    return '%d|%s|%d|%d|%d|%.6g|%d|%d' % (t['n'], t['kind'], t['E'], t['form'], t['ord'], t['eps'], t['N'], t.get('N0', 0))


def qmc_key(t):
    return '%d|%s|%d|%d|%.6g|%s' % (t['n'], t['kind'], t['E'], t['ord'], t['eps'], t['map'])
