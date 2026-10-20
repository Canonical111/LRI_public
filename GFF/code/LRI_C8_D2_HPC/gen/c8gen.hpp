// gen/c8gen.hpp: shared definitions of the C8(2) d=2 payload generator (LRI_C8_D2_HPC, PLAN.md component A).
//
// Class files (classesL.txt, from the C8(1) enumeration) hold a header "n NG" and then exactly NG rows
// "key aut orbit". A key packs the edge multiplicity of every vertex pair (a<b, lexicographic) into 2 bits, so a
// 9-vertex (8-loop) class needs 72 bits: 5,068 of the 26,540 L8 keys exceed 2^64. Reading them into uint64_t
// with operator>> sets failbit and yields silent garbage, which is why every reader here is checked. The generator
// programs read through read_generator_classes, which adds the semantic validation the builders rely on (below).
#pragma once
#include <algorithm>
#include <climits>
#include <fstream>
#include <istream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using Key = unsigned __int128;
constexpr int NV = 9;                   // at most 9 vertices: L <= 8 loops
constexpr int NP = NV * (NV - 1) / 2;   // 36 vertex pairs
// The rows reserved up front by read_classes (classes8.txt has 26,540): a header NG up to INT_MAX must end in the
// InputError of its first missing row, not in an allocation of NG rows (std::bad_alloc); the vector grows past it.
constexpr long long CLASS_RESERVE_CAP = 1LL << 16;
static_assert(2 * NP <= 128, "a class key packs 2 bits per vertex pair into 128 bits");

struct InputError : std::runtime_error {
  using std::runtime_error::runtime_error;
};

// Decimal rendering of a key (the standard streams have no operator<< for unsigned __int128).
inline std::string u128s(Key x) {
  if (x == 0) return "0";
  char b[48];
  int p = 47;
  b[p] = 0;
  while (x) {
    b[--p] = char('0' + int(x % 10));
    x /= 10;
  }
  return std::string(b + p);
}

// Strict decimal parse of one token: digits only, value below 2^128. Every error names the token.
inline Key parse_u128(const std::string &tok) {
  if (tok.empty()) throw InputError("empty key token");
  const Key top = ~Key(0);
  Key x = 0;
  for (char c : tok) {
    if (c < '0' || c > '9') throw InputError("key token '" + tok + "' is not a decimal number");
    const unsigned d = unsigned(c - '0');
    if (x > (top - d) / 10) throw InputError("key token '" + tok + "' overflows 2^128");
    x = x * 10 + d;
  }
  return x;
}

// Reads one whitespace-delimited token and parses it with parse_u128.
inline Key readu128(std::istream &in) {
  std::string tok;
  if (!(in >> tok)) throw InputError("missing key token");
  return parse_u128(tok);
}

// Strict decimal parse of a nonnegative count (header fields, aut, orbit).
inline long long parse_count(const std::string &tok, const char *what) {
  if (tok.empty()) throw InputError(std::string("empty ") + what + " token");
  long long x = 0;
  for (char c : tok) {
    if (c < '0' || c > '9') throw InputError(std::string(what) + " token '" + tok + "' is not a decimal number");
    const int d = c - '0';
    if (x > (LLONG_MAX - d) / 10) throw InputError(std::string(what) + " token '" + tok + "' overflows");
    x = x * 10 + d;
  }
  return x;
}

struct ClassRow {
  Key key;
  long long aut, orbit;
};

struct ClassFile {
  int n = 0, NG = 0;
  std::vector<ClassRow> rows;
};

inline std::vector<std::string> split_tokens(const std::string &line) {
  std::istringstream is(line);
  std::vector<std::string> out;
  std::string t;
  while (is >> t) out.push_back(t);
  return out;
}

// Reads a class file: header "n NG" with 1 <= n <= NV, then exactly NG rows of exactly three tokens
// "key aut orbit", one row per line, and nothing but whitespace after them. A key must fit the 2 n(n-1)/2 bits of
// an n-vertex class. Throws InputError naming the file, the row and the offending token.
inline ClassFile read_classes(const std::string &path) {
  std::ifstream f(path);
  if (!f) throw InputError(path + ": cannot open class file");
  std::string line;
  if (!std::getline(f, line)) throw InputError(path + ": empty file, expected the header 'n NG'");
  const std::vector<std::string> head = split_tokens(line);
  if (head.size() != 2) throw InputError(path + ": header must be 'n NG', got '" + line + "'");
  long long n = 0, ng = 0;
  try {
    n = parse_count(head[0], "n");
    ng = parse_count(head[1], "NG");
  } catch (const InputError &e) {
    throw InputError(path + ": header: " + e.what());
  }
  if (n < 1 || n > NV) throw InputError(path + ": header n=" + head[0] + " outside [1, " + std::to_string(NV) + "]");
  if (ng > INT_MAX) throw InputError(path + ": header NG=" + head[1] + " too large");
  const int keybits = int(n * (n - 1));  // 2 bits per vertex pair
  ClassFile cf;
  cf.n = int(n);
  cf.NG = int(ng);
  cf.rows.reserve(size_t(std::min(ng, CLASS_RESERVE_CAP)));
  for (long long i = 0; i < ng; i++) {
    const std::string where = path + ": row " + std::to_string(i + 1) + " of " + std::to_string(ng);
    if (!std::getline(f, line)) throw InputError(where + ": missing (file truncated)");
    const std::vector<std::string> t = split_tokens(line);
    if (t.size() != 3)
      throw InputError(where + ": expected 'key aut orbit', got " + std::to_string(t.size()) + " tokens in '" + line + "'");
    ClassRow r{};
    try {
      r.key = parse_u128(t[0]);
      r.aut = parse_count(t[1], "aut");
      r.orbit = parse_count(t[2], "orbit");
    } catch (const InputError &e) {
      throw InputError(where + ": " + e.what());
    }
    if (keybits < 128 && (r.key >> keybits) != 0)
      throw InputError(where + ": key token '" + t[0] + "' does not fit " + std::to_string(keybits) + " bits (n=" +
                       head[0] + ")");
    cf.rows.push_back(r);
  }
  while (std::getline(f, line)) {
    const std::vector<std::string> t = split_tokens(line);
    if (!t.empty())
      throw InputError(path + ": trailing token '" + t[0] + "' after the " + std::to_string(ng) + " declared rows");
  }
  if (f.bad()) throw InputError(path + ": read error");
  return cf;
}

// Semantic validation of a class file for the generator programs (build_free, build_power, check_edge_forests),
// kept apart from the syntax-only reader above (gen/test_keys.py round-trips class files through read_classes alone).
// The builders walk exactly E = 2L edges (ed[e] for e < E), index fact[4 - deg] and form
// D_G = aut * prod_pairs m! * prod_vertices (4 - deg)! in long long, and their spanning-tree walk needs L >= 1 and a
// connected graph. So before any output is created and before any OpenMP region every class must be:
//   * of a supported loop order: 2 <= n <= NV (L = n - 1 in [1, 8]), with NG >= 1 classes;
//   * a graph of exactly 2L edges (the key's 2-bit pair multiplicities), every vertex of degree <= 4, connected;
//   * with aut >= 1, orbit >= 1 and aut * orbit = n! (the orbit of the n! vertex labellings), so D_G is a positive
//     long long, here computed with overflow checks;
//   * with a key no other row of the file has.
// The decoding pass only adds (edge counts and degrees: at most 36 * 3 = 108); no product is formed until the edge
// count, the degrees and aut, orbit are accepted, and then every multiplication is checked (Stage-6 round-2 finding
// S6R2-B-01: a key such as 2^72 - 1, all 36 multiplicities 3, used to overflow the pair product before its edge
// count was looked at).
// Every class file classes1..8 of reference/c8d1_inputs8 satisfies all of them. Throws InputError naming the file,
// the row and the defect. Nothing here changes what the builders compute for a valid class.
inline long long checked_mul(long long a, long long b, const std::string &where, const char *what) {
  long long r = 0;
  if (__builtin_mul_overflow(a, b, &r)) throw InputError(where + ": " + what + " overflows a long long");
  return r;
}

inline void validate_generator_classes(const ClassFile &cf, const std::string &path) {
  const int n = cf.n;
  if (n < 2 || n > NV)
    throw InputError(path + ": header n=" + std::to_string(n) + ": the generator needs 2 <= n <= " +
                     std::to_string(NV) + " (L = n - 1 loops in [1, " + std::to_string(NV - 1) + "])");
  if (cf.NG < 1 || size_t(cf.NG) != cf.rows.size())
    throw InputError(path + ": header NG=" + std::to_string(cf.NG) + ": the generator needs at least one class");
  const int L = n - 1, E = 2 * L;
  long long nfact = 1;
  for (int k = 2; k <= n; k++) nfact *= k;  // n <= 9: at most 362880
  static const long long fact[] = {1, 1, 2, 6, 24};
  std::vector<Key> keys;
  keys.reserve(cf.rows.size());
  for (size_t i = 0; i < cf.rows.size(); i++) {
    const ClassRow &r = cf.rows[i];
    const std::string where = path + ": row " + std::to_string(i + 1) + " of " + std::to_string(cf.NG) + " (key " +
                              u128s(r.key) + ")";
    int deg[NV] = {}, parent[NV];
    for (int v = 0; v < NV; v++) parent[v] = v;
    auto find = [&parent](int v) {
      while (parent[v] != v) v = parent[v];
      return v;
    };
    int edges = 0, ix = 0, comps = n;
    for (int a = 0; a < n; a++)
      for (int b = a + 1; b < n; b++, ix++) {
        const int m = int((r.key >> (2 * ix)) & 3);
        if (!m) continue;
        edges += m;  // sums only: no product before the checks below
        deg[a] += m;
        deg[b] += m;
        const int ra = find(a), rb = find(b);
        if (ra != rb) {
          parent[ra] = rb;
          comps--;
        }
      }
    if (edges != E)
      throw InputError(where + ": " + std::to_string(edges) + " edges, an n=" + std::to_string(n) + " class (L=" +
                       std::to_string(L) + ") has exactly " + std::to_string(E));
    for (int v = 0; v < n; v++)
      if (deg[v] > 4)
        throw InputError(where + ": vertex " + std::to_string(v) + " has degree " + std::to_string(deg[v]) +
                         " > 4");
    if (comps != 1) throw InputError(where + ": the graph is not connected (" + std::to_string(comps) + " components)");
    if (r.aut < 1 || r.orbit < 1)
      throw InputError(where + ": aut=" + std::to_string(r.aut) + " and orbit=" + std::to_string(r.orbit) +
                       " must both be >= 1");
    if (checked_mul(r.aut, r.orbit, where, "aut * orbit") != nfact)
      throw InputError(where + ": aut * orbit = " + std::to_string(r.aut) + " * " + std::to_string(r.orbit) +
                       " differs from n! = " + std::to_string(nfact));
    // D_G in the builders' order (aut, then m! pair by pair, then (4 - deg)! vertex by vertex), every product checked:
    // all factors are >= 1, so a D_G that fits makes every partial product of the builders fit too.
    long long den = r.aut;
    ix = 0;
    for (int a = 0; a < n; a++)
      for (int b = a + 1; b < n; b++, ix++)
        den = checked_mul(den, fact[int((r.key >> (2 * ix)) & 3)], where, "the denominator D_G");
    for (int v = 0; v < n; v++) den = checked_mul(den, fact[4 - deg[v]], where, "the denominator D_G");
    if (den < 1) throw InputError(where + ": the denominator D_G = " + std::to_string(den) + " is not positive");
    keys.push_back(r.key);
  }
  std::vector<Key> sorted_keys(keys);
  std::sort(sorted_keys.begin(), sorted_keys.end());
  for (size_t i = 1; i < sorted_keys.size(); i++)
    if (sorted_keys[i] == sorted_keys[i - 1]) {
      size_t first = 0, second = 0;
      for (size_t j = 0; j < keys.size() && !second; j++)
        if (keys[j] == sorted_keys[i]) (first ? second : first) = j + 1;
      throw InputError(path + ": row " + std::to_string(second) + " of " + std::to_string(cf.NG) + " (key " +
                       u128s(sorted_keys[i]) + "): the key of row " + std::to_string(first) + " again");
    }
}

// The reader of the generator programs: read_classes, then validate_generator_classes.
inline ClassFile read_generator_classes(const std::string &path) {
  ClassFile cf = read_classes(path);
  validate_generator_classes(cf, path);
  return cf;
}
