#include "../src/kernel.hpp"
#include <iostream>
#include <map>
// Point checks of the three precision tiers against an independent 450-digit evaluation (cpp_dec_float<450>):
//  * MP tier (calculate_shared<MP,false>): error scaled by the absolute terms <= 1e-280;
//  * binary128 sharing: bitwise equal to the reference formula (calculate_reference<Q>);
//  * long-double tier, as evaluate() computes it (calculate_products if moderate, else calculate_reference<ld>), at
//    every point the tier ACCEPTS (|v| >= 1e-9 sum|terms|): relative error <= 1e-9 and error scaled by the absolute
//    terms <= 1e-14 (long double eps 5.4e-20 times the operation count).
// C8(3) (PLAN.md A-RPL-5, A-KER-7; Stage 3a): the array size comes from EMAX (C.1), the maxima are also reported per
// loop (the measured column of docs/NUMERICS.md's accuracy contract), and
//  * --contract: a long-double or MP breach is counted and reported instead of failing the run. Only for L8 lists
//    (Stage 3b): there the accepted error can reach A_max 2^-64/1e-9 ~ 6e-6 by design, and a breach is a
//    precision-contract finding (A-RPL-5's disposition: any A-RPL-5 bound at L8). Each breach is one JSON line on
//    stderr ({"breach":"ld"|"mp", "graph": path, "L", "sample", the scaled and relative errors, ...}); the binary128
//    sharing check (bitwise equal to calculate_reference<Q>) is an arithmetic identity and stays hard. At L <= 7 the
//    gates stay C7(3)'s exact, hard gates (the default).
//  * --deep FILE: the deep-cancellation fixture of A-KER-7 (tests/fixtures/deep_cancellation/L3/G0.txt): two terms
//    over the same three monomials with opposite numerators, summed in opposite orders, so the forest sum is zero in
//    exact arithmetic and the floating sums cancel to their rounding level at every point. At the four sample points:
//    the 450-digit value is below 1e-330 of its sum|terms|; the long-double and binary128 tests both fail (the point
//    reaches the MP tier); the MP value with its error estimate (calculate_shared<MP,true>) equals the unchecked one
//    bit for bit; the MP tier's log10(|v|/err) (kernel.hpp mp_check_record) is below -320 for the gmp350 backend (the
//    mp_alarm level; decimal300 has fewer digits and is only recorded); and the MP value is within 1e-280 of the
//    450-digit one, scaled by 1 + sum|terms|.
using Ref=boost::multiprecision::number<boost::multiprecision::cpp_dec_float<450>>;
std::pair<Ref,Ref> independent(const Graph&g,const ld*lx,ld shift){
    std::vector<Ref>x(g.E),mons(g.masks.size());Ref S=0;
    for(int j=0;j<g.E;++j){x[j]=exp(Ref(lx[j]));S+=x[j];}
    for(size_t k=0;k<g.masks.size();++k){Ref z=-Ref(shift);unsigned m=g.masks[k];while(m){int j=__builtin_ctz(m);m&=m-1;z+=Ref(lx[j]);}mons[k]=exp(z);}
    Ref v=0,err=0;for(const auto&t:g.terms){Ref U=0,n=0,a=0;for(int i:t.ids)U+=mons[i];for(int j=0;j<g.E;++j){Ref z=Ref(t.co[j])*x[j];n+=z;a+=abs(z);}Ref den=U*sqrt(U);v+=n/den;err+=a/den;}return{v/S,err/S};
}
// The four sample points of every check: a direct point, then three with the first L log-coordinates lowered by
// 180, 360 and 540 (shifted, and non-moderate for the larger drops).
static void sample_point(const Graph&g,int sample,ld*lx,ld&shift){
    for(int j=0;j<g.E;++j)lx[j]=logl((3+(j*11+g.id)%29)/32.L)-(sample&&j<g.L?sample*180.L:0);
    shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld a=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;a+=lx[j];}shift=std::max(shift,a);}
}
static std::string str(const Ref&x){std::ostringstream o;o<<std::setprecision(6)<<std::scientific<<x;return o.str();}
static int deep(const char*path){
    auto g=load_graph(path,.8L);Scratch s;s.resize(g);std::cout<<"{\"status\":\"passed\",\"fixture\":\""<<path<<"\",\"backend\":\""<<mp_backend<<"\",\"points\":[";
    for(int sample=0;sample<4;++sample){
        ld lx[EMAX],shift=0;sample_point(g,sample,lx,shift);
        bool moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
        auto v=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);ld rld=absolute(v.first)/(v.second+1e-4900L);
        auto q=calculate_shared<Q>(g,lx,shift);bool qfail=absolute(q.first)<Q(1e-23L)*q.second;
        auto m0=calculate_shared<MP,false>(g,lx,shift);auto m1=calculate_shared<MP,true>(g,lx,shift);
        Scratch c;mp_check_record(c,m1);
        auto ref=independent(g,lx,shift);Ref r450=abs(ref.first)/ref.second;
        Ref mr(m1.first.str(430,std::ios_base::scientific));Ref error=abs(Ref(mr-ref.first))/(1+ref.second);
        if(!(rld<1e-9L))throw std::runtime_error("deep fixture: the long-double test passes at sample "+std::to_string(sample));
        if(!qfail)throw std::runtime_error("deep fixture: the binary128 test passes at sample "+std::to_string(sample));
        if(!(m0.first==m1.first))throw std::runtime_error("deep fixture: calculate_shared<MP,true> changed the MP value");
        if(!(r450<Ref("1e-330")))throw std::runtime_error("deep fixture: the 450-digit sum does not cancel below 1e-330 of sum|terms| (|v|/err = "+str(r450)+")");
        if(error>Ref("1e-280"))throw std::runtime_error("deep fixture: MP value differs from the 450-digit value");
        const bool gmp=std::string(mp_backend)=="gmp350";
        if(gmp&&!(c.mp_log10< -320))throw std::runtime_error("deep fixture: the MP self-check does not raise the alarm (log10 "+std::to_string(double(c.mp_log10))+")");
        std::cout<<(sample?",":"")<<"{\"sample\":"<<sample<<",\"moderate\":"<<(moderate?"true":"false")<<",\"ld_ratio\":\""<<std::setprecision(6)<<rld
                 <<"\",\"quad_test_fails\":true,\"mp_log10_ratio\":\""<<c.mp_log10<<"\",\"mp_alarm\":"<<(c.mp_log10< -320?"true":"false")
                 <<",\"ref450_ratio\":\""<<str(r450)<<"\",\"mp_error_scaled\":\""<<str(error)<<"\",\"mp_true_equals_false\":true}";
    }
    std::cout<<"],\"gates\":\"ld and binary128 tests fail; |v450|/err450 < 1e-330; MP <true> == <false>; MP vs 450 digits <= 1e-280; gmp350: log10(|v|/err) < -320\"}\n";
    return 0;
}
int main(int argc,char**argv){try{
    // --describe: the identity make's build record needs (the sanitizer builds of `make sanitize`); never a worker.
    if(argc==2&&std::string(argv[1])=="--describe"){std::cout<<"{\"schema\":\"c8-d3-point-checks-1\",\"dimension\":3,\"emax\":"<<EMAX<<",\"mp_backend\":\""<<mp_backend
        <<"\",\"diagnostic\":true,\"diagnostic_kind\":\"point_checks\",\"compiler\":\""<<__VERSION__<<"\",\"long_double_bits\":"<<std::numeric_limits<ld>::digits<<"}\n";return 0;}
    if(argc==3&&std::string(argv[1])=="--deep")return deep(argv[2]);
    bool contract=false;int a=1;if(argc==3&&std::string(argv[1])=="--contract"){contract=true;a=2;}
    if(argc!=a+1){std::cerr<<"usage: point_checks [--contract] LIST | point_checks --deep FIXTURE\n";return 1;}
    std::ifstream list(argv[a]);if(!list)throw std::runtime_error(std::string(argv[a])+": cannot open the list");
    std::string path;int n=0,nld=0,nld_rel=0,nmoderate=0,breaches=0,mp_breaches=0,ld_breaches=0;ld maxerr=0,ldscaled=0,ldrel=0;Scratch s;
    struct Loop{int checks=0,ld_accepted=0,breaches=0,mp_breaches=0;ld mp=0,ldsc=0,ldrel=0;};std::map<int,Loop>loops;
    while(list>>path){auto g=load_graph(path,.8L);s.resize(g);auto&lp=loops[g.L];for(int sample=0;sample<4;++sample){
        ld lx[EMAX],shift=0;sample_point(g,sample,lx,shift);
        auto q=calculate_shared<Q>(g,lx,shift);auto m=calculate_shared<MP,false>(g,lx,shift);auto ref=independent(g,lx,shift);
        Ref mr(m.first.str(430,std::ios_base::scientific));Ref error=abs(Ref(mr-ref.first))/(1+ref.second);
        if(error>Ref("1e-280")){
            if(!contract)throw std::runtime_error("MP point check failed: "+path);
            // contract mode (L8): an MP breach is a precision-contract finding too (A-RPL-5's disposition): recorded with its point
            std::cerr<<"{\"breach\":\"mp\",\"graph\":\""<<path<<"\",\"L\":"<<g.L<<",\"sample\":"<<sample<<",\"scaled\":\""<<str(error)<<"\",\"bound\":\"1e-280\"}\n";
            ++breaches;++mp_breaches;lp.mp_breaches++;}
        auto oldq=calculate_reference<Q>(g,lx,shift);if(q.first!=oldq.first||q.second!=oldq.second)throw std::runtime_error("Quad sharing changed arithmetic: "+path);
        maxerr=std::max(maxerr,error.convert_to<ld>());++n;lp.checks++;lp.mp=std::max(lp.mp,error.convert_to<ld>());
        bool moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
        auto v=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);nmoderate+=moderate;
        ld ratio=absolute(v.first)/(v.second+1e-4900L);
        if(ratio>=1e-9L&&std::isfinite(v.first)){
            Ref d=abs(Ref(v.first)-ref.first);ld sc=(d/ref.second).convert_to<ld>(),re=(d/abs(ref.first)).convert_to<ld>();
            if(sc>1e-14L||re>1e-9L){
                if(!contract){std::cerr<<"long-double tier check failed: "<<path<<" sample "<<sample<<" scaled "<<sc<<" relative "<<re<<" ratio "<<ratio<<"\n";
                    throw std::runtime_error("long-double point check failed: "+path);}
                // contract mode (L8): one JSON line per breach on stderr (tests/check_points.py records them)
                std::cerr<<std::setprecision(6)<<"{\"breach\":\"ld\",\"graph\":\""<<path<<"\",\"L\":"<<g.L<<",\"sample\":"<<sample<<",\"moderate\":"<<(moderate?"true":"false")
                         <<",\"scaled\":\""<<sc<<"\",\"relative\":\""<<re<<"\",\"ratio\":\""<<ratio<<"\",\"scaled_bound\":\"1e-14\",\"relative_bound\":\"1e-9\",\"which\":\""
                         <<(sc>1e-14L&&re>1e-9L?"scaled and relative":(sc>1e-14L?"scaled":"relative"))<<"\"}\n";
                ++breaches;lp.breaches++;ld_breaches++;}
            ldscaled=std::max(ldscaled,sc);ldrel=std::max(ldrel,re);++nld;nld_rel+=re>1e-9L;lp.ld_accepted++;lp.ldsc=std::max(lp.ldsc,sc);lp.ldrel=std::max(lp.ldrel,re);}
    }}
    std::cout<<std::setprecision(21)<<"{\"status\":\""<<(breaches?"contract_finding":"passed")<<"\",\"checks\":"<<n<<",\"backend\":\""<<mp_backend<<"\",\"max_error_scaled_by_absolute_terms\":\""<<maxerr<<"\",\"reference_digits\":450"
             <<",\"long_double_tier\":{\"accepted_points\":"<<nld<<",\"moderate_points\":"<<nmoderate<<",\"max_error_scaled_by_absolute_terms\":\""<<ldscaled<<"\",\"max_relative_error\":\""<<ldrel
             <<"\",\"points_above_1e-9_relative\":"<<nld_rel<<",\"breaches\":"<<ld_breaches<<",\"gate\":\"relative <= 1e-9 and scaled <= 1e-14 at every accepted point"<<(contract?" (contract mode: breaches reported)":"")<<"\"},\"per_loop\":{";
    bool first=true;for(auto&kv:loops){if(!first)std::cout<<',';first=false;auto&lp=kv.second;
        std::cout<<"\""<<kv.first<<"\":{\"checks\":"<<lp.checks<<",\"mp_max_scaled\":\""<<lp.mp<<"\",\"ld_accepted\":"<<lp.ld_accepted<<",\"ld_max_scaled\":\""<<lp.ldsc<<"\",\"ld_max_relative\":\""<<lp.ldrel<<"\",\"ld_breaches\":"<<lp.breaches<<",\"mp_breaches\":"<<lp.mp_breaches<<"}";}
    std::cout<<"},\"mp_breaches\":"<<mp_breaches<<",\"contract_mode\":"<<(contract?"true":"false")<<"}\n";
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
