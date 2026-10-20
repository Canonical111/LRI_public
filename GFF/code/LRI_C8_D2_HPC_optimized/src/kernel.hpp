#pragma once
// Finite-MOM kernels specialized for d=2, extended to target order eight.
// Algebra, importance map, summation order, and precision tiers are retained.
// Ordered-prefix sharing preserves each polynomial's original addition order.
#include <algorithm>
#include <array>
#include <cfenv>
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
#ifndef C8_DISABLE_FAST_Q_ADD
#include "positive_qadd.hpp"
#endif
#include <boost/version.hpp>
#include <boost/multiprecision/cpp_dec_float.hpp>
#ifdef C8_USE_GMP
#include <boost/multiprecision/gmp.hpp>
#endif
#ifdef __FAST_MATH__
#error "Fast-math is incompatible with the numerical contract"
#endif
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
struct Term { std::vector<int> ids, co; int denominator=0, numerator=0; };
struct Segment { int parent=0, begin=0, end=0; };
struct Graph {
    int id=0,E=0,L=0; ld wa=0,wb=0,Z=0;
    std::vector<unsigned> masks;
    std::vector<Term> terms;
    std::vector<ld> alpha,dp;
    // Loaded L8 rate tables usually contain only a few distinct values.
    // The palette stores the original scaled long doubles without rounding.
    std::vector<ld> alpha_palette;
    std::vector<unsigned char> alpha_index;
    std::vector<std::pair<int,int>> products;
    std::vector<int> mon_ids;
    std::vector<Segment> segments;
    std::vector<int> addends;
    std::vector<std::vector<std::pair<int,int>>> numerators;
    std::vector<ld> choice_total;
    ld proposal_alpha(unsigned subset) const {
#ifndef C8_DISABLE_RATE_PALETTE
        if(!alpha_index.empty())return alpha_palette[alpha_index[subset]];
#endif
        return alpha[subset];
    }
};
struct Scratch {
    std::array<ld,16> x{}, xs{},lx{},lt{};
    std::array<int,16> order{};
    std::vector<ld> products, sums, numerator,abs_numerator;
    ld S=0;
    void resize(const Graph&g) {
        products.resize(g.products.size()+1); sums.resize(g.segments.size()+1);
        numerator.resize(g.numerators.size()); abs_numerator.resize(g.numerators.size());
    }
};
struct Eval {ld y; int level;};
template<class T> T exponential(T x) { using std::exp; return exp(x); }
template<> inline Q exponential(Q x) { return expq(x); }
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
inline void compact_sampling_rates(Graph&g) {
#ifndef C8_DISABLE_RATE_PALETTE
    // Keep dense storage for other orders and unusual rate tables. Refusing
    // negative zero/nonfinite entries also preserves their exact semantics.
    if(g.L!=8 || g.alpha.size()!=size_t(1u<<g.E) || !g.alpha_index.empty())return;
    std::map<ld,unsigned> index;
    std::vector<ld> palette;
    std::vector<unsigned char> indices;indices.reserve(g.alpha.size());
    for(ld value:g.alpha){
        if(!std::isfinite(value) || (value==0 && std::signbit(value)))return;
        auto found=index.find(value);
        if(found==index.end()){
            if(palette.size()==256)return;
            unsigned id=unsigned(palette.size());index.emplace(value,id);
            palette.push_back(value);indices.push_back(static_cast<unsigned char>(id));
        }else indices.push_back(static_cast<unsigned char>(found->second));
    }
    g.alpha_palette=std::move(palette);g.alpha_index=std::move(indices);
    std::vector<ld>().swap(g.alpha);
#else
    (void)g;
#endif
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
inline Graph load_graph(const std::string&path,ld scale) {
    std::ifstream f(path);std::string magic;Graph g;int M=0,T=0,n=0;
    f>>magic>>g.L>>g.id>>g.wa>>g.wb>>M>>T;g.E=2*g.L;
    if((magic!="C8D2GRAPH1" && !(magic=="C7D2GRAPH1" && g.L<=7))||g.L<2||g.L>8||M<1||T<1||M>65536||T>1000000)throw std::runtime_error("invalid graph header: "+path);
    g.masks.resize(M);for(auto&m:g.masks)f>>m;
    for(int k=0;k<T;++k){Term t;f>>n;if(n<1||n>M)throw std::runtime_error("bad denominator size");t.ids.resize(n);for(auto&i:t.ids)f>>i;t.co.resize(g.E);for(auto&c:t.co)f>>c;g.terms.push_back(std::move(t));}
    f>>n;if(n!=(1<<g.E))throw std::runtime_error("invalid rate table");g.alpha.resize(n);for(auto&a:g.alpha)f>>a;
    if(!f)throw std::runtime_error("truncated graph: "+path);std::string extra;if(f>>extra)throw std::runtime_error("extra graph tokens");rates(g,scale);prepare(g);compact_sampling_rates(g);return g;
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
    std::array<T,16> x{},xs{};
    std::vector<T> products,sums,numerator,abs_numerator;
#ifndef C8_DISABLE_PROMOTED_SCALAR_REUSE
    // Reusing these scalar objects avoids repeated GMP limb allocation in
    // each segment/numerator. The arithmetic expressions and order stay fixed.
    T total=0,segment=0,num=0,absolute_num=0,product=0,value=0,error=0;
#endif
    void resize(const Graph&g) {
        auto ensure=[](std::vector<T>&values,size_t n){
#if !defined(C8_ENABLE_PROMOTED_GROW_ONLY) || defined(C8_DISABLE_PROMOTED_GROW_ONLY)
            values.resize(n);
#else
            // Opt-in: attribution did not establish a runtime/RSS benefit.
            // All accesses are bounded by the current graph, not this capacity.
            // Retain constructed GMP objects when the next graph is smaller.
            if(values.size()<n)values.resize(n);
#endif
        };
        ensure(products,g.products.size()+1);ensure(sums,g.segments.size()+1);
        ensure(numerator,g.numerators.size());ensure(abs_numerator,g.numerators.size());
    }
};
template<class T,bool NeedError=true>
std::pair<T,T> calculate_shared(const Graph&g,const ld*logx,ld shift) {
    static thread_local PromotedScratch<T> scratch;
    auto&s=scratch;s.resize(g);
#ifndef C8_DISABLE_FAST_Q_ADD
    // Only the Q denominator sums use the exact-value specialization. Check
    // the active rounding mode once; directed modes retain compiler addition.
    // Floating exception flags are not part of the integrator's value contract.
    bool fast_q_add=false;
    if constexpr(std::is_same_v<T,Q>)fast_q_add=std::fegetround()==FE_TONEAREST;
#endif
#ifdef C8_DISABLE_PROMOTED_SCALAR_REUSE
    T S=0;
#else
    T&S=s.total;S=0;
#endif
    s.products[0]=1;s.sums[0]=0;
    for(int j=0;j<g.E;++j){s.x[j]=exponential(T(logx[j]));S+=s.x[j];
        s.xs[j]=shift==0?s.x[j]:exponential(T(T(logx[j])-T(shift)/g.L));}
    for(size_t j=0;j<g.products.size();++j){auto o=g.products[j];s.products[j+1]=s.products[o.first]*s.xs[o.second];}
    for(size_t j=0;j<g.segments.size();++j){auto a=g.segments[j];
#ifdef C8_DISABLE_PROMOTED_SCALAR_REUSE
        T v=s.sums[a.parent];
#else
        T&v=s.segment;v=s.sums[a.parent];
#endif
#ifndef C8_DISABLE_FAST_Q_ADD
        if constexpr(std::is_same_v<T,Q>){
            if(fast_q_add){for(int k=a.begin;k<a.end;++k)v=c8::add_positive_nearest(v,s.products[g.addends[k]]);}
            else {for(int k=a.begin;k<a.end;++k)v+=s.products[g.addends[k]];}
        }else
#endif
        {for(int k=a.begin;k<a.end;++k)v+=s.products[g.addends[k]];}
        s.sums[j+1]=v;}
    for(size_t j=0;j<g.numerators.size();++j){
#ifdef C8_DISABLE_PROMOTED_SCALAR_REUSE
        T n=0,ab=0;
#else
        T&n=s.num;T&ab=s.absolute_num;n=0;if constexpr(NeedError)ab=0;
#endif
        for(auto [i,c]:g.numerators[j]){
#ifdef C8_DISABLE_PROMOTED_SCALAR_REUSE
            T p=T(c)*s.x[i];
#else
            T&p=s.product;p=T(c)*s.x[i];
#endif
            n+=p;if constexpr(NeedError)ab+=absolute(p);}
        s.numerator[j]=n;if constexpr(NeedError)s.abs_numerator[j]=ab;}
#ifdef C8_DISABLE_PROMOTED_SCALAR_REUSE
    T val=0,err=0;
#else
    T&val=s.value;T&err=s.error;val=0;if constexpr(NeedError)err=0;
#endif
    for(const auto&t:g.terms){const T&U=s.sums[t.denominator];
        val+=s.numerator[t.numerator]/U;if constexpr(NeedError)err+=s.abs_numerator[t.numerator]/U;}
    return {val/S,NeedError?err/S:T(0)};
}
inline Eval evaluate(const Graph&g,const ld*lx,ld factor,Scratch&s) {
    ld shift=0;bool direct=true;for(int j=0;j<g.E;++j)if(lx[j]<-600||lx[j]>0)direct=false;
    if(!direct){shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld v=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;v+=lx[j];}shift=std::max(shift,v);}}
    bool moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
    auto v=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);
    if(!moderate){s.S=0;for(int j=0;j<g.E;++j)s.S+=expl(lx[j]);}
    ld ratio=absolute(v.first)/(v.second+1e-4900L);int lev=0;ld f=v.first;
    if(ratio<1e-9L){auto q=calculate_shared<Q>(g,lx,shift);lev=1;f=ld(q.first);if(absolute(q.first)<Q(1e-23L)*q.second){auto m=calculate_shared<MP,false>(g,lx,shift);f=m.first.convert_to<ld>();lev=2;}}
    ld y=f*expl(factor-shift)*g.Z;if(!std::isfinite(y))throw std::runtime_error("nonfinite integrand");return {y,lev};
}
inline std::array<ld,7> sample(const Graph&g,const ld*uu,int K,const std::array<ld,7>&logs,int&level,int layout,Scratch&s) {
    if(K<0 || K>6)throw std::runtime_error("invalid Taylor jet order");
    int E=g.E,S=(1<<E)-1;ld fac=0,ou=uu[0];
    for(int pos=0;pos<E;++pos){ld u=(layout==2?ou:uu[layout==0?2*pos:E-1+pos])*g.choice_total[S];int pick=-1;
        for(int j=0;j<E;++j)if(S>>j&1){u-=g.dp[S^(1<<j)];if(u<=0){pick=j;break;}}
        if(pick<0)pick=31-__builtin_clz(S);
        if(layout==2){ld pr=g.dp[S^(1<<pick)];ou=(u+pr)/pr;ou=std::max(0.L,std::min(nextafterl(1.L,0.L),ou));}
        s.order[pos]=pick;S^=1<<pick;
        if(S){int ix=layout==0?2*pos+1:(layout==2?pos+1:pos);ld alpha=g.proposal_alpha(unsigned(S));ld l=logl(uu[ix])/alpha;s.lt[pos]=l;fac+=(__builtin_popcount(unsigned(S))/2.0L-alpha)*l;}}
    ld cur=0;for(int j=0;j<E;++j){s.lx[s.order[j]]=cur;if(j<E-1)cur+=s.lt[j];}
    auto v=evaluate(g,s.lx.data(),fac,s);level=v.level;std::array<ld,7>out{};out[0]=1;
    // At the target loop order the regulator recurrence is empty.
    if(K){ld sumlog=0;for(int j=0;j<E;++j)sumlog+=s.lx[j];ld z=sumlog/4-g.L/2.L*logl(s.S);
        for(int n=1;n<=K;++n){ld a=0;for(int j=1;j<=n;++j)a+=j*(logs[j]+(j==1?z:0))*out[n-j];out[n]=a/n;}}
    for(int j=0;j<=K;++j)out[j]*=v.y;return out;
}
