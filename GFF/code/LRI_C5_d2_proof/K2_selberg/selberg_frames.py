"""Structural check: is the d=2 K-path master J_t a complex Selberg (Aomoto / Dotsenko-Fateev) integral in some
conformal frame?  Complete J_d(a,b,c,f,e) to the balanced K5 (gs:completion); a frame = choice of the two
integrated vertices {X,Y}; Selberg form requires lambda_{XA} = lambda_{YA} for the three fixed vertices A.
Also checks the Fourier-dual kite J(2-a, 2-c, 2-b, 2-f, 2-e) (planar duality of the propagator-type kite),
and the pattern-B base point t -> 0 itself."""
import sympy as sp
from itertools import combinations
t, d = sp.symbols('t d')

def K5(a, b, c, f, e, d):
    lam = {(0,1): 3*d-a-b-c-f-e, (0,2): a, (0,3): c, (0,4): b+f+e-d, (1,2): b, (1,3): f,
           (1,4): a+c+e-d, (2,3): e, (2,4): 2*d-a-b-e, (3,4): 2*d-c-f-e}
    L = lambda i, j: lam[(min(i,j), max(i,j))]
    for v in range(5):
        assert sp.simplify(sum(L(v, w) for w in range(5) if w != v) - 2*d) == 0
    return L

def selberg_frames(L, label, generic=True):
    hits = []
    for X, Y in combinations(range(5), 2):
        fixed = [A for A in range(5) if A not in (X, Y)]
        conds = [sp.simplify(L(X, A) - L(Y, A)) for A in fixed]
        if generic:
            ok = all(c == 0 for c in conds)          # identically in t
        else:
            ok = all(c == 0 for c in conds)
        if ok:
            hits.append((X, Y))
    print('%-55s Selberg frames: %s' % (label, hits if hits else 'none'))

L = K5(1, 1, 1, 2-t, 1, 2)
print('K5 exponents of J_t at d=2:', {(i,j): L(i,j) for i in range(5) for j in range(i+1,5)})
selberg_frames(L, 'J_t (d=2), identically in t')
selberg_frames(K5(1, 1, 1, 2-sp.Rational(0), 1, 2) if False else K5(1,1,1,2,1,2), 'pattern-B base point t=0 (d=2)')
selberg_frames(K5(2-1, 2-1, 2-1, 2-(2-t), 2-1, 2), 'Fourier-dual kite of J_t')
# the balanced three-wheel (gs:W3d2) for comparison: J(2-b, b, 2-b, b, b)
bb = sp.symbols('b')
selberg_frames(K5(2-bb, bb, 2-bb, bb, bb, 2), 'balanced three-wheel W3(2;b) (control: should be Selberg)')
# Pattern-B 5-parameter neighbourhood: is the base point on any Selberg subspace?
p1, p2, z1, z2, e = sp.symbols('p1 p2 z1 z2 e')
# invert: f = d - p1, b = 2d - f - e - p2, c = 2d - f - e - z2, a = 3d - b - c - f - e - z1
dd = 2
f_ = dd - p1; b_ = 2*dd - f_ - e - p2; c_ = 2*dd - f_ - e - z2; a_ = 3*dd - b_ - c_ - f_ - e - z1
LB = K5(a_, b_, c_, f_, e, dd)
base = {p1: 0, p2: 0, z1: 0, z2: 0, e: 1}
hits = []
for X, Y in combinations(range(5), 2):
    fixed = [A for A in range(5) if A not in (X, Y)]
    if all(sp.simplify((LB(X, A) - LB(Y, A)).subs(base)) == 0 for A in fixed):
        hits.append((X, Y))
print('%-55s Selberg frames: %s' % ('pattern-B base point (all 5 local coordinates = 0)', hits if hits else 'none'))
