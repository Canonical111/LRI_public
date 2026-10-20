// R4c `exp1` (PLAN A-FLAG-3/5; Stage 4c; opt-in, off by default, D1): one exponential per call for the shifted
// coordinates of the binary128 and MP tiers. Where the exact path computes, per edge,
//     xs_j = exp(T(lx_j) - T(shift)/L)                                  (E exponentials per shifted call),
// this profile computes the factor F = exp(-(T(shift)/L)) once per call and
//     xs_j = x_j * F,  x_j = exp(T(lx_j)) (the value the tier computes anyway for its numerators and S).
// Only calls with shift != 0 change: a direct point (shift == 0) has xs_j = x_j on both paths and computes no F. The
// long-double first pass (calculate_products, calculate_reference<ld>) is untouched, and so is every other statement.
// Included by src/numerics/numerics.hpp at both stages (no include guard); stage 1 defines the hooks, stage 2 nothing.
//
// Tiers. binary128 (T = Q): F by expq, the product by quadfast::mul (libgcc's __multf3 bit for bit). Every MP type
// of calculate_shared (boost::multiprecision numbers: gmp_float<350>, and mp256's 77-digit tier in a combination
// build): F by the type's exp, the product by its operator*. Any other calculate_shared type (e.g. a double-double
// tier, should one use calculate_shared) keeps the exact expression: A-FLAG-5 applies exp1 to binary128 and MP only.
//
// Accuracy. Exact path: the argument T(lx_j) - a, a = T(shift)/L, carries the rounding of a (|a| eps, common to every
// edge) and of the subtraction (|lx_j - a| eps, per edge), then the exponential's own error. exp1: x_j has an exact
// argument, F carries the same |a| eps of a, and the product one rounding. The |a| eps part multiplies every xs_j by the
// same factor on both paths, hence every monomial of degree L by the same factor: it scales the value as a whole
// (relative L |a| eps) and is not amplified by the numerators' cancellation. The per-edge part, which is amplified by the
// cancellation (the acceptance ratios guard it), is bounded by about 2 ulps on exp1 (two exponentials of exact or
// common arguments and one product) and by (|lx_j - a| + 1) ulps on the exact path; on the forced shifted points of
// the dev_exp1 probe at L8 (where T(shift)/8 is exact) it measured at most 1.35 ulps on exp1 and 0.51 on the exact
// path. MP has no range limit (GMP exponents); its precision is 350 (or 77) digits on both paths.
//
// Range guard (binary128 only). x_j and F are separate binary128 numbers, so exp1 needs each in the normal range where
// the exact path needs only their quotient there: a call uses the product only when |shift| <= C8_EXP1_RANGE * L
// (|a| <= 5000), and an edge only when |lx_j| <= C8_EXP1_RANGE; then x_j, F and xs_j lie in [e^-10000, e^10000],
// inside binary128's normal range (|ln| < 11355). Every other edge of a shifted call takes the exact expression.
//
// Direct calls (in practice every call: the probe in benchmarks/expanse_2026-10-c8/stage4c/dev_exp1/ found no shifted
// point among 1.47e9 sampled ones) run as little extra code as possible: begin() returns an inactive factor after one
// test of shift, and the factor and the binary128 product live in out-of-line functions, so the loop of calculate_shared
// keeps the exact path's shape apart from the never-taken branch.
//
// Counters (F1/F3 only; they never change a number). Per thread, for the shifted calls only: the calls per type class,
// those that used the factor, and the edges that took the exact expression. The F1 tool
// (tests/numerics_f1.cpp) drains them after each point through C8_NX_F1_CHECKS_EXP1, which numerics.hpp's
// nx::f1_checks (C8_NX_F1_CHECKS) runs first among the profiles of the build. No counter is a *_violations counter:
// exp1's accuracy is gated by F1 itself and by the forced-shift probe (benchmarks/expanse_2026-10-c8/stage4c/dev_exp1/),
// since natural shifted points are rare.
#if C8_NX_STAGE == 1
// -DC8_EXP1_RANGE=<n> (an experiment; the F-gates validate 5000) makes the build a development build: --describe and the
// native JSON then add "development":true and "overrides":["C8_EXP1_RANGE"], and production.py plan refuses it
// (A-FLAG-1). A build without the override prints neither field.
#ifdef C8_EXP1_RANGE
#define C8_NX_EXP1_DEVELOPMENT 1
#else
#define C8_EXP1_RANGE 5000
#endif
namespace nx {
namespace exp1 {
constexpr ld range = C8_EXP1_RANGE;
static_assert(2 * C8_EXP1_RANGE < 11355, "x_j, F and xs_j must stay in binary128's normal range");
// Type classes of calculate_shared: binary128, the exact MP tier (gmp_float<350>), another MP type (mp256's), other.
enum Kind : int { KQ = 0, KMP = 1, KMPX = 2, KOTHER = 3 };
constexpr int NKIND = 4;
constexpr const char* kind_names[NKIND] = {"binary128", "mp350", "mp_other", "other"};
template <class T> constexpr bool is_q = std::is_same<T, Q>::value;
template <class T> constexpr bool is_mp = boost::multiprecision::is_number<T>::value;
template <class T> constexpr int kind = is_q<T> ? KQ : (std::is_same<T, MP>::value ? KMP : (is_mp<T> ? KMPX : KOTHER));
struct Counters { unsigned long long shifted[NKIND]{}, factored[NKIND]{}, exact_edges = 0; };
inline thread_local Counters counters{};
// The per-call factor: on = this call uses xs_j = x_j * f (shift != 0, a binary128 or MP type, and for binary128 the
// call guard). A direct call (shift == 0) computes nothing: its xs_j = x_j as on the exact path.
template <class T> struct Factor { bool on = false; T f{}; };
template <class T> __attribute__((noinline, cold)) Factor<T> shifted_factor(const Graph& g, ld shift) {
    Factor<T> F; Counters& c = counters; ++c.shifted[kind<T>];
    if constexpr (is_q<T>) {
        if (!(fabsl(shift) <= range * g.L)) return F;
        F.f = exponential(T(-(T(shift) / g.L))); F.on = true; ++c.factored[KQ];
    } else if constexpr (is_mp<T>) {
        F.f = exponential(T(-(T(shift) / g.L))); F.on = true; ++c.factored[kind<T>];
    }
    return F;
}
template <class T> inline Factor<T> begin(const Graph& g, ld shift) { return shift == 0 ? Factor<T>{} : shifted_factor<T>(g, shift); }
// The binary128 edge guard; NaN fails it.
inline bool edge_in_range(ld lx) { return fabsl(lx) <= range; }
// The binary128 product x_j * F (quadfast::mul, i.e. libgcc's __multf3 bit for bit), out of line.
__attribute__((noinline, cold)) inline Q mul_q(Q x, Q f) { return quadfast::mul(x, f); }
// An edge of a shifted call that takes the exact expression (binary128 guard, or a type exp1 does not touch).
template <class T> inline T exact_edge(T v) { ++counters.exact_edges; return v; }
// The MP product (only reached with F.on, i.e. for MP types).
template <class T> inline T scaled(const T& x, const Factor<T>& F) {
    if constexpr (is_mp<T>) return T(x * F.f); else return x;  // the else branch is unreachable: F.on is false
}
// F1/F3: this thread's counters since the last point (the F1 tool evaluates its points one at a time per thread),
// added to the F1 tool's named counters and reset.
template <class C> inline void f1_checks(const Graph&, const ld*, ld shift, C& counts) {
    const Counters c = counters; counters = Counters{};
    counts["exp1_points"] += 1; counts["exp1_points_shifted"] += shift != 0;
    for (int k = 0; k < NKIND; ++k) {
        if (!c.shifted[k] && k >= KMPX) continue;
        const std::string n = std::string("exp1_") + kind_names[k];
        counts[n + "_calls_shifted"] += c.shifted[k]; counts[n + "_calls_factored"] += c.factored[k];
    }
    counts["exp1_exact_edges_in_shifted_calls"] += c.exact_edges;
}
}  // namespace exp1
}  // namespace nx
// The hooks of src/kernel.hpp's calculate_shared<T> (locals g, logx, shift, s, j; template parameter T).
#define C8_NX_SHARED_BEGIN(T) const auto nx_exp1 = nx::exp1::begin<T>(g, shift);
#define C8_NX_XS_Q(e) (nx_exp1.on && nx::exp1::edge_in_range(logx[j]) ? nx::exp1::mul_q(s.x[j], nx_exp1.f) : nx::exp1::exact_edge(e))
#define C8_NX_XS_MP(e) (nx_exp1.on ? nx::exp1::scaled<T>(s.x[j], nx_exp1) : nx::exp1::exact_edge(T(e)))
#ifdef C8_NX_EXP1_DEVELOPMENT
#define C8_NX_PARAMS_EXP1(os) (os << "\"xs\":\"x_j*exp(-shift/L) per shifted call\",\"tiers\":\"binary128,mp\",\"binary128_range\":" << C8_EXP1_RANGE \
                                  << ",\"development\":true,\"overrides\":[\"C8_EXP1_RANGE\"]")
#else
#define C8_NX_PARAMS_EXP1(os) (os << "\"xs\":\"x_j*exp(-shift/L) per shifted call\",\"tiers\":\"binary128,mp\",\"binary128_range\":" << C8_EXP1_RANGE)
#endif
#define C8_NX_F1_CHECKS_EXP1(g, lx, shift, counts) nx::exp1::f1_checks(g, lx, shift, counts)
#elif C8_NX_STAGE == 2
#endif
