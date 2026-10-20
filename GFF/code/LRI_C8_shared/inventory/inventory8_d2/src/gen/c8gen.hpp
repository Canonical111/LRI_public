// gen/c8gen.hpp: shared definitions of the C8(2) d=2 payload generator (LRI_C8_D2_HPC, PLAN.md component A).
//
// Class files (classesL.txt, from the C8(1) enumeration) hold a header "n NG" and then exactly NG rows
// "key aut orbit". A key packs the edge multiplicity of every vertex pair (a<b, lexicographic) into 2 bits, so a
// 9-vertex (8-loop) class needs 72 bits: 5,068 of the 26,540 L8 keys exceed 2^64. Reading them into uint64_t
// with operator>> sets failbit and yields silent garbage, which is why every reader here is checked.
#pragma once
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
  cf.rows.reserve(size_t(ng));
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
