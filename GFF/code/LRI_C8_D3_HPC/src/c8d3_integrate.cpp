// C8(3) native worker (PLAN.md component C; HD2, HD3). One binary, two orders: order 7 replays C7(3) (loops 2-7,
// K = 7-L, gamma_d3_7.txt) and is bitwise a6ce987's src/c7d3_integrate.cpp on the same toolchain in every row field the
// C7 worker writes (A-RPL-1); order 8 is production (loops 3-8 plus the L=2 control, K = 8-L, gamma_d3_8.txt), and its
// slots z^0..z^(7-L) are bitwise those of order 7 (A-RPL-2). The arithmetic, the stream mixing, the Kahan summation,
// max_abs and the in-block order by points x addends are C7(3)'s (C.9).
//   c8d3_{gmp,decimal} graphs_root gamma net tasks output seed layout rate threads sum_mode grid_or_dash [--mp-check on|off|stride16]
//   c8d3_{gmp,decimal} --describe
// tasks: "C8D3TASKS1 <order> <L> <nt>" (order 7 or 8, 2 <= L <= order, 1 <= nt <= 100,000), or C7(3)'s
//        "C7D3TASKS1 <L> <nt>", read as order 7 (input only; 2 <= L <= 7), then nt rows "uid rep graph begin end total".
// gamma: rows l = 2..order labelled order-l, each "label norm logs[0..order-2]" (exactly order-1 logs), then end of
//        file; an order-8 task given gamma_d3_7.txt, or the reverse, fails the label check of the first row.
// Every task, net, gamma, grid and graph error names its file and exits 2 (C.2, A-KER-1).
// Class-B outputs (C.3, C.4; no value, counter or max_abs depends on them, A-KER-6):
//  * per row, with t = v_0*jac the weight-free base integrand at a point (v[0] after the Jacobian multiplication,
//    before norm, the weights and the regulator jet): "tail_top" the TAILK = 16 largest |t| of the row's points in
//    descending order (fewer if the row has fewer points; an equal value never displaces an earlier one), "tail_sum"
//    the long-double sum of |t| in point order, "tail_argmax" the global point index of the first largest |t|;
//  * per row "nondirect" (points with some log-coordinate outside [-600, 0], i.e. evaluated with a shift; every
//    log-coordinate is <= 0 and only the first is 0, so these are exactly the points with shift != 0) and
//    "nonmoderate" (points evaluated by calculate_reference<ld>);
//  * with --mp-check on (every MP point) or stride16 (the MP points whose global point index is = 0 mod 16), the MP
//    tier runs with its error estimate (calculate_shared<MP,true>, the same value) and each row gains "mp_checked",
//    "mp_hist" (18 counts of x = log10(|v|/err) at the MP tier: x >= -20, then [-40,-20), ..., [-340,-320), then
//    x < -340), "mp_min_log10" and "mp_alarm" (points with x < -320, i.e. fewer than 30 of 350 digits left).
// Test-only builds: -DC8_NO_TAIL_FIELDS (no tail fields; A-KER-6 (a)), -DC8_ORDER_TRACE (the in-block execution order
// and each graph's addends.size(); A-KER-5); the diagnostic builds of C.5. All report "diagnostic":true.
#include "kernel.hpp"
#include "stream.hpp"
#include "identity.hpp"
#include <cassert>
#include <iostream>
#include <memory>
#include <set>
#include <sstream>
#include <sys/resource.h>
#include <omp.h>
struct Task {uint64_t uid,rep,graph,begin,end,total;};
constexpr int MPBINS=18;  // x >= -20, [-40,-20), ..., [-340,-320), x < -340
struct Row {std::array<ld,NVALUES> value{};uint64_t q=0,mp=0;ld maxabs=0;double seconds=0;
    std::array<ld,TAILK> tail_top{};int tail_n=0;ld tail_sum=0;uint64_t tail_argmax=0;
    uint64_t nondirect=0,nonmoderate=0,mp_checked=0,mp_alarm=0;std::array<uint64_t,MPBINS> mp_hist{};
    ld mp_min_log10=std::numeric_limits<ld>::infinity();};
#ifndef C8_NO_TAIL_FIELDS
// One point's |t| into the row's tail fields: the sum in point order, the first index of the largest value, and the
// descending top TAILK (an equal value never displaces an earlier one).
inline void tail_add(Row&r,ld a,uint64_t i){
    r.tail_sum+=a;
    if(r.tail_n==0||a>r.tail_top[0])r.tail_argmax=i;
    if(r.tail_n<TAILK)++r.tail_n;else if(!(a>r.tail_top[TAILK-1]))return;
    int k=r.tail_n-1;while(k>0&&r.tail_top[k-1]<a){r.tail_top[k]=r.tail_top[k-1];--k;}r.tail_top[k]=a;
}
#endif
inline int mp_bin(ld x){if(x>=-20)return 0;if(!(x>=-340))return MPBINS-1;int k=int(ceill(-x/20))-1;return std::min(std::max(k,1),MPBINS-2);}
enum {MP_OFF=0,MP_ON=1,MP_STRIDE16=2};
static const char* mp_mode_name(int m){return m==MP_ON?"on":m==MP_STRIDE16?"stride16":"off";}
[[noreturn]] static void fail(const std::string&s){throw std::runtime_error(s);}
static std::string shown(const std::string&s){return "'"+printable(s)+"'";}
int main(int argc,char**argv){try {
    if(argc==2 && std::string(argv[1])=="--describe"){
        bool mismatch=false;std::string common=describe_common(mismatch);
#ifdef C8_NO_TAIL_FIELDS
        const int tail=0;
#else
        const int tail=TAILK;
#endif
        std::cout<<"{\"schema\":\"c8-d3-build-1\","<<common<<",\"tail_top\":"<<tail<<",\"mp_check_modes\":[\"off\",\"on\",\"stride16\"]}\n";
        if(mismatch){std::cerr<<"gmp.h and the loaded libgmp differ in version\n";return 3;}
        return 0;}
    if(argc!=12&&argc!=14){std::cerr<<"graphs_root gamma net tasks output seed layout rate threads sum_mode grid_or_dash [--mp-check on|off|stride16]\n";return 1;}
    bool gmp_mismatch=false;const std::string gmp=gmp_block(gmp_mismatch);
    if(gmp_mismatch){std::cerr<<"refusing to run: gmp.h and the loaded libgmp differ in version: "<<gmp<<"\n";return 3;}
    int mpmode=MP_OFF;
    if(argc==14){std::string flag=argv[12],v=argv[13];
        if(flag!="--mp-check")fail("unknown option "+shown(flag)+" (only --mp-check on|off|stride16 may follow the 11 arguments)");
        if(v=="on")mpmode=MP_ON;else if(v=="off")mpmode=MP_OFF;else if(v=="stride16")mpmode=MP_STRIDE16;else fail("--mp-check: "+shown(v)+" is not on, off or stride16");}
    std::string root=argv[1],gammapath=argv[2],netpath=argv[3],taskpath=argv[4],out=argv[5],mode=argv[10],gridarg=argv[11];
    uint64_t seed=0;int layout=0,threads=0;ld scale=0;
    try{seed=std::stoull(argv[6]);layout=std::stoi(argv[7]);threads=std::stoi(argv[9]);scale=std::stold(argv[8]);}catch(const std::exception&){fail("bad execution options (seed, layout, rate or threads unreadable)");}
    if(threads<1||layout<0||layout>2||!(scale>0&&scale<=1)|| (mode!="compensated"&&mode!="legacy"))fail("bad execution options");
    // The task file (HD3): every token is extracted and the stream tested before any comparison.
    std::ifstream tf(taskpath);if(!tf)fail(taskpath+": cannot open the task file");
    std::string magic;int order=0,L=0,nt=0;bool legacy=false;
    if(!(tf>>magic))fail(taskpath+": truncated or malformed task header (magic)");
    if(magic=="C8D3TASKS1"){if(!(tf>>order))fail(taskpath+": truncated or malformed task header (order)");}
    else if(magic=="C7D3TASKS1"){order=7;legacy=true;}
    else fail(taskpath+": task magic "+shown(magic)+" is neither C8D3TASKS1 <order> <L> <nt> nor C7D3TASKS1 <L> <nt>");
    if(!(tf>>L))fail(taskpath+": truncated or malformed task header (L)");
    if(!(tf>>nt))fail(taskpath+": truncated or malformed task header (task count)");
    if(order<ORDER_MIN||order>ORDER_MAX)fail(taskpath+": order "+std::to_string(order)+" out of range ["+std::to_string(ORDER_MIN)+","+std::to_string(ORDER_MAX)+"]");
    if(L<2||L>order)fail(taskpath+": L "+std::to_string(L)+" out of range [2, order = "+std::to_string(order)+"]"+(legacy?" (C7D3TASKS1 is an order-7 task file)":""));
    if(nt<1||nt>100000)fail(taskpath+": task count "+std::to_string(nt)+" out of range [1,100000]");
    std::vector<Task>tasks(nt);std::set<uint64_t>uids,graphs,reps;
    for(int k=0;k<nt;++k){auto&t=tasks[k];
        if(!(tf>>t.uid>>t.rep>>t.graph>>t.begin>>t.end>>t.total))fail(taskpath+": truncated or malformed task row "+std::to_string(k));
        if(!uids.insert(t.uid).second||t.begin>=t.end||t.end>t.total||!t.total||(t.total&(t.total-1)))fail(taskpath+": invalid or duplicate task (row "+std::to_string(k)+", uid "+std::to_string(t.uid)+")");
        if(t.graph>uint64_t(std::numeric_limits<int>::max()))fail(taskpath+": graph id "+std::to_string(t.graph)+" out of range (row "+std::to_string(k)+")");
        graphs.insert(t.graph);reps.insert(t.rep);}
    {std::string extra;if(tf>>extra)fail(taskpath+": extra task data "+shown(extra));}
    // The net (C.2: the header is initialized and tested before B, dim and bits are formed; dim <= DIMMAX).
    const NetFile netf=read_net(netpath,layout,L,reps);const int dim=netf.dim,bits=netf.bits;
    for(auto&t:tasks)if(t.total>(uint64_t(1)<<bits))fail(taskpath+": net period exceeded (task uid "+std::to_string(t.uid)+" total "+std::to_string(t.total)+" > 2^"+std::to_string(bits)+" of "+netpath+")");
    // The gamma rows (HD3, DECISIONS B1).
    const int K=order-L;if(K<0||K>KMAX)fail(taskpath+": jet order K = "+std::to_string(K)+" outside [0, KMAX = "+std::to_string(KMAX)+"]");
    ld norm=0;std::array<ld,NLOGS>logs{};
    {std::ifstream gamma(gammapath);if(!gamma)fail(gammapath+": cannot open the gamma file");
     for(int l=2;l<=order;++l){std::string line;
        if(!std::getline(gamma,line))fail(gammapath+": missing the row of L="+std::to_string(l)+" (an order-"+std::to_string(order)+" gamma file has rows L = 2.."+std::to_string(order)+")");
        std::istringstream is(line);int kl=0;if(!(is>>kl))fail(gammapath+": truncated or malformed label in the row of L="+std::to_string(l));
        if(kl!=order-l)fail(gammapath+": gamma label mismatch: the row of L="+std::to_string(l)+" has label "+std::to_string(kl)+", expected order-L = "+std::to_string(order-l)+" (a gamma file of another order?)");
        ld nl=0;std::array<ld,NLOGS>v{};if(!(is>>nl))fail(gammapath+": truncated or malformed norm in the row of L="+std::to_string(l));
        for(int j=0;j<order-1;++j)if(!(is>>v[j]))fail(gammapath+": the row of L="+std::to_string(l)+" has fewer than "+std::to_string(order-1)+" log values (a gamma file of another order?)");
        std::string more;if(is>>more)fail(gammapath+": trailing token "+shown(more)+" in the row of L="+std::to_string(l)+" (exactly "+std::to_string(order-1)+" log values per row at order "+std::to_string(order)+")");
        if(l==L){norm=nl;logs=v;}}
     std::string more;if(gamma>>more)fail(gammapath+": data after the row of L="+std::to_string(order)+": "+shown(more));}
    if(!norm||!std::isfinite(norm))fail(gammapath+": invalid normalization in the row of L="+std::to_string(L));
    // Graphs (C.6, R5a, Stage 4b): parallel load through the checked reader, one graph per iteration (dynamic,1) over the
    // ascending ids into its own slot of a pre-sized vector, so the block's threads (pinned to the lane's cores) first-touch
    // the graphs they load. Loading is I/O and parsing only: no value depends on the thread. Each slot keeps its own
    // error, and after the loop the lowest id's error is thrown: the error the serial loop threw first, whatever the
    // timing. The id -> graph map is built serially afterwards; moving a Graph moves its tables, never copies them.
    std::map<uint64_t,Graph>loaded;double start=omp_get_wtime();
    {const std::vector<uint64_t>ids(graphs.begin(),graphs.end());const int ng=int(ids.size());
     std::vector<Graph>slots(ng);std::vector<std::string>why(ng);std::vector<char>failed(ng,0);
     #pragma omp parallel for num_threads(threads) schedule(dynamic,1)
     for(int k=0;k<ng;++k){const uint64_t id=ids[k];const std::string gp=root+"/L"+std::to_string(L)+"/G"+std::to_string(id)+".txt";
        try{auto g=load_graph(gp,scale);
            if(g.id!=int(id)||g.L!=L)fail(gp+": graph identity mismatch (header L "+std::to_string(g.L)+" id "+std::to_string(g.id)+", expected L "+std::to_string(L)+" id "+std::to_string(id)+")");
            slots[k]=std::move(g);}
        catch(const std::exception&e){failed[k]=1;why[k]=e.what();}}
     for(int k=0;k<ng;++k)if(failed[k])throw std::runtime_error(why[k]);
     for(int k=0;k<ng;++k)loaded.emplace(ids[k],std::move(slots[k]));}
    // Optional frozen grid.
    std::map<uint64_t,Grid>grids;if(gridarg!="-")grids=read_grid(gridarg,L,graphs);
    double load_seconds=omp_get_wtime()-start;std::vector<Row>rows(nt);std::string error;
    std::vector<int>order_of(nt);for(int i=0;i<nt;++i)order_of[i]=i;
    std::stable_sort(order_of.begin(),order_of.end(),[&](int a,int b){auto cost=[&](int i){auto&t=tasks[i];return ld(t.end-t.begin)*loaded.at(t.graph).addends.size();};return cost(a)>cost(b);});
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
            try {const auto&t=tasks[ti];const auto&g=loaded.at(t.graph);scratch.resize(g);Row&r=rows[ti];double t0=omp_get_wtime();
            Net net(dim,bits,netf.directions.at(t.rep),stream_seed(seed,t.rep,g.id),t.begin);
            std::array<ld,DIMMAX>u{};std::array<ld,NLOGS>sum{},comp{};auto git=grids.find(t.graph);const Grid*grid=git!=grids.end()?&git->second:nullptr;
            assert(dim<=int(u.size()));
            for(uint64_t i=t.begin;i<t.end;++i){if(i>t.begin)net.next(i);net.point(u.data());ld jac=apply_grid(grid,g.E,layout,u.data());
                scratch.mp_check=mpmode==MP_ON||(mpmode==MP_STRIDE16&&(i&15)==0);
                int level;auto v=sample(g,u.data(),K,logs,level,layout,scratch);r.q+=level>=1;r.mp+=level>=2;
                r.nondirect+=!scratch.direct;r.nonmoderate+=!scratch.moderate;
                if(scratch.mp_checked){ld x=scratch.mp_log10;r.mp_checked++;r.mp_hist[mp_bin(x)]++;r.mp_alarm+=x< -320;if(x<r.mp_min_log10)r.mp_min_log10=x;}
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
            {if(error.empty())error="task uid "+std::to_string(tasks[ti].uid)+" (graph "+std::to_string(tasks[ti].graph)+", replicate "+std::to_string(tasks[ti].rep)+"): "+e.what();}
        }}
#if defined(C8_TIER_TIMERS) || defined(C8_RATIO_HISTOGRAM)
        #pragma omp critical
        {diagnostics.add(thread_diagnostics());}
#endif
    }
    if(!error.empty())throw std::runtime_error(error);double seconds=omp_get_wtime()-start;
    // Peak resident set of this process image: VmHWM of /proc/self/status. getrusage's ru_maxrss is recorded too, and is
    // the fallback; on Linux it also counts the pre-exec image (the forking parent's RSS).
    long vm_hwm_kb=-1;{std::ifstream st("/proc/self/status");std::string key;while(st>>key){if(key=="VmHWM:"){st>>vm_hwm_kb;break;}std::getline(st,key);}}
    struct rusage usage{};getrusage(RUSAGE_SELF,&usage);const long rusage_kb=usage.ru_maxrss;
    const long max_rss_kb=vm_hwm_kb>=0?vm_hwm_kb:rusage_kb;
    // Native output goes only to a temporary file supplied by the checked Python publisher.
    std::ofstream f(out);if(!f)fail(out+": cannot open the output");f<<std::setprecision(std::numeric_limits<ld>::max_digits10);
    f<<"{\"schema\":\"c8-d3-hpc-native-1\",\"order\":"<<order<<",\"task_magic\":\""<<magic<<"\",\"L\":"<<L<<",\"seed\":"<<seed<<",\"layout\":"<<layout<<",\"bits\":"<<bits<<",\"rate\":\""<<scale<<"\",\"sum_mode\":\""<<mode
     <<"\",\"long_double_bits\":"<<std::numeric_limits<ld>::digits<<",\"mp_backend\":\""<<mp_backend<<"\",\"mp_digits10\":"<<std::numeric_limits<MP>::digits10<<",\"numerics\":\""<<numerics_profile
     <<"\",\"mp_check\":\""<<mp_mode_name(mpmode)<<"\",\"threads\":"<<threads<<",\"load_seconds\":"<<load_seconds<<",\"integration_seconds\":"<<seconds<<",\"graphs_loaded\":"<<loaded.size()
     <<",\"max_rss_kb\":"<<max_rss_kb<<",\"max_rss_source\":\""<<(vm_hwm_kb>=0?"VmHWM":"getrusage")<<"\",\"rusage_maxrss_kb\":"<<rusage_kb<<",\"gmp\":"<<gmp<<",\"libraries\":"<<libraries_json()
     <<",\"diagnostic\":"<<(diagnostic_kind?"true":"false");
    if(diagnostic_kind)f<<",\"diagnostic_kind\":\""<<diagnostic_kind<<"\"";
#ifndef C8_NO_TAIL_FIELDS
    f<<",\"tail_top_k\":"<<TAILK;
#endif
    if(mpmode!=MP_OFF){f<<",\"mp_hist_bins\":[\"[-20,inf)\"";for(int b=1;b<MPBINS-1;++b)f<<",\"["<<-20*(b+1)<<","<<-20*b<<")\"";f<<",\"(-inf,-340)\"],\"mp_alarm_rule\":\"log10(|v|/err) < -320 at the MP tier\"";}
#if defined(C8_TIER_TIMERS) || defined(C8_RATIO_HISTOGRAM)
    diagnostics_json(f,diagnostics);
#endif
#ifdef C8_ORDER_TRACE
    f<<",\"addends\":{";{bool first=true;for(auto&kv:loaded){if(!first)f<<',';first=false;f<<'"'<<kv.first<<"\":"<<kv.second.addends.size();}}
    f<<"},\"execution_order\":[";for(int i=0;i<nt;++i){if(i)f<<',';f<<trace[i];}f<<"]";
#endif
    f<<",\"rows\":[";
    for(int i=0;i<nt;++i){if(i)f<<',';auto&t=tasks[i];auto&r=rows[i];f<<"{\"uid\":"<<t.uid<<",\"rep\":"<<t.rep<<",\"graph\":"<<t.graph<<",\"begin\":"<<t.begin<<",\"end\":"<<t.end<<",\"total\":"<<t.total<<",\"quad\":"<<r.q<<",\"mp\":"<<r.mp<<",\"seconds\":"<<r.seconds<<",\"max_abs\":\""<<r.maxabs<<"\",\"values\":[";for(int j=0;j<2*(K+1);++j){if(j)f<<',';f<<'"'<<r.value[j]<<'"';}f<<"]";
#ifndef C8_NO_TAIL_FIELDS
        f<<",\"tail_top\":[";for(int j=0;j<r.tail_n;++j){if(j)f<<',';f<<'"'<<r.tail_top[j]<<'"';}f<<"],\"tail_sum\":\""<<r.tail_sum<<"\",\"tail_argmax\":"<<r.tail_argmax;
#endif
        f<<",\"nondirect\":"<<r.nondirect<<",\"nonmoderate\":"<<r.nonmoderate;
        if(mpmode!=MP_OFF){f<<",\"mp_checked\":"<<r.mp_checked<<",\"mp_hist\":[";for(int b=0;b<MPBINS;++b){if(b)f<<',';f<<r.mp_hist[b];}f<<"],\"mp_min_log10\":";
            if(r.mp_checked)f<<'"'<<r.mp_min_log10<<'"';else f<<"null";f<<",\"mp_alarm\":"<<r.mp_alarm;}
        f<<"}";}
    f<<"]}\n";if(!f)fail(out+": output write failed");
    std::cerr<<"completed "<<nt<<" tasks, "<<loaded.size()<<" graphs; integration "<<seconds<<" s\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;} }
