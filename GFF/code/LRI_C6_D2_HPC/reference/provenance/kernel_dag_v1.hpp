// Finite power-free forest kernels, with cancellation monitored and re-evaluated.
// Estimates the epsilon-dependent zero-momentum RG coefficients, NOT MS coefficients.
#include <bits/stdc++.h>
#include <quadmath.h>
#include <boost/multiprecision/cpp_dec_float.hpp>
#include <omp.h>
using namespace std;
#ifndef SPATIAL_D
#define SPATIAL_D 3
#endif
constexpr int D=SPATIAL_D;
#ifndef SINGLE_ORDER
#define SINGLE_ORDER 0
#endif
using ld=long double;using Q=__float128;using MP=boost::multiprecision::number<boost::multiprecision::cpp_dec_float<300>>;
struct Term{vector<int> ids;vector<int> co;};
struct Graph{int id,E,L;ld wa,wb,Z;vector<unsigned> masks;vector<Term>terms;vector<ld>alpha,dp;vector<pair<int,int>> prod_ops;vector<int>mon_ids;};
struct Eval{ld y;int level;};
template<class T>T expT(T x){return exp(x);}template<>Q expT(Q x){return expq(x);}template<class T>T absT(T x){return x<0?-x:x;}

template<class T>T sqrtT(T x){return sqrt(x);}template<>Q sqrtT(Q x){return sqrtq(x);}

template<class T>pair<T,T> calculate(const Graph&g,const vector<ld>&logx,ld shift){
 vector<T>x(g.E),mons(g.masks.size());T S=0;
 for(int j=0;j<g.E;j++){x[j]=expT(T(logx[j]));S+=x[j];}
 for(int i=0;i<(int)mons.size();i++){T ex=-T(shift);unsigned b=g.masks[i];while(b){int j=__builtin_ctz(b);b&=b-1;ex+=T(logx[j]);}mons[i]=expT(ex);}
 T val=0,err=0;
 for(const auto&t:g.terms){T U=0,n=0,na=0;for(int i:t.ids)U+=mons[i];for(int j=0;j<g.E;j++){T p=T(t.co[j])*x[j];n+=p;na+=absT(p);}T den= D==2 ? U : U*sqrtT(U);val+=n/den;err+=na/den;}
 return{val/S,err/S};
}
// Shared product DAG, retaining the previous extended-precision fallbacks.
pair<ld,ld> calculate_products(const Graph&g,const vector<ld>&logx,ld shift){
 vector<ld>x(g.E),xs(g.E),p(g.prod_ops.size()+1);p[0]=1;ld S=0;
 for(int j=0;j<g.E;j++){x[j]=expl(logx[j]);S+=x[j];xs[j]=expl(logx[j]-shift/g.L);}
 for(size_t j=0;j<g.prod_ops.size();j++){auto o=g.prod_ops[j];p[j+1]=p[o.first]*xs[o.second];}
 ld val=0,err=0;
 for(const auto&t:g.terms){ld U=0,n=0,na=0;for(int i:t.ids)U+=p[g.mon_ids[i]];
 for(int j=0;j<g.E;j++)if(t.co[j]){ld z=ld(t.co[j])*x[j];n+=z;na+=abs(z);}
 ld den=D==2?U:U*sqrtl(U);val+=n/den;err+=na/den;}
 return{val/S,err/S};
}
Eval evaluate(const Graph&g,const vector<ld>&logx,ld factor){
 ld shift=-numeric_limits<ld>::infinity();for(unsigned mask:g.masks){ld v=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;v+=logx[j];}shift=max(shift,v);}
 #ifdef FAST_INITIAL
 auto fast=calculate<double>(g,logx,shift);
 if(isfinite(fast.first)&&isfinite(fast.second)&&fabs(fast.first)>1e-2*fast.second){return{ld(fast.first)*expl(factor-(D/2.L)*shift)*g.Z,-1};}
 #endif
 bool moderate=true;for(ld x:logx)if(abs(x-shift/g.L)>500)moderate=false;
 #ifdef REFERENCE_EVAL
 auto v=calculate<ld>(g,logx,shift);
 #else
 auto v=moderate?calculate_products(g,logx,shift):calculate<ld>(g,logx,shift);
 #endif
ld ratio=abs(v.first)/(v.second+1e-4900L);int lev=0;ld f=v.first;
 if(ratio<1e-9L){auto q=calculate<Q>(g,logx,shift);lev=1;f=(ld)q.first;if(absT(q.first)<Q(1e-23L)*q.second){auto m=calculate<MP>(g,logx,shift);f=m.first.convert_to<ld>();lev=2;}}
 return{f*expl(factor-(D/2.L)*shift)*g.Z,lev};
}
vector<Graph> load(const string&file,const string&rate){
 ifstream in(file);int L,N;in>>L>>N;vector<Graph>gs;
 for(int z=0;z<N;z++){Graph g;int M,T;g.L=L;g.E=2*L;in>>g.id>>g.wa>>g.wb>>M>>T;int a,b;for(int i=0;i<g.E;i++)in>>a>>b;g.masks.resize(M);for(auto&m:g.masks)in>>m;
 for(int i=0;i<T;i++){Term t;int n;in>>n;t.ids.resize(n);for(auto&j:t.ids)in>>j;t.co.resize(g.E);for(auto&j:t.co)in>>j;g.terms.push_back(t);}gs.push_back(g);}
 ifstream ri(rate);int nn;ri>>nn;map<int,vector<ld>>rates;for(int n=0;n<nn;n++){int id,sz;ri>>id>>sz;vector<ld>a(sz);for(auto&v:a)ri>>v;rates[id]=a;}
 for(auto&g:gs){int sz=1<<g.E;g.alpha=rates.at(g.id);g.dp.assign(sz,0);g.dp[0]=1;for(int s=1;s<sz;s++){ld sum=0;for(int j=0;j<g.E;j++)if(s>>j&1)sum+=g.dp[s^(1<<j)];g.dp[s]=sum/(s==sz-1?1:g.alpha[s]);}g.Z=g.dp.back();
  vector<int> ind(1<<g.E,-1);ind[0]=0;
  function<int(unsigned)> get=[&](unsigned mask)->int{if(ind[mask]>=0)return ind[mask];int j=__builtin_ctz(mask);int prev=get(mask^(1u<<j));g.prod_ops.push_back({prev,j});return ind[mask]=int(g.prod_ops.size());};
  for(unsigned mask:g.masks){if(__builtin_popcount(mask)!=g.L)throw runtime_error("nonhomogeneous mask");g.mon_ids.push_back(get(mask));}
 }
 return gs;
}
ld uniform(mt19937_64&r){return (ld(r())+.5L)/18446744073709551616.0L;}
struct DigitalNet{
 int dim,bits,j=0; const uint64_t* directions; vector<uint64_t>state;
 DigitalNet(int dim_,int bits_,const uint64_t*dir,mt19937_64&r):dim(dim_),bits(bits_),directions(dir),state(dim_){for(auto&x:state)x=r()>>(64-bits);}
 void point(uint64_t i){j=0;if(i){int k=__builtin_ctzll(i);for(int a=0;a<dim;a++)state[a]^=directions[a*bits+k];}}
};
ld uniform(DigitalNet&r){if(r.j>=r.dim)throw runtime_error("digital net dimension exhausted");return (ld(r.state[r.j++])+.5L)/ld(uint64_t(1)<<r.bits);}
template<class RNG>vector<ld> sample(const Graph&g,RNG&r,int K,const vector<ld>&logs,int&level){
 int S=(1<<g.E)-1;vector<int>order;vector<ld>lt;ld fac=0;ld order_u=0;if(SINGLE_ORDER)order_u=uniform(r);
 for(int pos=0;pos<g.E;pos++){
  ld tot=0;for(int j=0;j<g.E;j++)if(S>>j&1)tot+=g.dp[S^(1<<j)];ld u=(SINGLE_ORDER?order_u:uniform(r))*tot;int pick=-1;
  for(int j=0;j<g.E;j++)if(S>>j&1){u-=g.dp[S^(1<<j)];if(u<=0){pick=j;break;}}
  if(pick<0)pick=31-__builtin_clz(S);if(SINGLE_ORDER){ld pr=g.dp[S^(1<<pick)];order_u=(u+pr)/pr;order_u=max(0.L,min(nextafterl(1.L,0.L),order_u));}order.push_back(pick);S^=1<<pick;
  if(S){ld l=logl(uniform(r))/g.alpha[S];lt.push_back(l);fac+=(D*__builtin_popcount((unsigned)S)/4.0L-g.alpha[S])*l;}
 }
 vector<ld>lx(g.E);ld cur=0;for(int j=0;j<g.E;j++){lx[order[j]]=cur;if(j<g.E-1)cur+=lt[j];}
 auto v=evaluate(g,lx,fac);level=v.level;
 ld sumlog=accumulate(lx.begin(),lx.end(),0.L);ld X=0;for(auto l:lx)X+=expl(l);ld s=sumlog/4-g.L/2.L*logl(X);
 vector<ld>ex(K+1,0);ex[0]=1;
 for(int n=1;n<=K;n++){ld val=0;for(int j=1;j<=n;j++)val+=j*(logs[j]+(j==1?s:0))*ex[n-j];ex[n]=val/n;}
 for(auto&x:ex)x*=v.y;return ex;
}
