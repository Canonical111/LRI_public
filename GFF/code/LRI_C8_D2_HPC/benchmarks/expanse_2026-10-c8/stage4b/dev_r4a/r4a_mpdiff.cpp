// R4a differential test and MP-tier micro-benchmark (Stage 4b development; not part of any worker build).
// Built with the worker's gmp flags (-DC8_USE_GMP) against src/kernel.hpp. For every graph file given:
//   * NPOINTS points drawn as sample() does for layout 0 (uniform u, the same choice walk and logarithms), with
//     every EXTREME-th point pushed far out (its odd uniforms raised to the power 100) so that some log-coordinate is
//     below -600 and evaluate()'s shift is nonzero (the xs exponentials of the MP tier); shift as evaluate() computes it;
//   * "reference": the generic calculate_shared<T,NeedError> body of src/kernel.hpp before R4a (C7(2)'s a55958f),
//     copied verbatim below under the name reference_shared, i.e. the Boost expression-template code;
//   * "r4a": kernel.hpp's calculate_shared<MP,false> and <MP,true> (calculate_shared_gmp, R4a);
//   * "prefetch": the R4a code plus software prefetches of the next products (variant under test, below).
// Exactness: the mpf representation (precision, sign and size, exponent, every limb) of r4a's and prefetch's first
// element equals the reference's for NeedError=false, and both elements for NeedError=true (r4a only), at every point.
// Timing: each variant evaluates the graph's points (NeedError=false) REPEATS times in rotating order; per variant the
// sum over repeats of its steady_clock seconds. Graphs run in parallel (OpenMP, dynamic), each thread with its own
// per-thread scratch, so the timings include the L3 sharing of a busy node.
//   r4a_mpdiff OUT.json NPOINTS EXTREME REPEATS SEED RATE GRAPH_FILE...
#include "../../../../src/kernel.hpp"
#include <chrono>
#include <cstdio>
#include <iostream>
#include <random>
#include <string>
#include <omp.h>

// ---- the pre-R4a generic body, verbatim (src/kernel.hpp at a785602, lines 174-190), renamed.
template<class T,bool NeedError=true>
std::pair<T,T> reference_shared(const Graph&g,const ld*logx,ld shift) {
    static thread_local PromotedScratch<T> scratch;
    auto&s=scratch;s.resize(g);T S=0;s.products[0]=1;s.sums[0]=0;
    for(int j=0;j<g.E;++j){s.x[j]=exponential(T(logx[j]));S+=s.x[j];
        s.xs[j]=shift==0?s.x[j]:exponential(T(T(logx[j])-T(shift)/g.L));}
    for(size_t j=0;j<g.products.size();++j){auto o=g.products[j];s.products[j+1]=s.products[o.first]*s.xs[o.second];}
    for(size_t j=0;j<g.segments.size();++j){auto a=g.segments[j];T v=s.sums[a.parent];
        for(int k=a.begin;k<a.end;++k)v+=s.products[g.addends[k]];s.sums[j+1]=v;}
    for(size_t j=0;j<g.numerators.size();++j){T n=0,ab=0;
        for(auto [i,c]:g.numerators[j]){T p=T(c)*s.x[i];n+=p;if constexpr(NeedError)ab+=absolute(p);}
        s.numerator[j]=n;if constexpr(NeedError)s.abs_numerator[j]=ab;}
    T val=0,err=0;
    for(const auto&t:g.terms){const T&U=s.sums[t.denominator];
        val+=s.numerator[t.numerator]/U;if constexpr(NeedError)err+=s.abs_numerator[t.numerator]/U;}
    return {val/S,NeedError?err/S:T(0)};
}

// ---- variant under test: R4a plus software prefetches (the products' mpf structs PF2 addends ahead, their limbs
// PF addends ahead, along the flattened addend order of the segment loop; the parent product of the products loop).
constexpr int PF=3;
inline void prefetch_limbs(const MP&v){const mp_limb_t*d=v.backend().data()[0]._mp_d;__builtin_prefetch(d);__builtin_prefetch(d+8);__builtin_prefetch(d+16);}
template<bool NeedError>
std::pair<MP,MP> prefetch_shared(const Graph&g,const ld*logx,ld shift) {
    static thread_local GmpScratch scratch;
    auto&s=scratch;s.resize(g);mpf_ptr S=mpf_of(s.S);mpf_set_si(S,0);s.products[0]=1;s.sums[0]=0;
    for(int j=0;j<g.E;++j){s.x[j]=exponential(MP(logx[j]));mpf_add(S,S,mpf_of(s.x[j]));
        if(shift!=0)s.xs[j]=exponential(MP(MP(logx[j])-MP(shift)/g.L));}
    const MP*xs=shift==0?s.x.data():s.xs.data();
    const size_t NP=g.products.size();
    for(size_t j=0;j<NP;++j){auto o=g.products[j];
        if(j+PF<NP)prefetch_limbs(s.products[g.products[j+PF].first]);
        mpf_mul(mpf_of(s.products[j+1]),mpf_of(s.products[o.first]),mpf_of(xs[o.second]));}
    const int N=int(g.addends.size());const int*ad=g.addends.data();
    for(int k=0;k<std::min(N,2*PF);++k)__builtin_prefetch(&s.products[ad[k]]);
    for(int k=0;k<std::min(N,PF);++k)prefetch_limbs(s.products[ad[k]]);
    for(size_t j=0;j<g.segments.size();++j){auto a=g.segments[j];mpf_ptr v=mpf_of(s.sums[j+1]);
        if(a.begin==a.end){mpf_set(v,mpf_of(s.sums[a.parent]));continue;}
        for(int k=a.begin;k<a.end;++k){
            if(k+2*PF<N)__builtin_prefetch(&s.products[ad[k+2*PF]]);
            if(k+PF<N)prefetch_limbs(s.products[ad[k+PF]]);
            mpf_add(v,k==a.begin?mpf_of(s.sums[a.parent]):v,mpf_of(s.products[ad[k]]));}}
    mpf_ptr c=mpf_of(s.c),p=mpf_of(s.p),ap=mpf_of(s.a);
    for(size_t j=0;j<g.numerators.size();++j){mpf_ptr n=mpf_of(s.numerator[j]),ab=mpf_of(s.abs_numerator[j]);
        mpf_set_si(n,0);mpf_set_si(ab,0);
        for(auto [i,cv]:g.numerators[j]){mpf_set_si(c,cv);mpf_mul(p,c,mpf_of(s.x[i]));mpf_add(n,n,p);
            if constexpr(NeedError){mpf_set(ap,p);if(mpf_cmp_si(ap,0)<0)mpf_neg(ap,ap);mpf_add(ab,ab,ap);}}}
    mpf_ptr val=mpf_of(s.val),err=mpf_of(s.err),q=mpf_of(s.q);
    mpf_set_si(val,0);mpf_set_si(err,0);
    for(const auto&t:g.terms){mpf_srcptr U=mpf_of(s.sums[t.denominator]);
        mp_divisor_check(U);mpf_div(q,mpf_of(s.numerator[t.numerator]),U);mpf_add(val,val,q);
        if constexpr(NeedError){mp_divisor_check(U);mpf_div(q,mpf_of(s.abs_numerator[t.numerator]),U);mpf_add(err,err,q);}}
    std::pair<MP,MP> out;
    if constexpr(NeedError){mp_divisor_check(S);mpf_div(mpf_of(out.second),err,S);}else mpf_set_si(mpf_of(out.second),0);
    mp_divisor_check(S);mpf_div(mpf_of(out.first),val,S);
    return out;
}

using Point=std::array<ld,EMAX>;
static void log_coordinates(const Graph&g,const ld*uu,Point&lx){  // sample(), layout 0
    std::array<int,EMAX> order{};std::array<ld,EMAX> lt{};int E=g.E,S=(1<<E)-1;
    for(int pos=0;pos<E;++pos){ld u=uu[2*pos]*g.choice_total[S];int pick=-1;
        for(int j=0;j<E;++j)if(S>>j&1){u-=g.dp[S^(1<<j)];if(u<=0){pick=j;break;}}
        if(pick<0)pick=31-__builtin_clz(S);
        order[pos]=pick;S^=1<<pick;if(S)lt[pos]=logl(uu[2*pos+1])/g.alpha[S];}
    ld cur=0;for(int j=0;j<E;++j){lx[order[j]]=cur;if(j<E-1)cur+=lt[j];}
}
static ld shift_of(const Graph&g,const Point&lx){  // evaluate()'s shift
    bool direct=true;for(int j=0;j<g.E;++j)if(lx[j]<-600||lx[j]>0)direct=false;
    if(direct)return 0;
    ld shift=-std::numeric_limits<ld>::infinity();
    for(auto mask:g.masks){ld v=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;v+=lx[j];}shift=std::max(shift,v);}
    return shift;
}
static bool same(const MP&a,const MP&b){
    const __mpf_struct&x=a.backend().data()[0];const __mpf_struct&y=b.backend().data()[0];
    if(x._mp_prec!=y._mp_prec||x._mp_size!=y._mp_size||x._mp_exp!=y._mp_exp)return false;
    int n=x._mp_size<0?-x._mp_size:x._mp_size;
    for(int i=0;i<n;++i)if(x._mp_d[i]!=y._mp_d[i])return false;
    return true;
}
struct Result{std::string file;int L=0,E=0;size_t products=0,addends=0,segments=0,terms=0;int points=0,shifted=0,mismatch_r4a=0,mismatch_r4a_err=0,mismatch_prefetch=0;
    double t_ref=0,t_r4a=0,t_pf=0;};

int main(int argc,char**argv){try{
    if(argc<8){std::cerr<<"r4a_mpdiff OUT.json NPOINTS EXTREME REPEATS SEED RATE GRAPH_FILE...\n";return 1;}
    std::string out=argv[1];int npoints=std::stoi(argv[2]),extreme=std::stoi(argv[3]),repeats=std::stoi(argv[4]);
    uint64_t seed=std::stoull(argv[5]);ld rate=std::stold(argv[6]);std::vector<std::string> files(argv+7,argv+argc);
    std::vector<Result> res(files.size());
    #pragma omp parallel for schedule(dynamic,1)
    for(size_t f=0;f<files.size();++f){
        Result&r=res[f];r.file=files[f];Graph g=load_graph(files[f],rate);
        r.L=g.L;r.E=g.E;r.products=g.products.size();r.addends=g.addends.size();r.segments=g.segments.size();r.terms=g.terms.size();
        std::mt19937_64 rng(seed+0x9e3779b97f4a7c15ULL*(g.id+1));std::uniform_real_distribution<double> U01(0x1p-60,1.0);
        std::vector<Point> lx(npoints);std::vector<ld> sh(npoints);
        for(int i=0;i<npoints;++i){std::array<ld,DIMMAX> uu{};for(int d=0;d<2*g.E-1;++d)uu[d]=U01(rng);  // layout 0 reads u[0..2E-2]
            if(extreme>0&&i%extreme==extreme-1)for(int d=1;d<2*g.E-1;d+=2)uu[d]=powl(uu[d],100);
            log_coordinates(g,uu.data(),lx[i]);sh[i]=shift_of(g,lx[i]);r.shifted+=sh[i]!=0;}
        r.points=npoints;
        for(int i=0;i<npoints;++i){
            auto a=reference_shared<MP,false>(g,lx[i].data(),sh[i]);auto b=calculate_shared<MP,false>(g,lx[i].data(),sh[i]);
            auto c=prefetch_shared<false>(g,lx[i].data(),sh[i]);
            r.mismatch_r4a+=!same(a.first,b.first)||!same(a.second,b.second);r.mismatch_prefetch+=!same(a.first,c.first)||!same(a.second,c.second);
            auto ae=reference_shared<MP,true>(g,lx[i].data(),sh[i]);auto be=calculate_shared<MP,true>(g,lx[i].data(),sh[i]);
            r.mismatch_r4a_err+=!same(ae.first,be.first)||!same(ae.second,be.second);}
        using clk=std::chrono::steady_clock;
        for(int rep=0;rep<repeats;++rep)for(int v0=0;v0<3;++v0){int v=(v0+rep)%3;auto t0=clk::now();
            for(int i=0;i<npoints;++i){
                if(v==0){auto m=reference_shared<MP,false>(g,lx[i].data(),sh[i]);}
                else if(v==1){auto m=calculate_shared<MP,false>(g,lx[i].data(),sh[i]);}
                else {auto m=prefetch_shared<false>(g,lx[i].data(),sh[i]);}}
            double dt=std::chrono::duration<double>(clk::now()-t0).count();(v==0?r.t_ref:v==1?r.t_r4a:r.t_pf)+=dt;}
    }
    FILE*o=fopen(out.c_str(),"w");if(!o)throw std::runtime_error("cannot open "+out);
    double tr=0,ta=0,tp=0;long pts=0,shifted=0,mm=0,mme=0,mmp=0;
    fprintf(o,"{\"schema\":\"c8-d2-r4a-mpdiff-1\",\"npoints\":%d,\"extreme_every\":%d,\"repeats\":%d,\"seed\":%llu,\"threads\":%d,\"prefetch_distance\":%d,\"graphs\":[",
            npoints,extreme,repeats,(unsigned long long)seed,omp_get_max_threads(),PF);
    for(size_t f=0;f<res.size();++f){auto&r=res[f];tr+=r.t_ref;ta+=r.t_r4a;tp+=r.t_pf;pts+=r.points;shifted+=r.shifted;mm+=r.mismatch_r4a;mme+=r.mismatch_r4a_err;mmp+=r.mismatch_prefetch;
        fprintf(o,"%s{\"file\":\"%s\",\"L\":%d,\"products\":%zu,\"addends\":%zu,\"segments\":%zu,\"terms\":%zu,\"points\":%d,\"shifted\":%d,\"mismatch_r4a\":%d,\"mismatch_r4a_need_error\":%d,\"mismatch_prefetch\":%d,\"seconds_reference\":%.6f,\"seconds_r4a\":%.6f,\"seconds_prefetch\":%.6f}",
                f?",":"",r.file.c_str(),r.L,r.products,r.addends,r.segments,r.terms,r.points,r.shifted,r.mismatch_r4a,r.mismatch_r4a_err,r.mismatch_prefetch,r.t_ref,r.t_r4a,r.t_pf);}
    fprintf(o,"],\"totals\":{\"points\":%ld,\"shifted\":%ld,\"mismatch_r4a\":%ld,\"mismatch_r4a_need_error\":%ld,\"mismatch_prefetch\":%ld,\"seconds_reference\":%.6f,\"seconds_r4a\":%.6f,\"seconds_prefetch\":%.6f,\"speedup_r4a\":%.5f,\"speedup_prefetch\":%.5f}}\n",
            pts,shifted,mm,mme,mmp,tr,ta,tp,tr/ta,tr/tp);
    fclose(o);
    std::cout<<"points "<<pts<<" shifted "<<shifted<<" mismatches r4a "<<mm<<" r4a(NeedError) "<<mme<<" prefetch "<<mmp<<"; speedup r4a "<<tr/ta<<" prefetch "<<tr/tp<<"\n";
    return (mm||mme||mmp)?3:0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
