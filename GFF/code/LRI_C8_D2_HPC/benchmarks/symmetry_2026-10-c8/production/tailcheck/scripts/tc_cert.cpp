// tc_cert.cpp (v2, 2026-10-08): multi-prime randomized cancellation verification that the C8(2) importance weights
// are bounded (tail check; v1, two fixed primes and one point each, is scripts/v1/tc_cert.cpp, job 571351).
//
// For a payload graph (C7D2GRAPH1 format: masks of U, forest terms (basis monomial lists, numerator edge
// coefficients), the stored rate table alpha_G(S) over all edge subsets S), with the sampler of src/kernel.hpp:
//   T_c = Z_c * K_G(x) * prod_i z_i^{|S_i|/2 - rho_c alpha_G(S_i)},  K_G = (1/sum_e x_e) sum_F N_F / U_F,
// in every ordered (Hepp) sector, rho_a = 0.8, rho_b = 0.9. Let m_G(S) = |S|/2 + nu_S(K_G) be the exact leading
// exponent of the measure times the CANCELLED forest sum when x_e -> lambda x_e for e in S.
//   * Each forest term's own exponent is |S|/2 + a_F(S) - h_F(S) (a_F = 1 iff the numerator support lies in S,
//     h_F = min over the term's denominator monomials of |m & S|), so the term-wise minimum raw(S)/2 is a lower
//     bound of m_G(S) (a sum cannot have a lower leading exponent than its terms).
//   * The builder stores alpha_G(S) = max(raw(S), 1 if |S| odd else 2) / 2.
//   * K_G is rational in x, so m_G(S) lies in |S|/2 + Z. Hence m_G(S) > 0 implies m_G(S) >= alpha_G(S) whenever
//     raw(S) <= 0 (clamped); and m_G(S) >= raw(S)/2 = alpha_G(S) when raw(S) > 0.
// Steps per graph:
//  (1) recompute raw(S) for every proper nonempty S exactly (integers) as the builder does, and compare the stored
//      rate table with max(raw, floor)/2 (skipped for legacy non-half-integer tables and for "given" rate tables);
//  (2) at every clamped S (every S for legacy or "given" tables) expand sum_F N_F/U_F in lambda and find the lowest
//      order whose Laurent coefficient is nonzero, by exact arithmetic modulo K random primes, J random evaluation
//      points per prime (defaults K = 4, J = 2). Primes: uniform among the primes in [2^61, 2^62) (rejection sampling
//      of odd candidates, deterministic Miller-Rabin for 64-bit integers). Points: every edge variable uniform in
//      [1, p-1] (rejection sampling). A point at which some included term's leading denominator coefficient c_h
//      vanishes mod p is redrawn and the whole graph pass is redone with it (degenerate_retries); a nonzero
//      coefficient is therefore a proof of nonvanishing, and only a false zero can err. The reported order is the
//      minimum over all K*J trials.
//      Error bound (assumption: the generator's draws behave as independent uniform draws). For a fixed S, order j
//      <= jtop and common denominator D = prod_G c_{h_G}^{E_G}, E_G = jtop + h_G + 1 (G the included terms), the
//      coefficient times D is an integer polynomial Q in the E edge variables with
//        deg Q <= d_S = L * sum_G E_G,      log2 ||Q||_inf <= B_S = 1 + log2(sum_G s_G) + sum_G E_G log2(2 b_G)
//      (s_G = sum_e |numerator coefficient|, b_G = number of denominator monomials; the inverse-series polynomials
//      obey ||P_n||_1 <= (2b)^n). If Q != 0 over Z, at most ceil(B_S / 61) primes >= 2^61 divide all its
//      coefficients ("bad" primes), so a uniform prime is bad with probability <= beta = ceil(B_S/61) / (N_P - K),
//      N_P >= 3.8e16 primes in [2^61, 2^62) (Dusart: pi(x) >= x/ln x, pi(x) <= 1.25506 x/ln x). At a good prime a
//      point uniform in [1, p-1]^E, conditioned on no degeneracy anywhere in the graph pass (probability >= 1 - gamma,
//      gamma = n_series * T * L / (2^61 - 2)), is a zero of Q with probability <= delta = d_S / ((2^61 - 2)(1 - gamma))
//      (Schwartz-Zippel). So the true lowest nonzero coefficient is missed at S with probability
//        P_S <= (beta + delta^J)^K,
//      and the union bound over all expanded S of all graphs bounds the probability of any wrong valuation. The
//      program records max_S log10 P_S and log10 sum_S P_S per graph (log10_err_max, log10_err_sum).
//      For the clamped subsets of builder tables the coefficients below nu* (the first order with |S|/2 + nu > 0)
//      must vanish, i.e. m_G(S) >= alpha_G(S) ("failures" counts violations); the coefficient AT nu* tells whether
//      m_G(S) = alpha_G(S) ("tight") or more ("higher").
//  (3) check on 16 random orderings that every term's denominator monomial set has a simultaneous minimizer of all
//      suffix counts (the matroid/greedy property behind the nested-limit argument; regression evidence only, the
//      all-sector argument rests on the builder's construction).
// Flags: bounded = every check passed and min_S (m_low - rho alpha) > 0 at both rates; certified (finite second
// moment at both rates) = every check passed and min_S (2 m_low - rho alpha) > 0 at both rates. m_low is a lower
// bound of m_G(S) (exact where a coefficient was found nonzero); the inequalities are STRICT, which is conservative
// (boundedness also holds at equality), so the flags are sufficient conditions, not an "iff" classifier.
//
// Usage: tc_cert LIST OUT.jsonl --seed S [--threads N] [--primes K] [--points J] [--expect N]
//   LIST lines: "<sector> <L> <id> <pack path> <offset> <length> [<label> [builder|given]]" (members verified by the
//   Python driver; "given" treats the stored table as the proposal rates: no builder comparison, every S expanded).
// Output: one JSON object per list line, in list order. Exit status: 0 every record certified with no error; 3 a
// record has an error, a failed check or is not certified; 4 the list does not hold --expect lines or a record is
// missing; 2 usage, input or self-test failure.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif
typedef unsigned long long u64;
typedef unsigned __int128 u128;
struct Mod {
  u64 p;
  u64 mul(u64 a, u64 b) const { return (u64)((u128)a * b % p); }
  u64 add(u64 a, u64 b) const { u64 s = a + b; return s >= p ? s - p : s; }
  u64 sub(u64 a, u64 b) const { return a >= b ? a - b : a + p - b; }
  u64 pw(u64 a, u64 e) const { u64 r = 1; while (e) { if (e & 1) r = mul(r, a); a = mul(a, a); e >>= 1; } return r; }
  u64 inv(u64 a) const { return pw(a, p - 2); }
  u64 from(long long v) const { long long r = v % (long long)p; if (r < 0) r += (long long)p; return (u64)r; }
};

static bool is_prime(u64 n) {  // deterministic for n < 2^64 (Sinclair's seven bases)
  if (n < 2) return false;
  static const u64 small[] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71};
  for (u64 q : small) { if (n % q == 0) return n == q; }
  u64 d = n - 1; int r = 0; while (!(d & 1)) { d >>= 1; ++r; }
  Mod M{n};
  static const u64 bases[] = {2ULL, 325ULL, 9375ULL, 28178ULL, 450775ULL, 9780504ULL, 1795265022ULL};
  for (u64 a : bases) {
    u64 x = a % n; if (x == 0) continue;
    x = M.pw(x, d);
    if (x == 1 || x == n - 1) continue;
    bool composite = true;
    for (int i = 1; i < r; ++i) { x = M.mul(x, x); if (x == n - 1) { composite = false; break; } }
    if (composite) return false;
  }
  return true;
}
static void self_test() {
  const u64 primes[] = {2305843009213693951ULL /* 2^61-1 */, 4611686018427387847ULL /* 2^62-57 */, 18446744073709551557ULL /* 2^64-59 */};
  const u64 composites[] = {2305843009213693953ULL /* 2^61+1, divisible by 3 */, 3215031751ULL /* spsp(2,3,5,7) */,
                            3825123056546413051ULL /* spsp(2..23) */, 4611686014132420609ULL /* (2^31-1)^2 */,
                            4611686018427387903ULL /* 2^62-1 */};
  for (u64 p : primes) if (!is_prime(p)) throw std::runtime_error("self-test: a known prime was rejected");
  for (u64 c : composites) if (is_prime(c)) throw std::runtime_error("self-test: a known composite was accepted");
  int count = 0; for (u64 n = 1000000; n < 1000200; ++n) count += is_prime(n);  // pi(1000200) - pi(1000000) = 16
  if (count != 16) throw std::runtime_error("self-test: wrong prime count in [10^6, 10^6 + 200)");
}
static u64 splitmix(u64 &s) { u64 z = (s += 0x9e3779b97f4a7c15ULL); z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL; z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL; return z ^ (z >> 31); }

static const int MAXT = 16;                 // most trials (primes x points) per graph
static const double PRIME_COUNT_LB = 3.8e16;  // primes in [2^61, 2^62), lower bound
static const double TWO61M2 = 2305843009213693950.0;

struct Graph {
  int L = 0, E = 0, id = 0;
  std::vector<unsigned> masks;
  std::vector<std::vector<int>> basis;
  std::vector<std::vector<int>> co;
  std::vector<int> rate2;  // 2 * stored rate when it is a half-integer
  std::vector<long double> rate;
  bool legacy = false;     // a stored rate that is not a half-integer (the legacy free L<=6 tables)
};

static Graph parse(const std::string &text) {
  std::istringstream f(text);
  std::string magic; Graph g; double wa, wb; int M, T;
  f >> magic >> g.L >> g.id >> wa >> wb >> M >> T;
  if (!f || magic != "C7D2GRAPH1" || g.L < 2 || g.L > 8 || M < 1 || T < 1) throw std::runtime_error("bad header");
  g.E = 2 * g.L;
  g.masks.resize(M);
  for (auto &m : g.masks) f >> m;
  g.basis.resize(T); g.co.resize(T);
  for (int t = 0; t < T; ++t) {
    int n; f >> n; if (!f || n < 1 || n > M) throw std::runtime_error("bad term");
    g.basis[t].resize(n); for (auto &i : g.basis[t]) { f >> i; if (i < 0 || i >= M) throw std::runtime_error("bad monomial id"); }
    g.co[t].resize(g.E); for (auto &c : g.co[t]) f >> c;
  }
  int n; f >> n; if (!f || n != (1 << g.E)) throw std::runtime_error("bad rate table size");
  g.rate2.resize(n); g.rate.resize(n);
  for (int s = 0; s < n; ++s) {
    std::string tok; f >> tok; if (!f) throw std::runtime_error("truncated rate table");
    long double v = std::strtold(tok.c_str(), nullptr); g.rate[s] = v; long double r2 = 2 * v; long k = std::lround((double)r2);
    if (std::fabs((double)(r2 - k)) > 1e-12) g.legacy = true;
    g.rate2[s] = (int)k;
  }
  std::string extra; if (f >> extra) throw std::runtime_error("extra tokens");
  return g;
}

struct Result {
  std::string sector, label, rates_mode = "builder"; int L = 0, id = 0, E = 0, terms = 0, monomials = 0;
  long basis_entries = 0;
  int clamped = 0, rate_mismatch = 0, raw_min = 1000, max_orders_cancelled = 0;
  int tight = 0, higher = 0, failures = 0, degenerate_retries = 0, structural_mismatch = 0, trial_disagreements = 0;
  int greedy_checked = 0, greedy_fail = 0;
  long double min_bound[2] = {1e9, 1e9}, min_second[2] = {1e9, 1e9};  // min over S of m_low - rho alpha, 2 m_low - rho alpha
  bool legacy = false; int series_subsets = 0;
  long double xi[2] = {0, 0};  // analytic tail-index bound max_S (1 - m_low/(rho alpha))^+ of the weight
  std::vector<unsigned> failed_sets;
  std::vector<u64> primes;
  int points_per_prime = 0;
  long max_degree = 0; double max_height_bits = 0, log10_err_max = -1e300, log10_err_sum = -1e300, gamma = 0;
  std::string error;
  double seconds = 0;
};

static double log10_add(double a, double b) { if (a < b) std::swap(a, b); if (b < -1e299) return a; return a + std::log10(1 + std::pow(10.0, b - a)); }

struct Opts { u64 seed = 0; int K = 4, J = 2; };

static void certify(const Graph &g, Result &R, const Opts &O, bool given) {
  const int E = g.E, L = g.L, ALL = (1 << E) - 1, T = (int)g.basis.size();
  const int NT = O.K * O.J;
  R.E = E; R.terms = T; R.monomials = (int)g.masks.size(); R.points_per_prime = O.J;
  for (auto &b : g.basis) R.basis_entries += (long)b.size();
  for (auto m : g.masks) if (__builtin_popcount(m) != L || m > (unsigned)ALL) throw std::runtime_error("nonhomogeneous mask");
  const bool all_subsets = g.legacy || given;
  // (1) raw(S) exactly as gen/build_free.cpp and gen/build_power.cpp
  std::vector<int> raw(ALL + 1, 100);
  std::vector<int8_t> dist(ALL + 1);
  std::vector<unsigned> supp(T, 0);
  std::vector<long> absco(T, 0);
  for (int t = 0; t < T; ++t) {
    std::fill(dist.begin(), dist.end(), (int8_t)100);
    for (int k : g.basis[t]) dist[g.masks[k]] = 0;
    for (int b = 0; b < E; ++b) { int bit = 1 << b; for (int s = 0; s <= ALL; ++s) if (!(s & bit)) { int u = s | bit; int a = dist[s], c = dist[u]; dist[s] = (int8_t)std::min(a, c + 1); dist[u] = (int8_t)std::min(c, a + 1); } }
    for (int i = 0; i < E; ++i) if (g.co[t][i]) { supp[t] |= 1u << i; absco[t] += std::labs((long)g.co[t][i]); }
    for (int s = 1; s < ALL; ++s) { int pc = __builtin_popcount((unsigned)s); int h = (L - E + pc + int(dist[ALL ^ s])) / 2; int a = (supp[t] & ~(unsigned)s) ? 0 : 1; raw[s] = std::min(raw[s], pc + 2 * a - 2 * h); }
  }
  for (int s = 1; s < ALL; ++s) {
    int pc = __builtin_popcount((unsigned)s); int fl = (pc % 2) ? 1 : 2; int want = std::max(fl, raw[s]);
    if (!all_subsets && g.rate2[s] != want) R.rate_mismatch++;
    if (raw[s] <= 0) { R.clamped++; R.raw_min = std::min(R.raw_min, raw[s]); }
  }
  if (!all_subsets && (g.rate2[0] != 0 || g.rate2[ALL] != 0)) R.rate_mismatch++;
  R.legacy = g.legacy; R.rates_mode = given ? "given" : "builder";
  std::vector<int> series;  // the subsets expanded
  for (int s = 1; s < ALL; ++s) if (all_subsets || raw[s] <= 0) series.push_back(s);
  R.series_subsets = (int)series.size();
  R.gamma = (double)series.size() * T * L / TWO61M2;
  // randomness: K distinct primes, J points per prime
  u64 st = O.seed ^ (R.sector == "power" ? 0x706f776572ULL : 0x66726565ULL) ^ ((u64)L << 56) ^ ((u64)(unsigned)g.id * 0x9e3779b97f4a7c15ULL);
  std::mt19937_64 rng(splitmix(st));
  std::vector<u64> P(NT);
  for (int k = 0; k < O.K; ++k) {
    u64 x;
    for (;;) { x = (1ULL << 61) | (rng() & ((1ULL << 61) - 1)) | 1ULL; if (!is_prime(x)) continue; bool dup = false; for (int j = 0; j < k; ++j) if (R.primes[j] == x) dup = true; if (!dup) break; }
    R.primes.push_back(x);
    for (int j = 0; j < O.J; ++j) P[k * O.J + j] = x;
  }
  const size_t Mn = g.masks.size();
  std::vector<u64> y((size_t)E * NT), val(Mn * NT);
  auto draw = [&](int t) {
    const u64 p = P[t];
    for (int e = 0; e < E; ++e) { u64 r; do { r = rng() >> 2; } while (r >= p - 1); y[(size_t)e * NT + t] = r + 1; }
    Mod M{p};
    for (size_t k = 0; k < Mn; ++k) { u64 v = 1; unsigned m = g.masks[k]; while (m) { int e = __builtin_ctz(m); m &= m - 1; v = M.mul(v, y[(size_t)e * NT + t]); } val[k * NT + t] = v; }
  };
  for (int t = 0; t < NT; ++t) draw(t);
  const long double rho[2] = {0.8L, 0.9L};
  Mod MM[MAXT]; for (int t = 0; t < NT; ++t) MM[t] = Mod{P[t]};
  // per-subset results of the pass (redone from scratch if a trial point is degenerate)
  std::vector<int> mord_of(series.size());
  std::vector<char> disagree(series.size());
  // buffers
  std::vector<u64> cbuf((size_t)T * 9 * NT), n0buf((size_t)T * NT), n1buf((size_t)T * NT), invh((size_t)T * NT), pref((size_t)T * NT);
  std::vector<int> hof(T), inc;
  std::vector<u64> coef, invs;
  int pass_struct = 0; long pass_maxdeg = 0; double pass_maxh = 0, pass_lmax = -1e300, pass_lsum = -1e300;
  for (int attempt = 0;; ++attempt) {
    if (attempt == 8) throw std::runtime_error("degenerate random points 8 times");
    bool degenerate[MAXT] = {false};
    bool anydeg = false;
    pass_struct = 0; pass_maxdeg = 0; pass_maxh = 0; pass_lmax = -1e300; pass_lsum = -1e300;
    for (size_t si = 0; si < series.size() && !anydeg; ++si) {
      const int s = series[si];
      const int pc = __builtin_popcount((unsigned)s);
      const long double alpha = g.rate[s];
      if ((raw[s] - pc) % 2) throw std::runtime_error("raw parity");
      const int vmin = (raw[s] - pc) / 2;
      const int nustar = -(pc / 2) + (pc % 2 == 0 ? 1 : 0);       // first order with |S|/2 + nu > 0
      const int jneed = (int)std::ceil((double)(alpha - pc / 2.0L));  // first order with |S|/2 + nu >= alpha
      const int jtop = std::max(std::max(nustar, jneed), vmin) + 1;
      const int nord = jtop - vmin + 1;
      // term classes c_j(y) for all trials; included terms
      inc.clear();
      for (int t = 0; t < T; ++t) {
        u64 *c = &cbuf[(size_t)t * 9 * NT]; std::fill(c, c + 9 * NT, 0ULL); unsigned present = 0;
        for (int k : g.basis[t]) { int j = __builtin_popcount(g.masks[k] & (unsigned)s); present |= 1u << j; u64 *cj = c + j * NT; const u64 *vk = &val[(size_t)k * NT]; for (int q = 0; q < NT; ++q) cj[q] = MM[q].add(cj[q], vk[q]); }
        const int h = __builtin_ctz(present); hof[t] = h;
        const int a = (supp[t] & ~(unsigned)s) ? 0 : 1;
        const int vT = a - h;
        if (vT < vmin) { pass_struct++; continue; }
        if (vT > jtop) continue;
        inc.push_back(t);
        for (int q = 0; q < NT; ++q) {
          u64 n0 = 0, n1 = 0;
          for (int e = 0; e < E; ++e) if (g.co[t][e]) { u64 term = MM[q].mul(MM[q].from(g.co[t][e]), y[(size_t)e * NT + q]); if (s >> e & 1) n1 = MM[q].add(n1, term); else n0 = MM[q].add(n0, term); }
          n0buf[(size_t)t * NT + q] = n0; n1buf[(size_t)t * NT + q] = n1;
        }
      }
      // batch inversion of the leading coefficients c_h, per trial
      for (int q = 0; q < NT; ++q) {
        u64 acc = 1;
        for (size_t i = 0; i < inc.size(); ++i) { int t = inc[i]; u64 ch = cbuf[(size_t)t * 9 * NT + hof[t] * NT + q]; if (ch == 0) { degenerate[q] = true; break; } pref[i * NT + q] = acc; acc = MM[q].mul(acc, ch); }
        if (degenerate[q]) { anydeg = true; continue; }
        u64 ia = MM[q].inv(acc);
        for (size_t i = inc.size(); i-- > 0;) { int t = inc[i]; u64 ch = cbuf[(size_t)t * 9 * NT + hof[t] * NT + q]; invh[(size_t)t * NT + q] = MM[q].mul(ia, pref[i * NT + q]); ia = MM[q].mul(ia, ch); }
      }
      if (anydeg) break;
      // series per included term and trial
      coef.assign((size_t)nord * NT, 0ULL);
      double degsum = 0, hbits = 0; long double ssum = 0;
      for (int t : inc) {
        const int h = hof[t];
        const int need = jtop + h;
        const int Eg = jtop + h + 1;
        degsum += (double)L * Eg; hbits += Eg * std::log2(2.0 * (double)g.basis[t].size()); ssum += absco[t];
        invs.assign((size_t)(need + 1), 0ULL);
        for (int q = 0; q < NT; ++q) {
          const Mod &M = MM[q];
          const u64 *c = &cbuf[(size_t)t * 9 * NT];
          const u64 i0 = invh[(size_t)t * NT + q];
          invs[0] = i0;
          for (int n = 1; n <= need; ++n) { u64 acc = 0; for (int k = 1; k <= n && h + k <= L; ++k) acc = M.add(acc, M.mul(c[(h + k) * NT + q], invs[n - k])); invs[n] = M.mul(M.sub(0, acc), i0); }
          const u64 n0 = n0buf[(size_t)t * NT + q], n1 = n1buf[(size_t)t * NT + q];
          for (int j = std::max(vmin, -h); j <= jtop; ++j) {
            int idx = j + h; u64 v = M.mul(n0, invs[idx]); if (idx >= 1) v = M.add(v, M.mul(n1, invs[idx - 1]));
            u64 &cf = coef[(size_t)(j - vmin) * NT + q]; cf = M.add(cf, v);
          }
        }
      }
      int lo = 1000, hi = -100000;
      for (int q = 0; q < NT; ++q) { int l = 1000; for (int j = 0; j < nord; ++j) if (coef[(size_t)j * NT + q]) { l = vmin + j; break; } lo = std::min(lo, l); hi = std::max(hi, l); }
      mord_of[si] = lo < 1000 ? lo : jtop + 1;  // exact leading order (nonzero somewhere), or a lower bound of it
      disagree[si] = (lo != hi);
      {
        // error bound of this subset: P_S <= (beta + delta^J)^K
        const double heightbits = 1 + (ssum > 0 ? std::log2((double)ssum) : 0) + hbits;
        const double nbad = std::ceil(heightbits / 61.0);
        pass_maxdeg = std::max(pass_maxdeg, (long)degsum); pass_maxh = std::max(pass_maxh, heightbits);
        const double beta = nbad / (PRIME_COUNT_LB - O.K);
        const double delta = degsum / (TWO61M2 * (1 - R.gamma));
        const double phi = beta + std::pow(delta, O.J);
        const double l10 = O.K * std::log10(phi);
        pass_lmax = std::max(pass_lmax, l10); pass_lsum = log10_add(pass_lsum, l10);
      }
    }
    if (!anydeg) break;
    for (int q = 0; q < NT; ++q) if (degenerate[q]) { R.degenerate_retries++; draw(q); }
  }
  R.structural_mismatch = pass_struct; R.max_degree = pass_maxdeg; R.max_height_bits = pass_maxh;
  R.log10_err_max = pass_lmax; R.log10_err_sum = pass_lsum;
  // tally the pass
  for (size_t si = 0; si < series.size(); ++si) {
    const int s = series[si]; const int pc = __builtin_popcount((unsigned)s);
    const int vmin = (raw[s] - pc) / 2; const int nustar = -(pc / 2) + (pc % 2 == 0 ? 1 : 0);
    const int mord = mord_of[si];
    if (disagree[si]) R.trial_disagreements++;
    if (raw[s] <= 0) {
      R.max_orders_cancelled = std::max(R.max_orders_cancelled, nustar - vmin);
      if (mord < nustar) { R.failures++; if (R.failed_sets.size() < 20) R.failed_sets.push_back((unsigned)s); }
      else if (mord == nustar) R.tight++; else R.higher++;
    }
  }
  std::vector<int> mlow2(ALL + 1, 0);  // 2 * m_low per subset
  for (int s = 1; s < ALL; ++s) mlow2[s] = raw[s];  // term-wise bound (used where no expansion was made: raw > 0)
  for (size_t si = 0; si < series.size(); ++si) { int s = series[si]; mlow2[s] = __builtin_popcount((unsigned)s) + 2 * mord_of[si]; }
  for (int s = 1; s < ALL; ++s) {
    const long double alpha = g.rate[s]; const long double mlow = mlow2[s] / 2.0L;
    for (int q = 0; q < 2; ++q) { R.min_bound[q] = std::min(R.min_bound[q], mlow - rho[q] * alpha); R.min_second[q] = std::min(R.min_second[q], 2 * mlow - rho[q] * alpha); if (alpha > 0) R.xi[q] = std::max(R.xi[q], 1 - mlow / (rho[q] * alpha)); }
  }
  // (3) greedy / simultaneous-minimizer property on random orderings
  u64 st2 = O.seed ^ 0x5ec70ULL ^ (u64)(unsigned)g.id ^ ((u64)L << 48) ^ (R.sector == "power" ? 0x9fULL << 40 : 0);
  std::mt19937_64 rg(splitmix(st2));
  std::vector<int> perm(E), pos(E);
  for (int rep = 0; rep < 16; ++rep) {
    std::iota(perm.begin(), perm.end(), 0); std::shuffle(perm.begin(), perm.end(), rg);
    for (int j = 0; j < E; ++j) pos[perm[j]] = j;  // position 0 = largest x
    for (int t = 0; t < T; ++t) {
      std::array<int, 17> best; best.fill(1000);
      std::vector<std::array<int8_t, 17>> cnt(g.basis[t].size());
      for (size_t i = 0; i < g.basis[t].size(); ++i) {
        int hist[17] = {0}; unsigned m = g.masks[g.basis[t][i]]; while (m) { int e = __builtin_ctz(m); m &= m - 1; hist[pos[e]]++; }
        int acc = 0; for (int k = E - 1; k >= 1; --k) { acc += hist[k]; cnt[i][k] = (int8_t)acc; best[k] = std::min(best[k], acc); }
      }
      bool ok = false;
      for (size_t i = 0; i < g.basis[t].size() && !ok; ++i) { bool all = true; for (int k = 1; k < E; ++k) if (cnt[i][k] != best[k]) { all = false; break; } ok = all; }
      R.greedy_checked++; if (!ok) R.greedy_fail++;
    }
  }
}

static std::string jnum(double v) { if (v < -1e299) return "null"; char b[64]; std::snprintf(b, sizeof b, "%.10g", v); return b; }

int main(int argc, char **argv) {
  if (argc < 3) { std::cerr << "usage: tc_cert LIST OUT.jsonl --seed S [--threads N] [--primes K] [--points J] [--expect N]\n"; return 2; }
  Opts O; int threads = 1; long expect = -1; bool have_seed = false; (void)threads;
  for (int i = 3; i < argc; ++i) {
    std::string a = argv[i];
    auto next = [&]() -> std::string { if (i + 1 >= argc) { std::cerr << "missing value for " << a << "\n"; std::exit(2); } return argv[++i]; };
    if (a == "--seed") { O.seed = std::stoull(next()); have_seed = true; }
    else if (a == "--threads") threads = std::stoi(next());
    else if (a == "--primes") O.K = std::stoi(next());
    else if (a == "--points") O.J = std::stoi(next());
    else if (a == "--expect") expect = std::stol(next());
    else { std::cerr << "unknown option " << a << "\n"; return 2; }
  }
  if (!have_seed || O.K < 1 || O.J < 1 || O.K * O.J > MAXT) { std::cerr << "need --seed, and 1 <= primes*points <= " << MAXT << "\n"; return 2; }
  try { self_test(); } catch (const std::exception &e) { std::cerr << e.what() << "\n"; return 2; }
  struct Item { std::string sector, pack, label, mode; int L, id; long long off, len; };
  std::vector<Item> items;
  {
    std::ifstream lf(argv[1]); if (!lf) { std::cerr << "cannot read " << argv[1] << "\n"; return 2; }
    std::string line; long ln = 0;
    while (std::getline(lf, line)) {
      ++ln; if (line.empty()) continue;
      std::istringstream is(line); Item it; it.mode = "builder";
      if (!(is >> it.sector >> it.L >> it.id >> it.pack >> it.off >> it.len)) { std::cerr << "bad list line " << ln << "\n"; return 2; }
      is >> it.label; std::string m; if (is >> m) it.mode = m;
      if (it.mode != "builder" && it.mode != "given") { std::cerr << "bad rates mode on line " << ln << "\n"; return 2; }
      items.push_back(it);
    }
  }
  if (expect >= 0 && (long)items.size() != expect) { std::cerr << "list holds " << items.size() << " lines, expected " << expect << "\n"; return 4; }
  std::vector<Result> res(items.size());
#ifdef _OPENMP
  omp_set_num_threads(threads);
#pragma omp parallel for schedule(dynamic, 1)
#endif
  for (long i = 0; i < (long)items.size(); ++i) {
    auto &it = items[i]; auto &R = res[i]; R.sector = it.sector; R.L = it.L; R.id = it.id; R.label = it.label;
    auto t0 = std::chrono::steady_clock::now();
    try {
      std::ifstream pf(it.pack, std::ios::binary); pf.seekg(it.off); std::string text(it.len, '\0'); pf.read(&text[0], it.len);
      if (!pf) throw std::runtime_error("cannot read member");
      Graph g = parse(text);
      if (g.id != it.id || g.L != it.L) throw std::runtime_error("identity mismatch");
      certify(g, R, O, it.mode == "given");
    } catch (const std::exception &e) { R.error = e.what(); }
    R.seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  }
  std::ofstream out(argv[2]);
  long n_written = 0, n_bad = 0, n_err = 0;
  for (size_t i = 0; i < res.size(); ++i) {
    const auto &R = res[i];
    bool structural = R.error.empty() && R.rate_mismatch == 0 && R.failures == 0 && R.structural_mismatch == 0 && R.greedy_fail == 0;
    bool bounded = structural && R.min_bound[0] > 0 && R.min_bound[1] > 0;
    bool cert = structural && R.min_second[0] > 0 && R.min_second[1] > 0;  // finite second moment at both rates
    if (!R.error.empty()) n_err++;
    if (!cert) n_bad++;
    out << "{\"sector\":\"" << R.sector << "\",\"L\":" << R.L << ",\"id\":" << R.id << ",\"label\":\"" << R.label << "\",\"rates_mode\":\"" << R.rates_mode
        << "\",\"E\":" << R.E << ",\"terms\":" << R.terms
        << ",\"monomials\":" << R.monomials << ",\"basis_entries\":" << R.basis_entries << ",\"clamped\":" << R.clamped
        << ",\"raw_min\":" << (R.clamped ? R.raw_min : 0) << ",\"max_orders_cancelled\":" << R.max_orders_cancelled
        << ",\"rate_mismatch\":" << R.rate_mismatch << ",\"structural_mismatch\":" << R.structural_mismatch
        << ",\"tight\":" << R.tight << ",\"higher\":" << R.higher << ",\"failures\":" << R.failures
        << ",\"degenerate_retries\":" << R.degenerate_retries << ",\"trial_disagreements\":" << R.trial_disagreements
        << ",\"greedy_checked\":" << R.greedy_checked << ",\"greedy_fail\":" << R.greedy_fail
        << ",\"legacy_rates\":" << (R.legacy ? "true" : "false") << ",\"series_subsets\":" << R.series_subsets
        << ",\"primes\":[";
    for (size_t k = 0; k < R.primes.size(); ++k) out << (k ? "," : "") << "\"" << R.primes[k] << "\"";
    out << "],\"points_per_prime\":" << R.points_per_prime << ",\"max_degree_bound\":" << R.max_degree << ",\"max_height_bits\":" << jnum(R.max_height_bits)
        << ",\"gamma\":" << jnum(R.gamma) << ",\"log10_err_max\":" << jnum(R.log10_err_max) << ",\"log10_err_sum\":" << jnum(R.log10_err_sum)
        << ",\"min_bound_margin_a\":" << (double)R.min_bound[0] << ",\"min_bound_margin_b\":" << (double)R.min_bound[1]
        << ",\"min_second_margin_a\":" << (double)R.min_second[0] << ",\"min_second_margin_b\":" << (double)R.min_second[1] << ",\"xi_bound_a\":" << (double)R.xi[0] << ",\"xi_bound_b\":" << (double)R.xi[1]
        << ",\"bounded\":" << (bounded ? "true" : "false") << ",\"failed_sets\":[";
    for (size_t k = 0; k < R.failed_sets.size(); ++k) out << (k ? "," : "") << R.failed_sets[k];
    out << "],\"certified\":" << (cert ? "true" : "false") << ",\"error\":\"" << R.error << "\",\"seconds\":" << R.seconds << "}\n";
    n_written++;
  }
  out.close();
  if (!out) { std::cerr << "cannot write " << argv[2] << "\n"; return 2; }
  std::cerr << "tc_cert: " << items.size() << " listed, " << n_written << " records, " << n_err << " with errors, " << n_bad << " not certified; seed "
            << O.seed << ", " << O.K << " primes x " << O.J << " points\n";
  if (n_written != (long)items.size() || (expect >= 0 && n_written != expect)) return 4;
  return (n_err || n_bad) ? 3 : 0;
}
