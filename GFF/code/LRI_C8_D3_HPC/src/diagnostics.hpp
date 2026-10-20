#pragma once
// Diagnostic hooks of kernel.hpp's evaluate() (PLAN.md C.5; the d-independent design of C62d's
// LRI_C8_D2_HPC src/diagnostics.hpp, re-implemented here). Included only under -DC8_TIER_TIMERS (`make profile` ->
// bin/c8d3_gmp_prof) or -DC8_RATIO_HISTOGRAM (`make ratiohist` -> bin/c8d3_gmp_ratiohist). `plan` never accepts these
// executables: their --describe reports "diagnostic":true. The hooks only read values the default code computes anyway;
// they never change an operand, so a diagnostic build writes the same rows as the default build.
//
// Tier timers: thread-local steady-clock seconds and calls per tier. Tier 0 is the first pass (long double:
// calculate_products, or calculate_reference<ld> at non-moderate points, plus the ratio test), tier 1 the binary128
// evaluation, tier 2 the MP evaluation with its conversion to long double. The worker sums the threads' totals. Stage 4a
// adds the same seconds and calls per graph id ("per_graph"; evaluate()'s `g` at the hook), so a stratified fixture
// block can be re-weighted to its population (tools/perf_profile.py). The in-tier sub-timers of C.5 are not built:
// Expanse allows perf, whose symbol shares and source lines (P1) resolve the tiers' functions and loops instead, and
// instrumented copies of the tier loops would change src/kernel.hpp, i.e. the Stage-3 baseline the profiles measure.
//
// Ratio histograms: counts of floor(log10(|v|/err)) at the two promotion tests, bin b holding the ratios in
// [10^-(b+1), 10^-b) for b = 0..RATIO_BINS-2 (ratios >= 1 are counted in bin 0) and bin RATIO_BINS-1 holding ratio 0 and
// every ratio below 10^-(RATIO_BINS-1):
//   ld_fail : the long-double ratio of every point that fails the 1e-9 test (and is promoted to binary128);
//   quad    : |q|/err_q of every binary128 evaluation (the 1e-23 test fails from bin 23 on);
//   mp      : |m|/err_m of every MP evaluation. This build accumulates the MP error estimate at every MP point
//             (calculate_shared<MP,true>): its value is computed by the same operation sequence as <MP,false>.
#include <chrono>
#include <cmath>
#include <map>
#include <ostream>
#include <string>
#if defined(C8_TIER_TIMERS) && defined(C8_RATIO_HISTOGRAM)
#error "build one diagnostic at a time (make profile or make ratiohist)"
#endif
constexpr int NTIERS=3;
constexpr int RATIO_BINS=402;
struct GraphTiers {double seconds[NTIERS]{};unsigned long long calls[NTIERS]{};};
struct Diagnostics {
    double seconds[NTIERS]{};
    unsigned long long calls[NTIERS]{};
    unsigned long long ld_fail[RATIO_BINS]{},quad[RATIO_BINS]{},mp[RATIO_BINS]{};
    std::map<int,GraphTiers> per_graph;   // tier timers only: the same seconds and calls per graph id
    std::chrono::steady_clock::time_point last{};
    void add(const Diagnostics&o){
        for(int k=0;k<NTIERS;++k){seconds[k]+=o.seconds[k];calls[k]+=o.calls[k];}
        for(int b=0;b<RATIO_BINS;++b){ld_fail[b]+=o.ld_fail[b];quad[b]+=o.quad[b];mp[b]+=o.mp[b];}
        for(const auto&kv:o.per_graph){auto&t=per_graph[kv.first];for(int k=0;k<NTIERS;++k){t.seconds[k]+=kv.second.seconds[k];t.calls[k]+=kv.second.calls[k];}}
    }
};
inline Diagnostics& thread_diagnostics(){static thread_local Diagnostics d;return d;}
inline void diagnostics_reset(){thread_diagnostics()=Diagnostics{};}
inline int ratio_bin(long double r){
    if(!(r>0))return RATIO_BINS-1;
    long double e=-std::floor(log10l(r));
    if(e<1)return 0;
    if(e>RATIO_BINS-1)return RATIO_BINS-1;
    return int(e)-1;
}
#ifdef C8_TIER_TIMERS
#define C8_DIAGNOSTIC_KIND "tier_timers"
#define C8_DIAG_BEGIN() (thread_diagnostics().last=std::chrono::steady_clock::now())
// The hook sits in evaluate(), whose graph parameter is `g`.
#define C8_DIAG_TIER(level) do{auto&d_=thread_diagnostics();auto n_=std::chrono::steady_clock::now(); \
    const double s_=std::chrono::duration<double>(n_-d_.last).count();d_.seconds[level]+=s_;d_.calls[level]++; \
    auto&p_=d_.per_graph[g.id];p_.seconds[level]+=s_;p_.calls[level]++;d_.last=n_;}while(0)
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
// The worker's JSON block (printed after the top-level identity fields).
inline void diagnostics_json(std::ostream&f,const Diagnostics&d){
#ifdef C8_TIER_TIMERS
    static const char*names[NTIERS]={"first_pass","quad","mp"};
    f<<",\"tier_timers\":{\"clock\":\"steady_clock\"";
    for(int k=0;k<NTIERS;++k)f<<",\""<<names[k]<<"_seconds\":"<<d.seconds[k]<<",\""<<names[k]<<"_calls\":"<<d.calls[k];
    f<<",\"per_graph_fields\":[\"first_pass_seconds\",\"quad_seconds\",\"mp_seconds\",\"first_pass_calls\",\"quad_calls\",\"mp_calls\"],\"per_graph\":{";
    bool first=true;
    for(const auto&kv:d.per_graph){if(!first)f<<',';first=false;f<<'"'<<kv.first<<"\":[";
        for(int k=0;k<NTIERS;++k)f<<kv.second.seconds[k]<<',';
        for(int k=0;k<NTIERS;++k)f<<kv.second.calls[k]<<(k+1<NTIERS?",":"");
        f<<']';}
    f<<"}}";
#else
    auto hist=[&](const char*name,const unsigned long long*h){
        f<<",\""<<name<<"\":{";bool first=true;
        for(int b=0;b<RATIO_BINS;++b)if(h[b]){if(!first)f<<',';first=false;
            f<<"\""<<(b==RATIO_BINS-1?std::string("zero_or_below"):std::to_string(-(b+1)))<<"\":"<<h[b];}
        f<<"}";};
    f<<",\"ratio_histogram\":{\"bins\":\"key -k counts ratios in [1e-k, 1e-(k-1)); ratios >= 1 under -1; zero_or_below = 0 or < 1e-401\"";
    hist("ld_fail",d.ld_fail);hist("quad",d.quad);hist("mp",d.mp);
    f<<"}";
#endif
}
