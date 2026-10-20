# Step 4: 1D reduced forms of the bivariate values, high precision (mpmath).
import mpmath as mp, time, json, sys
from params import setup
from kernels import N_alpha, N_p, Psi_sig, Pt
DPS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
P = setup(DPS + 10)
mp.mp.dps = DPS + 10
pi = mp.pi
out = {}
def line(F, pts=(0, 1, 3, 8, 20, 60, mp.inf)):
    # B_{1/4}[F] = (1/pi) int_0^inf Re F(1/4+iu) du  (conjugation symmetry)
    return mp.quad(lambda u: mp.re(F(mp.mpc(0.25, u))), list(pts))/pi
def chk(F, label):
    t0 = time.time()
    v1 = line(F); v2 = line(F, (0, 0.5, 2, 5, 12, 40, 150, mp.inf))
    # conj symmetry check at a point
    s = mp.mpc(0.25, 1.7)
    cs = abs(F(mp.conj(s)) - mp.conj(F(s)))/abs(F(s))
    print(f"{label:34s} {mp.nstr(v1, DPS)}  [subdiv diff {mp.nstr(v1-v2, 2)}, conj-sym {mp.nstr(cs, 2)}] {time.time()-t0:.1f}s", flush=True)
    return v1

d = lambda s: mp.psi(1, 0.5 - s) - mp.psi(1, 1 - s)
HW = pi*chk(lambda s: N_alpha(s, P['alphaW'])*d(s), "B[N_aW d]")
print("H_W = pi B[N_aW d]                =", mp.nstr(HW, DPS))
print("W0 = sqrt89/pi^2 H_W              =", mp.nstr(mp.sqrt(89)/pi**2*HW, DPS))
Psi = lambda s: mp.digamma(1 - 2*s) + mp.euler
H7 = chk(lambda s: N_p(s, P['beta7'])*Psi(s), "B[N_p Psi]")/pi
print("H7 = B[N_p Psi]/pi                =", mp.nstr(H7, DPS))
out.update(H_W_1d=str(HW), H7_1d=str(H7), W0_from_HW=str(mp.sqrt(89)/pi**2*HW))

# inner-identity spot checks at sample s (eq:wheelinner and eq:seventhinner)
for s in (mp.mpc(0.25, 0.6), mp.mpc(0.25, -2.2)):
    inner = mp.quad(lambda w: Pt(mp.mpc(1/8., w))/(0.5 - s - mp.mpc(1/8., w))**2, [-mp.inf, -3, 0, 3, mp.inf])/(2*pi)
    print("eq:wheelinner  B_{1/8}[P/(1/2-s-t)^2] / (pi d(s)) - 1 =", mp.nstr(inner/(pi*d(s)) - 1, 3), " at s =", s)
    # cot(2 pi v) -> -/+ i at +/- infinity: subtract the sign part and do it analytically by quad on the rational part
    g = lambda w: mp.cot(2*pi*mp.mpc(1/16., w))/((0.5 - mp.mpc(1/16., w))*(0.5 - s - mp.mpc(1/16., w)))
    inner7 = mp.quad(g, [-mp.inf, -20, -3, 0, 3, 20, mp.inf])/(2*pi)
    print("eq:seventhinner B_{1/16}[cot/((1/2-v)(1/2-s-v))] / (-Psi/(pi s)) - 1 =", mp.nstr(inner7/(-Psi(s)/(pi*s)) - 1, 3))

# primitive: elliptic forms of g_j, check against Meijer G at a sample point
def gj(x):
    m = x/(2*(1 + mp.sqrt(1 - x)))
    K = mp.ellipk(m); Kc = mp.ellipk(1 - m)
    c = pi**mp.mpf(1.5)
    return (4*K**2/c, 4*K*Kc/c, 2*(Kc**2 - K**2)/c)
mp.mp.dps = 25
xs = mp.mpf('0.3')
gm = [mp.meijerg([[0.5]*(3 - j), [0.5]*j], [[0]*j, [0]*(3 - j)], xs) for j in (1, 2, 3)]
print("g_j(0.3) elliptic vs meijerg rel diffs:", [mp.nstr(abs(a - b)/abs(b), 2) for a, b in zip(gj(xs), gm)])
# Gauss-function identities v=2K/pi, sqrtQ h(1-x) = 2(K+Kc)
m = xs/(2*(1 + mp.sqrt(1 - xs))); K = mp.ellipk(m); Kc = mp.ellipk(1 - m); Q = mp.gamma(0.25)**4/pi
print("v(x)-2K/pi:", mp.nstr(mp.hyp2f1(0.25, 0.25, 1, xs) - 2*K/pi, 2), " sqrtQ h(1-x) - 2(K+Kc):", mp.nstr(mp.sqrt(Q)*mp.hyp2f1(0.25, 0.25, 0.5, 1 - xs) - 2*(K + Kc), 2))
json.dump(out, open(f'reduced1d_{DPS}.json', 'w'), indent=1)
# (primitive pairing moved to primitive1d.py: endpoint-safe version)
