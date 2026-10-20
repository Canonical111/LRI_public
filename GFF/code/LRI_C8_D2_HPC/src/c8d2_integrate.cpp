// C8(2) native worker (PLAN.md component C). Order 7 replays C7(2) (loops 2-7, K = 7-L; bitwise C7(2)'s
// src/c7d2_integrate.cpp at a55958f); order 8 is production (loops 3-8 plus the L=2 control, K = 8-L). Every size
// comes from kernel.hpp's constants; the arithmetic, the stream mixing and the Kahan summation are C7(2)'s.
//   c8d2_{decimal,gmp} graphs_root gamma net tasks output seed layout rate threads sum_mode grid_or_dash
//   c8d2_{decimal,gmp} --describe
// tasks: "C8D2TASKS1 <order> <L> <nt>" then nt rows "uid rep graph begin end total".
// gamma: rows l = 2..order labelled order-l, each "label norm logs[0..order-2]" (exactly order-1 logs), then EOF.
// rate:  a decimal in (0, 1] applied to every graph, or @FILE: one "graph rate" line for exactly the graphs of the
//        task file (R7 only; the JSON then says "rate":"file" and echoes each row's rate).
// Rows carry the class-B tail fields (PLAN addition (ii), C63d's definition): with t = v_0*jac the weight-free base
// integrand at a point (before norm, the weights and the regulator jet), "tail_top" holds the 16 largest |t| of the
// row's points in descending order (fewer if the row has fewer points), "tail_sum" the long-double sum of |t| in point
// order, and "tail_argmax" the global point index of the first largest |t|. No existing value depends on them.
// Diagnostic build -DC8_ORDER_TRACE (A-KER-5, checkpoint review T-04; tests/validate.py, never accepted by plan): every
// iteration of the parallel task loop records the uid of the task it runs, and the JSON gains "addends" (each loaded
// graph's addends.size(), the ordering key) and "execution_order" (those uids in iteration order). No computed value
// changes; without the macro the preprocessed program is the production one.
#include "kernel.hpp"
#include <chrono>
#include <iostream>
#include <memory>
#include <random>
#include <set>
#include <sstream>
#include <sys/resource.h>
#include <omp.h>
constexpr int NTAIL=16;  // class-B tail fields: the 16 largest |t| of a row
struct Task {uint64_t uid,rep,graph,begin,end,total;};
struct Row {std::array<ld,NVALUES> value{};uint64_t q=0,mp=0;ld maxabs=0;double seconds=0;
    std::array<ld,NTAIL> tail_top{};int tail_n=0;ld tail_sum=0;uint64_t tail_argmax=0;};
struct Net {
    int dim,bits;const std::vector<uint64_t>&direction;std::vector<uint64_t>state;
    Net(int d,int b,const std::vector<uint64_t>&v,uint64_t seed,uint64_t begin):dim(d),bits(b),direction(v),state(d){
        std::mt19937_64 rng(seed);for(auto&s:state)s=rng()>>(64-bits);
        uint64_t gray=begin^(begin>>1);while(gray){int k=__builtin_ctzll(gray);gray&=gray-1;for(int j=0;j<dim;++j)state[j]^=direction[j*bits+k];}}
    void next(uint64_t n){int k=__builtin_ctzll(n);if(k>=bits)throw std::runtime_error("Sobol period exceeded");for(int j=0;j<dim;++j)state[j]^=direction[j*bits+k];}
    void point(ld*u)const {for(int j=0;j<dim;++j)u[j]=(ld(state[j])+.5L)/ld(uint64_t(1)<<bits);}
};
#ifndef C8_NO_TAIL_FIELDS
// One point's |t| into the row's tail fields: the sum in point order, the first index of the largest value, and the
// descending top NTAIL (an equal value never displaces an earlier one).
inline void tail_add(Row&r,ld a,uint64_t i){
    r.tail_sum+=a;
    if(r.tail_n==0||a>r.tail_top[0])r.tail_argmax=i;
    if(r.tail_n<NTAIL)++r.tail_n;else if(!(a>r.tail_top[NTAIL-1]))return;
    int k=r.tail_n-1;while(k>0&&r.tail_top[k-1]<a){r.tail_top[k]=r.tail_top[k-1];--k;}r.tail_top[k]=a;
}
#endif
// Diagnostic identity for --describe and the native JSON (plan refuses every diagnostic executable).
#if defined(C8_TIER_TIMERS) || defined(C8_RATIO_HISTOGRAM)
static constexpr const char* diagnostic_kind=C8_DIAGNOSTIC_KIND;
#elif defined(__SANITIZE_ADDRESS__) || defined(_GLIBCXX_ASSERTIONS)
static constexpr const char* diagnostic_kind="sanitize";
#elif defined(C8_NO_TAIL_FIELDS)
static constexpr const char* diagnostic_kind="no_tail_fields";
#elif defined(C8_ORDER_TRACE)
static constexpr const char* diagnostic_kind="order_trace";
#else
static constexpr const char* diagnostic_kind=nullptr;
#endif
// The numerics profile: "exact" (the default path), or the opt-in profile name that src/numerics/numerics.hpp builds
// from the C8_NUMERICS_<P> macros (Stage 4c, PLAN A-FLAG-1; `make gmp NUMERICS=<p>`).
#ifdef C8_NUMERICS
static constexpr const char* numerics_profile=nx::profile_name.s;
#else
static constexpr const char* numerics_profile="exact";
#endif
static ld parse_rate(const std::string&s,const std::string&what){
    size_t used=0;ld x=0;
    try{x=std::stold(s,&used);}catch(const std::exception&){used=0;}
    if(!used||used!=s.size()||!(x>0&&x<=1))throw std::runtime_error("invalid rate "+what+": '"+s+"' (a decimal in (0, 1] is required)");
    return x;
}
int main(int argc,char**argv){try {
    if(argc==2 && std::string(argv[1])=="--describe"){
    std::cout<<"{\"schema\":\"c8-d2-build-1\",\"dimension\":2,\"orders\":["<<ORDER_MIN<<","<<ORDER_MAX<<"],\"lmax\":"<<LMAX<<",\"kmax\":"<<KMAX<<",\"emax\":"<<EMAX<<",\"dimmax\":"<<DIMMAX
             <<",\"numerics\":\""<<numerics_profile<<"\",\"diagnostic\":"<<(diagnostic_kind?"true":"false");
    if(diagnostic_kind)std::cout<<",\"diagnostic_kind\":\""<<diagnostic_kind<<"\"";
    C8_NX_DESCRIBE(std::cout)
#ifdef C8_NO_TAIL_FIELDS
    std::cout<<",\"tail_top\":0";
#else
    std::cout<<",\"tail_top\":"<<NTAIL;
#endif
    std::cout<<",\"compiler\":\""<<__VERSION__<<"\",\"long_double_bits\":"<<std::numeric_limits<ld>::digits<<",\"mp_backend\":\""<<mp_backend<<"\",\"mp_digits10\":"<<std::numeric_limits<MP>::digits10<<",\"mp_max_digits10\":"<<std::numeric_limits<MP>::max_digits10<<",\"openmp\":"<<_OPENMP<<"}\n";return 0;}
    if(argc!=12){std::cerr<<"graphs_root gamma net tasks output seed layout rate threads sum_mode grid_or_dash\n";return 1;}
    std::string root=argv[1],out=argv[5],mode=argv[10],rate_arg=argv[8];uint64_t seed=std::stoull(argv[6]);int layout=std::stoi(argv[7]),threads=std::stoi(argv[9]);
    const bool rate_file=!rate_arg.empty()&&rate_arg[0]=='@';ld scale=rate_file?1:parse_rate(rate_arg,"argument");
    if(threads<1||layout<0||layout>2|| (mode!="compensated"&&mode!="legacy"))throw std::runtime_error("bad execution options");
    std::ifstream tf(argv[4]);std::string magic;int order=0,L=0,nt=0;tf>>magic>>order>>L>>nt;
    if(!tf||magic!="C8D2TASKS1")throw std::runtime_error("invalid task header: expected C8D2TASKS1 <order> <L> <nt>");
    if(order<ORDER_MIN||order>ORDER_MAX)throw std::runtime_error("task order "+std::to_string(order)+" outside ["+std::to_string(ORDER_MIN)+", "+std::to_string(ORDER_MAX)+"]");
    if(L<2||L>order||L>LMAX)throw std::runtime_error("task L="+std::to_string(L)+" outside [2, order="+std::to_string(order)+"]");
    if(nt<1||nt>100000)throw std::runtime_error("invalid task count "+std::to_string(nt));
    std::vector<Task>tasks(nt);std::set<uint64_t>uids,graphs,reps;
    for(auto&t:tasks){tf>>t.uid>>t.rep>>t.graph>>t.begin>>t.end>>t.total;if(!tf||!uids.insert(t.uid).second||t.begin>=t.end||t.end>t.total||!t.total||(t.total&(t.total-1)))throw std::runtime_error("invalid or duplicate task");graphs.insert(t.graph);reps.insert(t.rep);}
    std::string extra;if(tf>>extra)throw std::runtime_error("extra task data");
    std::ifstream netf(argv[3],std::ios::binary);uint32_t head[3]={0,0,0};netf.read(reinterpret_cast<char*>(head),sizeof(head));
    if(!netf)throw std::runtime_error("cannot read the net header");
    int B=head[0],dim=head[1],bits=head[2];
    if(head[1]>uint32_t(DIMMAX))throw std::runtime_error("net dimension "+std::to_string(head[1])+" exceeds DIMMAX="+std::to_string(DIMMAX));
    if(B<2||dim!=(layout==2?2*L:4*L-1)||bits<32||bits>60||*reps.rbegin()>=uint64_t(B))throw std::runtime_error("bad net header");
    netf.seekg(0,std::ios::end);if(uint64_t(netf.tellg())!=12+uint64_t(B)*dim*bits*8)throw std::runtime_error("net file size mismatch");
    std::map<uint64_t,std::vector<uint64_t>>directions;for(auto rep:reps){auto&v=directions[rep];v.resize(dim*bits);netf.seekg(12+rep*dim*bits*8);netf.read(reinterpret_cast<char*>(v.data()),v.size()*8);if(!netf)throw std::runtime_error("truncated direction matrix");for(auto x:v)if(x>=(uint64_t(1)<<bits))throw std::runtime_error("invalid direction number");}
    for(auto&t:tasks)if(t.total>(uint64_t(1)<<bits))throw std::runtime_error("net period exceeded");
    // Gamma rows l = 2..order: "label norm logs[0..order-2]", label order-l, exactly order-1 logs, then end of file. An
    // order-8 task given gamma_d2_7.txt (or the reverse) fails the label check of its first row.
    int K=order-L;if(K<0||K>KMAX)throw std::runtime_error("jet order K="+std::to_string(K)+" outside [0, KMAX="+std::to_string(KMAX)+"]");
    ld norm=0;std::array<ld,NLOGS>logs{};std::ifstream gamma(argv[2]);if(!gamma)throw std::runtime_error(std::string("cannot open gamma file ")+argv[2]);
    for(int l=2;l<=order;++l){std::string line;if(!std::getline(gamma,line))throw std::runtime_error("gamma file: missing the row of L="+std::to_string(l)+" (order "+std::to_string(order)+")");
        std::istringstream is(line);int kl;is>>kl;if(!is)throw std::runtime_error("gamma file: unreadable label in the row of L="+std::to_string(l));
        if(kl!=order-l)throw std::runtime_error("gamma label mismatch: the row of L="+std::to_string(l)+" has label "+std::to_string(kl)+", expected order-L="+std::to_string(order-l)+" (a gamma file of another order?)");
        ld nl;std::array<ld,NLOGS>v{};is>>nl;for(int j=0;j<order-1;++j)is>>v[j];
        if(!is)throw std::runtime_error("gamma file: the row of L="+std::to_string(l)+" has fewer than "+std::to_string(order-1)+" log values (a gamma file of another order?)");
        std::string more;if(is>>more)throw std::runtime_error("gamma file: trailing token '"+more+"' in the row of L="+std::to_string(l)+" (exactly "+std::to_string(order-1)+" log values per row at order "+std::to_string(order)+")");
        if(l==L){norm=nl;logs=v;}}
    {std::string more;if(gamma>>more)throw std::runtime_error("gamma file: data after the row of L="+std::to_string(order)+": '"+more+"'");}
    if(!norm||!std::isfinite(norm))throw std::runtime_error("invalid normalization");
    // Rates: one scalar for every graph, or the @FILE map, which must cover exactly the graphs of the task file.
    std::map<uint64_t,ld>rate_of;
    if(rate_file){std::string path=rate_arg.substr(1);std::ifstream rf(path);if(!rf)throw std::runtime_error("cannot open rate file "+path);
        std::string line;size_t lineno=0;
        while(std::getline(rf,line)){++lineno;std::istringstream is(line);std::string gtok,rtok,more;
            if(!(is>>gtok>>rtok)||(is>>more))throw std::runtime_error("rate file "+path+" line "+std::to_string(lineno)+": expected exactly 'graph rate'");
            if(gtok.empty()||gtok.size()>20||gtok.find_first_not_of("0123456789")!=std::string::npos)throw std::runtime_error("rate file "+path+" line "+std::to_string(lineno)+": invalid graph id '"+gtok+"'");
            uint64_t gid=0;try{gid=std::stoull(gtok);}catch(const std::exception&){throw std::runtime_error("rate file "+path+" line "+std::to_string(lineno)+": invalid graph id '"+gtok+"'");}
            if(!rate_of.emplace(gid,parse_rate(rtok,"for graph "+gtok+" in "+path)).second)throw std::runtime_error("rate file "+path+": duplicate graph "+gtok);}
        if(rf.bad())throw std::runtime_error("cannot read rate file "+path);
        for(auto id:graphs)if(!rate_of.count(id))throw std::runtime_error("rate file "+path+" has no rate for graph "+std::to_string(id)+" of the task file");
        for(auto&kv:rate_of)if(!graphs.count(kv.first))throw std::runtime_error("rate file "+path+" lists graph "+std::to_string(kv.first)+", which is not in the task file");}
    // Parallel graph loading (R5a, Stage 4b): one graph per iteration (dynamic,1) into its own slot of a pre-sized
    // vector, ids ascending, so the block's threads (pinned to the lane's cores) first-touch the graphs they load.
    // Loading is pure I/O and parsing: no value depends on the thread. Errors are kept per slot and the lowest graph
    // id's is thrown, the error the serial loop threw first; `loaded` indexes the slots by id.
    const std::vector<uint64_t>ids(graphs.begin(),graphs.end());std::vector<Graph>slots(ids.size());std::map<uint64_t,const Graph*>loaded;double start=omp_get_wtime();
    {const int ng=int(ids.size());std::vector<char>failed(ng,0);std::vector<std::string>why(ng);
    #pragma omp parallel for num_threads(threads) schedule(dynamic,1)
    for(int k=0;k<ng;++k){const uint64_t id=ids[k];
        try{auto g=load_graph(root+"/L"+std::to_string(L)+"/G"+std::to_string(id)+".txt",rate_file?rate_of.at(id):scale);if(g.id!=int(id)||g.L!=L)throw std::runtime_error("graph identity mismatch");slots[k]=std::move(g);}
        catch(const std::exception&e){failed[k]=1;why[k]=e.what();}}
    for(int k=0;k<ng;++k)if(failed[k])throw std::runtime_error(why[k]);}
    for(size_t k=0;k<ids.size();++k)loaded.emplace(ids[k],&slots[k]);
    // Optional frozen grid. Reading it does not silently normalize its endpoints.
    using Grid=std::vector<std::array<ld,33>>;std::map<uint64_t,Grid>grids;
    if(std::string(argv[11])!="-"){std::ifstream gf(argv[11]);int n,e,nb;gf>>n>>e>>nb;if(!gf||n<1||e!=2*L-1||nb!=32)throw std::runtime_error("invalid grid header");std::set<int>seen;
        for(int k=0;k<n;++k){int id;gf>>id;if(!seen.insert(id).second)throw std::runtime_error("duplicate grid graph");Grid gr(e);for(auto&axis:gr){for(auto&x:axis)gf>>x;for(int j=0;j<32;++j)if(!std::isfinite(axis[j])||!std::isfinite(axis[j+1])||axis[j+1]<=axis[j])throw std::runtime_error("nonmonotonic grid");if(fabsl(axis[0])>1e-12L||fabsl(axis[32]-1)>1e-12L)throw std::runtime_error("grid endpoints outside tolerance");}if(graphs.count(id))grids.emplace(id,std::move(gr));}
        if(!gf||grids.size()!=graphs.size())throw std::runtime_error("missing grid rows");}
    double load_seconds=omp_get_wtime()-start;std::vector<Row>rows(nt);std::string error;
    std::vector<int>order_of(nt);for(int i=0;i<nt;++i)order_of[i]=i;
    std::stable_sort(order_of.begin(),order_of.end(),[&](int a,int b){auto cost=[&](int i){auto&t=tasks[i];return ld(t.end-t.begin)*loaded.at(t.graph)->addends.size();};return cost(a)>cost(b);});
#ifdef C8_ORDER_TRACE
    std::vector<uint64_t>trace(nt,UINT64_MAX);
#endif
#if defined(C8_TIER_TIMERS) || defined(C8_RATIO_HISTOGRAM)
    Diagnostics diagnostics;
#endif
    start=omp_get_wtime();
    #pragma omp parallel num_threads(threads)
    {
        Scratch scratch;
#if defined(C8_TIER_TIMERS) || defined(C8_RATIO_HISTOGRAM)
        diagnostics_reset();
#endif
        #pragma omp for schedule(dynamic,1)
        for(int oi=0;oi<nt;++oi){int ti=order_of[oi];
#ifdef C8_ORDER_TRACE
            trace[oi]=tasks[ti].uid;
#endif
            try {const auto&t=tasks[ti];const auto&g=*loaded.at(t.graph);scratch.resize(g);Row&r=rows[ti];double t0=omp_get_wtime();
            Net net(dim,bits,directions.at(t.rep),seed+0x9e3779b97f4a7c15ULL*(t.rep+1)+0xbf58476d1ce4e5b9ULL*(g.id+1),t.begin);
            std::array<ld,DIMMAX>u{};std::array<ld,NLOGS>sum{},comp{};auto git=grids.find(t.graph);
            for(uint64_t i=t.begin;i<t.end;++i){if(i>t.begin)net.next(i);net.point(u.data());ld jac=1;
                if(git!=grids.end())for(int j=0;j<g.E-1;++j){int ix=layout==0?2*j+1:(layout==2?j+1:j);ld y=u[ix]*32;int bin=std::min(31,int(y));const auto&axis=git->second[j];ld w=axis[bin+1]-axis[bin];u[ix]=axis[bin]+w*(y-bin);jac*=32*w;}
                int level;auto v=sample(g,u.data(),K,logs,level,layout,scratch);r.q+=level>=1;r.mp+=level>=2;
                for(int j=0;j<=K;++j){v[j]*=jac;if(!std::isfinite(v[j]))throw std::runtime_error("nonfinite jet");ld z=v[j]/t.total;
                    if(mode=="compensated"){ld y=z-comp[j],x=sum[j]+y;comp[j]=(x-sum[j])-y;sum[j]=x;}else sum[j]+=z;}
                r.maxabs=std::max(r.maxabs,fabsl(norm*(3*g.wb-g.wa)*v[0]));
#ifndef C8_NO_TAIL_FIELDS
                tail_add(r,fabsl(v[0]),i);
#endif
            }
            for(int j=0;j<=K;++j){r.value[j]=norm*g.wa*sum[j];r.value[K+1+j]=norm*g.wb*sum[j];}r.seconds=omp_get_wtime()-t0;
        }catch(const std::exception&e){
            #pragma omp critical
            {if(error.empty())error=e.what();}
        }}
#if defined(C8_TIER_TIMERS) || defined(C8_RATIO_HISTOGRAM)
        #pragma omp critical
        {diagnostics.add(thread_diagnostics());}
#endif
    }
    if(!error.empty())throw std::runtime_error(error);double seconds=omp_get_wtime()-start;
    // Peak resident set of this process image: VmHWM of /proc/self/status (Linux). getrusage's ru_maxrss is only the
    // fallback: on Linux it also counts the pre-exec image, i.e. the forking Python parent's RSS.
    long max_rss_kb=-1;const char*rss_source="VmHWM";
    {std::ifstream st("/proc/self/status");std::string key;while(st>>key){if(key=="VmHWM:"){st>>max_rss_kb;break;}std::getline(st,key);}}
    if(max_rss_kb<0){struct rusage usage{};getrusage(RUSAGE_SELF,&usage);max_rss_kb=usage.ru_maxrss;rss_source="getrusage";
#ifdef __APPLE__
        max_rss_kb/=1024;  // macOS reports bytes
#endif
    }
    // Native output goes only to a temporary file supplied by the checked Python publisher.
    std::ofstream f(out);if(!f)throw std::runtime_error("cannot open output");f<<std::setprecision(std::numeric_limits<ld>::max_digits10);
    f<<"{\"schema\":\"c8-d2-hpc-native-1\",\"order\":"<<order<<",\"L\":"<<L<<",\"seed\":"<<seed<<",\"layout\":"<<layout<<",\"bits\":"<<bits<<",\"rate\":\"";
    if(rate_file)f<<"file";else f<<scale;
    f<<"\",\"sum_mode\":\""<<mode<<"\",\"long_double_bits\":"<<std::numeric_limits<ld>::digits<<",\"mp_backend\":\""<<mp_backend<<"\",\"mp_digits10\":"<<std::numeric_limits<MP>::digits10<<",\"numerics\":\""<<numerics_profile<<"\",\"threads\":"<<threads<<",\"load_seconds\":"<<load_seconds<<",\"integration_seconds\":"<<seconds<<",\"graphs_loaded\":"<<loaded.size()<<",\"max_rss_kb\":"<<max_rss_kb<<",\"max_rss_source\":\""<<rss_source<<"\"";
    if(diagnostic_kind)f<<",\"diagnostic\":\""<<diagnostic_kind<<"\"";
    C8_NX_DESCRIBE(f)
#if defined(C8_TIER_TIMERS) || defined(C8_RATIO_HISTOGRAM)
    diagnostics_json(f,diagnostics);
#endif
#ifdef C8_ORDER_TRACE
    f<<",\"addends\":{";{bool first=true;for(auto&kv:loaded){if(!first)f<<',';first=false;f<<'"'<<kv.first<<"\":"<<kv.second->addends.size();}}
    f<<"},\"execution_order\":[";for(int i=0;i<nt;++i){if(i)f<<',';f<<trace[i];}f<<"]";
#endif
    f<<",\"rows\":[";
    for(int i=0;i<nt;++i){if(i)f<<',';auto&t=tasks[i];auto&r=rows[i];f<<"{\"uid\":"<<t.uid<<",\"rep\":"<<t.rep<<",\"graph\":"<<t.graph<<",\"begin\":"<<t.begin<<",\"end\":"<<t.end<<",\"total\":"<<t.total<<",\"quad\":"<<r.q<<",\"mp\":"<<r.mp<<",\"seconds\":"<<r.seconds<<",\"max_abs\":\""<<r.maxabs<<"\",\"values\":[";for(int j=0;j<2*(K+1);++j){if(j)f<<',';f<<'"'<<r.value[j]<<'"';}f<<"]";
#ifndef C8_NO_TAIL_FIELDS
        f<<",\"tail_top\":[";for(int j=0;j<r.tail_n;++j){if(j)f<<',';f<<'"'<<r.tail_top[j]<<'"';}f<<"],\"tail_sum\":\""<<r.tail_sum<<"\",\"tail_argmax\":"<<r.tail_argmax;
#endif
        if(rate_file)f<<",\"rate\":\""<<rate_of.at(t.graph)<<"\"";
        f<<"}";}f<<"]}\n";if(!f)throw std::runtime_error("output write failed");
    std::cerr<<"completed "<<nt<<" tasks, "<<loaded.size()<<" graphs; integration "<<seconds<<" s\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;} }
