// c6sum: deterministic ordered-sector spectral quadrature for the 1D long-range Ising Laurent amplitudes
// (L=6 H mode: six-loop simple pole H6; L=5 H/J modes: five-loop poles and J5). Derived from reference/full.cpp.
// Builds: default = 8-lane double as two AVX2 halves (portable, AMD and Intel); -DC6_AVX512 = one AVX-512 register
// (Intel only, bitwise identical); -DC6_REFERENCE = scalar long double. Derived from reference/full.cpp:
// same graphs, weights, sector enumeration, group/left-right factorization and Laurent recursion. Changes:
//  - the per-(group, 8-point block) weight tensor is computed on the fly (no cache): memory O(points);
//  - each block's contribution is accumulated with TwoSum compensation over groups (and optionally over graph
//    terms, --comp 2), lane-reduced in long double and stored; blocks are reduced in index order with a compensated
//    long-double sum. The result is bitwise independent of thread count, scheduling and sector splitting;
//  - sector ranges, JSONL output with a provenance header, resume after interruption;
//  - --stratum hard|light (reference/full_hard.cpp filter and its complement), --perturb SEED (+-1 ulp of every
//    nonzero node datum and weight);
//  - -DC6_REFERENCE builds a scalar long-double version (weights from the double-double file) for rounding checks.
// No physical coefficient is an input.
#include <bits/stdc++.h>
#include <omp.h>
#include <unistd.h>
#ifndef C6_REFERENCE
#include <immintrin.h>
#endif
using namespace std;
using LD=long double;
#ifndef C6_GIT_SHA
#define C6_GIT_SHA "unknown"
#endif
#ifndef C6_SRC_SHA
#define C6_SRC_SHA "unknown"
#endif

#ifdef C6_REFERENCE
using R=long double;using V=long double;constexpr int LANES=1;static const char*KIND="reference-longdouble";
static inline V vzero(){return 0;}static inline V vset1(R x){return x;}static inline V vadd(V a,V b){return a+b;}
static inline V vsub(V a,V b){return a-b;}static inline V vmul(V a,V b){return a*b;}static inline V vfma(V a,V b,V c){return a*b+c;}
static inline V vload(const R*p){return *p;}static inline void vstore(R*p,V a){*p=a;}
static inline V vgather(const R*base,const int*idx){return base[idx[0]];}
static inline R rcos(R x){return cosl(x);}static inline R rlog(R x){return logl(x);}static inline R rsqrt(R x){return sqrtl(x);}static inline R rpi(){return acosl(-1.0L);}
#elif defined(C6_AVX512)
// 8-lane double, one AVX-512 register (Intel only).
using R=double;using V=__m512d;constexpr int LANES=8;static const char*KIND="double8";
static inline V vzero(){return _mm512_setzero_pd();}static inline V vset1(R x){return _mm512_set1_pd(x);}
static inline V vadd(V a,V b){return _mm512_add_pd(a,b);}static inline V vsub(V a,V b){return _mm512_sub_pd(a,b);}
static inline V vmul(V a,V b){return _mm512_mul_pd(a,b);}static inline V vfma(V a,V b,V c){return _mm512_fmadd_pd(a,b,c);}
static inline V vload(const R*p){return _mm512_loadu_pd(p);}static inline void vstore(R*p,V a){_mm512_storeu_pd(p,a);}
static inline V vgather(const R*base,const int*idx){return _mm512_i32gather_pd(_mm256_loadu_si256((const __m256i*)idx),base,8);}
static inline R rcos(R x){return cos(x);}static inline R rlog(R x){return log(x);}static inline R rsqrt(R x){return sqrt(x);}static inline R rpi(){return acos(-1.);}
#else
// 8-lane double as two AVX2 halves (portable: AMD and Intel). Every lane undergoes exactly the same IEEE operations
// (add, sub, mul, fused multiply-add, gather) as in the AVX-512 build, so the results are bitwise identical to it.
struct V{__m256d lo,hi;};
using R=double;constexpr int LANES=8;static const char*KIND="double8";
static inline V vzero(){return {_mm256_setzero_pd(),_mm256_setzero_pd()};}static inline V vset1(R x){return {_mm256_set1_pd(x),_mm256_set1_pd(x)};}
static inline V vadd(V a,V b){return {_mm256_add_pd(a.lo,b.lo),_mm256_add_pd(a.hi,b.hi)};}static inline V vsub(V a,V b){return {_mm256_sub_pd(a.lo,b.lo),_mm256_sub_pd(a.hi,b.hi)};}
static inline V vmul(V a,V b){return {_mm256_mul_pd(a.lo,b.lo),_mm256_mul_pd(a.hi,b.hi)};}static inline V vfma(V a,V b,V c){return {_mm256_fmadd_pd(a.lo,b.lo,c.lo),_mm256_fmadd_pd(a.hi,b.hi,c.hi)};}
static inline V vload(const R*p){return {_mm256_loadu_pd(p),_mm256_loadu_pd(p+4)};}static inline void vstore(R*p,V a){_mm256_storeu_pd(p,a.lo);_mm256_storeu_pd(p+4,a.hi);}
static inline V vgather(const R*base,const int*idx){return {_mm256_i32gather_pd(base,_mm_loadu_si128((const __m128i*)idx),8),_mm256_i32gather_pd(base,_mm_loadu_si128((const __m128i*)(idx+4)),8)};}
static inline R rcos(R x){return cos(x);}static inline R rlog(R x){return log(x);}static inline R rsqrt(R x){return sqrt(x);}static inline R rpi(){return acos(-1.);}
#endif
// Knuth TwoSum accumulation: s+c carries the running sum; exact error term added to c.
static inline void tsum(V&s,V&c,V x){V t=vadd(s,x);V bp=vsub(t,s);V e=vadd(vsub(s,vsub(t,bp)),vsub(x,bp));c=vadd(c,e);s=t;}
static inline void tsumL(LD&s,LD&c,LD x){LD t=s+x;LD bp=t-s;LD e=(s-(t-bp))+(x-bp);c+=e;s=t;}

// ---------------------------------------------------------------- SHA-256 (FIPS 180-4), for provenance only
struct Sha256{uint32_t h[8];uint64_t n=0;unsigned char b[64];size_t k=0;
 static uint32_t r(uint32_t x,int s){return (x>>s)|(x<<(32-s));}
 Sha256(){const uint32_t i[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};memcpy(h,i,32);}
 void blk(const unsigned char*p){static const uint32_t K[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
  uint32_t w[64];for(int i=0;i<16;i++)w[i]=(uint32_t)p[4*i]<<24|(uint32_t)p[4*i+1]<<16|(uint32_t)p[4*i+2]<<8|p[4*i+3];
  for(int i=16;i<64;i++){uint32_t s0=r(w[i-15],7)^r(w[i-15],18)^(w[i-15]>>3),s1=r(w[i-2],17)^r(w[i-2],19)^(w[i-2]>>10);w[i]=w[i-16]+s0+w[i-7]+s1;}
  uint32_t a=h[0],bb=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],hh=h[7];
  for(int i=0;i<64;i++){uint32_t S1=r(e,6)^r(e,11)^r(e,25),ch=(e&f)^(~e&g),t1=hh+S1+ch+K[i]+w[i],S0=r(a,2)^r(a,13)^r(a,22),mj=(a&bb)^(a&c)^(bb&c),t2=S0+mj;hh=g;g=f;f=e;e=d+t1;d=c;c=bb;bb=a;a=t1+t2;}
  h[0]+=a;h[1]+=bb;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=hh;}
 void add(const void*v,size_t len){const unsigned char*p=(const unsigned char*)v;n+=len;while(len){size_t m=min(len,64-k);memcpy(b+k,p,m);k+=m;p+=m;len-=m;if(k==64){blk(b);k=0;}}}
 string hex(){uint64_t bits=n*8;unsigned char pad=0x80;add(&pad,1);unsigned char z=0;while(k!=56)add(&z,1);unsigned char L8[8];for(int i=0;i<8;i++)L8[i]=bits>>(56-8*i);add(L8,8);
  char o[65];for(int i=0;i<8;i++)snprintf(o+8*i,9,"%08x",h[i]);return string(o,64);}
};
static string sha_file(const string&f){ifstream in(f,ios::binary);if(!in){cerr<<"cannot read "<<f<<endl;exit(2);}Sha256 s;vector<char>buf(1<<20);while(in){in.read(buf.data(),buf.size());s.add(buf.data(),in.gcount());}return s.hex();}

// ---------------------------------------------------------------- perturbation (rounding-sensitivity replicates only)
static inline uint64_t mix(uint64_t x){x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);}
// Every nonzero value moves one ulp up or down with equal probability (hash of seed and key); zeros stay zero.
static inline R pert(R v,uint64_t seed,uint64_t key){if(!seed||v==0)return v;uint64_t hsh=mix(mix(seed)^key);bool up=hsh&1;
#ifdef C6_REFERENCE
 return up?nextafterl(v,INFINITY):nextafterl(v,-INFINITY);
#else
 return up?nextafter(v,INFINITY):nextafter(v,-INFINITY);
#endif
}

struct Term{uint32_t l,r;int w;};
struct Sig{array<unsigned char,8>e{};};
struct Graph{array<unsigned char,21>e{};uint32_t l,r;int w;};
struct Group{int id;vector<Term>ts;};

static void usage(){cerr<<"usage: c6sum L N threads root mode(H|J) --out FILE [--first a] [--stop b] [--mod K] [--stratum all|hard|light] [--comp 1|2] [--perturb SEED]\n";exit(64);}

int main(int argc,char**argv){
 if(argc<6)usage();
 int L=atoi(argv[1]),N=atoi(argv[2]),nt=atoi(argv[3]);string root=argv[4],mode=argv[5];
 int first=0,stop=1<<30,comp=1,modk=1;uint64_t PERT=0;string out,stratum="all";
 for(int i=6;i<argc;i++){string a=argv[i];auto nx=[&](){if(i+1>=argc)usage();return string(argv[++i]);};
  if(a=="--out")out=nx();else if(a=="--first")first=stoi(nx());else if(a=="--stop")stop=stoi(nx());else if(a=="--stratum")stratum=nx();else if(a=="--mod")modk=stoi(nx());
  else if(a=="--comp")comp=stoi(nx());else if(a=="--perturb")PERT=stoull(nx());else usage();}
 if(out.empty()||(L!=5&&L!=6)||(mode!="H"&&mode!="J")||N<2||nt<1||(stratum!="all"&&stratum!="hard"&&stratum!="light")||(comp!=1&&comp!=2)||first<0||stop<=first||modk<1)usage();
 int nv=L+1,D=L-1,nn=N+1,NE=L*(L+1)/2,NR=NE+2;long long NPl=1;for(int j=0;j<D;j++)NPl*=nn;if(NPl>(1LL<<31)-64){cerr<<"too many points\n";return 2;}
 int NP=NPl,NB=(NP+LANES-1)/LANES,NC=NB*LANES,maxExpo=mode=="H"?0:1,NW=D+maxExpo+1;omp_set_num_threads(nt);
 int nsect=1;for(int i=2;i<=L;i++)nsect*=i;nsect/=2;
 string gfile=root+"/graphs"+to_string(nv)+".bin",wfile=root+"/w_"+to_string(L)+"_"+to_string(N)+".bin";
#ifdef C6_REFERENCE
 string wread=root+"/w_"+to_string(L)+"_"+to_string(N)+".dd.bin";
#else
 string wread=wfile;
#endif
 auto t0=chrono::steady_clock::now();
 // ---------------- graphs
 vector<pair<int,int>>edges;vector<int>nadj;for(int i=0;i<nv;i++)for(int j=i+1;j<nv;j++){if(j>i+1)nadj.push_back(edges.size());edges.push_back({i,j});}int EL=nadj.size()/2,ER=nadj.size()-EL;
 vector<Sig>left,right;vector<int>lm(1<<(2*EL),-1),rm(1<<(2*ER),-1);vector<Graph>G;string g_sha_mem,w_sha_mem;
 {ifstream in(gfile,ios::binary|ios::ate);if(!in){cerr<<"cannot open "<<gfile<<endl;return 3;}size_t nb=in.tellg();in.seekg(0);
  const size_t expect_rows=L==6?2427005:59145;if(nb!=expect_rows*NR*4){cerr<<gfile<<": size "<<nb<<" != "<<expect_rows*NR*4<<" bytes ("<<expect_rows<<" graphs)"<<endl;return 3;}
  vector<int>gg(nb/4);in.read((char*)gg.data(),nb);if(!in||(size_t)in.gcount()!=nb){cerr<<"graph read failed"<<endl;return 3;}int NG0=gg.size()/NR;
  {Sha256 s;s.add(gg.data(),nb);g_sha_mem=s.hex();} // hash of the bytes actually used
  for(int gi=0;gi<NG0;gi++){int*gr=&gg[(size_t)gi*NR];int deg[8]={},tot=0;for(int e=0;e<NE;e++){if(gr[e]<0||gr[e]>3){cerr<<"bad multiplicity in graph "<<gi<<endl;return 3;}tot+=gr[e];deg[edges[e].first]+=gr[e];deg[edges[e].second]+=gr[e];}
   bool ok=tot==2*L;for(int v=0;v<nv;v++)if(deg[v]<2||deg[v]>4)ok=false;if(!ok){cerr<<"graph "<<gi<<" violates the degree/edge-count invariants"<<endl;return 3;}}
  for(int gi=0;gi<NG0;gi++){int*gr=&gg[(size_t)gi*NR];int w=mode=="H"?3*gr[NE+1]-gr[NE]:8*gr[NE+1]-3*gr[NE];if(w==0)continue;Graph g;g.w=w;for(int e=0;e<NE;e++)g.e[e]=gr[e];
   int kl=0,kr=0;Sig sl,sr;for(int i=0;i<EL;i++){sl.e[i]=gr[nadj[i]];kl|=gr[nadj[i]]<<(2*i);}for(int i=0;i<ER;i++){sr.e[i]=gr[nadj[i+EL]];kr|=gr[nadj[i+EL]]<<(2*i);}
   if(lm[kl]<0){lm[kl]=left.size();left.push_back(sl);}if(rm[kr]<0){rm[kr]=right.size();right.push_back(sr);}g.l=lm[kl];g.r=rm[kr];G.push_back(g);}}
 // ---------------- per-axis weight tables qw[j][b][r][i] (reference: hi+lo double-double -> long double)
 size_t QW=(size_t)D*(2*L+1)*7*nn;vector<R>qw(QW);
 {ifstream wi(wread,ios::binary|ios::ate);size_t nbw=wi.tellg();wi.seekg(0);
#ifdef C6_REFERENCE
  if(nbw!=QW*16){cerr<<"weights size mismatch "<<wread<<"\n";return 3;}vector<double>tmp(2*QW);wi.read((char*)tmp.data(),nbw);{Sha256 s;s.add(tmp.data(),nbw);w_sha_mem=s.hex();}for(size_t i=0;i<QW;i++)qw[i]=(LD)tmp[2*i]+(LD)tmp[2*i+1];
#else
  if(nbw!=QW*8){cerr<<"weights size mismatch "<<wread<<"\n";return 3;}wi.read((char*)qw.data(),nbw);{Sha256 s;s.add(qw.data(),nbw);w_sha_mem=s.hex();}
#endif
  if(!wi){cerr<<"weights read failed\n";return 3;}}
 if(PERT)for(size_t i=0;i<QW;i++)qw[i]=pert(qw[i],PERT,(3ULL<<60)^i);
 auto qoff=[&](int j,int b,int r){return (((size_t)j*(2*L+1)+b)*7+(r+1))*nn;};
 // ---------------- provenance header (everything that determines the numbers)
 char host[256]={};gethostname(host,255);string cpu;{ifstream ci("/proc/cpuinfo");string ln;while(getline(ci,ln))if(ln.rfind("model name",0)==0){cpu=ln.substr(ln.find(':')+2);break;}}
 string exe_sha=sha_file("/proc/self/exe"),g_sha=g_sha_mem,w_sha=w_sha_mem; // input hashes are of the in-memory bytes
 ostringstream hd;hd<<"{\"type\":\"header\",\"engine\":\"c6sum\",\"kind\":\""<<KIND<<"\",\"git\":\""<<C6_GIT_SHA<<"\",\"source_sha256\":\""<<C6_SRC_SHA<<"\",\"exe_sha256\":\""<<exe_sha<<"\",\"graphs_sha256\":\""<<g_sha<<"\",\"weights_file\":\""<<wread.substr(wread.rfind('/')+1)<<"\",\"weights_sha256\":\""<<w_sha
  <<"\",\"L\":"<<L<<",\"N\":"<<N<<",\"mode\":\""<<mode<<"\",\"stratum\":\""<<stratum<<"\",\"comp\":"<<comp<<",\"perturb\":"<<PERT<<",\"first\":"<<first<<",\"stop\":"<<min(stop,nsect)<<",\"mod\":"<<modk<<",\"sectors_total\":"<<nsect<<",\"normalization\":\"1/(L*864)\"}";
 string header=hd.str();
 // ---------------- resume: identical header required; completed sectors are skipped; a torn last line is dropped
 set<int>doneset;
 {ifstream ex(out);if(ex){string all((istreambuf_iterator<char>(ex)),istreambuf_iterator<char>());ex.close();
   if(!all.empty()){size_t cut=all.rfind('\n');string keep=cut==string::npos?string():all.substr(0,cut+1);
    istringstream ss(keep);string line;bool first_line=true;
    while(getline(ss,line)){if(first_line){if(line!=header){cerr<<"header mismatch in "<<out<<"; refusing to resume\n";return 3;}first_line=false;continue;}
     if(line.rfind("{\"type\":\"attempt\"",0)==0)continue;
     static const string pre="{\"type\":\"sector\",\"sector\":";
     if(line.rfind(pre,0)!=0){cerr<<"bad line in "<<out<<"\n";return 3;}int s=atoi(line.c_str()+pre.size());if(!doneset.insert(s).second){cerr<<"duplicate sector "<<s<<" in "<<out<<"\n";return 3;}}
    if(keep!=all){ofstream tr(out,ios::trunc);tr<<keep;}
    if(keep.empty()){ofstream tr(out,ios::trunc);}}}}
 bool fresh=true;{ifstream ex(out);string l;if(ex&&getline(ex,l)&&l==header)fresh=false;}
 ofstream jout(out,fresh?ios::trunc:ios::app);if(!jout){cerr<<"cannot write "<<out<<endl;return 2;}
 if(fresh){jout<<header<<"\n";}
 {time_t now=time(nullptr);char ts[32];strftime(ts,32,"%Y-%m-%dT%H:%M:%S%z",localtime(&now));
  jout<<"{\"type\":\"attempt\",\"host\":\""<<host<<"\",\"cpu\":\""<<cpu<<"\",\"threads\":"<<nt<<",\"compiler\":\""<<__VERSION__<<"\",\"started\":\""<<ts<<"\",\"sectors_already_done\":"<<doneset.size()<<"}\n";jout.flush();}
 jout<<setprecision(21);
 cerr<<"c6sum "<<KIND<<" L="<<L<<" N="<<N<<" mode="<<mode<<" stratum="<<stratum<<" comp="<<comp<<" perturb="<<PERT<<" sectors ["<<first<<","<<min(stop,nsect)<<") resume-done="<<doneset.size()<<" host="<<host<<" cpu="<<cpu<<" threads="<<nt<<endl;
 // ---------------- node data: q^{-1/2}, q^{-1}, q^{-3/2}, log(q)/2 per mask, and -L log H
 vector<array<int,5>>inds(NC);vector<int>indT((size_t)D*NC,0);vector<R>qs((size_t)(1<<L)*4*NC,0),LH(NC,0);
 #pragma omp parallel for
 for(int p=0;p<NP;p++){int k=p;R t[5];for(int j=D-1;j>=0;j--){inds[p][j]=k%nn;k/=nn;t[j]=(1+rcos(rpi()*inds[p][j]/N))/2;if(inds[p][j]==0)t[j]=1;if(inds[p][j]==N)t[j]=0;}
  for(int j=0;j<D;j++)indT[(size_t)j*NC+p]=inds[p][j];
  for(int m=1;m<(1<<L);m++){int mini=__builtin_ctz(m);R q=1,z=1;for(int r=mini+1;r<L;r++){z*=t[r-1];if(m&(1<<r))q+=z;}R*o=&qs[(size_t)m*4*NC+p];o[0]=1/rsqrt(q);o[NC]=o[0]*o[0];o[2*NC]=o[NC]*o[0];o[3*NC]=rlog(q)/2;if(m==(1<<L)-1)LH[p]=-L*rlog(q);}}
 if(PERT){
  #pragma omp parallel for
  for(int p=0;p<NP;p++){for(int m=1;m<(1<<L);m++)for(int c=0;c<4;c++){size_t i=(size_t)(m*4+c)*NC+p;qs[i]=pert(qs[i],PERT,(1ULL<<60)^i);}LH[p]=pert(LH[p],PERT,(2ULL<<60)^(uint64_t)p);}}
 cerr<<"graphs="<<G.size()<<" left="<<left.size()<<" right="<<right.size()<<" points="<<NP<<" blocks="<<NB<<" prepared="<<chrono::duration<double>(chrono::steady_clock::now()-t0).count()<<"s"<<endl;
 // ---------------- sectors
 int bbase=2*L+1,btot=1;for(int j=0;j<D;j++)btot*=bbase;vector<int>ids(btot,-1);vector<array<int,5>>bs;vector<int>bkey;
 vector<int>perm(L);iota(perm.begin(),perm.end(),0);int sector=0;
 vector<array<LD,14>>blockval(NB);
 do{
  vector<int>rev(L);for(int i=0;i<L;i++)rev[i]=L-1-perm[i];if(perm>rev)continue;int sidx=sector++;if(sidx<first)continue;if(sidx>=stop)break;if(sidx%modk)continue;if(doneset.count(sidx))continue;
  auto ts0=chrono::steady_clock::now();
  int rank[6],masks[21],mins[21];for(int r=0;r<L;r++)rank[perm[r]]=r;for(int e=0;e<NE;e++){auto[a,b]=edges[e];int mask=0;for(int i=a;i<b;i++)mask|=1<<rank[i];masks[e]=mask;mins[e]=__builtin_ctz(mask);}
  vector<int>gi(G.size());vector<int>counts(bs.size(),0);
  for(size_t ix=0;ix<G.size();ix++){int buckets[6]={};for(int e=0;e<NE;e++)buckets[mins[e]]+=G[ix].e[e];array<int,5>b{};int v=0,key=0;for(int j=D-1;j>=0;j--){v+=buckets[j+1];b[j]=v;key=key*bbase+v;}
   if(stratum!="all"){int poles=0,power=0;for(int j=0;j<D;j++){int a2=2*(L-2-j)-b[j];if(a2<=-2&&a2%2==0)poles++;if(a2<-2)power++;}
    bool hard=poles>=2||power>0;if(hard!=(stratum=="hard")){gi[ix]=-1;continue;}} // hard: reference/full_hard.cpp filter; light: complement
   int id=ids[key];if(id<0){id=bs.size();ids[key]=id;bs.push_back(b);bkey.push_back(key);counts.push_back(0);}gi[ix]=id;counts[id]++;}
  vector<Group>groups;vector<int>grouploc(bs.size(),-1);
  vector<int>order;for(int id=0;id<(int)counts.size();id++)if(counts[id])order.push_back(id);
  sort(order.begin(),order.end(),[&](int x,int y){return bkey[x]<bkey[y];}); // accumulation order independent of sector history
  for(int id:order){grouploc[id]=groups.size();groups.push_back({id,{}});groups.back().ts.reserve(counts[id]);}
  for(size_t ix=0;ix<G.size();ix++){if(gi[ix]<0)continue;auto&g=G[ix];groups[grouploc[gi[ix]]].ts.push_back({g.l,g.r,g.w});}
  // Per active group: base offsets of qw rows for (axis j, bucket b[j], r); fixed within the sector.
  int ng=groups.size();vector<size_t>goff((size_t)ng*D*7);vector<int>gb((size_t)ng*D);
  for(int gix=0;gix<ng;gix++){auto&b=bs[groups[gix].id];for(int j=0;j<D;j++){gb[(size_t)gix*D+j]=b[j];for(int r=-1;r<=5;r++)goff[((size_t)gix*D+j)*7+(r+1)]=qoff(j,b[j],r);}}
  #pragma omp parallel
  {
   vector<V>lv(left.size()),rv(right.size()),ll(left.size()),rl(right.size());
   #pragma omp for schedule(dynamic,16)
   for(int ip=0;ip<NB;ip++){int pp=LANES*ip;V pw[15][4],lg[15];
    for(int i=0;i<(int)nadj.size();i++){int m=masks[nadj[i]];pw[i][0]=vset1(1);for(int j=1;j<=3;j++)pw[i][j]=vload(&qs[((size_t)m*4+j-1)*NC+pp]);lg[i]=vload(&qs[((size_t)m*4+3)*NC+pp]);}
    for(int h=0;h<(int)left.size();h++){V z=vset1(1),l=vzero();for(int j=0;j<EL;j++){int e=left[h].e[j];if(e){z=vmul(z,pw[j][e]);l=vfma(vset1(e),lg[j],l);}}lv[h]=z;ll[h]=l;}
    for(int h=0;h<(int)right.size();h++){V z=vset1(1),l=vzero();for(int j=0;j<ER;j++){int e=right[h].e[j];if(e){z=vmul(z,pw[j+EL][e]);l=vfma(vset1(e),lg[j+EL],l);}}rv[h]=z;rl[h]=l;}
    V hp[8];hp[0]=vset1(1);V hh=vload(&LH[pp]);for(int j=1;j<NW;j++)hp[j]=vmul(vmul(hp[j-1],hh),vset1((R)1/j));
    int lanesIdx[5][LANES];for(int j=0;j<D;j++)for(int k=0;k<LANES;k++)lanesIdx[j][k]=indT[(size_t)j*NC+pp+k];
    V acc[14],cmp[14];for(int j=0;j<2*NW;j++){acc[j]=vzero();cmp[j]=vzero();}
    for(int gix=0;gix<ng;gix++){auto&g=groups[gix];
     // Laurent weight tensor for this group at the block's points: same recursion and order as reference/full.cpp.
     V a[16],bb[16];for(int k=0;k<16;k++)a[k]=vzero();a[6]=vset1(1);
     for(int j=0;j<D;j++){for(int k=0;k<16;k++)bb[k]=vzero();V q[7];for(int r=-1;r<=5;r++)q[r+1]=vgather(&qw[goff[((size_t)gix*D+j)*7+(r+1)]],lanesIdx[j]);
      for(int k=-j;k<=D-j+maxExpo;k++)for(int r=-1;r<=5;r++)if(k+r>=-j-1&&k+r<=D-j-1+maxExpo)bb[k+r+6]=vfma(a[k+6],q[r+1],bb[k+r+6]);
      for(int k=0;k<16;k++)a[k]=bb[k];}
     V wt[8];for(int k=-D;k<=maxExpo;k++)wt[k+D]=a[k+6];
     alignas(64) R tmpw[LANES];
     if(pp+LANES>NP||PERT){for(int o=0;o<NW;o++){vstore(tmpw,wt[o]);for(int k=0;k<LANES;k++){if(pp+k>=NP)tmpw[k]=0;else if(PERT)tmpw[k]=pert(tmpw[k],PERT,(4ULL<<60)^((uint64_t)bkey[g.id]<<34)^((uint64_t)o<<30)^(uint64_t)(pp+k));}wt[o]=vload(tmpw);}}
     int minr=NW-1;for(int o=0;o<NW;o++){vstore(tmpw,wt[o]);bool any=false;for(int k=0;k<LANES;k++)if(tmpw[k]!=0){any=true;break;}if(any){minr=o;break;}}
     int km=NW-1-minr;V mom[8];for(int j=0;j<=km;j++)mom[j]=vzero();
     if(comp==2){V mc[8];for(int j=0;j<=km;j++)mc[j]=vzero();
      for(auto&t:g.ts){V z=vmul(vmul(vset1(t.w),lv[t.l]),rv[t.r]);tsum(mom[0],mc[0],z);if(km){V k=vadd(ll[t.l],rl[t.r]);for(int j=1;j<=km;j++){z=vmul(vmul(z,k),vset1((R)1/j));tsum(mom[j],mc[j],z);}}}
      for(int j=0;j<=km;j++)mom[j]=vadd(mom[j],mc[j]);}
     else if(km==0){for(auto&t:g.ts)mom[0]=vfma(vmul(vset1(t.w),lv[t.l]),rv[t.r],mom[0]);}
     else{for(auto&t:g.ts){V z=vmul(vmul(vset1(t.w),lv[t.l]),rv[t.r]);V k=vadd(ll[t.l],rl[t.r]);mom[0]=vadd(mom[0],z);for(int j=1;j<=km;j++){z=vmul(vmul(z,k),vset1((R)1/j));mom[j]=vadd(mom[j],z);}}}
     V vals[8];for(int o=0;o<NW;o++){vals[o]=vzero();for(int j=0;j<=min(km,o);j++)vals[o]=vfma(mom[j],wt[o-j],vals[o]);tsum(acc[o],cmp[o],vals[o]);V sv=vzero();for(int j=0;j<=o;j++)sv=vfma(vals[j],hp[o-j],sv);tsum(acc[NW+o],cmp[NW+o],sv);}
    }
    for(int j=0;j<2*NW;j++){alignas(64) R a1[LANES],c1[LANES];vstore(a1,acc[j]);vstore(c1,cmp[j]);LD s=0;for(int k=0;k<LANES;k++)s+=(LD)a1[k]+(LD)c1[k];blockval[ip][j]=s;}
   }
  }
  LD st[14];for(int j=0;j<2*NW;j++){LD s=0,c=0;for(int ip=0;ip<NB;ip++)tsumL(s,c,blockval[ip][j]);st[j]=(s+c)/(L*(LD)864);}
  double secs=chrono::duration<double>(chrono::steady_clock::now()-ts0).count();
  jout<<"{\"type\":\"sector\",\"sector\":"<<sidx<<",\"values\":[";for(int j=0;j<2*NW;j++){if(j)jout<<",";jout<<st[j];}jout<<"],\"active_groups\":"<<ng<<",\"seconds\":"<<setprecision(6)<<secs<<setprecision(21)<<"}\n";jout.flush();
  if(!jout){cerr<<"write failed\n";return 2;}
  cerr<<"sector="<<sidx<<" groups="<<ng<<" seconds="<<secs<<" elapsed="<<chrono::duration<double>(chrono::steady_clock::now()-t0).count()<<endl;
 }while(next_permutation(perm.begin(),perm.end()));
 cerr<<"DONE "<<out<<" elapsed="<<chrono::duration<double>(chrono::steady_clock::now()-t0).count()<<"s"<<endl;
}
