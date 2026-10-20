// Numerical engine for the n-bubble connected Mayer cluster J_n(K, delta) of the 1D kink gas, analytically continued
// in K. Input: sector/term file from cluster_gen.py. Output: per sector, the angular integrals A^{(k)}_j such that
//   J^{(k)}(K) = sum_j Gamma^{(j)}(alpha) A^{(k)}_j(K),  alpha = 2n - 1 - 2nK,
// k = delta order (0, 1), j = power of the radial log (D).
//
// Continuation (per sector variable t with exponent c = a + b w, w = 1 - K): [0,1] = [tau,1] U [0,tau].
//   [tau,1]: Gauss-Legendre in y, t = tau^y (no subtraction, no point closer than tau to the boundary);
//   [0,tau]: the integrand without t^c is analytic in |t| < R (R > tau): trapezoid rule on |t| = tau gives its Taylor
//   coefficients, integrated analytically: int_0^tau t^{c+n} log^p t dt = d^p/dc^p [tau^{c+n+1}/(c+n+1)],
//   folded into complex node weights W_m(c, p). Log insertions log t of a circle variable are kept symbolic (lambda).
// Variables whose exponent is a non-negative integer for every term and that carry no log insertion: plain GL on [0,1].
//
// Modes: 'cx' (fixed complex K, all arithmetic complex double-double) and 'ser' (truncated Laurent series in w; the
// Laurent coefficients of A_j are computed directly).
#include "dd.h"
#include "sha256.h"
#include <unistd.h>
#include <cmath>
#include <vector>
#include <array>
#include <string>
#include <fstream>
#include <sstream>
#include <iostream>
#include <cstring>
#include <cstdlib>
#include <chrono>
#include <algorithm>
#include <functional>
#ifdef _OPENMP
#include <omp.h>
#else
static inline int omp_get_max_threads() { return 1; }
static inline int omp_get_thread_num() { return 0; }
#endif
using namespace std;
#ifdef USE_DOUBLE
typedef double R;     // plain double build (fast, ~15 digits): for cost/precision studies
#else
typedef dd R;
#endif
typedef cx<R> C;
[[maybe_unused]] static inline double HI(const dd &x) { return x.hi; }
[[maybe_unused]] static inline double LO(const dd &x) { return x.lo; }
[[maybe_unused]] static inline double HI(double x) { return x; }
[[maybe_unused]] static inline double LO(double) { return 0.0; }
#ifdef USE_DOUBLE
static const R RPI = M_PI;
#else
static const R RPI = DD_PI;
#endif

static const int MAXD = 6;      // max sector variables (n = 4: 6)
static const int MAXE = 12;     // max monomial exponent

// ------------------------------------------------------------------ data
struct IntervalD { vector<int> M; vector<vector<int>> red; vector<int> deps; };
struct TermD {
    int coef; vector<pair<int, int>> pairs; vector<int> far; vector<int> a, b;
    // precomputed log-insertion integer sums
    int nu[MAXD]; int kap[MAXD][MAXD];
};
struct FarD { int ra, rb, g, gra, grb, tot; vector<int> la, lb; };
struct SectorD {
    int pat; vector<int> jac; vector<int> plain0, plain1; vector<double> Rk;
    vector<IntervalD> iv; vector<int> Ms; vector<vector<int>> sred; vector<int> scoef;
    vector<TermD> terms; vector<FarD> fars; int maxe;
};
struct PatternD { vector<int> q; int factor; };
int NB, NK, NG, D, NINT;
vector<PatternD> pats;
vector<SectorD> secs;

static void load(const string &fn) {
    ifstream f(fn);
    if (!f) { cerr << "cannot open " << fn << endl; exit(1); }
    string tok; int npat;
    f >> tok >> NB >> tok >> NINT >> tok >> npat;
    NK = 2 * NB; NG = NK - 1; D = NG - 1;
    vector<pair<int, int>> ivs;
    for (int i = 0; i < NK; ++i) for (int j = i + 1; j < NK; ++j) ivs.push_back({i, j});
    for (int p = 0; p < npat; ++p) {
        PatternD P; f >> tok; P.q.resize(NK);
        for (int i = 0; i < NK; ++i) f >> P.q[i];
        int nsec; f >> tok >> P.factor >> tok >> nsec;
        pats.push_back(P);
        for (int s = 0; s < nsec; ++s) {
            SectorD S; S.pat = p; S.jac.resize(D); S.plain0.resize(D); S.plain1.resize(D);
            f >> tok; for (int k = 0; k < D; ++k) f >> S.jac[k];
            f >> tok; for (int k = 0; k < D; ++k) f >> S.plain0[k];
            f >> tok; for (int k = 0; k < D; ++k) f >> S.plain1[k];
            S.Rk.resize(D); f >> tok; for (int k = 0; k < D; ++k) f >> S.Rk[k];
            S.maxe = 0;
            S.iv.resize(NINT);
            for (int I = 0; I < NINT; ++I) {
                f >> tok; S.iv[I].M.resize(D);
                for (int k = 0; k < D; ++k) f >> S.iv[I].M[k];
                int nr; f >> nr; S.iv[I].red.assign(nr, vector<int>(D));
                for (int r = 0; r < nr; ++r) for (int k = 0; k < D; ++k) { f >> S.iv[I].red[r][k]; S.maxe = max(S.maxe, S.iv[I].red[r][k]); }
            }
            f >> tok; S.Ms.resize(D); for (int k = 0; k < D; ++k) f >> S.Ms[k];
            int nr; f >> nr; S.sred.assign(nr, vector<int>(D)); S.scoef.resize(nr);
            for (int r = 0; r < nr; ++r) { for (int k = 0; k < D; ++k) { f >> S.sred[r][k]; S.maxe = max(S.maxe, S.sred[r][k]); } f >> S.scoef[r]; }
            int nt; f >> tok >> nt;
            for (int t = 0; t < nt; ++t) {
                TermD T; int np, nf; f >> tok >> T.coef >> np;
                T.pairs.resize(np);
                for (int i = 0; i < np; ++i) f >> T.pairs[i].first >> T.pairs[i].second;
                f >> nf;
                for (int i = 0; i < nf; ++i) {
                    FarD F; f >> F.ra >> F.rb >> F.g >> F.gra >> F.grb >> F.tot;
                    int found = -1;
                    for (size_t j = 0; j < S.fars.size(); ++j) if (S.fars[j].ra == F.ra && S.fars[j].rb == F.rb) found = j;
                    if (found < 0) {
                        F.la.resize(D); F.lb.resize(D);
                        for (int k = 0; k < D; ++k) {
                            F.la[k] = S.iv[F.ra].M[k] - S.iv[F.g].M[k]; F.lb[k] = S.iv[F.rb].M[k] - S.iv[F.g].M[k];
                            if (F.la[k] < 0 || F.lb[k] < 0) { cerr << "bad far lead" << endl; exit(1); }
                            S.maxe = max(S.maxe, max(F.la[k], F.lb[k]));
                        }
                        S.fars.push_back(F); found = S.fars.size() - 1;
                    }
                    T.far.push_back(found);
                }
                f >> tok; T.a.resize(D); for (int k = 0; k < D; ++k) f >> T.a[k];
                f >> tok; T.b.resize(D); for (int k = 0; k < D; ++k) f >> T.b[k];
                for (int k = 0; k < D; ++k) {
                    T.nu[k] = 0;
                    for (auto &pq : T.pairs) T.nu[k] += pq.second * (S.iv[pq.first].M[k] - S.Ms[k]);
                    for (int l = 0; l < D; ++l) {
                        T.kap[k][l] = 0;
                        for (auto &pq : T.pairs) T.kap[k][l] += pq.second * (S.iv[pq.first].M[k] - S.Ms[k]) * (S.iv[pq.first].M[l] - S.Ms[l]);
                    }
                }
                S.terms.push_back(T);
            }
            if (S.maxe >= MAXE) { cerr << "MAXE too small " << S.maxe << endl; exit(1); }
            secs.push_back(S);
        }
    }
}

// ------------------------------------------------------------------ Gauss-Legendre on [0,1] in double-double
static void gauss_legendre(int n, vector<R> &x, vector<R> &w) {
    x.resize(n); w.resize(n);
    for (int i = 0; i < n; ++i) {
        R z(std::cos(M_PI * (i + 0.75) / (n + 0.5))), pp;
        for (int it = 0; it < 100; ++it) {
            R p1(1.0), p2(0.0);
            for (int j = 1; j <= n; ++j) {
                R p3 = p2; p2 = p1;
                p1 = ((2.0 * j - 1.0) * z * p2 - (j - 1.0) * p3) / R(double(j));
            }
            pp = R(double(n)) * (z * p1 - p2) / (z * z - 1.0);
            R dz = p1 / pp;
            z = z - dz;
            if (std::fabs(to_double(dz)) < 1e-33 || (sizeof(R) == sizeof(double) && it > 30)) break;
        }
        x[i] = (1.0 - z) * 0.5;
        w[i] = R(1.0) / ((1.0 - z * z) * pp * pp) * 2.0 * 0.5;
    }
}

// ------------------------------------------------------------------ series arithmetic (mode 'ser')
#ifndef LS
#define LS 11
#endif
#ifndef VMIN
#define VMIN (-6)
#endif
struct Ser { C c[LS]; };          // Taylor series in w, coefficients of w^0..w^{LS-1}
struct Lau { int v; Ser s; };      // w^{-v} * s
static inline Ser operator+(const Ser &a, const Ser &b) { Ser r; for (int i = 0; i < LS; ++i) r.c[i] = a.c[i] + b.c[i]; return r; }
static inline Ser operator*(const Ser &a, const C &x) { Ser r; for (int i = 0; i < LS; ++i) r.c[i] = a.c[i] * x; return r; }
static inline Ser operator*(const Ser &a, const Ser &b) {
    Ser r;
    for (int i = 0; i < LS; ++i) {
        C acc;
        for (int j = 0; j <= i; ++j) acc += a.c[j] * b.c[i - j];
        r.c[i] = acc;
    }
    return r;
}
static inline Ser ser_const(const C &x) { Ser r; r.c[0] = x; return r; }
struct InvTable { R v[64]; InvTable() { for (int i = 1; i < 64; ++i) v[i] = R(1.0) / R(double(i)); } };
static const InvTable INV;
// e^{A + B w}
static inline Ser ser_expAB(const C &A, const C &B) {
    Ser r; C e = cexp(A); r.c[0] = e;
    for (int i = 1; i < LS; ++i) r.c[i] = r.c[i - 1] * B * INV.v[i];
    return r;
}

// ------------------------------------------------------------------ modes
struct ModeCx {
    typedef C V; typedef C W;
    C w, K;
    V expAB(const C &A, const C &B) const { return cexp(A + B * w); }
    V Kv() const { return K; }
    V mulK(const V &a) const { return a * K; }
    // G~ = expm1(2K lz)/l_z, given gt = lz/l_z
    V Gt(const C &lz, const C &gt) const { C y = lz * (K * R(2.0)); return cexpm1_over(y) * (K * R(2.0)) * gt; }
    V Cf(const C &lz) const { return cexp(lz * (K * R(2.0))); }
    static V mulc(const V &a, const C &x) { return a * x; }
    static V mul(const V &a, const V &b) { return a * b; }
    static V add(const V &a, const V &b) { return a + b; }
    static W wmulc(const W &a, const C &x) { return a * x; }
    static W wmul(const W &a, const W &b) { return a * b; }
    static W wadd(const W &a, const W &b) { return a + b; }
    static W wzero() { return C(); }
    static W wconst(const C &x) { return x; }
    static void realpart(W &x) { x.im = R(0.0); }
    // circle weight W_m(c, p) = (1/M) sum_n e^{-i n th} d^p/dc^p [tau^{c+1}/(c+n+1)]
    W circle(int a, int b, int p, const C &eith, int M, const R & /*tau*/, const R &ltau) const {
        C c = C(R(double(a))) + w * R(double(b));
        C tc1 = cexp((c + C(R(1.0))) * ltau);
        C sum, ph(R(1.0)), eim = conj(eith);
        for (int nn = 0; nn < M; ++nn) {
            C den = c + C(R(double(nn + 1))), inv = C(R(1.0)) / den, invp = inv, acc;
            double fac = 1.0;
            for (int j = 0; j <= p; ++j) {
                double bin = 1.0; for (int q = 0; q < j; ++q) bin = bin * (p - q) / (q + 1);
                R lt(1.0); for (int q = 0; q < p - j; ++q) lt = lt * ltau;
                acc += invp * (lt * R(bin * fac * ((j % 2) ? -1.0 : 1.0)));
                invp = invp * inv; fac *= (j + 1);
            }
            sum += ph * acc;
            ph = ph * eim;
        }
        return sum * tc1 / R(double(M));
    }
};

struct AccSer { C c[LS]; };   // window: w^{VMIN} .. w^{VMIN+LS-1}
struct ModeSer {
    typedef Ser V; typedef Lau W;
    V expAB(const C &A, const C &B) const { return ser_expAB(A, B); }
    V Kv() const { Ser r; r.c[0] = C(R(1.0)); r.c[1] = C(R(-1.0)); return r; }
    V mulK(const V &a) const { Ser r; r.c[0] = a.c[0]; for (int i = 1; i < LS; ++i) r.c[i] = a.c[i] - a.c[i - 1]; return r; }
    // G~(w) = 2 gt expm1_over(2 lz) + e^{2 lz} gt sum_{n>=1} (-2)^n lz^{n-1} w^n / n!
    V Gt(const C &lz, const C &gt) const {
        Ser r; C l2 = lz * R(2.0);
        r.c[0] = cexpm1_over(l2) * gt * R(2.0);
        C e = cexp(l2) * gt, term(R(1.0));   // term = (-2)^n lz^{n-1}/n!
        for (int i = 1; i < LS; ++i) {
            if (i == 1) term = C(R(-2.0));
            else term = term * lz * (INV.v[i] * R(-2.0));
            r.c[i] = e * term;
        }
        return r;
    }
    V Cf(const C &lz) const { C l2 = lz * R(2.0); return ser_expAB(l2, -l2); }
    static V mulc(const V &a, const C &x) { return a * x; }
    static V mul(const V &a, const V &b) { return a * b; }
    static V add(const V &a, const V &b) { return a + b; }
    static W wmulc(const W &a, const C &x) { W r = a; r.s = a.s * x; return r; }
    static W wmul(const W &a, const W &b) { W r; r.v = a.v + b.v; r.s = a.s * b.s; return r; }
    static W wadd(const W &a, const W &b) {
        // align to the larger pole order
        if (a.v == b.v) { W r; r.v = a.v; r.s = a.s + b.s; return r; }
        const W &hi = a.v > b.v ? a : b, &lo = a.v > b.v ? b : a;
        int sh = hi.v - lo.v; W r = hi;
        for (int i = sh; i < LS; ++i) r.s.c[i] += lo.s.c[i - sh];
        return r;
    }
    static W wzero() { W r; r.v = 0; return r; }
    static W wconst(const C &x) { W r; r.v = 0; r.s = ser_const(x); return r; }
    static void realpart(W &x) { for (int i = 0; i < LS; ++i) x.s.c[i].im = R(0.0); }
    W circle(int a, int b, int p, const C &eith, int M, const R & /*tau*/, const R &ltau) const {
        // tau^{c+1} = tau^{a+1} e^{b ltau w}
        Ser tc1 = ser_expAB(C(ltau * R(double(a + 1))), C(ltau * R(double(b))));
        // sum over n of e^{-i n th} * sum_j binom(p,j) ltau^{p-j} (-1)^j j! (c+n+1)^{-(j+1)}
        int vmax = 0; int n0 = -a - 1;
        if (n0 >= 0 && n0 < M) { if (b == 0) { cerr << "pole with b=0" << endl; exit(1); } vmax = p + 1; }
        W tot; tot.v = vmax;
        C ph(R(1.0)), eim = conj(eith);
        for (int nn = 0; nn < M; ++nn) {
            double A0 = a + nn + 1;   // c + n + 1 = A0 + b w
            for (int j = 0; j <= p; ++j) {
                double bin = 1.0; for (int q = 0; q < j; ++q) bin = bin * (p - q) / (q + 1);
                double fac = 1.0; for (int q = 2; q <= j; ++q) fac *= q;
                R lt(1.0); for (int q = 0; q < p - j; ++q) lt = lt * ltau;
                C coef = C(lt * R(bin * fac * ((j % 2) ? -1.0 : 1.0))) * ph;
                // (A0 + b w)^{-(j+1)} as w^{-vmax} * series
                Ser s;
                if (nn == n0) {
                    // (b w)^{-(j+1)}: shift by vmax - (j+1)
                    R bj(1.0); for (int q = 0; q <= j; ++q) bj = bj * R(double(b));
                    int pos = vmax - (j + 1);
                    if (pos < LS) s.c[pos] = C(R(1.0) / bj);
                } else {
                    // A0^{-(j+1)} (1 + (b/A0) w)^{-(j+1)} = sum_m binom(-(j+1), m) (b/A0)^m w^m
                    R base = R(1.0); for (int q = 0; q <= j; ++q) base = base / R(A0);
                    R x = R(double(b)) / R(A0), term = base;
                    for (int m = 0; m + vmax < LS; ++m) {
                        s.c[m + vmax] = C(term);
                        term = term * x * R(-double(j + 1 + m)) / R(double(m + 1));
                    }
                }
                for (int i = 0; i < LS; ++i) tot.s.c[i] += s.c[i] * coef;
            }
            ph = ph * eim;
        }
        tot.s = tot.s * tc1;
        tot.s = tot.s * C(R(1.0) / R(double(M)));
        return tot;
    }
};

// ------------------------------------------------------------------ parameters
struct Params {
    int kmax = 1; double tau = 0.1; double taurat = 0.1, plainR = 0.3; int nseg = 24, mcirc = 32, nplain = 30;
    string mode = "cx"; double Kre = 0.3, Kim = 0.0; R Kd[2] = {R(0.3), R(0.0)};
    int sec0 = 0, sec1 = -1; int conj = -1; int generic = 0;   // conj: use conjugate symmetry of circle nodes (-1: auto)
};

// ------------------------------------------------------------------ per-sector integration
template <class Mode> static typename Mode::W mulVW(const typename Mode::V &v, const typename Mode::W &w);
template <> C mulVW<ModeCx>(const C &v, const C &w) { return v * w; }
template <> Lau mulVW<ModeSer>(const Ser &v, const Lau &w) { Lau r; r.v = w.v; r.s = v * w.s; return r; }

template <class Mode> struct Integrator {
    typedef typename Mode::V V; typedef typename Mode::W W;
    const Mode &mode; const Params &P; const SectorD &S; int kmax;
    int vtype[MAXD];                       // 0 plain, 1 split
    vector<R> gx, gw, px, pw;              // segment GL (in y), plain GL
    vector<R> segt[MAXD], seglogt[MAXD], segw[MAXD];   // segment nodes per variable: t = tau_k^y, log t, weight
    vector<R> plainlogt;
    R tauk[MAXD], ltauk[MAXD]; int M;
    vector<C> eith;                        // circle phases e^{i theta_m}
    vector<vector<vector<array<W, 5>>>> cw; // circle weights [term][var][m][p]
    unsigned ivmask[64], smask, farmask[16]; bool conjsym;
    Integrator(const Mode &m, const Params &p, const SectorD &s, bool cj) : mode(m), P(p), S(s), conjsym(cj) {
        kmax = P.kmax;
        if (conjsym && (P.mcirc % 2)) { cerr << "conjugate symmetry needs even m" << endl; exit(1); }
        for (int k = 0; k < D; ++k) vtype[k] = ((kmax == 0 ? S.plain0[k] : S.plain1[k]) && S.Rk[k] >= P.plainR) ? 0 : 1;
        gauss_legendre(P.nseg, gx, gw); gauss_legendre(P.nplain, px, pw);
        M = P.mcirc;
        for (int k = 0; k < D; ++k) {
            double tk = std::min(P.tau, P.taurat * S.Rk[k]);
            tauk[k] = R(tk); ltauk[k] = log(tauk[k]);
            for (int i = 0; i < P.nseg; ++i) {
                R tt = exp(gx[i] * ltauk[k]); segt[k].push_back(tt); seglogt[k].push_back(gx[i] * ltauk[k]); segw[k].push_back(gw[i] * tt * (-ltauk[k]));
            }
        }
        for (int i = 0; i < P.nplain; ++i) plainlogt.push_back(log(px[i]));
        eith.resize(M);
        for (int mm = 0; mm < M; ++mm) {
            R th = RPI * R(2.0 * mm + 1.0) / R(double(M)); R sn, cs; sincos(th, sn, cs); eith[mm] = C(cs, sn);
        }
        int pmax = 2 * kmax;
        cw.resize(S.terms.size());
        for (size_t t = 0; t < S.terms.size(); ++t) {
            cw[t].resize(D);
            for (int k = 0; k < D; ++k) {
                if (!vtype[k]) continue;
                cw[t][k].resize(M);
                for (int mm = 0; mm < M; ++mm)
                    for (int pp = 0; pp <= pmax; ++pp)
                        cw[t][k][mm][pp] = mode.circle(S.terms[t].a[k], S.terms[t].b[k], pp, eith[mm], M, tauk[k], ltauk[k]);
            }
        }
        auto vmask = [&](const vector<int> &e) { unsigned r = 0; for (int k = 0; k < D; ++k) if (e[k]) r |= 1u << k; return r; };
        for (int I = 0; I < NINT; ++I) { ivmask[I] = 0; for (auto &r : S.iv[I].red) ivmask[I] |= vmask(r); }
        smask = 0; for (auto &r : S.sred) smask |= vmask(r);
        for (size_t f = 0; f < S.fars.size(); ++f) {
            const FarD &F = S.fars[f];
            farmask[f] = ivmask[F.ra] | ivmask[F.rb] | ivmask[F.g] | ivmask[F.gra] | ivmask[F.grb] | ivmask[F.tot] | vmask(F.la) | vmask(F.lb);
        }
    }
    struct Acc { W v[3][5]; };

    // per-thread evaluation state for one region
    struct State {
        const Integrator *I; unsigned circ; int isc[MAXD], A[MAXD], nA; double wfac = 1.0;
        C t[MAXD]; R logt[MAXD], wk[MAXD]; int mi[MAXD], mic[MAXD];   // mic: circle indices of the current block
        C tp[MAXD][MAXE]; R tpr[MAXD][MAXE];
        C reg[64], lr[64], ell[64]; C regs, lrs;
        struct FarV { C lz, gt, T2t, T3t, l; } fv[16];
        vector<W> Wc0; vector<array<W, MAXD>> Wc1; vector<array<array<W, MAXD>, MAXD>> Wc2;
        void init(const Integrator *In, unsigned circmask) {
            I = In; circ = circmask; nA = 0;
            for (int k = 0; k < D; ++k) { isc[k] = (circ >> k) & 1; if (isc[k]) A[nA++] = k; }
            size_t nt = I->S.terms.size();
            Wc0.resize(nt); Wc1.resize(nt); Wc2.resize(nt);
        }
        void setvar(int k, int i) {
            mi[k] = 0;
            if (!I->vtype[k]) { t[k] = C(I->px[i]); logt[k] = I->plainlogt[i]; wk[k] = I->pw[i]; }
            else if (isc[k]) { t[k] = I->eith[i] * I->tauk[k]; mi[k] = i; logt[k] = R(0.0); wk[k] = R(1.0); }
            else { t[k] = C(I->segt[k][i]); logt[k] = I->seglogt[k][i]; wk[k] = I->segw[k][i]; }
            tp[k][0] = C(R(1.0)); tpr[k][0] = R(1.0);
            if (isc[k]) for (int e = 1; e <= I->S.maxe; ++e) tp[k][e] = tp[k][e - 1] * t[k];
            else for (int e = 1; e <= I->S.maxe; ++e) { tpr[k][e] = tpr[k][e - 1] * t[k].re; tp[k][e] = C(tpr[k][e]); }
        }
        C mono(const vector<int> &e) const { C r(R(1.0)); for (int k = 0; k < D; ++k) if (e[k]) r = r * tp[k][e[k]]; return r; }
        R monor(const vector<int> &e) const { R r(1.0); for (int k = 0; k < D; ++k) if (e[k]) r = r * tpr[k][e[k]]; return r; }
        // recompute everything that depends on the variables in chg
        void update(unsigned chg, bool all = false) {
            const SectorD &S = I->S;
            for (int Iv = 0; Iv < NINT; ++Iv) {
                if (!all && !(I->ivmask[Iv] & chg)) continue;
                if (I->ivmask[Iv] & circ) {
                    C s; for (auto &r : S.iv[Iv].red) s += mono(r);
                    reg[Iv] = s; lr[Iv] = cxlog(s);
                } else {
                    R s(0.0); for (auto &r : S.iv[Iv].red) s += monor(r);
                    reg[Iv] = C(s); lr[Iv] = C(log(s));
                }
            }
            if (all || (I->smask & chg)) {
                if (I->smask & circ) {
                    C s; for (size_t r = 0; r < S.sred.size(); ++r) s += mono(S.sred[r]) * R(double(S.scoef[r]));
                    regs = s; lrs = cxlog(s);
                } else {
                    R s(0.0); for (size_t r = 0; r < S.sred.size(); ++r) s += monor(S.sred[r]) * R(double(S.scoef[r]));
                    regs = C(s); lrs = C(log(s));
                }
            }
            if (I->kmax >= 1)
                for (int Iv = 0; Iv < NINT; ++Iv) {
                    C v = lr[Iv] - lrs;
                    for (int k = 0; k < D; ++k) if (!isc[k]) { int mu = S.iv[Iv].M[k] - S.Ms[k]; if (mu) v += C(logt[k] * R(double(mu))); }
                    ell[Iv] = v;
                }
            for (size_t f = 0; f < S.fars.size(); ++f) {
                if (!all && !(I->farmask[f] & chg)) continue;
                const FarD &F = S.fars[f];
                C la = mono(F.la), lb = mono(F.lb);
                C qa = reg[F.ra] / reg[F.g], qb = reg[F.rb] / reg[F.g];
                C regz = qa * qb * reg[F.g] / reg[F.tot];
                C z = la * lb * regz;
                C lo = clog1p_over(z);
                fv[f].lz = lo * z; fv[f].gt = lo * regz;
                if (I->kmax >= 1) {
                    C rhoa = la * qa, rhob = lb * qb;
                    C qa2 = reg[F.ra] / reg[F.grb], qb2 = reg[F.rb] / reg[F.gra];
                    C rhoa2 = la * qa2, rhob2 = lb * qb2;
                    C at = clog1p_over(rhoa) * qa, bt = clog1p_over(rhob) * qb;
                    C at2 = clog1p_over(rhoa2) * qa2, bt2 = clog1p_over(rhob2) * qb2;
                    if (to_double(abs2(rhoa)) <= to_double(abs2(rhob)))
                        fv[f].T2t = at * fv[f].gt * la - bt * at2 - at2 * bt2;
                    else
                        fv[f].T2t = bt * fv[f].gt * lb - at * bt2 - at2 * bt2;
                    fv[f].l = la * lb;
                    if (I->kmax >= 2)   // T3/(la lb) = gt lz^2 - 3 (alpha + beta) alpha'/la beta'/lb  (stable)
                        fv[f].T3t = fv[f].gt * fv[f].lz * fv[f].lz - (at * la + bt * lb) * at2 * bt2 * R(3.0);
                }
            }
            if (all || (chg & circ)) for (int k = 0; k < D; ++k) mic[k] = mi[k];
            if (!I->P.generic && (all || (chg & circ))) {
                // circle-weight products per term (without the scalar segment/plain weights)
                for (size_t ti = 0; ti < S.terms.size(); ++ti) {
                    const auto &cw = I->cw[ti];
                    W w0 = Mode::wconst(C(R(wfac)));
                    for (int i = 0; i < nA; ++i) w0 = Mode::wmul(w0, cw[A[i]][mi[A[i]]][0]);
                    Wc0[ti] = w0;
                    if (I->kmax >= 1)
                        for (int i = 0; i < nA; ++i) {
                            W x = Mode::wconst(C(R(wfac)));
                            for (int j = 0; j < nA; ++j) x = Mode::wmul(x, cw[A[j]][mi[A[j]]][j == i ? 1 : 0]);
                            Wc1[ti][i] = x;
                            for (int i2 = i; i2 < nA; ++i2) {
                                W y = Mode::wconst(C(R(wfac)));
                                for (int j = 0; j < nA; ++j) y = Mode::wmul(y, cw[A[j]][mi[A[j]]][(j == i) + (j == i2)]);
                                Wc2[ti][i][i2] = y;
                            }
                        }
                }
            }
        }
        // block accumulators: [term][delta k][D-power j][lambda component p] (p: 0, 1+i, then pairs)
        int ncomp() const { return 1 + nA + nA * (nA + 1) / 2; }
        int pidx2(int i, int i2) const { int r = 1 + nA; for (int a = 0; a < i; ++a) r += nA - a; return r + (i2 - i); }
        vector<V> blk; vector<char> blkused;
        void blk_reset() {
            size_t nt = I->S.terms.size(), n = nt * 2 * 3 * ncomp();
            if (blk.size() != n) { blk.assign(n, V()); blkused.assign(nt, 0); }
            for (auto &x : blk) x = V();
            for (auto &u : blkused) u = 0;
        }
        V &B(size_t ti, int k, int j, int p) { return blk[((ti * 2 + k) * 3 + j) * ncomp() + p]; }
        void flush(Acc &acc) {
            size_t nt = I->S.terms.size(); int nc = ncomp();
            for (size_t ti = 0; ti < nt; ++ti) {
                if (!blkused[ti]) continue;
                for (int k = 0; k <= I->kmax; ++k)
                    for (int j = 0; j <= 2 * k; ++j)
                        for (int p = 0; p < nc; ++p) {
                            const V &v = B(ti, k, j, p);
                            const W *w;
                            if (p == 0) w = &Wc0[ti];
                            else if (p <= nA) w = &Wc1[ti][p - 1];
                            else { int i = 0, r = p - 1 - nA; while (r >= nA - i) { r -= nA - i; ++i; } w = &Wc2[ti][i][i + r]; }
                            if (k == 0 && p > 0) continue;
                            acc.v[k][j] = Mode::wadd(acc.v[k][j], mulVW<Mode>(v, *w));
                        }
            }
            blk_reset();
        }
        static void addc(V &a, const V &v, const C &x) { a = Mode::add(a, Mode::mulc(v, x)); }
        // ================= generic delta path (any kmax <= 2; also -generic for kmax <= 1) =================
        // polynomials in (D, lambda_A[0..nA-1]) of total degree <= dmax, dense over a monomial table
        int dmax = 0, NM = 0, NL = 0;
        vector<array<int, MAXD + 1>> mexp;      // poly monomial exponents: [0] = D, [1+i] = lambda_i
        vector<int> mj, ml;                      // D power and lambda-monomial index of each poly monomial
        vector<array<int, MAXD>> lexp;           // lambda monomials (degree <= dmax)
        vector<int> mtab;                        // NM x NM product table (-1 if degree too high)
        vector<int> vidx;                        // poly index of the variable monomials D, lambda_i
        void gen_init() {
            dmax = 2 * I->kmax;
            // lambda monomials
            lexp.clear();
            array<int, MAXD> e{};
            std::function<void(int, int)> recl = [&](int i, int left) {
                if (i == nA) { lexp.push_back(e); return; }
                for (int d = 0; d <= left; ++d) { e[i] = d; recl(i + 1, left - d); }
                e[i] = 0;
            };
            recl(0, dmax);
            NL = lexp.size();
            auto lindex = [&](const array<int, MAXD> &x) { for (int q = 0; q < NL; ++q) { bool eq = true; for (int i = 0; i < nA; ++i) if (lexp[q][i] != x[i]) eq = false; if (eq) return q; } return -1; };
            mexp.clear(); mj.clear(); ml.clear();
            for (int dD = 0; dD <= dmax; ++dD)
                for (int q = 0; q < NL; ++q) {
                    int deg = dD; for (int i = 0; i < nA; ++i) deg += lexp[q][i];
                    if (deg > dmax) continue;
                    array<int, MAXD + 1> m{}; m[0] = dD; for (int i = 0; i < nA; ++i) m[1 + i] = lexp[q][i];
                    mexp.push_back(m); mj.push_back(dD); ml.push_back(q);
                }
            NM = mexp.size();
            auto mindex = [&](const array<int, MAXD + 1> &x) { for (int q = 0; q < NM; ++q) { bool eq = true; for (int i = 0; i <= nA; ++i) if (mexp[q][i] != x[i]) eq = false; if (eq) return q; } return -1; };
            mtab.assign((size_t)NM * NM, -1);
            for (int a = 0; a < NM; ++a) for (int b = 0; b < NM; ++b) {
                array<int, MAXD + 1> s{}; int deg = 0;
                for (int i = 0; i <= nA; ++i) { s[i] = mexp[a][i] + mexp[b][i]; deg += s[i]; }
                if (deg <= dmax) mtab[(size_t)a * NM + b] = mindex(s);
            }
            vidx.assign(nA + 1, -1);
            for (int i = 0; i <= nA; ++i) { array<int, MAXD + 1> s{}; s[i] = 1; vidx[i] = mindex(s); }
            (void)lindex;
        }
        typedef vector<C> Poly;
        Poly pzero() const { return Poly(NM); }
        Poly affine(const C &c0, const C &cD, const C *cl) const {
            Poly p(NM); p[0] = c0; p[vidx[0]] = cD;
            for (int i = 0; i < nA; ++i) p[vidx[1 + i]] = cl[i];
            return p;
        }
        Poly pmul(const Poly &a, const Poly &b) const {
            Poly r(NM);
            for (int x = 0; x < NM; ++x) {
                if (a[x].re.hi == 0 && a[x].im.hi == 0) continue;
                for (int y = 0; y < NM; ++y) {
                    int z = mtab[(size_t)x * NM + y];
                    if (z < 0 || (b[y].re.hi == 0 && b[y].im.hi == 0)) continue;
                    r[z] += a[x] * b[y];
                }
            }
            return r;
        }
        static void padd(Poly &a, const Poly &b, const C &f) { for (size_t i = 0; i < a.size(); ++i) if (b[i].re.hi != 0 || b[i].im.hi != 0) a[i] += b[i] * f; }
        vector<V> gblk; vector<char> gused;
        V &GB(size_t ti, int k, int j, int q) { return gblk[(((ti * 3 + k) * 5 + j) * (size_t)NL) + q]; }
        void gblk_reset() {
            size_t n = I->S.terms.size() * 3 * 5 * (size_t)NL;
            if (gblk.size() != n) { gblk.assign(n, V()); gused.assign(n, 0); return; }
            for (size_t i = 0; i < n; ++i) if (gused[i]) { gblk[i] = V(); gused[i] = 0; }
        }
        void gacc(size_t ti, int k, const V &U, const Poly &p, const C &f) {
            for (int x = 0; x < NM; ++x) {
                if (p[x].re.hi == 0 && p[x].im.hi == 0) continue;
                size_t id = (((ti * 3 + k) * 5 + mj[x]) * (size_t)NL) + ml[x];
                gblk[id] = Mode::add(gblk[id], Mode::mulc(U, p[x] * f)); gused[id] = 1;
            }
        }
        void gflush(Acc &acc) {
            size_t nt = I->S.terms.size();
            vector<W> wc(NL); vector<char> wv(NL);
            for (size_t ti = 0; ti < nt; ++ti) {
                std::fill(wv.begin(), wv.end(), 0);
                const auto &cw = I->cw[ti];
                for (int k = 0; k <= I->kmax; ++k)
                    for (int j = 0; j <= 2 * k; ++j)
                        for (int q = 0; q < NL; ++q) {
                            size_t id = (((ti * 3 + k) * 5 + j) * (size_t)NL) + q;
                            if (!gused[id]) continue;
                            if (!wv[q]) {
                                W w = Mode::wconst(C(R(wfac)));
                                for (int i = 0; i < nA; ++i) w = Mode::wmul(w, cw[A[i]][mic[A[i]]][lexp[q][i]]);
                                wc[q] = w; wv[q] = 1;
                            }
                            acc.v[k][j] = Mode::wadd(acc.v[k][j], mulVW<Mode>(gblk[id], wc[q]));
                        }
            }
            gblk_reset();
        }
        void gterms() {
            const SectorD &S = I->S; const Mode &mode = I->mode; int kmax = I->kmax;
            R swt(1.0); for (int k = 0; k < D; ++k) if (!isc[k]) swt = swt * wk[k];
            C third = C(R(1.0) / R(3.0)), half = C(R(0.5)), one = C(R(1.0));
            for (size_t ti = 0; ti < S.terms.size(); ++ti) {
                const TermD &T = S.terms[ti];
                C XA, XB;
                for (auto &pq : T.pairs) { if (pq.second > 0) { XA += lr[pq.first]; XB -= lr[pq.first]; } else { XA -= lr[pq.first]; XB += lr[pq.first]; } }
                XA = XA * R(2.0); XB = XB * R(2.0);
                XA += lrs; XB += lrs * R(-2.0 * NB);
                R xa(0.0), xb(0.0);
                for (int k = 0; k < D; ++k) if (!isc[k]) { if (T.a[k]) xa += logt[k] * R(double(T.a[k])); if (T.b[k]) xb += logt[k] * R(double(T.b[k])); }
                XA += C(xa); XB += C(xb);
                V Phi = mode.expAB(XA, XB);
                Phi = Mode::mulc(Phi, C(swt * R(double(T.coef))));
                int nf = T.far.size();
                V G[8], Cv[8];
                for (int i = 0; i < nf; ++i) { G[i] = mode.Gt(fv[T.far[i]].lz, fv[T.far[i]].gt); if (kmax >= 1) Cv[i] = mode.Cf(fv[T.far[i]].lz); }
                V U0 = Phi;
                for (int i = 0; i < nf; ++i) U0 = Mode::mul(U0, G[i]);
                Poly P1 = pzero(); P1[0] = one;
                gacc(ti, 0, U0, P1, one);
                if (kmax < 1) continue;
                // Lambda_r^E = sum_E qq (D + L')^r,  L' = ell + mu . lambda
                Poly P2 = pzero(), P3 = pzero();
                for (auto &pq : T.pairs) {
                    C cl[MAXD]; for (int i = 0; i < nA; ++i) cl[i] = C(R(double(S.iv[pq.first].M[A[i]] - S.Ms[A[i]])));
                    Poly Y = affine(ell[pq.first], one, cl);
                    Poly Y2 = pmul(Y, Y);
                    C q(R(double(pq.second)));
                    padd(P2, Y2, q);
                    if (kmax >= 2) padd(P3, pmul(Y2, Y), q);
                }
                // far pairs: Q2 = Lambda2^f / l = 2 Y gt + T2t, Q3 = Lambda3^f / l = 3 Y^2 gt + 3 Y T2t + T3t
                Poly Q2[8], Q3[8];
                for (int i = 0; i < nf; ++i) {
                    const FarD &F = S.fars[T.far[i]]; const auto &q = fv[T.far[i]];
                    C cl[MAXD]; for (int ii = 0; ii < nA; ++ii) cl[ii] = C(R(double(S.iv[F.g].M[A[ii]] - S.Ms[A[ii]])));
                    Poly Y = affine(ell[F.g], one, cl);
                    Q2[i] = pzero(); padd(Q2[i], Y, q.gt * R(2.0)); Q2[i][0] += q.T2t;
                    if (kmax >= 2) {
                        Q3[i] = pzero(); padd(Q3[i], pmul(Y, Y), q.gt * R(3.0)); padd(Q3[i], Y, q.T2t * R(3.0)); Q3[i][0] += q.T3t;
                    }
                }
                // structure s0: V = Phi prod G~
                V KU0 = mode.mulK(U0);
                gacc(ti, 1, KU0, P2, one);
                // structure s_f: V = Phi C_f prod_{f'!=f} G~
                V Uf[8], KUf[8];
                for (int i = 0; i < nf; ++i) {
                    Uf[i] = Mode::mul(Phi, Cv[i]);
                    for (int j = 0; j < nf; ++j) if (j != i) Uf[i] = Mode::mul(Uf[i], G[j]);
                    KUf[i] = mode.mulK(Uf[i]);
                    gacc(ti, 1, KUf[i], Q2[i], one);
                }
                if (kmax < 2) continue;
                // delta^2: s0: K/3 Lambda3 + K^2/2 Lambda2^2
                V K2U0 = mode.mulK(KU0);
                gacc(ti, 2, KU0, P3, third);
                gacc(ti, 2, K2U0, pmul(P2, P2), half);
                for (int i = 0; i < nf; ++i) {
                    V K2Uf = mode.mulK(KUf[i]);
                    // E1 g1: K^2 Lambda2^E Q2_f ; g2: K/3 Q3_f + K^2/2 l_f Q2_f^2
                    gacc(ti, 2, K2Uf, pmul(P2, Q2[i]), one);
                    gacc(ti, 2, KUf[i], Q3[i], third);
                    gacc(ti, 2, K2Uf, pmul(Q2[i], Q2[i]), half * fv[T.far[i]].l);
                    for (int i2 = i + 1; i2 < nf; ++i2) {
                        V Uff = Mode::mul(Mode::mul(Phi, Cv[i]), Cv[i2]);
                        for (int j = 0; j < nf; ++j) if (j != i && j != i2) Uff = Mode::mul(Uff, G[j]);
                        gacc(ti, 2, mode.mulK(mode.mulK(Uff)), pmul(Q2[i], Q2[i2]), one);
                    }
                }
            }
        }
        void terms() {
            const SectorD &S = I->S; const Mode &mode = I->mode; int kmax = I->kmax;
            R swt(1.0); for (int k = 0; k < D; ++k) if (!isc[k]) swt = swt * wk[k];
            for (size_t ti = 0; ti < S.terms.size(); ++ti) {
                const TermD &T = S.terms[ti];
                blkused[ti] = 1;
                C XA, XB;
                for (auto &pq : T.pairs) { if (pq.second > 0) { XA += lr[pq.first]; XB -= lr[pq.first]; } else { XA -= lr[pq.first]; XB += lr[pq.first]; } }
                XA = XA * R(2.0); XB = XB * R(2.0);
                XA += lrs; XB += lrs * R(-2.0 * NB);
                R xa(0.0), xb(0.0);
                for (int k = 0; k < D; ++k) if (!isc[k]) { if (T.a[k]) xa += logt[k] * R(double(T.a[k])); if (T.b[k]) xb += logt[k] * R(double(T.b[k])); }
                XA += C(xa); XB += C(xb);
                V Phi = mode.expAB(XA, XB);
                Phi = Mode::mulc(Phi, C(swt * R(double(T.coef))));
                int nf = T.far.size();
                V G[8], Cv[8];
                for (int i = 0; i < nf; ++i) { G[i] = mode.Gt(fv[T.far[i]].lz, fv[T.far[i]].gt); if (kmax >= 1) Cv[i] = mode.Cf(fv[T.far[i]].lz); }
                V U0 = Phi;
                for (int i = 0; i < nf; ++i) U0 = Mode::mul(U0, G[i]);
                B(ti, 0, 0, 0) = Mode::add(B(ti, 0, 0, 0), U0);
                if (kmax < 1) continue;
                C s1, s2;
                for (auto &pq : T.pairs) {
                    if (pq.second > 0) { s1 += ell[pq.first]; s2 += ell[pq.first] * ell[pq.first]; }
                    else { s1 -= ell[pq.first]; s2 -= ell[pq.first] * ell[pq.first]; }
                }
                V KU0 = mode.mulK(U0);
                addc(B(ti, 1, 2, 0), KU0, C(R(-double(NB))));
                addc(B(ti, 1, 1, 0), KU0, s1 * R(2.0));
                addc(B(ti, 1, 0, 0), KU0, s2);
                for (int i = 0; i < nA; ++i) {
                    int k = A[i]; C r;
                    for (auto &pq : T.pairs) { int mu = S.iv[pq.first].M[k] - S.Ms[k]; if (mu) r += ell[pq.first] * R(double(pq.second * mu)); }
                    if (T.nu[k]) addc(B(ti, 1, 1, 1 + i), KU0, C(R(2.0 * T.nu[k])));
                    addc(B(ti, 1, 0, 1 + i), KU0, r * R(2.0));
                    for (int i2 = i; i2 < nA; ++i2) {
                        int kv = T.kap[k][A[i2]] * (i == i2 ? 1 : 2);
                        if (kv) addc(B(ti, 1, 0, pidx2(i, i2)), KU0, C(R(double(kv))));
                    }
                }
                for (int i = 0; i < nf; ++i) {
                    V Uf = mode.mulK(Mode::mul(Phi, Cv[i]));
                    for (int j = 0; j < nf; ++j) if (j != i) Uf = Mode::mul(Uf, G[j]);
                    const FarD &F = S.fars[T.far[i]];
                    const auto &q = fv[T.far[i]];
                    addc(B(ti, 1, 1, 0), Uf, q.gt * R(2.0));
                    addc(B(ti, 1, 0, 0), Uf, ell[F.g] * q.gt * R(2.0) + q.T2t);
                    for (int ii = 0; ii < nA; ++ii) {
                        int mu = S.iv[F.g].M[A[ii]] - S.Ms[A[ii]];
                        if (mu) addc(B(ti, 1, 0, 1 + ii), Uf, q.gt * R(2.0 * mu));
                    }
                }
            }
        }
    };

    Acc integrate() const {
        bool useconj = conjsym;
        vector<int> split; for (int k = 0; k < D; ++k) if (vtype[k]) split.push_back(k);
        int nreg = 1 << split.size();
        struct Region { unsigned circ; int perm[MAXD], nn[MAXD]; int dbl; };
        vector<Region> regs(nreg);
        int ndep[MAXD];
        for (int k = 0; k < D; ++k) { ndep[k] = 0; for (int Iv = 0; Iv < NINT; ++Iv) if (ivmask[Iv] >> k & 1) ndep[k]++; }
        for (int r = 0; r < nreg; ++r) {
            unsigned circ = 0;
            for (size_t q = 0; q < split.size(); ++q) if (r >> q & 1) circ |= 1u << split[q];
            regs[r].circ = circ;
            vector<int> order(D); for (int k = 0; k < D; ++k) order[k] = k;
            // circle variables outermost, then by decreasing number of dependent intervals
            sort(order.begin(), order.end(), [&](int x, int y) {
                int cx_ = circ >> x & 1, cy_ = circ >> y & 1;
                if (cx_ != cy_) return cx_ > cy_;
                return ndep[x] > ndep[y];
            });
            for (int p = 0; p < D; ++p) {
                int k = order[p]; regs[r].perm[p] = k;
                regs[r].nn[p] = !vtype[k] ? P.nplain : ((circ >> k & 1) ? M : P.nseg);
            }
            regs[r].dbl = 0;
            if (useconj && circ) { regs[r].nn[0] = M / 2; regs[r].dbl = 1; }   // conjugate pairs: half the outer circle, weight 2
        }
        struct Item { int reg, i0; };
        vector<Item> items;
        for (int r = 0; r < nreg; ++r) for (int i0 = 0; i0 < regs[r].nn[0]; ++i0) items.push_back({r, i0});
        int nth = omp_get_max_threads();
        vector<Acc> accs(nth);
        for (auto &a : accs) for (int x = 0; x < 3; ++x) for (int y = 0; y < 5; ++y) a.v[x][y] = Mode::wzero();
#pragma omp parallel
        {
            State st;
#pragma omp for schedule(dynamic, 1)
            for (size_t it = 0; it < items.size(); ++it) {
                Acc &acc = accs[omp_get_thread_num()];
                const Region &rg = regs[items[it].reg];
                st.init(this, rg.circ); st.wfac = rg.dbl ? 2.0 : 1.0;
                bool gen = P.generic;
                if (gen) { st.gen_init(); st.gblk_reset(); } else st.blk_reset();
                int idx[MAXD];
                for (int p = 0; p < D; ++p) { idx[p] = (p == 0 ? items[it].i0 : 0); st.setvar(rg.perm[p], idx[p]); }
                st.update(~0u, true);
                while (true) {
                    if (gen) st.gterms(); else st.terms();
                    int p = D - 1; unsigned chg = 0;
                    while (p >= 1) {
                        chg |= 1u << rg.perm[p];
                        if (++idx[p] < rg.nn[p]) { st.setvar(rg.perm[p], idx[p]); break; }
                        idx[p] = 0; st.setvar(rg.perm[p], 0); --p;
                    }
                    if (p < 1) break;
                    if (chg & rg.circ) { if (gen) st.gflush(acc); else st.flush(acc); }     // circle weights change: flush first
                    st.update(chg);
                }
                if (gen) st.gflush(acc); else st.flush(acc);
            }
        }
        Acc tot = accs[0];
        for (int th = 1; th < nth; ++th)
            for (int x = 0; x < 3; ++x) for (int y = 0; y < 5; ++y) tot.v[x][y] = Mode::wadd(tot.v[x][y], accs[th].v[x][y]);
        if (useconj) for (int x = 0; x < 3; ++x) for (int y = 0; y < 5; ++y) Mode::realpart(tot.v[x][y]);
        return tot;
    }
};

#ifndef BUILD_ID
#define BUILD_ID "unknown"
#endif
static void fail(const string &msg) { cerr << "error: " << msg << endl; exit(2); }

int main(int argc, char **argv) {
    Params P; string infile, outfile;
    string argline;
    for (int i = 1; i < argc; ++i) { if (i > 1) argline += " "; argline += argv[i]; }
    try {
        for (int i = 1; i < argc; ++i) {
            string a = argv[i];
            auto nx = [&]() { if (i + 1 >= argc) fail("missing value after " + a); return string(argv[++i]); };
            if (a == "-i") infile = nx(); else if (a == "-o") outfile = nx();
            else if (a == "-k") P.kmax = stoi(nx()); else if (a == "-tau") P.tau = stod(nx()); else if (a == "-taurat") P.taurat = stod(nx()); else if (a == "-plainR") P.plainR = stod(nx());
            else if (a == "-nseg") P.nseg = stoi(nx()); else if (a == "-m") P.mcirc = stoi(nx());
            else if (a == "-nplain") P.nplain = stoi(nx()); else if (a == "-mode") P.mode = nx();
            else if (a == "-K") { P.Kre = stod(nx()); P.Kim = stod(nx()); P.Kd[0] = R(P.Kre); P.Kd[1] = R(P.Kim); }
            else if (a == "-Kdd") { if (i + 4 >= argc) fail("-Kdd needs 4 values");
                                    double a1 = strtod(argv[++i], 0), a2 = strtod(argv[++i], 0), a3 = strtod(argv[++i], 0), a4 = strtod(argv[++i], 0);
                                    P.Kd[0] = R(a1) + R(a2); P.Kd[1] = R(a3) + R(a4); P.Kre = a1; P.Kim = a3; }
            else if (a == "-sec") { P.sec0 = stoi(nx()); P.sec1 = stoi(nx()); }
            else if (a == "-conj") P.conj = stoi(nx());
            else if (a == "-generic") P.generic = 1;
            else if (a == "-version") { printf("%s\n", BUILD_ID); return 0; }
            else fail("unknown argument " + a);
        }
    } catch (const std::exception &ex) { fail(string("bad numeric argument: ") + ex.what()); }
    // validate everything before allocating or opening the output
    if (infile.empty() || outfile.empty()) fail("need -i INPUT and -o OUTPUT");
    if (P.kmax < 0 || P.kmax > 2) fail("delta order -k must be 0, 1 or 2");
    if (P.kmax == 2 && P.mode == "ser" && (LS < 13 || VMIN > -8)) fail("delta^2 in ser mode needs a build with -DLS=13 -DVMIN=-8 (or larger window)");
    if (P.kmax == 2) P.generic = 1;
    if (P.mode != "cx" && P.mode != "ser") fail("mode must be cx or ser");
    if (P.nseg < 1 || P.mcirc < 2 || P.nplain < 1) fail("node counts must be positive (m >= 2)");
    if (!(P.tau > 0 && P.tau < 1) || !(P.taurat > 0) || !(P.plainR >= 0)) fail("bad tau/taurat/plainR");
    if (P.conj < -1 || P.conj > 1) fail("-conj must be -1, 0 or 1");
    // conjugate symmetry is valid only for real K (cx) or the series mode (MSC-016)
    if (P.mode == "cx" && P.conj == 1 && !(HI(P.Kd[1]) == 0.0 && LO(P.Kd[1]) == 0.0))
        fail("-conj 1 requires a real K in cx mode (the imaginary part of K is nonzero)");
    if (P.mode == "cx" && (!std::isfinite(P.Kre) || !std::isfinite(P.Kim))) fail("bad K");
    string insha;
    if (!sha256_file(infile, insha)) fail("cannot read input " + infile);
    load(infile);
    if (P.sec1 < 0) P.sec1 = secs.size();
    if (P.sec0 < 0 || P.sec0 >= P.sec1 || P.sec1 > (int)secs.size()) fail("bad sector range");
    ModeCx mcx; mcx.K = C(P.Kd[0], P.Kd[1]); mcx.w = C(R(1.0)) - mcx.K;
    ModeSer mser;
    // write to OUTPUT.partial, publish by fsync + rename only after the last sector
    string part = outfile + ".partial";
    FILE *fo = fopen(part.c_str(), "w");
    if (!fo) fail("cannot open " + part);
    fprintf(fo, "# n %d mode %s kmax %d tau %.6g nseg %d m %d nplain %d K %.17g %.17g LS %d VMIN %d Kdd %a %a %a %a taurat %.6g plainR %.6g conj %d generic %d\n", NB, P.mode.c_str(), P.kmax,
            P.tau, P.nseg, P.mcirc, P.nplain, P.Kre, P.Kim, LS, VMIN, HI(P.Kd[0]), LO(P.Kd[0]), HI(P.Kd[1]), LO(P.Kd[1]), P.taurat, P.plainR, P.conj, P.generic);
    fprintf(fo, "# fingerprint input_sha256 %s build %s nsec_input %zu sec0 %d sec1 %d\n", insha.c_str(), BUILD_ID, secs.size(), P.sec0, P.sec1);
    fprintf(fo, "# args %s\n", argline.c_str());
    auto t0 = chrono::steady_clock::now();
    for (int s = P.sec0; s < P.sec1; ++s) {
        auto ts = chrono::steady_clock::now();
        auto run = [&](auto &mode) {
            typedef typename std::remove_reference<decltype(mode)>::type MT;
            bool cj = P.conj >= 0 ? P.conj : (P.mode == "ser" || (HI(P.Kd[1]) == 0.0 && LO(P.Kd[1]) == 0.0));
            Integrator<MT> I(mode, P, secs[s], cj);
            return I.integrate();
        };
        double dt;
        if (P.mode == "cx") {
            auto tot = run(mcx);
            dt = chrono::duration<double>(chrono::steady_clock::now() - ts).count();
            fprintf(fo, "sector %d pat %d time %.2f nterm %zu\n", s, secs[s].pat, dt, secs[s].terms.size());
            for (int k = 0; k <= P.kmax; ++k) for (int j = 0; j <= 2 * k; ++j)
                fprintf(fo, "A %d %d %a %a %a %a\n", k, j, HI(tot.v[k][j].re), LO(tot.v[k][j].re), HI(tot.v[k][j].im), LO(tot.v[k][j].im));
        } else {
            auto tot = run(mser);
            dt = chrono::duration<double>(chrono::steady_clock::now() - ts).count();
            fprintf(fo, "sector %d pat %d time %.2f nterm %zu\n", s, secs[s].pat, dt, secs[s].terms.size());
            for (int k = 0; k <= P.kmax; ++k) for (int j = 0; j <= 2 * k; ++j) {
                // window output: coefficient of w^{e} for e = -v .. LS-1-v
                const Lau &L = tot.v[k][j];
                for (int i = 0; i < LS; ++i)
                    fprintf(fo, "S %d %d %d %a %a %a %a\n", k, j, i - L.v, HI(L.s.c[i].re), LO(L.s.c[i].re), HI(L.s.c[i].im), LO(L.s.c[i].im));
            }
        }
        fprintf(fo, "end sector %d\n", s);
        if (fflush(fo) != 0) fail("write error");
        fprintf(stderr, "sector %d done %.2fs\n", s, dt);
    }
    double tt = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
    fprintf(fo, "# total time %.2f threads %d\n", tt, omp_get_max_threads());
    fprintf(fo, "# complete sectors %d %d\n", P.sec0, P.sec1);
    if (fflush(fo) != 0 || fsync(fileno(fo)) != 0 || fclose(fo) != 0) fail("cannot flush " + part);
    if (rename(part.c_str(), outfile.c_str()) != 0) fail("cannot rename " + part + " to " + outfile);
    return 0;
}
