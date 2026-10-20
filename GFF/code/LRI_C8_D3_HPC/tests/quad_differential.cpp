// Stage 4b #4 differential test (= C62d's R3a proof; port of LRI_C8_D2_HPC@14d7347 tests/quad_differential.cpp, sha256
// a26d5039..., names only; PLAN "Performance plan", #4 proof): src/quadfast.hpp's add, sub and mul against libgcc's
// __addtf3, __subtf3 and __multf3, bit for bit, on random pairs and on edge lists. Built by `make quaddiff` with the
// worker's compile command (bin/c8d3_quad_differential); driven by tests/quad_differential.py.
//
//   c8d3_quad_differential [--pairs N] [--seed S] [--threads T] [--kernel-add LO:HI] [--kernel-mul LO:HI]
//                          [--edges-only] [--no-edges] [--inject K] [--bench]
//
// --pairs N: random pairs PER OPERATION, split equally over the four streams of each operation (below). Every pair
// compares quadfast::{add,sub,mul}(a,b), the functions the kernel inlines, with the libgcc result computed through
// volatile operands in an out-of-line function, as 16-byte patterns. The fast path's own predicate
// (addsub_fast/mul_fast) is evaluated as well, to count the pairs that exercised the inline code ("fast") rather
// than the libgcc fallback; on a fast pair its result is compared too.
// Streams (biased exponents; d = exponent difference; LO:HI of --kernel-add/--kernel-mul are the exponent windows the
// kernel's operands occupy, from tests/quad_ranges.cpp, widened by the driver):
//   add, sub: kernel  ea uniform in the kernel window; d: 60% uniform 0..127, 20% 0..3, 20% uniform over the window;
//                     random signs and significand patterns (random, sparse, dense, runs, low/high bits only, 0, all 1)
//             full    the same over the whole normal range 1..0x7FFE
//             cancel  d in {0,1,2}, the smaller significand derived from the larger's (low k bits changed,
//                     k = 0..112), 90% effective subtraction: massive cancellation and exact zeros
//             bits    both operands uniform random 128-bit patterns (zeros, subnormals, inf and NaN included)
//   mul:      kernel  ea, eb uniform in the kernel window
//             full    result exponent ea+eb-16383 uniform over -120..0x7FFE+120, or (30%) within 3 of the
//                     subnormal and overflow boundaries
//             ties    b = 1 + 2^(s-112), a's lowest set bit at 111-s: exact ties of the product, and +-1 in a's last
//                     bit (just above and below half); random exponents with a valid result
//             bits    uniform random 128-bit patterns
// Edge lists (deterministic, every pair also in swapped order for add and mul): specials (all ordered pairs of ~80
// values: signed zeros, subnormals, smallest/largest normals, 1 +- ulp, inf, quiet and signaling NaNs with payloads,
// values at exponents 1, 2, 0x7FFD, 0x7FFE), align (every alignment d = 0..130 and larger ones, the smaller
// significand's shifted-out part exactly half, half +- one sticky bit, a lone low bit, all ones, zero, random, against
// even/odd/all-ones/power-of-two larger significands, same and opposite signs), cancel (equal and adjacent exponents,
// significands differing in the low k bits, k = 0..112, exact zeros), carry (all-ones significands rounding up,
// carries into the overflow exponent), boundary (results at the subnormal and overflow boundaries), mul_ties
// (s = 0..111), mul_boundary (result exponents -3..3 and 0x7FFB..0x8002 with and without the normalization bit),
// zeros (x + -x, x - x, signed zero products). --inject K (self-test only): the fast result of every K-th random pair
// gets its last bit flipped, so the comparison must report mismatches.
// --bench: ns per operation of quadfast against libgcc on a dependent accumulation chain (the kernel's v += p) and on
// independent multiplications (informative).
// Output: one JSON object on stdout. Exit 0 when the run completed (the driver checks the mismatch counts), 2 on usage.
#include "../src/quadfast.hpp"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <omp.h>
namespace qf=quadfast;
using F=qf::F;
using u128=qf::u128;
constexpr int EMAXN=0x7FFE;  // largest normal biased exponent

__attribute__((noipa)) static F ref_add(F a,F b){volatile F x=a,y=b;return x+y;}
__attribute__((noipa)) static F ref_sub(F a,F b){volatile F x=a,y=b;return x-y;}
__attribute__((noipa)) static F ref_mul(F a,F b){volatile F x=a,y=b;return x*y;}

static inline uint64_t splitmix(uint64_t&x){uint64_t z=(x+=0x9e3779b97f4a7c15ULL);z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;z=(z^(z>>27))*0x94d049bb133111ebULL;return z^(z>>31);}
struct Rng {  // xoshiro256**
    uint64_t s[4];
    explicit Rng(uint64_t seed){for(auto&v:s)v=splitmix(seed);}
    static uint64_t rotl(uint64_t x,int k){return (x<<k)|(x>>(64-k));}
    uint64_t next(){const uint64_t r=rotl(s[1]*5,7)*9,t=s[1]<<17;s[2]^=s[0];s[3]^=s[1];s[1]^=s[2];s[0]^=s[3];s[2]^=t;s[3]=rotl(s[3],45);return r;}
    uint64_t below(uint64_t n){return uint64_t((u128(next())*n)>>64);}
    int range(int lo,int hi){return lo+int(below(uint64_t(hi-lo)+1));}  // inclusive
    bool coin(){return next()>>63;}
    u128 wide(){return (u128(next())<<64)|next();}
};
static uint64_t mix(uint64_t a,uint64_t b,uint64_t c,uint64_t d){uint64_t x=a;splitmix(x);x^=b*0x9e3779b97f4a7c15ULL;splitmix(x);x^=c*0xc2b2ae3d27d4eb4fULL;splitmix(x);x^=d*0x165667b19e3779f9ULL;return splitmix(x);}

static inline u128 bitsof(F x){return qf::bits(x);}
static inline F make(bool neg,int e,u128 frac){return qf::value((neg?qf::SIGN:u128(0))|(u128(unsigned(e))<<112)|(frac&qf::FRAC));}
static inline int clampe(int e){return e<1?1:(e>EMAXN?EMAXN:e);}
static u128 lowmask(int k){return k<=0?u128(0):(k>=128?~u128(0):((qf::ONE<<k)-1));}
// A 112-bit fraction drawn from patterns that exercise carries, borrows and sticky bits.
static u128 frac(Rng&r){
    switch(r.below(10)){
        case 0:return 0;
        case 1:return qf::FRAC;
        case 2:{u128 f=0;int n=r.range(1,6);for(int i=0;i<n;++i)f|=qf::ONE<<r.below(112);return f;}             // sparse
        case 3:{u128 f=qf::FRAC;int n=r.range(1,6);for(int i=0;i<n;++i)f&=~(qf::ONE<<r.below(112));return f;}   // dense
        case 4:{int lo=r.range(0,111),hi=r.range(lo,111);return lowmask(hi+1)&~lowmask(lo);}                     // a run of ones
        case 5:return r.wide()&lowmask(r.range(1,112));                                                         // low bits only
        case 6:return r.wide()&qf::FRAC&~lowmask(r.range(0,111));                                               // high bits only
        default:return r.wide()&qf::FRAC;
    }
}
// d: 60% uniform 0..127, 20% 0..3, 20% uniform 0..span
static int distance(Rng&r,int span){uint64_t u=r.below(10);if(u<6)return r.range(0,127);if(u<8)return r.range(0,3);return r.range(0,span<0?0:span);}

struct Mismatch {int op;F a,b,got,want;std::string where;};
struct Tally {
    unsigned long long pairs=0,fast=0,mismatches=0;
    void add(const Tally&o){pairs+=o.pairs;fast+=o.fast;mismatches+=o.mismatches;}
};
static std::vector<Mismatch> g_mism;
static const char*OPN[3]={"add","sub","mul"};
static unsigned long long g_inject=0;

// One pair of operation op: compares quadfast with libgcc; counts the fast-path pairs.
static inline void check(int op,F a,F b,Tally&t,const char*where,unsigned long long index){
    F want,got;u128 fast=0;bool isfast;const u128 ua=bitsof(a),ub=bitsof(b);
    if(op==0){want=ref_add(a,b);got=qf::add(a,b);isfast=qf::addsub_fast<false>(ua,ub,fast);}
    else if(op==1){want=ref_sub(a,b);got=qf::sub(a,b);isfast=qf::addsub_fast<true>(ua,ub,fast);}
    else{want=ref_mul(a,b);got=qf::mul(a,b);isfast=qf::mul_fast(ua,ub,fast);}
    if(g_inject&&index%g_inject==0)got=qf::value(bitsof(got)^1);
    ++t.pairs;t.fast+=isfast;
    const u128 w=bitsof(want);
    const bool bad=bitsof(got)!=w||(isfast&&fast!=w);
    if(__builtin_expect(bad,0)){
        ++t.mismatches;
        #pragma omp critical(mism)
        {if(g_mism.size()<24)g_mism.push_back({op,a,b,got,want,where});}
    }
}

// ---------------------------------------------------------------- random streams
struct Window {int lo=1,hi=EMAXN;};
static void stream_pair(int op,int stream,Rng&r,const Window&ka,const Window&km,F&a,F&b){
    if(op<2){
        switch(stream){
            case 0:case 1:{const Window w=stream==0?ka:Window{};int ea=r.range(w.lo,w.hi);int d=distance(r,w.hi-w.lo);
                int eb=clampe(r.coin()?ea-d:ea+d);a=make(r.coin(),ea,frac(r));b=make(r.coin(),eb,frac(r));return;}
            case 2:{int d=int(r.below(3)),ea=r.range(1+d,EMAXN),k=r.range(0,112);u128 fa=frac(r),fb;
                if(d==0)fb=fa^(r.wide()&lowmask(k));
                else{fa&=lowmask(k);fb=qf::FRAC^(r.wide()&lowmask(k));}                     // 1.000xxx vs 0.111yyy
                bool sa=r.coin(),sb=r.below(10)<9?(op==0?!sa:sa):r.coin();                    // 90% effective subtraction
                a=make(sa,ea,fa);b=make(sb,ea-d,fb);if(r.coin())std::swap(a,b);return;}
            default:a=qf::value(r.wide());b=qf::value(r.wide());return;
        }
    }
    switch(stream){
        case 0:a=make(r.coin(),r.range(km.lo,km.hi),frac(r));b=make(r.coin(),r.range(km.lo,km.hi),frac(r));return;
        case 1:{int er=r.below(10)<7?r.range(-120,EMAXN+120):(r.coin()?r.range(-3,3):r.range(EMAXN-3,EMAXN+4));
            int lo=std::max(1,er+qf::BIAS-EMAXN),hi=std::min(EMAXN,er+qf::BIAS-1);int ea=r.range(lo,hi);
            a=make(r.coin(),ea,frac(r));b=make(r.coin(),er+qf::BIAS-ea,frac(r));return;}
        case 2:{int s=r.range(0,111);u128 fb=qf::ONE<<s;u128 fa=((r.wide()<<(112-s))|(qf::ONE<<(111-s)))&qf::FRAC;
            uint64_t u=r.below(3);if(u==1)fa+=1;else if(u==2)fa-=1;fa&=qf::FRAC;
            int er=r.range(-2,EMAXN+2);int lo=std::max(1,er+qf::BIAS-EMAXN),hi=std::min(EMAXN,er+qf::BIAS-1);int ea=r.range(lo,hi);
            a=make(r.coin(),ea,fa);b=make(r.coin(),er+qf::BIAS-ea,fb);if(r.coin())std::swap(a,b);return;}
        default:a=qf::value(r.wide());b=qf::value(r.wide());return;
    }
}
static const char*STREAMS[2][4]={{"kernel","full","cancel","bits"},{"kernel","full","ties","bits"}};

// ---------------------------------------------------------------- edge lists
struct EdgeRun {
    // category -> per-op tallies
    std::vector<std::string> names;std::vector<Tally> t[3];
    Tally&at(int op,const std::string&n){for(size_t i=0;i<names.size();++i)if(names[i]==n)return t[op][i];names.push_back(n);for(auto&v:t)v.emplace_back();return t[op].back();}
};
static std::vector<F> specials(){
    std::vector<F> s;Rng r(0x5eed5eedULL);
    std::vector<u128> mag={0,1,2,qf::FRAC,qf::FRAC-1,qf::HIDDEN>>1,                                   // zero, subnormals
        u128(1)<<112,(u128(1)<<112)|1,(u128(1)<<112)|qf::FRAC,(u128(2)<<112),                         // smallest normals
        (u128(EMAXN)<<112)|qf::FRAC,(u128(EMAXN)<<112)|(qf::FRAC-1),(u128(EMAXN)<<112),(u128(EMAXN-1)<<112)|qf::FRAC,  // largest
        u128(qf::BIAS)<<112,(u128(qf::BIAS)<<112)|1,(u128(qf::BIAS-1)<<112)|qf::FRAC,(u128(qf::BIAS+1)<<112),  // 1, 1+ulp, 1-ulp/2, 2
        u128(0x7FFF)<<112,                                                                            // inf
        (u128(0x7FFF)<<112)|(qf::ONE<<111),(u128(0x7FFF)<<112)|(qf::ONE<<111)|12345,                  // quiet NaNs
        (u128(0x7FFF)<<112)|1,(u128(0x7FFF)<<112)|(qf::ONE<<110)|777};                                // signaling NaNs
    for(int e:{1,2,3,EMAXN-2,EMAXN-1,EMAXN,qf::BIAS-60,qf::BIAS+60})for(int k=0;k<3;++k)mag.push_back((u128(unsigned(e))<<112)|(r.wide()&qf::FRAC));
    for(int k=0;k<3;++k)mag.push_back(r.wide()&qf::FRAC&lowmask(r.range(1,111)));                // random subnormals
    for(auto m:mag){s.push_back(qf::value(m));s.push_back(qf::value(m|qf::SIGN));}
    return s;
}
static void edges(EdgeRun&E){
    // specials: every ordered pair, every operation
    {auto S=specials();for(int op=0;op<3;++op){auto&t=E.at(op,"specials");for(F a:S)for(F b:S)check(op,a,b,t,"specials",1);}}
    Rng r(0xed6e5ULL);
    // align: every alignment distance with exact sticky patterns, both signs, both orders, add and sub
    {std::vector<int> ds;for(int d=0;d<=130;++d)ds.push_back(d);for(int d:{150,200,500,1000,4000,16000,30000})ds.push_back(d);
     for(int op=0;op<2;++op){auto&t=E.at(op,"align");
      for(int d:ds)for(int bp=0;bp<7;++bp)for(int ap=0;ap<4;++ap)for(int sg=0;sg<2;++sg)for(int rep=0;rep<16;++rep){
        u128 fa;switch(ap){case 0:fa=(r.wide()&qf::FRAC)&~u128(1);break;case 1:fa=(r.wide()&qf::FRAC)|1;break;case 2:fa=qf::FRAC;break;default:fa=0;}
        u128 mb=qf::HIDDEN|(r.wide()&qf::FRAC);int k=std::min(d,113);    // the bits of b's significand shifted below a's last bit
        switch(bp){
            case 0:if(k>=1)mb=(mb&~lowmask(k))|(qf::ONE<<(k-1));break;                 // exactly half
            case 1:if(k>=2)mb=(mb&~lowmask(k))|(qf::ONE<<(k-1))|1;break;               // half + sticky
            case 2:if(k>=2)mb=(mb&~lowmask(k))|lowmask(k-1);break;                      // half - one unit
            case 3:mb=qf::HIDDEN|1;break;                                                // a lone low bit
            case 4:mb=qf::HIDDEN|qf::FRAC;break;                                         // all ones
            case 5:mb=qf::HIDDEN;break;                                                  // power of two
            default:break;                                                               // random
        }
        int ea;uint64_t u=r.below(4);ea=u==0?r.range(1+d<EMAXN?1+d:EMAXN,std::min(EMAXN,d+8)):(u==1?r.range(std::max(1,EMAXN-3),EMAXN):r.range(std::min(EMAXN,1+d),EMAXN));
        int eb=ea-d;bool sa=r.coin(),sb=sg?!sa:sa;
        F a=make(sa,ea,fa),b=eb>=1?make(sb,eb,mb):make(sb,1,mb);                       // d too large for ea: b at exponent 1
        check(op,a,b,t,"align",1);check(op,b,a,t,"align",1);}}}
    // cancel: equal and adjacent exponents, significands differing in the low k bits (k = 0: exact zero)
    {for(int op=0;op<2;++op){auto&t=E.at(op,"cancel");
      for(int d=0;d<=1;++d)for(int k=0;k<=112;++k)for(int rep=0;rep<64;++rep){
        int ea=rep%8==0?r.range(1+d,4+d):r.range(1+d,EMAXN);u128 fa=r.wide()&qf::FRAC,fb;
        if(d==0)fb=fa^(r.wide()&lowmask(k));else{fa&=lowmask(k);fb=qf::FRAC^(r.wide()&lowmask(k));}
        bool sa=r.coin(),sb=op==0?!sa:sa;F a=make(sa,ea,fa),b=make(sb,ea-d,fb);
        check(op,a,b,t,"cancel",1);check(op,b,a,t,"cancel",1);}}}
    // carry: all-ones significands that round up into the next binade, and carries into the overflow exponent
    {for(int op=0;op<2;++op){auto&t=E.at(op,"carry");
      for(int d=0;d<=120;++d)for(int rep=0;rep<64;++rep){
        int ea=rep%4==0?r.range(std::max(1,EMAXN-2),EMAXN):r.range(std::min(EMAXN,1+d),EMAXN);int eb=ea-d;if(eb<1)continue;
        u128 fa=qf::FRAC&~(r.coin()?u128(0):lowmask(r.range(0,3)));u128 fb=rep%2?qf::FRAC:(r.wide()&qf::FRAC);
        bool sa=r.coin(),sb=op==0?sa:!sa;F a=make(sa,ea,fa),b=make(sb,eb,fb);
        check(op,a,b,t,"carry",1);check(op,b,a,t,"carry",1);}}}
    // boundary: results at the subnormal and overflow boundaries
    {for(int op=0;op<2;++op){auto&t=E.at(op,"boundary");
      for(int rep=0;rep<200000;++rep){bool low=rep%2;int ea,eb;
        if(low){ea=r.range(1,6);eb=r.range(1,ea);}else{ea=r.range(EMAXN-5,EMAXN);eb=r.range(std::max(1,ea-120),ea);}
        F a=make(r.coin(),ea,frac(r)),b=make(r.coin(),eb,frac(r));check(op,a,b,t,"boundary",1);check(op,b,a,t,"boundary",1);}
      F mx=make(false,EMAXN,qf::FRAC);                                                    // max normal +- half ulp (ties)
      for(int sh=111;sh<=116;++sh)for(int sg=0;sg<4;++sg){F h=make(sg&1,EMAXN-sh,0),m=make(sg&2,EMAXN,qf::FRAC);check(op,m,h,t,"boundary",1);check(op,h,m,t,"boundary",1);}
      check(op,mx,mx,t,"boundary",1);}}
    // zeros: x + (-x), x - x, -x - (-x): exact zeros and their signs
    {for(int op=0;op<2;++op){auto&t=E.at(op,"zeros");
      for(int rep=0;rep<100000;++rep){F x=make(r.coin(),r.range(1,EMAXN),frac(r));F y=op==0?qf::value(bitsof(x)^qf::SIGN):x;check(op,x,y,t,"zeros",1);check(op,y,x,t,"zeros",1);}}}
    // mul_ties: exact product ties for s = 0..111, and +-1 in a's last bit
    {auto&t=E.at(2,"mul_ties");
     for(int s=0;s<=111;++s)for(int pm=0;pm<3;++pm)for(int rep=0;rep<256;++rep){
        u128 fb=qf::ONE<<s;u128 fa=((r.wide()<<(112-s))|(qf::ONE<<(111-s)))&qf::FRAC;if(pm==1)fa=(fa+1)&qf::FRAC;else if(pm==2)fa=(fa-1)&qf::FRAC;
        int ea=r.range(qf::BIAS-4000,qf::BIAS+4000),eb=r.range(qf::BIAS-4000,qf::BIAS+4000);
        F a=make(r.coin(),ea,fa),b=make(r.coin(),eb,fb);check(2,a,b,t,"mul_ties",1);check(2,b,a,t,"mul_ties",1);}}
    // mul_boundary: result exponents -3..3 and 0x7FFB..0x8002, with small (no normalization bit) and large significands
    {auto&t=E.at(2,"mul_boundary");
     for(int er=-3;er<=3+(EMAXN+4-(EMAXN-3)+1);++er){int target=er<=3?er:EMAXN-3+(er-4);
      int lo=std::max(1,target+qf::BIAS-EMAXN),hi=std::min(EMAXN,target+qf::BIAS-1);
      for(int big=0;big<3;++big)for(int rep=0;rep<4096;++rep){int ea=r.range(lo,hi);u128 fa,fb;
        if(big==0){fa=r.wide()&lowmask(r.range(0,100));fb=r.wide()&lowmask(r.range(0,100));}
        else if(big==1){fa=qf::FRAC&~(r.wide()&lowmask(r.range(0,100)));fb=qf::FRAC&~(r.wide()&lowmask(r.range(0,100)));}
        else{fa=r.wide()&qf::FRAC;fb=r.wide()&qf::FRAC;}
        F a=make(r.coin(),ea,fa),b=make(r.coin(),target+qf::BIAS-ea,fb);check(2,a,b,t,"mul_boundary",1);check(2,b,a,t,"mul_boundary",1);}}}
    // mul_carry: significands near all ones times 1 + tiny, rounding up into the next binade
    {auto&t=E.at(2,"mul_carry");
     for(int rep=0;rep<400000;++rep){u128 fa=qf::FRAC&~(r.wide()&lowmask(r.range(0,8)));u128 fb=r.wide()&lowmask(r.range(0,8));
        int ea=r.range(2,EMAXN),lo=std::max(1,qf::BIAS-ea+1),hi=std::min(EMAXN,EMAXN+qf::BIAS-ea);if(lo>hi)continue;int eb=r.range(lo,hi);
        F a=make(r.coin(),ea,fa),b=make(r.coin(),eb,fb);check(2,a,b,t,"mul_carry",1);check(2,b,a,t,"mul_carry",1);}}
}

// ---------------------------------------------------------------- benchmark (informative)
static double now(){return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();}
__attribute__((noipa)) static F chain_ref(const F*p,int n,int reps){F v=0;for(int r=0;r<reps;++r)for(int k=0;k<n;++k)v=v+p[k];return v;}
__attribute__((noipa)) static F chain_fast(const F*p,int n,int reps){F v=0;for(int r=0;r<reps;++r)for(int k=0;k<n;++k)v=qf::add(v,p[k]);return v;}
__attribute__((noipa)) static void muls_ref(const F*a,const F*b,F*c,int n,int reps){for(int r=0;r<reps;++r)for(int k=0;k<n;++k)c[k]=a[k]*b[(k+r)&(n-1)];}  // n: a power of 2
__attribute__((noipa)) static void muls_fast(const F*a,const F*b,F*c,int n,int reps){for(int r=0;r<reps;++r)for(int k=0;k<n;++k)c[k]=qf::mul(a[k],b[(k+r)&(n-1)]);}
static void bench(){
    const int n=4096,reps=2000;std::vector<F> p(n),a(n),b(n),c1(n),c2(n);Rng r(42);
    for(int k=0;k<n;++k){p[k]=make(false,r.range(qf::BIAS-3000,qf::BIAS-2900),r.wide()&qf::FRAC);a[k]=make(r.coin(),r.range(qf::BIAS-400,qf::BIAS+400),r.wide()&qf::FRAC);b[k]=make(false,r.range(qf::BIAS-400,qf::BIAS+400),r.wide()&qf::FRAC);}
    double t0=now();F v1=chain_ref(p.data(),n,reps);double t1=now();F v2=chain_fast(p.data(),n,reps);double t2=now();
    muls_ref(a.data(),b.data(),c1.data(),n,reps/4);double t3=now();muls_fast(a.data(),b.data(),c2.data(),n,reps/4);double t4=now();
    const double ops=double(n)*reps,mops=double(n)*(reps/4);
    std::printf(",\"bench\":{\"add_chain_ns_libgcc\":%.3f,\"add_chain_ns_quadfast\":%.3f,\"mul_ns_libgcc\":%.3f,\"mul_ns_quadfast\":%.3f,\"identical\":%s}",
        (t1-t0)/ops*1e9,(t2-t1)/ops*1e9,(t3-t2)/mops*1e9,(t4-t3)/mops*1e9,(bitsof(v1)==bitsof(v2)&&std::memcmp(c1.data(),c2.data(),sizeof(F)*n)==0)?"true":"false");
}

static std::string hex(F x){u128 u=bitsof(x);char s[40];std::snprintf(s,sizeof s,"%016llx%016llx",(unsigned long long)(u>>64),(unsigned long long)u);return s;}
static bool parse_window(const char*s,Window&w){int lo,hi;if(std::sscanf(s,"%d:%d",&lo,&hi)!=2||lo<1||hi>EMAXN||lo>hi)return false;w={lo,hi};return true;}

int main(int argc,char**argv){
    unsigned long long pairs=1ULL<<32,seed=20261004ULL;int threads=omp_get_max_threads();bool do_edges=true,do_random=true,do_bench=false;Window ka,km;
    for(int i=1;i<argc;++i){std::string o=argv[i];auto val=[&]()->const char*{if(i+1>=argc){std::fprintf(stderr,"%s needs a value\n",o.c_str());std::exit(2);}return argv[++i];};
        if(o=="--pairs")pairs=std::strtoull(val(),nullptr,10);else if(o=="--seed")seed=std::strtoull(val(),nullptr,10);else if(o=="--threads")threads=std::atoi(val());
        else if(o=="--kernel-add"){if(!parse_window(val(),ka))return 2;}else if(o=="--kernel-mul"){if(!parse_window(val(),km))return 2;}
        else if(o=="--edges-only")do_random=false;else if(o=="--no-edges")do_edges=false;else if(o=="--inject")g_inject=std::strtoull(val(),nullptr,10);
        else if(o=="--bench")do_bench=true;else{std::fprintf(stderr,"unknown option %s\n",o.c_str());return 2;}}
    if(threads<1)return 2;
    omp_set_num_threads(threads);double t0=now();
    // random streams: chunks of 2^20 pairs, each with its own generator seeded from (seed, op, stream, chunk)
    const unsigned long long CH=1ULL<<20,per=pairs/4,nch=(per+CH-1)/CH;Tally rs[3][4];
    if(do_random){
        for(int op=0;op<3;++op)for(int st=0;st<4;++st){
            Tally tot;
            #pragma omp parallel
            {Tally loc;
             #pragma omp for schedule(dynamic,1)
             for(long long ch=0;ch<(long long)nch;++ch){Rng r(mix(seed,uint64_t(op),uint64_t(st),uint64_t(ch)));
                const unsigned long long n=std::min(CH,per-ch*CH);F a,b;
                for(unsigned long long i=0;i<n;++i){stream_pair(op,st,r,ka,km,a,b);check(op,a,b,loc,STREAMS[op==2][st],ch*CH+i+1);}}
             #pragma omp critical(tally)
             tot.add(loc);}
            rs[op][st]=tot;}
    }
    double t1=now();EdgeRun E;if(do_edges)edges(E);double t2=now();
    std::printf("{\"schema\":\"c8-d3-quad-differential-1\",\"compiler\":\"%s\",\"seed\":%llu,\"threads\":%d,\"pairs_requested_per_op\":%llu,\"inject\":%llu,",
        __VERSION__,seed,threads,do_random?pairs:0ULL,g_inject);
    std::printf("\"kernel_add_window\":[%d,%d],\"kernel_mul_window\":[%d,%d],\"random\":{",ka.lo,ka.hi,km.lo,km.hi);
    for(int op=0;op<3;++op){Tally s;std::printf("%s\"%s\":{\"streams\":{",op?",":"",OPN[op]);
        for(int st=0;st<4;++st){s.add(rs[op][st]);std::printf("%s\"%s\":{\"pairs\":%llu,\"fast\":%llu,\"mismatches\":%llu}",st?",":"",STREAMS[op==2][st],rs[op][st].pairs,rs[op][st].fast,rs[op][st].mismatches);}
        std::printf("},\"pairs\":%llu,\"fast\":%llu,\"mismatches\":%llu}",s.pairs,s.fast,s.mismatches);}
    std::printf("},\"edges\":{");
    for(int op=0;op<3;++op){Tally s;bool first=true;std::printf("%s\"%s\":{\"categories\":{",op?",":"",OPN[op]);
        for(size_t i=0;i<E.names.size();++i){const Tally&t=E.t[op][i];if(!t.pairs)continue;s.add(t);std::printf("%s\"%s\":{\"pairs\":%llu,\"fast\":%llu,\"mismatches\":%llu}",first?"":",",E.names[i].c_str(),t.pairs,t.fast,t.mismatches);first=false;}
        std::printf("},\"pairs\":%llu,\"fast\":%llu,\"mismatches\":%llu}",s.pairs,s.fast,s.mismatches);}
    std::printf("},\"first_mismatches\":[");
    for(size_t i=0;i<g_mism.size();++i){auto&m=g_mism[i];std::printf("%s{\"op\":\"%s\",\"where\":\"%s\",\"a\":\"%s\",\"b\":\"%s\",\"got\":\"%s\",\"want\":\"%s\"}",i?",":"",OPN[m.op],m.where.c_str(),hex(m.a).c_str(),hex(m.b).c_str(),hex(m.got).c_str(),hex(m.want).c_str());}
    std::printf("],\"random_seconds\":%.3f,\"edge_seconds\":%.3f",t1-t0,t2-t1);
    if(do_bench)bench();
    std::printf("}\n");return 0;
}
