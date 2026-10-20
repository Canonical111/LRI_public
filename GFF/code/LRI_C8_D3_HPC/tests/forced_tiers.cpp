// Forced-tier checks of the precision policy (PLAN.md A-RPL-4, the accuracy contract; F-table row forced_tiers.cpp)
// and the tier diagnosis of a single point (G-RUN1 T2).
//   forced_tiers points GRAPHS_ROOT L NET SEED LAYOUT RATE GRID_OR_DASH TASKS THREADS
//       TASKS: lines "uid rep graph begin end total" (the worker's task rows), optionally after the worker's task header
//       (C8D3TASKS1 <order> <L> <nt> or C7D3TASKS1 <L> <nt>; its L must be L and nt the row count). S1-06: every other
//       non-blank line must be a row of exactly six unsigned integers with begin < end <= total, a new uid and
//       graph <= INT_MAX, or the tool exits 2 naming the line; S1-04: every range must lie in the net period 2^bits
//       (checked before any point is computed). Every point
//       of every row is regenerated exactly as the worker does (src/stream.hpp: the net, the stream seed, the grid,
//       then sample(), whose evaluate() gives the worker's tier decision) and then gets EVERY tier on its
//       log-coordinates, plus an independent 450-digit value (cpp_dec_float<450>, the formula of point_checks.cpp):
//         ld tier   v = calculate_products (moderate) or calculate_reference<ld> (not moderate), as evaluate();
//         binary128 q = calculate_shared<Q>;
//         MP        m = calculate_shared<MP,true> (the same value as the worker's <MP,false>, A-KER-7).
//       Measured on each tier's NATIVE output (before any conversion):
//         s_ld = |v - f450| / err450,  s_q = |q - f450| / err450  (err450 = the 450-digit sum|terms|),
//         s_mp = |m - f450| / (1 + err450), and the relative errors |x - f450| / |f450|;
//         conv_q, conv_mp = |ld(x) - x| / |x|, the conversion of the binary128 and MP outputs to long double;
//         the tool's own decision (|v| < 1e-9 (err+1e-4900) promotes, |q| < 1e-23 err_q promotes) against evaluate()'s.
//       Per tier: the maxima of s, of the relative error and of the conversion error over all points, and over the
//       points the tier ACCEPTS (ld: |v| >= 1e-9 err; binary128: promoted from ld and |q| >= 1e-23 err_q; MP: every
//       point that reaches it), the counts, and the decision mismatches. One JSON summary on stdout ("rows": the task
//       rows read); forced_tiers.py applies the gates (s_ld <= 1e-14, s_q <= 1e-28, s_mp <= 1e-280, conversions <= 2^-64,
//       no decision mismatch) from "breach_counts" (S1-03): per condition (ld_scaled, quad_scaled, mp_scaled,
//       quad_conversion, mp_conversion) the number of points whose full-precision (450-digit) comparison here exceeded
//       the bound. The maxima are display values: six digits as before, and per tier "full_precision" with 17
//       significant digits; no verdict is taken from them.
//       Stage 3b (the precise record of a precision-contract finding): each maximum carries the point where it occurs
//       (graph, rep, index); every accepted point above its bound, and every conversion above 2^-64, is listed as a
//       breach with its point, tier, value, evaluate()'s level, moderate/direct, the 450-digit value and err450 (at
//       most 400 listed; breach_count counts all); per tier a histogram of floor(log10 s) over the accepted points;
//       per graph the evaluate() level counts.
//   forced_tiers --point GRAPH REP INDEX... -- GRAPHS_ROOT L NET SEED LAYOUT RATE GRID_OR_DASH
//       Every INDEX must lie in the net period (S1-04). One JSON line per point: the long-double test ratio |v|/(err + 1e-4900) against 1e-9, the binary128 test ratio
//       |q|/err_q against 1e-23, each ratio over its threshold, and the tier evaluate() chose. G-RUN1 accepts a
//       promotion-counter mismatch only at a point whose test ratio is within 1 +- 1e-6 of its threshold.
//   forced_tiers --scan GRAPH REP BEGIN END -- GRAPHS_ROOT L NET SEED LAYOUT RATE GRID_OR_DASH
//       Every point of [BEGIN, END), END <= 2^bits checked first (S1-04) (OpenMP): one JSON line per point whose long-double test ratio is within a factor
//       1 +- 1e-6 of 1e-9, or whose binary128 test ratio (computed when the long-double test fails or is that close)
//       is within 1 +- 1e-6 of 1e-23; then a summary line {"points", "near_threshold_points"} (G-RUN1 T2 diagnosis of a
//       row whose promotion counters moved).
#include "../src/kernel.hpp"
#include "../src/stream.hpp"
#include <charconv>
#include <climits>
#include <iostream>
#include <map>
#include <omp.h>
using Ref=boost::multiprecision::number<boost::multiprecision::cpp_dec_float<450>>;
static std::pair<Ref,Ref> independent(const Graph&g,const ld*lx,ld shift){
    std::vector<Ref>x(g.E),mons(g.masks.size());Ref S=0;
    for(int j=0;j<g.E;++j){x[j]=exp(Ref(lx[j]));S+=x[j];}
    for(size_t k=0;k<g.masks.size();++k){Ref z=-Ref(shift);unsigned m=g.masks[k];while(m){int j=__builtin_ctz(m);m&=m-1;z+=Ref(lx[j]);}mons[k]=exp(z);}
    Ref v=0,err=0;for(const auto&t:g.terms){Ref U=0,n=0,a=0;for(int i:t.ids)U+=mons[i];for(int j=0;j<g.E;++j){Ref z=Ref(t.co[j])*x[j];n+=z;a+=abs(z);}Ref den=U*sqrt(U);v+=n/den;err+=a/den;}return{v/S,err/S};
}
static Ref from_q(Q x){char buf[128];quadmath_snprintf(buf,sizeof buf,"%.40Qe",x);return Ref(buf);}
static Ref from_mp(const MP&x){return Ref(x.str(430,std::ios_base::scientific));}
// The shift and moderate flag exactly as evaluate() forms them.
static void shift_of(const Graph&g,const ld*lx,ld&shift,bool&moderate){
    shift=0;bool direct=true;for(int j=0;j<g.E;++j)if(lx[j]<-600||lx[j]>0)direct=false;
    if(!direct){shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld v=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;v+=lx[j];}shift=std::max(shift,v);}}
    moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
}
// A point's place in the sample: (graph, replicate, point index).
struct Loc{uint64_t graph=0,rep=0,index=0;bool set=false;};
// Per tier: counts; the maxima of s and of the relative error over all evaluations and over the accepted points, each
// with the point where it occurs; the conversion maximum with its point; and a histogram of floor(log10 s) over the
// accepted points ("zero" for s = 0), the measured column of the contract table.
struct Stat {unsigned long long n=0,accepted=0;Ref s_all=0,s_acc=0,rel_all=0,rel_acc=0,conv=0;Loc at_s_acc,at_rel_acc,at_conv;std::map<std::string,unsigned long long>hist;
    void add(const Ref&s,const Ref&rel,bool acc,const Loc&w){++n;if(s>s_all)s_all=s;if(rel>rel_all)rel_all=rel;
        if(acc){++accepted;if(s>s_acc||!at_s_acc.set){s_acc=s;at_s_acc=w;}if(rel>rel_acc||!at_rel_acc.set){rel_acc=rel;at_rel_acc=w;}
            std::string b="zero";if(s>0){Ref l=floor(log10(s));b=std::to_string(l.convert_to<long long>());}hist[b]++;}}
    void conversion(const Ref&c,const Loc&w){if(c>conv||!at_conv.set){conv=c;at_conv=w;}}
    void merge(const Stat&o){n+=o.n;accepted+=o.accepted;if(o.s_all>s_all)s_all=o.s_all;if(o.rel_all>rel_all)rel_all=o.rel_all;
        if(o.at_s_acc.set&&(!at_s_acc.set||o.s_acc>s_acc)){s_acc=o.s_acc;at_s_acc=o.at_s_acc;}
        if(o.at_rel_acc.set&&(!at_rel_acc.set||o.rel_acc>rel_acc)){rel_acc=o.rel_acc;at_rel_acc=o.at_rel_acc;}
        if(o.at_conv.set&&(!at_conv.set||o.conv>conv)){conv=o.conv;at_conv=o.at_conv;}for(auto&kv:o.hist)hist[kv.first]+=kv.second;}};
static std::string sci(const Ref&x){std::ostringstream o;o<<std::setprecision(6)<<std::scientific<<x;return o.str();}
static std::string g17(const Ref&x){std::ostringstream o;o<<std::setprecision(16)<<std::scientific<<x;return o.str();}   // %.17g's digits (S1-03)
struct Row{uint64_t uid,rep,graph,begin,end,total;};
struct Ctx{std::string root;int L;NetFile net;uint64_t seed;int layout;ld scale;std::map<uint64_t,Grid>grids;std::map<uint64_t,Graph>graphs;};
static Ctx context(int argc,char**argv,int at,const std::set<uint64_t>&reps,const std::set<uint64_t>&ids){
    if(argc-at<7)throw std::runtime_error("missing arguments");
    Ctx c;c.root=argv[at];c.L=std::stoi(argv[at+1]);const std::string netpath=argv[at+2];c.seed=std::stoull(argv[at+3]);c.layout=std::stoi(argv[at+4]);c.scale=std::stold(argv[at+5]);
    const std::string grid=argv[at+6];
    if(c.L<2||c.L>LMAX||c.layout<0||c.layout>2||!(c.scale>0&&c.scale<=1))throw std::runtime_error("bad options");
    c.net=read_net(netpath,c.layout,c.L,reps);if(grid!="-")c.grids=read_grid(grid,c.L,ids);
    for(auto id:ids){std::string gp=c.root+"/L"+std::to_string(c.L)+"/G"+std::to_string(id)+".txt";auto g=load_graph(gp,c.scale);
        if(g.id!=int(id)||g.L!=c.L)throw std::runtime_error(gp+": graph identity mismatch");c.graphs.emplace(id,std::move(g));}
    return c;
}
// Regenerates point i of (graph, rep) into s.lx and returns evaluate()'s level.
static int regenerate(const Ctx&c,const Graph&g,uint64_t rep,uint64_t i,Scratch&s){
    Net net(c.net.dim,c.net.bits,c.net.directions.at(rep),stream_seed(c.seed,rep,g.id),i);std::array<ld,DIMMAX>u{};net.point(u.data());
    auto git=c.grids.find(uint64_t(g.id));apply_grid(git==c.grids.end()?nullptr:&git->second,g.E,c.layout,u.data());
    int level=0;const std::array<ld,NLOGS>logs{};sample(g,u.data(),0,logs,level,c.layout,s);return level;
}
// The contract's bounds (docs/NUMERICS.md; PLAN A-RPL-4): a point whose tier output exceeds one is listed as a breach
// (forced_tiers.py turns any into a precision-contract finding; nothing here fails the run).
static const Ref B_LD("1e-14"),B_Q("1e-28"),B_MP("1e-280"),B_CONV=pow(Ref(2),-64);
static constexpr size_t MAX_BREACHES=400;
// S1-03: the conditions counted per point (the authoritative verdict; the printed maxima are display values).
static const char*const CONDITIONS[5]={"ld_scaled","quad_scaled","mp_scaled","quad_conversion","mp_conversion"};
// S1-06: the task file. An unsigned decimal token (digits only, fits uint64_t).
static bool unsigned_token(const std::string&s,uint64_t&v){if(s.empty())return false;for(char ch:s)if(ch<'0'||ch>'9')return false;
    auto r=std::from_chars(s.data(),s.data()+s.size(),v);return r.ec==std::errc()&&r.ptr==s.data()+s.size();}
static std::vector<Row> read_tasks(const std::string&tpath,int L){
    std::ifstream tf(tpath);if(!tf)throw std::runtime_error(tpath+": cannot open");
    std::vector<Row>rows;std::set<uint64_t>uids;std::string line;size_t lineno=0;bool first=true,header=false;uint64_t declared=0;
    while(std::getline(tf,line)){++lineno;std::istringstream is(line);std::vector<std::string>tok;std::string s;while(is>>s)tok.push_back(s);if(tok.empty())continue;
        const std::string where=tpath+": line "+std::to_string(lineno);
        if(first&&(tok[0]=="C8D3TASKS1"||tok[0]=="C7D3TASKS1")){first=false;header=true;const bool c8=tok[0]=="C8D3TASKS1";uint64_t v[3]={0,0,0};
            if(tok.size()!=(c8?4u:3u))throw std::runtime_error(where+": task header "+tok[0]+(c8?" <order> <L> <nt>":" <L> <nt>")+" expected ("+std::to_string(tok.size())+" fields)");
            for(size_t k=1;k<tok.size();++k)if(!unsigned_token(tok[k],v[k-1]))throw std::runtime_error(where+": malformed task header field "+std::to_string(k+1));
            if(v[c8?1:0]!=uint64_t(L))throw std::runtime_error(where+": task header L "+std::to_string(v[c8?1:0])+" is not L "+std::to_string(L));
            declared=v[c8?2:1];continue;}
        first=false;
        if(tok.size()!=6)throw std::runtime_error(where+": a task row is six fields uid rep graph begin end total ("+std::to_string(tok.size())+" found)");
        uint64_t v[6];for(int k=0;k<6;++k)if(!unsigned_token(tok[k],v[k]))throw std::runtime_error(where+": task row field "+std::to_string(k+1)+" is not an unsigned 64-bit integer");
        const Row r{v[0],v[1],v[2],v[3],v[4],v[5]};
        if(r.begin>=r.end)throw std::runtime_error(where+": empty row");
        if(r.end>r.total||r.graph>uint64_t(INT_MAX))throw std::runtime_error(where+": invalid task row (end <= total and graph <= INT_MAX required)");
        if(!uids.insert(r.uid).second)throw std::runtime_error(where+": duplicate task uid "+std::to_string(r.uid));
        rows.push_back(r);}
    if(tf.bad())throw std::runtime_error(tpath+": read error");
    if(rows.empty())throw std::runtime_error(tpath+": no task rows");
    if(header&&declared!=rows.size())throw std::runtime_error(tpath+": the task header declares "+std::to_string(declared)+" rows, "+std::to_string(rows.size())+" found");
    return rows;
}
// S1-04: a point index or range end outside the net period would make Net read past its direction numbers.
static void in_period(const Ctx&c,uint64_t end,const std::string&what){if(end>(uint64_t(1)<<c.net.bits))throw std::runtime_error(what+": end "+std::to_string(end)+" beyond the net period 2^"+std::to_string(c.net.bits));}
static std::string loc(const Loc&w){std::ostringstream o;if(!w.set)return "null";o<<"{\"graph\":"<<w.graph<<",\"rep\":"<<w.rep<<",\"index\":"<<w.index<<"}";return o.str();}
static int points(int argc,char**argv){
    if(argc!=11){std::cerr<<"usage: forced_tiers points GRAPHS_ROOT L NET SEED LAYOUT RATE GRID_OR_DASH TASKS THREADS\n";return 1;}
    const std::string tpath=argv[9];const std::vector<Row>rows=read_tasks(tpath,std::stoi(argv[3]));std::set<uint64_t>reps,ids;
    for(const auto&r:rows){reps.insert(r.rep);ids.insert(r.graph);}
    const Ctx c=context(argc,argv,2,reps,ids);const int threads=std::stoi(argv[10]);
    for(size_t k=0;k<rows.size();++k)in_period(c,rows[k].end,tpath+": task row "+std::to_string(k)+" (uid "+std::to_string(rows[k].uid)+")");
    struct Acc{Stat ld,q,mp;unsigned long long points=0,mismatch=0,levels[3]{},nbreach=0,nb[5]{};std::vector<std::string>breaches,mismatches;
        std::map<uint64_t,std::array<unsigned long long,3>>graph_levels;};
    std::vector<Acc>acc(std::max(1,threads));std::string error;
    std::vector<std::pair<uint64_t,uint64_t>>work;for(size_t k=0;k<rows.size();++k)for(uint64_t i=rows[k].begin;i<rows[k].end;++i)work.emplace_back(k,i);
    #pragma omp parallel num_threads(threads)
    {
        Scratch s;Acc&a=acc[omp_get_thread_num()];
        #pragma omp for schedule(dynamic,4)
        for(size_t w=0;w<work.size();++w){try{
            const Row&r=rows[work[w].first];const uint64_t i=work[w].second;const Graph&g=c.graphs.at(r.graph);s.resize(g);const Loc where{r.graph,r.rep,i,true};
            const int level=regenerate(c,g,r.rep,i,s);ld lx[EMAX];for(int j=0;j<g.E;++j)lx[j]=s.lx[j];
            ld shift;bool moderate;shift_of(g,lx,shift,moderate);
            auto v=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);
            auto q=calculate_shared<Q>(g,lx,shift);auto m=calculate_shared<MP,true>(g,lx,shift);auto ref=independent(g,lx,shift);
            const bool ld_ok=!(absolute(v.first)/(v.second+1e-4900L)<1e-9L),q_ok=!(absolute(q.first)<Q(1e-23L)*q.second);
            const int mine=ld_ok?0:(q_ok?1:2);a.points++;a.levels[level]++;a.graph_levels[r.graph][level]++;
            if(mine!=level){a.mismatch++;if(a.mismatches.size()<50){std::ostringstream o;o<<"{\"graph\":"<<r.graph<<",\"rep\":"<<r.rep<<",\"index\":"<<i<<",\"evaluate_level\":"<<level<<",\"tool_level\":"<<mine<<"}";a.mismatches.push_back(o.str());}}
            const Ref f=ref.first,err=ref.second,af=abs(f);
            auto rel=[&](const Ref&x){return af>0?Ref(abs(x-f)/af):Ref(abs(x-f)>0?1:0);};
            Ref xv(v.first),xq=from_q(q.first),xm=from_mp(m.first);
            const Ref sv=abs(xv-f)/err,sq=abs(xq-f)/err,sm=abs(xm-f)/(1+err),rv=rel(xv),rq=rel(xq),rm=rel(xm);
            a.ld.add(sv,rv,ld_ok,where);
            a.q.add(sq,rq,!ld_ok&&q_ok,where);
            a.mp.add(sm,rm,mine==2,where);
            Ref cq=0,cm=0;
            if(xq!=0){cq=abs(Ref(ld(q.first))-xq)/abs(xq);a.q.conversion(cq,where);}
            if(xm!=0){cm=abs(Ref(m.first.convert_to<ld>())-xm)/abs(xm);a.mp.conversion(cm,where);}
            // A breach of the contract at the tier's native output (gates (a)-(c)), recorded with its point.
            auto breach=[&](int which,const char*tier,const char*what,const Ref&x,const Ref&bound){a.nbreach++;a.nb[which]++;if(a.breaches.size()>=MAX_BREACHES)return;std::ostringstream o;
                o<<"{\"tier\":\""<<tier<<"\",\"quantity\":\""<<what<<"\",\"value\":\""<<sci(x)<<"\",\"bound\":\""<<sci(bound)<<"\",\"graph\":"<<r.graph<<",\"rep\":"<<r.rep<<",\"index\":"<<i
                 <<",\"evaluate_level\":"<<level<<",\"moderate\":"<<(moderate?"true":"false")<<",\"direct\":"<<(shift==0?"true":"false")<<",\"ld_ratio\":\""<<sci(Ref(absolute(v.first)/(v.second+1e-4900L)))
                 <<"\",\"relative\":\""<<sci(std::string(tier)=="ld"?rv:(std::string(tier)=="quad"?rq:rm))<<"\",\"f450\":\""<<sci(f)<<"\",\"err450\":\""<<sci(err)<<"\"}";a.breaches.push_back(o.str());};
            if(ld_ok&&sv>B_LD)breach(0,"ld","scaled",sv,B_LD);
            if(!ld_ok&&q_ok&&sq>B_Q)breach(1,"quad","scaled",sq,B_Q);
            if(mine==2&&sm>B_MP)breach(2,"mp","scaled",sm,B_MP);
            if(cq>B_CONV)breach(3,"quad","conversion",cq,B_CONV);
            if(cm>B_CONV)breach(4,"mp","conversion",cm,B_CONV);
        }catch(const std::exception&e){
            #pragma omp critical
            {if(error.empty())error=e.what();}
        }}
    }
    if(!error.empty())throw std::runtime_error(error);
    Acc t;for(auto&a:acc){t.ld.merge(a.ld);t.q.merge(a.q);t.mp.merge(a.mp);t.points+=a.points;t.mismatch+=a.mismatch;t.nbreach+=a.nbreach;for(int k=0;k<5;++k)t.nb[k]+=a.nb[k];for(int k=0;k<3;++k)t.levels[k]+=a.levels[k];
        for(auto&b:a.breaches)if(t.breaches.size()<MAX_BREACHES)t.breaches.push_back(b);for(auto&b:a.mismatches)if(t.mismatches.size()<50)t.mismatches.push_back(b);
        for(auto&kv:a.graph_levels)for(int k=0;k<3;++k)t.graph_levels[kv.first][k]+=kv.second[k];}
    auto stat=[&](const char*name,const Stat&s){std::cout<<"\""<<name<<"\":{\"evaluated\":"<<s.n<<",\"accepted\":"<<s.accepted<<",\"max_scaled_all\":\""<<sci(s.s_all)<<"\",\"max_scaled_accepted\":\""<<sci(s.s_acc)
        <<"\",\"max_relative_all\":\""<<sci(s.rel_all)<<"\",\"max_relative_accepted\":\""<<sci(s.rel_acc)<<"\",\"max_conversion_relative\":\""<<sci(s.conv)<<"\""
        <<",\"full_precision\":{\"max_scaled_all\":\""<<g17(s.s_all)<<"\",\"max_scaled_accepted\":\""<<g17(s.s_acc)<<"\",\"max_relative_all\":\""<<g17(s.rel_all)
        <<"\",\"max_relative_accepted\":\""<<g17(s.rel_acc)<<"\",\"max_conversion_relative\":\""<<g17(s.conv)<<"\"}"
        <<",\"at_max_scaled_accepted\":"<<loc(s.at_s_acc)<<",\"at_max_relative_accepted\":"<<loc(s.at_rel_acc)<<",\"at_max_conversion\":"<<loc(s.at_conv)<<",\"log10_scaled_accepted_histogram\":{";
        bool first=true;for(auto&kv:s.hist){if(!first)std::cout<<',';first=false;std::cout<<"\""<<kv.first<<"\":"<<kv.second;}std::cout<<"}}";};
    std::cout<<"{\"L\":"<<c.L<<",\"backend\":\""<<mp_backend<<"\",\"rows\":"<<rows.size()<<",\"points\":"<<t.points<<",\"graphs\":"<<c.graphs.size()<<",\"levels\":["<<t.levels[0]<<","<<t.levels[1]<<","<<t.levels[2]<<"],\"decision_mismatches\":"<<t.mismatch<<",";
    stat("ld",t.ld);std::cout<<",";stat("quad",t.q);std::cout<<",";stat("mp",t.mp);
    std::cout<<",\"breach_count\":"<<t.nbreach<<",\"breach_counts\":{";for(int k=0;k<5;++k)std::cout<<(k?",":"")<<"\""<<CONDITIONS[k]<<"\":"<<t.nb[k];
    std::cout<<"},\"breaches\":[";for(size_t k=0;k<t.breaches.size();++k)std::cout<<(k?",":"")<<t.breaches[k];
    std::cout<<"],\"mismatch_examples\":[";for(size_t k=0;k<t.mismatches.size();++k)std::cout<<(k?",":"")<<t.mismatches[k];
    std::cout<<"],\"graph_levels\":{";{bool first=true;for(auto&kv:t.graph_levels){if(!first)std::cout<<',';first=false;std::cout<<"\""<<kv.first<<"\":["<<kv.second[0]<<","<<kv.second[1]<<","<<kv.second[2]<<"]";}}
    std::cout<<"},\"bounds\":{\"ld\":\"1e-14\",\"quad\":\"1e-28\",\"mp\":\"1e-280\",\"conversion\":\"2^-64\"}";
    std::cout<<",\"notes\":\"mp scaled by 1+err450; quad and ld scaled by err450; conversion = |ld(x)-x|/|x| over all evaluations; breaches: accepted points above the bound (at most "<<MAX_BREACHES<<" listed, breach_count counts all)\"}\n";
    return 0;
}
static int point(int argc,char**argv){
    int sep=-1;for(int i=2;i<argc;++i)if(std::string(argv[i])=="--"){sep=i;break;}
    if(sep<5||argc-sep-1!=7){std::cerr<<"usage: forced_tiers --point GRAPH REP INDEX... -- GRAPHS_ROOT L NET SEED LAYOUT RATE GRID_OR_DASH\n";return 1;}
    const uint64_t gid=std::stoull(argv[2]),rep=std::stoull(argv[3]);std::vector<uint64_t>idx;for(int i=4;i<sep;++i)idx.push_back(std::stoull(argv[i]));
    const Ctx c=context(argc,argv,sep+1,{rep},{gid});const Graph&g=c.graphs.at(gid);Scratch s;s.resize(g);
    for(uint64_t i:idx)if(i>>c.net.bits)throw std::runtime_error("point index "+std::to_string(i)+" beyond the net period 2^"+std::to_string(c.net.bits));   // S1-04
    std::cout<<std::setprecision(21);
    for(uint64_t i:idx){const int level=regenerate(c,g,rep,i,s);ld lx[EMAX];for(int j=0;j<g.E;++j)lx[j]=s.lx[j];ld shift;bool moderate;shift_of(g,lx,shift,moderate);
        auto v=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);auto q=calculate_shared<Q>(g,lx,shift);
        const ld rld=absolute(v.first)/(v.second+1e-4900L);const Ref rq=q.second>0?Ref(from_q(absolute(q.first))/from_q(q.second)):Ref(0);
        std::cout<<"{\"graph\":"<<gid<<",\"rep\":"<<rep<<",\"index\":"<<i<<",\"level\":"<<level<<",\"moderate\":"<<(moderate?"true":"false")
                 <<",\"ld_ratio\":\""<<rld<<"\",\"ld_ratio_over_threshold\":\""<<rld/1e-9L<<"\",\"quad_ratio\":\""<<sci(rq)<<"\",\"quad_ratio_over_threshold\":\""<<sci(rq/Ref("1e-23"))<<"\"}\n";}
    return 0;
}
static int scan(int argc,char**argv){
    if(argc!=14||std::string(argv[6])!="--"){std::cerr<<"usage: forced_tiers --scan GRAPH REP BEGIN END -- GRAPHS_ROOT L NET SEED LAYOUT RATE GRID_OR_DASH\n";return 1;}
    const uint64_t gid=std::stoull(argv[2]),rep=std::stoull(argv[3]),b=std::stoull(argv[4]),e=std::stoull(argv[5]);
    if(b>=e)throw std::runtime_error("empty range");
    const Ctx c=context(argc,argv,7,{rep},{gid});const Graph&g=c.graphs.at(gid);in_period(c,e,"scan range");
    const ld tol=1e-6L;unsigned long long near=0;std::vector<std::string>lines;
    #pragma omp parallel
    {
        Scratch s;s.resize(g);
        #pragma omp for schedule(dynamic,256) reduction(+:near)
        for(uint64_t i=b;i<e;++i){
            const int level=regenerate(c,g,rep,i,s);ld lx[EMAX];for(int j=0;j<g.E;++j)lx[j]=s.lx[j];ld shift;bool moderate;shift_of(g,lx,shift,moderate);
            auto v=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);
            const ld rld=absolute(v.first)/(v.second+1e-4900L)/1e-9L;bool hit=fabsl(rld-1)<=tol;ld rq=-1;
            if(rld<1+tol){auto q=calculate_shared<Q>(g,lx,shift);if(q.second>0){rq=ld(absolute(q.first)/q.second)/1e-23L;hit=hit||fabsl(rq-1)<=tol;}}
            if(hit){++near;std::ostringstream o;o<<std::setprecision(21)<<"{\"index\":"<<i<<",\"level\":"<<level<<",\"ld_ratio_over_threshold\":\""<<rld<<"\",\"quad_ratio_over_threshold\":\""<<rq<<"\"}";
                #pragma omp critical
                lines.push_back(o.str());}
        }
    }
    for(auto&l:lines)std::cout<<l<<'\n';
    std::cout<<"{\"graph\":"<<gid<<",\"rep\":"<<rep<<",\"points\":"<<(e-b)<<",\"near_threshold_points\":"<<near<<",\"tolerance\":\"1e-6\"}\n";
    return 0;
}
int main(int argc,char**argv){try{
    const std::string cmd=argc>1?argv[1]:"";
    if(cmd=="--scan")return scan(argc,argv);
    if(cmd=="points")return points(argc,argv);
    if(cmd=="--point")return point(argc,argv);
    std::cerr<<"usage: forced_tiers points ... | forced_tiers --point ...\n";return 1;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
