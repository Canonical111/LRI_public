#pragma once
// Shared data, deterministic work units and checked I/O.  No fast-math is permitted.
#include <bits/stdc++.h>
#include <omp.h>
#include <quadmath.h>
#include <boost/multiprecision/cpp_dec_float.hpp>
#include <boost/version.hpp>
#include <unistd.h>
#include <fcntl.h>
#include <sys/resource.h>
using LD=long double;
using MP=boost::multiprecision::cpp_dec_float_100;
using namespace std;
#ifdef __FAST_MATH__
#error "C7 requires strict floating-point semantics; remove -ffast-math/-Ofast."
#endif
static_assert(numeric_limits<LD>::digits>=64,"At least 64 mantissa bits are required for long double.");
constexpr int NW=7,MAX_L=7,MAX_E=28;
inline void require(bool b,const string& s){if(!b)throw runtime_error(s);}
struct Edge{int k,m,co;};
struct Prefix{int parent,k,m;};
struct Term{uint64_t key=0;vector<Edge> e;int leaf=0;};
struct Graph{int id=0,power=0,primitive=0;LD wa=0,wb=0;vector<Term>terms;vector<Prefix>prefix;};
inline void make_prefix(Graph& g){
 g.prefix.push_back({-1,0,0});map<tuple<int,int,int>,int> ids;
 for(auto& t:g.terms){int p=0;for(auto e:t.e){auto key=make_tuple(p,e.k,e.m);auto z=ids.find(key);
  if(z==ids.end()){int n=g.prefix.size();ids[key]=n;g.prefix.push_back({p,e.k,e.m});p=n;}else p=z->second;}
  t.leaf=p;
 }
}
struct Work{uint64_t uid=0;int rep=0,graph=0;uint64_t begin=0,end=0,total=0;};
struct Options{
 string mode,inputs,tasks,output,net,selection="all";int L=0,degree=0,threads=0;
 uint64_t seed=0;LD rate=.8L;size_t tile=128,scratch_mib=32;bool profile=false,oracle=false;
};
inline Options parse_args(int argc,char**argv){
 Options a;map<string,string>kv;
 for(int i=1;i<argc;i++){
  string k=argv[i];if(k=="--help"){cout<<"c7_integrate --mode qmc|power --inputs DIR --L 2..7 --tasks FILE --seed U64 --rate 0.8 --output FILE [--net FILE] [--degree N] [--threads N] [--tile 128] [--scratch-mib 32] [--profile] [--oracle-point]\n";exit(0);}
  if(k=="--profile"){a.profile=true;continue;}if(k=="--oracle-point"){a.oracle=true;continue;}
  require(k.rfind("--",0)==0&&i+1<argc,"missing value: "+k);require(!kv.count(k),"duplicate option "+k);kv[k]=argv[++i];
 }
 auto take=[&](const string&k,const string&d=""){auto it=kv.find(k);if(it==kv.end())return d;string v=it->second;kv.erase(it);return v;};
 a.mode=take("--mode");a.inputs=take("--inputs");a.tasks=take("--tasks");a.output=take("--output");a.net=take("--net");
 a.L=stoi(take("--L","0"));a.degree=stoi(take("--degree","0"));a.threads=stoi(take("--threads","0"));
 a.seed=stoull(take("--seed","0"));a.rate=stold(take("--rate","0.8"));
 a.tile=stoull(take("--tile","128"));a.scratch_mib=stoull(take("--scratch-mib","32"));
 require(kv.empty(),"unrecognized option "+(kv.empty()?string():kv.begin()->first));
 require(a.mode=="qmc"||a.mode=="power","mode must be qmc or power");require(a.L>=2&&a.L<=7,"supported loop orders: 2..7, not an arbitrary-loop engine");
 require(!a.inputs.empty()&&!a.tasks.empty()&&!a.output.empty(),"inputs/tasks/output required");require(isfinite(a.rate)&&a.rate>0&&a.rate<=1,"rate must lie in (0,1]");
 require(a.threads>=0&&a.threads<=4096,"invalid thread count");require(a.tile>0&&a.tile<=1048576&&a.scratch_mib>=1&&a.scratch_mib<=65536,"invalid tile/scratch budget");
 if(a.mode=="qmc")require(!a.net.empty(),"qmc requires --net");else require(a.degree>=1&&a.degree<=254,"quadrature degree must be 1..254");
 require(!filesystem::exists(a.output),"refusing to overwrite "+a.output);
 if(a.threads)omp_set_num_threads(a.threads);omp_set_dynamic(0);return a;
}
inline vector<Work> read_work(const string&path,int&ng){
 ifstream in(path);string magic;uint64_t count;in>>magic>>ng>>count;require(in&&magic=="C7TASKS1"&&ng>0&&count>0&&count<100000000,"invalid tasks header");
 vector<Work>w;w.reserve(count);set<uint64_t>uids;
 for(uint64_t i=0;i<count;i++){Work v;in>>v.uid>>v.rep>>v.graph>>v.begin>>v.end>>v.total;
  require(in&&v.rep>=0&&v.graph>=0&&v.graph<ng&&v.begin<v.end&&v.end<=v.total,"invalid work row");
  require(uids.insert(v.uid).second,"duplicate work uid");w.push_back(v);
 }string extra;require(!(in>>extra),"trailing task data");return w;
}
// Only construct requested graphs.  An optional byte-offset index eliminates repeated scans.
inline vector<Graph> load_graphs(const Options&o,const vector<Work>&work,int expected_ng,vector<int>&slot){
 string path=o.inputs+"/L"+to_string(o.L)+"_coord.txt";ifstream in(path);int L,ng;in>>L>>ng;
 require(in&&L==o.L&&ng==expected_ng,"graph inventory header mismatch");
 set<int>wanted;for(auto&w:work)wanted.insert(w.graph);slot.assign(ng,-1);vector<Graph>gs;gs.reserve(wanted.size());int NE=L*(L+1)/2;
 vector<uint64_t>offset;ifstream ix(path+".idx");if(ix){string magic;uint64_t bytes;int ni;ix>>magic>>bytes>>ni;
  require(magic=="C7IDX1"&&bytes==filesystem::file_size(path)&&ni==ng,"invalid/stale graph index");offset.resize(ng);for(auto&v:offset)ix>>v;require(bool(ix),"truncated graph index");}
 auto one=[&](int expected,bool keep){Graph g;size_t nt;in>>g.id>>g.wa>>g.wb>>g.power>>g.primitive>>nt;
  require(in&&g.id==expected&&nt<=10000000,"invalid graph header");string line;getline(in,line);
  if(!keep){for(size_t i=0;i<nt;i++)require(bool(getline(in,line)),"truncated skipped graph");return;}
  g.terms.reserve(nt);for(size_t t=0;t<nt;t++){Term term;in>>term.key;for(int k=0;k<NE;k++){int co;in>>co;int m=(term.key>>(2*k))&3;if(m)term.e.push_back({k,m,co});else require(co==0,"root numerator outside denominator edge support");}require(bool(in),"truncated term");g.terms.push_back(move(term));}
  require(!g.terms.empty(),"work includes empty forest graph "+to_string(g.id));
  if(o.mode=="qmc")require(!g.power,"power-containing graph supplied to continuous sampler");
  make_prefix(g);slot[g.id]=gs.size();gs.push_back(move(g));
 };
 if(offset.empty()){for(int i=0;i<ng;i++)one(i,wanted.count(i));}else for(int i:wanted){in.seekg(offset[i]);one(i,true);}
 return gs;
}
inline uint64_t graph_seed(uint64_t seed,int rep,int gi){return seed+0x9e3779b97f4a7c15ULL*uint64_t(rep+1)+0xbf58476d1ce4e5b9ULL*uint64_t(gi+1);}
struct TP{int n,L;LD rate,Z;vector<LD>a,w;vector<vector<pair<int,LD>>>cdf;};
inline TP prep_tree(const Graph&g,int L,LD rate,bool power){TP p;p.L=L;p.n=L+1;p.rate=rate;int full=(1<<p.n)-1;p.a.resize(full+1);p.w.resize(full+1);p.cdf.resize(full+1);uint64_t inside[256]={};
 for(int s=1;s<=full;s++){int k=0;for(int i=0;i<p.n;i++)for(int j=i+1;j<p.n;j++,k++)if((s>>i&1)&&(s>>j&1))inside[s]|=1ULL<<(2*k);}
 for(int s=1;s<=full;s++){int v=__builtin_popcount(unsigned(s));if(v==1){p.w[s]=1;continue;}int em=0;
  for(auto&t:g.terms){int e=__builtin_popcountll(t.key&inside[s])+2*__builtin_popcountll((t.key>>1)&inside[s]);em=max(em,e);}
  LD pw=v-1-em/2.L;require(power||pw>=0,"negative cluster exponent in continuous graph");
  p.a[s]=s==full?1:rate*max(.5L,power?abs(pw):pw);int bit=s&-s;LD sum=0;
  for(int u=(s-1)&s;u;u=(u-1)&s)if(u&bit){int v=s^u;sum+=2*p.w[u]*p.w[v];p.cdf[s].push_back({u,sum});}p.w[s]=sum/p.a[s];
 }p.Z=p.w[full];return p;
}
struct TreeSample{int n=0,L=0,ng=0,nn=0,leafn=0;int masks[28]{},gapnodes[7]{},parents[7]{},sizes[7]{},clusters[7]{},order[8]{};LD lt[7]{},alpha[7]{};};
inline void draw_rec(const TP&p,const LD*u,TreeSample&t,int&ci,int s,int parent,bool radial){
 if(!(s&(s-1))){t.order[t.leafn++]=__builtin_ctz(unsigned(s));return;}
 int id=t.nn++;t.parents[id]=parent;t.sizes[id]=__builtin_popcount(unsigned(s));t.clusters[id]=s;LD v=u[ci++];
 if(id){t.alpha[id]=p.a[s];if(radial)t.lt[id]=logl(u[p.L+id-1])/t.alpha[id];}else t.alpha[id]=1;
 bool flip=v>.5L;v=flip?2*v-1:2*v;LD z=v*p.cdf[s].back().second;
 auto it=lower_bound(p.cdf[s].begin(),p.cdf[s].end(),z,[](auto&a,LD b){return a.second<b;});if(it==p.cdf[s].end())--it;
 int A=it->first,B=s^A;if(flip)swap(A,B);draw_rec(p,u,t,ci,A,id,radial);t.gapnodes[t.ng++]=id;draw_rec(p,u,t,ci,B,id,radial);
}
inline TreeSample draw_tree(const TP&p,const LD*u,bool radial=true){TreeSample t;t.n=p.n;t.L=p.L;int ci=0;draw_rec(p,u,t,ci,(1<<p.n)-1,-1,radial);
 if(radial){int pos[8];for(int i=0;i<p.n;i++)pos[t.order[i]]=i;int k=0;for(int i=0;i<p.n;i++)for(int j=i+1;j<p.n;j++){int lo=min(pos[i],pos[j]),hi=max(pos[i],pos[j]);t.masks[k++]=((1<<hi)-1)^((1<<lo)-1);}}return t;}
template<class T>T sqrtt(T x){using std::sqrt;return sqrt(x);}template<>inline __float128 sqrtt(__float128 x){return sqrtq(x);}
template<class T>T logt(T x){using std::log;return log(x);}template<>inline __float128 logt(__float128 x){return logq(x);}
template<class T>T expt(T x){using std::exp;return exp(x);}template<>inline __float128 expt(__float128 x){return expq(x);}
struct Profile{double draw=0,point=0,quad=0,mp=0,geometry=0,weights=0,contract=0;uint64_t n=0,nquad=0,nmp=0,nodes=0;size_t scratch_peak=0;};
struct Row{array<LD,14>v{};uint64_t nquad=0,nmp=0;double seconds=0;};
inline string json_string(const string&s){string out="\"";for(unsigned char c:s){if(c=='"'||c=='\\'){out+='\\';out+=c;}else if(c=='\n')out+="\\n";else if(c<32)out+='?';else out+=c;}return out+'"';}
inline void write_results(const Options&o,int ng,const vector<Work>&works,const vector<Row>&rows,const vector<Profile>&prof,double prep,double sec){
 string tmp=o.output+".tmp."+to_string(getpid());int fd=open(tmp.c_str(),O_WRONLY|O_CREAT|O_EXCL,0666);require(fd>=0,"cannot create temporary output "+tmp);close(fd);
 try{ofstream f(tmp);f<<setprecision(numeric_limits<LD>::max_digits10)<<"{\"schema\":\"c7-hpc-1\",\"build\":{\"compiler\":"<<json_string(__VERSION__)<<",\"boost\":"<<json_string(BOOST_LIB_VERSION)<<"},\"mode\":"<<json_string(o.mode)<<",\"L\":"<<o.L<<",\"degree\":"<<o.degree<<",\"seed\":"<<o.seed<<",\"rate\":"<<o.rate<<",\"inventory_count\":"<<ng<<",\"threads\":"<<omp_get_max_threads()<<",\"long_double_bits\":"<<numeric_limits<LD>::digits<<",\"long_double_bytes\":"<<sizeof(LD)<<",\"tile\":"<<o.tile<<",\"scratch_mib\":"<<o.scratch_mib<<",\"oracle_point\":"<<(o.oracle?"true":"false")<<",\"preparation_seconds\":"<<prep<<",\"integration_seconds\":"<<sec<<",\"rows\":[";
 for(size_t i=0;i<works.size();i++){auto&w=works[i];auto&r=rows[i];if(i)f<<',';f<<"{\"uid\":"<<w.uid<<",\"replicate\":"<<w.rep<<",\"graph\":"<<w.graph<<",\"begin\":"<<w.begin<<",\"end\":"<<w.end<<",\"total\":"<<w.total<<",\"quad_calls\":"<<r.nquad<<",\"mp_calls\":"<<r.nmp<<",\"seconds\":"<<r.seconds<<",\"value\":[";
  for(int j=0;j<14;j++){require(isfinite(r.v[j]),"nonfinite result");if(j)f<<',';f<<r.v[j];}f<<"]}";}
 f<<"],\"profile\":[";for(size_t i=0;i<prof.size();i++){auto&p=prof[i];if(i)f<<',';f<<"{\"draw\":"<<p.draw<<",\"point\":"<<p.point<<",\"quad\":"<<p.quad<<",\"mp\":"<<p.mp<<",\"geometry\":"<<p.geometry<<",\"weights\":"<<p.weights<<",\"contract\":"<<p.contract<<",\"samples\":"<<p.n<<",\"tensor_nodes\":"<<p.nodes<<",\"scratch_bytes\":"<<p.scratch_peak<<"}";}f<<"]}";f.flush();require(bool(f),"output write failure");f.close();
 // Same-directory hard link publishes atomically and fails instead of replacing an existing result.
 require(link(tmp.c_str(),o.output.c_str())==0,"output exists or atomic publish failed");unlink(tmp.c_str());
 }catch(...){unlink(tmp.c_str());throw;}
}
