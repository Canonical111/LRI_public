// tc_cert.cpp: per-graph analytic certificate that the C8(2) importance weights are bounded (tail check, 2026-10-07).
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
// This program (1) recomputes raw(S) for every proper nonempty S exactly as the builder does and checks the stored
// rate table against max(raw, floor)/2; (2) at every clamped S, expands sum_F N_F/U_F in lambda at a random point
// modulo two 61/62-bit primes and checks that every Laurent coefficient below order nu* (the first order with
// |S|/2 + nu* > 0) vanishes, i.e. m_G(S) >= alpha_G(S) (Schwartz-Zippel: a nonzero coefficient vanishes at a
// random point with probability <= deg/p ~ 1e-16 per prime); the coefficient AT nu* tells whether m_G(S) =
// alpha_G(S) exactly ("tight") or larger; (3) checks on random orderings that every term's denominator monomial set
// has a simultaneous minimizer of all suffix counts (the matroid/greedy property that makes the single-scale
// exponents control nested sector limits). If (1)-(3) pass, m_G(S) >= alpha_G(S) > rho_c alpha_G(S) at every S, so
// the weight T_c is bounded in every sector (exponent of z_i at least (1 - rho_c) alpha_G(S_i) > 0): all moments of
// the per-point estimator are finite at both production rates.
//
// Usage: tc_cert LIST OUT.jsonl [threads]
//   LIST lines: "<sector> <L> <id> <pack path> <offset> <length>" (members verified by the Python driver).
// Output: one JSON object per graph.
#include <algorithm>
#include <chrono>
#include <numeric>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
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
static const u64 PRIMES[2] = {2305843009213693951ULL /* 2^61-1 */, 4611686018427387847ULL /* 2^62-57 */};

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
  std::string sector; int L = 0, id = 0, E = 0, terms = 0, monomials = 0;
  long basis_entries = 0;
  int clamped = 0, rate_mismatch = 0, raw_min = 1000, max_orders_cancelled = 0;
  int tight = 0, higher = 0, failures = 0, degenerate_retries = 0, structural_mismatch = 0;
  int greedy_checked = 0, greedy_fail = 0;
  long double min_bound[2] = {1e9, 1e9}, min_second[2] = {1e9, 1e9};  // min over S of m_low - rho alpha, 2 m_low - rho alpha
  bool legacy = false; int series_subsets = 0;
  long double xi[2] = {0, 0};  // analytic tail-index bound max_S (1 - m_low/(rho alpha))^+ of the weight
  std::vector<unsigned> failed_sets;
  std::string error;
  double seconds = 0;
};

static void certify(const Graph &g, Result &R) {
  const int E = g.E, L = g.L, ALL = (1 << E) - 1, T = (int)g.basis.size();
  R.E = E; R.terms = T; R.monomials = (int)g.masks.size();
  for (auto &b : g.basis) R.basis_entries += (long)b.size();
  for (auto m : g.masks) if (__builtin_popcount(m) != L || m > (unsigned)ALL) throw std::runtime_error("nonhomogeneous mask");
  // (1) raw(S) exactly as gen/build_free.cpp and gen/build_power.cpp
  std::vector<int> raw(ALL + 1, 100);
  std::vector<int8_t> dist(ALL + 1);
  std::vector<unsigned> supp(T, 0);
  for (int t = 0; t < T; ++t) {
    std::fill(dist.begin(), dist.end(), (int8_t)100);
    for (int k : g.basis[t]) dist[g.masks[k]] = 0;
    for (int b = 0; b < E; ++b) { int bit = 1 << b; for (int s = 0; s <= ALL; ++s) if (!(s & bit)) { int u = s | bit; int a = dist[s], c = dist[u]; dist[s] = (int8_t)std::min(a, c + 1); dist[u] = (int8_t)std::min(c, a + 1); } }
    for (int i = 0; i < E; ++i) if (g.co[t][i]) supp[t] |= 1u << i;
    for (int s = 1; s < ALL; ++s) { int pc = __builtin_popcount((unsigned)s); int h = (L - E + pc + int(dist[ALL ^ s])) / 2; int a = (supp[t] & ~(unsigned)s) ? 0 : 1; raw[s] = std::min(raw[s], pc + 2 * a - 2 * h); }
  }
  for (int s = 1; s < ALL; ++s) {
    int pc = __builtin_popcount((unsigned)s); int fl = (pc % 2) ? 1 : 2; int want = std::max(fl, raw[s]);
    if (!g.legacy && g.rate2[s] != want) R.rate_mismatch++;
    if (raw[s] <= 0) { R.clamped++; R.raw_min = std::min(R.raw_min, raw[s]); }
  }
  if (!g.legacy && (g.rate2[0] != 0 || g.rate2[ALL] != 0)) R.rate_mismatch++;
  R.legacy = g.legacy;
  // (2) the clamped subsets: Laurent coefficients of sum_F N_F/U_F at a random point, two primes
  std::vector<std::array<u64, 2>> y(E);
  std::vector<std::array<u64, 2>> val(g.masks.size());
  std::mt19937_64 rng(0x7a11c4ec0ULL ^ (u64(g.id) * 0x9e3779b97f4a7c15ULL) ^ (u64(L) << 56));
  auto draw = [&]() {
    for (int e = 0; e < E; ++e) for (int q = 0; q < 2; ++q) y[e][q] = 1 + rng() % (PRIMES[q] - 1);
    for (size_t k = 0; k < g.masks.size(); ++k) for (int q = 0; q < 2; ++q) {
      Mod M{PRIMES[q]}; u64 v = 1; unsigned m = g.masks[k]; while (m) { int e = __builtin_ctz(m); m &= m - 1; v = M.mul(v, y[e][q]); } val[k][q] = v; }
  };
  draw();
  const long double rho[2] = {0.8L, 0.9L};
  for (int s = 1; s < ALL; ++s) {
    const int pc = __builtin_popcount((unsigned)s);
    const long double alpha = g.rate[s];
    auto note = [&](long double mlow) { for (int q = 0; q < 2; ++q) { R.min_bound[q] = std::min(R.min_bound[q], mlow - rho[q] * alpha); R.min_second[q] = std::min(R.min_second[q], 2 * mlow - rho[q] * alpha); if (alpha > 0) R.xi[q] = std::max(R.xi[q], 1 - mlow / (rho[q] * alpha)); } };
    if (!g.legacy && raw[s] > 0) { note(raw[s] / 2.0L); continue; }  // term-wise bound: m >= raw/2 = alpha
    if ((raw[s] - pc) % 2) throw std::runtime_error("raw parity");
    R.series_subsets++;
    const int vmin = (raw[s] - pc) / 2;
    const int nustar = -(pc / 2) + (pc % 2 == 0 ? 1 : 0);       // first order with |S|/2 + nu > 0
    const int jneed = (int)std::ceil((double)(alpha - pc / 2.0L));  // first order with |S|/2 + nu >= alpha
    const int jtop = std::max(std::max(nustar, jneed), vmin) + 1;
    const int nord = jtop - vmin + 1;
    if (raw[s] <= 0) R.max_orders_cancelled = std::max(R.max_orders_cancelled, nustar - vmin);
    int lowest[2] = {1000, 1000};
    for (int attempt = 0; attempt < 4; ++attempt) {
      bool degenerate = false;
      for (int q = 0; q < 2 && !degenerate; ++q) {
        Mod M{PRIMES[q]};
        std::vector<u64> coef(nord, 0);
        for (int t = 0; t < T; ++t) {
          u64 c[9] = {0, 0, 0, 0, 0, 0, 0, 0, 0}; unsigned present = 0;
          for (int k : g.basis[t]) { int j = __builtin_popcount(g.masks[k] & (unsigned)s); c[j] = M.add(c[j], val[k][q]); present |= 1u << j; }
          const int h = __builtin_ctz(present);
          u64 n0 = 0, n1 = 0;
          for (int e = 0; e < E; ++e) if (g.co[t][e]) { u64 term = M.mul(M.from(g.co[t][e]), y[e][q]); if (s >> e & 1) n1 = M.add(n1, term); else n0 = M.add(n0, term); }
          const int a = (supp[t] & ~(unsigned)s) ? 0 : 1;
          const int vT = a - h;
          if (vT < vmin) { R.structural_mismatch++; continue; }
          if (vT > jtop) continue;
          if (c[h] == 0) { degenerate = true; break; }
          const int need = jtop + h;  // inv up to this index
          std::vector<u64> inv(need + 1, 0);
          const u64 i0 = M.inv(c[h]);
          inv[0] = i0;
          for (int n = 1; n <= need; ++n) { u64 acc = 0; for (int k = 1; k <= n && h + k <= L; ++k) acc = M.add(acc, M.mul(c[h + k], inv[n - k])); inv[n] = M.mul(M.sub(0, acc), i0); }
          for (int j = std::max(vmin, -h); j <= jtop; ++j) {
            int idx = j + h; u64 v = M.mul(n0, inv[idx]); if (idx >= 1) v = M.add(v, M.mul(n1, inv[idx - 1]));
            coef[j - vmin] = M.add(coef[j - vmin], v);
          }
        }
        if (degenerate) break;
        lowest[q] = 1000;
        for (int j = 0; j < nord; ++j) if (coef[j]) { lowest[q] = vmin + j; break; }
      }
      if (!degenerate) break;
      R.degenerate_retries++; draw();
      if (attempt == 3) throw std::runtime_error("degenerate random points 4 times");
    }
    // a coefficient nonzero modulo either prime is nonzero; a vanishing one must vanish modulo both
    const int low = std::min(lowest[0], lowest[1]);
    const int mord = low < 1000 ? low : jtop + 1;                  // exact leading order, or a lower bound of it
    if (raw[s] <= 0) {
      if (mord < nustar) { R.failures++; if (R.failed_sets.size() < 20) R.failed_sets.push_back((unsigned)s); }
      else if (mord == nustar) R.tight++; else R.higher++;
    }
    note(pc / 2.0L + mord);
  }
  // (3) greedy / simultaneous-minimizer property on random orderings
  std::mt19937_64 rg(0x5ec70ULL ^ u64(g.id) ^ (u64(L) << 48));
  std::vector<int> perm(E), pos(E);
  for (int rep = 0; rep < 16; ++rep) {
    std::iota(perm.begin(), perm.end(), 0); std::shuffle(perm.begin(), perm.end(), rg);
    for (int j = 0; j < E; ++j) pos[perm[j]] = j;  // position 0 = largest x
    for (int t = 0; t < T; ++t) {
      // suffix S_k = edges at positions >= k (k = 1..E-1); count |m & S_k| for each monomial
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

int main(int argc, char **argv) {
  if (argc < 3) { std::cerr << "usage: tc_cert LIST OUT.jsonl [threads]\n"; return 1; }
  struct Item { std::string sector, pack; int L, id; long long off, len; };
  std::vector<Item> items;
  { std::ifstream lf(argv[1]); Item it; while (lf >> it.sector >> it.L >> it.id >> it.pack >> it.off >> it.len) items.push_back(it); }
  int threads = argc > 3 ? std::atoi(argv[3]) : 1;
  std::vector<Result> res(items.size());
#ifdef _OPENMP
  omp_set_num_threads(threads);
#pragma omp parallel for schedule(dynamic, 1)
#endif
  for (long i = 0; i < (long)items.size(); ++i) {
    auto &it = items[i]; auto &R = res[i]; R.sector = it.sector; R.L = it.L; R.id = it.id;
    auto t0 = std::chrono::steady_clock::now();
    try {
      std::ifstream pf(it.pack, std::ios::binary); pf.seekg(it.off); std::string text(it.len, '\0'); pf.read(&text[0], it.len);
      if (!pf) throw std::runtime_error("cannot read member");
      Graph g = parse(text);
      if (g.id != it.id || g.L != it.L) throw std::runtime_error("identity mismatch");
      certify(g, R);
    } catch (const std::exception &e) { R.error = e.what(); }
    R.seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  }
  std::ofstream out(argv[2]);
  for (auto &R : res) {
    bool structural = R.error.empty() && R.rate_mismatch == 0 && R.failures == 0 && R.structural_mismatch == 0 && R.greedy_fail == 0;
    bool bounded = structural && R.min_bound[0] > 0 && R.min_bound[1] > 0;
    bool cert = structural && R.min_second[0] > 0 && R.min_second[1] > 0;  // finite second moment at both rates
    out << "{\"sector\":\"" << R.sector << "\",\"L\":" << R.L << ",\"id\":" << R.id << ",\"E\":" << R.E << ",\"terms\":" << R.terms
        << ",\"monomials\":" << R.monomials << ",\"basis_entries\":" << R.basis_entries << ",\"clamped\":" << R.clamped
        << ",\"raw_min\":" << (R.clamped ? R.raw_min : 0) << ",\"max_orders_cancelled\":" << R.max_orders_cancelled
        << ",\"rate_mismatch\":" << R.rate_mismatch << ",\"structural_mismatch\":" << R.structural_mismatch
        << ",\"tight\":" << R.tight << ",\"higher\":" << R.higher << ",\"failures\":" << R.failures
        << ",\"degenerate_retries\":" << R.degenerate_retries << ",\"greedy_checked\":" << R.greedy_checked << ",\"greedy_fail\":" << R.greedy_fail
        << ",\"legacy_rates\":" << (R.legacy ? "true" : "false") << ",\"series_subsets\":" << R.series_subsets
        << ",\"min_bound_margin_a\":" << (double)R.min_bound[0] << ",\"min_bound_margin_b\":" << (double)R.min_bound[1]
        << ",\"min_second_margin_a\":" << (double)R.min_second[0] << ",\"min_second_margin_b\":" << (double)R.min_second[1] << ",\"xi_bound_a\":" << (double)R.xi[0] << ",\"xi_bound_b\":" << (double)R.xi[1]
        << ",\"bounded\":" << (bounded ? "true" : "false") << ",\"failed_sets\":[";
    for (size_t k = 0; k < R.failed_sets.size(); ++k) out << (k ? "," : "") << R.failed_sets[k];
    out << "],\"certified\":" << (cert ? "true" : "false") << ",\"error\":\"" << R.error << "\",\"seconds\":" << R.seconds << "}\n";
  }
  return 0;
}
