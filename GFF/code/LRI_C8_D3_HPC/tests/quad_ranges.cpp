// Stage 4b #4 (= C62d's R3a; port of LRI_C8_D2_HPC@14d7347 tests/quad_ranges.cpp, sha256 adbcb7ed..., names only): the
// operand ranges the d=3 kernel's binary128 tier actually sees (PLAN "Performance plan", R3a proof: the
// differential test covers "the exponent ranges P1 observes"). Built by `make quaddiff` (bin/c8d3_quad_ranges) with the
// worker's gmp command; driven by tests/quad_differential.py.
//
//   c8d3_quad_ranges GRAPHS_ROOT L RATE NPOINTS SEED THREADS ID [ID ...]   -> one JSON object on stdout
//
// For every graph G<ID> of GRAPHS_ROOT/L<L>, NPOINTS uniform pseudo-random points go through kernel.hpp's own sample()
// (layout 0, K = 0: the point map, evaluate() with its 1e-9 and 1e-23 tests, calculate_shared<Q> for the promoted
// points). This program defines C8_QUADFAST_OBSERVE before including kernel.hpp, so every operand pair of
// quadfast::add/sub/mul, i.e. every binary128 +, - and * of calculate_shared<Q>, is recorded: operand classes,
// the biased-exponent range and histogram (bins of 256) of normal operands and results, for add/sub the exponent
// difference d and the effective-subtraction cancellation depth, and how many pairs take the inline fast path. The
// results are libgcc's (the observer recomputes them); the worker's arithmetic is unchanged.
#include <cstdint>
void qr_observe(char op,__float128 a,__float128 b);
#define C8_QUADFAST_OBSERVE(op,a,b) qr_observe(op,a,b)
#include "../src/kernel.hpp"
#include <cstdio>
#include <iostream>
#include <random>
#include <string>
#include <vector>
#include <omp.h>
namespace qf=quadfast;
constexpr int EBINS=128,DBINS=131,SBINS=117;
struct OpStats {
    unsigned long long n=0,normal=0,zero=0,subnormal=0,infnan=0,fast=0,eff_sub=0,res_zero=0,res_subnormal=0,res_inf=0;
    int emin=1<<30,emax=-1,rmin=1<<30,rmax=-1;
    unsigned long long ehist[EBINS]{},rhist[EBINS]{},dhist[DBINS]{},shist[SBINS]{};
    void add(const OpStats&o){
        n+=o.n;normal+=o.normal;zero+=o.zero;subnormal+=o.subnormal;infnan+=o.infnan;fast+=o.fast;eff_sub+=o.eff_sub;
        res_zero+=o.res_zero;res_subnormal+=o.res_subnormal;res_inf+=o.res_inf;
        emin=std::min(emin,o.emin);emax=std::max(emax,o.emax);rmin=std::min(rmin,o.rmin);rmax=std::max(rmax,o.rmax);
        for(int i=0;i<EBINS;++i){ehist[i]+=o.ehist[i];rhist[i]+=o.rhist[i];}
        for(int i=0;i<DBINS;++i)dhist[i]+=o.dhist[i];
        for(int i=0;i<SBINS;++i)shist[i]+=o.shist[i];
    }
};
struct Stats {OpStats op[3];unsigned long long points=0,quad=0,mp=0;};
static thread_local Stats TS;
static int expo(qf::u128 u){return int(u>>112)&0x7FFF;}
void qr_observe(char c,__float128 a,__float128 b){
    const int k=c=='+'?0:(c=='-'?1:2);OpStats&s=TS.op[k];++s.n;
    const qf::u128 ua=qf::bits(a),ub=qf::bits(b);const int ea=expo(ua),eb=expo(ub);
    const bool za=(ua<<1)==0,zb=(ub<<1)==0;
    if(za||zb)++s.zero;
    if((ea==0&&!za)||(eb==0&&!zb))++s.subnormal;
    if(ea==0x7FFF||eb==0x7FFF)++s.infnan;
    const bool normal=ea>=1&&ea<=0x7FFE&&eb>=1&&eb<=0x7FFE;
    if(normal)++s.normal;
    for(int e:{ea,eb})if(e>=1&&e<=0x7FFE){s.emin=std::min(s.emin,e);s.emax=std::max(s.emax,e);++s.ehist[e>>8];}
    qf::u128 ur,f;bool fast;
    if(k==0){ur=qf::slow_add(ua,ub);fast=qf::addsub_fast<false>(ua,ub,f);}
    else if(k==1){ur=qf::slow_sub(ua,ub);fast=qf::addsub_fast<true>(ua,ub,f);}
    else{ur=qf::slow_mul(ua,ub);fast=qf::mul_fast(ua,ub,f);}
    s.fast+=fast;
    const int er=expo(ur);
    if((ur<<1)==0)++s.res_zero;else if(er==0)++s.res_subnormal;else if(er==0x7FFF)++s.res_inf;
    else{s.rmin=std::min(s.rmin,er);s.rmax=std::max(s.rmax,er);++s.rhist[er>>8];}
    if(k<2&&normal){
        const int d=ea>eb?ea-eb:eb-ea;++s.dhist[std::min(d,DBINS-1)];
        const bool sub=((ua^ub)>>127)!=(k==1);
        if(sub){++s.eff_sub;if(er>=1&&er<=0x7FFE){int sh=std::max(ea,eb)-er;if(sh>=0)++s.shist[std::min(sh,SBINS-1)];}}
    }
}
static void put_hist(const char*name,const unsigned long long*h,int n,int scale){
    std::printf("\"%s\":{",name);bool first=true;
    for(int i=0;i<n;++i)if(h[i]){std::printf("%s\"%d\":%llu",first?"":",",i*scale,h[i]);first=false;}
    std::printf("}");
}
int main(int argc,char**argv){try{
    if(argc<8){std::cerr<<"GRAPHS_ROOT L RATE NPOINTS SEED THREADS ID [ID ...]\n";return 2;}
    const std::string root=argv[1];const int L=std::stoi(argv[2]);const ld rate=std::stold(argv[3]);
    const long npoints=std::stol(argv[4]);const uint64_t seed=std::stoull(argv[5]);const int threads=std::stoi(argv[6]);
    std::vector<int> ids;for(int i=7;i<argc;++i)ids.push_back(std::stoi(argv[i]));
    Stats total;std::string error;
    #pragma omp parallel num_threads(threads)
    {
        Scratch scratch;
        #pragma omp for schedule(dynamic,1)
        for(size_t gi=0;gi<ids.size();++gi){
            try{
                Graph g=load_graph(root+"/L"+std::to_string(L)+"/G"+std::to_string(ids[gi])+".txt",rate);scratch.resize(g);
                std::mt19937_64 rng(seed*0x9e3779b97f4a7c15ULL+uint64_t(ids[gi]));std::array<ld,DIMMAX> u{};std::array<ld,NLOGS> logs{};
                for(long p=0;p<npoints;++p){
                    for(int j=0;j<4*L-1;++j)u[j]=(ld(rng()>>11)+.5L)/ld(uint64_t(1)<<53);
                    int level=0;sample(g,u.data(),0,logs,level,0,scratch);
                    ++TS.points;TS.quad+=level>=1;TS.mp+=level>=2;
                }
            }catch(const std::exception&e){
                #pragma omp critical(err)
                {if(error.empty())error=e.what();}
            }
        }
        #pragma omp critical(merge)
        {for(int k=0;k<3;++k)total.op[k].add(TS.op[k]);total.points+=TS.points;total.quad+=TS.quad;total.mp+=TS.mp;}
    }
    if(!error.empty())throw std::runtime_error(error);
    std::printf("{\"schema\":\"c8-d3-quad-ranges-1\",\"L\":%d,\"rate\":\"%s\",\"graphs\":%zu,\"points_per_graph\":%ld,\"seed\":%llu,\"points\":%llu,\"quad_points\":%llu,\"mp_points\":%llu,\"ops\":{",
        L,argv[3],ids.size(),npoints,(unsigned long long)seed,total.points,total.quad,total.mp);
    const char*names[3]={"add","sub","mul"};
    for(int k=0;k<3;++k){const OpStats&s=total.op[k];
        std::printf("%s\"%s\":{\"n\":%llu,\"both_normal\":%llu,\"zero_operand\":%llu,\"subnormal_operand\":%llu,\"inf_nan_operand\":%llu,\"fast\":%llu,\"effective_sub\":%llu,"
            "\"result_zero\":%llu,\"result_subnormal\":%llu,\"result_inf_nan\":%llu,\"operand_exponent_min\":%d,\"operand_exponent_max\":%d,\"result_exponent_min\":%d,\"result_exponent_max\":%d,",
            k?",":"",names[k],s.n,s.normal,s.zero,s.subnormal,s.infnan,s.fast,s.eff_sub,s.res_zero,s.res_subnormal,s.res_inf,
            s.n?s.emin:-1,s.emax,s.n?s.rmin:-1,s.rmax);
        put_hist("operand_exponent_hist256",s.ehist,EBINS,256);std::printf(",");put_hist("result_exponent_hist256",s.rhist,EBINS,256);
        if(k<2){std::printf(",");put_hist("exponent_difference_hist",s.dhist,DBINS,1);std::printf(",");put_hist("cancellation_shift_hist",s.shist,SBINS,1);}
        std::printf("}");}
    std::printf("},\"compiler\":\"%s\",\"bias\":16383}\n",__VERSION__);
    return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
