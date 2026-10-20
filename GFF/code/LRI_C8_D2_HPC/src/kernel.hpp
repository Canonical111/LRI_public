#pragma once
// Same finite-MOM kernels as reference/code/kernel.hpp, specialized for d=2.
// Ordered-prefix sharing preserves each polynomial's original addition order.
// C8(2) (PLAN.md component C): the arithmetic is C7(2)'s (a55958f) unchanged; only the array sizes come from the
// constants below, the GMP macro is C8_USE_GMP, and the diagnostic builds add empty-by-default hooks in evaluate().
// Stage 4b R3a: calculate_shared<Q> computes its binary128 +, - and * with src/quadfast.hpp's inline fast paths, which
// give libgcc's results bit for bit, in the same order; every value is unchanged.
// Stage 4c (PLAN D1, A-FLAG-1): hook points for the opt-in numerics profiles (src/numerics/, built only by `make gmp
// NUMERICS=<p>`). Without C8_NUMERICS every hook expands to exactly the tokens of the exact path, so the default
// preprocessed program and executables are unchanged (A-RPL-8); see "Opt-in numerics hooks" below.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <functional>
#include <iomanip>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>
#include <quadmath.h>
#include <boost/multiprecision/cpp_dec_float.hpp>
#ifdef C8_USE_GMP
#include <boost/multiprecision/gmp.hpp>
#endif
#ifdef __FAST_MATH__
#error "Fast-math is incompatible with the numerical contract"
#endif
#include "quadfast.hpp"
using ld = long double;
using Q = __float128;
#ifdef C8_USE_GMP
// Explicit opt-in backend change: 350 decimal digits, above the reference
// cpp_dec_float<300>'s 328-digit storage+guard precision on the test build.
using MP = boost::multiprecision::number<boost::multiprecision::gmp_float<350>>;
static constexpr const char* mp_backend="gmp350";
#else
using MP = boost::multiprecision::number<boost::multiprecision::cpp_dec_float<300>>;
static constexpr const char* mp_backend="decimal300";
#endif
static_assert(std::numeric_limits<ld>::digits >= 64, "long double must retain >=64 significant binary bits");
static_assert(std::numeric_limits<ld>::max_exponent >= 16384, "extended exponent range required");
// C8(2) limits (PLAN.md component C), replacing the literal C7(2) sizes. Order 7 replays C7(2) (loops 2-7,
// K = 7-L); order 8 is production (loops 3-8 plus the L=2 control, K = 8-L). The larger arrays only add storage.
constexpr int LMAX=8;                         // loops (n = 9 vertices)
constexpr int ORDER_MIN=7, ORDER_MAX=8;       // 7: replay of C7(2); 8: production
constexpr int EMAX=2*LMAX;                    // 16 propagators
constexpr int KMAX=ORDER_MAX-2;               // 6: highest regulator jet order (the L=2 control at order 8)
constexpr int NLOGS=KMAX+1;                   // gamma log values per row at order 8: logs[0..6]
constexpr int NVALUES=2*NLOGS;                // values per output row (b and c jets): 14
constexpr int DIMMAX=4*LMAX-1;                // Sobol coordinates for layouts 0/1: 31
constexpr int MAXMASKS=16384, MAXTERMS=10000; // header limits; L8 maxima 4,032 and 280
static_assert(EMAX<=31, "subset masks are 32-bit and 1<<E must fit an int");
static_assert(DIMMAX>=2*EMAX-1, "layouts 0/1 read u[0..2E-2]");
static_assert(NLOGS==KMAX+1 && NVALUES==2*(KMAX+1), "jet widths");
static_assert(EMAX==2*LMAX && DIMMAX==4*LMAX-1 && ORDER_MAX==LMAX && ORDER_MIN==ORDER_MAX-1, "one order fixes every size");
struct Term { std::vector<int> ids, co; int denominator=0, numerator=0; };
struct Segment { int parent=0, begin=0, end=0; };
struct Graph {
    int id=0,E=0,L=0; ld wa=0,wb=0,Z=0;
    std::vector<unsigned> masks;
    std::vector<Term> terms;
    std::vector<ld> alpha,dp;
    std::vector<std::pair<int,int>> products;
    std::vector<int> mon_ids;
    std::vector<Segment> segments;
    std::vector<int> addends;
    std::vector<std::vector<std::pair<int,int>>> numerators;
    std::vector<ld> choice_total;
};
struct Scratch {
    std::array<ld,EMAX> x{}, xs{},lx{},lt{};
    std::array<int,EMAX> order{};
    std::vector<ld> products, sums, numerator,abs_numerator;
    ld S=0;
    void resize(const Graph&g) {
        products.resize(g.products.size()+1); sums.resize(g.segments.size()+1);
        numerator.resize(g.numerators.size()); abs_numerator.resize(g.numerators.size());
    }
};
static_assert(std::tuple_size<decltype(Scratch::x)>::value==EMAX && std::tuple_size<decltype(Scratch::order)>::value==EMAX,
              "scratch arrays hold every propagator");
struct Eval {ld y; int level;};
// Diagnostic builds (PLAN component C): `make profile` (-DC8_TIER_TIMERS, per-tier timers) and `make ratiohist`
// (-DC8_RATIO_HISTOGRAM, log10(|v|/err) histograms) define these hooks in diagnostics.hpp; `plan` refuses such
// executables (--describe reports "diagnostic":true). In every other build the hooks are empty, so evaluate() is
// C7(2)'s, and the MP tier keeps C7(2)'s calculate_shared<MP,false>.
#if defined(C8_TIER_TIMERS) || defined(C8_RATIO_HISTOGRAM)
#include "diagnostics.hpp"
#else
#define C8_DIAG_BEGIN() ((void)0)
#define C8_DIAG_TIER(level) ((void)0)
#define C8_DIAG_LD_FAIL(ratio) ((void)0)
#define C8_DIAG_QUAD(pair) ((void)0)
#define C8_DIAG_MP(pair) ((void)0)
#define C8_MP_NEED_ERROR false
#endif
template<class T> T exponential(T x) { using std::exp; return exp(x); }
template<> inline Q exponential(Q x) { return expq(x); }
template<class T> T absolute(T x) { return x<0 ? -x : x; }
// Opt-in numerics hooks (Stage 4c; PLAN D1, A-FLAG-1). A profile build (`make gmp NUMERICS=<p>[,<p>...]`) defines
// C8_NUMERICS and C8_NUMERICS_<P>, and src/numerics/numerics.hpp is included twice: stage 1 here (hook macros and
// helpers that need only the code above) and stage 2 after calculate_shared (the promotion tiers, nx::promote). The
// default build never includes it, and the hooks below then expand to the exact path's own tokens:
//   C8_NX_SHARED_BEGIN(T)  a statement at the top of calculate_shared<T> (after the scratch set-up); default nothing.
//   C8_NX_XS_Q(e)          xs_j of the binary128 tier, given the exact expression e; default e.
//   C8_NX_XS_MP(e)         xs_j of every other calculate_shared type (the MP tiers); default e.
//   C8_NX_DESCRIBE(os)     a statement that appends profile fields to --describe and to the native JSON; default nothing.
//   evaluate()             promotes a point that fails the 1e-9 test through nx::promote() (numerics.hpp) in a profile
//                          build, and through the exact binary128 -> MP code otherwise.
// The macros see calculate_shared's locals (g, logx, shift, s, S, j); they are the profiles' contract with this file.
// Z3 (Stage-6 fix round 3, S6A3-03): the C8_NX_* macros belong to src/numerics/ alone, which defines them only below,
// inside a profile build. One defined before this point came from outside (-D, -include, -imacros, -Wp, a response
// file, a header included first) and could change the kernel while --describe still says "exact": refused. The list
// is every C8_NX_* name that src/ or the precision tools consult (tests/test_native_guards.py keeps it complete).
#if defined(C8_NX_STAGE) || defined(C8_NX_SHARED_BEGIN) || defined(C8_NX_XS_Q) || defined(C8_NX_XS_MP) || defined(C8_NX_DESCRIBE) \
    || defined(C8_NX_PARAMS_DD) || defined(C8_NX_PARAMS_MP256) || defined(C8_NX_PARAMS_EXP1) || defined(C8_NX_F1_CHECKS) \
    || defined(C8_NX_F1_CHECKS_DD) || defined(C8_NX_F1_CHECKS_MP256) || defined(C8_NX_F1_CHECKS_EXP1) \
    || defined(C8_NX_MP256_DEVELOPMENT) || defined(C8_NX_MP256_STR) || defined(C8_NX_MP256_STR2) || defined(C8_NX_EXP1_DEVELOPMENT)
#error "a C8_NX_* numerics hook is defined from outside src/numerics/ (e.g. -DC8_NX_...): the hooks are the opt-in profiles' alone (make gmp NUMERICS=<p>)"
#endif
#ifdef C8_NUMERICS
#define C8_NX_STAGE 1
#include "numerics/numerics.hpp"
#undef C8_NX_STAGE
#endif
#ifndef C8_NX_SHARED_BEGIN
#define C8_NX_SHARED_BEGIN(T)
#endif
#ifndef C8_NX_XS_Q
#define C8_NX_XS_Q(e) e
#endif
#ifndef C8_NX_XS_MP
#define C8_NX_XS_MP(e) e
#endif
#ifndef C8_NX_DESCRIBE
#define C8_NX_DESCRIBE(os)
#endif
inline void rates(Graph&g,ld scale) {
    int sz=1<<g.E;
    if(g.alpha.size()!=size_t(sz))throw std::runtime_error("rate count mismatch");
    for(int s=1;s<sz-1;++s)if(!(g.alpha[s]>0) || !std::isfinite(g.alpha[s]))throw std::runtime_error("nonpositive/nonfinite rate");
    for(auto&a:g.alpha)a*=scale;
    g.dp.assign(sz,0);g.choice_total.assign(sz,0);g.dp[0]=1;
    for(int s=1;s<sz;++s){ld sum=0;for(int j=0;j<g.E;++j)if(s>>j&1)sum+=g.dp[s^(1<<j)];
        g.choice_total[s]=sum; g.dp[s]=sum/(s==sz-1?1:g.alpha[s]);
        if(!std::isfinite(g.dp[s]))throw std::runtime_error("nonfinite importance normalization");}
    g.Z=g.dp.back();
}
inline void prepare(Graph&g) {
    std::vector<int> ids(1<<g.E,-1); ids[0]=0;
    std::function<int(unsigned)> make=[&](unsigned mask)->int {
        if(ids[mask]>=0)return ids[mask];int j=__builtin_ctz(mask);int p=make(mask^(1u<<j));
        g.products.emplace_back(p,j);return ids[mask]=int(g.products.size());};
    for(auto m:g.masks){if(m>=unsigned(1<<g.E)||__builtin_popcount(m)!=g.L)throw std::runtime_error("nonhomogeneous mask");g.mon_ids.push_back(make(m));}
    // Trie of ordered monomial sums, compressed at branch and terminal nodes.
    struct Node {int parent=-1,mon=-1,terminal=0;std::map<int,int> children;};
    std::vector<Node> tree(1);std::vector<int> ends;
    std::map<std::vector<int>,int> nums;
    for(auto&t:g.terms){int at=0;for(int m:t.ids){if(m<0||m>=int(g.masks.size()))throw std::runtime_error("bad monomial index");
        auto it=tree[at].children.find(m);if(it==tree[at].children.end()){int next=int(tree.size());tree[at].children[m]=next;tree.push_back({at,m,0,{}});at=next;}else at=it->second;}
        tree[at].terminal++;ends.push_back(at);
        auto it=nums.find(t.co);if(it==nums.end()){int k=int(nums.size());nums.emplace(t.co,k);t.numerator=k;g.numerators.emplace_back();for(int j=0;j<g.E;++j)if(t.co[j])g.numerators.back().emplace_back(j,t.co[j]);}else t.numerator=it->second;
    }
    std::vector<int> compressed(tree.size(),-1);compressed[0]=0;
    std::function<void(int)> visit=[&](int at){for(auto [mon,child]:tree[at].children){std::vector<int> run;int end=child;
        while(true){run.push_back(g.mon_ids[tree[end].mon]);if(tree[end].terminal||tree[end].children.size()!=1)break;end=tree[end].children.begin()->second;}
        int begin=int(g.addends.size());g.addends.insert(g.addends.end(),run.begin(),run.end());g.segments.push_back({compressed[at],begin,int(g.addends.size())});compressed[end]=int(g.segments.size());visit(end);}};
    visit(0);for(size_t i=0;i<g.terms.size();++i)g.terms[i].denominator=compressed[ends[i]];
}
// Z4 (Stage-6 fix round 3, S6A3-04): every extraction is checked before its value is used. A body that ends early or
// holds an unreadable token fails the stream; the loader then throws "truncated graph" at once (after the mask list,
// after each denominator size, monomial-id list and coefficient row, after the rate-table size and after the table),
// so no unassigned or stale size reaches a comparison or a resize. M, T and n start at 0. A valid file takes exactly
// the reads and values it took before; only these checks are added (tests/test_native_guards.py, tests/validate.py).
inline Graph load_graph(const std::string&path,ld scale) {
    std::ifstream f(path);std::string magic;Graph g;int M=0,T=0,n=0;
    f>>magic>>g.L>>g.id>>g.wa>>g.wb>>M>>T;
    // E = 2L propagators: the EMAX guard is tested on L, before 2L is formed.
    if(f&&magic=="C7D2GRAPH1"&&g.L>EMAX/2)throw std::runtime_error("graph has "+std::to_string(g.L)+" loops, i.e. more than EMAX="+std::to_string(EMAX)+" propagators (E=2L): "+path);
    if(!f||magic!="C7D2GRAPH1"||g.L<2||g.L>LMAX||M<1||T<1||M>MAXMASKS||T>MAXTERMS)throw std::runtime_error("invalid graph header: "+path);
    g.E=2*g.L;
    g.masks.resize(M);for(auto&m:g.masks)f>>m;
    if(!f)throw std::runtime_error("truncated graph: "+path);
    for(int k=0;k<T;++k){Term t;f>>n;if(!f)throw std::runtime_error("truncated graph: "+path);if(n<1||n>M)throw std::runtime_error("bad denominator size");t.ids.resize(n);for(auto&i:t.ids)f>>i;if(!f)throw std::runtime_error("truncated graph: "+path);t.co.resize(g.E);for(auto&c:t.co)f>>c;if(!f)throw std::runtime_error("truncated graph: "+path);g.terms.push_back(std::move(t));}
    f>>n;if(!f)throw std::runtime_error("truncated graph: "+path);if(n!=(1<<g.E))throw std::runtime_error("invalid rate table");g.alpha.resize(n);for(auto&a:g.alpha)f>>a;
    if(!f)throw std::runtime_error("truncated graph: "+path);std::string extra;if(f>>extra)throw std::runtime_error("extra graph tokens");rates(g,scale);prepare(g);return g;
}
// The promotion paths use exactly the reference log-sum/exponential formula.
template<class T> std::pair<T,T> calculate_reference(const Graph&g,const ld*logx,ld shift) {
    std::vector<T>x(g.E),xs(g.E),prod(g.products.size()+1);T S=0;prod[0]=1;
    for(int j=0;j<g.E;++j){x[j]=exponential(T(logx[j]));S+=x[j];xs[j]=shift==0?x[j]:exponential(T(logx[j])-T(shift)/g.L);}
    for(size_t j=0;j<g.products.size();++j){auto o=g.products[j];prod[j+1]=prod[o.first]*xs[o.second];}
    T val=0,err=0;for(const auto&t:g.terms){T U=0,n=0,na=0;for(int i:t.ids)U+=prod[g.mon_ids[i]];for(int j=0;j<g.E;++j){T p=T(t.co[j])*x[j];n+=p;na+=absolute(p);}val+=n/U;err+=na/U;}return {val/S,err/S};
}
inline std::pair<ld,ld> calculate_products(const Graph&g,const ld*logx,ld shift,Scratch&s) {
    s.S=0;s.products[0]=1;s.sums[0]=0;
    for(int j=0;j<g.E;++j){s.x[j]=expl(logx[j]);s.S+=s.x[j];s.xs[j]=shift==0?s.x[j]:expl(logx[j]-shift/g.L);}
    for(size_t j=0;j<g.products.size();++j){auto o=g.products[j];s.products[j+1]=s.products[o.first]*s.xs[o.second];}
#ifndef NO_SUM_SHARING
    for(size_t j=0;j<g.segments.size();++j){auto a=g.segments[j];ld v=s.sums[a.parent];for(int k=a.begin;k<a.end;++k)v+=s.products[g.addends[k]];s.sums[j+1]=v;}
    for(size_t j=0;j<g.numerators.size();++j){ld n=0,a=0;for(auto [i,c]:g.numerators[j]){ld p=ld(c)*s.x[i];n+=p;a+=absolute(p);}s.numerator[j]=n;s.abs_numerator[j]=a;}
    ld val=0,err=0;for(const auto&t:g.terms){ld U=s.sums[t.denominator];val+=s.numerator[t.numerator]/U;err+=s.abs_numerator[t.numerator]/U;}
#else
    ld val=0,err=0;for(const auto&t:g.terms){ld U=0,n=0,na=0;for(int i:t.ids)U+=s.products[g.mon_ids[i]];for(int j=0;j<g.E;++j)if(t.co[j]){ld p=ld(t.co[j])*s.x[j];n+=p;na+=absolute(p);}val+=n/U;err+=na/U;}
#endif
    return {val/s.S,err/s.S};
}

// Shared fallbacks: identical per-polynomial addition order and precision.
// Persistent per-thread buffers avoid rebuilding hundreds-digit objects at
// every promotion. The final MP error estimate was unused by the reference.
template<class T> struct PromotedScratch {
    std::array<T,EMAX> x{},xs{};
    std::vector<T> products,sums,numerator,abs_numerator;
    void resize(const Graph&g) {
        products.resize(g.products.size()+1);sums.resize(g.segments.size()+1);
        numerator.resize(g.numerators.size());abs_numerator.resize(g.numerators.size());
    }
};
// R3a (Stage 4b, PLAN "Performance plan"): in the binary128 tier (T = Q), every +, - and * goes through
// src/quadfast.hpp's inline fast paths, which give libgcc's __addtf3/__subtf3/__multf3 results bit for bit
// (tests/quad_differential.cpp), in the same order; division, conversions, comparisons and expq stay
// libgcc/libquadmath. The dispatch on T is per statement with if constexpr, so every other T (the MP backends)
// instantiates exactly the original statements with its own operators and compiles to the same code as before.
template<class T,bool NeedError=true>
std::pair<T,T> calculate_shared(const Graph&g,const ld*logx,ld shift) {
    constexpr bool quad=std::is_same<T,Q>::value;
    static thread_local PromotedScratch<T> scratch;
    auto&s=scratch;s.resize(g);T S=0;s.products[0]=1;s.sums[0]=0;C8_NX_SHARED_BEGIN(T)
    for(int j=0;j<g.E;++j){s.x[j]=exponential(T(logx[j]));
        if constexpr(quad){S=quadfast::add(S,s.x[j]);s.xs[j]=shift==0?s.x[j]:C8_NX_XS_Q(exponential(quadfast::sub(T(logx[j]),T(shift)/g.L)));}
        else{S+=s.x[j];s.xs[j]=shift==0?s.x[j]:C8_NX_XS_MP(exponential(T(T(logx[j])-T(shift)/g.L)));}}
    for(size_t j=0;j<g.products.size();++j){auto o=g.products[j];
        if constexpr(quad)s.products[j+1]=quadfast::mul(s.products[o.first],s.xs[o.second]);
        else s.products[j+1]=s.products[o.first]*s.xs[o.second];}
    for(size_t j=0;j<g.segments.size();++j){auto a=g.segments[j];T v=s.sums[a.parent];
        for(int k=a.begin;k<a.end;++k){if constexpr(quad)v=quadfast::add(v,s.products[g.addends[k]]);else v+=s.products[g.addends[k]];}
        s.sums[j+1]=v;}
    for(size_t j=0;j<g.numerators.size();++j){T n=0,ab=0;
        for(auto [i,c]:g.numerators[j]){
            if constexpr(quad){T p=quadfast::mul(T(c),s.x[i]);n=quadfast::add(n,p);if constexpr(NeedError)ab=quadfast::add(ab,absolute(p));}
            else{T p=T(c)*s.x[i];n+=p;if constexpr(NeedError)ab+=absolute(p);}}
        s.numerator[j]=n;if constexpr(NeedError)s.abs_numerator[j]=ab;}
    T val=0,err=0;
    for(const auto&t:g.terms){const T&U=s.sums[t.denominator];
        if constexpr(quad){val=quadfast::add(val,s.numerator[t.numerator]/U);if constexpr(NeedError)err=quadfast::add(err,s.abs_numerator[t.numerator]/U);}
        else{val+=s.numerator[t.numerator]/U;if constexpr(NeedError)err+=s.abs_numerator[t.numerator]/U;}}
    return {val/S,NeedError?err/S:T(0)};
}
#ifdef C8_NUMERICS
#define C8_NX_STAGE 2
#include "numerics/numerics.hpp"
#undef C8_NX_STAGE
#endif
inline Eval evaluate(const Graph&g,const ld*lx,ld factor,Scratch&s) {
    ld shift=0;bool direct=true;for(int j=0;j<g.E;++j)if(lx[j]<-600||lx[j]>0)direct=false;
    if(!direct){shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld v=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;v+=lx[j];}shift=std::max(shift,v);}}
    bool moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
    C8_DIAG_BEGIN();
    auto v=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);
    if(!moderate){s.S=0;for(int j=0;j<g.E;++j)s.S+=expl(lx[j]);}
    ld ratio=absolute(v.first)/(v.second+1e-4900L);int lev=0;ld f=v.first;C8_DIAG_TIER(0);
    if(ratio<1e-9L){C8_DIAG_LD_FAIL(ratio);
#ifdef C8_NUMERICS
        nx::promote(g,lx,shift,f,lev);}
#else
        auto q=calculate_shared<Q>(g,lx,shift);lev=1;f=ld(q.first);C8_DIAG_TIER(1);C8_DIAG_QUAD(q);
        if(absolute(q.first)<Q(1e-23L)*q.second){auto m=calculate_shared<MP,C8_MP_NEED_ERROR>(g,lx,shift);f=m.first.convert_to<ld>();lev=2;C8_DIAG_TIER(2);C8_DIAG_MP(m);}}
#endif
    ld y=f*expl(factor-shift)*g.Z;if(!std::isfinite(y))throw std::runtime_error("nonfinite integrand");return {y,lev};
}
inline std::array<ld,NLOGS> sample(const Graph&g,const ld*uu,int K,const std::array<ld,NLOGS>&logs,int&level,int layout,Scratch&s) {
    int E=g.E,S=(1<<E)-1;ld fac=0,ou=uu[0];
    for(int pos=0;pos<E;++pos){ld u=(layout==2?ou:uu[layout==0?2*pos:E-1+pos])*g.choice_total[S];int pick=-1;
        for(int j=0;j<E;++j)if(S>>j&1){u-=g.dp[S^(1<<j)];if(u<=0){pick=j;break;}}
        if(pick<0)pick=31-__builtin_clz(S);
        if(layout==2){ld pr=g.dp[S^(1<<pick)];ou=(u+pr)/pr;ou=std::max(0.L,std::min(nextafterl(1.L,0.L),ou));}
        s.order[pos]=pick;S^=1<<pick;
        if(S){int ix=layout==0?2*pos+1:(layout==2?pos+1:pos);ld l=logl(uu[ix])/g.alpha[S];s.lt[pos]=l;fac+=(__builtin_popcount(unsigned(S))/2.0L-g.alpha[S])*l;}}
    ld cur=0;for(int j=0;j<E;++j){s.lx[s.order[j]]=cur;if(j<E-1)cur+=s.lt[j];}
    auto v=evaluate(g,s.lx.data(),fac,s);level=v.level;std::array<ld,NLOGS>out{};out[0]=1;
    // At the top loop L = order (K = 0) the unused logarithm and entire regulator recurrence disappear.
    if(K){ld sumlog=0;for(int j=0;j<E;++j)sumlog+=s.lx[j];ld z=sumlog/4-g.L/2.L*logl(s.S);
        for(int n=1;n<=K;++n){ld a=0;for(int j=1;j<=n;++j)a+=j*(logs[j]+(j==1?z:0))*out[n-j];out[n]=a/n;}}
    for(int j=0;j<=K;++j)out[j]*=v.y;return out;
}
