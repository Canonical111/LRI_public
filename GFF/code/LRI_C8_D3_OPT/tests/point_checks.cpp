#include "../src/kernel.hpp"
#include <iostream>
// Point checks of the three precision tiers against an independent 450-digit evaluation (cpp_dec_float<450>):
//  * MP tier (calculate_shared<MP,false>): error scaled by the absolute terms <= 1e-280;
//  * binary128 sharing: bitwise equal to the reference formula (calculate_reference<Q>);
//  * long-double tier, as evaluate() computes it (calculate_products if moderate, else calculate_reference<ld>), at
//    every point the tier ACCEPTS (|v| >= 1e-9 sum|terms|): relative error <= 1e-9 and error scaled by the absolute
//    terms <= 1e-14 (long double eps 5.4e-20 times the operation count).
using Ref=boost::multiprecision::number<boost::multiprecision::cpp_dec_float<450>>;
std::pair<Ref,Ref> independent(const Graph&g,const ld*lx,ld shift){
    std::vector<Ref>x(g.E),mons(g.masks.size());Ref S=0;
    for(int j=0;j<g.E;++j){x[j]=exp(Ref(lx[j]));S+=x[j];}
    for(size_t k=0;k<g.masks.size();++k){Ref z=-Ref(shift);unsigned m=g.masks[k];while(m){int j=__builtin_ctz(m);m&=m-1;z+=Ref(lx[j]);}mons[k]=exp(z);}
    Ref v=0,err=0;for(const auto&t:g.terms){Ref U=0,n=0,a=0;for(int i:t.ids)U+=mons[i];for(int j=0;j<g.E;++j){Ref z=Ref(t.co[j])*x[j];n+=z;a+=abs(z);}Ref den=U*sqrt(U);v+=n/den;err+=a/den;}return{v/S,err/S};
}
int main(int argc,char**argv){try{
    if(argc!=2)throw std::runtime_error("usage: point_checks graph_path_list");
    std::ifstream list(argv[1]);if(!list)throw std::runtime_error("cannot read graph list");std::string path;int n=0,nld=0,nld_rel=0,nmoderate=0;ld maxerr=0,ldscaled=0,ldrel=0;Scratch s;
    while(list>>path){auto g=load_graph(path,.8L);s.resize(g);for(int sample=0;sample<4;++sample){
        ld lx[MaxEdges],shift=0;for(int j=0;j<g.E;++j)lx[j]=logl((3+(j*11+g.id)%29)/32.L)-(sample&&j<g.L?sample*180.L:0);
        shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld a=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;a+=lx[j];}shift=std::max(shift,a);}
        auto q=calculate_shared<Q>(g,lx,shift);auto m=calculate_shared<MP,false>(g,lx,shift);auto ref=independent(g,lx,shift);
        Ref mr(m.first.str(430,std::ios_base::scientific));Ref error=abs(Ref(mr-ref.first))/(1+ref.second);
        if(error>Ref("1e-280"))throw std::runtime_error("MP point check failed");
        auto oldq=calculate_reference<Q>(g,lx,shift);if(q.first!=oldq.first||q.second!=oldq.second)throw std::runtime_error("Quad sharing changed arithmetic");
        maxerr=std::max(maxerr,error.convert_to<ld>());++n;
        bool moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
        auto v=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);nmoderate+=moderate;
        ld ratio=absolute(v.first)/(v.second+1e-4900L);
        if(ratio>=1e-9L&&std::isfinite(v.first)){
            Ref d=abs(Ref(v.first)-ref.first);ld sc=(d/ref.second).convert_to<ld>(),re=(d/abs(ref.first)).convert_to<ld>();
            if(sc>1e-14L||re>1e-9L){std::cerr<<"long-double tier check failed: "<<path<<" sample "<<sample<<" scaled "<<sc<<" relative "<<re<<" ratio "<<ratio<<"\n";throw std::runtime_error("long-double point check failed");}
            ldscaled=std::max(ldscaled,sc);ldrel=std::max(ldrel,re);++nld;nld_rel+=re>1e-9L;}
    }}
    std::cout<<std::setprecision(21)<<"{\"status\":\"passed\",\"checks\":"<<n<<",\"backend\":\""<<mp_backend<<"\",\"max_error_scaled_by_absolute_terms\":\""<<maxerr<<"\",\"reference_digits\":450"
             <<",\"long_double_tier\":{\"accepted_points\":"<<nld<<",\"moderate_points\":"<<nmoderate<<",\"max_error_scaled_by_absolute_terms\":\""<<ldscaled<<"\",\"max_relative_error\":\""<<ldrel
             <<"\",\"points_above_1e-9_relative\":"<<nld_rel<<",\"gate\":\"relative <= 1e-9 and scaled <= 1e-14 at every accepted point\"}}\n";
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
