"""
Exact (symbolic) evaluation of the rotated (KLT) region sum for the d=2 master
  I(tau) = int_{C^2} |x|^{-1}|1-x|^{-1}|y|^{-1}|1-y|^{-2+2 tau}|x-y|^{-1} d^2x d^2y
         = (i/2)^2 * sum_{R,R'} exp(i pi phi(R,R')) A(R) A(R')
where the 12 regions R of R^2 (orderings of x,y relative to 0,1 and each other)
carry the real integrals A(R) = 2 I_j (I_j = d=1 elliptic moments of the note),
and phi(R,R') = sum_f a_f [sign_f(R) != sign_f(R')].
Then the d=1 moment relations reduce everything to I_3, I_4.
Output: the region sum equals 4 sin^2(pi tau) (I_3^2 + I_4^2), identically in tau.
"""
import sympy as sp

tau = sp.symbols('tau', positive=True)
I3, I4 = sp.symbols('I3 I4')
s, c = sp.sin(sp.pi*tau), sp.cos(sp.pi*tau)

# exponents a_f of the linear forms f = (x, 1-x, y, 1-y, y-x): integrand prod |f|^{2 a_f}
a = [sp.Rational(-1, 2), sp.Rational(-1, 2), sp.Rational(-1, 2), -1 + tau, sp.Rational(-1, 2)]

# regions: name -> (sign pattern of (x,1-x,y,1-y,y-x), which I_j gives A(R)=2 I_j)
regions = {
    'R1  x<y<0':      ((-1, +1, -1, +1, +1), 6),
    'R2  y<x<0':      ((-1, +1, -1, +1, -1), 5),
    'R3  x<0<y<1':    ((-1, +1, +1, +1, +1), 2),
    'R4  x<0,1<y':    ((-1, +1, +1, -1, +1), 4),
    'R5  y<0<x<1':    ((+1, +1, -1, +1, -1), 6),
    'R6  0<x<y<1':    ((+1, +1, +1, +1, +1), 1),
    'R7  0<y<x<1':    ((+1, +1, +1, +1, -1), 2),
    'R8  0<x<1<y':    ((+1, +1, +1, -1, +1), 3),
    'R9  y<0,1<x':    ((+1, -1, -1, +1, -1), 5),
    'R10 0<y<1<x':    ((+1, -1, +1, +1, -1), 1),
    'R11 1<x<y':      ((+1, -1, +1, -1, +1), 4),
    'R12 1<y<x':      ((+1, -1, +1, -1, -1), 3),
}

# consistency of the sign patterns with the verbal description (sample points)
samples = {
    'R1  x<y<0': (-2, -1), 'R2  y<x<0': (-1, -2), 'R3  x<0<y<1': (-1, .5), 'R4  x<0,1<y': (-1, 2),
    'R5  y<0<x<1': (.5, -1), 'R6  0<x<y<1': (.3, .6), 'R7  0<y<x<1': (.6, .3), 'R8  0<x<1<y': (.5, 2),
    'R9  y<0,1<x': (2, -1), 'R10 0<y<1<x': (2, .5), 'R11 1<x<y': (2, 3), 'R12 1<y<x': (3, 2)}
for k, (xx, yy) in samples.items():
    sg = tuple(int(sp.sign(v)) for v in (xx, 1 - xx, yy, 1 - yy, yy - xx))
    assert sg == regions[k][0], (k, sg)

# d=1 moment relations of the note (eq:KproofMomentRelations), at parameter tau
Ival = {3: I3, 4: I4, 1: c*I3 + s*I4, 5: s*I3 - c*I4, 2: s*I3, 6: s*I4}

total = 0
for k1, (s1, j1) in regions.items():
    for k2, (s2, j2) in regions.items():
        phi = sum(a[f] for f in range(5) if s1[f] != s2[f])
        total += sp.exp(sp.I*sp.pi*phi) * (2*Ival[j1]) * (2*Ival[j2])
I_rot = sp.Rational(-1, 4) * total          # (i/2)^2 = -1/4

target = 4*s**2*(I3**2 + I4**2)
diff = sp.expand(sp.expand_complex(sp.expand(I_rot - target)))
diff = sp.simplify(sp.expand_trig(diff))
print('region sum - 4 sin^2(pi tau)(I3^2+I4^2) =', diff)

# also the two-term KLT form: sin(pi a1) sin(pi b2) A(R6)A(R4) + sin(pi a2) sin(pi b1) A(R7)A(R9)
klt = sp.sin(sp.pi*a[0])*sp.sin(sp.pi*a[3])*(2*Ival[1])*(2*Ival[4]) + sp.sin(sp.pi*a[2])*sp.sin(sp.pi*a[1])*(2*Ival[2])*(2*Ival[5])
print('two-term KLT form - target =', sp.simplify(sp.expand(klt - target)))

# numerical spot checks of the identity at random tau and random I3, I4 (guards against simplify mistakes)
import random
for _ in range(5):
    tv = random.uniform(0.05, 0.95); i3 = random.uniform(-3, 3); i4 = random.uniform(-3, 3)
    v1 = complex(I_rot.subs({tau: tv, I3: i3, I4: i4}).evalf(30))
    v2 = complex(target.subs({tau: tv, I3: i3, I4: i4}).evalf(30))
    print(f'tau={tv:.4f}: region sum = {v1.real:+.15e}{v1.imag:+.2e}i, target = {v2.real:+.15e}, |diff| = {abs(v1-v2):.2e}')
