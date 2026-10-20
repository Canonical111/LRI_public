// Independent check of single sector integrals (fix round 1, MSC-011).
//
// For one sector of the engine input and one complex K it computes the delta = 0 angular integral
//   A_s(K) = sum_terms int_{[0,1]^4} prod_k t_k^{c_k} G_T(t) dt      (analytically continued in K)
// by a method independent of cluster_engine.cpp:
//  * parametrization: the corner of the two contact variables (p, q) (both carry dipole exponents a = -2) is split
//    Hepp-style into t_q = t_p s and t_p = t_q s; the double contact then sits in ONE variable rho = t_p with
//    exponent c_p + c_q + 1 = -3 + 4w (the plan's simultaneous-contact case);
//  * continuation: explicit nested Taylor subtraction (orders n with a + n + 1 <= 0 in every variable), the subtracted
//    terms integrated analytically (1/(c+n+1)), remainders integrated by tanh-sinh; Taylor coefficients by trapezoid
//    rules on small circles (multi-dimensional tables); near a subtracted boundary (t < x0) the remainder is summed
//    from its Taylor series instead of being formed by differencing (as in M2's two_bubble.py);
//  * integrand: evaluated from the full interval lengths and expm1(2K log1p z) for far pairs, exponents re-derived
//    from the lead monomials and checked against the generator's (a, b).
// Shared with the engine: the sector data of the generator and the double-double arithmetic of dd.h (validated
// against mpmath).
// usage: sector_check INPUT SECTOR Kre Kim [-split p q | -nosplit] [-level L] [-mc M] [-x0 X] [-extra E]
#include "dd.h"
#include "sha256.h"
#include <vector>
#include <array>
#include <string>
#include <fstream>
#include <iostream>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include <map>
#ifdef _OPENMP
#include <omp.h>
#endif
using namespace std;
#ifndef BUILD_ID
#define BUILD_ID "unknown"
#endif
typedef dd R;
typedef cx<R> C;

static int NB, NK, NINT, DV;
struct Term { int coef; vector<pair<int, int>> pairs; vector<array<int, 6>> far; vector<int> a, b; };
struct Sec { int pat; vector<int> jac; vector<double> Rk; vector<vector<int>> M; vector<vector<vector<int>>> red;
             vector<int> Ms; vector<vector<int>> sred; vector<int> scoef; vector<Term> terms; };

static vector<Sec> read_input(const string &fn) {
    ifstream f(fn); if (!f) { cerr << "cannot open " << fn << endl; exit(1); }
    string tok; int npat; vector<Sec> out;
    f >> tok >> NB >> tok >> NINT >> tok >> npat; NK = 2 * NB; DV = NK - 2;
    for (int p = 0; p < npat; ++p) {
        f >> tok; for (int i = 0; i < NK; ++i) f >> tok;
        int factor, nsec; f >> tok >> factor >> tok >> nsec;
        for (int s = 0; s < nsec; ++s) {
            Sec S; S.pat = p; S.jac.resize(DV); S.Rk.resize(DV);
            f >> tok; for (int k = 0; k < DV; ++k) f >> S.jac[k];
            f >> tok; for (int k = 0; k < DV; ++k) f >> tok;
            f >> tok; for (int k = 0; k < DV; ++k) f >> tok;
            f >> tok; for (int k = 0; k < DV; ++k) f >> S.Rk[k];
            S.M.assign(NINT, vector<int>(DV)); S.red.resize(NINT);
            for (int I = 0; I < NINT; ++I) {
                f >> tok; for (int k = 0; k < DV; ++k) f >> S.M[I][k];
                int nr; f >> nr; S.red[I].assign(nr, vector<int>(DV));
                for (int r = 0; r < nr; ++r) for (int k = 0; k < DV; ++k) f >> S.red[I][r][k];
            }
            f >> tok; S.Ms.resize(DV); for (int k = 0; k < DV; ++k) f >> S.Ms[k];
            int nr; f >> nr; S.sred.assign(nr, vector<int>(DV)); S.scoef.resize(nr);
            for (int r = 0; r < nr; ++r) { for (int k = 0; k < DV; ++k) f >> S.sred[r][k]; f >> S.scoef[r]; }
            int nt; f >> tok >> nt;
            for (int t = 0; t < nt; ++t) {
                Term T; int np, nf; f >> tok >> T.coef >> np; T.pairs.resize(np);
                for (int i = 0; i < np; ++i) f >> T.pairs[i].first >> T.pairs[i].second;
                f >> nf; T.far.resize(nf);
                for (int i = 0; i < nf; ++i) for (int j = 0; j < 6; ++j) f >> T.far[i][j];
                f >> tok; T.a.resize(DV); for (int k = 0; k < DV; ++k) f >> T.a[k];
                f >> tok; T.b.resize(DV); for (int k = 0; k < DV; ++k) f >> T.b[k];
                S.terms.push_back(T);
            }
            out.push_back(S);
        }
    }
    return out;
}

// ------------------------------------------------------------------ integrand in the ORIGINAL sector variables
struct Integrand {
    const Sec &S; C K; int nt;
    vector<vector<array<int, 8>>> mz;     // per term, per far pair: lead exponent of z
    int maxe;
    Integrand(const Sec &s, C k) : S(s), K(k), nt(s.terms.size()) {
        maxe = 0;
        for (auto &T : S.terms) {
            vector<array<int, 8>> v;
            for (auto &F : T.far) {
                array<int, 8> e{};
                for (int q = 0; q < DV; ++q) { e[q] = S.M[F[0]][q] + S.M[F[1]][q] - S.M[F[2]][q] - S.M[F[5]][q]; maxe = std::max(maxe, e[q]); }
                v.push_back(e);
            }
            mz.push_back(v);
        }
        for (int I = 0; I < NINT; ++I) for (int q = 0; q < DV; ++q) { maxe = std::max(maxe, S.M[I][q]); for (auto &r : S.red[I]) maxe = std::max(maxe, r[q]); }
        for (auto &r : S.sred) for (int q = 0; q < DV; ++q) maxe = std::max(maxe, r[q]);
    }
    // all terms at point t (complex): G_T(t) = term(t) / prod t^{c}
    void eval(const C *t, C *out) const {
        C pw[8][16];
        for (int q = 0; q < DV; ++q) { pw[q][0] = C(R(1.0)); for (int e = 1; e <= maxe; ++e) pw[q][e] = pw[q][e - 1] * t[q]; }
        auto mono = [&](const int *e) { C r = pw[0][e[0]]; for (int q = 1; q < DV; ++q) r = r * pw[q][e[q]]; return r; };
        C lr[64], full[64];
        for (int I = 0; I < NINT; ++I) {
            C s; for (auto &r : S.red[I]) s += mono(r.data());
            lr[I] = cxlog(s); full[I] = mono(S.M[I].data()) * s;
        }
        C rs; for (size_t r = 0; r < S.sred.size(); ++r) rs += mono(S.sred[r].data()) * R(double(S.scoef[r]));
        C lrs = cxlog(rs);
        C twoK = K * R(2.0), sexp = K * R(2.0 * NB) - C(R(2.0 * NB - 1));
        for (int ti = 0; ti < nt; ++ti) {
            const Term &T = S.terms[ti];
            C X = lrs * sexp;
            for (auto &pq : T.pairs) X += lr[pq.first] * (twoK * R(double(pq.second)));
            C v = cexp(X) * R(double(T.coef));
            for (size_t i = 0; i < T.far.size(); ++i) {
                const auto &F = T.far[i];
                C z = full[F[0]] * full[F[1]] / (full[F[2]] * full[F[5]]);
                C l = clog1p(z) * twoK;
                C G = cexpm1_over(l) * l;                                   // expm1(2K log1p z)
                v = v * (G / mono(mz[ti][i].data()));
            }
            out[ti] = v;
        }
    }
};

// ------------------------------------------------------------------ tanh-sinh nodes on (0,1)
static void tanh_sinh(int level, vector<R> &x, vector<R> &w) {
    double h = std::ldexp(1.0, -level);
    for (int k = -int(4.2 / h); k <= int(4.2 / h); ++k) {
        R tk = R(double(k)) * R(h);
        R sh = (exp(tk) - exp(-tk)) * R(0.5), ch = (exp(tk) + exp(-tk)) * R(0.5);
        R u = DD_PI * R(0.5) * sh;
        // x = 1/(1 + e^{-2u}) written to keep relative accuracy near 0: x = e^{u}/(e^{u}+e^{-u})
        R eu = exp(u), emu = exp(-u);
        R xv = eu / (eu + emu);
        R wv = R(h) * DD_PI * R(0.5) * ch * R(4.0) / ((eu + emu) * (eu + emu)) * R(0.5);
        bool inside = xv.hi > 0 && (xv.hi < 1 || (xv.hi == 1 && xv.lo < 0));   // dd value strictly inside (0,1)
        if (!inside || wv.hi < 1e-40) continue;
        x.push_back(xv); w.push_back(wv);
    }
}

// ------------------------------------------------------------------ nested Taylor subtraction in 4 variables
struct Params { int level = 3, mc = 24, extra = 10; double x0 = 5e-4, rcfrac = 8.0; };

int main(int argc, char **argv) {
    if (argc == 2 && string(argv[1]) == "-version") { printf("%s\n", BUILD_ID); return 0; }
    if (argc < 5) { cerr << "usage: sector_check INPUT SECTOR Kre Kim [-split p q|-nosplit] [-level L] [-mc M] [-x0 X] [-extra E]" << endl; return 2; }
    string insha;
    if (!sha256_file(argv[1], insha)) { cerr << "cannot read input" << endl; return 2; }
    vector<Sec> secs = read_input(argv[1]);
    int sid = atoi(argv[2]);
    C K(R(strtod(argv[3], 0)), R(strtod(argv[4], 0)));
    Params P; int sp = -1, sq = -1; bool nosplit = false;
    for (int i = 5; i < argc; ++i) {
        string a = argv[i];
        if (a == "-split") { sp = atoi(argv[++i]); sq = atoi(argv[++i]); }
        else if (a == "-nosplit") nosplit = true;
        else if (a == "-level") P.level = atoi(argv[++i]);
        else if (a == "-mc") P.mc = atoi(argv[++i]);
        else if (a == "-x0") P.x0 = atof(argv[++i]);
        else if (a == "-extra") P.extra = atoi(argv[++i]);
        else if (a == "-rcfrac") P.rcfrac = atof(argv[++i]);
        else if (a == "-Kdd") { double a1 = strtod(argv[++i], 0), a2 = strtod(argv[++i], 0), a3 = strtod(argv[++i], 0), a4 = strtod(argv[++i], 0);
                                K = C(R(a1) + R(a2), R(a3) + R(a4)); }
        else { cerr << "unknown arg " << a << endl; return 2; }
    }
    if (sid < 0 || sid >= (int)secs.size()) { cerr << "bad sector" << endl; return 2; }
    if (!std::isfinite(K.re.hi) || !std::isfinite(K.im.hi) || !std::isfinite(K.re.lo) || !std::isfinite(K.im.lo)) { cerr << "nonfinite K" << endl; return 2; }
    if (P.level < 0 || P.level > 6 || P.mc < 8 || !(P.x0 > 0) || P.extra < 1 || !(P.rcfrac > 1)) { cerr << "bad numerical parameters" << endl; return 2; }
    const Sec &S = secs[sid];
    int nt = S.terms.size();
    if (DV != 4 && DV != 2) { cerr << "only 2 or 4 sector variables supported" << endl; return 2; }
    if (nt > 64 || NINT > 64) { cerr << "too many terms/intervals" << endl; return 2; }
    C w = C(R(1.0)) - K;
    // exponents re-derived from the lead monomials and checked against the generator
    vector<vector<int>> ea(nt, vector<int>(DV)), eb(nt, vector<int>(DV));
    for (int ti = 0; ti < nt; ++ti) {
        const Term &T = S.terms[ti];
        for (int k = 0; k < DV; ++k) {
            int sq2 = 0; for (auto &pq : T.pairs) sq2 += 2 * pq.second * S.M[pq.first][k];
            int fz = 0; for (auto &F : T.far) fz += S.M[F[0]][k] + S.M[F[1]][k] - S.M[F[2]][k] - S.M[F[5]][k];
            ea[ti][k] = S.jac[k] + sq2 + S.Ms[k] + fz;
            eb[ti][k] = -sq2 - 2 * NB * S.Ms[k];
            if (ea[ti][k] != T.a[k] || eb[ti][k] != T.b[k]) { cerr << "exponent mismatch with the generator" << endl; return 3; }
        }
    }
    // choose the contact pair if not given: two variables with a <= -2 in one term
    if (!nosplit && sp < 0) {
        for (int ti = 0; ti < nt && sp < 0; ++ti)
            for (int p = 0; p < DV && sp < 0; ++p) for (int q = p + 1; q < DV; ++q)
                if (ea[ti][p] <= -2 && ea[ti][q] <= -2) { sp = p; sq = q; break; }
        if (sp < 0) nosplit = true;
    }
    Integrand I(S, K);
    vector<R> xs, ws; tanh_sinh(P.level, xs, ws);
    int N = xs.size();
    vector<R> lx(N); for (int i = 0; i < N; ++i) lx[i] = log(xs[i]);
    int nsub = nosplit ? 1 : 2;
    vector<C> total(nt);
    for (int sub = 0; sub < nsub; ++sub) {
        // sub-sector map: t_p = u_p, t_q = u_p u_q (sub 0: p = sp, q = sq; sub 1: swapped)
        int p = sub == 0 ? sp : sq, q = sub == 0 ? sq : sp;
        auto tmap = [&](const C *u, C *t) {
            for (int k = 0; k < DV; ++k) t[k] = u[k];
            if (!nosplit) t[q] = u[p] * u[q];
        };
        // exponents in the sub-sector
        vector<vector<C>> cc(nt, vector<C>(DV)); vector<vector<int>> aa(nt, vector<int>(DV));
        for (int ti = 0; ti < nt; ++ti)
            for (int k = 0; k < DV; ++k) {
                int a = ea[ti][k], b = eb[ti][k];
                if (!nosplit && k == p) { a = ea[ti][p] + ea[ti][q] + 1; b = eb[ti][p] + eb[ti][q]; }
                aa[ti][k] = a; cc[ti][k] = C(R(double(a))) + w * R(double(b));
            }
        // rigorous lower bound on the analyticity radius in every SUB-SECTOR variable: each regular part is a polynomial
        // with positive coefficients; in u_k it reads a_0 + sum_d a_d u_k^d with a_0 >= its constant term c and
        // |a_d| <= a_d(other variables = 1) on the closed unit polydisc, so no zero lies in |u_k| < r*, where
        // sum_{d>=1} a_d(1) r*^d = c (Rouche). The bound is taken over all interval sums and s.
        vector<double> Rv(DV, 1e300), rc(DV);
        {
            vector<vector<pair<vector<int>, double>>> polys;
            for (int Ii = 0; Ii < NINT; ++Ii) { vector<pair<vector<int>, double>> P_; for (auto &r : S.red[Ii]) P_.push_back({r, 1.0}); polys.push_back(P_); }
            { vector<pair<vector<int>, double>> P_; for (size_t r = 0; r < S.sred.size(); ++r) P_.push_back({S.sred[r], double(S.scoef[r])}); polys.push_back(P_); }
            for (auto &P_ : polys) {
                // exponents in sub-sector variables: t_p = u_p, t_q = u_p u_q
                vector<pair<vector<int>, double>> Q;
                for (auto &mc_ : P_) { vector<int> e = mc_.first; if (!nosplit) e[p] += e[q]; Q.push_back({e, mc_.second}); }
                for (int k = 0; k < DV; ++k) {
                    double c0 = 0; vector<double> ad(64, 0.0); int dmax = 0;
                    for (auto &mc_ : Q) {
                        bool allzero = true; for (int v = 0; v < DV; ++v) if (mc_.first[v]) allzero = false;
                        if (allzero) c0 += mc_.second;
                        int d = mc_.first[k]; if (d > 0) { ad[d] += mc_.second; dmax = std::max(dmax, d); }
                    }
                    if (dmax == 0) continue;
                    if (c0 <= 0) { cerr << "regular part without constant term" << endl; exit(3); }
                    double lo = 0, hi = 1e6;
                    for (int it = 0; it < 200; ++it) {
                        double r = 0.5 * (lo + hi), f = 0, x = 1;
                        for (int d = 1; d <= dmax; ++d) { x *= r; f += ad[d] * x; }
                        if (f < c0) lo = r; else hi = r;
                    }
                    Rv[k] = std::min(Rv[k], lo);
                }
            }
            for (int k = 0; k < DV; ++k) if (Rv[k] > 1.0) Rv[k] = 1.0;
        }
        for (int k = 0; k < DV; ++k) rc[k] = Rv[k] / P.rcfrac;
        fprintf(stderr, "sub-sector %d radii:", sub); for (int k = 0; k < DV; ++k) fprintf(stderr, " %.4g", Rv[k]); fprintf(stderr, "\n");
        // subtraction orders
        vector<vector<int>> Nn(nt, vector<int>(DV));
        unsigned Vall = 0;
        for (int ti = 0; ti < nt; ++ti) for (int k = 0; k < DV; ++k) {
            Nn[ti][k] = std::max(0, -aa[ti][k]);
            if (Nn[ti][k]) Vall |= 1u << k;
            // b = 0 with a <= -1 would be a K-independent divergence
            if (aa[ti][k] <= -1 && (cc[ti][k].im.hi == 0 && w.im.hi != 0)) { cerr << "nonregularizable exponent" << endl; return 3; }
        }
        int nmax[8]; for (int k = 0; k < DV; ++k) { int m = 0; for (int ti = 0; ti < nt; ++ti) m = std::max(m, Nn[ti][k]); nmax[k] = m + P.extra; }
        double x0[8]; for (int k = 0; k < DV; ++k) x0[k] = std::min(P.x0, rc[k] / 4.0);
        // ---------------- tables H_U for every nonempty U subset of Vall
        // layout: for U, rest variables r_1 < r_2 < ... (not in U); grid index g = sum idx_r * N^{pos};
        // multi-index over U variables u_1 < ... with sizes nmax+1; value index = ((g * prodU) + mi) * nt + ti
        vector<vector<C>> H(1u << DV); vector<vector<int>> Uvars(1u << DV), Rvars(1u << DV); vector<long> prodU(1u << DV, 0);
        vector<array<long, 8>> gstride(1u << DV), nstride(1u << DV);
        int MC = P.mc;
        vector<C> eth(MC); for (int m = 0; m < MC; ++m) { R s_, c_; sincos(DD_PI * R(2.0 * m) / R(double(MC)), s_, c_); eth[m] = C(c_, s_); }   // angle in double-double
        for (unsigned U = 1; U < (1u << DV); ++U) {
            if ((U & Vall) != U) continue;
            vector<int> uv, rv; for (int k = 0; k < DV; ++k) ((U >> k) & 1 ? uv : rv).push_back(k);
            long pu = 1; for (int k : uv) pu *= nmax[k] + 1;
            long ng = 1; for (size_t i = 0; i < rv.size(); ++i) ng *= N;
            Uvars[U] = uv; Rvars[U] = rv; prodU[U] = pu;
            { long m1 = 1; for (int k = 0; k < DV; ++k) gstride[U][k] = 0; for (int k : rv) { gstride[U][k] = m1; m1 *= N; }
              long m2 = 1; for (int k = 0; k < DV; ++k) nstride[U][k] = 0; for (int k : uv) { nstride[U][k] = m2; m2 *= nmax[k] + 1; } }
            vector<C> &tab = H[U]; tab.assign((size_t)ng * pu * nt, C());
            long ntor = 1; for (size_t i = 0; i < uv.size(); ++i) ntor *= MC;
            // phase 1: integrand on every (grid point, torus point), in parallel
            vector<C> Fall((size_t)ng * ntor * nt);
#pragma omp parallel for schedule(dynamic, 16)
            for (long gm = 0; gm < ng * ntor; ++gm) {
                long g = gm / ntor, m = gm % ntor;
                C u[8], t[8]; long gg = g, mm = m;
                for (int k : rv) { u[k] = C(xs[gg % N]); gg /= N; }
                for (int k : uv) { u[k] = eth[mm % MC] * R(rc[k]); mm /= MC; }
                tmap(u, t);
                I.eval(t, &Fall[(size_t)gm * nt]);
            }
            // phase 2: separable DFT per grid point (dimension by dimension; first U variable fastest)
            // coefficient(n) = (1/MC^|U|) sum_m F(m) prod_k e^{-i n_k th_m} / rc_k^{n_k}
            vector<vector<R>> invpow(uv.size());
            for (size_t di = 0; di < uv.size(); ++di) {
                int k = uv[di]; R invr = R(1.0) / R(rc[k]); invpow[di].resize(nmax[k] + 1);
                R x = R(1.0) / R(double(MC));
                for (int n = 0; n <= nmax[k]; ++n) { invpow[di][n] = x; x = x * invr; }
            }
            auto dft = [&](long g, bool inner_parallel) {
                vector<C> cur(Fall.begin() + (size_t)g * ntor * nt, Fall.begin() + (size_t)(g + 1) * ntor * nt);
                vector<long> dims(uv.size(), MC);
                for (size_t di = 0; di < uv.size(); ++di) {
                    int nk = nmax[uv[di]] + 1;
                    long before = 1, after = 1;
                    for (size_t j = 0; j < di; ++j) before *= dims[j];
                    for (size_t j = di + 1; j < dims.size(); ++j) after *= dims[j];
                    vector<C> nxt((size_t)before * nk * after * nt);
#pragma omp parallel for collapse(2) schedule(static) if (inner_parallel)
                    for (long a0 = 0; a0 < after; ++a0)
                        for (long b0 = 0; b0 < before; ++b0)
                            for (int n = 0; n < nk; ++n)
                                for (int ti = 0; ti < nt; ++ti) {
                                    C acc;
                                    for (int m = 0; m < MC; ++m)
                                        acc += cur[((size_t)(b0 + before * (m + (long)MC * a0))) * nt + ti] * conj(eth[(long(m) * n) % MC]);
                                    nxt[((size_t)(b0 + before * (n + (long)nk * a0))) * nt + ti] = acc * invpow[di][n];
                                }
                    cur.swap(nxt); dims[di] = nk;
                }
                for (long mi = 0; mi < pu; ++mi) for (int ti = 0; ti < nt; ++ti) tab[((size_t)g * pu + mi) * nt + ti] = cur[(size_t)mi * nt + ti];
            };
            if (ng >= 64) {
#pragma omp parallel for schedule(dynamic, 1)
                for (long g = 0; g < ng; ++g) dft(g, false);
            } else {
                for (long g = 0; g < ng; ++g) dft(g, true);
            }
        }
        auto Hget = [&](unsigned U, const int *idx, const int *n, int ti) -> const C & {
            long g = 0, mi = 0;
            for (int k = 0; k < DV; ++k) { g += idx[k] * gstride[U][k]; mi += n[k] * nstride[U][k]; }
            return H[U][((size_t)g * prodU[U] + mi) * nt + ti];
        };
        // ---------------- assemble: I_T = sum_S sum_{n_S < N_S} prod_{k in S} 1/(c_k+n_k+1) Q_S(n_S)
        vector<C> subtot(nt);
        for (unsigned Sm = 0; Sm < (1u << DV); ++Sm) {
            if ((Sm & Vall) != Sm) continue;
            vector<int> rv; for (int k = 0; k < DV; ++k) if (!((Sm >> k) & 1)) rv.push_back(k);
            long ng = 1; for (size_t i = 0; i < rv.size(); ++i) ng *= N;
            int nthr = 1;
#ifdef _OPENMP
            nthr = omp_get_max_threads();
#endif
            vector<vector<C>> acc(nthr, vector<C>(nt));
#pragma omp parallel for schedule(dynamic, 64)
            for (long g = 0; g < ng; ++g) {
                int th = 0;
#ifdef _OPENMP
                th = omp_get_thread_num();
#endif
                int idx[8] = {0}; long gg = g;
                for (int k : rv) { idx[k] = gg % N; gg /= N; }
                C u[8], t[8];
                for (int k : rv) u[k] = C(xs[idx[k]]);
                C direct[64]; bool have_direct = false;
                R tp[8][64];
                for (int k : rv) { tp[k][0] = R(1.0); for (int e = 1; e <= nmax[k]; ++e) tp[k][e] = tp[k][e - 1] * xs[idx[k]]; }
                for (int ti = 0; ti < nt; ++ti) {
                    unsigned VT = 0; for (int k = 0; k < DV; ++k) if (Nn[ti][k]) VT |= 1u << k;
                    if ((Sm & VT) != Sm) continue;
                    unsigned F = VT & ~Sm, Bm = 0;
                    for (int k = 0; k < DV; ++k) if ((F >> k) & 1 && xs[idx[k]].hi < x0[k]) Bm |= 1u << k;
                    unsigned Am = F & ~Bm;
                    // weight prod_{k not in S} w_k t_k^{c_k}
                    C wt(R(1.0));
                    for (int k : rv) wt = wt * cexp(cc[ti][k] * C(lx[idx[k]])) * ws[idx[k]];
                    // loop over n_S
                    int sv[8], nsv = 0; for (int k = 0; k < DV; ++k) if ((Sm >> k) & 1) sv[nsv++] = k;
                    int nS[8] = {0};
                    while (true) {
                        // R_F G^{(S)}_{nS} at the node
                        C val;
                        for (unsigned Sp = Am;; Sp = (Sp - 1) & Am) {
                            // sum over n_{S'} < N and n_B in [N, nmax]
                            int var[8], nvar = 0; for (int k = 0; k < DV; ++k) if (((Sp | Bm) >> k) & 1) var[nvar++] = k;
                            int n[8]; for (int k = 0; k < DV; ++k) n[k] = nS[k];
                            for (int j = 0; j < nvar; ++j) { int k = var[j]; n[k] = ((Sp >> k) & 1) ? 0 : Nn[ti][k]; }
                            double sign = (__builtin_popcount(Sp) % 2) ? -1.0 : 1.0;
                            while (true) {
                                C term;
                                unsigned U = Sm | Sp | Bm;
                                if (U == 0) {
                                    if (!have_direct) { tmap(u, t); I.eval(t, direct); have_direct = true; }
                                    term = direct[ti];
                                } else term = Hget(U, idx, n, ti);
                                for (int j = 0; j < nvar; ++j) term = term * tp[var[j]][n[var[j]]];
                                val += term * R(sign);
                                // next multi-index
                                int j = 0;
                                for (; j < nvar; ++j) {
                                    int k = var[j];
                                    int hi = ((Sp >> k) & 1) ? Nn[ti][k] : nmax[k] + 1;
                                    if (++n[k] < hi) break;
                                    n[k] = ((Sp >> k) & 1) ? 0 : Nn[ti][k];
                                }
                                if (j == nvar) break;
                            }
                            if (Sp == 0) break;
                        }
                        // analytic factor for S
                        C fac(R(1.0));
                        for (int jj = 0; jj < nsv; ++jj) { int k = sv[jj]; fac = fac / (cc[ti][k] + C(R(double(nS[k] + 1)))); }
                        acc[th][ti] += val * wt * fac;
                        int j = 0;
                        for (; j < nsv; ++j) { int k = sv[j]; if (++nS[k] < Nn[ti][k]) break; nS[k] = 0; }
                        if (j == nsv || nsv == 0) break;
                    }
                }
            }
            for (int th = 0; th < nthr; ++th) for (int ti = 0; ti < nt; ++ti) subtot[ti] += acc[th][ti];
        }
        for (int ti = 0; ti < nt; ++ti) total[ti] += subtot[ti];
        fprintf(stderr, "sub-sector %d (rho = t%d, s = t%d) done\n", sub, p, q);
    }
    C sum; for (int ti = 0; ti < nt; ++ti) sum += total[ti];
    // MSC-012: never publish a nonfinite result
    if (!std::isfinite(sum.re.hi) || !std::isfinite(sum.re.lo) || !std::isfinite(sum.im.hi) || !std::isfinite(sum.im.lo)) {
        cerr << "nonfinite sector integral; nothing written" << endl; return 3;
    }
    printf("sector %d split %d %d level %d mc %d x0 %g extra %d rcfrac %g radii rouche nodes %d\n", sid, nosplit ? -1 : sp, nosplit ? -1 : sq, P.level, P.mc, P.x0, P.extra, P.rcfrac, N);
    // MSC-013: fingerprint (input hash, build, exact K, numerical arguments)
    printf("# fingerprint input_sha256 %s build %s sector %d Kdd %a %a %a %a level %d mc %d x0 %a extra %d rcfrac %a split %d %d\n",
           insha.c_str(), BUILD_ID, sid, K.re.hi, K.re.lo, K.im.hi, K.im.lo, P.level, P.mc, P.x0, P.extra, P.rcfrac,
           nosplit ? -1 : sp, nosplit ? -1 : sq);
    printf("A00 %a %a %a %a\n", sum.re.hi, sum.re.lo, sum.im.hi, sum.im.lo);
    printf("# complete\n");
    return 0;
}
