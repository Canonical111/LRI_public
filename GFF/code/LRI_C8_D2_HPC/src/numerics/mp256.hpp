// R4b `mp256` (PLAN A-FLAG-3/5; Stage 4c; D1: an opt-in numerics change, off by default): the staged 256-bit MP tier.
// Built only by `make gmp NUMERICS=mp256` (or a combination naming mp256); included by src/numerics/numerics.hpp at
// both stages (no include guard). The default build never includes it (A-RPL-8).
//
// The tier. A point that fails the binary128 1e-23 test reaches nx::mp_tier, which in this profile is
// nx::mp256::tier:
//   1. calculate_shared<MP77,true>: the kernel's own shared-prefix evaluation (the operation sequence of the exact
//      350-digit tier: the same prefix products and sums, the same per-polynomial addition order, Boost's
//      exponentials, and C8_NX_XS_MP when a combination enables exp1) at gmp_float<77>, with the error estimate
//      err = sum_t sum_j |c_tj x_j| / U_t / S that the binary128 tier and the ratio-histogram build compute.
//      gmp_float<77> asks GMP for 257 bits; mpf rounds that up to whole limbs, so every value carries at least 320
//      significant bits (--describe: "mpf_precision_bits"), against 1,216 for gmp_float<350>.
//   2. Accepted when |v| >= C8_MP256_RATIO x err (default 1e-63, A-FLAG-5): f = v.convert_to<long double>() (Boost's
//      conversion, as in the exact tier), lev = 2, nx::last_tier = nx::MP256. With 77 decimal digits this leaves
//      at least 14 digits after the cancellation, as the binary128 test's 1e-23 leaves 11 of binary128's 34.
//   3. Otherwise the point is escalated to nx::mp_tier_exact, the unchanged 350-digit evaluation of the default
//      build (it sets nx::MP350). Stage 4a's P3 histograms put 2.0e-4 to 2.3e-3 of the MP evaluations below 1e-63
//      (the deepest at 1e-131).
// Every MP-promoted point keeps lev = 2, so the worker's quad and mp row counters mean what they mean in the default
// build. The process counts the tier's decisions (relaxed atomics, one increment per MP evaluation) and, when it made
// any, prints one line on stderr at exit: "mp256 tier: N MP evaluations: A accepted at 77 digits, B escalated to 350
// digits (ratio 1e-63)". No output file changes shape.
//
// F1 (A-FLAG-5: "F1 is checked on every MP-promoted point"): C8_NX_F1_CHECKS_MP256, compiled only into
// tests/numerics_f1.cpp, recomputes for every point that reached this tier the 77-digit evaluation and a 350-digit one
// with its own error estimate, and counts (tests/numerics_flags.py fails F1 on any nonzero *_violations counter):
//   mp256_mp_promoted, mp256_accepted, mp256_escalated            the points and the tier's decisions;
//   mp256_decision_violations     the recomputed decision differs from the one evaluate() took (nx::last_tier);
//   mp256_scaled_violations       an accepted point with |v77 - v350| > 1e-69 x err77: the error bound that, at the
//                                 acceptance threshold |v| = 1e-63 x err, still gives relative error <= 1e-6;
//   mp256_relative_violations     an accepted point with |v77 - v350| > 1e-6 |v350| (F1's own 1e-6 bound, against the
//                                 350-digit value; F1 also checks every accepted value against 450 digits);
//   mp256_ld_identical, mp256_ld_differs   whether an accepted point's long double equals the 350-digit tier's;
//   histograms (counter per decade e<k> = floor(log10)): mp256_ratio_e<k> of |v77|/err77 for every MP point,
//   mp256_accepted_scaled_e<k> of |v77 - v350|/err77, mp256_accepted_relative_e<k> of |v77 - v350|/|v350|, and
//   mp256_escalated_relative_e<k>, the relative error the 77-digit value would have had at an escalated point
//   ("zero" when the difference is 0).
// The macro is C8_NX_F1_CHECKS_MP256; numerics.hpp's nx::f1_checks (C8_NX_F1_CHECKS) runs it with every other
// profile's checks of the build, after exp1's and before dd's.
//
// Parameters (--describe and the native JSON, "numerics_params":{"mp256":{...}}): digits10, mpf_precision_bits,
// ratio (the text of C8_MP256_RATIO, parsed at 77 digits; a malformed value makes --describe fail) and the
// escalation tier. -DC8_MP256_RATIO=<decimal> changes the ratio for experiments only: the F-gates validate 1e-63. Any
// such override (even to 1e-63) makes the build a development build: --describe and the native JSON then add
// "development":true and "overrides":["C8_MP256_RATIO"], and production.py plan refuses it (A-FLAG-1). A build without
// the override prints neither field and compiles to the same program as before.
#if C8_NX_STAGE == 1
#include <atomic>
#include <cmath>
#include <cstdio>
#include <ostream>
#ifdef C8_MP256_RATIO
#define C8_NX_MP256_DEVELOPMENT 1
#else
#define C8_MP256_RATIO 1e-63
#endif
#define C8_NX_MP256_STR2(x) #x
#define C8_NX_MP256_STR(x) C8_NX_MP256_STR2(x)
namespace nx {
namespace mp256 {
constexpr unsigned digits10 = 77;
using MP77 = boost::multiprecision::number<boost::multiprecision::gmp_float<digits10>>;
constexpr const char* ratio_text = C8_NX_MP256_STR(C8_MP256_RATIO);
// The acceptance ratio at 77 digits, parsed once (thread-safe initialization of a function-local static).
inline const MP77& ratio() { static const MP77 r(ratio_text); return r; }
// The significand bits GMP gives a gmp_float<77> (mpf_get_prec: whole limbs, at least the 257 requested).
inline unsigned long precision_bits() { MP77 x; return static_cast<unsigned long>(mpf_get_prec(x.backend().data())); }
// The tier's decisions in this process, reported on stderr at exit when there were any.
struct alignas(64) Counters {
    std::atomic<unsigned long long> accepted{0}, escalated{0};
    ~Counters() {
        const unsigned long long a = accepted.load(), e = escalated.load();
        if (a + e) std::fprintf(stderr, "mp256 tier: %llu MP evaluations: %llu accepted at %u digits, %llu escalated to 350 digits (ratio %s)\n",
                                a + e, a, digits10, e, ratio_text);
    }
};
inline Counters counters;
// Set by tier() for the point it evaluates; read and cleared by the F1 checks (tests/numerics_f1.cpp only).
inline thread_local bool reached = false;
inline void params(std::ostream& os) {
    (void)ratio();  // a malformed C8_MP256_RATIO fails here, at --describe, before any evaluation
    os << "\"digits10\":" << digits10 << ",\"mpf_precision_bits\":" << precision_bits() << ",\"ratio\":\"" << ratio_text
       << "\",\"error_estimate\":\"calculate_shared<MP77,true>\",\"escalation\":\"mp350\""
#ifdef C8_NX_MP256_DEVELOPMENT
       << ",\"development\":true,\"overrides\":[\"C8_MP256_RATIO\"]"
#endif
       ;
}
}  // namespace mp256
}  // namespace nx
#define C8_NX_PARAMS_MP256(os) nx::mp256::params(os)

#elif C8_NX_STAGE == 2
namespace nx {
namespace mp256 {
inline void tier(const Graph& g, const ld* lx, ld shift, ld& f, int& lev) {
    reached = true;
    auto m = calculate_shared<MP77, true>(g, lx, shift);
    if (absolute(m.first) < ratio() * m.second) {
        counters.escalated.fetch_add(1, std::memory_order_relaxed);
        mp_tier_exact(g, lx, shift, f, lev);  // 350 digits; sets f, lev = 2, nx::last_tier = MP350
        return;
    }
    counters.accepted.fetch_add(1, std::memory_order_relaxed);
    f = m.first.convert_to<ld>(); lev = 2; last_tier = MP256; C8_DIAG_TIER(2);
}
// floor(log10(num/den)) as a counter suffix: "e<k>", "zero" (num = 0) or "inf" (den = 0 < num); long double holds every
// ratio met here (|v| and err are far inside its exponent range).
template<class R> std::string decade(const R& num, const R& den) {
    if (num == 0) return "zero";
    if (den == 0) return "inf";
    const ld r = R(num / den).template convert_to<ld>();
    return "e" + std::to_string(static_cast<long>(std::floor(std::log10(r))));
}
// The F1 checks of this tier (see the header comment); a template, so that only the F1 tool instantiates it.
template<class Counts> void f1_checks(const Graph& g, const ld* lx, ld shift, Counts& c) {
    if (!reached) return;
    reached = false;
    const bool took = last_tier == MP256;
    const auto m = calculate_shared<MP77, true>(g, lx, shift);
    const auto x = calculate_shared<MP, true>(g, lx, shift);
    const bool accept = !(absolute(m.first) < ratio() * m.second);
    c["mp256_mp_promoted"]++;
    if (accept != took) c["mp256_decision_violations"]++;
    MP v77, e77;  // exact copies: 350 digits hold every 77-digit value
    mpf_set(v77.backend().data(), m.first.backend().data());
    mpf_set(e77.backend().data(), m.second.backend().data());
    const MP d = abs(MP(v77 - x.first)), ax = abs(x.first);
    c["mp256_ratio_" + decade(MP(abs(v77)), e77)]++;
    if (!accept) {
        c["mp256_escalated"]++;
        c["mp256_escalated_relative_" + decade(d, ax)]++;
        return;
    }
    c["mp256_accepted"]++;
    c["mp256_accepted_scaled_" + decade(d, e77)]++;
    c["mp256_accepted_relative_" + decade(d, ax)]++;
    if (d > MP("1e-69") * e77) c["mp256_scaled_violations"]++;
    if (d > MP("1e-6") * ax) c["mp256_relative_violations"]++;
    if (m.first.convert_to<ld>() == x.first.convert_to<ld>()) c["mp256_ld_identical"]++;
    else c["mp256_ld_differs"]++;
}
}  // namespace mp256
}  // namespace nx
#define C8_NX_F1_CHECKS_MP256(g, lx, shift, counts) nx::mp256::f1_checks(g, lx, shift, counts)
#endif
