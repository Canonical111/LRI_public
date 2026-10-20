// R4c `exp1` development probe (Stage 4c; PLAN A-FLAG-5). F1's A-RPL-5 point set holds (almost) no shifted point
// (shift != 0 needs some lx_j < -600), and exp1 changes nothing else, so F1 alone cannot see exp1 at work. This probe
// (1) counts how often the worker's own points are shifted, per tier, and (2) validates exp1 on forced shifted points
// against independent 450-digit values and against the exact path, and (3) times the tiers on shifted points.
// exp1_probe.py compiles it with the EXACT compile command of an executable's build record (as numerics_flags.py does
// tests/numerics_f1.cpp), once for bin/c8d2_gmp (the exact path) and once for bin/c8d2_gmp_exp1, so each copy runs
// that build's own sample(), evaluate() and calculate_shared.
//   exp1_probe census   L LIST NET BEGIN END SEED RATE THREADS
//       every point as the worker samples it (sample(), layout 0; the net's first matrix, the worker's seed mixing):
//       per level (0 long double, 1 binary128, 2 MP) the points and the shifted points; the non-moderate points; the
//       histogram of min_j lx_j; in an exp1 build, exp1's own counters.
//   exp1_probe lxcensus L LIST NET BEGIN END SEED RATE THREADS
//       the log-coordinates only (sample()'s statements before evaluate(), checked bit for bit against sample() on the
//       first 64 points of every graph): the shifted fraction and the min_j lx_j histogram on many more points.
//   exp1_probe forced   L LIST NET BEGIN END SEED THREADS REF write|read
//       forced shifted points: each sampled point (rate .8) with lx of the edges order[p..E-1] lowered by D, for
//       D in REGIMES and the cut p = 1 + (point mod (E-1)) (a tiny u at sampling step p, the way natural shifted points
//       arise). Per point: evaluate() at factor = shift (status, level, accepted value y = f Z), the binary128 and MP
//       tiers forced (calculate_shared<Q> and calculate_shared<MP,true>: value and error scale), and in write mode the
//       independent 450-digit value of tests/numerics_f1.cpp (no shared prefix products or sums). write (the exact
//       build) stores one line per point in REF; read (the exp1 build) recomputes everything with exp1 and compares
//       with REF: F1's bound on y (relative error <= 1e-6; gated on the points in the precision policy's range,
//       |f450| >= 1e-274 (1 + err), see forced()), the A-RPL-5 bounds on the forced tiers (binary128
//       |q - ref| <= 1e-29 err, MP |m - ref| / (1 + err) <= 1e-280), the paired differences with the exact path, the
//       level transitions, and per edge the shifted coordinate xs_j of both paths against exp(lx_j - shift/L) in 450
//       digits (exp1's: within (|shift/L| + 8) ulps in binary128 and (|shift/L| + 1000) eps in MP).
//   exp1_probe timing   L LIST NET BEGIN END SEED THREADS REPS
//       per point (rate .8): the natural point and the forced shifted points at D = 700 and 2000; per variant the
//       minimum over REPS calls of calculate_shared<Q> and of calculate_shared<MP,C8_MP_NEED_ERROR> (the worker's MP
//       call), in nanoseconds, summed per variant.
//   exp1_probe bound    LIST THREADS
//       per graph the largest |min_j lx_j| any point can reach (all u at the net's smallest value) and a tail bound on the
//       probability of a shifted point (see bound() below).
// One JSON object goes to stdout. Exit 2 on bad input, a REF mismatch, or a census lx replication mismatch.
#include "../../../../../src/kernel.hpp"
#include <chrono>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
#include <omp.h>
using Ref=boost::multiprecision::number<boost::multiprecision::cpp_dec_float<450>>;
#ifdef C8_NUMERICS
static const char* PROFILE=nx::profile_name.s;
#else
static const char* PROFILE="exact";
#endif
#ifdef C8_NUMERICS_EXP1
static constexpr bool EXP1=true;
#else
static constexpr bool EXP1=false;
#endif
struct Net {   // tests/numerics_f1.cpp's Net (the native's digital shift and Gray-code walk)
    int dim,bits;const std::vector<uint64_t>&direction;std::vector<uint64_t>state;uint64_t index;
    Net(int d,int b,const std::vector<uint64_t>&v,uint64_t seed,uint64_t begin):dim(d),bits(b),direction(v),state(d),index(begin){
        std::mt19937_64 rng(seed);for(auto&s:state)s=rng()>>(64-bits);
        uint64_t gray=begin^(begin>>1);while(gray){int k=__builtin_ctzll(gray);gray&=gray-1;for(int j=0;j<dim;++j)state[j]^=direction[j*bits+k];}}
    void point(ld*u)const {for(int j=0;j<dim;++j)u[j]=(ld(state[j])+.5L)/ld(uint64_t(1)<<bits);}
    void next(){int k=__builtin_ctzll(index+1);for(int j=0;j<dim;++j)state[j]^=direction[j*bits+k];++index;}
};
static uint64_t graph_seed(uint64_t seed,const Graph&g){return seed+0x9e3779b97f4a7c15ULL*1+0xbf58476d1ce4e5b9ULL*(g.id+1);}
// sample()'s statements before evaluate() (layout 0): the log-coordinates lx and the order.
static void lx_only(const Graph&g,const ld*uu,Scratch&s){
    int E=g.E,S=(1<<E)-1;
    for(int pos=0;pos<E;++pos){ld u=uu[2*pos]*g.choice_total[S];int pick=-1;
        for(int j=0;j<E;++j)if(S>>j&1){u-=g.dp[S^(1<<j)];if(u<=0){pick=j;break;}}
        if(pick<0)pick=31-__builtin_clz(S);
        s.order[pos]=pick;S^=1<<pick;
        if(S){ld l=logl(uu[2*pos+1])/g.alpha[S];s.lt[pos]=l;}}
    ld cur=0;for(int j=0;j<E;++j){s.lx[s.order[j]]=cur;if(j<E-1)cur+=s.lt[j];}
}
// evaluate()'s shift, with its own statements.
static ld shift_of(const Graph&g,const ld*lx,bool&direct,bool&moderate){
    ld shift=0;direct=true;for(int j=0;j<g.E;++j)if(lx[j]<-600||lx[j]>0)direct=false;
    if(!direct){shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld v=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;v+=lx[j];}shift=std::max(shift,v);}}
    moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
    return shift;
}
static std::pair<Ref,Ref> independent(const Graph&g,const ld*lx,ld shift){   // tests/numerics_f1.cpp's
    std::vector<Ref>x(g.E),xs(g.E),mons(g.masks.size());Ref S=0;const Ref sh=Ref(shift)/g.L;
    for(int j=0;j<g.E;++j){x[j]=exp(Ref(lx[j]));S+=x[j];xs[j]=shift==0?x[j]:exp(Ref(lx[j])-sh);}
    for(size_t k=0;k<g.masks.size();++k){Ref z=1;unsigned m=g.masks[k];while(m){int j=__builtin_ctz(m);m&=m-1;z*=xs[j];}mons[k]=z;}
    Ref v=0,err=0;for(const auto&t:g.terms){Ref U=0,n=0,a=0;for(int i:t.ids)U+=mons[i];for(int j=0;j<g.E;++j){Ref z=Ref(t.co[j])*x[j];n+=z;a+=abs(z);}v+=n/U;err+=a/U;}return{v/S,err/S};
}
static uint64_t lxhash(const ld*lx,int E){uint64_t h=1469598103934665603ULL;for(int j=0;j<E;++j){unsigned char b[sizeof(ld)];std::memcpy(b,&lx[j],sizeof(ld));for(int k=0;k<10;++k){h^=b[k];h*=1099511628211ULL;}}return h;}
static std::string qstr(Q x,int digits=36){char buf[128];quadmath_snprintf(buf,sizeof buf,"%.*Qe",digits-1,x);return buf;}
static Q qparse(const std::string&s){char*end=nullptr;Q x=strtoflt128(s.c_str(),&end);if(!end||*end)throw std::runtime_error("bad number: "+s);return x;}
static std::string lstr(ld x){char buf[64];snprintf(buf,sizeof buf,"%.3Le",x);return buf;}
template<class N> static std::string nstr(const N&x,int digits){return x.str(digits,std::ios_base::scientific);}
// Histogram of min_j lx_j: bin b = floor(-min/50), the last bin -min >= 50 (HB-1).
constexpr int HB=41;
static int hbin(ld m){ld b=-m/50;return b>=HB-1?HB-1:int(b);}
static const int REGIMES[]={700,2000,4500,9000,15000};constexpr int NR=5;
static void force(const Graph&g,const Scratch&s,uint64_t point,int D,ld*lx){
    int p=1+int(point%uint64_t(g.E-1));for(int j=0;j<g.E;++j)lx[j]=s.lx[j];for(int k=p;k<g.E;++k)lx[s.order[k]]-=D;
}
struct Input {int L,dim,bits;std::vector<Graph>graphs;std::vector<uint64_t>dir;};
static Input load_input(int L,const char*list,const char*netpath,ld rate){
    Input in;in.L=L;{std::ifstream f(list);std::string path;while(f>>path){in.graphs.push_back(load_graph(path,rate));if(in.graphs.back().L!=L)throw std::runtime_error("graph of another L: "+path);}}
    if(in.graphs.empty())throw std::runtime_error("empty graph list");
    std::ifstream netf(netpath,std::ios::binary);uint32_t head[3]={0,0,0};netf.read(reinterpret_cast<char*>(head),sizeof head);
    in.dim=head[1];in.bits=head[2];if(!netf||head[0]<1||in.dim!=4*L-1||in.bits<32||in.bits>60)throw std::runtime_error("bad net");
    in.dir.resize(size_t(in.dim)*in.bits);netf.read(reinterpret_cast<char*>(in.dir.data()),in.dir.size()*8);if(!netf)throw std::runtime_error("truncated net");
    return in;
}
template<class F> static void parallel(uint64_t n,int threads,F body){
    std::string error;
    #pragma omp parallel num_threads(threads)
    {
        #pragma omp for schedule(dynamic,1)
        for(uint64_t w=0;w<n;++w){try{body(w,omp_get_thread_num());}catch(const std::exception&e){
            #pragma omp critical
            {if(error.empty())error=e.what();}
        }}
    }
    if(!error.empty())throw std::runtime_error(error);
}
// ------------------------------------------------------------------------------------------------ census, lxcensus
struct Census {unsigned long long points=0,level[3]{},shifted[3]{},nonmoderate=0,beyond_guard=0,hist[HB]{};ld min_lx=0;
    unsigned long long x_shifted[4]{},x_factored[4]{},x_exact_edges=0;
    void add(const Census&o){points+=o.points;nonmoderate+=o.nonmoderate;beyond_guard+=o.beyond_guard;min_lx=std::min(min_lx,o.min_lx);x_exact_edges+=o.x_exact_edges;
        for(int k=0;k<3;++k){level[k]+=o.level[k];shifted[k]+=o.shifted[k];}for(int b=0;b<HB;++b)hist[b]+=o.hist[b];
        for(int k=0;k<4;++k){x_shifted[k]+=o.x_shifted[k];x_factored[k]+=o.x_factored[k];}}};
static int census(bool full,int argc,char**argv){
    if(argc!=10)throw std::runtime_error("census|lxcensus L LIST NET BEGIN END SEED RATE THREADS");
    const int L=std::stoi(argv[2]);const uint64_t begin=std::stoull(argv[5]),end=std::stoull(argv[6]),seed=std::stoull(argv[7]);
    const ld rate=std::stold(argv[8]);const int threads=std::stoi(argv[9]);
    Input in=load_input(L,argv[3],argv[4],rate);if(begin>=end||end>(uint64_t(1)<<in.bits))throw std::runtime_error("bad range");
    const uint64_t n=end-begin;const uint64_t chunk=full?64:4096,nchunks=(n+chunk-1)/chunk;
    std::vector<Census>per(threads);
    parallel(uint64_t(in.graphs.size())*nchunks,threads,[&](uint64_t w,int t){
        const Graph&g=in.graphs[w/nchunks];const uint64_t b=begin+(w%nchunks)*chunk,e=std::min(end,b+chunk);
        Scratch s;s.resize(g);Census&c=per[t];Net net(in.dim,in.bits,in.dir,graph_seed(seed,g),b);std::array<ld,DIMMAX>u{};
        for(uint64_t i=b;i<e;++i,net.next()){net.point(u.data());int level=0;
            if(full){std::array<ld,NLOGS>logs{};sample(g,u.data(),0,logs,level,0,s);}
            else{lx_only(g,u.data(),s);
                if(i<64){Scratch r;r.resize(g);std::array<ld,NLOGS>logs{};int lv;sample(g,u.data(),0,logs,lv,0,r);
                    for(int j=0;j<g.E;++j)if(std::memcmp(&r.lx[j],&s.lx[j],10))throw std::runtime_error("lx replication differs from sample() at graph "+std::to_string(g.id)+" point "+std::to_string(i));}}
            bool direct,moderate;shift_of(g,s.lx.data(),direct,moderate);ld m=0;for(int j=0;j<g.E;++j)m=std::min(m,s.lx[j]);
            c.points++;c.level[level]++;c.shifted[level]+=!direct;c.nonmoderate+=!moderate;c.hist[hbin(m)]++;c.min_lx=std::min(c.min_lx,m);c.beyond_guard+=m< -ld(5000);}
#ifdef C8_NUMERICS_EXP1
        auto&x=nx::exp1::counters;for(int k=0;k<4;++k){c.x_shifted[k]+=x.shifted[k];c.x_factored[k]+=x.factored[k];}c.x_exact_edges+=x.exact_edges;x=nx::exp1::Counters{};
#endif
    });
    Census all;for(auto&c:per)all.add(c);
    std::ostream&f=std::cout;
    f<<"{\"mode\":\""<<(full?"census":"lxcensus")<<"\",\"numerics\":\""<<PROFILE<<"\",\"L\":"<<L<<",\"graphs\":"<<in.graphs.size()<<",\"begin\":"<<begin<<",\"end\":"<<end<<",\"rate\":\""<<argv[8]<<"\",\"points\":"<<all.points
     <<",\"shifted_points\":"<<(all.shifted[0]+all.shifted[1]+all.shifted[2])<<",\"nonmoderate\":"<<all.nonmoderate<<",\"min_lx_below_minus_5000\":"<<all.beyond_guard<<",\"min_lx\":\""<<lstr(all.min_lx)<<"\"";
    if(full)f<<",\"level\":["<<all.level[0]<<','<<all.level[1]<<','<<all.level[2]<<"],\"shifted_by_level\":["<<all.shifted[0]<<','<<all.shifted[1]<<','<<all.shifted[2]<<']';
    f<<",\"hist_min_lx_per_50\":{";bool first=true;for(int b=0;b<HB;++b)if(all.hist[b]){if(!first)f<<',';first=false;f<<'"'<<(b==HB-1?std::string(">=2000"):std::to_string(50*b))<<"\":"<<all.hist[b];}f<<'}';
    if(full&&EXP1){f<<",\"exp1_counters\":{";const char*kn[4]={"binary128","mp350","mp_other","other"};
        for(int k=0;k<4;++k){if(k)f<<',';f<<'"'<<kn[k]<<"\":{\"shifted\":"<<all.x_shifted[k]<<",\"factored\":"<<all.x_factored[k]<<'}';}
        f<<",\"exact_edges_in_shifted_calls\":"<<all.x_exact_edges<<'}';}
    f<<"}\n";return 0;
}
// ------------------------------------------------------------------------------------------------ forced
constexpr int BINS=50;   // floor(log10(x)) bins: "e<k>" for x in [10^k, 10^(k+1)), "zero", "nonfinite"
struct Hist {std::map<std::string,unsigned long long>h;void add(ld x){std::string k;if(x==0)k="zero";else if(!std::isfinite(x))k="nonfinite";else k="e"+std::to_string(int(std::floor(log10l(x))));h[k]++;}
    void merge(const Hist&o){for(auto&kv:o.h)h[kv.first]+=kv.second;}};
struct Forced {
    unsigned long long points=0,status_exact=0,status_exp1=0,status_mismatch=0,trans[3][3]{},f1_exact=0,f1_exp1=0,f1_new=0,y_identical=0,
        q_identical=0,q_bound_exact=0,q_bound_exp1=0,q_bound_new=0,m_identical=0,m_bound_exact=0,m_bound_exp1=0,m_bound_new=0,
        xs_q_edges=0,xs_q_exact_edges=0,xs_q_viol=0,xs_mp_edges=0,xs_mp_viol=0,shifted=0,nonmoderate=0,checks_bad=0,
        beyond=0,in_f1_exact=0,in_f1_exp1=0,in_identical=0,in_f1_new=0,f1_fixed=0;
    ld y_rel_exact=0,y_rel_exp1=0,y_pair=0,q_sc_exact=0,q_sc_exp1=0,m_sc_exact=0,m_sc_exp1=0,xs_q_ulps_exp1=0,xs_q_ulps_exact=0,xs_mp_eps_exp1=0,xs_mp_eps_exact=0,abs_a_max=0,in_pair=0,in_rel_exp1=0;
    Hist q_exact,q_exp1,q_pair,m_pair,ratio;std::vector<std::string>first,pairs;
    void add(const Forced&o){
#define A(x) x+=o.x;
        A(points)A(status_exact)A(status_exp1)A(status_mismatch)A(f1_exact)A(f1_exp1)A(f1_new)A(y_identical)A(q_identical)A(q_bound_exact)A(q_bound_exp1)A(q_bound_new)
        A(m_identical)A(m_bound_exact)A(m_bound_exp1)A(m_bound_new)A(xs_q_edges)A(xs_q_exact_edges)A(xs_q_viol)A(xs_mp_edges)A(xs_mp_viol)A(shifted)A(nonmoderate)A(checks_bad)A(beyond)A(in_f1_exact)A(in_f1_exp1)A(in_identical)A(in_f1_new)A(f1_fixed)
#undef A
#define M(x) x=std::max(x,o.x);
        M(y_rel_exact)M(y_rel_exp1)M(y_pair)M(q_sc_exact)M(q_sc_exp1)M(m_sc_exact)M(m_sc_exp1)M(xs_q_ulps_exp1)M(xs_q_ulps_exact)M(xs_mp_eps_exp1)M(xs_mp_eps_exact)M(abs_a_max)M(in_pair)M(in_rel_exp1)
#undef M
        for(int a=0;a<3;++a)for(int b=0;b<3;++b)trans[a][b]+=o.trans[a][b];q_exact.merge(o.q_exact);q_exp1.merge(o.q_exp1);q_pair.merge(o.q_pair);m_pair.merge(o.m_pair);ratio.merge(o.ratio);
        for(auto&s:o.first)if(first.size()<20)first.push_back(s);for(auto&s:o.pairs)if(pairs.size()<20)pairs.push_back(s);}
};
static ld rel(const Ref&v,const Ref&r){Ref d=abs(v-r);return r!=0?ld((d/abs(r)).convert_to<long double>()):ld(d.convert_to<long double>());}
static Ref refq(Q x){return Ref(qstr(x,36));}
struct Point {int status=0,level=0;Q y=0;std::pair<Q,Q>q;std::pair<MP,MP>m;};
static Point compute(const Graph&g,const ld*lx,ld shift,Scratch&s){
    Point p;try{Eval e=evaluate(g,lx,shift,s);p.level=e.level;p.y=Q(e.y);}catch(const std::exception&){p.status=1;p.y=Q(0);}
    p.q=calculate_shared<Q>(g,lx,shift);p.m=calculate_shared<MP,true>(g,lx,shift);return p;
}
static int forced(int argc,char**argv){
    if(argc!=11||(std::string(argv[10])!="write"&&std::string(argv[10])!="read"))throw std::runtime_error("forced L LIST NET BEGIN END SEED THREADS REF write|read");
    const int L=std::stoi(argv[2]);const uint64_t begin=std::stoull(argv[5]),end=std::stoull(argv[6]),seed=std::stoull(argv[7]);const int threads=std::stoi(argv[8]);
    const std::string refpath=argv[9];const bool write=std::string(argv[10])=="write";
    if(write==EXP1)throw std::runtime_error(write?"write mode belongs to the exact build":"read mode belongs to the exp1 build");
    Input in=load_input(L,argv[3],argv[4],.8L);if(begin>=end||end>(uint64_t(1)<<in.bits))throw std::runtime_error("bad range");
    const uint64_t n=end-begin,total=uint64_t(in.graphs.size())*n*NR;
    std::vector<std::string>lines(total);
    if(!write){std::ifstream rf(refpath);if(!rf)throw std::runtime_error("cannot open REF "+refpath);for(auto&l:lines)if(!std::getline(rf,l))throw std::runtime_error("REF has fewer lines than points");
        std::string extra;if(std::getline(rf,extra))throw std::runtime_error("REF has more lines than points");}
    std::vector<Forced>per(NR*threads);
    const Q eps_q=Q(1)/Q(uint64_t(1)<<56)/Q(uint64_t(1)<<56);   // 2^-112
    const MP eps_mp=std::numeric_limits<MP>::epsilon();
    parallel(total,threads,[&](uint64_t w,int t){
        const uint64_t gi=w/(n*NR),i=begin+(w/NR)%n;const int r=int(w%NR),D=REGIMES[r];const Graph&g=in.graphs[gi];
        Scratch s;s.resize(g);Net net(in.dim,in.bits,in.dir,graph_seed(seed,g),i);std::array<ld,DIMMAX>u{};net.point(u.data());
        std::array<ld,NLOGS>logs{};int lv;sample(g,u.data(),0,logs,lv,0,s);
        std::array<ld,EMAX>lx{};force(g,s,i,D,lx.data());const int cut=1+int(i%uint64_t(g.E-1));
        bool direct,moderate;const ld shift=shift_of(g,lx.data(),direct,moderate);const uint64_t h=lxhash(lx.data(),g.E);
        Point p=compute(g,lx.data(),shift,s);
#ifdef C8_NUMERICS_EXP1
        nx::exp1::counters=nx::exp1::Counters{};
#endif
        std::ostringstream key;key<<g.id<<' '<<i<<' '<<D<<' '<<cut<<' '<<h;
        if(write){auto ref=independent(g,lx.data(),shift);std::ostringstream o;
            o<<key.str()<<' '<<p.status<<' '<<p.level<<' '<<qstr(p.y)<<' '<<qstr(p.q.first)<<' '<<qstr(p.q.second)<<' '<<nstr(p.m.first,360)<<' '<<nstr(p.m.second,12)
             <<' '<<nstr(ref.first,420)<<' '<<nstr(ref.second,12)<<' '<<nstr(Ref(ref.first*Ref(g.Z)),40);
            lines[w]=o.str();return;}
        Forced&c=per[r*threads+t];std::istringstream is(lines[w]);uint64_t gid,pi,hh;int dd,cc,st0,lv0;std::string ys,qv,qe,mv,me,rv,re,ry;
        if(!(is>>gid>>pi>>dd>>cc>>hh>>st0>>lv0>>ys>>qv>>qe>>mv>>me>>rv>>re>>ry)||gid!=uint64_t(g.id)||pi!=i||dd!=D||cc!=cut||hh!=h)throw std::runtime_error("REF line mismatch at graph "+std::to_string(g.id)+" point "+std::to_string(i)+" D "+std::to_string(D));
        auto note=[&](const std::string&what){if(c.first.size()<20)c.first.push_back("graph "+std::to_string(g.id)+" point "+std::to_string(i)+" D "+std::to_string(D)+": "+what);};
        c.points++;c.shifted+=!direct;c.nonmoderate+=!moderate;c.abs_a_max=std::max(c.abs_a_max,fabsl(shift/g.L));
        c.status_exact+=st0!=0;c.status_exp1+=p.status!=0;if(st0!=p.status){c.status_mismatch++;note("evaluate() status differs");}
        if(st0==0&&p.status==0)c.trans[lv0][p.level]++;
        const Ref rval(rv),rerr(re),ryv(ry);
        // The precision policy's range. Its MP tier (350 digits) is accepted without a test, and A-RPL-5 (b) bounds it by
        // |f - f450| <= 1e-280 (1 + err); this implies F1's relative 1e-6 only where |f450| >= 1e-274 (1 + err) ("in
        // range"; natural points have |val|/err >= 1e-131, P3). Below it ("beyond"), both paths hold the policy's bound
        // but neither value has a guaranteed relative accuracy, and their F1 outcomes are compared only for information.
        const ld ratio=rerr>0?ld((abs(rval)/rerr).convert_to<long double>()):ld(1);c.ratio.add(ratio);
        const bool inrange=abs(rval)>=Ref("1e-274")*(1+rerr);c.beyond+=!inrange;
        // F1's bound on the accepted value, both paths
        if(st0==0&&p.status==0){const Q y0=qparse(ys);const ld e0=rel(refq(y0),ryv),e1=rel(refq(p.y),ryv);
            c.y_rel_exact=std::max(c.y_rel_exact,e0);c.y_rel_exp1=std::max(c.y_rel_exp1,e1);
            const bool v0=!(e0<=1e-6L),v1=!(e1<=1e-6L);c.f1_exact+=v0;c.f1_exp1+=v1;c.f1_fixed+=v0&&!v1;
            if(v1&&!v0){c.f1_new++;c.in_f1_new+=inrange;note(std::string("F1 bound broken by exp1 only (")+(inrange?"IN RANGE":"beyond the policy's range")+"): rel "+lstr(e1)+", level "+std::to_string(lv0)+"->"+std::to_string(p.level)
                +", |val|/err "+lstr(ratio)+", y "+qstr(y0,12)+" -> "+qstr(p.y,12)+", ref "+nstr(ryv,12));}
            const ld pd=p.y==y0?ld(0):rel(refq(p.y),refq(y0));if(p.y==y0)c.y_identical++;else c.y_pair=std::max(c.y_pair,pd);
            if(inrange){c.in_f1_exact+=v0;c.in_f1_exp1+=v1;c.in_identical+=p.y==y0;c.in_pair=std::max(c.in_pair,pd);c.in_rel_exp1=std::max(c.in_rel_exp1,e1);}
            if(pd>1e-9L&&c.pairs.size()<20)c.pairs.push_back("graph "+std::to_string(g.id)+" point "+std::to_string(i)+" D "+std::to_string(D)+": paired "+lstr(pd)+", level "+std::to_string(lv0)+"->"+std::to_string(p.level)
                +", |val|/err "+lstr(ratio)+", rel exact "+lstr(e0)+" exp1 "+lstr(e1)+", y "+qstr(y0,12)+" -> "+qstr(p.y,12)+", ref "+nstr(ryv,12));}
        // the binary128 tier forced: |q - ref| <= 1e-29 err_q (A-RPL-5 (a)), both paths
        {const Q q0=qparse(qv),qe0=qparse(qe);
            auto sc=[&](Q v,Q e)->ld{if(!finiteq(v)||!finiteq(e))return std::numeric_limits<ld>::infinity();Ref d=abs(refq(v)-rval);return e>0?ld((d/refq(e)).convert_to<long double>()):(d==0?0:std::numeric_limits<ld>::infinity());};
            const ld s0=sc(q0,qe0),s1=sc(p.q.first,p.q.second);c.q_exact.add(s0);c.q_exp1.add(s1);c.q_sc_exact=std::max(c.q_sc_exact,s0);c.q_sc_exp1=std::max(c.q_sc_exp1,s1);
            const bool v0=!(s0<=1e-29L),v1=!(s1<=1e-29L);c.q_bound_exact+=v0;c.q_bound_exp1+=v1;if(v1&&!v0){c.q_bound_new++;note("binary128 bound broken by exp1 only: "+lstr(s1));}
            if(memcmp(&q0,&p.q.first,sizeof(Q))==0)c.q_identical++;else c.q_pair.add(rel(refq(p.q.first),refq(q0)));}
        // the MP tier forced: |m - ref| / (1 + err) <= 1e-280 (A-RPL-5 (b)), both paths
        {const Ref m0(mv),m1(nstr(p.m.first,360));const ld s0=ld((abs(m0-rval)/(1+rerr)).convert_to<long double>()),s1=ld((abs(m1-rval)/(1+rerr)).convert_to<long double>());
            c.m_sc_exact=std::max(c.m_sc_exact,s0);c.m_sc_exp1=std::max(c.m_sc_exp1,s1);const bool v0=!(s0<=1e-280L),v1=!(s1<=1e-280L);c.m_bound_exact+=v0;c.m_bound_exp1+=v1;
            if(v1&&!v0){c.m_bound_new++;note("MP bound broken by exp1 only: "+lstr(s1));}
            if(m1==m0)c.m_identical++;else c.m_pair.add(rel(m1,m0));}
#ifdef C8_NUMERICS_EXP1
        // per edge: xs_j of both paths against exp(lx_j - shift/L) in 450 digits (exp1's formula through its own helpers)
        if(shift!=0){const ld a=fabsl(shift/g.L);const Ref sh=Ref(shift)/g.L;
            const auto Fq=nx::exp1::begin<Q>(g,shift);const auto Fm=nx::exp1::begin<MP>(g,shift);nx::exp1::counters=nx::exp1::Counters{};
            for(int j=0;j<g.E;++j){const Ref tr=exp(Ref(lx[j])-sh);
                const Q x=exponential(Q(lx[j])),xs0=exponential(quadfast::sub(Q(lx[j]),Q(shift)/g.L));
                if(Fq.on&&nx::exp1::edge_in_range(lx[j])){const Q xs1=quadfast::mul(x,Fq.f);c.xs_q_edges++;
                    const ld u1=rel(refq(xs1),tr)/ld(eps_q),u0=rel(refq(xs0),tr)/ld(eps_q);c.xs_q_ulps_exp1=std::max(c.xs_q_ulps_exp1,u1);c.xs_q_ulps_exact=std::max(c.xs_q_ulps_exact,u0);
                    if(!(u1<=a+8)){c.xs_q_viol++;note("binary128 xs_"+std::to_string(j)+" off by "+lstr(u1)+" ulps");}}
                else c.xs_q_exact_edges++;
                const MP xm=exponential(MP(lx[j])),xm1=nx::exp1::scaled<MP>(xm,Fm),xm0=exponential(MP(MP(lx[j])-MP(shift)/g.L));c.xs_mp_edges++;
                const ld e1=rel(Ref(nstr(xm1,360)),tr)/ld(eps_mp.convert_to<long double>()),e0=rel(Ref(nstr(xm0,360)),tr)/ld(eps_mp.convert_to<long double>());
                c.xs_mp_eps_exp1=std::max(c.xs_mp_eps_exp1,e1);c.xs_mp_eps_exact=std::max(c.xs_mp_eps_exact,e0);
                if(!(e1<=a+1000)){c.xs_mp_viol++;note("MP xs_"+std::to_string(j)+" off by "+lstr(e1)+" eps");}}}
#endif
    });
    if(write){std::ofstream rf(refpath);if(!rf)throw std::runtime_error("cannot write REF");for(auto&l:lines)rf<<l<<'\n';if(!rf)throw std::runtime_error("REF write failed");
        std::cout<<"{\"mode\":\"forced\",\"write\":true,\"numerics\":\""<<PROFILE<<"\",\"L\":"<<L<<",\"graphs\":"<<in.graphs.size()<<",\"points\":"<<total<<"}\n";return 0;}
    std::ostream&f=std::cout;
    auto hist=[&](const char*name,const Hist&h){f<<'"'<<name<<"\":{";bool first=true;for(auto&kv:h.h){if(!first)f<<',';first=false;f<<'"'<<kv.first<<"\":"<<kv.second;}f<<'}';};
    auto emit=[&](const Forced&c){
        f<<"{\"points\":"<<c.points<<",\"beyond_policy_range\":"<<c.beyond<<",\"in_range\":{\"f1_violations_exact\":"<<c.in_f1_exact<<",\"f1_violations_exp1\":"<<c.in_f1_exp1
         <<",\"y_identical\":"<<c.in_identical<<",\"max_paired_rel\":\""<<lstr(c.in_pair)<<"\",\"max_rel_exp1\":\""<<lstr(c.in_rel_exp1)<<"\"},";hist("hist_ref_ratio",c.ratio);f<<",\"shifted\":"<<c.shifted<<",\"nonmoderate\":"<<c.nonmoderate<<",\"max_abs_shift_over_L\":\""<<lstr(c.abs_a_max)<<"\",\"evaluate_threw\":{\"exact\":"<<c.status_exact<<",\"exp1\":"<<c.status_exp1<<",\"mismatch\":"<<c.status_mismatch<<'}'
         <<",\"level_transitions\":[";for(int a=0;a<3;++a){if(a)f<<',';f<<'['<<c.trans[a][0]<<','<<c.trans[a][1]<<','<<c.trans[a][2]<<']';}
        f<<"],\"f1\":{\"violations_exact\":"<<c.f1_exact<<",\"violations_exp1\":"<<c.f1_exp1<<",\"new_violations\":"<<c.f1_new<<",\"new_violations_in_range\":"<<c.in_f1_new<<",\"fixed_by_exp1\":"<<c.f1_fixed<<",\"max_rel_exact\":\""<<lstr(c.y_rel_exact)<<"\",\"max_rel_exp1\":\""<<lstr(c.y_rel_exp1)<<"\",\"identical\":"<<c.y_identical<<",\"max_paired_rel\":\""<<lstr(c.y_pair)<<"\"}"
         <<",\"binary128_forced\":{\"bound_violations_exact\":"<<c.q_bound_exact<<",\"bound_violations_exp1\":"<<c.q_bound_exp1<<",\"new_violations\":"<<c.q_bound_new<<",\"max_scaled_exact\":\""<<lstr(c.q_sc_exact)<<"\",\"max_scaled_exp1\":\""<<lstr(c.q_sc_exp1)<<"\",\"identical\":"<<c.q_identical<<',';
        hist("hist_scaled_exact",c.q_exact);f<<',';hist("hist_scaled_exp1",c.q_exp1);f<<',';hist("hist_paired_rel",c.q_pair);
        f<<"},\"mp_forced\":{\"bound_violations_exact\":"<<c.m_bound_exact<<",\"bound_violations_exp1\":"<<c.m_bound_exp1<<",\"new_violations\":"<<c.m_bound_new<<",\"max_scaled_exact\":\""<<lstr(c.m_sc_exact)<<"\",\"max_scaled_exp1\":\""<<lstr(c.m_sc_exp1)<<"\",\"identical\":"<<c.m_identical<<',';
        hist("hist_paired_rel",c.m_pair);
        f<<"},\"xs\":{\"binary128_edges_exp1\":"<<c.xs_q_edges<<",\"binary128_edges_exact_expression\":"<<c.xs_q_exact_edges<<",\"binary128_violations\":"<<c.xs_q_viol<<",\"binary128_max_ulps_exp1\":\""<<lstr(c.xs_q_ulps_exp1)<<"\",\"binary128_max_ulps_exact\":\""<<lstr(c.xs_q_ulps_exact)
         <<"\",\"mp_edges\":"<<c.xs_mp_edges<<",\"mp_violations\":"<<c.xs_mp_viol<<",\"mp_max_eps_exp1\":\""<<lstr(c.xs_mp_eps_exp1)<<"\",\"mp_max_eps_exact\":\""<<lstr(c.xs_mp_eps_exact)<<"\",\"mp_epsilon\":\""<<lstr(ld(std::numeric_limits<MP>::epsilon().convert_to<long double>()))<<"\"}";
        f<<",\"first\":[";for(size_t k=0;k<c.first.size();++k){if(k)f<<',';f<<'"'<<c.first[k]<<'"';}
        f<<"],\"paired_differences\":[";for(size_t k=0;k<c.pairs.size();++k){if(k)f<<',';f<<'"'<<c.pairs[k]<<'"';}f<<"]}";};
    Forced tot;f<<"{\"mode\":\"forced\",\"write\":false,\"numerics\":\""<<PROFILE<<"\",\"L\":"<<L<<",\"graphs\":"<<in.graphs.size()<<",\"begin\":"<<begin<<",\"end\":"<<end<<",\"regimes\":{";
    for(int r=0;r<NR;++r){Forced c;for(int t=0;t<threads;++t)c.add(per[r*threads+t]);tot.add(c);if(r)f<<',';f<<"\"D"<<REGIMES[r]<<"\":";emit(c);}
    f<<"},\"total\":";emit(tot);f<<"}\n";return 0;
}
// ------------------------------------------------------------------------------------------------ timing
static int timing(int argc,char**argv){
    if(argc!=10)throw std::runtime_error("timing L LIST NET BEGIN END SEED THREADS REPS");
    const int L=std::stoi(argv[2]);const uint64_t begin=std::stoull(argv[5]),end=std::stoull(argv[6]),seed=std::stoull(argv[7]);const int threads=std::stoi(argv[8]),reps=std::stoi(argv[9]);
    Input in=load_input(L,argv[3],argv[4],.8L);if(begin>=end||reps<1)throw std::runtime_error("bad range");
    const uint64_t n=end-begin,total=uint64_t(in.graphs.size())*n;constexpr int NV=3;const int DV[NV]={0,700,2000};
    struct T {unsigned long long calls=0,shifted=0;double q_ns=0,mp_ns=0;};std::vector<std::array<T,NV>>per(threads);
    using clk=std::chrono::steady_clock;
    parallel(total,threads,[&](uint64_t w,int t){
        const Graph&g=in.graphs[w/n];const uint64_t i=begin+w%n;Scratch s;s.resize(g);Net net(in.dim,in.bits,in.dir,graph_seed(seed,g),i);std::array<ld,DIMMAX>u{};net.point(u.data());
        std::array<ld,NLOGS>logs{};int lv;sample(g,u.data(),0,logs,lv,0,s);
        for(int v=0;v<NV;++v){std::array<ld,EMAX>lx{};if(DV[v])force(g,s,i,DV[v],lx.data());else for(int j=0;j<g.E;++j)lx[j]=s.lx[j];
            bool direct,moderate;const ld shift=shift_of(g,lx.data(),direct,moderate);double bq=1e300,bm=1e300;volatile double sink=0;
            for(int k=0;k<reps;++k){auto t0=clk::now();auto q=calculate_shared<Q>(g,lx.data(),shift);auto t1=clk::now();sink=sink+double(q.first);
                bq=std::min(bq,std::chrono::duration<double,std::nano>(t1-t0).count());}
            for(int k=0;k<reps;++k){auto t0=clk::now();auto m=calculate_shared<MP,C8_MP_NEED_ERROR>(g,lx.data(),shift);auto t1=clk::now();sink=sink+m.first.convert_to<double>();
                bm=std::min(bm,std::chrono::duration<double,std::nano>(t1-t0).count());}
            T&x=per[t][v];x.calls++;x.shifted+=!direct;x.q_ns+=bq;x.mp_ns+=bm;}
    });
    std::ostream&f=std::cout;f<<"{\"mode\":\"timing\",\"numerics\":\""<<PROFILE<<"\",\"L\":"<<L<<",\"graphs\":"<<in.graphs.size()<<",\"begin\":"<<begin<<",\"end\":"<<end<<",\"reps\":"<<reps<<",\"threads\":"<<threads<<",\"variants\":{";
    for(int v=0;v<NV;++v){T a;for(auto&p:per){a.calls+=p[v].calls;a.shifted+=p[v].shifted;a.q_ns+=p[v].q_ns;a.mp_ns+=p[v].mp_ns;}
        if(v)f<<',';f<<'"'<<(DV[v]?"D"+std::to_string(DV[v]):std::string("natural"))<<"\":{\"calls\":"<<a.calls<<",\"shifted\":"<<a.shifted<<",\"binary128_ns\":"<<std::setprecision(17)<<a.q_ns<<",\"mp_ns\":"<<a.mp_ns<<'}';}
    f<<"}}\n";return 0;
}
// ------------------------------------------------------------------------------------------------ bound
// Whether a graph can produce a shifted point at all. sample() (layout 0) sets lx of the edge picked at step k to the sum
// of lt_i = log(u_i)/alpha[S_i] over the earlier steps (S_i the nonempty remaining set after step i), so every lx_j <= 0
// and the most negative is the last edge's, the sum over the E-1 steps of a chain full = S_0 > S_1 > ... > S_{E-2}
// (|S_{E-2}| = 1). The native nets have bits <= 60 (u >= 2^-61), so |log u| <= 61 ln 2 = 42.28 and
//     -min_j lx_j <= (bits+1) ln 2 / rate * C0,   C0 = max over chains of sum 1/alpha0[S_i]   (alpha0: the file's rates),
// by a DP over the subsets (supersets are larger integers). A shifted point (some lx_j < -600) is impossible when this
// bound is <= 600. Probability (independent uniform u, the Monte-Carlo idealisation of the net): every term is
// X_i/alpha_i with X_i ~ Exp(1) and alpha_i >= rate * amin (amin: the smallest alpha0 over 0 < S < full), so
// P(min lx < -600) <= P(Gamma(E-1, 1) > 600 rate amin) = exp(-x) sum_{k<E-1} x^k/k!, x = 600 rate amin.
//   exp1_probe bound LIST THREADS      one JSON object: per graph (id, L, C0, amin), in LIST order
static long double log10_gamma_tail(int m,long double x){   // log10 P(Gamma(m,1) > x)
    long double t=0,lsum=-INFINITY;for(int k=0;k<m;++k){long double lk=k*logl(x)-t;lsum=std::max(lsum,lk)+log1pl(expl(-fabsl(lsum-lk)));t+=logl(k+1);}
    return (lsum-x)/logl(10);
}
static int bound(int argc,char**argv){
    if(argc!=4)throw std::runtime_error("bound LIST THREADS");
    std::vector<std::string>paths;{std::ifstream f(argv[2]);std::string q;while(f>>q)paths.push_back(q);}
    if(paths.empty())throw std::runtime_error("empty graph list");
    const int threads=std::stoi(argv[3]);struct R{int id=0,L=0;ld c0=0,amin=0;};std::vector<R>res(paths.size());
    parallel(paths.size(),threads,[&](uint64_t w,int){const Graph g=load_graph(paths[w],1.0L);const int E=g.E,F=(1<<E)-1;
        std::vector<ld>best(F+1,-1);best[F]=0;ld amin=INFINITY;for(int S=1;S<F;++S)amin=std::min(amin,g.alpha[S]);
        for(int S=F;S>0;--S){if(best[S]<0)continue;for(int j=0;j<E;++j)if(S>>j&1){const int T=S^(1<<j);if(T){const ld v=best[S]+1/g.alpha[T];if(v>best[T])best[T]=v;}}}
        ld c=0;for(int j=0;j<E;++j)c=std::max(c,best[1<<j]);res[w]={g.id,g.L,c,amin};});
    std::ostream&f=std::cout;f<<"{\"mode\":\"bound\",\"graphs\":[";
    for(size_t k=0;k<res.size();++k){const R&r=res[k];if(k)f<<',';f<<'['<<r.id<<','<<r.L<<','<<std::setprecision(10)<<double(r.c0)<<','<<double(r.amin)<<','<<double(log10_gamma_tail(2*r.L-1,600*0.8L*r.amin))<<']';}
    f<<"],\"columns\":[\"id\",\"L\",\"C0\",\"amin\",\"log10_P_shift_bound_rate_0.8\"]}\n";return 0;
}
int main(int argc,char**argv){try{
    const std::string mode=argc>1?argv[1]:"";
    if(mode=="census")return census(true,argc,argv);
    if(mode=="lxcensus")return census(false,argc,argv);
    if(mode=="forced")return forced(argc,argv);
    if(mode=="timing")return timing(argc,argv);
    if(mode=="bound")return bound(argc,argv);
    std::cerr<<"exp1_probe census|lxcensus|forced|timing|bound ...\n";return 1;
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
