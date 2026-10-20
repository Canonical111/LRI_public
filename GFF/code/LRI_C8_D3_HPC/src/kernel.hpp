#pragma once
// Same finite-MOM kernels as reference/code/kernel.hpp, specialized for d=3.
// Ordered-prefix sharing preserves each polynomial's original addition order.
// C8(3) (PLAN.md component C, Stage 3a). The arithmetic is C7(3)'s (a6ce987) on the default path (C.9): the tier code,
// the thresholds 1e-9 and 1e-23, the 1e-4900L floor, rates(), prepare() and sample()'s arithmetic are unchanged.
// Changed: every array size comes from the constants below (C.1); load_graph is a checked reader whose every error
// names its file (C.2, round-1 R11); calculate_shared carries C7(2)'s A-L18 hunk (F4); evaluate() records the class-B
// per-point facts of C.3/C.4 in the scratch (direct, moderate, the MP self-check), which no value depends on.
// Stage 4b #4 (= C62d's R3a, H5): calculate_shared<Q> computes its binary128 +, - and * with src/quadfast.hpp's inline
// fast paths, which give libgcc's results bit for bit, in the same order; every value is unchanged.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <functional>
#include <iomanip>
#include <istream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>
#include <quadmath.h>
#include <boost/multiprecision/cpp_dec_float.hpp>
#ifdef C7_USE_GMP
#include <boost/multiprecision/gmp.hpp>
#endif
#ifdef __FAST_MATH__
#error "Fast-math is incompatible with the numerical contract"
#endif
#include "quadfast.hpp"
// Test-only (C.7 coverage self-test): it removes both guards of a term's monomial index (the reader's and prepare()'s)
// and may only enter the sanitizer self-test binary bin/selftest/c8d3_inspect_unguarded_san.
#if defined(C8_TEST_UNGUARDED_INDEX) && !defined(_GLIBCXX_ASSERTIONS)
#error "C8_TEST_UNGUARDED_INDEX is for bin/selftest/c8d3_inspect_unguarded_san only (it needs _GLIBCXX_ASSERTIONS)"
#endif
using ld = long double;
using Q = __float128;
#ifdef C7_USE_GMP
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
constexpr int SpatialD = 3;
// C8(3) limits (PLAN.md C.1), replacing every literal C7(3) size. Order 7 replays C7(3) (loops 2-7, K = 7-L,
// gamma_d3_7.txt); order 8 is production (loops 3-8 plus the L=2 control, K = 8-L, gamma_d3_8.txt).
constexpr int LMAX=8;                         // loops (n = 9 vertices)
constexpr int ORDER_MIN=7, ORDER_MAX=8;       // 7: replay of C7(3); 8: production
constexpr int EMAX=2*LMAX;                    // 16 propagators
constexpr int KMAX=ORDER_MAX-2;               // 6: highest regulator jet (the L=2 control at order 8)
constexpr int NLOGS=KMAX+1;                   // gamma log values per row at order 8: logs[0..6]
constexpr int NVALUES=2*NLOGS;                // values per output row (b and c jets): 14
constexpr int DIMMAX=4*LMAX-1;                // Sobol coordinates for layouts 0/1: 31
constexpr int MAXMASKS=16384, MAXTERMS=10000; // header limits; L8 maxima 4,032 and 280
constexpr int TAILK=16;                       // largest |t| values kept per row
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
    // Class-B per-point facts (C.3, C.4): set by evaluate(), read by the worker after sample(). No value depends on
    // them. mp_check is the caller's request for this point; mp_checked says whether the MP tier ran with its error
    // estimate, mp_log10 is then log10(|v|/err) at the MP tier (-inf for an exact zero).
    bool direct=true, moderate=true, mp_check=false, mp_checked=false;
    ld mp_log10=0;
    void resize(const Graph&g) {
        products.resize(g.products.size()+1); sums.resize(g.segments.size()+1);
        numerator.resize(g.numerators.size()); abs_numerator.resize(g.numerators.size());
    }
};
static_assert(std::tuple_size<decltype(Scratch::x)>::value==EMAX && std::tuple_size<decltype(Scratch::order)>::value==EMAX,
              "scratch arrays hold every propagator");
struct Eval {ld y; int level;};
// Diagnostic builds (C.5): `make profile` (-DC8_TIER_TIMERS) and `make ratiohist` (-DC8_RATIO_HISTOGRAM) define these
// hooks in diagnostics.hpp; `plan` refuses such executables (--describe says "diagnostic":true). In every other
// build the hooks are empty.
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
template<class T> T square_root(T x) { using std::sqrt; return sqrt(x); }
template<> inline Q square_root(Q x) { return sqrtq(x); }
template<class T> T absolute(T x) { return x<0 ? -x : x; }
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
    for(auto&t:g.terms){int at=0;for(int m:t.ids){
#ifndef C8_TEST_UNGUARDED_INDEX
        if(m<0||m>=int(g.masks.size()))throw std::runtime_error("bad monomial index");
#endif
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
// The checked G-file reader (C.2, round-1 R11). Every extraction goes through GraphReader::get, which fails with
// "<path>: truncated or malformed <field> (end of file|malformed)"; every check comes before any resize or index use:
// magic C7D3GRAPH1; L in [2,LMAX] (so E = 2L <= EMAX); id >= 0; wa and wb finite; M in [1,MAXMASKS] and T in
// [1,MAXTERMS]; each mask < 2^E with popcount L as it is read; per term a length n in [1,M] before the term is sized,
// each index in [0,M) as it is read, exactly E coefficients; a rate count equal to 2^E before the table is sized,
// then 2^E values and nothing after them. rates() and prepare() run inside a try that prefixes their message with the
// path. The extractions read the same types in the same order as a6ce987's reader, so every valid file loads to the
// same values (A-RPL-1/2). The worker, c8d3_inspect and tests/point_checks.cpp all load through it.
// A token as it may appear in a message: printable ASCII, other bytes as \xHH, at most n bytes shown.
inline std::string printable(const std::string&t,size_t n=40){
    std::string o;for(size_t i=0;i<t.size();++i){if(i>=n){o+="...";break;}unsigned char c=t[i];
        if(c>=32&&c<127)o+=char(c);else{const char*hex="0123456789abcdef";o+="\\x";o+=hex[c>>4];o+=hex[c&15];}}
    return o;
}
struct GraphReader {
    std::istream&f;const std::string&path;
    [[noreturn]] void fail(const std::string&what)const{throw std::runtime_error(path+": "+what);}
    // The field's name is formed only on failure: "<a>[ <i>][ <b>][ <j>]", e.g. "term 3 index 5".
    static std::string name(const char*a,long i,const char*b,long j){
        std::string s=a;if(i>=0)s+=" "+std::to_string(i);if(b)s+=std::string(" ")+b;if(j>=0)s+=" "+std::to_string(j);return s;}
    template<class T> void get(T&x,const char*a,long i=-1,const char*b=nullptr,long j=-1){
        if(!(f>>x))fail("truncated or malformed "+name(a,i,b,j)+(f.eof()?" (end of file)":" (malformed)"));}
};
inline Graph read_graph(std::istream&f,const std::string&path,ld scale) {
    GraphReader r{f,path};Graph g;std::string magic;int L=0,id=0,M=0,T=0;ld wa=0,wb=0;
    r.get(magic,"magic");
    if(magic!="C7D3GRAPH1")r.fail("magic '"+printable(magic)+"' is not C7D3GRAPH1");
    r.get(L,"L");
    if(L<2||L>LMAX)r.fail("L "+std::to_string(L)+" out of range [2,"+std::to_string(LMAX)+"] (E = 2L propagators, EMAX = "+std::to_string(EMAX)+")");
    r.get(id,"id");if(id<0)r.fail("id "+std::to_string(id)+" out of range (a non-negative integer)");
    r.get(wa,"wa");if(!std::isfinite(wa))r.fail("wa is not finite");
    r.get(wb,"wb");if(!std::isfinite(wb))r.fail("wb is not finite");
    r.get(M,"M");if(M<1||M>MAXMASKS)r.fail("M "+std::to_string(M)+" out of range [1,"+std::to_string(MAXMASKS)+"]");
    r.get(T,"T");if(T<1||T>MAXTERMS)r.fail("T "+std::to_string(T)+" out of range [1,"+std::to_string(MAXTERMS)+"]");
    g.L=L;g.id=id;g.wa=wa;g.wb=wb;g.E=2*L;const int E=g.E;
    g.masks.resize(M);
    for(int k=0;k<M;++k){unsigned m=0;r.get(m,"mask",k);
        if(m>=(1u<<E))r.fail("mask "+std::to_string(k)+" "+std::to_string(m)+" out of range [0,"+std::to_string((1u<<E)-1)+"]");
        if(__builtin_popcount(m)!=L)r.fail("mask "+std::to_string(k)+" "+std::to_string(m)+" has popcount "+std::to_string(__builtin_popcount(m))+", expected L = "+std::to_string(L));
        g.masks[k]=m;}
    g.terms.reserve(T);
    for(int k=0;k<T;++k){Term t;int n=0;r.get(n,"term",k,"length");
        if(n<1||n>M)r.fail("term "+std::to_string(k)+" length "+std::to_string(n)+" out of range [1,"+std::to_string(M)+"]");
        t.ids.resize(n);
        for(int i=0;i<n;++i){int x=0;r.get(x,"term",k,"index",i);
#ifndef C8_TEST_UNGUARDED_INDEX
            if(x<0||x>=M)r.fail("term "+std::to_string(k)+" index "+std::to_string(i)+" "+std::to_string(x)+" out of range [0,"+std::to_string(M-1)+"]");
#endif
            t.ids[i]=x;}
        t.co.resize(E);for(int j=0;j<E;++j){int c=0;r.get(c,"term",k,"coefficient",j);t.co[j]=c;}
        g.terms.push_back(std::move(t));}
    int n=0;r.get(n,"rate count");
    if(n!=(1<<E))r.fail("rate count "+std::to_string(n)+" out of range (2^E = "+std::to_string(1<<E)+" required)");
    g.alpha.resize(n);for(int s=0;s<n;++s){ld a=0;r.get(a,"rate",s);g.alpha[s]=a;}
    std::string extra;if(f>>extra)r.fail("trailing data '"+printable(extra)+"' after the rate list");
    try{rates(g,scale);prepare(g);}catch(const std::exception&e){r.fail(e.what());}
    return g;
}
inline Graph load_graph(const std::string&path,ld scale) {
    std::ifstream f(path);if(!f)throw std::runtime_error(path+": cannot open the graph file");
    return read_graph(f,path,scale);
}
// The promotion paths use exactly the reference log-sum/exponential formula.
template<class T> std::pair<T,T> calculate_reference(const Graph&g,const ld*logx,ld shift) {
    std::vector<T>x(g.E),xs(g.E),prod(g.products.size()+1);T S=0;prod[0]=1;
    for(int j=0;j<g.E;++j){x[j]=exponential(T(logx[j]));S+=x[j];xs[j]=shift==0?x[j]:exponential(T(logx[j])-T(shift)/g.L);}
    for(size_t j=0;j<g.products.size();++j){auto o=g.products[j];prod[j+1]=prod[o.first]*xs[o.second];}
    T val=0,err=0;for(const auto&t:g.terms){T U=0,n=0,na=0;for(int i:t.ids)U+=prod[g.mon_ids[i]];for(int j=0;j<g.E;++j){T p=T(t.co[j])*x[j];n+=p;na+=absolute(p);}T den=U*square_root(U);val+=n/den;err+=na/den;}return {val/S,err/S};
}
inline std::pair<ld,ld> calculate_products(const Graph&g,const ld*logx,ld shift,Scratch&s) {
    s.S=0;s.products[0]=1;s.sums[0]=0;
    for(int j=0;j<g.E;++j){s.x[j]=expl(logx[j]);s.S+=s.x[j];s.xs[j]=shift==0?s.x[j]:expl(logx[j]-shift/g.L);}
    for(size_t j=0;j<g.products.size();++j){auto o=g.products[j];s.products[j+1]=s.products[o.first]*s.xs[o.second];}
#ifndef NO_SUM_SHARING
    for(size_t j=0;j<g.segments.size();++j){auto a=g.segments[j];ld v=s.sums[a.parent];for(int k=a.begin;k<a.end;++k)v+=s.products[g.addends[k]];s.sums[j+1]=v;}
    for(size_t j=0;j<g.numerators.size();++j){ld n=0,a=0;for(auto [i,c]:g.numerators[j]){ld p=ld(c)*s.x[i];n+=p;a+=absolute(p);}s.numerator[j]=n;s.abs_numerator[j]=a;}
    ld val=0,err=0;for(const auto&t:g.terms){ld U=s.sums[t.denominator];ld den=U*sqrtl(U);val+=s.numerator[t.numerator]/den;err+=s.abs_numerator[t.numerator]/den;}
#else
    ld val=0,err=0;for(const auto&t:g.terms){ld U=0,n=0,na=0;for(int i:t.ids)U+=s.products[g.mon_ids[i]];for(int j=0;j<g.E;++j)if(t.co[j]){ld p=ld(t.co[j])*s.x[j];n+=p;na+=absolute(p);}ld den=U*sqrtl(U);val+=n/den;err+=na/den;}
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
// Stage 4b #4 (= C62d's R3a, LRI_C8_D2_HPC@14d7347; PLAN "Performance plan", H5): in the binary128 tier (T = Q), every
// +, - and * goes through src/quadfast.hpp's inline fast paths, which give libgcc's __addtf3/__subtf3/__multf3 results
// bit for bit (tests/quad_differential.cpp), in the same order; division, the square root (d=3's U*sqrt(U)),
// conversions, comparisons and expq stay libgcc/libquadmath. The dispatch on T is per statement with if constexpr, so
// every other T (the MP backends) instantiates exactly the original statements with its own operators.
template<class T,bool NeedError=true>
std::pair<T,T> calculate_shared(const Graph&g,const ld*logx,ld shift) {
    constexpr bool quad=std::is_same<T,Q>::value;
    static thread_local PromotedScratch<T> scratch;
    auto&s=scratch;s.resize(g);T S=0;s.products[0]=1;s.sums[0]=0;
    for(int j=0;j<g.E;++j){s.x[j]=exponential(T(logx[j]));
        if constexpr(quad){S=quadfast::add(S,s.x[j]);s.xs[j]=shift==0?s.x[j]:exponential(T(quadfast::sub(T(logx[j]),T(shift)/g.L)));}
        else{S+=s.x[j];s.xs[j]=shift==0?s.x[j]:exponential(T(T(logx[j])-T(shift)/g.L));}}
    for(size_t j=0;j<g.products.size();++j){auto o=g.products[j];
        if constexpr(quad)s.products[j+1]=quadfast::mul(s.products[o.first],s.xs[o.second]);
        else s.products[j+1]=s.products[o.first]*s.xs[o.second];}
    for(size_t j=0;j<g.segments.size();++j){auto a=g.segments[j];T v=s.sums[a.parent];
        for(int k=a.begin;k<a.end;++k)if constexpr(quad)v=quadfast::add(v,s.products[g.addends[k]]);else v+=s.products[g.addends[k]];
        s.sums[j+1]=v;}
    for(size_t j=0;j<g.numerators.size();++j){T n=0,ab=0;
        for(auto [i,c]:g.numerators[j]){
            if constexpr(quad){T p=quadfast::mul(T(c),s.x[i]);n=quadfast::add(n,p);if constexpr(NeedError)ab=quadfast::add(ab,absolute(p));}
            else{T p=T(c)*s.x[i];n+=p;if constexpr(NeedError)ab+=absolute(p);}}
        s.numerator[j]=n;if constexpr(NeedError)s.abs_numerator[j]=ab;}
    T val=0,err=0;
    for(const auto&t:g.terms){const T&U=s.sums[t.denominator];
        if constexpr(quad){T den=quadfast::mul(U,square_root(U));val=quadfast::add(val,s.numerator[t.numerator]/den);
            if constexpr(NeedError)err=quadfast::add(err,s.abs_numerator[t.numerator]/den);}
        else{T den=U*square_root(U);val+=s.numerator[t.numerator]/den;if constexpr(NeedError)err+=s.abs_numerator[t.numerator]/den;}}
    return {val/S,NeedError?err/S:T(0)};
}
// The MP self-check (C.4): log10(|v|/err) of an MP evaluation made with its error estimate. Only reads m.
inline void mp_check_record(Scratch&s,const std::pair<MP,MP>&m) {
    s.mp_checked=true;
    if(!(m.second>0)){s.mp_log10=-std::numeric_limits<ld>::infinity();return;}
    ld r=MP(absolute(m.first)/m.second).convert_to<ld>();
    s.mp_log10=r>0?log10l(r):-std::numeric_limits<ld>::infinity();
}
// With s.mp_check the MP tier runs calculate_shared<MP,true>: the value is computed by the same operation sequence as
// calculate_shared<MP,false> (the error accumulations are separate variables), so values and counters are bitwise
// those of the unchecked call (A-KER-7).
inline Eval evaluate(const Graph&g,const ld*lx,ld factor,Scratch&s) {
    ld shift=0;bool direct=true;for(int j=0;j<g.E;++j)if(lx[j]<-600||lx[j]>0)direct=false;
    if(!direct){shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld v=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;v+=lx[j];}shift=std::max(shift,v);}}
    bool moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
    s.direct=direct;s.moderate=moderate;s.mp_checked=false;
    C8_DIAG_BEGIN();
    auto v=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);
    if(!moderate){s.S=0;for(int j=0;j<g.E;++j)s.S+=expl(lx[j]);}
    ld ratio=absolute(v.first)/(v.second+1e-4900L);int lev=0;ld f=v.first;C8_DIAG_TIER(0);
    if(ratio<1e-9L){C8_DIAG_LD_FAIL(ratio);auto q=calculate_shared<Q>(g,lx,shift);lev=1;f=ld(q.first);C8_DIAG_TIER(1);C8_DIAG_QUAD(q);
        if(absolute(q.first)<Q(1e-23L)*q.second){
            if(s.mp_check||C8_MP_NEED_ERROR){auto m=calculate_shared<MP,true>(g,lx,shift);f=m.first.convert_to<ld>();lev=2;C8_DIAG_TIER(2);C8_DIAG_MP(m);if(s.mp_check)mp_check_record(s,m);}
            else{auto m=calculate_shared<MP,false>(g,lx,shift);f=m.first.convert_to<ld>();lev=2;C8_DIAG_TIER(2);}}}
    ld y=f*expl(factor-(SpatialD/2.L)*shift)*g.Z;if(!std::isfinite(y))throw std::runtime_error("nonfinite integrand");return {y,lev};
}
inline std::array<ld,NLOGS> sample(const Graph&g,const ld*uu,int K,const std::array<ld,NLOGS>&logs,int&level,int layout,Scratch&s) {
    int E=g.E,S=(1<<E)-1;ld fac=0,ou=uu[0];
    for(int pos=0;pos<E;++pos){ld u=(layout==2?ou:uu[layout==0?2*pos:E-1+pos])*g.choice_total[S];int pick=-1;
        for(int j=0;j<E;++j)if(S>>j&1){u-=g.dp[S^(1<<j)];if(u<=0){pick=j;break;}}
        if(pick<0)pick=31-__builtin_clz(S);
        if(layout==2){ld pr=g.dp[S^(1<<pick)];ou=(u+pr)/pr;ou=std::max(0.L,std::min(nextafterl(1.L,0.L),ou));}
        s.order[pos]=pick;S^=1<<pick;
        if(S){int ix=layout==0?2*pos+1:(layout==2?pos+1:pos);ld l=logl(uu[ix])/g.alpha[S];s.lt[pos]=l;fac+=(SpatialD*__builtin_popcount(unsigned(S))/4.0L-g.alpha[S])*l;}}
    ld cur=0;for(int j=0;j<E;++j){s.lx[s.order[j]]=cur;if(j<E-1)cur+=s.lt[j];}
    auto v=evaluate(g,s.lx.data(),fac,s);level=v.level;std::array<ld,NLOGS>out{};out[0]=1;
    // At the top loop L = order (K = 0) the unused logarithm and the entire regulator recurrence disappear.
    if(K){ld sumlog=0;for(int j=0;j<E;++j)sumlog+=s.lx[j];ld z=sumlog/4-g.L/2.L*logl(s.S);
        for(int n=1;n<=K;++n){ld a=0;for(int j=1;j<=n;++j)a+=j*(logs[j]+(j==1?z:0))*out[n-j];out[n]=a/n;}}
    for(int j=0;j<=K;++j)out[j]*=v.y;return out;
}
