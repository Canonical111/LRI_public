// R3b `dd` (PLAN A-FLAG-3/4; Stage 4c): the double-double tier. Opt-in only (`make gmp NUMERICS=dd`, NX_FLAGS_dd =
// -mavx2 -mfma); the default executables never include this file (A-RPL-8). Design, error analysis and measurements:
// docs/NUMERICS.md, "R3b: the double-double tier (profile dd)". Included by src/numerics/numerics.hpp at both stages
// (no include guard); stage 1 also stands alone (tests/dd_accuracy.cpp includes it with C8_NX_STAGE 1 only).
//
// A point that fails the long-double 1e-9 test is evaluated in double-double (dd: an unevaluated sum hi + lo of two
// doubles, 106-bit significand, every product error captured with an explicit fma) instead of binary128, when
//   (range)    every |lx_j - shift/L| <= 300 (evaluate()'s moderate test with 300), and
//   (products) no product underflows: every product of the prefix-shared monomial table lies in [2^-900, 2^900]
//              (C8_DD_GUARD 0, the default); and the dd value and error are finite.
// Otherwise the point stays on binary128 (nx::quad_tier, bit for bit the exact path's statements). The dd value is
// accepted when |val| >= C8_DD_RATIO (1e-20) x err, err the error scale built like the binary128 one,
// err = sum_t (sum_i |c_i x_i|) / U_t (over S), here in double precision (only its magnitude enters the test). A dd
// failure goes, with C8_DD_ROUTING 1 (cascade, the default), to binary128 when |val| >= C8_DD_CASCADE_LOW (1e-23) x err
// (binary128 then applies its own 1e-23 test and may still go to MP) and straight to MP below; with C8_DD_ROUTING 0
// (direct) every dd failure goes to MP. Routing changes only the cost: every accepted value passed its tier's test.
//
// Formula. Mathematically the binary128 tier's: f = (sum_t n_t / U_t) / S with n_t = sum_i c_i x_i, U_t the sums of
// the degree-L monomials in xs_j = exp(lx_j - shift/L), S = sum_j x_j. The dd tier computes only the E exponentials
// xs_j and uses them for the numerators and S as well: x_j = exp(shift/L) xs_j, so the common factor exp(shift/L)
// cancels exactly between every n_t and S, and between val and err (with shift = 0, the usual case, x_j = xs_j
// anyway). The monomial products, the prefix-shared segment sums and the term order are the kernel's tables.
//
// Parameters are fixed in a profile build. Development builds (measurements only) may override C8_DD_RATIO,
// C8_DD_CASCADE_LOW, C8_DD_ROUTING or C8_DD_GUARD together with -DC8_DD_DEVELOPMENT; --describe then says
// "development":true in numerics_params.dd.
#if C8_NX_STAGE == 1
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <map>
#include <ostream>
#include <string>
#if defined(C8_DD_RATIO) || defined(C8_DD_CASCADE_LOW) || defined(C8_DD_ROUTING) || defined(C8_DD_GUARD)
#ifndef C8_DD_DEVELOPMENT
#error "the dd profile's parameters are fixed (PLAN A-FLAG-4); overriding C8_DD_RATIO, C8_DD_CASCADE_LOW, C8_DD_ROUTING or C8_DD_GUARD needs -DC8_DD_DEVELOPMENT (measurement builds only)"
#endif
#endif
#ifndef C8_DD_RATIO
#define C8_DD_RATIO 1e-20
#endif
#ifndef C8_DD_CASCADE_LOW
#define C8_DD_CASCADE_LOW 1e-23
#endif
#ifndef C8_DD_ROUTING
#define C8_DD_ROUTING 1
#endif
#ifndef C8_DD_GUARD
#define C8_DD_GUARD 0
#endif
#if C8_DD_ROUTING != 0 && C8_DD_ROUTING != 1
#error "C8_DD_ROUTING: 1 (cascade dd -> binary128 -> MP) or 0 (direct dd -> MP)"
#endif
#if C8_DD_GUARD != 0 && C8_DD_GUARD != 1
#error "C8_DD_GUARD: 0 (every product in [2^-900, 2^900]) or 1 (development: with every xs_j <= 1, every denominator >= 2^-900)"
#endif
#if defined(C8_DD_PHASE_TIMERS) && !defined(C8_DD_DEVELOPMENT)
#error "C8_DD_PHASE_TIMERS (per-phase cycle counters for the F1 checks) is a development build: add -DC8_DD_DEVELOPMENT"
#endif
#if defined(__x86_64__) && !defined(__FMA__)
#error "the dd profile needs the hardware fma: build it with make gmp NUMERICS=dd (NX_FLAGS_dd = -mavx2 -mfma)"
#endif
#ifdef C8_DD_PHASE_TIMERS
#include <x86intrin.h>
#define C8_DD_T0() unsigned long long t_ = __rdtsc()
#define C8_DD_TP(k) do { const unsigned long long n_ = __rdtsc(); phase_cycles[k] += n_ - t_; t_ = n_; } while (0)
#else
#define C8_DD_T0() ((void)0)
#define C8_DD_TP(k) ((void)0)
#endif
#define C8_DD_STR2(x) #x
#define C8_DD_STR(x) C8_DD_STR2(x)
#define C8_DD_INLINE __attribute__((always_inline)) inline
namespace nx {
namespace dd {
// A double-double (double-word) value hi + lo, normalized: |lo| <= ulp(hi)/2. u = 2^-53 below; the error bounds quoted are relative,
// for normal operands and results (docs/NUMERICS.md, "R3b", derives them; tests/dd_accuracy.cpp measures them).
struct DW { double h, l; };
C8_DD_INLINE DW two_sum(double a, double b) { const double s = a + b, bb = s - a; return {s, (a - (s - bb)) + (b - bb)}; }  // exact
C8_DD_INLINE DW fast_two_sum(double a, double b) { const double s = a + b; return {s, b - (s - a)}; }  // exact if |a| >= |b|
C8_DD_INLINE DW two_prod(double a, double b) { const double p = a * b; return {p, __builtin_fma(a, b, -p)}; }  // exact
C8_DD_INLINE DW neg(DW x) { return {-x.h, -x.l}; }
// x + y, any signs (accurate addition): <= 3u^2 |x + y|.
C8_DD_INLINE DW add(DW x, DW y) {
    const DW s = two_sum(x.h, y.h), t = two_sum(x.l, y.l);
    const DW v = fast_two_sum(s.h, s.l + t.h);
    return fast_two_sum(v.h, t.l + v.l);
}
// x + d: <= 2u^2 |x + d|.
C8_DD_INLINE DW add_d(DW x, double d) { const DW s = two_sum(x.h, d); return fast_two_sum(s.h, x.l + s.l); }
// x * y: <= 6u^2 |x y| (fma for the cross terms).
C8_DD_INLINE DW mul(DW x, DW y) {
    const double ch = x.h * y.h, cl1 = __builtin_fma(x.h, y.h, -ch);
    const double tl1 = __builtin_fma(x.h, y.l, x.l * y.l), cl2 = __builtin_fma(x.l, y.h, tl1);
    return fast_two_sum(ch, cl1 + cl2);
}
// x * d: <= 2u^2 |x d|.
C8_DD_INLINE DW mul_d(DW x, double d) {
    const double ch = x.h * d, cl1 = __builtin_fma(x.h, d, -ch);
    return fast_two_sum(ch, __builtin_fma(x.l, d, cl1));
}
// x / y: th = x.h / y.h, the residual x - th y (x.h - th y.h is exact), its correction: <= 11u^2 |x / y|.
C8_DD_INLINE DW div(DW x, DW y) {
    const double th = x.h / y.h; const DW p = two_prod(th, y.h);
    const double r = __builtin_fma(-th, y.l, ((x.h - p.h) - p.l) + x.l);
    return fast_two_sum(th, r / y.h);
}
// x / d: <= 4u^2 |x / d|.
C8_DD_INLINE DW div_d(DW x, double d) {
    const double th = x.h / d; const DW p = two_prod(th, d);
    return fast_two_sum(th, (((x.h - p.h) - p.l) + x.l) / d);
}
// long double (64-bit significand) -> dd exactly; dd -> long double with one rounding.
C8_DD_INLINE DW from_ld(long double x) { const double h = double(x); return {h, double(x - (long double)h)}; }
C8_DD_INLINE long double to_ld(DW x) { return (long double)x.h + (long double)x.l; }
// 2^k as a double, -1022 <= k <= 1023.
C8_DD_INLINE double pow2(int k) { const uint64_t b = uint64_t(k + 1023) << 52; double d; std::memcpy(&d, &b, sizeof d); return d; }

// Constants (tests/test_dd_profile.py re-derives every one from mpmath at 600 bits):
// ln 2 = LN2_1 + LN2_2 + LN2_3 + O(2^-157): LN2_1 has 42 significant bits, so k LN2_1 is exact for |k| < 2^11.
constexpr double LN2_1 = 0x1.62e42fefa3800p-1, LN2_2 = 0x1.ef35793c76730p-45, LN2_3 = 0x1.f97b57a079a19p-103;
constexpr double INV_LN2 = 0x1.71547652b82fep+0;
// 1/k! as dd, k = 0..11 (each to within 2^-106 relative).
constexpr DW INV_FACT[12] = {
    {0x1p+0, 0.0}, {0x1p+0, 0.0}, {0x1p-1, 0.0},
    {0x1.5555555555555p-3, 0x1.5555555555555p-57}, {0x1.5555555555555p-5, 0x1.5555555555555p-59},
    {0x1.1111111111111p-7, 0x1.1111111111111p-63}, {0x1.6c16c16c16c17p-10, -0x1.f49f49f49f49fp-65},
    {0x1.a01a01a01a01ap-13, 0x1.a01a01a01a01ap-73}, {0x1.a01a01a01a01ap-16, 0x1.a01a01a01a01ap-76},
    {0x1.71de3a556c734p-19, -0x1.c154f8ddc6c00p-73}, {0x1.27e4fb7789f5cp-22, 0x1.cbbc05b4fa99ap-76},
    {0x1.ae64567f544e4p-26, -0x1.c062e06d1f209p-80}};
constexpr int EXP_SQUARINGS = 6;   // |r| <= ln2/2 is scaled by 2^-6 before the Taylor series
constexpr int EXP_DEGREE = 11;     // Taylor degree of expm1 on |x| <= 0.00542: truncation < 3e-34 relative
// exp(a) for a dd argument with -670 <= a <= 700 (the tier uses |a| <= 300; below -670 the low part of the result is
// subnormal and the relative accuracy degrades, above 709.78 it overflows). k = nearest(a/ln2), r = a - k ln2 with the
// three-part ln 2 (k LN2_1 and a.h - k LN2_1 exact, the rest in dd); x = r/64; expm1(x) by its degree-11 Taylor
// polynomial (Horner in dd); six doublings expm1(2y) = expm1(y) (2 + expm1(y)), which keep the relative error of the
// small quantity expm1 instead of doubling it at every squaring; exp(a) = 2^k (1 + expm1(r)). Relative error
// <= 40u^2 (about 5e-31; tests/dd_accuracy.cpp measures the largest).
inline DW exp_dd(DW a) {
    const double k = __builtin_nearbyint(a.h * INV_LN2);
    const DW p2 = two_prod(k, LN2_2);
    DW r = two_sum(a.h - k * LN2_1, a.l);
    r = add(r, neg(p2));
    r = add_d(r, -(k * LN2_3));
    const DW x = {r.h * 0x1p-6, r.l * 0x1p-6};
    DW q = INV_FACT[EXP_DEGREE];
    for (int i = EXP_DEGREE - 1; i >= 1; --i) q = add(mul(q, x), INV_FACT[i]);
    DW s = mul(q, x);
    for (int i = 0; i < EXP_SQUARINGS; ++i) s = mul(s, add_d(s, 2.0));
    const DW e = add_d(s, 1.0); const double p = pow2(int(k));
    return {e.h * p, e.l * p};
}
// The positive compensated sum of the kernel's segments: hi + lo += sum_k P[idx[k]] over [begin, end). Each addend's
// hi goes through an exact two_sum on the running hi; the rounding errors and the addends' lo parts collect in lo,
// which is folded back (fast_two_sum) after every block of 8 addends and at the end, so hi + lo is a normalized dd on
// return. A segment of n >= 8 addends runs in 4 independent lanes (GCC vector extensions: AVX2 here, two NEON
// registers on arm64), lane 0 starting from (hi, lo) and lane i taking the addends k = begin + i mod 4, each lane
// folded after 8 of its addends; the lanes are combined by three accurate dd additions and the last n mod 4 addends
// added by the scalar loop. Relative error <= (7.5 n + 1) u^2 for n < 8 and <= (7.5 n + 29) u^2 for n >= 8
// (docs/NUMERICS.md, "R3b"). The scalar loop's critical path is one double addition per addend instead of a dd
// addition's nine; the lanes then remove the throughput limit of the two_sum (8 additions per addend).
constexpr int SUM_BLOCK = 8, SUM_LANES = 4;
typedef double V4 __attribute__((vector_size(32)));
C8_DD_INLINE void sum_scalar(double& hi, double& lo, const DW* P, const int* idx, int k, int end) {
    while (k < end) {
        const int stop = end - k > SUM_BLOCK ? k + SUM_BLOCK : end;
        for (; k < stop; ++k) {
            const DW p = P[idx[k]]; const double s = hi + p.h, bb = s - hi;
            lo += ((hi - (s - bb)) + (p.h - bb)) + p.l; hi = s;
        }
        const double s = hi + lo; lo -= s - hi; hi = s;
    }
}
C8_DD_INLINE void sum_positive(double& hi, double& lo, const DW* P, const int* idx, int begin, int end) {
    if (end - begin < 2 * SUM_LANES) { sum_scalar(hi, lo, P, idx, begin, end); return; }
    V4 H = {hi, 0.0, 0.0, 0.0}, Lo = {lo, 0.0, 0.0, 0.0};
    int k = begin; const int vend = end - (end - begin) % SUM_LANES;
    while (k < vend) {
        const int stop = vend - k > SUM_LANES * SUM_BLOCK ? k + SUM_LANES * SUM_BLOCK : vend;
        for (; k < stop; k += SUM_LANES) {
            const DW a = P[idx[k]], b = P[idx[k + 1]], c = P[idx[k + 2]], d = P[idx[k + 3]];
            const V4 ph = {a.h, b.h, c.h, d.h}, pl = {a.l, b.l, c.l, d.l};
            const V4 s = H + ph, bb = s - H;
            Lo += ((H - (s - bb)) + (ph - bb)) + pl; H = s;
        }
        const V4 s = H + Lo; Lo -= s - H; H = s;
    }
    DW t = add(DW{H[0], Lo[0]}, DW{H[1], Lo[1]}); t = add(t, DW{H[2], Lo[2]}); t = add(t, DW{H[3], Lo[3]});
    hi = t.h; lo = t.l;
    sum_scalar(hi, lo, P, idx, k, end);
}
// Development builds with -DC8_DD_PHASE_TIMERS: rdtsc cycles per phase of the dd evaluation (xs, products, sums,
// numerators, terms), read by the F1 checks; the arithmetic is unchanged.
constexpr int NPHASE = 5;
constexpr const char* phase_names[NPHASE] = {"xs", "products", "sums", "numerators", "terms"};
inline thread_local unsigned long long phase_cycles[NPHASE] = {};
inline void params(std::ostream& os) {
    os << "\"dd_ratio\":\"" C8_DD_STR(C8_DD_RATIO) "\",\"routing\":\"" << (C8_DD_ROUTING ? "cascade" : "direct") << '"'
       << ",\"cascade_low\":\"" C8_DD_STR(C8_DD_CASCADE_LOW) "\",\"range\":300,\"guard\":\""
       << (C8_DD_GUARD ? "denominators" : "products") << "\",\"product_range\":[\"2^-900\",\"2^900\"],\"exp\":\"dd-k-ln2-r64-taylor11-x6\""
       << ",\"sum\":\"compensated-b8-x4\",\"err\":\"double\""
#ifdef C8_DD_PHASE_TIMERS
       << ",\"phase_timers\":true"
#endif
       << ",\"development\":"
#ifdef C8_DD_DEVELOPMENT
       << "true";
#else
       << "false";
#endif
}
}  // namespace dd
}  // namespace nx
#define C8_NX_PARAMS_DD(os) nx::dd::params(os)

#elif C8_NX_STAGE == 2
namespace nx {
namespace dd {
struct Scratch {
    std::array<DW, EMAX> xs{};
    std::vector<DW> products, sums, numerator;
    std::vector<double> abs_numerator;
    void resize(const Graph& g) {
        products.resize(g.products.size() + 1); sums.resize(g.segments.size() + 1);
        numerator.resize(g.numerators.size()); abs_numerator.resize(g.numerators.size());
    }
};
// The route of a promoted point (F1 checks and the routing measurement read it through nx::dd::trace).
enum Route : int { NONE = -1, ACCEPT = 0, GUARD_RANGE = 1, GUARD_PRODUCTS = 2, GUARD_NONFINITE = 3, RATIO_QUAD = 4, RATIO_MP = 5 };
constexpr int NROUTE = 6;
constexpr const char* route_names[NROUTE] = {"accepted", "guard_range", "guard_products", "guard_nonfinite", "ratio_to_binary128", "ratio_to_mp"};
struct Trace { int route = NONE; double ratio = 0; };
inline thread_local Trace trace;
constexpr long double RANGE = 300;
constexpr double TINY = 0x1p-900, BIG = 0x1p900;
struct Value { DW val; double err; DW S; bool literal, le1, dens; };
// The dd evaluation: GUARD_* when the point stays on binary128, else ACCEPT with v (val, err, S) set. Force (F1 checks
// only): 1 every point out of range, 2 every point fails the product guard. Classify (F1 checks only): no early exit,
// so that v.literal (every product in [2^-900, 2^900]), v.le1 (every xs_j <= 1) and v.dens (every denominator
// >= 2^-900) are all set.
template<int Force, bool Classify = false>
inline int evaluate_dd(const Graph& g, const ld* lx, ld shift, Value& v) {
    for (int j = 0; j < g.E; ++j) if (Force == 1 || fabsl(lx[j] - shift / g.L) > RANGE) return GUARD_RANGE;
    static thread_local Scratch scratch;
    auto& s = scratch; s.resize(g); C8_DD_T0();
    // xs_j = exp(lx_j - shift/L); the argument is exact when shift = 0, else c = shift/L is one dd for every j
    const DW c = shift == 0 ? DW{0, 0} : div_d(from_ld(shift), double(g.L));
    DW S = {0, 0}; bool le1 = true;
    for (int j = 0; j < g.E; ++j) {
        const DW a = shift == 0 ? from_ld(lx[j]) : add(from_ld(lx[j]), neg(c));
        const DW x = exp_dd(a); s.xs[j] = x; S = add(S, x); le1 &= x.h <= 1.0;
    }
    C8_DD_TP(0);
    DW* P = s.products.data(); P[0] = {1.0, 0.0}; bool inrange = Force != 2;
    for (size_t j = 0; j < g.products.size(); ++j) {
        const auto o = g.products[j]; const DW p = mul(P[o.first], s.xs[o.second]); P[j + 1] = p;
        inrange &= (p.h >= TINY) & (p.h <= BIG);
    }
    C8_DD_TP(1);
    v.literal = inrange; v.le1 = le1; v.dens = Force != 2;
    // C8_DD_GUARD 0: every product in range. C8_DD_GUARD 1 (development): with every xs_j <= 1 the products may
    // underflow, and every denominator is checked below instead (the products only shrink, so an underflowed one
    // carries an absolute error <= L 2^-1074 against a denominator >= 2^-900).
    const bool relaxed = C8_DD_GUARD == 1 && le1;
    if (!Classify && !relaxed && !inrange) return GUARD_PRODUCTS;
    DW* U = s.sums.data(); U[0] = {0.0, 0.0};
    const int* ad = g.addends.data();
    for (size_t j = 0; j < g.segments.size(); ++j) {
        const auto a = g.segments[j]; double hi = U[a.parent].h, lo = U[a.parent].l;
        sum_positive(hi, lo, P, ad, a.begin, a.end); U[j + 1] = {hi, lo};
    }
    C8_DD_TP(2);
    for (size_t j = 0; j < g.numerators.size(); ++j) {
        DW n = {0.0, 0.0}; double ab = 0;
        for (auto [i, c8] : g.numerators[j]) { const double cd = double(c8); n = add(n, mul_d(s.xs[i], cd)); ab += std::fabs(cd) * s.xs[i].h; }
        s.numerator[j] = n; s.abs_numerator[j] = ab;
    }
    C8_DD_TP(3);
    DW val = {0.0, 0.0}; double err = 0; bool dens = Force != 2;
    for (const auto& t : g.terms) {
        const DW& u = U[t.denominator]; dens &= u.h >= TINY;
        val = add(val, div(s.numerator[t.numerator], u)); err += s.abs_numerator[t.numerator] / u.h;
    }
    C8_DD_TP(4);
    v.dens = dens; v.val = val; v.err = err; v.S = S;
    if (!(relaxed ? dens : inrange)) return GUARD_PRODUCTS;
    if (!(std::isfinite(val.h) && std::isfinite(val.l) && std::isfinite(err))) return GUARD_NONFINITE;
    return ACCEPT;
}
template<int Force>
inline void tier_impl(const Graph& g, const ld* lx, ld shift, ld& f, int& lev) {
    Value v; const int r = evaluate_dd<Force>(g, lx, shift, v);
    if (r != ACCEPT) { trace = {r, 0.0}; quad_tier(g, lx, shift, f, lev); return; }
    const double av = std::fabs(v.val.h), ratio = av / v.err;
    if (!(av < C8_DD_RATIO * v.err)) { f = to_ld(div(v.val, v.S)); lev = 1; last_tier = nx::DD; trace = {ACCEPT, ratio}; return; }
#if C8_DD_ROUTING
    if (!(av < C8_DD_CASCADE_LOW * v.err)) { trace = {RATIO_QUAD, ratio}; quad_tier(g, lx, shift, f, lev); return; }
#endif
    trace = {RATIO_MP, ratio}; lev = 1; mp_tier(g, lx, shift, f, lev);
}
inline void tier(const Graph& g, const ld* lx, ld shift, ld& f, int& lev) { tier_impl<0>(g, lx, shift, f, lev); }

// F1 checks (C8_NX_F1_CHECKS_DD; tests/numerics_f1.cpp calls them through numerics.hpp's nx::f1_checks after
// evaluate() at every point, after the other profiles' checks; a counter whose name ends in
// _violations fails F1). For every promoted point: its route; the range guard against an independent recomputation;
// the point forced out of range and forced through the product guard, each of which must give exactly nx::quad_tier's
// value, level and tier (binary128 or an MP tier: mp350, or mp256 in a combination build); the decade of the dd ratio |val|/err with binary128's verdict on the same point (the data
// that fixes C8_DD_CASCADE_LOW); the guard classes (products in range; else every xs_j <= 1 and every denominator
// >= 2^-900); and, for a dd-accepted point, the difference to binary128 in units of binary128's err (<= 1e-26).
inline int decade(double x) { if (!(x > 0)) return -99; const int d = int(std::floor(std::log10(x))); return d < -98 ? -98 : (d > 9 ? 9 : d); }
template<class Map>
inline void f1_checks(const Graph& g, const ld* lx, ld shift, Map& counts) {
    const Trace t = trace; trace = Trace{};
    if (t.route == NONE) return;   // accepted by the first pass
    counts["dd_points"]++; counts[std::string("dd_route_") + route_names[t.route]]++;
    long double dev = 0; for (int j = 0; j < g.E; ++j) dev = std::max(dev, fabsl(lx[j] - shift / g.L));
    if (dev > RANGE) { counts["dd_out_of_range_points"]++; if (t.route != GUARD_RANGE) counts["dd_out_of_range_not_guarded_violations"]++; }
    else if (t.route == GUARD_RANGE) counts["dd_in_range_guarded_violations"]++;
    ld fq = 0; int lq = 0; quad_tier(g, lx, shift, fq, lq); const int tq = last_tier;
    for (int force = 1; force <= 2; ++force) {
        ld ff = 0; int lf = 0;
        if (force == 1) tier_impl<1>(g, lx, shift, ff, lf); else tier_impl<2>(g, lx, shift, ff, lf);
        const int tf = last_tier; const Trace tt = trace; trace = Trace{};
        const bool same = std::memcmp(&ff, &fq, 10) == 0 && lf == lq && tf == tq && (tf == QUAD || tf == MP256 || tf == MP350)
                          && tt.route == (force == 1 ? GUARD_RANGE : GUARD_PRODUCTS);
        const std::string name = force == 1 ? "dd_forced_out_of_range" : "dd_forced_product_guard";
        counts[name + "_points"]++; if (!same) counts[name + "_violations"]++;
    }
    if (dev <= RANGE) {
        Value c; evaluate_dd<0, true>(g, lx, shift, c);
        counts[c.literal ? "dd_guard_class_products_in_range" : (c.le1 && c.dens ? "dd_guard_class_le1_denominators_in_range" : "dd_guard_class_neither")]++;
    }
    if (t.route == ACCEPT || t.route == RATIO_QUAD || t.route == RATIO_MP) {
        counts["dd_ratio_decade_" + std::to_string(decade(t.ratio)) + (tq == QUAD ? "_binary128_pass" : "_binary128_fail")]++;
        if (t.route == ACCEPT && tq != QUAD) counts["dd_accepted_binary128_fails_violations"]++;
    }
#ifdef C8_DD_PHASE_TIMERS
    if (dev <= RANGE) {   // one dd evaluation and one binary128 calculate_shared on the same (warm) point, in cycles
        for (auto& c : phase_cycles) c = 0;
        Value w; unsigned long long t0 = __rdtsc(); evaluate_dd<0>(g, lx, shift, w); const unsigned long long t1 = __rdtsc();
        const auto b = calculate_shared<Q>(g, lx, shift); const unsigned long long t2 = __rdtsc(); (void)b;
        counts["dd_timer_points"]++; counts["dd_timer_dd_cycles"] += t1 - t0; counts["dd_timer_binary128_cycles"] += t2 - t1;
        for (int k = 0; k < NPHASE; ++k) counts[std::string("dd_timer_phase_") + phase_names[k] + "_cycles"] += phase_cycles[k];
        counts["dd_timer_products_count"] += g.products.size(); counts["dd_timer_addends_count"] += g.addends.size();
        counts["dd_timer_segments_count"] += g.segments.size(); counts["dd_timer_terms_count"] += g.terms.size();
    }
#endif
    if (t.route == ACCEPT) {
        Value v; evaluate_dd<0>(g, lx, shift, v); const DW q = div(v.val, v.S);
        const auto b = calculate_shared<Q>(g, lx, shift);
        const Q d = absolute((Q(q.h) + Q(q.l)) - b.first), sc = b.second > 0 ? d / b.second : d;
        counts["dd_vs_binary128_scaled_decade_" + std::to_string(sc > 0 ? decade(double(sc)) : -99)]++;
        if (!(sc <= Q(1e-26L))) counts["dd_vs_binary128_scaled_over_1e-26_violations"]++;
    }
}
}  // namespace dd
}  // namespace nx
#define C8_NX_F1_CHECKS_DD(g, lx, shift, counts) nx::dd::f1_checks(g, lx, shift, counts)
#endif
