// lri_engine.cpp -- independent Mellin + Hepp-sector engine for the small-eps expansion of the
// hard-core ordered moments of the one-dimensional alternating kink gas (LRI near s=1).
//
// Written from scratch for the LRI_SRI_C6C7_independent re-derivation (no archived engine code used).
//
// Mathematical summary (see ../README.md for the full derivation):
//   Mellin transform in the cutoff:  I~(s) = int_0^inf eps^{s-1} I(eps) deps = (1/s) int F(r) min_internal(r)^s dr.
//   geom=angular : spacings = the m=n-1 internal gaps, integral over the simplex sum x = 1 (radial part done
//                  analytically by the python driver);
//   geom=full    : spacings = r_0 (left boundary), the n-1 internal gaps, r_n (right boundary), simplex sum r = 1.
//   Cheng-Wu projective chart per Hepp sector (total order of the spacings):  x_{sigma(1)}=1,
//   x_{sigma(i+1)} = t_1...t_i, t in [0,1]^{M-1}.  Every sum of spacings = monomial * (1 + P(t)),
//   P = sum of products of consecutive t's.  The integrand is prod_l t_l^{a_l-1+b_l e} G(t;e),
//   G smooth.  Variables with a_l<=0 (b_l=1) are Taylor subtracted to order N_l=-a_l; the subtracted
//   Taylor terms are integrated analytically (pole factors), the remainders numerically.
//   Taylor coefficients are computed numerically with truncated multivariate power series ("jets").
//   e = s - s0 is kept formal; log t_l coming from log insertions are formal variables mu_l in the
//   pole terms.
//
// Output: Laurent coefficients [e^k] of A(s0+e) for k = lo..etarget, for each insertion channel,
// summed over the requested canonical sectors (reflection-symmetric pairs are folded: weight 2).

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <type_traits>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif
#include <unistd.h>
#include "dd.hpp"

using std::vector;
#define ENGINE_VERSION "v2-2026-10-03"
static const int MAXV = 12;  // max jet variables

// ---------------------------------------------------------------------------------------------
// Problem definition
// ---------------------------------------------------------------------------------------------
struct Term {
  double coef;
  int ex[7];  // powers of S1,S2,S3,S4,E1,E2,E3
};
struct Channel {
  std::string name;
  vector<Term> terms;
  int Dmu = 0;         // total log degree
  int etarget = 1000;  // highest Laurent order needed for this channel (clamped to the global etarget)
};
struct SumDef {
  vector<int> mem;  // spacing indices
  int wexp = 0;     // power in the rational weight
  int kind = 0;     // 0 pair, 1 endpoint, 2 D, 3 Sigma
  double qcoef = 0; // coefficient in S_k (pairs) or E_k (endpoints)
};
struct Problem {
  int n = 0;
  char type = 'Z';
  bool full = false;
  int s0 = 0;
  int etarget = 0;
  int M = 0, d = 0;
  vector<int> internal;  // per spacing
  vector<SumDef> sums;
  vector<int> pairs, eps;  // indices into sums
  int iD = -1, iSig = -1;
  int kappa = 0, dF = 0;
  vector<Channel> ch;
  int Dmu = 0;
  bool needS[5] = {0, 0, 0, 0, 0}, needE[4] = {0, 0, 0, 0};
  // numerics
  std::string prec = "auto";
  double tauC_d = 5.0, tauC_dd = 19.0;  // digits budget T: tau = 10^{-T/sumN}
  int mx_dd = 0;  // 0 = automatic
  double errTarget = 1e-13, tailMax = 0.02, maxJet = 200000, tailTol = 1e-13;
  int mx_d = 0;
  int transform = 3;
  long long N = 1;
  vector<long long> z;
  int shifts = 4;
  unsigned long long seed = 1234567;
  long long secStart = 0, secEnd = -1;
  long long secStride = 1, secOffset = 0;  // sample every secStride-th canonical sector (cost/convergence studies)
  int nthreads = 0;
  bool persector = true;
  bool persectorRep = true;  // v2: per-sector per-shift values in the output (refinement / outlier analysis)
  int taskShifts = 1;        // v2: shifts per OpenMP task (0 = phase-1 rule: whole sectors when >= 2*threads)
  bool longestFirst = true;  // v2: run tasks in decreasing estimated cost
  bool fold = true;
  std::string out = "";
};

static int mirror_index(const Problem &P, int p) { return P.M - 1 - p; }

static void build_problem(Problem &P) {
  int n = P.n;
  if (P.full) {
    P.M = n + 1;
  } else {
    P.M = n - 1;
  }
  P.d = P.M - 1;
  P.internal.assign(P.M, 1);
  if (P.full) {
    P.internal[0] = 0;
    P.internal[n] = 0;
  }
  auto gapIndex = [&](int g) { return P.full ? g : g - 1; };  // gap g between kinks g,g+1 (1-based)
  auto q = [&](int i) { return (i % 2 == 1) ? 1 : -1; };
  P.sums.clear();
  P.pairs.clear();
  P.eps.clear();
  P.dF = 0;
  for (int i = 1; i <= n; i++)
    for (int j = i + 1; j <= n; j++) {
      SumDef s;
      for (int g = i; g <= j - 1; g++) s.mem.push_back(gapIndex(g));
      s.wexp = 2 * q(i) * q(j);
      s.kind = 0;
      s.qcoef = q(i) * q(j);
      P.dF += s.wexp;
      P.pairs.push_back(P.sums.size());
      P.sums.push_back(s);
    }
  bool needEP = P.needE[1] || P.needE[2] || P.needE[3];
  if (needEP) {
    if (!P.full) {
      fprintf(stderr, "endpoint insertions need geom=full\n");
      exit(2);
    }
    double sgn = (n % 2 == 1) ? 1.0 : -1.0;
    for (int i = 1; i <= n; i++) {
      SumDef a, b;
      for (int p = 0; p <= i - 1; p++) a.mem.push_back(p);  // X_i
      for (int p = i; p <= n; p++) b.mem.push_back(p);      // 1 - X_i
      a.kind = b.kind = 1;
      a.qcoef = q(i);
      b.qcoef = sgn * q(i);
      P.eps.push_back(P.sums.size());
      P.sums.push_back(a);
      P.eps.push_back(P.sums.size());
      P.sums.push_back(b);
    }
  }
  if (P.type == 'Q') {
    SumDef s;
    for (int g = 1; g <= n - 1; g += 2) s.mem.push_back(gapIndex(g));
    s.kind = 2;
    s.wexp = 1;
    P.dF += 1;
    P.iD = P.sums.size();
    P.sums.push_back(s);
  }
  {
    SumDef s;
    for (int p = 0; p < P.M; p++) s.mem.push_back(p);
    s.kind = 3;
    P.iSig = P.sums.size();
    P.sums.push_back(s);
  }
  P.kappa = P.M + P.dF;
}

// ---------------------------------------------------------------------------------------------
// Jet layouts
// ---------------------------------------------------------------------------------------------
struct Layout {
  int nv = 0;
  int ord[MAXV];
  int stride[MAXV];
  int size = 1;
  vector<uint8_t> dig;   // size*nv
  vector<uint16_t> nz;   // digits>=1 bitmask
  void build(int nv_, const int *ord_) {
    nv = nv_;
    size = 1;
    for (int a = 0; a < nv; a++) {
      ord[a] = ord_[a];
      stride[a] = size;
      size *= (ord[a] + 1);
    }
    dig.assign((size_t)size * (nv > 0 ? nv : 1), 0);
    nz.assign(size, 0);
    for (int idx = 0; idx < size; idx++) {
      int r = idx;
      uint16_t m = 0;
      for (int a = 0; a < nv; a++) {
        int dgt = r % (ord[a] + 1);
        r /= (ord[a] + 1);
        dig[(size_t)idx * nv + a] = dgt;
        if (dgt) m |= (1u << a);
      }
      nz[idx] = m;
    }
  }
};

// Global (thread-safe) caches: layouts depend only on the order vector; level-restricted convolution
// pair lists depend on (orders, base subtraction orders).
#include <mutex>
struct LevelPairs {
  vector<uint8_t> nB;  // per jet index: number of variables with a tail digit (> base order)
};
static std::mutex g_cache_mtx;
static std::map<vector<int>, Layout *> g_layouts;
static std::map<vector<int>, LevelPairs *> g_levels;
static const Layout *get_layout(int nv, const int *ord) {
  vector<int> key(ord, ord + nv);
  std::lock_guard<std::mutex> lk(g_cache_mtx);
  auto it = g_layouts.find(key);
  if (it != g_layouts.end()) return it->second;
  Layout *L = new Layout();
  L->build(nv, ord);
  g_layouts[key] = L;
  return L;
}
static const LevelPairs *get_levels(const Layout &L, const int *Nbase) {
  vector<int> key(L.ord, L.ord + L.nv);
  key.push_back(-1);
  for (int a = 0; a < L.nv; a++) key.push_back(Nbase[a]);
  std::lock_guard<std::mutex> lk(g_cache_mtx);
  auto it = g_levels.find(key);
  if (it != g_levels.end()) return it->second;
  LevelPairs *lp = new LevelPairs();
  int nv = L.nv;
  lp->nB.assign(L.size, 0);
  for (int x = 0; x < L.size; x++) {
    int c = 0;
    for (int a = 0; a < nv; a++)
      if (L.dig[(size_t)x * nv + a] > Nbase[a]) c++;
    lp->nB[x] = c;
  }
  g_levels[key] = lp;
  return lp;
}

template <class T> struct Sparse {
  T c0;
  int nt = 0;
  int off[64];
  uint16_t mask[64];
  T coef[64];
};

template <class T> static inline void sp_mul(T *J, const Sparse<T> &s, const Layout &L) {
  for (int idx = L.size - 1; idx >= 0; idx--) {
    T v = s.c0 * J[idx];
    uint16_t nzm = L.nz[idx];
    for (int t = 0; t < s.nt; t++)
      if ((s.mask[t] & ~nzm) == 0) v += s.coef[t] * J[idx - s.off[t]];
    J[idx] = v;
  }
}
template <class T> static inline void sp_div(T *J, const Sparse<T> &s, const Layout &L) {
  T inv = NT<T>::c(1.0) / s.c0;
  for (int idx = 0; idx < L.size; idx++) {
    T v = J[idx];
    uint16_t nzm = L.nz[idx];
    for (int t = 0; t < s.nt; t++)
      if ((s.mask[t] & ~nzm) == 0) v -= s.coef[t] * J[idx - s.off[t]];
    J[idx] = v * inv;
  }
}
// jet of log(c0 + sum coef tau^mask)
template <class T> static inline void sp_log(T *Lj, const Sparse<T> &s, const Layout &L, T *scratch) {
  for (int i = 0; i < L.size; i++) scratch[i] = NT<T>::c(0.0);
  for (int t = 0; t < s.nt; t++) scratch[s.off[t]] = s.coef[t];
  Lj[0] = NT<T>::lg(s.c0);
  T inv = NT<T>::c(1.0) / s.c0;
  for (int idx = 1; idx < L.size; idx++) {
    uint16_t nzm = L.nz[idx];
    int v = __builtin_ctz(nzm);
    int dv = L.dig[(size_t)idx * L.nv + v];
    T acc = scratch[idx] * (double)dv;
    for (int t = 0; t < s.nt; t++)
      if ((s.mask[t] & ~nzm) == 0) {
        int w = dv - ((s.mask[t] >> v) & 1);
        if (w) acc -= s.coef[t] * Lj[idx - s.off[t]] * (double)w;
      }
    Lj[idx] = acc * inv / (double)dv;
  }
}
// out[x] += scale * sum_{i+j=x} a[i] b[j] (truncated to the layout box); if nB given, only outputs with nB[x] <= lv
template <class T>
static inline void conv_add(T *out, const T *a, const T *b, const Layout &L, double scale = 1.0,
                            const uint8_t *nB = nullptr, int lv = 1 << 20) {
  const int nv = L.nv;
  if (nv == 0) {
    if (!nB || nB[0] <= lv) out[0] += a[0] * b[0] * scale;
    return;
  }
  int ext[MAXV], dj[MAXV];
  for (int i = 0; i < L.size; i++) {
    if (NT<T>::d(a[i]) == 0.0) continue;
    T ai = (scale == 1.0) ? a[i] : a[i] * scale;
    const uint8_t *di = &L.dig[(size_t)i * nv];
    for (int q = 0; q < nv; q++) {
      ext[q] = L.ord[q] - di[q];
      dj[q] = 0;
    }
    int jl = 0;
    while (true) {
      int x = i + jl;
      if (!nB || nB[x] <= lv) out[x] += ai * b[jl];
      int q = 0;
      while (q < nv) {
        dj[q]++;
        jl += L.stride[q];
        if (dj[q] <= ext[q]) break;
        jl -= dj[q] * L.stride[q];
        dj[q] = 0;
        q++;
      }
      if (q == nv) break;
    }
  }
}

// L = log(F) for a dense jet F (F[0] > 0): F d_v L = d_v F, coefficient by coefficient
template <class T> static inline void dense_log(T *Lj, const T *F, const Layout &L) {
  const int nv = L.nv;
  Lj[0] = NT<T>::lg(F[0]);
  if (L.size == 1) return;
  T inv = NT<T>::c(1.0) / F[0];
  int dk[MAXV];
  for (int J = 1; J < L.size; J++) {
    const uint8_t *dJ = &L.dig[(size_t)J * nv];
    int v = __builtin_ctz(L.nz[J]);
    int Jv = dJ[v];
    T acc = F[J] * (double)Jv;
    // sum over K < J (componentwise), K != J, K_v >= 1:  F[J-K] K_v L[K]
    for (int q = 0; q < nv; q++) dk[q] = 0;
    int K = 0;
    while (true) {
      // advance odometer over the box [0..dJ]
      int q = 0;
      while (q < nv) {
        dk[q]++;
        K += L.stride[q];
        if (dk[q] <= dJ[q]) break;
        K -= dk[q] * L.stride[q];
        dk[q] = 0;
        q++;
      }
      if (q == nv || K == J) break;
      if (dk[v] == 0) continue;
      acc -= F[J - K] * Lj[K] * (double)dk[v];
    }
    Lj[J] = acc * inv / (double)Jv;
  }
}

// ---------------------------------------------------------------------------------------------
// mu-monomials (formal log t_l of jet variables)
// ---------------------------------------------------------------------------------------------
struct MuSet {
  int nv = 0, D = 0;
  vector<vector<uint8_t>> ex;  // exponents
  std::map<vector<uint8_t>, int> idx;
  vector<int> mult;  // mult[i*nm+j] = index of product or -1
  int nm = 0;
  void build(int nv_, int D_) {
    nv = nv_;
    D = D_;
    ex.clear();
    idx.clear();
    vector<uint8_t> e(nv, 0);
    // enumerate by total degree
    std::function<void(int, int)> rec = [&](int a, int rem) {
      if (a == nv) {
        ex.push_back(e);
        return;
      }
      for (int k = 0; k <= rem; k++) {
        e[a] = k;
        rec(a + 1, rem - k);
      }
      e[a] = 0;
    };
    rec(0, D);
    std::stable_sort(ex.begin(), ex.end(), [](const vector<uint8_t> &x, const vector<uint8_t> &y) {
      int sx = 0, sy = 0;
      for (auto v : x) sx += v;
      for (auto v : y) sy += v;
      return sx < sy;
    });
    nm = ex.size();
    for (int i = 0; i < nm; i++) idx[ex[i]] = i;
    mult.assign(nm * nm, -1);
    for (int i = 0; i < nm; i++)
      for (int j = 0; j < nm; j++) {
        vector<uint8_t> s(nv);
        int deg = 0;
        for (int a = 0; a < nv; a++) {
          s[a] = ex[i][a] + ex[j][a];
          deg += s[a];
        }
        if (deg <= D) mult[i * nm + j] = idx[s];
      }
  }
};

// ---------------------------------------------------------------------------------------------
// Laurent helpers
// ---------------------------------------------------------------------------------------------
// coefficients of (c+e)^{-(p+1)} * (-1)^p p!, orders lo..hi
static void pole_factor(int c, int p, int hi, int &lo, vector<double> &co) {
  double pf = (p % 2 ? -1.0 : 1.0);
  for (int i = 2; i <= p; i++) pf *= i;
  if (c == 0) {
    lo = -(p + 1);
    co.assign(hi - lo + 1 > 0 ? hi - lo + 1 : 0, 0.0);
    if (hi >= lo) co[0] = pf;
    return;
  }
  lo = 0;
  co.assign(hi + 1 > 0 ? hi + 1 : 0, 0.0);
  // (c+e)^{-(p+1)} = sum_i binom(-(p+1),i) c^{-(p+1)-i} e^i
  double b = 1.0;
  for (int i = 0; i <= hi; i++) {
    co[i] = pf * b * std::pow((double)c, -(double)(p + 1 + i));
    b *= (double)(-(p + 1) - i) / (double)(i + 1);
  }
}

// ---------------------------------------------------------------------------------------------
// Sector data
// ---------------------------------------------------------------------------------------------
struct SectorData {
  vector<int> ord;   // spacing index by rank (0-based rank)
  vector<int> rank;  // 1-based rank per spacing
  vector<int> rI;    // per sum: min rank
  vector<vector<int>> mr;  // per sum: ranks of non-max members
  vector<int> a, b;  // per variable l=1..d (index l-1)
  vector<int> sub;   // variable indices (0-based) in Sub
  vector<int> Nsub;
  int Nmax = 0;
  int lo = 0;  // lowest Laurent order
  // per S (bitmask over Sub positions): PF tables
  struct SInfo {
    vector<int> vars;  // positions in Sub
    MuSet mu;
    int nj = 1;
    int jstride[MAXV];
    int E = 0;  // e-order needed for V_S
    size_t vsize = 0;
    // PF per (mu index, j index): lo and coefficients up to etarget
    vector<int> pflo;
    vector<vector<double>> pf;
  };
  vector<SInfo> S;
};

static bool build_sector(const Problem &P, const vector<int> &ord, SectorData &sd, std::string &err) {
  int M = P.M, d = P.d;
  sd.ord = ord;
  sd.rank.assign(M, 0);
  for (int r = 0; r < M; r++) sd.rank[ord[r]] = r + 1;
  int ns = P.sums.size();
  sd.rI.assign(ns, 0);
  sd.mr.assign(ns, {});
  for (int I = 0; I < ns; I++) {
    int rmin = 1 << 30;
    for (int p : P.sums[I].mem) rmin = std::min(rmin, sd.rank[p]);
    sd.rI[I] = rmin;
    for (int p : P.sums[I].mem)
      if (sd.rank[p] != rmin) sd.mr[I].push_back(sd.rank[p]);
    std::sort(sd.mr[I].begin(), sd.mr[I].end());
  }
  int Kmax = 0;
  for (int p = 0; p < M; p++)
    if (P.internal[p]) Kmax = std::max(Kmax, sd.rank[p] - 1);
  sd.a.assign(d, 0);
  sd.b.assign(d, 0);
  sd.sub.clear();
  sd.Nsub.clear();
  sd.Nmax = 0;
  for (int l = 1; l <= d; l++) {
    int a = M - l;
    for (int I : P.pairs)
      if (sd.rI[I] > l) a += P.sums[I].wexp;
    if (P.iD >= 0 && sd.rI[P.iD] > l) a += 1;
    int b = (l <= Kmax) ? 1 : 0;
    a += P.s0 * b;
    sd.a[l - 1] = a;
    sd.b[l - 1] = b;
    if (a <= 0) {
      if (!b) {
        err = "unregulated divergence";
        return false;
      }
      sd.sub.push_back(l - 1);
      sd.Nsub.push_back(-a);
      sd.Nmax = std::max(sd.Nmax, -a);
    }
  }
  int K = sd.sub.size();
  if (K > MAXV) {
    err = "too many subtracted variables";
    return false;
  }
  sd.lo = -(K + P.Dmu);
  int nS = 1 << K;
  sd.S.assign(nS, {});
  for (int Sm = 0; Sm < nS; Sm++) {
    auto &si = sd.S[Sm];
    si.vars.clear();
    for (int k = 0; k < K; k++)
      if (Sm >> k & 1) si.vars.push_back(k);
    int ns_ = si.vars.size();
    si.mu.build(ns_, P.Dmu);
    si.nj = 1;
    for (int q = 0; q < ns_; q++) {
      si.jstride[q] = si.nj;
      si.nj *= (sd.Nsub[si.vars[q]] + 1);
    }
    si.E = P.etarget + ns_ + P.Dmu;
    if (si.E < 0) si.E = -1;
    si.vsize = (size_t)(si.E + 1) * si.mu.nm * si.nj;
    si.pflo.assign((size_t)si.mu.nm * si.nj, 0);
    si.pf.assign((size_t)si.mu.nm * si.nj, {});
    for (int im = 0; im < si.mu.nm; im++)
      for (int ij = 0; ij < si.nj; ij++) {
        // product over S vars of (-1)^p p! (c+e)^{-(p+1)}, c = a_k + j_k
        vector<int> cs, ps;
        int r = ij;
        for (int q = 0; q < ns_; q++) {
          int k = si.vars[q];
          int jk = r % (sd.Nsub[k] + 1);
          r /= (sd.Nsub[k] + 1);
          cs.push_back(sd.a[sd.sub[k]] + jk);
          ps.push_back(si.mu.ex[im][q]);
        }
        int lotot = 0;
        for (int q = 0; q < ns_; q++) lotot += (cs[q] == 0) ? -(ps[q] + 1) : 0;
        int lo = 0;
        vector<double> co(1, 1.0);
        int remlo = lotot;
        for (int q = 0; q < ns_; q++) {
          int lof = (cs[q] == 0) ? -(ps[q] + 1) : 0;
          remlo -= lof;  // sum of los of the factors still to come
          int hif = P.etarget - (lotot - lof);
          int lo2;
          vector<double> co2;
          pole_factor(cs[q], ps[q], hif, lo2, co2);
          int nlo = lo + lo2;
          int nhi = P.etarget - remlo;
          vector<double> nc(nhi - nlo + 1 > 0 ? nhi - nlo + 1 : 0, 0.0);
          for (size_t x = 0; x < co.size(); x++)
            for (size_t y = 0; y < co2.size(); y++) {
              int o = lo + (int)x + lo2 + (int)y;
              if (o <= nhi) nc[o - nlo] += co[x] * co2[y];
            }
          lo = nlo;
          co = nc;
        }
        si.pflo[(size_t)im * si.nj + ij] = lo;
        si.pf[(size_t)im * si.nj + ij] = co;
      }
  }
  return true;
}

// ---------------------------------------------------------------------------------------------
// Point evaluator (templated on scalar type)
// ---------------------------------------------------------------------------------------------
template <class T> struct ACtx {
  int Am = 0, SmallA = 0, nv = 0;
  int ordv[MAXV];
  int kOfA[MAXV];
  int posA[64];
  const Layout *Lp = nullptr;
  const LevelPairs *LV = nullptr;
  struct MemPlan {
    int slot;
    int nl;
    int ls[64];
  };
  struct SumPlan {
    int nslots = 1;  // slot 0 = constant
    uint16_t mask[64];
    int off[64];
    vector<MemPlan> mem;
  };
  vector<SumPlan> sp;
  MuSet *mu = nullptr;
  int muLin[MAXV];  // index of the degree-1 monomial mu_a
  vector<vector<int>> muSidx;                      // [Ssub][m]
  vector<vector<vector<std::pair<int, int>>>> muRest;  // [Ssub][m] -> (A position, power)
  int EA = 0;
  bool cacheValid = false;
  vector<vector<T>> GGcache;
  vector<vector<char>> mnzcache;
};

template <class T> struct Evaluator {
  const Problem &P;
  const SectorData &sd;
  int K;
  int mx;
  double tauC;
  vector<double> tauN;
  vector<int> mxN;
  double uprec = 2e-32, errTarget = 1e-13, tailMax = 0.02, maxJet = 200000, tailTol = 1e-13;
  long long nUnresolved = 0, nPoints = 0;
  int maxCacheMB = 400;
  int Dlog = 0;
  std::unordered_map<uint64_t, ACtx<T> *> cache;
  std::unordered_map<int, MuSet *> mcache;
  // buffers
  vector<T> R, scratch, scratch2, Lsig, G, wS, coefs, GG;
  vector<vector<T>> GGwork;
  vector<int> tgw;
  vector<vector<char>> MZwork;
  vector<double> wSd;
  T logtT[64];
  vector<T> RE;   // (EA+1)*size
  vector<T> Ins;  // nm*size
  vector<T> LI, pw, tmpf, prodb, ltp;
  vector<T> Sk[5], Ek[4];
  vector<vector<vector<T>>> V;  // [channel][Ssub]
  Evaluator(const Problem &P_, const SectorData &sd_, int mx_, double tauC_) : P(P_), sd(sd_), mx(mx_), tauC(tauC_) {
    K = sd.sub.size();
    // small-t thresholds.  Nested subtraction loses ~ u * prod_k t_k^{-(N_k+1)} (multiplicative over variables),
    // integrated ~ u * prod_k tau_k^{-N_k}.  Choose a common tau with u*tau^{-sumN} = 10^{-digits_lost_budget}:
    // tau = 10^{-T/sumN}, T = log10(target/u) passed in as tauC (= T).  Below tau the remainder is evaluated
    // from the Taylor tail (orders N+1..N+mx) at t=0 (no cancellation); tail truncation ~ (b*tau)^mx.
    tauN.assign(64, 0.0);
    mxN.assign(64, 0);
    int sumN = 0;
    for (int k = 0; k < K; k++) sumN += sd.Nsub[k];
    double tailtol = std::is_same<T, dd>::value ? 1e-16 : 1e-14;
    double tau = 0.0;
    if (sumN > 0) tau = std::pow(10.0, -tauC / sumN);
    if (tau > 0.05) tau = 0.05;
    int m = 0;
    if (tau > 0) m = (int)std::ceil(std::log(tailtol / tau) / std::log(2.0 * tau));
    if (m < 2) m = 2;
    if (mx > 0) m = mx;
    if (m > 40) m = 40;
    for (int Nn = 1; Nn < 64; Nn++) {
      tauN[Nn] = tau;
      mxN[Nn] = m;
    }
    uprec = std::is_same<T, dd>::value ? 2e-32 : 2.2e-16;
    errTarget = P.errTarget;
    tailMax = P.tailMax;
    maxJet = P.maxJet;
    tailTol = P.tailTol;
    Dlog = std::max(0, P.Dmu + P.etarget + K);
    V.assign(P.ch.size(), vector<vector<T>>(1 << K));
    TV.assign(1 << K, {});
    for (size_t c = 0; c < P.ch.size(); c++)
      for (int Sm = 0; Sm < (1 << K); Sm++) V[c][Sm].assign(sd.S[Sm].vsize, NT<T>::c(0.0));
  }
  ~Evaluator() {
    for (auto &kv : cache) delete kv.second;
    for (auto &kv : mcache) delete kv.second;
  }
  MuSet *muset(int nv) {
    auto it = mcache.find(nv);
    if (it != mcache.end()) return it->second;
    MuSet *m = new MuSet();
    m->build(nv, P.Dmu);
    mcache[nv] = m;
    return m;
  }
  size_t cacheBytes = 0;
  ACtx<T> *ctx(int Am, int SmallA, const int *Neff) {
    if (cacheBytes > (size_t)maxCacheMB * 1048576ull) {  // bound per-thread memory
      for (auto &kv : cache) delete kv.second;
      cache.clear();
      cacheBytes = 0;
    }
    uint64_t key = (uint64_t)Am;
    for (int k = 0; k < K; k++)
      if ((Am >> k) & 1) key = key * 64 + (uint64_t)(Neff[k] - sd.Nsub[k]);
    key = key * 4096 + (uint64_t)SmallA;
    auto it = cache.find(key);
    if (it != cache.end()) return it->second;
    ACtx<T> *C = new ACtx<T>();
    C->Am = Am;
    C->SmallA = SmallA;
    int d = P.d;
    for (int l = 0; l < d; l++) C->posA[l] = -1;
    int nv = 0;
    for (int k = 0; k < K; k++)
      if (Am >> k & 1) {
        C->ordv[nv] = Neff[k];
        C->kOfA[nv] = k;
        C->posA[sd.sub[k]] = nv;
        nv++;
      }
    C->nv = nv;
    C->Lp = get_layout(nv, C->ordv);
    const Layout &L = *C->Lp;
    // sum plans
    int ns = P.sums.size();
    C->sp.assign(ns, typename ACtx<T>::SumPlan());
    for (int I = 0; I < ns; I++) {
      auto &spl = C->sp[I];
      spl.nslots = 1;
      int r0 = sd.rI[I];
      for (int rg : sd.mr[I]) {
        typename ACtx<T>::MemPlan mp;
        mp.nl = 0;
        uint16_t mask = 0;
        bool drop = false;
        for (int l = r0; l <= rg - 1; l++) {
          int a = C->posA[l - 1];
          if (a >= 0) {
            if (L.ord[a] == 0) {
              drop = true;
              break;
            }
            mask |= (1u << a);
          } else
            mp.ls[mp.nl++] = l - 1;
        }
        if (drop) continue;
        int slot = 0;
        if (mask) {
          slot = -1;
          for (int q = 1; q < spl.nslots; q++)
            if (spl.mask[q] == mask) slot = q;
          if (slot < 0) {
            slot = spl.nslots++;
            spl.mask[slot] = mask;
            int off = 0;
            for (int a = 0; a < nv; a++)
              if (mask >> a & 1) off += L.stride[a];
            spl.off[slot] = off;
          }
        }
        mp.slot = slot;
        spl.mem.push_back(mp);
      }
    }
    {
      int Nb[MAXV];
      for (int a = 0; a < nv; a++) Nb[a] = sd.Nsub[C->kOfA[a]];
      C->LV = get_levels(L, Nb);
    }
    // mu maps
    if (P.Dmu > 0) {
      C->mu = muset(nv);
      MuSet &mu = *C->mu;
      for (int a = 0; a < nv; a++) {
        vector<uint8_t> e(nv, 0);
        e[a] = 1;
        C->muLin[a] = mu.idx.at(e);
      }
      C->muSidx.assign(1 << K, {});
      C->muRest.assign(1 << K, {});
      for (int Ssub = Am;; Ssub = (Ssub - 1) & Am) {
        auto &si = sd.S[Ssub];
        C->muSidx[Ssub].assign(mu.nm, -1);
        C->muRest[Ssub].assign(mu.nm, {});
        for (int m = 0; m < mu.nm; m++) {
          vector<uint8_t> exS(si.vars.size(), 0);
          for (int a = 0; a < nv; a++) {
            int k = C->kOfA[a];
            int p = mu.ex[m][a];
            if (Ssub >> k & 1) {
              int q = 0;
              while (si.vars[q] != k) q++;
              exS[q] = p;
            } else if (p > 0)
              C->muRest[Ssub][m].push_back({a, p});
          }
          auto it2 = si.mu.idx.find(exS);
          if (it2 != si.mu.idx.end()) C->muSidx[Ssub][m] = it2->second;
        }
        if (Ssub == 0) break;
      }
    }
    cacheBytes += sizeof(ACtx<T>) + 64 * C->sp.size() * 8 + (size_t)C->Lp->size * 64;
    cache[key] = C;
    return C;
  }

  void build_sparse(const ACtx<T> &C, int I, const double *t, Sparse<T> &s) {
    const auto &spl = C.sp[I];
    T cs[64];
    for (int q = 0; q < spl.nslots; q++) cs[q] = NT<T>::c(0.0);
    (void)0;
    for (const auto &mp : spl.mem) {
      T co = NT<T>::c(1.0);
      for (int u = 0; u < mp.nl; u++) co = co * NT<T>::c(t[mp.ls[u]]);
      cs[mp.slot] += co;
    }
    s.c0 = NT<T>::c(1.0) + cs[0];
    s.nt = spl.nslots - 1;
    for (int q = 1; q < spl.nslots; q++) {
      s.mask[q - 1] = spl.mask[q];
      s.off[q - 1] = spl.off[q];
      s.coef[q - 1] = cs[q];
    }
  }

  void eval(const double *t, const double *logwk, vector<vector<double>> &out) {
    const int d = P.d;
    double logt[64];
    for (int l = 0; l < d; l++) {
      logt[l] = std::log(t[l]);
      logtT[l] = std::is_same<T, dd>::value ? NT<T>::lg(NT<T>::c(t[l])) : NT<T>::c(logt[l]);
    }
    // Adaptive choice of tail ("Small") variables.  The nested subtraction loses relative precision
    //   err ~ u * prod_{k subtracted directly} t_k^{-(N_k+1)} (1+|log t_k|)^{Dlog}
    // (multiplicative over variables, log factors from insertions and the e-expansion).  While the
    // estimate exceeds errTarget, the worst variable (if t_k < tailMax) is switched to tail mode: its remainder
    // is evaluated from Taylor orders N_k+1..N_k+mx_k at t_k=0 (no cancellation), mx_k chosen so that
    // (4 t_k)^mx_k < 1e-16.
    int Smallm = 0;
    int Neff[MAXV];
    double lk[MAXV];
    double sumabslog = 0;
    for (int l = 0; l < d; l++) sumabslog += std::fabs(logt[l]);
    // absolute error of the integrand ~ u * prod_direct t_k^{-(N_k+1)} * (1+sum|log t|)^Dlog
    double lerr = std::log(uprec) + Dlog * std::log(1.0 + sumabslog);
    for (int k = 0; k < K; k++) {
      Neff[k] = sd.Nsub[k];
      lk[k] = -(sd.Nsub[k] + 1) * logt[sd.sub[k]];
      lerr += lk[k];
    }
    const double ltarget = std::log(errTarget);
    double jsize = 1;
    for (int k = 0; k < K; k++) jsize *= (Neff[k] + 1);
    while (lerr > ltarget) {
      int best = -1;
      double bl = 0;
      for (int k = 0; k < K; k++)
        if (!((Smallm >> k) & 1) && t[sd.sub[k]] < tailMax && lk[k] > bl) {
          bl = lk[k];
          best = k;
        }
      if (best < 0) break;
      double tk = t[sd.sub[best]];
      int m = (int)std::ceil(std::log10(tailTol) / std::log10(4.0 * tk));
      static const int steps[] = {3, 4, 6, 8, 12, 16, 24};
      int mm = 24;
      for (int st : steps)
        if (st >= m) {
          mm = st;
          break;
        }
      double nsize = jsize / (Neff[best] + 1) * (sd.Nsub[best] + mm + 1);
      if (nsize > maxJet) {  // keep jets bounded: leave this variable in direct mode
        lk[best] = -1;
        continue;
      }
      jsize = nsize;
      Smallm |= (1 << best);
      lerr -= (lk[best] > 0 ? lk[best] : 0);
      Neff[best] = sd.Nsub[best] + mm;
    }
    nPoints++;
    if (lerr > ltarget + 4.6) nUnresolved++;  // estimated error > 100 x target (diagnostic, reported per sector)
    for (size_t c = 0; c < P.ch.size(); c++)
      for (int Sm = 0; Sm < (1 << K); Sm++) std::fill(V[c][Sm].begin(), V[c][Sm].end(), NT<T>::c(0.0));
    int freeMask = ((1 << K) - 1) & ~Smallm;
    for (int sub = freeMask;; sub = (sub - 1) & freeMask) {
      int Am = sub | Smallm;
      ACtx<T> *C = ctx(Am, Smallm, Neff);
      process_A(*C, Smallm, t, logt);
      if (sub == 0) break;
    }
    for (size_t c = 0; c < P.ch.size(); c++) assemble(c, t, logt, logwk, out);
  }

  // jets of the smooth integrand for context C (all channels): fills GGout[c] (layout [m][i][x]) and mnzout[c]
  void compute_jets(ACtx<T> &C, const double *t, const double *logt, int EA, vector<vector<T>> &GGout,
                    vector<vector<char>> &mnzout) {
    const Layout &L = *C.Lp;
    int sz = L.size, nv = C.nv;
    // rational part: W = Q^2,  Q = prod_{same-charge pairs}(1+P) / prod_{opposite}(1+P)  (all |wexp| = 2)
    for (int i = 0; i < sz; i++) R[i] = NT<T>::c(0.0);
    R[0] = NT<T>::c(1.0);
    Sparse<T> s;
    T qconst = NT<T>::c(1.0);
    for (int I : P.pairs) {
      build_sparse(C, I, t, s);
      if (s.nt == 0) {
        if (P.sums[I].wexp > 0)
          qconst = qconst * s.c0;
        else
          qconst = qconst / s.c0;
        continue;
      }
      if (P.sums[I].wexp > 0)
        sp_mul(R.data(), s, L);
      else
        sp_div(R.data(), s, L);
    }
    for (int i = 0; i < sz; i++) R[i] = R[i] * qconst;
    if (sz == 1) {
      R[0] = R[0] * R[0];
    } else {
      for (int i = 0; i < sz; i++) scratch2[i] = R[i];
      for (int i = 0; i < sz; i++) R[i] = NT<T>::c(0.0);
      conv_add(R.data(), scratch2.data(), scratch2.data(), L);
    }
    if (P.iD >= 0) {
      build_sparse(C, P.iD, t, s);
      sp_mul(R.data(), s, L);
    }
    Sparse<T> ssig;
    build_sparse(C, P.iSig, t, ssig);
    int pwr = -(P.kappa + P.s0);
    for (int i = 0; i < std::abs(pwr); i++) {
      if (pwr > 0)
        sp_mul(R.data(), ssig, L);
      else
        sp_div(R.data(), ssig, L);
    }
    bool needLsig = (EA > 0) || (P.Dmu > 0);
    if (needLsig) sp_log(Lsig.data(), ssig, L, scratch.data());
    if ((int)RE.size() < (EA + 1) * sz) RE.resize((EA + 1) * sz);
    for (int i = 0; i < sz; i++) RE[i] = R[i];
    for (int i = 1; i <= EA; i++) {
      T *dst = &RE[(size_t)i * sz];
      for (int x = 0; x < sz; x++) dst[x] = NT<T>::c(0.0);
      int lv = std::min(EA - i, nv);  // outputs with more tail digits than lv are never used at this order
      conv_add(dst, &RE[(size_t)(i - 1) * sz], Lsig.data(), L, -1.0 / i, C.LV->nB.data(), lv);
    }
    int nm = (P.Dmu > 0) ? C.mu->nm : 1;
    GGout.resize(P.ch.size() + 1);
    mnzout.resize(P.ch.size() + 1);
    // extra entry: the base jets RE (for constant insertion components)
    GGout[P.ch.size()].assign(RE.begin(), RE.begin() + (size_t)(EA + 1) * sz);
    mnzout[P.ch.size()].assign(1, 1);
    for (size_t c = 0; c < P.ch.size(); c++) {
      const Channel &Ch = P.ch[c];
      if ((int)Ins.size() < nm * sz) Ins.resize(nm * sz);
      if (P.Dmu == 0) {
        double cst = 0;
        for (auto &tm : Ch.terms) cst += tm.coef;
        for (int x = 0; x < sz; x++) Ins[x] = NT<T>::c(0.0);
        Ins[0] = NT<T>::c(cst);
      } else {
        build_insertion(C, Ch, t, logt);
      }
      vector<T> &GGc = GGout[c];
      if (GGc.size() < (size_t)nm * (EA + 1) * sz) GGc.resize((size_t)nm * (EA + 1) * sz);
      mnzout[c].assign(nm, 0);
      for (int m = 0; m < nm; m++) {
        const T *insm = &Ins[(size_t)m * sz];
        bool any = false, cst = true;
        for (int x = 0; x < sz; x++)
          if (NT<T>::d(insm[x]) != 0.0) {
            any = true;
            if (x > 0) cst = false;
          }
        mnzout[c][m] = any;
        if (!any) continue;
        if (cst && P.Dmu > 0) {
          // constant insertion component: G = insm[0] * RE; contracted once (from RE) in process_A
          mnzout[c][m] = 2;
          GGc[((size_t)m * (EA + 1)) * sz] = insm[0];
          continue;
        }
        for (int i = 0; i <= EA; i++) {
          T *g = &GGc[((size_t)m * (EA + 1) + i) * sz];
          const T *re = &RE[(size_t)i * sz];
          if (cst) {
            for (int x = 0; x < sz; x++) g[x] = re[x] * insm[0];
          } else {
            for (int x = 0; x < sz; x++) g[x] = NT<T>::c(0.0);
            int lv = std::min(EA - i, nv);
            conv_add(g, re, insm, L, 1.0, C.LV->nB.data(), lv);
          }
        }
      }
    }
  }

  void process_A(ACtx<T> &C, int Smallm, const double *t, const double *logt) {
    const Layout &L = *C.Lp;
    int sz = L.size, nv = C.nv;
    int EA = P.etarget + nv + P.Dmu;
    if (EA < 0) return;
    if ((int)R.size() < sz) {
      R.resize(sz);
      scratch.resize(sz);
      Lsig.resize(sz);
      G.resize(sz);
      wS.resize(sz);
      wSd.resize(sz);
      scratch2.resize(sz);
    }
    // jets depend only on the variables outside A: if A contains every variable they are constants
    vector<vector<T>> *GGp;
    vector<vector<char>> *MZp;
    if (nv == P.d) {
      if (!C.cacheValid) {
        compute_jets(C, t, logt, EA, C.GGcache, C.mnzcache);
        C.cacheValid = true;
        for (auto &v : C.GGcache) cacheBytes += v.size() * sizeof(T);
      }
      GGp = &C.GGcache;
      MZp = &C.mnzcache;
    } else {
      compute_jets(C, t, logt, EA, GGwork, MZwork);
      GGp = &GGwork;
      MZp = &MZwork;
    }
    // weights per A var
    T wt[MAXV][64];
    for (int a = 0; a < nv; a++) {
      int k = C.kOfA[a];
      int l = sd.sub[k];
      int Nk = sd.Nsub[k];
      bool sm = (Smallm >> k) & 1;
      T tp = NT<T>::c(1.0);
      for (int j = 0; j <= L.ord[a]; j++) {
        if (sm)
          wt[a][j] = (j > Nk) ? tp : NT<T>::c(0.0);
        else
          wt[a][j] = -tp;
        tp = tp * NT<T>::c(t[l]);
      }
    }
    int nm = (P.Dmu > 0) ? C.mu->nm : 1;
    // Contraction for all S subset of A at once, variable by variable (keep: restrict the axis to digits <= N;
    // contract: weighted sum over the axis).  Cost ~ size * prod_a(1 + 1/(N_a+1)) instead of size * 2^|A|.
    for (int a = 0; a < nv; a++) {
      cdims0[a] = L.ord[a] + 1;
      Nkeep[a] = sd.Nsub[C.kOfA[a]] + 1;
    }
    // constant insertion components: contract the base jets once into TV[S], then distribute
    bool anyConst = false;
    for (size_t c = 0; c < P.ch.size(); c++)
      for (int m = 0; m < nm; m++)
        if ((*MZp)[c][m] == 2) anyConst = true;
    if (anyConst) {
      tempMode = true;
      for (int Ssub = C.Am;; Ssub = (Ssub - 1) & C.Am) {
        auto &si = sd.S[Ssub];
        size_t need = (size_t)(std::max(si.E, 0) + 1) * si.nj;
        if (TV[Ssub].size() < need) TV[Ssub].resize(need);
        for (size_t x = 0; x < need; x++) TV[Ssub][x] = NT<T>::c(0.0);
        if (Ssub == 0) break;
      }
      contract_rec(C, 0, (*GGp)[P.ch.size()].data(), cdims0, 0, wt, EA + 1, sz, P.etarget + P.Dmu);
      tempMode = false;
      for (size_t c = 0; c < P.ch.size(); c++) {
        const vector<T> &GGc = (*GGp)[c];
        for (int m = 0; m < nm; m++) {
          if ((*MZp)[c][m] != 2) continue;
          T cst = GGc[((size_t)m * (EA + 1)) * sz];
          for (int Ssub = C.Am;; Ssub = (Ssub - 1) & C.Am) {
            auto &si = sd.S[Ssub];
            if (si.E >= 0) {
              int muS = C.muSidx[Ssub][m];
              if (muS >= 0) {
                T muw = cst;
                for (auto &pr : C.muRest[Ssub][m])
                  for (int r = 0; r < pr.second; r++) muw = muw * logtT[sd.sub[C.kOfA[pr.first]]];
                int ie = std::min(si.E - (P.etarget - std::min(P.etarget, P.ch[c].etarget)), EA);
                for (int i = 0; i <= ie; i++) {
                  T *Vs = V[c][Ssub].data() + ((size_t)i * si.mu.nm + muS) * si.nj;
                  const T *tv = &TV[Ssub][(size_t)i * si.nj];
                  for (int j = 0; j < si.nj; j++) Vs[j] += tv[j] * muw;
                }
              }
            }
            if (Ssub == 0) break;
          }
        }
      }
    }
    for (size_t c = 0; c < P.ch.size(); c++) {
      const vector<T> &GGc = (*GGp)[c];
      const vector<char> &mnz = (*MZp)[c];
      for (int m = 0; m < nm; m++) {
        if (mnz[m] != 1) continue;
        // batch over the e-orders: layout [i][x], i is an extra outermost (never contracted) axis
        const T *g = &GGc[((size_t)m * (EA + 1)) * sz];
        cur_c = (int)c;
        cur_m = m;
        // a contracted variable lowers the largest reachable |S| and hence the largest useful e-order
        int chet = std::min(P.etarget, P.ch[c].etarget);
        int ibase = chet + P.Dmu;
        contract_rec(C, 0, g, cdims0, 0, wt, std::min(EA, chet + nv + P.Dmu) + 1, sz, ibase);
      }
    }
  }

  // recursive keep/contract over the A variables; at the leaf emit into V_S.
  // src layout: [i < ni][tensor with dims], tensor size tsz; e-orders i > ibase + kept + remaining are useless
  int cdims0[MAXV], Nkeep[MAXV];
  int cur_c = 0, cur_m = 0;
  bool tempMode = false;
  vector<vector<T>> TV;
  vector<T> cbuf[MAXV + 1][2];
  void contract_rec(ACtx<T> &C, int a, const T *src, const int *dims, int keepmask, T (*wt)[64], int ni, int tsz,
                    int ibase) {
    const int nv = C.nv;
    int nkept = __builtin_popcount(keepmask);
    int imax = std::min(ni - 1, ibase + nkept + (nv - a));
    if (imax < 0) return;
    if (a == nv) {
      int Ssub = 0;
      for (int b = 0; b < nv; b++)
        if ((keepmask >> b) & 1) Ssub |= (1 << C.kOfA[b]);
      auto &si = sd.S[Ssub];
      if (tempMode) {
        int ie = std::min(imax, si.E);
        for (int i = 0; i <= ie; i++) {
          T *tv = &TV[Ssub][(size_t)i * si.nj];
          const T *sp = src + (size_t)i * tsz;
          for (int j = 0; j < si.nj; j++) tv[j] += sp[j];
        }
        return;
      }
      int muS = 0;
      T muw = NT<T>::c(1.0);
      if (P.Dmu > 0) {
        muS = C.muSidx[Ssub][cur_m];
        if (muS < 0) return;
        for (auto &pr : C.muRest[Ssub][cur_m])
          for (int r = 0; r < pr.second; r++) muw = muw * logtT[sd.sub[C.kOfA[pr.first]]];
      }
      int ie = std::min(imax, si.E - (P.etarget - std::min(P.etarget, P.ch[cur_c].etarget)));
      for (int i = 0; i <= ie; i++) {
        T *Vs = V[cur_c][Ssub].data() + ((size_t)i * si.mu.nm + muS) * si.nj;
        const T *sp = src + (size_t)i * tsz;
        for (int j = 0; j < si.nj; j++) Vs[j] += sp[j] * muw;
      }
      return;
    }
    int inner = 1, outer = 1;
    for (int b = 0; b < a; b++) inner *= dims[b];
    for (int b = a + 1; b < nv; b++) outer *= dims[b];
    int da = dims[a];
    int nd[MAXV];
    for (int b = 0; b < nv; b++) nd[b] = dims[b];
    int nib = imax + 1;  // e-orders still useful
    // keep
    {
      int dk = Nkeep[a];
      nd[a] = dk;
      size_t ntsz = (size_t)inner * dk * outer;
      vector<T> &dst = cbuf[a][0];
      if (dst.size() < ntsz * nib) dst.resize(ntsz * nib);
      for (int i = 0; i < nib; i++)
        for (int o = 0; o < outer; o++)
          for (int j = 0; j < dk; j++) {
            const T *sp = src + (size_t)i * tsz + ((size_t)o * da + j) * inner;
            T *dp = &dst[i * ntsz + ((size_t)o * dk + j) * inner];
            for (int x = 0; x < inner; x++) dp[x] = sp[x];
          }
      contract_rec(C, a + 1, dst.data(), nd, keepmask | (1 << a), wt, nib, (int)ntsz, ibase);
    }
    // contract
    {
      nd[a] = 1;
      int nibc = std::min(nib, ibase + nkept + (nv - a - 1) + 1);
      if (nibc <= 0) return;
      size_t ntsz = (size_t)inner * outer;
      vector<T> &dst = cbuf[a][1];
      if (dst.size() < ntsz * nibc) dst.resize(ntsz * nibc);
      for (size_t x = 0; x < ntsz * nibc; x++) dst[x] = NT<T>::c(0.0);
      for (int i = 0; i < nibc; i++)
        for (int o = 0; o < outer; o++)
          for (int j = 0; j < da; j++) {
            const T w = wt[a][j];
            if (NT<T>::d(w) == 0.0) continue;
            const T *sp = src + (size_t)i * tsz + ((size_t)o * da + j) * inner;
            T *dp = &dst[i * ntsz + (size_t)o * inner];
            for (int x = 0; x < inner; x++) dp[x] += sp[x] * w;
          }
      contract_rec(C, a + 1, dst.data(), nd, keepmask, wt, nibc, (int)ntsz, ibase);
    }
  }

  // ---- insertion polynomials (formal in mu over the A variables)
  void formal_L(const ACtx<T> &C, int I, const double *t, const double *logt, T *out) {
    const Layout &L = *C.Lp;
    const MuSet &mu = *C.mu;
    int sz = L.size;
    for (int i = 0; i < mu.nm * sz; i++) out[i] = NT<T>::c(0.0);
    Sparse<T> s;
    build_sparse(C, I, t, s);
    sp_log(out, s, L, scratch.data());
    for (int x = 0; x < sz; x++) out[x] -= Lsig[x];
    int r0 = sd.rI[I];
    T lam = NT<T>::c(0.0);
    for (int l = 1; l < r0; l++) {
      int a = C.posA[l - 1];
      if (a >= 0) {
        out[(size_t)C.muLin[a] * sz] += NT<T>::c(1.0);
      } else
        lam += logtT[l - 1];
    }
    out[0] += lam;
  }
  // out = sum_I coef_I L_I  (formal in mu over A), coef_I = +-1:  jet part = log prod (1+P_I)^{coef_I}
  void formal_linear(const ACtx<T> &C, const vector<std::pair<int, int>> &terms, const double *t, const double *logt,
                     T *out) {
    const Layout &L = *C.Lp;
    const MuSet &mu = *C.mu;
    int sz = L.size;
    for (int i = 0; i < mu.nm * sz; i++) out[i] = NT<T>::c(0.0);
    // product jet
    for (int i = 0; i < sz; i++) scratch2[i] = NT<T>::c(0.0);
    scratch2[0] = NT<T>::c(1.0);
    Sparse<T> s;
    T cst = NT<T>::c(1.0);
    int csum = 0;
    T lam = NT<T>::c(0.0);
    double muc[MAXV] = {0};
    for (auto &pr : terms) {
      int I = pr.first, cf = pr.second;
      csum += cf;
      build_sparse(C, I, t, s);
      if (s.nt == 0) {
        cst = (cf > 0) ? cst * s.c0 : cst / s.c0;
      } else if (cf > 0)
        sp_mul(scratch2.data(), s, L);
      else
        sp_div(scratch2.data(), s, L);
      int r0 = sd.rI[I];
      for (int l = 1; l < r0; l++) {
        int a = C.posA[l - 1];
        if (a >= 0)
          muc[a] += cf;
        else
          lam += (cf > 0) ? logtT[l - 1] : -logtT[l - 1];
      }
    }
    for (int i = 0; i < sz; i++) scratch2[i] = scratch2[i] * cst;
    dense_log(out, scratch2.data(), L);
    for (int x = 0; x < sz; x++) out[x] -= Lsig[x] * (double)csum;
    out[0] += lam;
    if (mu.D >= 1)
      for (int a = 0; a < mu.nv; a++)
        if (muc[a] != 0) out[(size_t)C.muLin[a] * sz] += NT<T>::c(muc[a]);
  }
  void fmul(const T *a, const T *b, T *c, const ACtx<T> &C) {
    const MuSet &mu = *C.mu;
    int sz = C.Lp->size;
    for (int i = 0; i < mu.nm * sz; i++) c[i] = NT<T>::c(0.0);
    for (int i = 0; i < mu.nm; i++) {
      bool za = true;
      for (int x = 0; x < sz; x++)
        if (NT<T>::d(a[(size_t)i * sz + x]) != 0.0) {
          za = false;
          break;
        }
      if (za) continue;
      for (int j = 0; j < mu.nm; j++) {
        int k = mu.mult[i * mu.nm + j];
        if (k < 0) continue;
        conv_add(&c[(size_t)k * sz], &a[(size_t)i * sz], &b[(size_t)j * sz], *C.Lp);
      }
    }
  }
  void build_insertion(const ACtx<T> &C, const Channel &Ch, const double *t, const double *logt) {
    const MuSet &mu = *C.mu;
    const Layout &L = *C.Lp;
    int sz = C.Lp->size;
    size_t fs = (size_t)mu.nm * sz;
    int maxS = 0, maxE = 0;
    for (auto &tm : Ch.terms) {
      for (int k = 0; k < 4; k++)
        if (tm.ex[k]) maxS = std::max(maxS, k + 1);
      for (int k = 0; k < 3; k++)
        if (tm.ex[4 + k]) maxE = std::max(maxE, k + 1);
    }
    LI.resize(fs);
    pw.resize(fs);
    tmpf.resize(fs);
    prodb.resize(fs);
    for (int k = 1; k <= maxS; k++) Sk[k].assign(fs, NT<T>::c(0.0));
    for (int k = 1; k <= maxE; k++) Ek[k].assign(fs, NT<T>::c(0.0));
    // L_I = lambda_I (mu-linear, constant coefficients) + lt_I (pure jet):
    //   L^k = sum_p binom(k,p) lambda^p lt^{k-p}  -> only jet powers of lt need convolutions
    auto accum = [&](const vector<int> &idxs, int maxk, vector<T> *Arr) {
      if ((int)ltp.size() < (maxk + 1) * sz) ltp.resize((size_t)(maxk + 1) * sz);
      vector<double> lamp((size_t)(maxk + 1) * mu.nm, 0.0), lam1(mu.nm, 0.0), tmpm(mu.nm, 0.0);
      for (int I : idxs) {
        formal_L(C, I, t, logt, LI.data());  // LI[0] = lt jet; LI[m>0] = mu-linear constants at index 0
        double q = P.sums[I].qcoef;
        // jet powers lt^0..lt^maxk
        for (int x = 0; x < sz; x++) ltp[x] = NT<T>::c(0.0);
        ltp[0] = NT<T>::c(1.0);
        for (int x = 0; x < sz; x++) ltp[sz + x] = LI[x];
        for (int k = 2; k <= maxk; k++) {
          T *dst = &ltp[(size_t)k * sz];
          for (int x = 0; x < sz; x++) dst[x] = NT<T>::c(0.0);
          conv_add(dst, &ltp[(size_t)(k - 1) * sz], LI.data(), L);
        }
        // constant mu-polynomial powers of lambda
        std::fill(lam1.begin(), lam1.end(), 0.0);
        for (int m = 1; m < mu.nm; m++) lam1[m] = NT<T>::d(LI[(size_t)m * sz]);
        std::fill(lamp.begin(), lamp.end(), 0.0);
        lamp[0] = 1.0;
        for (int p = 1; p <= maxk; p++)
          for (int m1 = 0; m1 < mu.nm; m1++) {
            double a = lamp[(size_t)(p - 1) * mu.nm + m1];
            if (a == 0.0) continue;
            for (int m2 = 1; m2 < mu.nm; m2++) {
              if (lam1[m2] == 0.0) continue;
              int k = mu.mult[m1 * mu.nm + m2];
              if (k >= 0) lamp[(size_t)p * mu.nm + k] += a * lam1[m2];
            }
          }
        for (int k = 1; k <= maxk; k++) {
          double binom = 1.0;
          for (int p = 0; p <= k; p++) {
            if (p > 0) binom = binom * (k - p + 1) / p;
            const T *lj = &ltp[(size_t)(k - p) * sz];
            for (int m = 0; m < mu.nm; m++) {
              double c = lamp[(size_t)p * mu.nm + m];
              if (c == 0.0) continue;
              T *dst = &Arr[k][(size_t)m * sz];
              double f = q * binom * c;
              for (int x = 0; x < sz; x++) dst[x] += lj[x] * f;
            }
          }
        }
      }
    };
    // degree-1 sums via the log of a product (one log instead of one per sum)
    if (maxS == 1) {
      vector<std::pair<int, int>> tl;
      for (int I : P.pairs) tl.push_back({I, (int)P.sums[I].qcoef});
      formal_linear(C, tl, t, logt, Sk[1].data());
    } else if (maxS > 1)
      accum(P.pairs, maxS, Sk);
    if (maxE == 1) {
      vector<std::pair<int, int>> tl;
      for (int I : P.eps) tl.push_back({I, (int)P.sums[I].qcoef});
      formal_linear(C, tl, t, logt, Ek[1].data());
    } else if (maxE > 1)
      accum(P.eps, maxE, Ek);
    if ((int)Ins.size() < (int)fs) Ins.resize(fs);
    for (size_t i = 0; i < fs; i++) Ins[i] = NT<T>::c(0.0);
    for (auto &tm : Ch.terms) {
      bool first = true;
      for (int k = 0; k < 7; k++)
        for (int r = 0; r < tm.ex[k]; r++) {
          const vector<T> &f = (k < 4) ? Sk[k + 1] : Ek[k - 3];
          if (first) {
            for (size_t i = 0; i < fs; i++) prodb[i] = f[i] * tm.coef;
            first = false;
          } else {
            fmul(prodb.data(), f.data(), tmpf.data(), C);
            std::copy(tmpf.begin(), tmpf.begin() + fs, prodb.begin());
          }
        }
      if (first) {
        for (size_t i = 0; i < fs; i++) prodb[i] = NT<T>::c(0.0);
        prodb[0] = NT<T>::c(tm.coef);
      }
      for (size_t i = 0; i < fs; i++) Ins[i] += prodb[i];
    }
  }

  void assemble(int c, const double *t, const double *logt, const double *logwk, vector<vector<double>> &out) {
    const int d = P.d;
    for (int Sm = 0; Sm < (1 << K); Sm++) {
      auto &si = sd.S[Sm];
      if (si.E < 0) continue;
      double lmono = 0.0;
      double lsum = 0.0;
      char inS[64] = {0};
      for (int k : si.vars) inS[sd.sub[k]] = 1;
      // pole variables are not integrated: their transform Jacobian is dropped (exact integration in that
      // coordinate); bulk variables carry Jacobian * t^{a-1}
      for (int l = 0; l < d; l++)
        if (!inS[l]) {
          lmono += logwk[l] + (double)(sd.a[l] - 1) * logt[l];
          if (sd.b[l]) lsum += logt[l];
        }
      double mono = std::exp(lmono);
      if (mono == 0.0 || !std::isfinite(mono)) continue;
      int E = si.E;
      double Bs[64];
      Bs[0] = mono;
      for (int i = 1; i <= E; i++) Bs[i] = Bs[i - 1] * lsum / i;
      const vector<T> &Vv = V[c][Sm];
      for (int im = 0; im < si.mu.nm; im++)
        for (int ij = 0; ij < si.nj; ij++) {
          int lo = si.pflo[(size_t)im * si.nj + ij];
          const vector<double> &pf = si.pf[(size_t)im * si.nj + ij];
          if (pf.empty()) continue;
          double VB[64];
          bool nzv = false;
          for (int i = 0; i <= E; i++) {
            double acc = 0;
            for (int i2 = 0; i2 <= i; i2++) acc += NT<T>::d(Vv[((size_t)i2 * si.mu.nm + im) * si.nj + ij]) * Bs[i - i2];
            VB[i] = acc;
            if (acc != 0.0) nzv = true;
          }
          if (!nzv) continue;
          for (size_t x = 0; x < pf.size(); x++) {
            int o1 = lo + (int)x;
            if (pf[x] == 0.0) continue;
            for (int i = 0; i <= E; i++) {
              int o = o1 + i;
              if (o > std::min(P.etarget, P.ch[c].etarget)) break;
              out[c][o - sd.lo] += pf[x] * VB[i];
            }
          }
        }
    }
  }
};

// ---------------------------------------------------------------------------------------------
// Lattice / transforms / RNG
// ---------------------------------------------------------------------------------------------
static inline uint64_t splitmix64(uint64_t &x) {
  uint64_t z = (x += 0x9E3779B97F4A7C15ull);
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
  return z ^ (z >> 31);
}
static inline void korobov_tf(int r, double u, double &t, double &dt) {
  switch (r) {
    case 0:
      t = u;
      dt = 1.0;
      return;
    case 1:
      t = u * u * (3 - 2 * u);
      dt = 6 * u * (1 - u);
      return;
    case 2:
      t = u * u * u * (10 - 15 * u + 6 * u * u);
      dt = 30 * u * u * (1 - u) * (1 - u);
      return;
    case 3: {
      double u2 = u * u;
      t = u2 * u2 * (35 - 84 * u + 70 * u2 - 20 * u2 * u);
      double v = u * (1 - u);
      dt = 140 * v * v * v;
      return;
    }
    case 4: {
      double u2 = u * u, u4 = u2 * u2;
      t = u4 * u * (126 - 420 * u + 540 * u2 - 315 * u2 * u + 70 * u4);
      double v = u * (1 - u);
      dt = 630 * v * v * v * v;
      return;
    }
  }
  t = u;
  dt = 1;
}

static double korobov_P2(long long N, int d, long long a, double gam = 0.1) {
  // weighted P_alpha (alpha=2) for the Korobov vector (1,a,a^2,...) mod N with product weights gam:
  // small gam emphasizes the low-dimensional projections, which matter here because the pole
  // (lower-dimensional) terms of every sector are integrated with projections of the same lattice
  vector<long long> z(d);
  z[0] = 1;
  for (int j = 1; j < d; j++) z[j] = (__int128)z[j - 1] * a % N;
  double s = 0;
  const double c = gam * 2 * M_PI * M_PI;
  for (long long k = 0; k < N; k++) {
    double p = 1;
    for (int j = 0; j < d; j++) {
      double x = (double)((__int128)k * z[j] % N) / N;
      p *= 1 + c * (x * x - x + 1.0 / 6.0);
    }
    s += p;
  }
  return s / N - 1;
}

// ---------------------------------------------------------------------------------------------
// Sector enumeration
// ---------------------------------------------------------------------------------------------
static void enum_sectors(const Problem &P, vector<vector<int>> &out) {
  vector<int> perm(P.M);
  std::iota(perm.begin(), perm.end(), 0);
  out.clear();
  do {
    if (P.fold && P.M >= 2) {
      vector<int> mir(P.M);
      for (int r = 0; r < P.M; r++) mir[r] = mirror_index(P, perm[r]);
      if (!(perm < mir)) continue;
    }
    out.push_back(perm);
  } while (std::next_permutation(perm.begin(), perm.end()));
}

// ---------------------------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------------------------
static void parse(Problem &P, const char *fn) {
  std::ifstream in(fn);
  if (!in) {
    fprintf(stderr, "cannot open %s\n", fn);
    exit(2);
  }
  std::string line;
  Channel *cur = nullptr;
  while (std::getline(in, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::istringstream ss(line);
    std::string key;
    ss >> key;
    if (key == "n") ss >> P.n;
    else if (key == "type") { std::string s; ss >> s; P.type = s[0]; }
    else if (key == "geom") { std::string s; ss >> s; P.full = (s == "full"); }
    else if (key == "s0") ss >> P.s0;
    else if (key == "etarget") ss >> P.etarget;
    else if (key == "prec") ss >> P.prec;
    else if (key == "tauC_d") ss >> P.tauC_d;
    else if (key == "tauC_dd") ss >> P.tauC_dd;
    else if (key == "mx_dd") ss >> P.mx_dd;
    else if (key == "mx_d") ss >> P.mx_d;
    else if (key == "errTarget") ss >> P.errTarget;
    else if (key == "tailMax") ss >> P.tailMax;
    else if (key == "maxJet") ss >> P.maxJet;
    else if (key == "tailTol") ss >> P.tailTol;
    else if (key == "transform") ss >> P.transform;
    else if (key == "N") ss >> P.N;
    else if (key == "z") { long long v; P.z.clear(); while (ss >> v) P.z.push_back(v); }
    else if (key == "korobov") {
      long long a; ss >> a; P.z.clear(); long long v = 1;
      for (int j = 0; j < 64; j++) { P.z.push_back(v); v = (__int128)v * a % P.N; }
    }
    else if (key == "shifts") ss >> P.shifts;
    else if (key == "seed") ss >> P.seed;
    else if (key == "sectors") ss >> P.secStart >> P.secEnd;
    else if (key == "sectorstride") { ss >> P.secStride; if (!(ss >> P.secOffset)) P.secOffset = 0; }
    else if (key == "threads") ss >> P.nthreads;
    else if (key == "persector") { int v; ss >> v; P.persector = v; }
    else if (key == "persector_rep") { int v; ss >> v; P.persectorRep = v; }
    else if (key == "taskshifts") ss >> P.taskShifts;
    else if (key == "longestfirst") { int v; ss >> v; P.longestFirst = v; }
    else if (key == "fold") { int v; ss >> v; P.fold = v; }
    else if (key == "out") ss >> P.out;
    else if (key == "channel") {
      P.ch.push_back(Channel());
      cur = &P.ch.back();
      ss >> cur->name;
    } else if (key == "chet") {
      ss >> cur->etarget;
    } else if (key == "term") {
      Term tm;
      ss >> tm.coef;
      for (int k = 0; k < 7; k++) { tm.ex[k] = 0; ss >> tm.ex[k]; }
      int deg = 0;
      for (int k = 0; k < 4; k++) deg += (k + 1) * tm.ex[k];
      for (int k = 0; k < 3; k++) deg += (k + 1) * tm.ex[4 + k];
      cur->terms.push_back(tm);
      cur->Dmu = std::max(cur->Dmu, deg);
      for (int k = 0; k < 4; k++) if (tm.ex[k]) P.needS[k + 1] = true;
      for (int k = 0; k < 3; k++) if (tm.ex[4 + k]) P.needE[k + 1] = true;
    } else {
      fprintf(stderr, "unknown key %s\n", key.c_str());
      exit(2);
    }
  }
  P.Dmu = 0;
  for (auto &c : P.ch) P.Dmu = std::max(P.Dmu, c.Dmu);
}

// Relative cost estimate of one (sector, shift, point): the jet work grows like 2^K prod_k (N_k+1) over the K
// subtracted variables (measured: corr(log cpu, log estimate) = 0.97-0.99 on the pilot5 Q8, A7_v, Q6_E, A5_vE,
// Q6_d sectors); sectors without subtraction run in double precision (cheaper).
static double sector_cost(const Problem &P, const SectorData &sd) {
  double c = std::ldexp(1.0, (int)sd.sub.size());
  for (int nk : sd.Nsub) c *= (nk + 1);
  bool usedd = (P.prec == "dd") || (P.prec == "auto" && !sd.sub.empty());
  if (!usedd) c *= 0.2;
  return c;
}

template <class T>
static void run_sector(const Problem &P, const SectorData &sd, long long secId, int sh0, int sh1,
                       vector<vector<vector<double>>> &resv, vector<double> &secv,
                       vector<vector<vector<double>>> &absv, long long i0 = 0, long long i1 = -1) {
  // resv[sh][c][o]: (1/N) sum_i f_{c,o}(x_i + shift_sh) over points i0..i1-1 (Kahan-compensated)
  // absv[sh][c][o]: (1/N) sum_i |f_{c,o}(x_i + shift_sh)|  (L1 scale of the integrand, used for the error floor;
  //                 accumulated separately so that resv is bit-for-bit what the phase-1 engine produced)
  if (i1 < 0) i1 = P.N;
  static double dbgThresh = getenv("LRI_DEBUG_THRESH") ? atof(getenv("LRI_DEBUG_THRESH")) : 0.0;
  int mx = std::is_same<T, dd>::value ? P.mx_dd : P.mx_d;
  double tauC = std::is_same<T, dd>::value ? P.tauC_dd : P.tauC_d;
  Evaluator<T> ev(P, sd, mx, tauC);  // contexts are reused across shifts
  int nch = P.ch.size();
  int nOut = P.etarget - sd.lo + 1;
  int d = P.d;
  resv.assign(sh1 - sh0, {});
  absv.assign(sh1 - sh0, {});
  secv.assign(sh1 - sh0, 0.0);
  for (int sh = sh0; sh < sh1; sh++) {
    auto t0 = std::chrono::steady_clock::now();
    vector<vector<double>> &res = resv[sh - sh0];
    res.assign(nch, vector<double>(nOut, 0.0));
    absv[sh - sh0].assign(nch, vector<double>(nOut, 0.0));
    if (d == 0) {
      double tt[1], lw[1] = {0.0};
      ev.eval(tt, lw, res);
      for (int c = 0; c < nch; c++)
        for (int o = 0; o < nOut; o++) absv[sh - sh0][c][o] = std::fabs(res[c][o]);
      continue;
    }
    uint64_t st = P.seed ^ (0x1234567ull * (uint64_t)(secId + 1)) ^ (0x9876543ull * (uint64_t)(sh + 1));
    vector<double> shift(d);
    for (int j = 0; j < d; j++) shift[j] = (splitmix64(st) >> 11) * (1.0 / 9007199254740992.0);
    vector<double> tt(d), lwk(d);
    vector<vector<double>> acc(nch, vector<double>(nOut, 0.0)), comp(nch, vector<double>(nOut, 0.0)),
        tmp(nch, vector<double>(nOut, 0.0)), aacc(nch, vector<double>(nOut, 0.0));
    for (long long i = i0; i < i1; i++) {
      for (int j = 0; j < d; j++) {
        double u = (double)((__int128)i * P.z[j] % P.N) / (double)P.N + shift[j];
        if (u >= 1.0) u -= 1.0;
        double tj, dtj;
        korobov_tf(P.transform, u, tj, dtj);
        // never drop a point: pole (non-integrated) terms carry weight 1 in every coordinate they do not use
        if (!(tj > 1e-280)) tj = 1e-280;
        if (tj > 1.0) tj = 1.0;
        tt[j] = tj;
        lwk[j] = (dtj > 0.0) ? std::log(dtj) : -INFINITY;
      }
      for (auto &v : tmp) std::fill(v.begin(), v.end(), 0.0);
      ev.eval(tt.data(), lwk.data(), tmp);
      if (dbgThresh > 0) {
        double mx = 0;
        for (auto &v : tmp)
          for (double x : v) mx = std::max(mx, std::fabs(x));
        if (mx > dbgThresh) {
#pragma omp critical
          {
            fprintf(stderr, "DBG sec %lld sh %d i %lld max %.3e t:", secId, sh, i, mx);
            for (int j = 0; j < d; j++) fprintf(stderr, " %.6e", tt[j]);
            fprintf(stderr, "\n");
          }
        }
      }
      for (int c = 0; c < nch; c++)
        for (int o = 0; o < nOut; o++) {
          double x = tmp[c][o];
          double s = acc[c][o] + x;
          if (std::fabs(acc[c][o]) >= std::fabs(x))
            comp[c][o] += (acc[c][o] - s) + x;
          else
            comp[c][o] += (x - s) + acc[c][o];
          acc[c][o] = s;
          aacc[c][o] += std::fabs(x);
        }
    }
    for (int c = 0; c < nch; c++)
      for (int o = 0; o < nOut; o++) {
        res[c][o] = (acc[c][o] + comp[c][o]) / (double)P.N;
        absv[sh - sh0][c][o] = aacc[c][o] / (double)P.N;
      }
    if (ev.nUnresolved > 0) {
#pragma omp critical
      fprintf(stderr, "WARN sector %lld shift %d: %lld of %lld points above the precision target after tails\n", secId,
              sh, ev.nUnresolved, ev.nPoints);
    }
    ev.nUnresolved = 0;
    ev.nPoints = 0;
    auto t1 = std::chrono::steady_clock::now();
    secv[sh - sh0] = std::chrono::duration<double>(t1 - t0).count();
  }
}

int main(int argc, char **argv) {
  if (argc >= 2 && std::string(argv[1]) == "--korobov") {
    long long N = atoll(argv[2]);
    int d = atoi(argv[3]);
    int ncand = argc > 4 ? atoi(argv[4]) : 2000;
    double gam = argc > 5 ? atof(argv[5]) : 0.1;
    uint64_t st = 99;
    double best = 1e300;
    long long besta = 1;
    vector<long long> cands;
    if (N <= std::max(ncand + 2, 20000))
      for (long long a = 2; a < N - 1; a++) cands.push_back(a);
    else
      for (int i = 0; i < ncand; i++) cands.push_back(2 + (long long)(splitmix64(st) % (uint64_t)(N - 3)));
    for (long long a : cands) {
      double p = korobov_P2(N, d, a, gam);
      if (p < best) {
        best = p;
        besta = a;
      }
    }
    printf("%lld %d %lld %.6e\n", N, d, besta, best);
    return 0;
  }
  if (argc < 2) {
    fprintf(stderr, "usage: lri_engine job.cfg | --korobov N d [ncand]\n");
    return 2;
  }
  Problem P;
  parse(P, argv[1]);
  build_problem(P);
  vector<vector<int>> secs;
  enum_sectors(P, secs);
  long long nsec = secs.size();
  if (P.secStride > 1) {
    vector<vector<int>> keep;
    for (long long s = 0; s < nsec; s++)
      if (s % P.secStride == P.secOffset) keep.push_back(secs[s]);
    secs.swap(keep);
    nsec = secs.size();
    fprintf(stderr, "sector sample: every %lld-th sector (offset %lld): %lld sectors\n", P.secStride, P.secOffset, nsec);
  }
  long long s0 = std::max(0LL, P.secStart), s1 = (P.secEnd < 0) ? nsec : std::min(nsec, P.secEnd);
  double fw = (P.fold && P.M >= 2) ? 2.0 : 1.0;
  int nch = P.ch.size();
  // Build sector data
  vector<SectorData> sds(s1 - s0);
  int lo = 0;
  for (long long s = s0; s < s1; s++) {
    std::string err;
    if (!build_sector(P, secs[s], sds[s - s0], err)) {
      fprintf(stderr, "sector %lld: %s\n", s, err.c_str());
      return 3;
    }
    lo = std::min(lo, sds[s - s0].lo);
  }
  if (argc >= 3 && std::string(argv[2]) == "--sectors-info") {
    // per-sector subtraction structure and estimated relative cost (used by py/campaign.py to balance chunks)
    printf("{\"sectors_total\": %lld, \"range\": [%lld, %lld], \"d\": %d, \"sectors\": [\n", nsec, s0, s1, P.d);
    for (long long s = s0; s < s1; s++) {
      const SectorData &sd = sds[s - s0];
      printf(" {\"id\": %lld, \"Nsub\": [", s);
      for (size_t k = 0; k < sd.Nsub.size(); k++) printf("%d%s", sd.Nsub[k], k + 1 < sd.Nsub.size() ? "," : "");
      printf("], \"lo\": %d, \"est_cost\": %.6g}%s\n", sd.lo, sector_cost(P, sd), s + 1 < s1 ? "," : "");
    }
    printf("]}\n");
    return 0;
  }
  if (argc >= 4 && std::string(argv[2]) == "--point") {
    long long sid = atoll(argv[3]);
    vector<double> tt;
    for (int i = 4; i < argc; i++) tt.push_back(atof(argv[i]));
    const SectorData &sd = sds[sid - s0];
    vector<vector<double>> o1(nch, vector<double>(P.etarget - sd.lo + 1, 0.0)), o2 = o1;
    Evaluator<double> e1(P, sd, P.mx_d, P.tauC_d);
    Evaluator<dd> e2(P, sd, P.mx_dd, P.tauC_dd);
    vector<double> z0(tt.size() + 1, 0.0);
    e1.eval(tt.data(), z0.data(), o1);
    e2.eval(tt.data(), z0.data(), o2);
    for (int c = 0; c < nch; c++)
      for (size_t o = 0; o < o1[c].size(); o++) printf("ch%d order %d  double %.17e  dd %.17e\n", c, sd.lo + (int)o, o1[c][o], o2[c][o]);
    return 0;
  }
  if ((long long)P.z.size() < P.d) {
    fprintf(stderr, "lattice vector too short\n");
    return 2;
  }
  int nOut = P.etarget - lo + 1;
  // results: per sector per shift
  long long ntask = (s1 - s0) * (long long)P.shifts;
  vector<vector<vector<double>>> R(ntask), RA(ntask);
  vector<double> tsec(ntask, 0.0);
#ifdef _OPENMP
  if (P.nthreads > 0) omp_set_num_threads(P.nthreads);
#endif
  auto T0 = std::chrono::steady_clock::now();
  int dshifts = (P.d == 0) ? 1 : P.shifts;
  int nthr = 1;
#ifdef _OPENMP
  nthr = omp_get_max_threads();
#endif
  // task = (sector, block of shifts[, block of lattice points]).  Since v2 the default task is ONE
  // (sector, shift) pair (taskshifts 1), executed longest-first (estimated cost, see sector_cost), which
  // removes the load imbalance of the phase-1 sector-order schedule.  If there are still too few tasks,
  // lattice point blocks are split exactly as in phase 1 (same condition, so results are bit-for-bit
  // those of the phase-1 engine for the same cfg and thread count: every task stores its own result and
  // the per-shift evaluation does not depend on the task order).
  int blk = (P.taskShifts > 0) ? std::min(P.taskShifts, dshifts) : (((s1 - s0) >= 2 * nthr) ? dshifts : 1);
  int nblk = (dshifts + blk - 1) / blk;
  long long npb = 1;
  if (blk == 1 && (s1 - s0) * (long long)dshifts < 2LL * nthr && P.d > 0)
    npb = std::min<long long>(P.N / 64 + 1, (2LL * nthr + (s1 - s0) * dshifts - 1) / ((s1 - s0) * dshifts));
  long long ntask2 = (s1 - s0) * (long long)nblk * npb;
  vector<vector<vector<double>>> Rpart(ntask2), RApart(ntask2);
  vector<double> tpart(ntask2, 0.0);
  // longest-first order (stable for equal estimates)
  vector<long long> torder(ntask2);
  std::iota(torder.begin(), torder.end(), 0LL);
  {
    vector<double> tcost(ntask2);
    for (long long task = 0; task < ntask2; task++) {
      long long pb = task % npb, tq = task / npb;
      long long s = s0 + tq / nblk;
      int b0 = (tq % nblk) * blk, b1 = std::min(dshifts, b0 + blk);
      long long i0 = P.N * pb / npb, i1 = P.N * (pb + 1) / npb;
      tcost[task] = sector_cost(P, sds[s - s0]) * (double)(b1 - b0) * (double)(i1 - i0);
    }
    if (P.longestFirst)
      std::stable_sort(torder.begin(), torder.end(), [&](long long a, long long b) { return tcost[a] > tcost[b]; });
  }
#pragma omp parallel for schedule(dynamic, 1)
  for (long long it = 0; it < ntask2; it++) {
    long long task = torder[it];
    long long pb = task % npb;
    long long tq = task / npb;
    long long s = s0 + tq / nblk;
    int b0 = (tq % nblk) * blk, b1 = std::min(dshifts, b0 + blk);
    long long i0 = P.N * pb / npb, i1 = P.N * (pb + 1) / npb;
    const SectorData &sd = sds[s - s0];
    bool usedd = (P.prec == "dd") || (P.prec == "auto" && !sd.sub.empty());
    vector<vector<vector<double>>> resv, absv;
    vector<double> secv;
    if (usedd)
      run_sector<dd>(P, sd, s, b0, b1, resv, secv, absv, i0, i1);
    else
      run_sector<double>(P, sd, s, b0, b1, resv, secv, absv, i0, i1);
    // run_sector divides by N: partial sums over point blocks add up to the full average
    for (int sh = b0; sh < b1; sh++) {
      vector<vector<double>> r2(nch, vector<double>(nOut, 0.0)), a2(nch, vector<double>(nOut, 0.0));
      for (int c = 0; c < nch; c++)
        for (size_t o = 0; o < resv[sh - b0][c].size(); o++) {
          r2[c][o + (sd.lo - lo)] = resv[sh - b0][c][o] * fw;
          a2[c][o + (sd.lo - lo)] = absv[sh - b0][c][o] * fw;
        }
      if (npb == 1) {
        R[(s - s0) * P.shifts + sh] = r2;
        RA[(s - s0) * P.shifts + sh] = a2;
        tsec[(s - s0) * P.shifts + sh] = secv[sh - b0];
      } else {
        Rpart[task] = r2;
        RApart[task] = a2;
        tpart[task] = secv[sh - b0];
      }
    }
  }
  if (npb > 1) {
    for (long long tq = 0; tq < (s1 - s0) * (long long)nblk; tq++) {
      long long s = s0 + tq / nblk;
      int sh = (tq % nblk) * blk;  // blk == 1 here
      vector<vector<double>> acc(nch, vector<double>(nOut, 0.0)), aacc(nch, vector<double>(nOut, 0.0));
      double ts = 0;
      for (long long pb = 0; pb < npb; pb++) {
        auto &r = Rpart[tq * npb + pb];
        auto &ra = RApart[tq * npb + pb];
        for (int c = 0; c < nch; c++)
          for (int o = 0; o < nOut; o++) {
            acc[c][o] += r[c][o];
            aacc[c][o] += ra[c][o];
          }
        ts += tpart[tq * npb + pb];
      }
      R[(s - s0) * P.shifts + sh] = acc;
      RA[(s - s0) * P.shifts + sh] = aacc;
      tsec[(s - s0) * P.shifts + sh] = ts;
    }
  }
  auto T1 = std::chrono::steady_clock::now();
  double wall = std::chrono::duration<double>(T1 - T0).count();
  // statistics.  Output is written to <out>.tmp.<pid> and renamed to <out> only after a complete, error-free
  // write (atomic on POSIX filesystems incl. BeeGFS/Lustre/NFS within one directory): a killed or failed run
  // never leaves a partial <out>; the file ends with "complete": true.
  FILE *fo = stdout;
  std::string tmpout;
  if (!P.out.empty()) {
    tmpout = P.out + ".tmp." + std::to_string((long long)getpid());
    fo = fopen(tmpout.c_str(), "w");
    if (!fo) {
      fprintf(stderr, "cannot open %s for writing\n", tmpout.c_str());
      return 4;
    }
  }
  fprintf(fo, "{\n \"n\": %d, \"type\": \"%c\", \"geom\": \"%s\", \"s0\": %d, \"etarget\": %d, \"lo\": %d,\n", P.n,
          P.type, P.full ? "full" : "angular", P.s0, P.etarget, lo);
  fprintf(fo, " \"kappa\": %d, \"dF\": %d, \"M\": %d, \"N\": %lld, \"shifts\": %d, \"transform\": %d, \"prec\": \"%s\",\n",
          P.kappa, P.dF, P.M, P.N, dshifts, P.transform, P.prec.c_str());
  fprintf(fo, " \"sectors_total\": %lld, \"sector_range\": [%lld, %lld], \"wall_seconds\": %.3f,\n", nsec, s0, s1, wall);
  fprintf(fo, " \"engine_version\": \"%s\", \"seed\": %llu, \"threads\": %d, \"task_shifts\": %d, \"point_blocks\": %lld,\n",
          ENGINE_VERSION, (unsigned long long)P.seed, nthr, blk, npb);
  double cpu = 0;
  for (double x : tsec) cpu += x;
  fprintf(fo, " \"cpu_seconds\": %.3f,\n \"channels\": {\n", cpu);
  for (int c = 0; c < nch; c++) {
    vector<double> mean(nOut, 0.0), var(nOut, 0.0), amean(nOut, 0.0);
    for (long long s = s0; s < s1; s++) {
      for (int o = 0; o < nOut; o++) {
        double m = 0, m2 = 0, am = 0;
        for (int sh = 0; sh < dshifts; sh++) m += R[(s - s0) * P.shifts + sh][c][o];
        m /= dshifts;
        for (int sh = 0; sh < dshifts; sh++) {
          double x = R[(s - s0) * P.shifts + sh][c][o] - m;
          m2 += x * x;
          am += RA[(s - s0) * P.shifts + sh][c][o];
        }
        mean[o] += m;
        amean[o] += am / dshifts;
        if (dshifts > 1) var[o] += m2 / (dshifts - 1) / dshifts;
      }
    }
    fprintf(fo, "  \"%s\": {\"orders\": [", P.ch[c].name.c_str());
    for (int o = 0; o < nOut; o++) fprintf(fo, "%d%s", lo + o, o + 1 < nOut ? ", " : "");
    fprintf(fo, "], \"value\": [");
    for (int o = 0; o < nOut; o++) fprintf(fo, "%.17e%s", mean[o], o + 1 < nOut ? ", " : "");
    fprintf(fo, "], \"err\": [");
    for (int o = 0; o < nOut; o++) fprintf(fo, "%.6e%s", std::sqrt(var[o]), o + 1 < nOut ? ", " : "");
    fprintf(fo, "]");
    // v2: per-shift replicates summed over the sectors of this run (rep[sh][o]); the shifts of different
    // sectors are independent, so rep[0..shifts-1] are i.i.d. unbiased estimates of the whole sector range.
    // Correlated combinations (channels x Laurent orders -> eps^k log^j coefficients) must be formed per
    // replicate (py/lri_moments.py: assemble_replicates), not in quadrature.
    fprintf(fo, ",\n   \"rep\": [");
    for (int sh = 0; sh < dshifts; sh++) {
      fprintf(fo, "%s[", sh ? ", " : "");
      for (int o = 0; o < nOut; o++) {
        double x = 0;
        for (long long s = s0; s < s1; s++) x += R[(s - s0) * P.shifts + sh][c][o];
        fprintf(fo, "%.17e%s", x, o + 1 < nOut ? ", " : "");
      }
      fprintf(fo, "]");
    }
    fprintf(fo, "],\n   \"abs\": [");
    for (int o = 0; o < nOut; o++) fprintf(fo, "%.6e%s", amean[o], o + 1 < nOut ? ", " : "");
    fprintf(fo, "]");
    if (P.persector) {
      fprintf(fo, ",\n   \"per_sector\": [\n");
      for (long long s = s0; s < s1; s++) {
        fprintf(fo, "    {\"id\": %lld, \"ord\": [", s);
        for (int r = 0; r < P.M; r++) fprintf(fo, "%d%s", secs[s][r], r + 1 < P.M ? "," : "");
        fprintf(fo, "], \"Nsub\": [");
        auto &sd = sds[s - s0];
        for (size_t k = 0; k < sd.Nsub.size(); k++) fprintf(fo, "%d%s", sd.Nsub[k], k + 1 < sd.Nsub.size() ? "," : "");
        double ts = 0;
        for (int sh = 0; sh < dshifts; sh++) ts += tsec[(s - s0) * P.shifts + sh];
        fprintf(fo, "], \"cpu\": %.4f, \"value\": [", ts);
        for (int o = 0; o < nOut; o++) {
          double m = 0, m2 = 0;
          for (int sh = 0; sh < dshifts; sh++) m += R[(s - s0) * P.shifts + sh][c][o];
          m /= dshifts;
          for (int sh = 0; sh < dshifts; sh++) {
            double x = R[(s - s0) * P.shifts + sh][c][o] - m;
            m2 += x * x;
          }
          double e = dshifts > 1 ? std::sqrt(m2 / (dshifts - 1) / dshifts) : 0;
          fprintf(fo, "[%.17e, %.3e]%s", m, e, o + 1 < nOut ? ", " : "");
        }
        fprintf(fo, "]");
        if (P.persectorRep) {  // v2: per-shift values of this sector (refinement and outlier analysis)
          fprintf(fo, ", \"rep\": [");
          for (int sh = 0; sh < dshifts; sh++) {
            fprintf(fo, "%s[", sh ? ", " : "");
            for (int o = 0; o < nOut; o++)
              fprintf(fo, "%.17e%s", R[(s - s0) * P.shifts + sh][c][o], o + 1 < nOut ? ", " : "");
            fprintf(fo, "]");
          }
          fprintf(fo, "]");
        }
        fprintf(fo, ", \"est_cost\": %.4g}%s\n", sector_cost(P, sd), s + 1 < s1 ? "," : "");
      }
      fprintf(fo, "   ]");
    }
    fprintf(fo, "}%s\n", c + 1 < nch ? "," : "");
  }
  fprintf(fo, " },\n \"complete\": true\n}\n");
  if (fo != stdout) {
    bool bad = (fflush(fo) != 0) || ferror(fo);
    if (!bad) bad = (fsync(fileno(fo)) != 0);
    if (fclose(fo) != 0) bad = true;
    if (bad) {
      fprintf(stderr, "write error on %s; output not published\n", tmpout.c_str());
      remove(tmpout.c_str());
      return 4;
    }
    if (rename(tmpout.c_str(), P.out.c_str()) != 0) {
      fprintf(stderr, "cannot rename %s -> %s\n", tmpout.c_str(), P.out.c_str());
      return 4;
    }
  }
  return 0;
}
