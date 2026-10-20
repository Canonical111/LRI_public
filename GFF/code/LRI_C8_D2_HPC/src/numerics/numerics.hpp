// Opt-in numerics profiles (Stage 4c; PLAN D1, A-FLAG-1..5). Included ONLY by src/kernel.hpp, ONLY in a profile build
// (`make gmp NUMERICS=<p>[,<p>...]`: -DC8_NUMERICS and one -DC8_NUMERICS_<P> per profile), and twice: with
// C8_NX_STAGE 1 before calculate_shared and with C8_NX_STAGE 2 after it. No include guard, on purpose. Each profile
// header src/numerics/<p>.hpp is included at both stages and selects its part with #if C8_NX_STAGE == 1 / 2.
//
// The default build never sees this directory: its executables stay byte-identical (A-RPL-8, checked by
// benchmarks/expanse_2026-10-c8/stage4c/scripts/s4c_build.slurm).
//
// Contract with src/kernel.hpp (see "Opt-in numerics hooks" there):
//   stage 1   a profile may define C8_NX_SHARED_BEGIN(T), C8_NX_XS_Q(e), C8_NX_XS_MP(e) (exp1 owns these three) and its
//             own C8_NX_PARAMS_<P> (a function printing its JSON object body, see nx::describe). Only the code above
//             the stage-1 include point of kernel.hpp exists: Graph, Scratch, Eval, ld, Q, MP, exponential, absolute,
//             quadfast. kernel.hpp supplies the exact defaults of every hook a profile leaves undefined.
//   stage 2   calculate_shared exists. This file defines, in this order:
//               nx::mp_tier_exact  the exact MP tier (gmp_float<350>), as the default evaluate() runs it;
//               [mp256.hpp]        nx::mp256::tier, which may escalate to nx::mp_tier_exact;
//               nx::mp_tier        the MP tier of this build (mp256's, or the exact one);
//               nx::quad_tier      the exact binary128 tier, which hands a 1e-23 failure to nx::mp_tier;
//               [dd.hpp]           nx::dd::tier, which may route to nx::quad_tier or nx::mp_tier;
//               nx::promote        what evaluate() calls for a point that fails the 1e-9 test (dd's tier, or
//                                  nx::quad_tier).
//             Every tier sets f (the accepted value, a long double), lev (1: the middle tier, binary128 or dd; 2: an
//             MP tier; the worker counts quad = lev >= 1 and mp = lev >= 2) and nx::last_tier (the finer tier code
//             below, read by tests/numerics_f1.cpp for F3).
//   F1        a profile may define C8_NX_F1_CHECKS_<P>(g, lx, shift, counts) (F1 tool only); this file's nx::f1_checks
//             (C8_NX_F1_CHECKS) runs every one of the build, in the order exp1, mp256, dd (end of stage 2).
// With every profile a stub (the framework's no-op headers, commit 9870a68), a profile executable computes exactly the
// exact path's numbers: nx::promote = nx::quad_tier, nx::mp_tier = nx::mp_tier_exact, and the xs hooks are the
// defaults. The implemented profiles (Stage 4c, merged on c8): dd (R3b), mp256 (R4b) and exp1 (R4c).
#if !defined(C8_NUMERICS)
#error "src/numerics/numerics.hpp belongs to opt-in profile builds only (make gmp NUMERICS=<profile>)"
#endif
#if !defined(C8_USE_GMP)
#error "the opt-in numerics profiles exist for the gmp backend only (PLAN A-FLAG-1)"
#endif
#if !defined(C8_NX_STAGE)
#error "src/numerics/numerics.hpp is included by src/kernel.hpp only"
#endif
#if !defined(C8_NUMERICS_DD) && !defined(C8_NUMERICS_MP256) && !defined(C8_NUMERICS_EXP1)
#error "C8_NUMERICS without a profile macro (C8_NUMERICS_DD, C8_NUMERICS_MP256, C8_NUMERICS_EXP1)"
#endif

#if C8_NX_STAGE == 1
#include <ostream>
namespace nx {
// The finer tier of the last promoted point of this thread (F3). Tier 0 is never stored: a point accepted by the first
// pass has Eval::level 0 and does not reach nx::promote.
enum Tier : int { LD = 0, DD = 1, QUAD = 2, MP256 = 3, MP350 = 4 };
constexpr int NTIER = 5;
constexpr const char* tier_names[NTIER] = {"long_double", "double_double", "binary128", "mp256", "mp350"};
inline thread_local int last_tier = LD;
// The profile name: the enabled profiles in the canonical order dd, mp256, exp1, joined by '+'. The Makefile names the
// executable bin/c8d2_gmp_<name> by the same rule, and `production.py plan --numerics <name>` checks --describe.
struct Name { char s[32]{}; };
constexpr Name make_name() {
    Name n{}; int k = 0;
    const char* parts[3] = {
#ifdef C8_NUMERICS_DD
        "dd",
#else
        nullptr,
#endif
#ifdef C8_NUMERICS_MP256
        "mp256",
#else
        nullptr,
#endif
#ifdef C8_NUMERICS_EXP1
        "exp1",
#else
        nullptr,
#endif
    };
    for (const char* p : parts) { if (!p) continue; if (k) n.s[k++] = '+'; while (*p) n.s[k++] = *p++; }
    return n;
}
inline constexpr Name profile_name = make_name();
}  // namespace nx
#ifdef C8_NUMERICS_DD
#include "dd.hpp"
#endif
#ifdef C8_NUMERICS_MP256
#include "mp256.hpp"
#endif
#ifdef C8_NUMERICS_EXP1
#include "exp1.hpp"
#endif
#ifndef C8_NX_PARAMS_DD
#define C8_NX_PARAMS_DD(os) (os << "\"stub\":true")
#endif
#ifndef C8_NX_PARAMS_MP256
#define C8_NX_PARAMS_MP256(os) (os << "\"stub\":true")
#endif
#ifndef C8_NX_PARAMS_EXP1
#define C8_NX_PARAMS_EXP1(os) (os << "\"stub\":true")
#endif
namespace nx {
// The profile fields of --describe and of the native JSON: ,"numerics_params":{"<p>":{...},...} for every enabled
// profile, in the canonical order. A profile prints its parameters (thresholds, routing) through C8_NX_PARAMS_<P>.
inline void describe(std::ostream& os) {
    os << ",\"numerics_params\":{"; bool first = true;
    auto open = [&](const char* name) { if (!first) os << ','; first = false; os << '"' << name << "\":{"; };
#ifdef C8_NUMERICS_DD
    open("dd"); C8_NX_PARAMS_DD(os); os << '}';
#endif
#ifdef C8_NUMERICS_MP256
    open("mp256"); C8_NX_PARAMS_MP256(os); os << '}';
#endif
#ifdef C8_NUMERICS_EXP1
    open("exp1"); C8_NX_PARAMS_EXP1(os); os << '}';
#endif
    os << '}';
}
}  // namespace nx
#define C8_NX_DESCRIBE(os) nx::describe(os);

#elif C8_NX_STAGE == 2
namespace nx {
// The exact MP tier: the statements of the default evaluate(), with the tier code.
inline void mp_tier_exact(const Graph& g, const ld* lx, ld shift, ld& f, int& lev) {
    auto m = calculate_shared<MP, C8_MP_NEED_ERROR>(g, lx, shift); f = m.first.convert_to<ld>(); lev = 2; last_tier = MP350;
    C8_DIAG_TIER(2); C8_DIAG_MP(m);
}
}  // namespace nx
#ifdef C8_NUMERICS_MP256
#include "mp256.hpp"
#endif
namespace nx {
inline void mp_tier(const Graph& g, const ld* lx, ld shift, ld& f, int& lev) {
#ifdef C8_NUMERICS_MP256
    mp256::tier(g, lx, shift, f, lev);
#else
    mp_tier_exact(g, lx, shift, f, lev);
#endif
}
// The exact binary128 tier: the statements of the default evaluate(); a 1e-23 failure goes to this build's MP tier.
inline void quad_tier(const Graph& g, const ld* lx, ld shift, ld& f, int& lev) {
    auto q = calculate_shared<Q>(g, lx, shift); lev = 1; f = ld(q.first); last_tier = QUAD; C8_DIAG_TIER(1); C8_DIAG_QUAD(q);
    if (absolute(q.first) < Q(1e-23L) * q.second) mp_tier(g, lx, shift, f, lev);
}
}  // namespace nx
#ifdef C8_NUMERICS_DD
#include "dd.hpp"
#endif
#ifdef C8_NUMERICS_EXP1
#include "exp1.hpp"
#endif
namespace nx {
// evaluate()'s promotion of a point that fails the long-double 1e-9 test.
inline void promote(const Graph& g, const ld* lx, ld shift, ld& f, int& lev) {
#ifdef C8_NUMERICS_DD
    dd::tier(g, lx, shift, f, lev);
#else
    quad_tier(g, lx, shift, f, lev);
#endif
}
}  // namespace nx
// F1 checks (tests/numerics_f1.cpp only: it calls C8_NX_F1_CHECKS after evaluate() at every point). Each profile defines
// its own C8_NX_F1_CHECKS_<P> (exp1 at stage 1, mp256 and dd at stage 2), and this one function runs all of them, so a
// combination build checks every profile. Order: exp1 drains the counters evaluate() left, mp256 reads the tier
// evaluate() took (nx::last_tier, mp256::reached), and dd last, because its checks evaluate the point again (quad_tier
// and the forced guards may reach the MP tier); the state those re-evaluations leave is cleared, so that the next
// point's checks start from its own evaluate().
#if defined(C8_NX_F1_CHECKS_DD) || defined(C8_NX_F1_CHECKS_MP256) || defined(C8_NX_F1_CHECKS_EXP1)
namespace nx {
template<class Counts> inline void f1_checks(const Graph& g, const ld* lx, ld shift, Counts& counts) {
#ifdef C8_NX_F1_CHECKS_EXP1
    C8_NX_F1_CHECKS_EXP1(g, lx, shift, counts);
#endif
#ifdef C8_NX_F1_CHECKS_MP256
    C8_NX_F1_CHECKS_MP256(g, lx, shift, counts);
#endif
#ifdef C8_NX_F1_CHECKS_DD
    C8_NX_F1_CHECKS_DD(g, lx, shift, counts);
#endif
#ifdef C8_NUMERICS_MP256
    mp256::reached = false;
#endif
#ifdef C8_NUMERICS_EXP1
    exp1::counters = exp1::Counters{};
#endif
}
}  // namespace nx
#define C8_NX_F1_CHECKS(g, lx, shift, counts) nx::f1_checks(g, lx, shift, counts)
#endif
#else
#error "C8_NX_STAGE must be 1 or 2"
#endif
