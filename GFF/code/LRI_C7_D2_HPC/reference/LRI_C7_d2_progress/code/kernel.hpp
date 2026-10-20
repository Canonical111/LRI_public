#pragma once
// Same finite-MOM kernels as reference/code/kernel.hpp, specialized for d=2.
// Ordered-prefix sharing preserves each polynomial's original addition order.
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
#include <utility>
#include <vector>
#include <quadmath.h>
#include <boost/multiprecision/cpp_dec_float.hpp>
#ifdef __FAST_MATH__
#error "Fast-math is incompatible with the numerical contract"
#endif
using ld = long double;
using Q = __float128;
using MP = boost::multiprecision::number<boost::multiprecision::cpp_dec_float<300>>;
static_assert(std::numeric_limits<ld>::digits >= 64, "long double must retain >=64 significant binary bits");
static_assert(std::numeric_limits<ld>::max_exponent >= 16384, "extended exponent range required");
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
    std::array<ld,14> x{}, xs{},lx{},lt{};
    std::array<int,14> order{};
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
    std::ifstream f(path);std::string magic;Graph g;int M,T,n;
    f>>magic>>g.L>>g.id>>g.wa>>g.wb>>M>>T;g.E=2*g.L;
    if(magic!="C7D2GRAPH1"||g.L<2||g.L>7||M<1||T<1||M>16384||T>10000)throw std::runtime_error("invalid graph header: "+path);
    g.masks.resize(M);for(auto&m:g.masks)f>>m;
    for(int k=0;k<T;++k){Term t;f>>n;if(n<1||n>M)throw std::runtime_error("bad denominator size");t.ids.resize(n);for(auto&i:t.ids)f>>i;t.co.resize(g.E);for(auto&c:t.co)f>>c;g.terms.push_back(std::move(t));}
    f>>n;if(n!=(1<<g.E))throw std::runtime_error("invalid rate table");g.alpha.resize(n);for(auto&a:g.alpha)f>>a;
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
inline Eval evaluate(const Graph&g,const ld*lx,ld factor,Scratch&s) {
    ld shift=0;bool direct=true;for(int j=0;j<g.E;++j)if(lx[j]<-600||lx[j]>0)direct=false;
    if(!direct){shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld v=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;v+=lx[j];}shift=std::max(shift,v);}}
    bool moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
    auto v=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);
    if(!moderate){s.S=0;for(int j=0;j<g.E;++j)s.S+=expl(lx[j]);}
    ld ratio=absolute(v.first)/(v.second+1e-4900L);int lev=0;ld f=v.first;
    if(ratio<1e-9L){auto q=calculate_reference<Q>(g,lx,shift);lev=1;f=ld(q.first);if(absolute(q.first)<Q(1e-23L)*q.second){auto m=calculate_reference<MP>(g,lx,shift);f=m.first.convert_to<ld>();lev=2;}}
    ld y=f*expl(factor-shift)*g.Z;if(!std::isfinite(y))throw std::runtime_error("nonfinite integrand");return {y,lev};
}
inline std::array<ld,6> sample(const Graph&g,const ld*uu,int K,const std::array<ld,6>&logs,int&level,int layout,Scratch&s) {
    int E=g.E,S=(1<<E)-1;ld fac=0,ou=uu[0];
    for(int pos=0;pos<E;++pos){ld u=(layout==2?ou:uu[layout==0?2*pos:E-1+pos])*g.choice_total[S];int pick=-1;
        for(int j=0;j<E;++j)if(S>>j&1){u-=g.dp[S^(1<<j)];if(u<=0){pick=j;break;}}
        if(pick<0)pick=31-__builtin_clz(S);
        if(layout==2){ld pr=g.dp[S^(1<<pick)];ou=(u+pr)/pr;ou=std::max(0.L,std::min(nextafterl(1.L,0.L),ou));}
        s.order[pos]=pick;S^=1<<pick;
        if(S){int ix=layout==0?2*pos+1:(layout==2?pos+1:pos);ld l=logl(uu[ix])/g.alpha[S];s.lt[pos]=l;fac+=(__builtin_popcount(unsigned(S))/2.0L-g.alpha[S])*l;}}
    ld cur=0;for(int j=0;j<E;++j){s.lx[s.order[j]]=cur;if(j<E-1)cur+=s.lt[j];}
    auto v=evaluate(g,s.lx.data(),fac,s);level=v.level;std::array<ld,6>out{};out[0]=1;
    // At L=7 the unused logarithm and entire regulator recurrence disappear.
    if(K){ld sumlog=0;for(int j=0;j<E;++j)sumlog+=s.lx[j];ld z=sumlog/4-g.L/2.L*logl(s.S);
        for(int n=1;n<=K;++n){ld a=0;for(int j=1;j<=n;++j)a+=j*(logs[j]+(j==1?z:0))*out[n-j];out[n]=a/n;}}
    for(int j=0;j<=K;++j)out[j]*=v.y;return out;
}
