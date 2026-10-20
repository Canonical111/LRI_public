#include "kernel.hpp"
#include <chrono>
#include <iostream>
#include <memory>
#include <random>
#include <set>
#include <sstream>
#include <omp.h>
#if defined(__unix__) || defined(__APPLE__)
#include <sys/resource.h>
#endif
struct Task {uint64_t uid,rep,graph,begin,end,total;};
struct Row {std::array<ld,14> value{};uint64_t q=0,mp=0;ld maxabs=0;double seconds=0;};
// Process-wide resource counters do not instrument the numerical hot path.
// CPU time includes all OpenMP threads; task wall times can include preemption.
struct Resources {double user=-1,system=-1;long long peak_rss_kib=-1;};
Resources resources() {
    Resources out;
#if defined(__unix__) || defined(__APPLE__)
    rusage r{};
    if(getrusage(RUSAGE_SELF,&r)==0) {
        out.user=r.ru_utime.tv_sec+1e-6*r.ru_utime.tv_usec;
        out.system=r.ru_stime.tv_sec+1e-6*r.ru_stime.tv_usec;
        out.peak_rss_kib=r.ru_maxrss;
#if defined(__APPLE__)
        out.peak_rss_kib=(out.peak_rss_kib+1023)/1024;
#endif
    }
#endif
    return out;
}
struct Net {
    int dim,bits;const std::vector<uint64_t>&direction;std::vector<uint64_t>state;
    Net(int d,int b,const std::vector<uint64_t>&v,uint64_t seed,uint64_t begin):dim(d),bits(b),direction(v),state(d){
        std::mt19937_64 rng(seed);for(auto&s:state)s=rng()>>(64-bits);
        uint64_t gray=begin^(begin>>1);while(gray){int k=__builtin_ctzll(gray);gray&=gray-1;for(int j=0;j<dim;++j)state[j]^=direction[j*bits+k];}}
    void next(uint64_t n){int k=__builtin_ctzll(n);if(k>=bits)throw std::runtime_error("Sobol period exceeded");for(int j=0;j<dim;++j)state[j]^=direction[j*bits+k];}
    void point(ld*u)const {for(int j=0;j<dim;++j)u[j]=(ld(state[j])+.5L)/ld(uint64_t(1)<<bits);}
};
int main(int argc,char**argv){try {
    if(argc==2 && std::string(argv[1])=="--describe"){
    std::cout<<"{\"schema\":\"c8-d2-build-1\",\"dimension\":2,\"order\":8,\"compiler\":\""<<__VERSION__<<"\",\"boost_version\":\""<<BOOST_LIB_VERSION<<"\",\"long_double_bits\":"<<std::numeric_limits<ld>::digits<<",\"mp_backend\":\""<<mp_backend<<"\",\"mp_digits10\":"<<std::numeric_limits<MP>::digits10<<",\"mp_max_digits10\":"<<std::numeric_limits<MP>::max_digits10<<",\"openmp\":"<<_OPENMP<<"}\n";return 0;}
    if(argc!=12 && argc!=13){std::cerr<<"graphs_root gamma net tasks output seed layout rate threads sum_mode grid_or_dash [target_order=8]\n";return 1;}
    int target_order=argc==13?std::stoi(argv[12]):8;
    if(target_order!=7 && target_order!=8)throw std::runtime_error("target order must be 7 or 8");
    std::string root=argv[1],out=argv[5],mode=argv[10];uint64_t seed=std::stoull(argv[6]);int layout=std::stoi(argv[7]),threads=std::stoi(argv[9]);ld scale=std::stold(argv[8]);
    if(threads<1||layout<0||layout>2||!(scale>0&&scale<=1)|| (mode!="compensated"&&mode!="legacy"))throw std::runtime_error("bad execution options");
    std::ifstream tf(argv[4]);std::string magic;int L=0,nt=0;tf>>magic>>L>>nt;if((magic!="C8D2TASKS1" && !(magic=="C7D2TASKS1" && L<=7))||L<2||L>target_order||nt<1||nt>100000)throw std::runtime_error("invalid task header");
    std::vector<Task>tasks(nt);std::set<uint64_t>uids,graphs,reps;
    for(auto&t:tasks){tf>>t.uid>>t.rep>>t.graph>>t.begin>>t.end>>t.total;if(!tf||!uids.insert(t.uid).second||t.begin>=t.end||t.end>t.total||!t.total||(t.total&(t.total-1)))throw std::runtime_error("invalid or duplicate task");graphs.insert(t.graph);reps.insert(t.rep);}
    std::string extra;if(tf>>extra)throw std::runtime_error("extra task data");
    std::ifstream netf(argv[3],std::ios::binary);uint32_t head[3]{};netf.read(reinterpret_cast<char*>(head),sizeof(head));int B=head[0],dim=head[1],bits=head[2];
    if(!netf||B<2||dim!=(layout==2?2*L:4*L-1)||bits<32||bits>60||*reps.rbegin()>=uint64_t(B))throw std::runtime_error("bad net header");
    netf.seekg(0,std::ios::end);if(uint64_t(netf.tellg())!=12+uint64_t(B)*dim*bits*8)throw std::runtime_error("net file size mismatch");
    std::map<uint64_t,std::vector<uint64_t>>directions;for(auto rep:reps){auto&v=directions[rep];v.resize(dim*bits);netf.seekg(12+rep*dim*bits*8);netf.read(reinterpret_cast<char*>(v.data()),v.size()*8);if(!netf)throw std::runtime_error("truncated direction matrix");for(auto x:v)if(x>=(uint64_t(1)<<bits))throw std::runtime_error("invalid direction number");}
    for(auto&t:tasks)if(t.total>(uint64_t(1)<<bits))throw std::runtime_error("net period exceeded");
    int K=target_order-L;ld norm=0;std::array<ld,7>logs{};std::ifstream gamma(argv[2]);
    for(int l=2;l<=target_order;++l){int kl;ld nl;std::array<ld,7>v{};gamma>>kl>>nl;for(int j=0;j<target_order-1;++j)gamma>>v[j];
        if(!gamma||kl!=target_order-l)throw std::runtime_error("invalid gamma input for target order");if(l==L){norm=nl;logs=v;}}
    if(gamma>>extra)throw std::runtime_error("extra gamma input");
    if(!norm||!std::isfinite(norm))throw std::runtime_error("invalid normalization");
    std::map<uint64_t,Graph>loaded;double start=omp_get_wtime();for(auto id:graphs){auto g=load_graph(root+"/L"+std::to_string(L)+"/G"+std::to_string(id)+".txt",scale);if(g.id!=int(id)||g.L!=L)throw std::runtime_error("graph identity mismatch");loaded.emplace(id,std::move(g));}
    // Optional frozen grid. Reading it does not silently normalize its endpoints.
    using Grid=std::vector<std::array<ld,33>>;std::map<uint64_t,Grid>grids;
    if(std::string(argv[11])!="-"){std::ifstream gf(argv[11]);int n,e,nb;gf>>n>>e>>nb;if(!gf||n<1||e!=2*L-1||nb!=32)throw std::runtime_error("invalid grid header");std::set<int>seen;
        for(int k=0;k<n;++k){int id;gf>>id;if(!seen.insert(id).second)throw std::runtime_error("duplicate grid graph");Grid gr(e);for(auto&axis:gr){for(auto&x:axis)gf>>x;for(int j=0;j<32;++j)if(!std::isfinite(axis[j])||!std::isfinite(axis[j+1])||axis[j+1]<=axis[j])throw std::runtime_error("nonmonotonic grid");if(fabsl(axis[0])>1e-12L||fabsl(axis[32]-1)>1e-12L)throw std::runtime_error("grid endpoints outside tolerance");}if(graphs.count(id))grids.emplace(id,std::move(gr));}
        if(!gf||grids.size()!=graphs.size())throw std::runtime_error("missing grid rows");}
    double load_seconds=omp_get_wtime()-start;std::vector<Row>rows(nt);std::string error;int actual_threads=0;
    std::vector<int>order(nt);for(int i=0;i<nt;++i)order[i]=i;
    std::stable_sort(order.begin(),order.end(),[&](int a,int b){auto cost=[&](int i){auto&t=tasks[i];return ld(t.end-t.begin)*loaded.at(t.graph).addends.size();};return cost(a)>cost(b);});
    start=omp_get_wtime();
    #pragma omp parallel num_threads(threads)
    {
        Scratch scratch;
        #pragma omp single nowait
        actual_threads=omp_get_num_threads();
        #pragma omp for schedule(dynamic,1)
        for(int oi=0;oi<nt;++oi){int ti=order[oi];try {const auto&t=tasks[ti];const auto&g=loaded.at(t.graph);scratch.resize(g);Row&r=rows[ti];double t0=omp_get_wtime();
            Net net(dim,bits,directions.at(t.rep),seed+0x9e3779b97f4a7c15ULL*(t.rep+1)+0xbf58476d1ce4e5b9ULL*(g.id+1),t.begin);
            std::array<ld,32>u{};std::array<ld,7>sum{},comp{};auto git=grids.find(t.graph);
            for(uint64_t i=t.begin;i<t.end;++i){if(i>t.begin)net.next(i);net.point(u.data());ld jac=1;
                if(git!=grids.end())for(int j=0;j<g.E-1;++j){int ix=layout==0?2*j+1:(layout==2?j+1:j);ld y=u[ix]*32;int bin=std::min(31,int(y));const auto&axis=git->second[j];ld w=axis[bin+1]-axis[bin];u[ix]=axis[bin]+w*(y-bin);jac*=32*w;}
                int level;auto v=sample(g,u.data(),K,logs,level,layout,scratch);r.q+=level>=1;r.mp+=level>=2;
                for(int j=0;j<=K;++j){v[j]*=jac;if(!std::isfinite(v[j]))throw std::runtime_error("nonfinite jet");ld z=v[j]/t.total;
                    if(mode=="compensated"){ld y=z-comp[j],x=sum[j]+y;comp[j]=(x-sum[j])-y;sum[j]=x;}else sum[j]+=z;}
                r.maxabs=std::max(r.maxabs,fabsl(norm*(3*g.wb-g.wa)*v[0]));}
            for(int j=0;j<=K;++j){r.value[j]=norm*g.wa*sum[j];r.value[K+1+j]=norm*g.wb*sum[j];}r.seconds=omp_get_wtime()-t0;
        }catch(const std::exception&e){
            #pragma omp critical
            {if(error.empty())error=e.what();}
        }}
    }
    if(!error.empty())throw std::runtime_error(error);double seconds=omp_get_wtime()-start;
    const auto usage=resources();double task_seconds_sum=0;
    for(const auto&r:rows)task_seconds_sum+=r.seconds;
    // Native output goes only to a temporary file supplied by the checked Python publisher.
    std::ofstream f(out);if(!f)throw std::runtime_error("cannot open output");f<<std::setprecision(std::numeric_limits<ld>::max_digits10);
    f<<"{\"schema\":\"c8-d2-hpc-native-1\",\"order\":"<<target_order<<",\"L\":"<<L<<",\"seed\":"<<seed<<",\"layout\":"<<layout<<",\"bits\":"<<bits<<",\"rate\":\""<<scale<<"\",\"sum_mode\":\""<<mode<<"\",\"long_double_bits\":"<<std::numeric_limits<ld>::digits<<",\"mp_backend\":\""<<mp_backend<<"\",\"mp_digits10\":"<<std::numeric_limits<MP>::digits10<<",\"threads\":"<<threads<<",\"load_seconds\":"<<load_seconds<<",\"integration_seconds\":"<<seconds<<",\"graphs_loaded\":"<<loaded.size()<<",\"rows\":[";
    for(int i=0;i<nt;++i){if(i)f<<',';auto&t=tasks[i];auto&r=rows[i];f<<"{\"uid\":"<<t.uid<<",\"rep\":"<<t.rep<<",\"graph\":"<<t.graph<<",\"begin\":"<<t.begin<<",\"end\":"<<t.end<<",\"total\":"<<t.total<<",\"quad\":"<<r.q<<",\"mp\":"<<r.mp<<",\"seconds\":"<<r.seconds<<",\"max_abs\":\""<<r.maxabs<<"\",\"values\":[";for(int j=0;j<2*(K+1);++j){if(j)f<<',';f<<'"'<<r.value[j]<<'"';}f<<"]}";}f<<"],\"performance\":{\"actual_threads\":"<<actual_threads
     <<",\"task_wall_seconds_sum\":"<<task_seconds_sum
     <<",\"observed_task_parallelism\":"<<(seconds>0?task_seconds_sum/seconds:0)
     <<",\"wall_team_utilization\":"<<(seconds>0&&actual_threads>0?task_seconds_sum/(seconds*actual_threads):0)
     <<",\"cpu_user_seconds\":";
    auto optional_number=[&](auto value){if(value>=0)f<<value;else f<<"null";};
    optional_number(usage.user);f<<",\"cpu_system_seconds\":";optional_number(usage.system);
    f<<",\"peak_rss_kib\":";optional_number(usage.peak_rss_kib);f<<"}}\n";
    if(!f)throw std::runtime_error("output write failed");
    std::cerr<<"completed "<<nt<<" tasks, "<<loaded.size()<<" graphs; integration "<<seconds<<" s\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;} }
