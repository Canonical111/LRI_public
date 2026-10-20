#include <bits/stdc++.h>
#include <omp.h>
#include "quad_support.hpp"
using namespace std;
const int M=6, NW=7;
struct Term{uint64_t key;array<unsigned char,28>m{};array<int,28>co{};};
struct Graph{int id,power,primitive;LD wa,wb;vector<Term>terms;};
struct Grid{
 int L,D,N,nn,NP,B;vector<array<unsigned char,6>>idx;vector<LD>dist,pow1,logs,w,gamma;
 Grid(int LL,int NN,string root,bool build_distance=true):L(LL),D(L-1),N(NN),nn(N+1),NP(1),B(2*L+1){
  for(int j=0;j<D;j++)NP*=nn;idx.resize(NP);int sz=1<<L;if(build_distance){dist.resize((size_t)NP*sz);pow1.resize((size_t)NP*sz);logs.resize((size_t)NP*sz);}
  #pragma omp parallel for num_threads(4)
  for(int p=0;p<NP;p++){if(!build_distance){int v=p;for(int j=D-1;j>=0;j--){idx[p][j]=v%nn;v/=nn;}continue;}int v=p;LD t[6],g[7];g[0]=1;for(int j=D-1;j>=0;j--){idx[p][j]=v%nn;v/=nn;t[j]=(1+cosq(acosq(-1.L)*idx[p][j]/N))/2;if(idx[p][j]==N)t[j]=0;if(idx[p][j]==0)t[j]=1;}for(int j=1;j<L;j++)g[j]=g[j-1]*t[j-1];
   for(int mask=1;mask<sz;mask++){int r=__builtin_ctz(mask);LD q=1,z=1;for(int j=r+1;j<L;j++){z*=t[j-1];if(mask>>j&1)q+=z;}size_t k=(size_t)p*sz+mask;dist[k]=g[r]*q;pow1[k]=1/sqrtq(q);logs[k]=.5L*logq(q);}
  }
  w.resize((size_t)D*B*(M+2)*nn);ifstream in(root+"/cw_L"+to_string(L)+"_N"+to_string(N)+".bin",ios::binary);vector<long double>tmp(w.size());in.read((char*)tmp.data(),tmp.size()*sizeof(long double));for(size_t i=0;i<w.size();i++)w[i]=tmp[i];if(!in)throw runtime_error("missing weights");
  gamma.resize(NW);ifstream gi(root+"/cgamma_L"+to_string(L)+".txt");for(auto&g:gamma)gi>>g;if(!gi)throw runtime_error("gamma file");
 }
 LD wt(int j,int b,int r,int i)const{return w[(((size_t)j*B+b)*(M+2)+(r+1))*nn+i];}
};
struct Weights {vector<LD>v;vector<unsigned char>first;};
struct Cache {
 const Grid&g;unordered_map<uint64_t,shared_ptr<Weights>>cache;deque<uint64_t>fifo;size_t bytes=0;long long misses=0;
 Cache(const Grid&gg):g(gg){}
 shared_ptr<Weights>get(const array<int,6>&b){uint64_t key=0;for(int j=0;j<g.D;j++)key|=uint64_t(b[j])<<(4*j);auto it=cache.find(key);if(it!=cache.end())return it->second;
  auto out=make_shared<Weights>();out->v.resize((size_t)g.NP*NW);out->first.resize(g.NP);int K=7-g.L;
  for(int p=0;p<g.NP;p++){
   LD a[16]={};a[7]=1;
   for(int j=0;j<g.D;j++){LD bb[16]={};for(int k=-j;k<=K+g.D-j;k++)if(a[7+k])for(int r=-1;r<=M;r++){int h=k+r;if(h>=-j-1&&h<=K+g.D-j-1)bb[7+h]+=a[7+k]*g.wt(j,b[j],r,g.idx[p][j]);}copy(bb,bb+16,a);}
   int first=NW-1;for(int i=0;i<NW;i++)out->v[(size_t)p*NW+i]=a[7-g.D+i];for(int i=0;i<NW;i++)if(out->v[(size_t)p*NW+i]){first=i;break;}out->first[p]=first;
  }
  size_t now=out->v.size()*sizeof(LD)+out->first.size();while(bytes+now>256*1024*1024ULL&&!fifo.empty()){auto k=fifo.front();fifo.pop_front();auto z=cache.find(k);bytes-=z->second->v.size()*sizeof(LD)+z->second->first.size();cache.erase(z);}bytes+=now;fifo.push_back(key);cache[key]=out;misses++;return out;
 }
};
vector<Graph>load(string path,int&L){ifstream in(path);int ng;in>>L>>ng;int NE=L*(L+1)/2;vector<Graph>gs(ng);for(auto&g:gs){int nt;in>>g.id>>g.wa>>g.wb>>g.power>>g.primitive>>nt;g.terms.resize(nt);for(auto&t:g.terms){in>>t.key;for(int k=0;k<NE;k++){t.m[k]=(t.key>>(2*k))&3;in>>t.co[k];}}}if(!in)throw runtime_error("kernel input");return gs;}
array<LD,NW>evaluate(const Graph&g,const Grid&grid,Cache&cache,const array<unsigned char,8>&vp,const array<unsigned char,8>&gp){
 int L=grid.L,D=L-1,n=L+1,NE=n*(n-1)/2,sz=1<<L;int pos[8],rank[7];for(int j=0;j<n;j++)pos[vp[j]]=j;for(int j=0;j<L;j++)rank[gp[j]]=j;
 int masks[28],mins[28];int k=0;for(int a=0;a<n;a++)for(int b=a+1;b<n;b++){int lo=min(pos[a],pos[b]),hi=max(pos[a],pos[b]),mask=0;for(int j=lo;j<hi;j++)mask|=1<<rank[j];masks[k]=mask;mins[k]=__builtin_ctz(mask);k++;}
 array<LD,NW>total{};
 for(const auto&t:g.terms){array<int,6>b{};vector<int>nz;for(int e=0;e<NE;e++)if(t.m[e]){nz.push_back(e);for(int j=0;j<mins[e];j++)b[j]+=t.m[e];}
  auto ww=cache.get(b);
  for(int p=0;p<grid.NP;p++){
   auto*pp=&grid.pow1[(size_t)p*sz];auto*dd=&grid.dist[(size_t)p*sz];auto*ll=&grid.logs[(size_t)p*sz];LD H=0,R=0,base=1,logv=0;
   for(int e:nz){int m=t.m[e],mask=masks[e];H+=m*dd[mask];R+=t.co[e]*dd[mask];LD v=pp[mask];if(m==1)base*=v;else if(m==2)base*=v*v;else base*=v*v*v;logv+=m*ll[mask];}
   if(!R)continue;if(!(H>0))throw runtime_error("bad H");base*=R/H;int first=ww->first[p];auto*w=&ww->v[(size_t)p*NW];
   if(first==NW-1){total[NW-1]+=base*w[NW-1];continue;}
   logv-=L*logq(H);LD ep[NW];ep[0]=base;for(int j=1;j<NW-first;j++)ep[j]=ep[j-1]*logv/j;
   for(int a=first;a<NW;a++){LD z=0;for(int j=first;j<=a;j++)z+=w[j]*ep[a-j];total[a]+=z;}
  }
 }
 array<LD,NW>out{};for(int j=0;j<NW;j++)for(int a=0;a<=j;a++)out[j]+=total[a]*grid.gamma[j-a];return out;
}
vector<array<unsigned char,8>> perms(int n,bool reflect){vector<array<unsigned char,8>>out;array<unsigned char,8>a{};iota(a.begin(),a.begin()+n,0);do{if(!reflect||a[0]<a[n-1])out.push_back(a);}while(next_permutation(a.begin(),a.begin()+n));return out;}
int main(int argc,char**argv){try{
 if(argc<8){cerr<<"root L degree samples_per_graph replicates seed output [selection:all,power,free] [exact]\n";return 1;}
 string root=argv[1];int L=stoi(argv[2]),N=stoi(argv[3]),ns=stoi(argv[4]),B=stoi(argv[5]);uint64_t seed=stoull(argv[6]);string output=argv[7],sel=argc>8?argv[8]:"all";bool exact=argc>9&&string(argv[9])=="exact";
 int Li;auto gs=load(root+"/L"+to_string(L)+"_coord.txt",Li);if(L!=Li)throw runtime_error("L mismatch");Grid grid(L,N,root);auto vps=perms(L+1,true),gps=perms(L,false);
 LD norm=(L%2)?1:-1;for(int i=2;i<=L+1;i++)norm*=i;for(int i=2;i<=L;i++)norm*=i;
 vector<vector<LD>>batches(B,vector<LD>(2*NW));vector<vector<array<LD,2*NW>>>per(B,vector<array<LD,2*NW>>(gs.size()));vector<long long>misses(B);double start=omp_get_wtime();
 #pragma omp parallel num_threads(4)
 {
  Cache cache(grid);
  #pragma omp for schedule(dynamic)
  for(int ib=0;ib<B;ib++){
   for(int gi=0;gi<(int)gs.size();gi++){
    const auto&g=gs[gi];if((sel=="power"&&!g.power)||(sel=="free"&&g.power))continue;if(L==7&&3*g.wb==g.wa)continue;
    mt19937_64 rng(seed+0x9e3779b97f4a7c15ULL*(ib+1)+0xbf58476d1ce4e5b9ULL*(gi+1));array<LD,NW>sum{};int count=exact?int(vps.size()*gps.size()):ns;
    for(int s=0;s<count;s++){int vi=exact?s/int(gps.size()):rng()%vps.size();int pi=exact?s%int(gps.size()):rng()%gps.size();auto val=evaluate(g,grid,cache,vps[vi],gps[pi]);for(int j=0;j<NW;j++)sum[j]+=val[j]/count;}
    for(int j=0;j<NW;j++){per[ib][gi][j]=norm*g.wa*sum[j];per[ib][gi][NW+j]=norm*g.wb*sum[j];batches[ib][j]+=per[ib][gi][j];batches[ib][NW+j]+=per[ib][gi][NW+j];}
   }
   misses[ib]=cache.misses;
   #pragma omp critical
   cerr<<"rep "<<ib<<" elapsed "<<omp_get_wtime()-start<<" finite b "<<setprecision(16)<<batches[ib][L-1]<<" c "<<batches[ib][NW+L-1]<<"\n";
  }
 }
 double sec=omp_get_wtime()-start;ofstream out(output);out<<setprecision(24)<<"{\"L\":"<<L<<",\"N\":"<<N<<",\"samples_per_graph\":"<<ns<<",\"replicates\":"<<B<<",\"seed\":"<<seed<<",\"min_power\":"<<1-L<<",\"max_power\":"<<7-L<<",\"selection\":\""<<sel<<"\",\"exact_permutations\":"<<(exact?"true":"false")<<",\"seconds\":"<<sec<<",\"batches\":[";
 for(int b=0;b<B;b++){if(b)out<<',';out<<'[';for(int j=0;j<2*NW;j++){if(j)out<<',';out<<batches[b][j];}out<<']';}out<<"],\"graph_batches\":[";
 for(int b=0;b<B;b++){if(b)out<<',';out<<'[';for(int gi=0;gi<(int)gs.size();gi++){if(gi)out<<',';out<<'[';for(int j=0;j<2*NW;j++){if(j)out<<',';out<<per[b][gi][j];}out<<']';}out<<']';}out<<"]}\n";
 }catch(exception&e){cerr<<e.what()<<'\n';return 2;}}
