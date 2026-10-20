#pragma once
// Diagnostic hooks of kernel.hpp's evaluate() (PLAN component C, "Diagnostic builds"); included only under
// -DC8_TIER_TIMERS (`make profile` -> bin/c8d2_gmp_prof) or -DC8_RATIO_HISTOGRAM (`make ratiohist` ->
// bin/c8d2_gmp_ratiohist). `plan` never accepts these executables: their --describe reports "diagnostic":true.
// The hooks only read values the default code computes anyway; they never change an operand, so a diagnostic build
// writes the same rows as the default build (tests/validate.py, diagnostic_builds).
//
// Tier timers: thread-local seconds and calls per tier, in steady-clock time. Tier 0 is the first pass (long double:
// calculate_products, or calculate_reference<ld> for non-moderate points, plus the ratio test), tier 1 the binary128
// evaluation, tier 2 the MP evaluation with its conversion to long double. The worker sums the threads' totals.
//
// Ratio histograms: counts of floor(log10(|v|/err)) at the two promotion tests, bin b holding the ratios in
// [10^-b, 10^(1-b)) for b = 0..RATIO_BINS-2 (ratios >= 1 are counted in bin 0) and bin RATIO_BINS-1 holding ratio 0
// and every ratio below 10^-(RATIO_BINS-2):
//   ld_fail : the long-double ratio of every point that fails the 1e-9 test (and is promoted to binary128);
//   quad    : the binary128 ratio |q|/err_q of every binary128 evaluation (the 1e-23 test fails below bin 23);
//   mp      : |m|/err_m of every MP evaluation. Only this build accumulates the MP error estimate
//             (calculate_shared<MP,true>): its value is computed by the same operation sequence, the error terms
//             being separate variables, so the MP value and every row are those of the default build.
#include <chrono>
#include <ostream>
#if defined(C8_TIER_TIMERS) && defined(C8_RATIO_HISTOGRAM)
#error "build one diagnostic at a time (make profile or make ratiohist)"
#endif
constexpr int NTIERS=3;
constexpr int RATIO_BINS=402;
struct Diagnostics {
    double seconds[NTIERS]{};
    unsigned long long calls[NTIERS]{};
    unsigned long long ld_fail[RATIO_BINS]{},quad[RATIO_BINS]{},mp[RATIO_BINS]{};
    std::chrono::steady_clock::time_point last{};
    void add(const Diagnostics&o){
        for(int k=0;k<NTIERS;++k){seconds[k]+=o.seconds[k];calls[k]+=o.calls[k];}
        for(int b=0;b<RATIO_BINS;++b){ld_fail[b]+=o.ld_fail[b];quad[b]+=o.quad[b];mp[b]+=o.mp[b];}
    }
};
inline Diagnostics& thread_diagnostics(){static thread_local Diagnostics d;return d;}
inline void diagnostics_reset(){thread_diagnostics()=Diagnostics{};}
// floor(-log10(ratio)) clamped to the bins; computed in long double (binary128 and MP ratios are converted first;
// an MP ratio below the long-double range converts to 0 and lands in the last bin).
inline int ratio_bin(long double r){
    if(!(r>0))return RATIO_BINS-1;
    long double e=-std::floor(log10l(r));
    if(e<0)return 0;
    if(e>RATIO_BINS-2)return RATIO_BINS-1;
    return int(e);
}
#ifdef C8_TIER_TIMERS
#define C8_DIAGNOSTIC_KIND "tier_timers"
#define C8_DIAG_BEGIN() (thread_diagnostics().last=std::chrono::steady_clock::now())
#define C8_DIAG_TIER(level) do{auto&d_=thread_diagnostics();auto n_=std::chrono::steady_clock::now(); \
    d_.seconds[level]+=std::chrono::duration<double>(n_-d_.last).count();d_.calls[level]++;d_.last=n_;}while(0)
#define C8_DIAG_LD_FAIL(ratio) ((void)0)
#define C8_DIAG_QUAD(pair) ((void)0)
#define C8_DIAG_MP(pair) ((void)0)
#define C8_MP_NEED_ERROR false
#else
#define C8_DIAGNOSTIC_KIND "ratio_histogram"
#define C8_DIAG_BEGIN() ((void)0)
#define C8_DIAG_TIER(level) ((void)0)
#define C8_DIAG_LD_FAIL(ratio) (thread_diagnostics().ld_fail[ratio_bin(ratio)]++)
#define C8_DIAG_QUAD(pair) (thread_diagnostics().quad[ratio_bin((long double)(absolute((pair).first)/((pair).second+Q(1e-4900L))))]++)
#define C8_DIAG_MP(pair) (thread_diagnostics().mp[ratio_bin(MP(absolute((pair).first)/((pair).second+MP("1e-4900"))).convert_to<long double>())]++)
#define C8_MP_NEED_ERROR true
#endif
// The worker's JSON block (printed after "max_rss_kb").
inline void diagnostics_json(std::ostream&f,const Diagnostics&d){
#ifdef C8_TIER_TIMERS
    static const char*names[NTIERS]={"first_pass","quad","mp"};
    f<<",\"tier_timers\":{\"clock\":\"steady_clock\"";
    for(int k=0;k<NTIERS;++k)f<<",\""<<names[k]<<"_seconds\":"<<d.seconds[k]<<",\""<<names[k]<<"_calls\":"<<d.calls[k];
    f<<"}";
#else
    auto hist=[&](const char*name,const unsigned long long*h){
        f<<",\""<<name<<"\":{";bool first=true;
        for(int b=0;b<RATIO_BINS;++b)if(h[b]){if(!first)f<<',';first=false;f<<"\""<<(b==RATIO_BINS-1?std::string("zero_or_below"):std::to_string(-b))<<"\":"<<h[b];}
        f<<"}";};
    f<<",\"ratio_histogram\":{\"bins\":\"floor(log10(|v|/err)); zero_or_below = 0 or < 1e-400\"";
    hist("ld_fail",d.ld_fail);hist("quad",d.quad);hist("mp",d.mp);
    f<<"}";
#endif
}
