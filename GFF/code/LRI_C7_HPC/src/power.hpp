#pragma once
#include "common.hpp"
// The number of quadrature points still grows as (N+1)^(L-1).
// This implementation changes the storage/contraction order, NOT that quadrature rule.
struct SmallGrid{
 int L,D,N,nn,B;uint64_t NP=1;vector<LD>node,w;array<LD,7>gamma{};array<LD,8>integer_iv{},integer_half_log{};array<LD,99>integer_log_h{};
 SmallGrid(int LL,int NN,const string&root):L(LL),D(L-1),N(NN),nn(N+1),B(2*L+1){
  for(int j=0;j<D;j++){require(NP<=numeric_limits<uint64_t>::max()/nn,"tensor grid size overflow");NP*=nn;}
  node.resize(nn);for(int i=0;i<nn;i++)node[i]=i==0?1:(i==N?0:(1+cosl(acosl(-1.L)*i/N))/2);
  if(N==1){for(int k=1;k<=L;k++){integer_iv[k]=1/sqrtl(LD(k));integer_half_log[k]=.5L*logl(LD(k));}for(int k=1;k<=2*L*L;k++)integer_log_h[k]=logl(LD(k));}
  w.resize(size_t(D)*B*8*nn);string base=root+"/cw_L"+to_string(L)+"_N"+to_string(N);
  ifstream text(base+".txt");if(text){string magic;size_t count;text>>magic>>count;require(magic=="C7WEIGHTS1"&&count==w.size(),"invalid portable quadrature weights");for(auto&x:w)text>>x;require(bool(text),"truncated portable weights");}
  else{
   uint16_t endian=1;require(sizeof(LD)==16&&numeric_limits<LD>::digits==64&&*(unsigned char*)&endian==1,"native weights are x86 extended precision; generate portable weights first");
   ifstream f(base+".bin",ios::binary);require(f&&filesystem::file_size(base+".bin")==w.size()*sizeof(LD),"missing or wrong-sized quadrature weights");f.read((char*)w.data(),w.size()*sizeof(LD));require(bool(f),"quadrature weights read failure");
  }
  ifstream f(root+"/cgamma_L"+to_string(L)+".txt");for(auto&v:gamma)f>>v;require(bool(f),"missing Gamma coefficients");
 }
 LD wt(int axis,int b,int r,int i)const{return w[(((size_t)axis*B+b)*8+(r+1))*nn+i];}
};
struct GeoPlan{
 struct Pair{int lca,a,b;};array<Pair,28>pairs{};array<int,28>map{};
 GeoPlan(const TreeSample&s,int L){int pos[8],index[8][8];for(int i=0;i<=L;i++)pos[s.order[i]]=i;int k=0;
  for(int a=0;a<=L;a++)for(int b=a+1;b<=L;b++){index[a][b]=index[b][a]=k;int lca=8;for(int j=a;j<b;j++)lca=min(lca,s.gapnodes[j]);pairs[k++]={lca,a,b};}
  k=0;for(int a=0;a<=L;a++)for(int b=a+1;b<=L;b++)map[k++]=index[pos[a]][pos[b]];
 }
};
struct PowerScratch{
 size_t capacity;unique_ptr<LD[]>mem;vector<unsigned char>first,logs_ready;vector<array<unsigned char,6>>idx;
 vector<array<LD,7>>sum,correction;
 explicit PowerScratch(size_t mib):capacity(mib*1024*1024/sizeof(LD)),mem(new LD[capacity]){}
};
inline void compensated_add(LD x,LD&sum,LD&corr){LD t=sum+x;if(abs(sum)>=abs(x))corr+=(sum-t)+x;else corr+=(x-t)+sum;sum=t;}
inline array<LD,7> quadrature(const Graph&g,const SmallGrid&grid,const TreeSample&s,const Options&o,PowerScratch&scratch,Profile&pro){
 int L=grid.L,D=L-1,NE=L*(L+1)/2,K=7-L;GeoPlan geo(s,L);uint64_t inside[6]={};
 for(int j=0;j<D;j++){int k=0,sub=s.clusters[j+1];for(int a=0;a<=L;a++)for(int b=a+1;b<=L;b++,k++)if((sub>>a&1)&&(sub>>b&1))inside[j]|=1ULL<<(2*k);}
 vector<array<int,6>>signature;vector<int>which;map<array<int,6>,int>group;
 for(auto&t:g.terms){array<int,6>b{};for(int j=0;j<D;j++)b[j]=__builtin_popcountll(t.key&inside[j])+2*__builtin_popcountll((t.key>>1)&inside[j]);auto f=group.find(b);
  if(f==group.end()){int n=signature.size();signature.push_back(b);group[b]=n;which.push_back(n);}else which.push_back(f->second);}
 size_t ns=signature.size(),per_point=4*NE+7*ns;
 size_t tile=min({o.tile,size_t(grid.NP),scratch.capacity/per_point});require(tile>0,"scratch budget too small for one point");
 LD*dist=scratch.mem.get();LD*iv=dist+tile*NE;LD*q=iv+tile*NE;LD*logs=q+tile*NE;LD*weights=logs+tile*NE;
 scratch.first.resize(ns*tile);scratch.logs_ready.resize(tile);scratch.idx.resize(tile);scratch.sum.assign(g.terms.size(),{});scratch.correction.assign(g.terms.size(),{});
 size_t actual=per_point*tile*sizeof(LD)+scratch.first.size()+scratch.logs_ready.size()+scratch.idx.size()*sizeof(scratch.idx[0])+2*g.terms.size()*sizeof(array<LD,7>);
 pro.scratch_peak=max(pro.scratch_peak,actual);
 for(uint64_t begin=0;begin<grid.NP;begin+=tile){size_t count=min(uint64_t(tile),grid.NP-begin);double t=o.profile?omp_get_wtime():0;
  for(size_t p=0;p<count;p++){
   uint64_t v=begin+p;for(int j=D-1;j>=0;j--){scratch.idx[p][j]=v%grid.nn;v/=grid.nn;}
   LD ts[7],scale[7],relative[7][7]{};ts[0]=scale[0]=1;
   for(int j=1;j<L;j++){ts[j]=grid.node[scratch.idx[p][j-1]];scale[j]=scale[s.parents[j]]*ts[j];}
   // Each path product is computed in the original deepest-node-first order.
   for(int j=0;j<L;j++){int ancestor=j;LD product=1;relative[j][j]=1;while(ancestor){product*=ts[ancestor];ancestor=s.parents[ancestor];relative[j][ancestor]=product;}}
   for(int e=0;e<NE;e++){auto pair=geo.pairs[e];LD qq=0;for(int j=pair.a;j<pair.b;j++)qq+=relative[s.gapnodes[j]][pair.lca];size_t z=p*NE+e;q[z]=qq;dist[z]=scale[pair.lca]*qq;iv[z]=grid.N==1?grid.integer_iv[int(qq)]:1/sqrtl(qq);}
   scratch.logs_ready[p]=0;
  }
  if(o.profile){pro.geometry+=omp_get_wtime()-t;t=omp_get_wtime();}
  for(size_t gi=0;gi<ns;gi++)for(size_t p=0;p<count;p++){
   const auto&b=signature[gi];int start[6],nu=0;for(int j=0;j<D;j++){bool pole=grid.wt(L-s.sizes[j+1],b[j],-1,scratch.idx[p][j])!=0;start[j]=pole?-1:0;nu+=pole;}
   int deg=K+nu;auto&first=scratch.first[gi*tile+p];first=D-nu;LD*w=weights+(gi*tile+p)*7;
   if(deg==0){LD val=1;for(int j=0;j<D;j++)val*=grid.wt(L-s.sizes[j+1],b[j],0,scratch.idx[p][j]);w[0]=val;continue;}
   LD a[7]={1};for(int j=0;j<D;j++){LD bb[7]={},vv[7];for(int k=0;k<=deg;k++)vv[k]=grid.wt(L-s.sizes[j+1],b[j],start[j]+k,scratch.idx[p][j]);for(int k=0;k<=deg;k++)if(a[k])for(int r=0;k+r<=deg;r++)bb[k+r]+=a[k]*vv[r];copy(bb,bb+7,a);}for(int k=0;k<=deg;k++)w[k]=a[k];
  }
  if(o.profile){pro.weights+=omp_get_wtime()-t;t=omp_get_wtime();}
  for(size_t ti=0;ti<g.terms.size();ti++){auto&tterm=g.terms[ti];int wi=which[ti];auto&sum=scratch.sum[ti];auto&corr=scratch.correction[ti];
   for(size_t p=0;p<count;p++){size_t z=p*NE;int first=scratch.first[wi*tile+p];const LD*w=weights+(wi*tile+p)*7;
    if(first<6&&!scratch.logs_ready[p]){for(int e=0;e<NE;e++)logs[z+e]=grid.N==1?grid.integer_half_log[int(q[z+e])]:.5L*logl(q[z+e]);scratch.logs_ready[p]=1;}
    LD H=0,R=0,base=1,lv=0;for(auto&e:tterm.e){int k=geo.map[e.k],m=e.m;H+=m*dist[z+k];R+=e.co*dist[z+k];LD v=iv[z+k];if(m==1)base*=v;else if(m==2)base*=v*v;else base*=v*v*v;if(first<6)lv+=m*logs[z+k];}
    if(R==0)continue;require(H>0,"zero H in quadrature");base*=R/H;
    if(first==6){compensated_add(base*w[0],sum[6],corr[6]);continue;}
    lv-=L*(grid.N==1?grid.integer_log_h[int(H)]:logl(H));LD ep[7];ep[0]=base;for(int j=1;j<7-first;j++)ep[j]=ep[j-1]*lv/j;
    for(int a=first;a<7;a++)for(int j=first;j<=a;j++)compensated_add(w[j-first]*ep[a-j],sum[a],corr[a]);
   }
  }
  if(o.profile)pro.contract+=omp_get_wtime()-t;
 }
 array<LD,7>sum{},corr{},out{};for(size_t ti=0;ti<g.terms.size();ti++)for(int j=0;j<7;j++){compensated_add(scratch.sum[ti][j],sum[j],corr[j]);compensated_add(scratch.correction[ti][j],sum[j],corr[j]);}for(int j=0;j<7;j++)sum[j]+=corr[j];
 for(int j=0;j<7;j++)for(int a=0;a<=j;a++)out[j]+=sum[a]*grid.gamma[j-a];pro.nodes+=grid.NP;return out;
}
inline Row run_power(const Options&o,const Work&w,const Graph&g,const TP&p,const SmallGrid&grid,PowerScratch&scratch,Profile&pro){
 Row row;double time0=omp_get_wtime();mt19937_64 rng(graph_seed(o.seed,w.rep,w.graph));
 require(w.begin<=numeric_limits<uint64_t>::max()/uint64_t(2*o.L-1),"RNG discard overflow");rng.discard(w.begin*(2*o.L-1));array<LD,7>sum{};
 for(uint64_t i=w.begin;i<w.end;i++){LD u[16];for(int j=0;j<2*o.L-1;j++)u[j]=((LD)(rng()>>12)+.5L)/4503599627370496.L;
  double t=o.profile?omp_get_wtime():0;auto s=draw_tree(p,u,false);if(o.profile)pro.draw+=omp_get_wtime()-t;
  LD weight=p.Z;for(int j=1;j<o.L;j++)weight*=s.alpha[j];auto val=quadrature(g,grid,s,o,scratch,pro);
  for(int j=0;j<7;j++){require(isfinite(val[j]),"nonfinite quadrature");sum[j]+=weight*val[j]/w.total;}
 }
 LD sign=o.L%2?1:-1;for(int j=0;j<7;j++){row.v[j]=sign*g.wa*sum[j];row.v[7+j]=sign*g.wb*sum[j];}row.seconds=omp_get_wtime()-time0;pro.n+=w.end-w.begin;return row;
}
