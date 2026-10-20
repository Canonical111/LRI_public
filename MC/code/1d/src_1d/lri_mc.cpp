// d-dimensional long-range Ising, full periodic-image couplings: extended-Poisson SW (Fukui--Todo).
// C++17 / Linux-POSIX. One serial Markov chain; parallelize independent chains.
// No O(N^2) pair loop, no distance cutoff, and no fast-math requirement.
// Raw output is compatible with the previous exploratory simulator:
// little-endian f64: K,m2,m4,m2sample,[m6,m8,cmax,nclusters]. Version 5.
#include "xoshiro.hpp"
#include "alias.hpp"
#include "lattice.hpp"
#include "line_sampler.hpp"
#include <algorithm>
#include <sys/resource.h>
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
    while(p[x]>=0) { int y=p[x]; if(p[y]<0)return y; p[x]=p[y]; x=p[x]; } return x;
}
struct FileLock { int fd=-1;
    explicit FileLock(const fs::path& p) { fd=::open(p.c_str(),O_CREAT|O_RDWR,0664); require(fd>=0,"cannot open lock");
      if(::flock(fd,LOCK_EX|LOCK_NB)!=0) {::close(fd);fd=-1;throw std::runtime_error("another process holds this chain's output lock");} }
    ~FileLock(){ if(fd>=0) {::flock(fd,LOCK_UN);::close(fd);} }
};
int main(int argc,char** argv) {
 try {
    std::map<std::string,std::string> a;
    const std::vector<std::string> allowed={"dim","length","beta","couplings","measurements","warmup","seed","out","init","checkpoint-seconds","max-seconds","stop-after","sampler","core-radius","nn-extra","record","s","near-radius","batch"};
    for(int i=1;i<argc;i+=2) {
      std::string k=argv[i]; require(k.rfind("--",0)==0 && i+1<argc,"arguments must be --name value"); k=k.substr(2);
      require(std::find(allowed.begin(),allowed.end(),k)!=allowed.end(),"unknown option: "+k);
      require(a.emplace(k,argv[i+1]).second,"duplicate argument: "+k);
    }
    auto get=[&](const std::string& k,const std::string& def="") {auto it=a.find(k); if(it!=a.end())return it->second; require(!def.empty(),"missing --"+k);return def;};
    auto u64=[&](const std::string& k,const std::string& def="") {auto v=get(k,def);require(!v.empty()&&v[0]!='-',"invalid unsigned --"+k);size_t p=0;auto x=std::stoull(v,&p);require(p==v.size(),"invalid --"+k);return uint64_t(x);};
    #ifdef LRI_ONE_DIM
    require(u64("dim")==1,"this specialized binary requires --dim 1");
    constexpr int dim=1;int L=int(u64("length"));
#else
    int dim=int(u64("dim")),L=int(u64("length"));
#endif
    const std::string sampler=get("sampler",dim==1?"backbone":"hybrid");
    const bool line=(sampler=="line"||sampler=="backbone");
    const bool backbone=(sampler=="backbone");
    const int batch=int(u64("batch",line&&L>=(1<<20)?"256":"0"));require(batch>=0&&batch<=1024,"batch must be in [0,1024]");
    require(!batch||line,"batch optimization requires the line/backbone sampler");
    require(!line||dim==1,"line/backbone require dim=1");
    require(line||sampler=="flat"||sampler=="core"||(sampler=="lattice"||sampler=="hybrid"),"sampler must be backbone, line, flat, core, lattice, or hybrid");
    int radius=int(u64("core-radius",line?"256":((sampler=="lattice"||sampler=="hybrid")?"16":"2")));require(radius<=(line?4096:32),"core-radius too large");
    const int near_radius=int(u64("near-radius","1"));require(near_radius>=0&&near_radius<radius,"near-radius must be nonnegative and less than core-radius");
    const std::string record=get("record","extended");
    require(record=="extended"||record=="basic","record must be extended or basic");
    const uint32_t columns=record=="extended"?8:4; const uint64_t row_bytes=columns*8;
    double nn_extra=std::stod(get("nn-extra","0"));
    require(std::isfinite(nn_extra)&&nn_extra>=0,"nn-extra must be nonnegative");
    require(dim>=1&&dim<=3&&L>=2&&L<=(dim==1?(1<<28):(1<<20))&&!(L&(L-1)),"dim 1..3 and power-of-two length required");
    uint64_t n64=1;for(int z=0;z<dim;z++){n64*=L;require(n64<=(1ULL<<28),"N exceeds 2^28");}
    int lb=0;while((1<<lb)<L)++lb;int lm=L-1;
    auto inverse=[&](int r){int v=0;for(int z=0;z<dim;z++)v|=((-((r>>(z*lb))&lm))&lm)<<(z*lb);return v;};
    int n=int(n64); double beta=std::stod(get("beta"));
    uint64_t target=u64("measurements"),warm_target=u64("warmup","20000"),seed=u64("seed");
    double checkpoint_seconds=std::stod(get("checkpoint-seconds","600"));
    double max_seconds=std::stod(get("max-seconds","0")); uint64_t stop_after=u64("stop-after","0");
    std::string init=get("init","hot"); uint8_t init_code=init=="hot"?0:1;
    require(init=="hot"||init=="cold","--init must be hot or cold");
    require(std::isfinite(beta)&&beta>0&&target>0,"invalid beta or measurement count");
    require(target<std::numeric_limits<uint64_t>::max()/row_bytes,"output offset overflow");
    require(std::isfinite(checkpoint_seconds)&&checkpoint_seconds>0&&std::isfinite(max_seconds)&&max_seconds>=0,"invalid time interval");
    uint16_t endian=1;require(*reinterpret_cast<char*>(&endian)==1&&sizeof(double)==8,"little-endian binary64 host required");
    fs::path out_dir=get("out"); fs::create_directories(out_dir); FileLock lock(out_dir/"chain.lock");
    fs::path cp_path=out_dir/"checkpoint.bin", raw_path=out_dir/"samples.bin";
    const uint64_t mask0=uint64_t(L-1),mask1=mask0<<lb,mask2=mask0<<(2*lb);
    // Addition in alternating coordinate lanes prevents unwanted inter-lane carry.
    const uint64_t evenmask=mask0|(dim==3?mask2:0);
    const double exponent=std::stod(get("s","0"));
    double lambda=0,tail_fraction=0,sum=0;uint64_t jhash=0;
    Alias bulk,core;LatticeEnvelope infinite;LineEnvelope oned;
    if(line){
        oned.build(L,exponent,radius,near_radius,backbone,nn_extra);sum=2*oned.mass;
        tail_fraction=oned.tail_mass/oned.mass;
        std::ostringstream config;config<<std::setprecision(17)<<dim<<','<<L<<','<<exponent<<','<<nn_extra<<','<<radius<<','<<batch;
        std::string cfg=config.str();jhash=fnv(cfg.data(),cfg.size());
    }else if((sampler=="lattice"||sampler=="hybrid")){
        infinite.build(dim,L,exponent,radius,nn_extra,sampler=="hybrid",near_radius);sum=infinite.mass;
        tail_fraction=infinite.tail_mass/sum;
        std::ostringstream config;config<<std::setprecision(17)<<dim<<','<<L<<','<<exponent<<','<<nn_extra<<','<<radius;
        std::string cfg=config.str();jhash=fnv(cfg.data(),cfg.size());
    }else{
    fs::path j_path=get("couplings"); require(fs::file_size(j_path)==size_t(n)*8,"wrong coupling file size");
    std::vector<double> j(n); {std::ifstream f(j_path,std::ios::binary); f.read(reinterpret_cast<char*>(j.data()),n*8);require(bool(f),"cannot read couplings");}
    require(j[0]==0,"J[0] must be zero");
    // Optional additional ferromagnetic nearest-neighbour coupling. All fits
    // must group different nn-extra separately; it changes beta_c/corrections.
    if(nn_extra>0)for(int ax=0;ax<dim;++ax){j[1ULL<<(ax*lb)]+=nn_extra;j[uint64_t(L-1)<<(ax*lb)]+=nn_extra;}
    long double ss=0;
    for(double v:j){require(std::isfinite(v)&&v>=0,"bad coupling");ss+=v;}
    sum=double(ss); require(sum>0,"zero coupling sum");
    for(int r=1;r<n;r++)require(std::abs(j[r]-j[inverse(r)])<1e-12*sum,"couplings not symmetric");
    jhash=fnv(reinterpret_cast<const char*>(j.data()),n*8);

    if(sampler=="core"){
        std::vector<double> cw;std::vector<uint32_t> cv;
        long double tail=0;
        for(int r=0;r<n;++r){bool in=true;
            for(int ax=0;ax<dim;++ax){int c=(r>>(ax*lb))&lm;if(std::min(c,L-c)>radius){in=false;break;}}
            if(in&&j[r]>0){cw.push_back(j[r]);cv.push_back(uint32_t(r));j[r]=0;}
            else tail+=j[r];
        }
        if(tail>0){cw.push_back(double(tail));cv.push_back(UINT32_MAX);bulk.build(j);}
        core.build(cw,cv);tail_fraction=double(tail)/sum;
    }else bulk.build(j);
    std::vector<double>().swap(j);
    }
    lambda=beta*n*sum;require(std::isfinite(lambda)&&lambda<1e12,"Poisson rate out of supported range");
#ifdef LRI_MT
    using Random=std::mt19937_64;
    const std::string rng_name="mt19937_64";
#else
    using Random=Xoshiro256pp;
    const std::string rng_name="xoshiro256++";
#endif
    Random rng(seed);std::poisson_distribution<int64_t> poisson(lambda);
    std::vector<std::poisson_distribution<int64_t>> near_poisson;
    for(double w:(line?oned.near_weight:infinite.near_weight))near_poisson.emplace_back(beta*n*w);
    SmallPoisson local_count(backbone?2*beta*(1+nn_extra):1.0);
    std::vector<int8_t> spins(n);std::vector<int32_t> parent(n);
    uint64_t warm_done=0,done=0;
    if(fs::exists(cp_path)) {
      std::ifstream f(cp_path,std::ios::binary); std::string blob((std::istreambuf_iterator<char>(f)),{});
      require(blob.size()>16&&blob.substr(0,8)=="LRI1D102","invalid checkpoint magic");
      uint64_t stored;std::memcpy(&stored,blob.data()+8,8);std::string payload=blob.substr(16);
      require(fnv(payload.data(),payload.size())==stored,"checkpoint checksum mismatch");Reader r{payload};
      require(r.get<uint64_t>()==n64&&r.get<int>()==dim&&r.get<int>()==L&&r.get<double>()==beta&&r.get<uint64_t>()==seed&&r.get<uint64_t>()==jhash,"checkpoint configuration mismatch");
      require(r.get<uint64_t>()==warm_target&&r.get<uint8_t>()==init_code&&r.get<uint32_t>()==columns&&r.str()==sampler&&r.get<int>()==radius&&r.get<int>()==near_radius&&r.str()==rng_name&&r.get<double>()==nn_extra,"checkpoint warmup/initialization mismatch");
      warm_done=r.get<uint64_t>();done=r.get<uint64_t>();
      require(warm_done<=warm_target&&done<=target&&(done==0||warm_done==warm_target),"checkpoint progress incompatible with target");
      auto rs=r.str(),ps=r.str();std::istringstream ri(rs),pi(ps);ri>>rng;pi>>poisson;for(auto& dist:near_poisson)pi>>dist;
      require(bool(ri)&&bool(pi),"cannot restore RNG/distribution; use same compiler/standard library");
      require(r.p+size_t(n)==payload.size(),"invalid checkpoint spin data");std::memcpy(spins.data(),payload.data()+r.p,n);
      for(auto v:spins)require(v==1||v==-1,"bad spin in checkpoint");
      require(fs::exists(raw_path)&&fs::file_size(raw_path)>=done*row_bytes,"raw output shorter than committed checkpoint");
      fs::resize_file(raw_path,done*row_bytes); // drop records written after last committed checkpoint
      std::cout<<"Resumed warmup="<<warm_done<<" measurements="<<done<<"\n";
    } else {
      require(!fs::exists(raw_path)||fs::file_size(raw_path)==0,"raw output exists without checkpoint; refusing to overwrite");
      for(auto& v:spins)v=init=="cold"?1:((rng()&1)?1:-1);
    }
    // An old completion marker must not survive a requested extension.
    if(done<target&&fs::exists(out_dir/"DONE.json"))fs::remove(out_dir/"DONE.json");
    std::vector<char> iobuf(1<<20);std::ofstream raw;raw.rdbuf()->pubsetbuf(iobuf.data(),iobuf.size());raw.open(raw_path,std::ios::binary|std::ios::app);
    require(bool(raw),"cannot open raw output");
    uint64_t mask=n-1;double invn=1.0/n,norm2=invn*invn;
    auto start=std::chrono::steady_clock::now(),last_checkpoint=start;uint64_t call_sweeps=0;
    auto elapsed=[&](){return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
    auto status=[&](){std::ostringstream z;z<<std::setprecision(17)<<"{\"format\":5,\"engine\":\"1d\",\"record_columns\":"<<columns<<",\"batch\":"<<batch<<",\"sampler\":\""<<sampler<<"\",\"rng\":\""<<rng_name<<"\",\"nn_extra\":"<<nn_extra<<",\"s\":"<<exponent<<",\"near_radius\":"<<near_radius<<",\"core_radius\":"<<radius<<",\"remaining_proposal_rate_per_spin\":"<<lambda/n<<",\"tail_fraction\":"<<tail_fraction<<",\"N\":"<<n<<",\"d\":"<<dim<<",\"L\":"<<L<<",\"beta\":"<<beta<<",\"seed\":"<<seed<<",\"warmup_done\":"<<warm_done<<",\"measurements_done\":"<<done<<",\"measurements_target\":"<<target<<",\"committed_bytes\":"<<done*row_bytes<<",\"last_invocation_seconds\":"<<elapsed()<<",\"last_invocation_sweeps\":"<<call_sweeps<<",\"coupling_fnv64\":\""<<jhash<<"\"}\n";return z.str();};
    auto checkpoint=[&](){
      raw.flush();require(bool(raw),"raw write failed");sync_file(raw_path);
      std::string b;put(b,n64);put(b,dim);put(b,L);put(b,beta);put(b,seed);put(b,jhash);put(b,warm_target);put(b,init_code);put(b,columns);put_string(b,sampler);put(b,radius);put(b,near_radius);put_string(b,rng_name);put(b,nn_extra);put(b,warm_done);put(b,done);
      std::ostringstream ri,pi;ri<<rng;pi<<poisson;for(auto& dist:near_poisson)pi<<"\n"<<dist;put_string(b,ri.str());put_string(b,pi.str());b.append(reinterpret_cast<char*>(spins.data()),n);
      std::string blob="LRI1D102";put(blob,fnv(b.data(),b.size()));blob+=b;atomic_write(cp_path,blob);
      atomic_write(out_dir/"status.json",status());last_checkpoint=std::chrono::steady_clock::now();
    };
    std::signal(SIGUSR1,signal_handler);std::signal(SIGTERM,signal_handler);std::signal(SIGINT,signal_handler);
    checkpoint();
    while(warm_done<warm_target||done<target){
      if(stop_requested)break;
      int64_t count=poisson(rng),active=0;
      if(backbone){
          int r=0;parent[0]=-1;
          for(int i=1;i<n;++i){
              int k=(spins[i]==spins[i-1])?local_count.draw(rng):0;active+=k;
              if(k){parent[i]=r;--parent[r];}else{parent[i]=-1;r=i;}
          }
          int k=(spins[n-1]==spins[0])?local_count.draw(rng):0;active+=k;
          if(k&&r!=0){parent[0]+=parent[r];parent[r]=0;}
      }else std::fill(parent.begin(),parent.end(),-1);
      auto connect=[&](uint32_t disp,uint64_t xi){
        uint64_t yi=dim==1?((xi+disp)&mask):((((xi&evenmask)+(disp&evenmask))&evenmask)
                   |(((xi&mask1)+(disp&mask1))&mask1));
        int x=int(xi),y=int(yi);if(spins[x]!=spins[y])return;++active;
        x=root(parent,x);y=root(parent,y);if(x==y)return;
        if(parent[x]>parent[y])std::swap(x,y);
        parent[x]+=parent[y];parent[y]=x;
      };
      for(size_t q=0;q<near_poisson.size();++q){
          int64_t c=near_poisson[q](rng);uint32_t disp=line?oned.near_disp[q]:infinite.near_disp[q];
          int64_t z=0;
          for(;z+1<c;z+=2){uint64_t u=rng();connect(disp,u&mask);connect(disp,(u>>32)&mask);}
          if(z<c)connect(disp,rng()&mask);
      }
      auto displacement=[&](){
          if(line)return oned.draw(rng);
          if(sampler=="lattice"||sampler=="hybrid")return infinite.draw(rng);
          if(sampler=="core"){auto r=core.draw(rng);return r==UINT32_MAX?bulk.draw(rng):r;}
          return bulk.draw(rng);
      };
      if(batch){
          uint32_t xx[1024],rr[1024];
          for(int64_t offset=0;offset<count;offset+=batch){
              int used=0,nb=int(std::min<int64_t>(batch,count-offset));
              uint64_t sites=0;int available=0;
              for(int i=0;i<nb;++i){
                  uint32_t disp=displacement();if(disp==UINT32_MAX||disp==0)continue;
                  if(!available){sites=rng();available=2;}
                  uint32_t x=uint32_t(sites&mask);sites>>=32;--available;
                  xx[used]=x;rr[used]=disp;++used;
                  __builtin_prefetch(&spins[x],0,1);
                  __builtin_prefetch(&spins[(x+disp)&mask],0,1);
                  __builtin_prefetch(&parent[x],1,1);
                  __builtin_prefetch(&parent[(x+disp)&mask],1,1);
              }
              for(int i=0;i<used;++i)connect(rr[i],xx[i]);
          }
      }else{
      for(int64_t z=0;z<count;z++){
        uint32_t disp;
        if(line){disp=oned.draw(rng);if(disp==UINT32_MAX||disp==0)continue;}
        else if((sampler=="lattice"||sampler=="hybrid")){disp=infinite.draw(rng);if(disp==UINT32_MAX||disp==0)continue;}
        else if(sampler=="core"){disp=core.draw(rng);if(disp==UINT32_MAX)disp=bulk.draw(rng);}
        else disp=bulk.draw(rng);
        connect(disp,rng()&mask);
      }
      }
      double s2=0,s4=0,s6=0,s8=0,maxcluster=0;uint64_t clusters=0,sign_bits=0;int bits_left=0;int64_t mag=0;
      for(int i=0;i<n;i++)if(parent[i]<0){
          double c=-double(parent[i])*invn,v=c*c;s2+=v;s4+=v*v;
          if(columns==8){s6+=v*v*v;s8+=v*v*v*v;maxcluster=std::max(maxcluster,c);++clusters;}
          if(!bits_left){sign_bits=rng();bits_left=64;}
          spins[i]=(sign_bits&1)?1:-1;sign_bits>>=1;--bits_left;mag+=int64_t(-parent[i])*spins[i];
      }
      for(int i=0;i<n;i++){int r=root(parent,i);spins[i]=spins[r];}
      if(warm_done<warm_target)++warm_done;
      else {double row[8]={double(active),s2,3*s2*s2-2*s4,double(mag)*mag*norm2,
          15*s2*s2*s2-30*s2*s4+16*s6,
          105*s2*s2*s2*s2-420*s2*s2*s4+140*s4*s4+448*s2*s6-272*s8,
          maxcluster,double(clusters)};
          raw.write(reinterpret_cast<char*>(row),row_bytes);++done;}
      ++call_sweeps;
      if(stop_after&&call_sweeps>=stop_after)break;
      // Timing checks are amortized; signal checks happen every full sweep.
      if((n>(1<<22)||(call_sweeps&15)==0)){
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
