#pragma once
#include "common.hpp"
// Literal original arithmetic, retained as an executable oracle (same types and thresholds).
template<class T>array<T,NW> point_oracle(const Graph&g,int L,int K,const TreeSample&s,LD*rat){
 T scales[MAX_L],gap[MAX_L];scales[0]=1;T weight=1;for(int j=1;j<L;j++){T tt=expt(T(s.lt[j]));scales[j]=scales[s.parents[j]]*tt;weight*=expt(T((s.sizes[j]-1-s.alpha[j])*s.lt[j]));}
 for(int j=0;j<L;j++)gap[j]=scales[s.gapnodes[j]];int sz=1<<L;T dist[1<<MAX_L]={},iv[MAX_E],logs[MAX_E];for(int mask=1;mask<sz;mask++){int bit=__builtin_ctz(unsigned(mask));dist[mask]=dist[mask^(1<<bit)]+gap[bit];}
 int NE=L*(L+1)/2;for(int k=0;k<NE;k++){iv[k]=1/sqrtt(dist[s.masks[k]]);logs[k]=logt(dist[s.masks[k]])/2;}array<T,NW>sum{};T absum[NW]={};
 for(auto&t:g.terms){T H=0,R=0,base=1,lv=0;for(auto&e:t.e){int k=e.k,m=e.m;H+=m*dist[s.masks[k]];R+=e.co*dist[s.masks[k]];T v=iv[k];if(m==1)base*=v;else if(m==2)base*=v*v;else base*=v*v*v;lv+=m*logs[k];}
 if(R==0)continue;base*=R/H;lv-=L*logt(H);for(int j=0;j<=K;j++){sum[j]+=base;absum[j]+=base<0?-base:base;base*=lv/(j+1);}}
 if(rat){*rat=1;for(int j=0;j<=K;j++)if(absum[j]>0)*rat=min(*rat,abs((LD)(sum[j]/absum[j])));}for(int j=0;j<=K;j++)sum[j]*=weight;return sum;
}
template<class T>struct PointScratch{vector<T>H,base,lv;void size(size_t n,bool logs){H.resize(n);base.resize(n);if(logs)lv.resize(n);}};
// A prefix trie shares only identical ordered multiplication/addition prefixes.
// No reassociation of the forest sum; K=0 never computes unused logarithms.
template<class T>array<T,NW> point_fast(const Graph&g,int L,int K,const TreeSample&s,LD*rat,PointScratch<T>&scratch){
 scratch.size(g.prefix.size(),K>0);T scales[MAX_L],gap[MAX_L];scales[0]=1;T weight=1;
 for(int j=1;j<L;j++){T tt=expt(T(s.lt[j]));scales[j]=scales[s.parents[j]]*tt;weight*=expt(T((s.sizes[j]-1-s.alpha[j])*s.lt[j]));}
 for(int j=0;j<L;j++)gap[j]=scales[s.gapnodes[j]];
 T dist[1<<MAX_L]={},iv[MAX_E],v2[MAX_E],v3[MAX_E],logs[MAX_E];int sz=1<<L;for(int mask=1;mask<sz;mask++){int bit=__builtin_ctz(unsigned(mask));dist[mask]=dist[mask^(1<<bit)]+gap[bit];}
 int NE=L*(L+1)/2;for(int k=0;k<NE;k++){iv[k]=1/sqrtt(dist[s.masks[k]]);v2[k]=iv[k]*iv[k];v3[k]=iv[k]*iv[k]*iv[k];if(K)logs[k]=logt(dist[s.masks[k]])/2;}
 auto&H=scratch.H;auto&B=scratch.base;auto&V=scratch.lv;H[0]=0;B[0]=1;if(K)V[0]=0;
 for(size_t i=1;i<g.prefix.size();i++){auto p=g.prefix[i];H[i]=H[p.parent]+p.m*dist[s.masks[p.k]];
  if(p.m==1)B[i]=B[p.parent]*iv[p.k];else if(p.m==2)B[i]=B[p.parent]*v2[p.k];else B[i]=B[p.parent]*v3[p.k];
  if(K)V[i]=V[p.parent]+p.m*logs[p.k];
 }
 array<T,NW>sum{};T absum[NW]={};
 for(auto&t:g.terms){T R=0;for(auto&e:t.e)R+=e.co*dist[s.masks[e.k]];if(R==0)continue;T base=B[t.leaf];base*=R/H[t.leaf];T lv=0;if(K){lv=V[t.leaf];lv-=L*logt(H[t.leaf]);}
  for(int j=0;j<=K;j++){sum[j]+=base;absum[j]+=base<0?-base:base;if(j<K)base*=lv/(j+1);}
 }
 if(rat){*rat=1;for(int j=0;j<=K;j++)if(absum[j]>0)*rat=min(*rat,abs((LD)(sum[j]/absum[j])));}for(int j=0;j<=K;j++)sum[j]*=weight;return sum;
}
struct Net{
 int dim=0,bits=0,B=0;vector<vector<uint64_t>>directions;map<int,int>slot;
 Net(const string&path,const vector<Work>&works,int L){
  ifstream f(path,ios::binary);uint32_t h[3];f.read((char*)h,12);require(bool(f),"cannot read Sobol header");
  B=h[0];dim=h[1];bits=h[2];require(B>0&&dim>=2*L-1&&dim<=16&&bits>=1&&bits<=63,"unsupported Sobol dimensions/bits");
  require(filesystem::file_size(path)==12+uint64_t(B)*dim*bits*8,"Sobol file size mismatch");
  uint16_t endian=1;require(*(unsigned char*)&endian==1,"Sobol file requires little endian (convert on this platform)");
  set<int>needed;for(auto&w:works){require(w.rep<B,"replicate outside Sobol file");require((w.total&(w.total-1))==0&&w.total<=(1ULL<<bits),"QMC total must be a power of two within direction bit depth");needed.insert(w.rep);}
  for(int r:needed){slot[r]=directions.size();directions.emplace_back(dim*bits);f.seekg(12+uint64_t(r)*dim*bits*8);f.read((char*)directions.back().data(),dim*bits*8);require(bool(f),"truncated Sobol directions");}
 }
 const vector<uint64_t>&at(int r)const{return directions.at(slot.at(r));}
};
inline Row run_qmc(const Options&o,const Work&w,const Graph&g,const TP&p,const Net&net,const array<LD,NW>&gam,Profile&pro,PointScratch<LD>&sl,PointScratch<__float128>&sq,PointScratch<MP>&sm){
 Row row;double time0=omp_get_wtime();int L=o.L,K=NW-L,dim=net.dim,bits=net.bits;const auto&dir=net.at(w.rep);mt19937_64 rng(graph_seed(o.seed,w.rep,w.graph));
 array<uint64_t,16>state{};for(int j=0;j<dim;j++)state[j]=rng()&((1ULL<<bits)-1);
 // Reconstruct the exact original point at arbitrary global sample index via its Gray code.
 uint64_t gray=w.begin^(w.begin>>1);for(int b=0;b<bits;b++)if(gray>>b&1)for(int j=0;j<dim;j++)state[j]^=dir[j*bits+b];
 array<LD,NW>tot{};LD den=ldexpl(1.L,bits);for(uint64_t it=w.begin;it<w.end;it++){
  if(it>w.begin){int bit=__builtin_ctzll(it);for(int j=0;j<dim;j++)state[j]^=dir[j*bits+bit];}
  LD u[16];for(int j=0;j<dim;j++)u[j]=((LD)state[j]+.5L)/den;double t=o.profile?omp_get_wtime():0;
  auto s=draw_tree(p,u);if(o.profile){pro.draw+=omp_get_wtime()-t;t=omp_get_wtime();}
  LD ratio;auto val=o.oracle?point_oracle<LD>(g,L,K,s,&ratio):point_fast<LD>(g,L,K,s,&ratio,sl);if(o.profile)pro.point+=omp_get_wtime()-t;
  bool finite=true;for(int j=0;j<=K;j++)finite&=isfinite(val[j]);
  if(ratio<1e-7L||!finite){row.nquad++;t=o.profile?omp_get_wtime():0;auto q=o.oracle?point_oracle<__float128>(g,L,K,s,&ratio):point_fast<__float128>(g,L,K,s,&ratio,sq);
   for(int k=0;k<=K;k++)val[k]=(LD)q[k];if(o.profile)pro.quad+=omp_get_wtime()-t;
   finite=true;for(int j=0;j<=K;j++)finite&=isfinite(val[j]);
   if(ratio<1e-24L||!finite){row.nmp++;t=o.profile?omp_get_wtime():0;auto m=o.oracle?point_oracle<MP>(g,L,K,s,nullptr):point_fast<MP>(g,L,K,s,nullptr,sm);for(int k=0;k<=K;k++)val[k]=(LD)m[k];if(o.profile)pro.mp+=omp_get_wtime()-t;}
  }
  for(int j=0;j<=K;j++){require(isfinite(val[j]),"nonfinite point after precision fallback");tot[j]+=val[j]/w.total;}
 }
 LD sign=L%2?1:-1;for(int k=0;k<=K;k++){LD v=0;for(int j=0;j<=k;j++)v+=tot[j]*gam[k-j];int i=L-1+k;row.v[i]=sign*p.Z*g.wa*v;row.v[NW+i]=sign*p.Z*g.wb*v;}
 row.seconds=omp_get_wtime()-time0;pro.n+=w.end-w.begin;pro.nquad+=row.nquad;pro.nmp+=row.nmp;return row;
}
