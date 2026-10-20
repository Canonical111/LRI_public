"""Symbolic derivation (session L): explicit residue functional for r=4 at a general rim exponent, and the
three-node formula W_4 = elementary combination of Xi(t=0), Xi(tau=0), Xi(tau=1/2).
Conventions as in foundation/general_b_periodization.tex: sigma=b/2, Xi(t;b)=sum_k c_k cos(2 pi k (t+sigma/2)),
W_r = -[N_b/(pi sin pi sigma)]^r sum_k B_{r,k}(sigma) c_k."""
import sympy as sp

sig = sp.symbols('sigma', positive=True)
pi, I = sp.pi, sp.I


def bellE(xs):
    E = [sp.Integer(1)]
    for m in range(1, len(xs) + 1):
        E.append(sp.expand(sum(xs[h - 1] / sp.factorial(h - 1) * E[m - h] for h in range(1, m + 1)) / m))
    return E


def u_list(r):
    c = sp.cot(pi * sig)
    u1 = -r * pi * c
    u2 = r * pi ** 2 * (c ** 2 + sp.Rational(4, 3))
    u3 = -2 * r * pi ** 3 * c * (1 + c ** 2)
    return [u1, u2, u3][:r - 1]


def Bweights(r):
    u = u_list(r)
    out = []
    for k in range(r):
        Ep = bellE([u[0] + 2 * pi * I * k] + u[1:])[r - 1]
        Em = bellE([u[0] - 2 * pi * I * k] + u[1:])[r - 1]
        B = (sp.exp(I * pi * k * sig) * Ep + sp.exp(-I * pi * k * sig) * Em) / 2
        B = sp.simplify(sp.expand_complex(sp.expand(B)).rewrite(sp.cos))
        out.append(sp.simplify(sp.trigsimp(B)))
    return out


if __name__ == '__main__':
    s, co = sp.sin(pi * sig), sp.cos(pi * sig)
    for r in (3, 4):
        Bw = Bweights(r)
        print('r =', r)
        for k, B in enumerate(Bw):
            print('  B_{%d,%d} =' % (r, k), sp.simplify(B))
    # check the explicit forms of the foundation
    c0, c1, c2 = sp.symbols('c0 c1 c2')
    B4 = Bweights(4)
    W4 = -(1 / (pi * s) ** 4) * (B4[0] * c0 + B4[1] * c1 + B4[2] * c2)   # times N^4
    W4_found = 4 / (pi * s ** 7) * (co * (3 + 2 * co ** 2) * c0 + (1 + 4 * co ** 2) * c1 + 5 * co * c2)
    print('foundation W4 explicit check:', sp.simplify(sp.expand(sp.expand_trig(W4 - W4_found))))
    # symbolic numeric check of the difference at random sigma
    for sv in (0.3, 0.37, 0.61):
        print('  numeric diff at sigma=%g:' % sv, [sp.N((W4 - W4_found).subs(sig, sv).coeff(x)) for x in (c0, c1, c2)])
    print('top weight B_{4,3} =', sp.simplify(B4[3]))
    # three-node formula: X0 = Xi(t=0) = c0 + c1 cos(pi sig) + c2 cos(2 pi sig); Xz = Xi(tau=0)=c0+c1+c2; Xh = c0-c1+c2
    X0, Xz, Xh = sp.symbols('X0 Xz Xh')
    sol = sp.solve([sp.Eq(X0, c0 + c1 * co + c2 * sp.cos(2 * pi * sig)), sp.Eq(Xz, c0 + c1 + c2), sp.Eq(Xh, c0 - c1 + c2)],
                   [c0, c1, c2], dict=True)[0]
    W4n = sp.simplify(W4_found.subs(sol))
    cand = 2 / (pi * s ** 7) * ((1 + co) ** 2 * (1 + 2 * co) * Xz - (1 - co) ** 2 * (1 - 2 * co) * Xh - 2 * co * X0)
    print('three-node formula check:', sp.simplify(sp.expand(sp.expand_trig(W4n - cand))))
    for sv in (0.3, 0.37, 0.61):
        print('  numeric diff at sigma=%g:' % sv, [sp.N((W4n - cand).subs(sig, sv).coeff(x)) for x in (X0, Xz, Xh)])
