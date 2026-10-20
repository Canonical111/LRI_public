"""Truncated bivariate power series in (u, z) for flow normal forms (scratch)."""
import sympy as sp
u, z = sp.symbols('u z')

def trunc(e, D):
    p = sp.Poly(sp.expand(e), u, z)
    return sp.Add(*[c * u**i * z**j for (i, j), c in p.terms() if i + j <= D])

def compose(e, U, Z, D):
    """e(u,z) with u->U(u,z), z->Z(u,z), truncated at total degree D (U, Z have no constant term)."""
    p = sp.Poly(sp.expand(e), u, z)
    out = 0
    # cache powers
    Up = {0: sp.Integer(1)}; Zp = {0: sp.Integer(1)}
    for (i, j), c in p.terms():
        if i not in Up:
            for k in range(1, i + 1):
                if k not in Up: Up[k] = trunc(Up[k-1] * U, D)
        if j not in Zp:
            for k in range(1, j + 1):
                if k not in Zp: Zp[k] = trunc(Zp[k-1] * Z, D)
        out += c * trunc(Up[i] * Zp[j], D)
    return trunc(out, D)

def inverse(Uf, Zf, D):
    """Given new coords U'=Uf(u,z), Z'=Zf(u,z) (near identity), return (u,z) as series in (u',z') (named u,z)."""
    Ui, Zi = u, z
    for _ in range(D + 1):
        Ui_new = trunc(u - (compose(Uf, Ui, Zi, D) - Ui), D)
        Zi_new = trunc(z - (compose(Zf, Ui, Zi, D) - Zi), D)
        if sp.expand(Ui_new - Ui) == 0 and sp.expand(Zi_new - Zi) == 0:
            break
        Ui, Zi = Ui_new, Zi_new
    return Ui, Zi

def series_div(num, den, D):
    """num/den with den = 1 + O(u,z), truncated."""
    d1 = sp.expand(den - 1)
    inv, term = sp.Integer(1), sp.Integer(1)
    for _ in range(D + 1):
        term = trunc(-term * d1, D)
        if term == 0: break
        inv += term
    return trunc(num * inv, D)
