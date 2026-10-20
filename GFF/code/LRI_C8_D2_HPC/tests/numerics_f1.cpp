// A-FLAG-3 F1 (and F3 per tier) for an opt-in numerics profile (tests/numerics_flags.py drives it). Compiled with the
// EXACT compile command of the executable under test (its bin/<exe>.build.json, source and output swapped), so the
// kernel here is that executable's: the exact path for bin/c8d2_gmp, a profile's for bin/c8d2_gmp_<p>.
// For every graph of LIST (all of loop order L) and every point index in [BEGIN, END) the point is generated exactly
// as the worker generates it (the Sobol net of replicate 0, the worker's seed mixing, sample() at layout 0, rate .8:
// the A-RPL-5 point set of tests/forced_tiers.py), and evaluated by the build's own evaluate() with factor = shift, so
// that y = f * Z with f the accepted value of the build's tiers (shift recomputed here exactly as evaluate() does;
// expl(0) = 1).
//   write mode (the exact baseline): an independent 450-digit value f450 (cpp_dec_float<450>, the independent() of
//              tests/forced_tiers.cpp: no shared prefix products or sums) gives y_ref = f450 * Z; one line per point
//              "graph point lxhash level tier y y_ref err_ref" goes to REF, in (graph, point) order;
//   read mode  (a profile, or the exact binary in a self-test): REF is read, every point is checked to be the same
//              point (graph, index and the hash of its log-coordinates), and compared with y_ref and with the
//              baseline's own y (paired).
// Reported (one JSON object on stdout): per tier (nx tier codes: long_double, double_double, binary128, mp256,
// mp350) the counts, the histograms of floor(log10(|y - y_ref| / |y_ref|)) and of floor(log10(|y - y_ref| /
// err_ref)), the largest relative error and the violations of the F1 bound (relative error > 1e-6); the paired
// comparison with the baseline (identical points, histogram of the relative difference, the tier transition
// matrix); level mismatches between sample() and evaluate(); and, when the profile defines C8_NX_F1_CHECKS(g, lx,
// shift, counts), its named counters (a counter whose name ends in _violations fails F1).
//   numerics_f1 L LIST NET BEGIN END SEED THREADS REF write|read
// Exits 2 on unreadable input or a point mismatch with REF.
#include "../src/kernel.hpp"
#include <cstdio>
#include <cstring>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
#include <omp.h>
using Ref=boost::multiprecision::number<boost::multiprecision::cpp_dec_float<450>>;
struct Net {
    int dim,bits;const std::vector<uint64_t>&direction;std::vector<uint64_t>state;
    Net(int d,int b,const std::vector<uint64_t>&v,uint64_t seed,uint64_t begin):dim(d),bits(b),direction(v),state(d){
        std::mt19937_64 rng(seed);for(auto&s:state)s=rng()>>(64-bits);
        uint64_t gray=begin^(begin>>1);while(gray){int k=__builtin_ctzll(gray);gray&=gray-1;for(int j=0;j<dim;++j)state[j]^=direction[j*bits+k];}}
    void point(ld*u)const {for(int j=0;j<dim;++j)u[j]=(ld(state[j])+.5L)/ld(uint64_t(1)<<bits);}
};
// tests/forced_tiers.cpp's independent 450-digit value (val/S, err/S).
static std::pair<Ref,Ref> independent(const Graph&g,const ld*lx,ld shift){
    std::vector<Ref>x(g.E),xs(g.E),mons(g.masks.size());Ref S=0;const Ref sh=Ref(shift)/g.L;
    for(int j=0;j<g.E;++j){x[j]=exp(Ref(lx[j]));S+=x[j];xs[j]=shift==0?x[j]:exp(Ref(lx[j])-sh);}
    for(size_t k=0;k<g.masks.size();++k){Ref z=1;unsigned m=g.masks[k];while(m){int j=__builtin_ctz(m);m&=m-1;z*=xs[j];}mons[k]=z;}
    Ref v=0,err=0;for(const auto&t:g.terms){Ref U=0,n=0,a=0;for(int i:t.ids)U+=mons[i];for(int j=0;j<g.E;++j){Ref z=Ref(t.co[j])*x[j];n+=z;a+=abs(z);}v+=n/U;err+=a/U;}return{v/S,err/S};
}
// FNV-1a over the 10 value bytes of each long double of the point's log-coordinates (never the padding bytes).
static uint64_t lxhash(const ld*lx,int E){uint64_t h=1469598103934665603ULL;for(int j=0;j<E;++j){unsigned char b[sizeof(ld)];std::memcpy(b,&lx[j],sizeof(ld));for(int k=0;k<10;++k){h^=b[k];h*=1099511628211ULL;}}return h;}
static std::string qstr(Q x,int digits){char buf[128];quadmath_snprintf(buf,sizeof buf,"%.*Qe",digits-1,x);return buf;}
static Q qparse(const std::string&s){char*end=nullptr;Q x=strtoflt128(s.c_str(),&end);if(!end||*end)throw std::runtime_error("bad number in REF: "+s);return x;}
constexpr int NT=5;
static const char* TN[NT]={"long_double","double_double","binary128","mp256","mp350"};
// floor(log10(x)) bins: bin b counts x in [10^-b, 10^(1-b)) for b = 0..BINS-2 (x >= 1 in bin 0), the last bin x = 0 or
// below 10^-(BINS-2).
constexpr int BINS=62;
static int bin_of(Q x){if(!(x>0))return BINS-1;double e=-std::floor(double(log10q(x)));if(e<0)return 0;if(e>BINS-2)return BINS-1;return int(e);}
struct Rec {uint64_t graph=0,point=0,hash=0;int level=0,tier=0;Q y=0,yref=0,eref=0;};
struct Stats {
    unsigned long long points=0,level[3]{},tier[NT]{},viol[NT]{},level_mismatch=0,nonmoderate=0,nondirect=0,identical=0,trans[NT][NT]{};
    unsigned long long h_rel[NT][BINS]{},h_scaled[NT][BINS]{},h_pair[BINS]{};
    Q rel_max[NT]{},scaled_max[NT]{},pair_max=0;
    std::map<std::string,unsigned long long> checks;std::vector<std::string> first;
    void add(const Stats&o){points+=o.points;for(int k=0;k<3;++k)level[k]+=o.level[k];level_mismatch+=o.level_mismatch;nonmoderate+=o.nonmoderate;nondirect+=o.nondirect;identical+=o.identical;
        for(int t=0;t<NT;++t){tier[t]+=o.tier[t];viol[t]+=o.viol[t];if(o.rel_max[t]>rel_max[t])rel_max[t]=o.rel_max[t];if(o.scaled_max[t]>scaled_max[t])scaled_max[t]=o.scaled_max[t];
            for(int u=0;u<NT;++u)trans[t][u]+=o.trans[t][u];for(int b=0;b<BINS;++b){h_rel[t][b]+=o.h_rel[t][b];h_scaled[t][b]+=o.h_scaled[t][b];}}
        for(int b=0;b<BINS;++b)h_pair[b]+=o.h_pair[b];if(o.pair_max>pair_max)pair_max=o.pair_max;
        for(auto&kv:o.checks)checks[kv.first]+=kv.second;for(auto&s:o.first)if(first.size()<20)first.push_back(s);}
};
static void hist(std::ostream&f,const char*name,const unsigned long long*h){
    f<<'"'<<name<<"\":{";bool first=true;for(int b=0;b<BINS;++b)if(h[b]){if(!first)f<<',';first=false;f<<'"'<<(b==BINS-1?std::string("zero_or_below"):std::to_string(-b))<<"\":"<<h[b];}f<<'}';}
int main(int argc,char**argv){try{
    if(argc!=10||(std::string(argv[9])!="write"&&std::string(argv[9])!="read")){std::cerr<<"numerics_f1 L LIST NET BEGIN END SEED THREADS REF write|read\n";return 1;}
    const int L=std::stoi(argv[1]);const uint64_t begin=std::stoull(argv[4]),end=std::stoull(argv[5]),seed=std::stoull(argv[6]);const int threads=std::stoi(argv[7]);
    const std::string refpath=argv[8];const bool write=std::string(argv[9])=="write";
    if(L<2||L>LMAX||begin>=end||threads<1)throw std::runtime_error("bad arguments");
    std::vector<Graph>graphs;{std::ifstream list(argv[2]);std::string path;while(list>>path){graphs.push_back(load_graph(path,.8L));if(graphs.back().L!=L)throw std::runtime_error("graph of another L: "+path);}}
    if(graphs.empty())throw std::runtime_error("empty graph list");
    std::ifstream netf(argv[3],std::ios::binary);uint32_t head[3]={0,0,0};netf.read(reinterpret_cast<char*>(head),sizeof head);
    const int dim=head[1],bits=head[2];if(!netf||head[0]<1||dim!=4*L-1||bits<32||bits>60||end>(uint64_t(1)<<bits))throw std::runtime_error("bad net");
    std::vector<uint64_t>dir(size_t(dim)*bits);netf.read(reinterpret_cast<char*>(dir.data()),dir.size()*8);if(!netf)throw std::runtime_error("truncated net");
    const uint64_t n=end-begin,total=uint64_t(graphs.size())*n;
    std::vector<Rec>base;
    if(!write){std::ifstream rf(refpath);if(!rf)throw std::runtime_error("cannot open REF "+refpath);base.resize(total);std::string ys,rs,es;
        for(auto&r:base){if(!(rf>>r.graph>>r.point>>r.hash>>r.level>>r.tier>>ys>>rs>>es))throw std::runtime_error("REF "+refpath+" has fewer than "+std::to_string(total)+" points");r.y=qparse(ys);r.yref=qparse(rs);r.eref=qparse(es);}
        std::string extra;if(rf>>extra)throw std::runtime_error("REF "+refpath+" has more points than this range");}
    std::vector<Rec>out(write?total:0);
    Stats all;std::string error;
    #pragma omp parallel num_threads(threads)
    {
        Stats st;Scratch s;
        #pragma omp for schedule(dynamic,1)
        for(uint64_t w=0;w<total;++w){try{
            const Graph&g=graphs[w/n];const uint64_t i=begin+w%n;s.resize(g);
            Net net(dim,bits,dir,seed+0x9e3779b97f4a7c15ULL*1+0xbf58476d1ce4e5b9ULL*(g.id+1),i);std::array<ld,DIMMAX>u{};net.point(u.data());
            std::array<ld,NLOGS>logs{};int level=0;sample(g,u.data(),0,logs,level,0,s);
            std::array<ld,EMAX>lx{};for(int j=0;j<g.E;++j)lx[j]=s.lx[j];
            // evaluate()'s shift, recomputed with its own statements; then evaluate() at factor = shift: y = f * Z.
            ld shift=0;bool direct=true;for(int j=0;j<g.E;++j)if(lx[j]<-600||lx[j]>0)direct=false;
            if(!direct){shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld v=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;v+=lx[j];}shift=std::max(shift,v);}}
            bool moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
            const Eval e=evaluate(g,lx.data(),shift,s);
#ifdef C8_NUMERICS
            const int tier=e.level==0?0:nx::last_tier;
#else
            const int tier=e.level==0?0:(e.level==1?2:4);
#endif
            const uint64_t h=lxhash(lx.data(),g.E);
            auto note=[&](const std::string&what){if(st.first.size()<20){std::ostringstream o;o<<"graph "<<g.id<<" point "<<i<<": "<<what;st.first.push_back(o.str());}};
            st.points++;st.level[e.level]++;st.tier[tier]++;st.nonmoderate+=!moderate;st.nondirect+=!direct;
            if(e.level!=level){st.level_mismatch++;note("evaluate() level "+std::to_string(e.level)+" != sample() level "+std::to_string(level));}
            Rec r;r.graph=g.id;r.point=i;r.hash=h;r.level=e.level;r.tier=tier;r.y=Q(e.y);
            if(write){auto ref=independent(g,lx.data(),shift);const Ref z=Ref(g.Z);
                r.yref=qparse(Ref(ref.first*z).str(40,std::ios_base::scientific));r.eref=qparse(Ref(ref.second*z).str(8,std::ios_base::scientific));out[w]=r;}
            else{const Rec&b=base[w];
                if(b.graph!=r.graph||b.point!=r.point||b.hash!=r.hash)throw std::runtime_error("point mismatch with REF at graph "+std::to_string(g.id)+" point "+std::to_string(i)+" (REF: graph "+std::to_string(b.graph)+" point "+std::to_string(b.point)+")");
                r.yref=b.yref;r.eref=b.eref;st.trans[b.tier][tier]++;
                if(r.y==b.y)st.identical++;
                Q pd=r.y==b.y?Q(0):fabsq(r.y-b.y)/(b.y!=0?fabsq(b.y):Q(1));st.h_pair[bin_of(pd)]++;if(pd>st.pair_max)st.pair_max=pd;}
            const Q d=fabsq(r.y-r.yref),rel=r.yref!=0?d/fabsq(r.yref):d,sc=r.eref>0?d/r.eref:d;
            st.h_rel[tier][bin_of(rel)]++;st.h_scaled[tier][bin_of(sc)]++;if(rel>st.rel_max[tier])st.rel_max[tier]=rel;if(sc>st.scaled_max[tier])st.scaled_max[tier]=sc;
            if(rel>Q(1e-6L)){st.viol[tier]++;note(std::string("relative error ")+qstr(rel,3)+" > 1e-6 in tier "+TN[tier]);}
#ifdef C8_NX_F1_CHECKS
            C8_NX_F1_CHECKS(g,lx.data(),shift,st.checks);
#endif
        }catch(const std::exception&ex){
            #pragma omp critical
            {if(error.empty())error=ex.what();}
        }}
        #pragma omp critical
        {all.add(st);}
    }
    if(!error.empty())throw std::runtime_error(error);
    if(write){std::ofstream rf(refpath);if(!rf)throw std::runtime_error("cannot write REF "+refpath);
        for(const auto&r:out)rf<<r.graph<<' '<<r.point<<' '<<r.hash<<' '<<r.level<<' '<<r.tier<<' '<<qstr(r.y,36)<<' '<<qstr(r.yref,36)<<' '<<qstr(r.eref,8)<<'\n';
        if(!rf)throw std::runtime_error("REF write failed");}
#ifdef C8_NUMERICS
    const char* profile=nx::profile_name.s;
#else
    const char* profile="exact";
#endif
    std::ostream&f=std::cout;
    f<<"{\"L\":"<<L<<",\"graphs\":"<<graphs.size()<<",\"begin\":"<<begin<<",\"end\":"<<end<<",\"mode\":\""<<(write?"write":"read")<<"\",\"numerics\":\""<<profile<<"\",\"mp_backend\":\""<<mp_backend<<"\",\"points\":"<<all.points
     <<",\"level\":["<<all.level[0]<<','<<all.level[1]<<','<<all.level[2]<<"],\"level_mismatch\":"<<all.level_mismatch<<",\"nonmoderate\":"<<all.nonmoderate<<",\"nondirect\":"<<all.nondirect;
    f<<",\"tiers\":{";for(int t=0;t<NT;++t){if(t)f<<',';f<<'"'<<TN[t]<<"\":{\"points\":"<<all.tier[t]<<",\"violations\":"<<all.viol[t]<<",\"max_relative_error\":\""<<qstr(all.rel_max[t],3)<<"\",\"max_scaled_error\":\""<<qstr(all.scaled_max[t],3)<<"\",";
        hist(f,"hist_relative",all.h_rel[t]);f<<',';hist(f,"hist_scaled",all.h_scaled[t]);f<<'}';}
    f<<'}';
    if(!write){f<<",\"paired\":{\"identical\":"<<all.identical<<",\"max_relative_difference\":\""<<qstr(all.pair_max,3)<<"\",";hist(f,"hist_relative_difference",all.h_pair);
        f<<",\"transitions\":{";bool first=true;for(int t=0;t<NT;++t)for(int u=0;u<NT;++u)if(all.trans[t][u]){if(!first)f<<',';first=false;f<<'"'<<TN[t]<<"->"<<TN[u]<<"\":"<<all.trans[t][u];}f<<"}}";}
    f<<",\"profile_checks\":{";{bool first=true;for(auto&kv:all.checks){if(!first)f<<',';first=false;f<<'"'<<kv.first<<"\":"<<kv.second;}}f<<'}';
    f<<",\"first_violations\":[";for(size_t k=0;k<all.first.size();++k){if(k)f<<',';f<<'"'<<all.first[k]<<'"';}f<<"]}\n";
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
