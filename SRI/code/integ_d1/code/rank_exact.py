import random, sympy as sp
exec(open('linear_action.py').read().split('for key in sorted(res')[0])
mons = [(m, n) for m in range(1, D + 1) for n in range(0, D + 1 - m)]
gens = sorted(res, key=lambda t: (t[0] + t[1], t))
random.seed(1)
for trial in range(3):
    subs = {s: (1 if k == (1, 0) else sp.Rational(random.randint(-50, 50), random.randint(1, 9))) for k, s in Fs.items()}
    M = sp.Matrix([[sp.sympify(res[g].get(mo, 0)).subs(subs) for g in gens] for mo in mons])
    r = M.rank()
    left = M.T.nullspace()
    e40 = sp.Matrix([1 if mo == (4, 0) else 0 for mo in mons])
    in_span = M.row_join(e40).rank() == r
    print(f'trial {trial}: rank {r}/{len(mons)}; invariant functionals: ',
          [{mons[i]: v[i] for i in range(len(mons)) if v[i] != 0} for v in left], '; J9 direction removable:', in_span)
