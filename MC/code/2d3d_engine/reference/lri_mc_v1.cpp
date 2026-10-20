// d-dimensional long-range Ising, full periodic-image couplings: extended-Poisson SW (Fukui--Todo).
// C++17 / Linux-POSIX. One serial Markov chain; parallelize independent chains.
// No O(N^2) pair loop, no distance cutoff, and no fast-math requirement.
// Raw output is compatible with the previous exploratory simulator:
// little-endian float64 [K_active, m2_cluster, m4_cluster, m2_sample].
#include <algorithm>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>
namespace fs = std::filesystem;
static volatile std::sig_atomic_t stop_requested=0;
static void signal_handler(int) { stop_requested=1; }
static void require(bool ok,const std::string& msg) { if(!ok) throw std::runtime_error(msg); }
static uint64_t fnv(const char* p,size_t n) {
    uint64_t h=14695981039346656037ULL;
    for(size_t i=0;i<n;++i) { h^=static_cast<unsigned char>(p[i]); h*=1099511628211ULL; }
    return h;
}
static void sync_file(const fs::path& path) {
    int fd=::open(path.c_str(),O_RDONLY); require(fd>=0,"open for fsync failed: "+path.string());
    int rc=::fsync(fd); ::close(fd); require(rc==0,"fsync failed: "+path.string());
}
static void sync_directory(const fs::path& path) {
    int fd=::open(path.c_str(),O_RDONLY|O_DIRECTORY);
    require(fd>=0,"open directory for fsync failed"); int rc=::fsync(fd); ::close(fd);
    require(rc==0,"directory fsync failed");
}
static void atomic_write(const fs::path& path,const std::string& data) {
    fs::path tmp=path; tmp+=".tmp";
    { std::ofstream f(tmp,std::ios::binary|std::ios::trunc); f.write(data.data(),data.size());
      f.flush(); require(bool(f),"write failed: "+tmp.string()); }
    sync_file(tmp); fs::rename(tmp,path); sync_directory(path.parent_path());
}
template<class T> static void put(std::string& b,const T& v) { b.append(reinterpret_cast<const char*>(&v),sizeof(T)); }
static void put_string(std::string& b,const std::string& s) { put<uint64_t>(b,s.size()); b+=s; }
struct Reader {
    const std::string& b; size_t p=0;
    template<class T> T get() { require(p+sizeof(T)<=b.size(),"truncated checkpoint"); T v; std::memcpy(&v,b.data()+p,sizeof(T)); p+=sizeof(T); return v; }
    std::string str() { uint64_t n=get<uint64_t>(); require(n<=b.size()-p,"bad checkpoint string"); auto s=b.substr(p,n); p+=n; return s; }
};
static int root(std::vector<int32_t>& p,int x) {
    while(p[x]>=0) { int y=p[x]; if(p[y]>=0) p[x]=p[y]; x=y; } return x;
}
struct FileLock { int fd=-1;
    explicit FileLock(const fs::path& p) { fd=::open(p.c_str(),O_CREAT|O_RDWR,0664); require(fd>=0,"cannot open lock");
      if(::flock(fd,LOCK_EX|LOCK_NB)!=0) {::close(fd);fd=-1;throw std::runtime_error("another process holds this chain's output lock");} }
    ~FileLock(){ if(fd>=0) {::flock(fd,LOCK_UN);::close(fd);} }
};
int main(int argc,char** argv) {
 try {
    std::map<std::string,std::string> a;
    const std::vector<std::string> allowed={"dim","length","beta","couplings","measurements","warmup","seed","out","init","checkpoint-seconds","max-seconds","stop-after"};
    for(int i=1;i<argc;i+=2) {
      std::string k=argv[i]; require(k.rfind("--",0)==0 && i+1<argc,"arguments must be --name value"); k=k.substr(2);
      require(std::find(allowed.begin(),allowed.end(),k)!=allowed.end(),"unknown option: "+k);
      require(a.emplace(k,argv[i+1]).second,"duplicate argument: "+k);
    }
    auto get=[&](const std::string& k,const std::string& def="") {auto it=a.find(k); if(it!=a.end())return it->second; require(!def.empty(),"missing --"+k);return def;};
    auto u64=[&](const std::string& k,const std::string& def="") {auto v=get(k,def);require(!v.empty()&&v[0]!='-',"invalid unsigned --"+k);size_t p=0;auto x=std::stoull(v,&p);require(p==v.size(),"invalid --"+k);return uint64_t(x);};
    int dim=int(u64("dim")),L=int(u64("length"));
    require(dim>=1&&dim<=3&&L>=2&&L<=(1<<20)&&!(L&(L-1)),"dim 1..3 and power-of-two length required");
    uint64_t n64=1;for(int z=0;z<dim;z++){n64*=L;require(n64<=(1ULL<<28),"N exceeds 2^28");}
    int lb=0;while((1<<lb)<L)++lb;int lm=L-1;
    auto addsite=[&](int x,int r){
      if(dim==1)return (x+r)&lm;
      int y=((x+r)&lm)|(( ((x>>lb)+(r>>lb))&lm)<<lb);
      if(dim==3)y|=((((x>>(2*lb))+(r>>(2*lb)))&lm)<<(2*lb));
      return y;
    };
    auto inverse=[&](int r){int v=0;for(int z=0;z<dim;z++)v|=((-((r>>(z*lb))&lm))&lm)<<(z*lb);return v;};
    int n=int(n64); double beta=std::stod(get("beta"));
    uint64_t target=u64("measurements"),warm_target=u64("warmup","20000"),seed=u64("seed");
    double checkpoint_seconds=std::stod(get("checkpoint-seconds","600"));
    double max_seconds=std::stod(get("max-seconds","0")); uint64_t stop_after=u64("stop-after","0");
    std::string init=get("init","hot"); uint8_t init_code=init=="hot"?0:1;
    require(init=="hot"||init=="cold","--init must be hot or cold");
    require(std::isfinite(beta)&&beta>0&&target>0,"invalid beta or measurement count");
    require(target<std::numeric_limits<uint64_t>::max()/32,"output offset overflow");
    require(std::isfinite(checkpoint_seconds)&&checkpoint_seconds>0&&std::isfinite(max_seconds)&&max_seconds>=0,"invalid time interval");
    uint16_t endian=1;require(*reinterpret_cast<char*>(&endian)==1&&sizeof(double)==8,"little-endian binary64 host required");
    fs::path out_dir=get("out"); fs::create_directories(out_dir); FileLock lock(out_dir/"chain.lock");
    fs::path cp_path=out_dir/"checkpoint.bin", raw_path=out_dir/"samples.bin";
    fs::path j_path=get("couplings"); require(fs::file_size(j_path)==size_t(n)*8,"wrong coupling file size");
    std::vector<double> j(n); {std::ifstream f(j_path,std::ios::binary); f.read(reinterpret_cast<char*>(j.data()),n*8);require(bool(f),"cannot read couplings");}
    require(j[0]==0,"J[0] must be zero"); long double ss=0;
    for(double v:j){require(std::isfinite(v)&&v>=0,"bad coupling");ss+=v;}
    double sum=double(ss); require(sum>0,"zero coupling sum");
    for(int d=1;d<n;d++)require(std::abs(j[d]-j[inverse(d)])<1e-12*sum,"couplings not symmetric");
    uint64_t jhash=fnv(reinterpret_cast<const char*>(j.data()),n*8);
    double lambda=beta*n*sum;require(std::isfinite(lambda)&&lambda<1e12,"Poisson rate out of supported range");
    // Walker alias table. Sampling ordered (site, displacement) pairs at rate
    // beta*N*sum_r J[r] gives rate 2*beta*J_ij per UNORDERED bond.
    std::vector<double> prob(n);std::vector<int32_t> alias(n),small,large;small.reserve(n);large.reserve(n);
    for(int i=0;i<n;i++){prob[i]=n*j[i]/sum;(prob[i]<1?small:large).push_back(i);}
    while(!small.empty()&&!large.empty()){
      int x=small.back();small.pop_back();int y=large.back();large.pop_back();
      alias[x]=y;prob[y]-=1-prob[x];(prob[y]<1?small:large).push_back(y);
    }
    for(int i:large){prob[i]=1;alias[i]=i;}for(int i:small){prob[i]=1;alias[i]=i;}
    // Release coupling and construction work arrays before production.
    std::vector<double>().swap(j);std::vector<int32_t>().swap(small);std::vector<int32_t>().swap(large);
    std::mt19937_64 rng(seed);std::poisson_distribution<int64_t> poisson(lambda);
    std::vector<int8_t> spins(n),sign(n);std::vector<int32_t> parent(n);
    uint64_t warm_done=0,done=0;
    if(fs::exists(cp_path)) {
      std::ifstream f(cp_path,std::ios::binary); std::string blob((std::istreambuf_iterator<char>(f)),{});
      require(blob.size()>16&&blob.substr(0,8)=="LRIND003","invalid checkpoint magic");
      uint64_t stored;std::memcpy(&stored,blob.data()+8,8);std::string payload=blob.substr(16);
      require(fnv(payload.data(),payload.size())==stored,"checkpoint checksum mismatch");Reader r{payload};
      require(r.get<uint64_t>()==n64&&r.get<int>()==dim&&r.get<int>()==L&&r.get<double>()==beta&&r.get<uint64_t>()==seed&&r.get<uint64_t>()==jhash,"checkpoint configuration mismatch");
      require(r.get<uint64_t>()==warm_target&&r.get<uint8_t>()==init_code,"checkpoint warmup/initialization mismatch");
      warm_done=r.get<uint64_t>();done=r.get<uint64_t>();
      require(warm_done<=warm_target&&done<=target&&(done==0||warm_done==warm_target),"checkpoint progress incompatible with target");
      auto rs=r.str(),ps=r.str();std::istringstream ri(rs),pi(ps);ri>>rng;pi>>poisson;
      require(bool(ri)&&bool(pi),"cannot restore RNG/distribution; use same compiler/standard library");
      require(r.p+size_t(n)==payload.size(),"invalid checkpoint spin data");std::memcpy(spins.data(),payload.data()+r.p,n);
      for(auto v:spins)require(v==1||v==-1,"bad spin in checkpoint");
      require(fs::exists(raw_path)&&fs::file_size(raw_path)>=done*32,"raw output shorter than committed checkpoint");
      fs::resize_file(raw_path,done*32); // drop records written after last committed checkpoint
      std::cout<<"Resumed warmup="<<warm_done<<" measurements="<<done<<"\n";
    } else {
      require(!fs::exists(raw_path)||fs::file_size(raw_path)==0,"raw output exists without checkpoint; refusing to overwrite");
      for(auto& v:spins)v=init=="cold"?1:((rng()&1)?1:-1);
    }
    // An old completion marker must not survive a requested extension.
    if(done<target&&fs::exists(out_dir/"DONE.json"))fs::remove(out_dir/"DONE.json");
    std::vector<char> iobuf(1<<20);std::ofstream raw;raw.rdbuf()->pubsetbuf(iobuf.data(),iobuf.size());raw.open(raw_path,std::ios::binary|std::ios::app);
    require(bool(raw),"cannot open raw output");
    int bits=0;while((1U<<bits)<unsigned(n))++bits;uint64_t mask=n-1;
    double inv=std::ldexp(1.0,-(64-bits)),norm2=1.0/(double(n)*n),norm4=norm2*norm2;
    auto start=std::chrono::steady_clock::now(),last_checkpoint=start;uint64_t call_sweeps=0;
    auto elapsed=[&](){return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
    auto status=[&](){std::ostringstream z;z<<std::setprecision(17)<<"{\"format\":2,\"N\":"<<n<<",\"d\":"<<dim<<",\"L\":"<<L<<",\"beta\":"<<beta<<",\"seed\":"<<seed<<",\"warmup_done\":"<<warm_done<<",\"measurements_done\":"<<done<<",\"measurements_target\":"<<target<<",\"committed_bytes\":"<<done*32<<",\"last_invocation_seconds\":"<<elapsed()<<",\"last_invocation_sweeps\":"<<call_sweeps<<",\"coupling_fnv64\":\""<<jhash<<"\"}\n";return z.str();};
    auto checkpoint=[&](){
      raw.flush();require(bool(raw),"raw write failed");sync_file(raw_path);
      std::string b;put(b,n64);put(b,dim);put(b,L);put(b,beta);put(b,seed);put(b,jhash);put(b,warm_target);put(b,init_code);put(b,warm_done);put(b,done);
      std::ostringstream ri,pi;ri<<rng;pi<<poisson;put_string(b,ri.str());put_string(b,pi.str());b.append(reinterpret_cast<char*>(spins.data()),n);
      std::string blob="LRIND003";put(blob,fnv(b.data(),b.size()));blob+=b;atomic_write(cp_path,blob);
      atomic_write(out_dir/"status.json",status());last_checkpoint=std::chrono::steady_clock::now();
    };
    std::signal(SIGUSR1,signal_handler);std::signal(SIGTERM,signal_handler);std::signal(SIGINT,signal_handler);
    checkpoint();
    while(warm_done<warm_target||done<target){
      if(stop_requested)break;
      std::fill(parent.begin(),parent.end(),-1);int64_t count=poisson(rng),active=0;
      for(int64_t z=0;z<count;z++){
        uint64_t u=rng();int d=int(u&mask);if(double(u>>bits)*inv>=prob[d])d=alias[d];
        int x=int(rng()&mask),y=addsite(x,d);if(spins[x]!=spins[y])continue;++active;
        x=root(parent,x);y=root(parent,y);if(x==y)continue;
        if(parent[x]>parent[y])std::swap(x,y);
        parent[x]+=parent[y];parent[y]=x;
      }
      double s2=0,s4=0;
      for(int i=0;i<n;i++)if(parent[i]<0){double c=-double(parent[i]),v=c*c;s2+=v;s4+=v*v;sign[i]=(rng()&1)?1:-1;}
      int64_t mag=0;for(int i=0;i<n;i++){int r=root(parent,i);spins[i]=sign[r];mag+=spins[i];}
      if(warm_done<warm_target)++warm_done;
      else {double row[4]={double(active),s2*norm2,(3*s2*s2-2*s4)*norm4,double(mag)*mag*norm2};raw.write(reinterpret_cast<char*>(row),32);++done;}
      ++call_sweeps;
      if(stop_after&&call_sweeps>=stop_after)break;
      // Timing checks are amortized; signal checks happen every full sweep.
      if((call_sweeps&255)==0){
        auto now=std::chrono::steady_clock::now();
        if(max_seconds>0&&elapsed()>=max_seconds)break;
        if(std::chrono::duration<double>(now-last_checkpoint).count()>=checkpoint_seconds){checkpoint();std::cout<<"committed "<<done<<" / "<<target<<" measurements\n"<<std::flush;}
      }
    }
    checkpoint();bool complete=(warm_done==warm_target&&done==target);
    if(complete)atomic_write(out_dir/"DONE.json",status());
    std::cout<<(complete?"COMPLETE ":"CHECKPOINTED ")<<status();
    return complete?0:75; // 75 = intentional resumable stop, not simulation failure
 }catch(const std::exception& e){std::cerr<<"ERROR: "<<e.what()<<"\n";return 1;}
}
