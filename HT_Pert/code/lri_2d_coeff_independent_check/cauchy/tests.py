"""Self-tests (run in seconds):
 1. mode weights reproduce <phi(t1)phi(t2)> = |2 sin((t1-t2)/2)|^(-2x)
 2. M, V from the multiset combinatorics equal a brute-force construction (ordered mode tuples,
    explicit theta quadrature of the phases, explicit reflection-even vectors) at a generic real x
 3. M, V symmetric; <p|M|p> = 2p, <p|V|p> = p(p-1)/2
 4. Hellmann-Feynman derivatives (incl. the consistent-scheme chain rule) vs finite differences
"""
import math, itertools, cmath, sys
import numpy as np
from basis import Space, load_or_build
from flint import ctx, acb


def w_ab(x, a, b):
    w = 1.0
    for k in range(a):
        w *= (x + k) / (k + 1)
    for k in range(b):
        w *= (x + k) / (k + 1)
    return w


def test_twopoint():
    x = 0.37
    for th in (0.3, 1.1, 2.5):
        s = 0.0
        for a in range(400):
            for b in range(400):
                s += w_ab(x, a, b) * math.cos((a - b) * th)
        exact = abs(2 * math.sin(th / 2)) ** (-2 * x)
        assert abs(s - exact) < 2e-2 * exact, (s, exact)  # slowly convergent sum (truncation ~ N^(2x-2))
    print("two-point function: ok")


def numeric_op(sp, ops, par, name, x):
    sec = sp.sectors[par]
    n = len(sec['states'])
    cs = [math.sqrt(w_ab(x, a, b)) for a, b in sp.modes]
    A = np.zeros((n, n))
    for (i, j), md in ops[par][name].items():
        for mono, sd in md.items():
            v = 1.0
            for m, e in mono:
                v *= cs[m] ** e
            for S, q in sd.items():
                A[i, j] += float(q) * math.sqrt(S) * v
    return A


def brute_op(sp, par, K, x):
    """Brute force: ordered tuples of modes, theta average done by quadrature of the phases."""
    modes = sp.modes
    nm = len(modes)
    cs = [math.sqrt(w_ab(x, a, b)) for a, b in modes]
    sec = sp.sectors[par]
    # unsymmetrized J=0 states in the sector (all members of orbits)
    full = []
    for s in sec['states']:
        full.append(s)
        if sp.R(s) != s:
            full.append(sp.R(s))
    fidx = {s: i for i, s in enumerate(full)}
    nf = len(full)
    Op = np.zeros((nf, nf), dtype=complex)
    nth = 4 * (sp.L + 2) * K + 1
    thetas = [2 * math.pi * k / nth for k in range(nth)]
    for j, s in enumerate(full):
        for kc in range(K + 1):
            for tup in itertools.product(range(nm), repeat=K):
                cre, ann = tup[:kc], tup[kc:]
                # apply annihilators (rightmost first) then creators
                st = list(s)
                amp = 1.0
                ok = True
                for m in reversed(ann):
                    if st[m] == 0:
                        ok = False
                        break
                    amp *= math.sqrt(st[m])
                    st[m] -= 1
                if not ok:
                    continue
                for m in reversed(cre):
                    st[m] += 1
                    amp *= math.sqrt(st[m])
                t = tuple(st)
                if t not in fidx:
                    continue  # projection (level, J, cap)
                Jph = sum(modes[m][0] - modes[m][1] for m in cre) - sum(modes[m][0] - modes[m][1] for m in ann)
                avg = sum(cmath.exp(1j * Jph * th) for th in thetas) / nth
                c = 1.0
                for m in tup:
                    c *= cs[m]
                Op[fidx[t], j] += math.comb(K, kc) * c * amp * avg
    # reflection-even isometry
    U = np.zeros((nf, len(sec['states'])))
    for i, s in enumerate(sec['states']):
        if sp.R(s) == s:
            U[fidx[s], i] = 1
        else:
            U[fidx[s], i] = U[fidx[sp.R(s)], i] = 1 / math.sqrt(2)
    return (U.T @ Op @ U).real


def test_ops():
    for (L, cap) in ((2, 5), (4, 4)):
        sp, ops = load_or_build(L, cap)
        x = 0.4137
        for par in (0, 1):
            for name, K, pref in (('M', 2, 1.0), ('V', 4, 1 / 12)):
                A = numeric_op(sp, ops, par, name, x)
                B = brute_op(sp, par, K, x) * pref
                err = np.max(np.abs(A - B))
                assert err < 1e-12, (L, cap, par, name, err)
                assert np.max(np.abs(A - A.T)) < 1e-12
        print(f"operators L={L} cap={cap}: brute force agrees, symmetric")
    sp, ops = load_or_build(4, 9)
    for p in range(4):
        i = sp.ref_index(p)
        M = numeric_op(sp, ops, p % 2, 'M', 0.5)
        V = numeric_op(sp, ops, p % 2, 'V', 0.5)
        assert abs(M[i, i] - 2 * p) < 1e-13 and abs(V[i, i] - p * (p - 1) / 2) < 1e-13
    print("diagonal elements <p|M|p>=2p, <p|V|p>=p(p-1)/2: ok")


def test_hf():
    from hamil import NumOps
    from solve import Point, FlintBE, NumpyBE
    ctx.prec = 200
    sp, ops = load_or_build(4, 11)
    no = NumOps(sp, ops)
    eps = acb("0.03", "0.02")
    for scheme in ('raw', 'consistent', 'literal'):
        pt = Point(no, scheme, 4, eps, FlintBE())
        r, g = acb("0.001", "-0.0005"), eps / 3
        o = pt.energies(r, g)
        h = acb("1e-25")
        o_r = pt.energies(r + h, g)
        o_g = pt.energies(r, g + h)
        for p in range(4):
            fr = (o_r['E'][p] - o['E'][p]) / h
            fg = (o_g['E'][p] - o['E'][p]) / h
            er = float((fr - o['Er'][p]).abs_lower())
            eg = float((fg - o['Eg'][p]).abs_lower())
            assert er < 1e-20 and eg < 1e-20, (scheme, p, er, eg)
        if scheme == 'consistent':
            assert o['E0_minus_EvL'] < 1e-50, o['E0_minus_EvL']
        print(f"HF derivatives ({scheme}): ok; ref weights", {p: round(w, 6) for p, w in o['wts'].items()})
        # double-precision backend agrees with the flint backend
        p64 = Point(no, scheme, 4, complex(0.03, 0.02), NumpyBE())
        o64 = p64.energies(complex(0.001, -0.0005), complex(0.03, 0.02) / 3)
        for p in range(4):
            z = o['E'][p]
            assert abs(o64['E'][p] - complex(float(z.real.mid()), float(z.imag.mid()))) < 1e-13
            assert abs(o64['Er'][p] - complex(float(o['Er'][p].real.mid()), float(o['Er'][p].imag.mid()))) < 1e-10
        print(f"   numpy backend agrees ({scheme})")


if __name__ == '__main__':
    test_twopoint()
    test_ops()
    test_hf()
    print("ALL TESTS PASSED")
