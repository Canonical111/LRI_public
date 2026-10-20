// 450-digit independent point checks of the binary128 and MP tiers (kernel.hpp, both backends; C8: L2-L8, lx sized
// by EMAX). Prints one JSON line; exits 2 on the first failure.
#include "../src/kernel.hpp"
#include <iostream>
using Ref=boost::multiprecision::number<boost::multiprecision::cpp_dec_float<450>>;
std::pair<Ref,Ref> independent(const Graph&g,const ld*lx,ld shift){
    std::vector<Ref>x(g.E),mons(g.masks.size());Ref S=0;
    for(int j=0;j<g.E;++j){x[j]=exp(Ref(lx[j]));S+=x[j];}
    for(size_t k=0;k<g.masks.size();++k){Ref z=-Ref(shift);unsigned m=g.masks[k];while(m){int j=__builtin_ctz(m);m&=m-1;z+=Ref(lx[j]);}mons[k]=exp(z);}
    Ref v=0,err=0;for(const auto&t:g.terms){Ref U=0,n=0,a=0;for(int i:t.ids)U+=mons[i];for(int j=0;j<g.E;++j){Ref z=Ref(t.co[j])*x[j];n+=z;a+=abs(z);}v+=n/U;err+=a/U;}return{v/S,err/S};
}
int main(int argc,char**argv){try{
    std::ifstream list(argv[1]);std::string path;int n=0;ld maxerr=0;Scratch s;
    while(list>>path){auto g=load_graph(path,.8L);s.resize(g);for(int sample=0;sample<4;++sample){
        ld lx[EMAX],shift=0;for(int j=0;j<g.E;++j)lx[j]=logl((3+(j*11+g.id)%29)/32.L)-(sample&&j<g.L?sample*180.L:0);
        shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld a=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;a+=lx[j];}shift=std::max(shift,a);}
        auto q=calculate_shared<Q>(g,lx,shift);auto m=calculate_shared<MP,false>(g,lx,shift);auto ref=independent(g,lx,shift);
        Ref mr(m.first.str(430,std::ios_base::scientific));Ref error=abs(Ref(mr-ref.first))/(1+ref.second);
        if(error>Ref("1e-280"))throw std::runtime_error("MP point check failed");
        auto oldq=calculate_reference<Q>(g,lx,shift);if(q.first!=oldq.first||q.second!=oldq.second)throw std::runtime_error("Quad sharing changed arithmetic");
        maxerr=std::max(maxerr,error.convert_to<ld>());++n;
    }}
    std::cout<<"{\"status\":\"passed\",\"checks\":"<<n<<",\"backend\":\""<<mp_backend<<"\",\"max_error_scaled_by_absolute_terms\":\""<<std::setprecision(21)<<maxerr<<"\",\"reference_digits\":450}\n";
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
