# Step 1: L3 = Ls_3(pi/2) and C212 = Cl_{2,1,2}(pi/2), each by two independent methods.
import mpmath as mp, time, json
DPS = 70
mp.mp.dps = DPS
pi = mp.pi
out = {}

# ---- L3 method A: defining integral (tanh-sinh), two subdivisions
t0 = time.time()
f = lambda th: mp.log(2*mp.sin(th/2))**2
L3a = -mp.quad(f, [0, pi/2])
L3b = -mp.quad(f, [0, mp.mpf('0.1'), mp.mpf('0.6'), pi/2])
print("L3 integral A", mp.nstr(L3a, 65)); print("L3 integral B", mp.nstr(L3b, 65), " diff", mp.nstr(L3a - L3b, 3), f"{time.time()-t0:.1f}s")
out['L3_quad'] = str(L3a)

# ---- Method B for both: Taylor stepping of the unipotent ODE system for the MPLs along 0 -> i
# components: 0:1, 1:Li1, 2:Li2, 3:Li_{1,2}, 4:Li_{1,1,2}, 5:Li_{2,1,2}, 6:Li_{1,1}, 7:Li_{2,1}
# derivatives: Li1'=1/(1-z); Li2'=Li1/z; Li12'=Li2/(1-z); Li112'=Li12/(1-z); Li212'=Li112/z; Li11'=Li1/(1-z); Li21'=Li11/z
OM0 = [(2, 1), (5, 4), (7, 6)]      # (target, source) with letter dz/z
OM1 = [(1, 0), (3, 2), (4, 3), (6, 1)]  # letter dz/(1-z)
NC = 8

def series_at(z, nmax):
    # direct series (|z|<1)
    Y = [mp.mpc(0)]*NC; Y[0] = mp.mpc(1)
    H1 = mp.mpf(0); H2 = mp.mpf(0); T = mp.mpf(0)  # H_{n-1}, H^{(2)}_{n-1}, T_{n-1}=sum_{k<n} H2_{k-1}/k
    zn = mp.mpc(1)
    for n in range(1, nmax + 1):
        zn *= z
        Y[1] += zn/n; Y[2] += zn/n**2
        Y[3] += zn/n*H2; Y[4] += zn/n*T; Y[5] += zn/n**2*T
        Y[6] += zn/n*H1; Y[7] += zn/n**2*H1
        # update to n
        T += H2/n
        H1 += mp.mpf(1)/n; H2 += mp.mpf(1)/n**2
    return Y

def taylor_step(z0, Y0, h, kmax):
    # coefficients of Y(z0+h') in h'
    c0 = [(-1)**k/z0**(k + 1) for k in range(kmax + 1)]
    c1 = [1/(1 - z0)**(k + 1) for k in range(kmax + 1)]
    Yk = [list(Y0)]
    for k in range(kmax):
        new = [mp.mpc(0)]*NC
        for j in range(k + 1):
            src = Yk[k - j]
            for (tgt, sc) in OM0:
                new[tgt] += c0[j]*src[sc]
            for (tgt, sc) in OM1:
                new[tgt] += c1[j]*src[sc]
        Yk.append([v/(k + 1) for v in new])
    res = [mp.mpc(0)]*NC
    hp = mp.mpc(1)
    for k in range(kmax + 1):
        for i in range(NC):
            res[i] += Yk[k][i]*hp
        hp *= h
    return res, Yk

def path_value(nser, kmax, pts):
    Y = series_at(pts[0], nser)
    for a, b in zip(pts[:-1], pts[1:]):
        Y, Yk = taylor_step(a, Y, b - a, kmax)
    return Y

t0 = time.time()
I = mp.mpc(0, 1)
pts1 = [I/2, 3*I/4, I]
YA = path_value(260, 300, pts1)
pts2 = [mp.mpc('0.3', '0.3'), mp.mpc('0.2', '0.65'), I]   # different path, also checks branch consistency
YB = path_value(260, 300, pts2)
print(f"ODE stepping {time.time()-t0:.1f}s")
D3a = YA[7].imag; D3b = YB[7].imag
D5a = YA[5].real; D5b = YB[5].real
print("D3 path1", mp.nstr(D3a, 65)); print("D3 path2", mp.nstr(D3b, 65))
print("D5 path1", mp.nstr(D5a, 65)); print("D5 path2", mp.nstr(D5b, 65))
L3_ode = -2*(D3a + 7*pi**3/192)
print("L3 from D3 = -L3/2 - 7pi^3/192:", mp.nstr(L3_ode, 65), " diff vs quad", mp.nstr(L3_ode - L3a, 3))
# sanity: Li2(i) = -pi^2/48 + i G
print("Li2(i) check", mp.nstr(YA[2] - mp.mpc(-pi**2/48, mp.catalan), 3), " Li11 check", mp.nstr(YA[6] - mp.log(1 - I)**2/2, 3))
out['D3_ode'] = str(D3a); out['D5_ode'] = str(D5a); out['L3_ode'] = str(L3_ode)

# ---- C212 method C: alternating series over even n=2j: sum_j (-1)^j S(2j-1)/(4 j^2),
#      S(N) = sum_{m<=N} (1/m) H^{(2)}_{m-1}; Cohen-Villegas-Zagier acceleration
t0 = time.time()
def terms(J):
    a = []
    S = mp.mpf(0); H2 = mp.mpf(0)  # running
    m = 0
    for j in range(1, J + 1):
        N = 2*j - 1
        while m < N:
            m += 1
            S += H2/m          # uses H^{(2)}_{m-1}
            H2 += mp.mpf(1)/m**2
        a.append(S/(4*j**2))
    return a  # a[j-1] for j=1..J; series sum_j (-1)^j a_j

def cvz(a, n):
    # sum_{k>=0} (-1)^k a[k]  (Cohen-Rodriguez Villegas-Zagier, Algorithm 1)
    d = (3 + mp.sqrt(8))**n; d = (d + 1/d)/2
    b = mp.mpf(-1); c = -d; s = mp.mpf(0)
    for k in range(n):
        c = b - c
        s = s + c*a[k]
        b = (k + n)*(k - n)*b/((k + mp.mpf(1)/2)*(k + 1))
    return s/d

a = terms(400)
# series = sum_{j>=1} (-1)^j a_j = - sum_{k>=0} (-1)^k a[k]
for n in (60, 80, 100, 120):
    print("C212 CVZ n=%d" % n, mp.nstr(-cvz(a, n), 65))
C212_cvz = -cvz(a, 120)
# method D: partial sums with repeated averaging (Euler/van Wijngaarden style) on the raw partial sums
ps = []; s = mp.mpf(0)
for j, aj in enumerate(a, start=1):
    s += (-1)**j*aj; ps.append(s)
row = ps[-200:]
for it in range(150):
    row = [(row[i] + row[i + 1])/2 for i in range(len(row) - 1)]
print("C212 repeated averaging of partial sums 201..400 (150 passes):", mp.nstr(row[-1], 65), "spread", mp.nstr(max(row) - min(row), 3))
print(f"series {time.time()-t0:.1f}s")
out['C212_cvz'] = str(C212_cvz); out['C212_avg'] = str(row[-1])
json.dump(out, open('polylog_out.json', 'w'), indent=1)
