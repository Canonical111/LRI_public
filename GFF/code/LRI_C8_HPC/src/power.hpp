#pragma once
#include "common.hpp"
// The number of quadrature points still grows as (N+1)^(L-1).
// This implementation changes the storage/contraction order, NOT that quadrature rule.
// C8: the contraction is a template on the working type; T=long double is production, T=__float128 (--quad-bits 113)
// replays the identical rule on the identical long-double weights and nodes to measure contraction rounding.
struct SmallGrid{
 int L,D,N,nn,B;uint64_t NP=1;vector<LD>node,w;array<LD,NW>gamma{};array<LD,MAX_L+1>integer_iv{},integer_half_log{};array<LD,2*MAX_L*MAX_L+1>integer_log_h{};
 SmallGrid(int LL,int NN,const string&root):L(LL),D(L-1),N(NN),nn(N+1),B(2*L+1){
  require(D>=1&&D<=MAX_D,"loop order outside 2..8");
  for(int j=0;j<D;j++){require(NP<=numeric_limits<uint64_t>::max()/nn,"tensor grid size overflow");NP*=nn;}
  node.resize(nn);for(int i=0;i<nn;i++)node[i]=i==0?1:(i==N?0:(1+cosl(acosl(-1.L)*i/N))/2);
  if(N==1){for(int k=1;k<=L;k++){integer_iv[k]=1/sqrtl(LD(k));integer_half_log[k]=.5L*logl(LD(k));}for(int k=1;k<=2*L*L;k++)integer_log_h[k]=logl(LD(k));}
  // Layout (axis, exponent class b, slot r+1 for r=-1..NW-1, node i): NW+1 slots, the order-eight generator's M+2.
  w.resize(size_t(D)*B*(NW+1)*nn);string base=root+"/cw_L"+to_string(L)+"_N"+to_string(N);
  ifstream text(base+".txt");require(bool(text),"missing portable quadrature weights "+base+".txt (C8 uses order-eight weights only)");
  string magic;size_t count;text>>magic>>count;require(magic=="C8WEIGHTS1"&&count==w.size(),"invalid portable quadrature weights (need C8WEIGHTS1 with "+to_string(w.size())+" values)");for(auto&x:w)text>>x;require(bool(text),"truncated portable weights");
  string extra;require(!(text>>extra),"trailing data in portable weights");
  ifstream f(root+"/cgamma_L"+to_string(L)+".txt");for(auto&v:gamma)f>>v;require(bool(f),"missing Gamma coefficients");require(!(f>>extra),"Gamma file must hold exactly NW coefficients");
 }
 LD wt(int axis,int b,int r,int i)const{return w[(((size_t)axis*B+b)*(NW+1)+(r+1))*nn+i];}
};
struct GeoPlan{
 struct Pair{int lca,a,b;};array<Pair,MAX_E>pairs{};array<int,MAX_E>map{};
 GeoPlan(const TreeSample&s,int L){int pos[MAX_N],index[MAX_N][MAX_N];for(int i=0;i<=L;i++)pos[s.order[i]]=i;int k=0;
  for(int a=0;a<=L;a++)for(int b=a+1;b<=L;b++){index[a][b]=index[b][a]=k;int lca=MAX_L;for(int j=a;j<b;j++)lca=min(lca,s.gapnodes[j]);pairs[k++]={lca,a,b};}
  k=0;for(int a=0;a<=L;a++)for(int b=a+1;b<=L;b++)map[k++]=index[pos[a]][pos[b]];
 }
};
template<class T>struct PowerScratchT{
 size_t capacity;unique_ptr<T[]>mem;vector<unsigned char>first,logs_ready;vector<array<unsigned char,MAX_D>>idx;
 vector<array<T,NW>>sum,correction;
 explicit PowerScratchT(size_t mib):capacity(mib*1024*1024/sizeof(T)),mem(new T[capacity]){}
};
using PowerScratch=PowerScratchT<LD>;
template<class T>inline void compensated_add(T x,T&sum,T&corr){T t=sum+x;if(abst(sum)>=abst(x))corr+=(sum-t)+x;else corr+=(x-t)+sum;sum=t;}
template<class T>inline array<T,NW> quadrature(const Graph&g,const SmallGrid&grid,const TreeSample&s,const Options&o,PowerScratchT<T>&scratch,Profile&pro){
 constexpr bool native=is_same<T,LD>::value;
 int L=grid.L,D=L-1,NE=L*(L+1)/2,K=NW-L;GeoPlan geo(s,L);Key inside[MAX_D]={};
 for(int j=0;j<D;j++){int k=0,sub=s.clusters[j+1];for(int a=0;a<=L;a++)for(int b=a+1;b<=L;b++,k++)if((sub>>a&1)&&(sub>>b&1))inside[j]|=pair_bit(k);}
 vector<array<int,MAX_D>>signature;vector<int>which;map<array<int,MAX_D>,int>group;
 for(auto&t:g.terms){array<int,MAX_D>b{};for(int j=0;j<D;j++)b[j]=popc(t.key&inside[j])+2*popc((t.key>>1)&inside[j]);auto f=group.find(b);
  if(f==group.end()){int n=signature.size();signature.push_back(b);group[b]=n;which.push_back(n);}else which.push_back(f->second);}
 size_t ns=signature.size(),per_point=4*NE+NW*ns;
 size_t tile=min({o.tile,size_t(grid.NP),scratch.capacity/per_point});require(tile>0,"scratch budget too small for one point");
 T*dist=scratch.mem.get();T*iv=dist+tile*NE;T*q=iv+tile*NE;T*logs=q+tile*NE;T*weights=logs+tile*NE;
 scratch.first.resize(ns*tile);scratch.logs_ready.resize(tile);scratch.idx.resize(tile);scratch.sum.assign(g.terms.size(),{});scratch.correction.assign(g.terms.size(),{});
 size_t actual=per_point*tile*sizeof(T)+scratch.first.size()+scratch.logs_ready.size()+scratch.idx.size()*sizeof(scratch.idx[0])+2*g.terms.size()*sizeof(array<T,NW>);
 pro.scratch_peak=max(pro.scratch_peak,actual);
 for(uint64_t begin=0;begin<grid.NP;begin+=tile){size_t count=min(uint64_t(tile),grid.NP-begin);double t=o.profile?omp_get_wtime():0;
  for(size_t p=0;p<count;p++){
   uint64_t v=begin+p;for(int j=D-1;j>=0;j--){scratch.idx[p][j]=v%grid.nn;v/=grid.nn;}
   T ts[MAX_L],scale[MAX_L],relative[MAX_L][MAX_L]{};ts[0]=scale[0]=1;
   for(int j=1;j<L;j++){ts[j]=grid.node[scratch.idx[p][j-1]];scale[j]=scale[s.parents[j]]*ts[j];}
   // Each path product is computed in the original deepest-node-first order.
   for(int j=0;j<L;j++){int ancestor=j;T product=1;relative[j][j]=1;while(ancestor){product*=ts[ancestor];ancestor=s.parents[ancestor];relative[j][ancestor]=product;}}
   for(int e=0;e<NE;e++){auto pair=geo.pairs[e];T qq=0;for(int j=pair.a;j<pair.b;j++)qq+=relative[s.gapnodes[j]][pair.lca];size_t z=p*NE+e;q[z]=qq;dist[z]=scale[pair.lca]*qq;
    if constexpr(native)iv[z]=grid.N==1?grid.integer_iv[int(qq)]:1/sqrtl(qq);else iv[z]=1/sqrtt(qq);}
   scratch.logs_ready[p]=0;
  }
  if(o.profile){pro.geometry+=omp_get_wtime()-t;t=omp_get_wtime();}
  for(size_t gi=0;gi<ns;gi++)for(size_t p=0;p<count;p++){
   const auto&b=signature[gi];int start[MAX_D],nu=0;for(int j=0;j<D;j++){bool pole=grid.wt(L-s.sizes[j+1],b[j],-1,scratch.idx[p][j])!=0;start[j]=pole?-1:0;nu+=pole;}
   int deg=K+nu;auto&first=scratch.first[gi*tile+p];first=D-nu;T*w=weights+(gi*tile+p)*NW;
   if(deg==0){T val=1;for(int j=0;j<D;j++)val*=T(grid.wt(L-s.sizes[j+1],b[j],0,scratch.idx[p][j]));w[0]=val;continue;}
   T a[NW]={1};for(int j=0;j<D;j++){T bb[NW]={},vv[NW];for(int k=0;k<=deg;k++)vv[k]=T(grid.wt(L-s.sizes[j+1],b[j],start[j]+k,scratch.idx[p][j]));for(int k=0;k<=deg;k++)if(a[k]!=0)for(int r=0;k+r<=deg;r++)bb[k+r]+=a[k]*vv[r];copy(bb,bb+NW,a);}for(int k=0;k<=deg;k++)w[k]=a[k];
  }
  if(o.profile){pro.weights+=omp_get_wtime()-t;t=omp_get_wtime();}
  for(size_t ti=0;ti<g.terms.size();ti++){auto&tterm=g.terms[ti];int wi=which[ti];auto&sum=scratch.sum[ti];auto&corr=scratch.correction[ti];
   for(size_t p=0;p<count;p++){size_t z=p*NE;int first=scratch.first[wi*tile+p];const T*w=weights+(wi*tile+p)*NW;
    if(first<NW-1&&!scratch.logs_ready[p]){for(int e=0;e<NE;e++){if constexpr(native)logs[z+e]=grid.N==1?grid.integer_half_log[int(q[z+e])]:.5L*logl(q[z+e]);else logs[z+e]=logt(q[z+e])/2;}scratch.logs_ready[p]=1;}
    T H=0,R=0,base=1,lv=0;for(auto&e:tterm.e){int k=geo.map[e.k],m=e.m;H+=m*dist[z+k];R+=e.co*dist[z+k];T v=iv[z+k];if(m==1)base*=v;else if(m==2)base*=v*v;else base*=v*v*v;if(first<NW-1)lv+=m*logs[z+k];}
    if(R==0)continue;require(H>0,"zero H in quadrature");base*=R/H;
    if(first==NW-1){compensated_add<T>(base*w[0],sum[NW-1],corr[NW-1]);continue;}
    if constexpr(native)lv-=L*(grid.N==1?grid.integer_log_h[int(H)]:logl(H));else lv-=L*logt(H);
    T ep[NW];ep[0]=base;for(int j=1;j<NW-first;j++)ep[j]=ep[j-1]*lv/j;
    for(int a=first;a<NW;a++)for(int j=first;j<=a;j++)compensated_add<T>(w[j-first]*ep[a-j],sum[a],corr[a]);
   }
  }
  if(o.profile)pro.contract+=omp_get_wtime()-t;
 }
 array<T,NW>sum{},corr{},out{};for(size_t ti=0;ti<g.terms.size();ti++)for(int j=0;j<NW;j++){compensated_add<T>(scratch.sum[ti][j],sum[j],corr[j]);compensated_add<T>(scratch.correction[ti][j],sum[j],corr[j]);}for(int j=0;j<NW;j++)sum[j]+=corr[j];
 for(int j=0;j<NW;j++)for(int a=0;a<=j;a++)out[j]+=sum[a]*T(grid.gamma[j-a]);pro.nodes+=grid.NP;return out;
}
template<class T>inline Row run_power(const Options&o,const Work&w,const Graph&g,const TP&p,const SmallGrid&grid,PowerScratchT<T>&scratch,Profile&pro){
 Row row;double time0=omp_get_wtime();mt19937_64 rng(graph_seed(o.seed,w.rep,w.graph));
 require(w.begin<=numeric_limits<uint64_t>::max()/uint64_t(2*o.L-1),"RNG discard overflow");rng.discard(w.begin*(2*o.L-1));array<T,NW>sum{};
 for(uint64_t i=w.begin;i<w.end;i++){LD u[16];for(int j=0;j<2*o.L-1;j++)u[j]=((LD)(rng()>>12)+.5L)/4503599627370496.L;
  double t=o.profile?omp_get_wtime():0;auto s=draw_tree(p,u,false);if(o.profile)pro.draw+=omp_get_wtime()-t;
  LD weight=p.Z;for(int j=1;j<o.L;j++)weight*=s.alpha[j];auto val=quadrature<T>(g,grid,s,o,scratch,pro);
  for(int j=0;j<NW;j++){require(isfinite((LD)val[j]),"nonfinite quadrature");sum[j]+=T(weight)*val[j]/T(w.total);}
 }
 LD sign=o.L%2?1:-1;for(int j=0;j<NW;j++){row.v[j]=sign*g.wa*(LD)sum[j];row.v[NW+j]=sign*g.wb*(LD)sum[j];}row.seconds=omp_get_wtime()-time0;pro.n+=w.end-w.begin;return row;
}
// Exact mode: the row is the complete deterministic sum over the ordered trees [begin,end) of the catalog, each with
// its full tensor quadrature; weight 2 per reflection pair; no division by total (chunks add to the full-tree sum).
template<class T>inline Row run_exact(const Options&o,const Work&w,const Graph&g,const TreeCatalog&cat,const SmallGrid&grid,PowerScratchT<T>&scratch,Profile&pro){
 Row row;double time0=omp_get_wtime();require(w.rep==0,"exact mode has a single deterministic replicate 0");require(w.total==cat.size(),"exact work total must equal the number of ordered trees");
 array<T,NW>sum{},corr{};
 for(uint64_t i=w.begin;i<w.end;i++){auto s=cat.tree(i);auto val=quadrature<T>(g,grid,s,o,scratch,pro);
  for(int j=0;j<NW;j++){require(isfinite((LD)val[j]),"nonfinite quadrature");compensated_add<T>(T(2)*val[j],sum[j],corr[j]);}
 }
 for(int j=0;j<NW;j++)sum[j]+=corr[j];
 LD sign=o.L%2?1:-1;for(int j=0;j<NW;j++){row.v[j]=sign*g.wa*(LD)sum[j];row.v[NW+j]=sign*g.wb*(LD)sum[j];}row.seconds=omp_get_wtime()-time0;pro.n+=w.end-w.begin;return row;
}
