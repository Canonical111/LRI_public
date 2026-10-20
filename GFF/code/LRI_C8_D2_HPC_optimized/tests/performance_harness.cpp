// Deterministic branch fixtures for exact comparison of native kernel candidates.
// This complements kernel_points.cpp's independent 450-digit accuracy checks.
// It is a correctness replay, not a physical estimate or a throughput benchmark.
#ifndef C8_KERNEL_HEADER
#define C8_KERNEL_HEADER "../src/kernel.hpp"
#endif
#include C8_KERNEL_HEADER
#include <cfenv>
#include <iostream>
#include <sstream>

Graph algebra_fixture(int L,bool cancellation=false){
    Graph g;g.L=L;g.E=2*L;g.id=-L;
    unsigned half=(1u<<L)-1;g.masks={half,half<<L};
    Term a;a.ids={0,1};a.co.assign(g.E,1);
    if(cancellation){a.co.assign(g.E,0);a.co[0]=1;Term b;b.ids={0};b.co=a.co;b.co[0]=-1;g.terms={a,b};}
    else g.terms={a};
    g.alpha.assign(1u<<g.E,1);g.alpha.front()=g.alpha.back()=0;rates(g,.8L);prepare(g);return g;
}
std::string quad_string(Q x){char out[256];quadmath_snprintf(out,sizeof(out),"%.36Qg",x);return out;}
void vector_json(const std::array<ld,7>&v,int K){std::cout<<'[';for(int j=0;j<=K;++j){if(j)std::cout<<',';std::cout<<'"'<<v[j]<<'"';}std::cout<<']';}
void point_json(const Graph&g,const std::array<ld,16>&lx,int which,bool&comma){
    Scratch s;s.resize(g);auto result=evaluate(g,lx.data(),0,s);
    ld shift=-std::numeric_limits<ld>::infinity();
    for(auto mask:g.masks){ld v=0;for(int j=0;j<g.E;++j)if(mask>>j&1)v+=lx[j];shift=std::max(shift,v);}
    auto q=calculate_shared<Q>(g,lx.data(),shift);auto reference=calculate_reference<Q>(g,lx.data(),shift);
    if(q.first!=reference.first||q.second!=reference.second)throw std::runtime_error("shared Q value or error changed arithmetic order");
    auto mp=calculate_shared<MP,false>(g,lx.data(),shift);
    if(comma)std::cout<<',';comma=true;
    std::cout<<"{\"kind\":\"direct\",\"L\":"<<g.L<<",\"graph\":"<<g.id<<",\"case\":"<<which
        <<",\"level\":"<<result.level<<",\"y\":\""<<result.y<<"\",\"sum_x\":\""<<s.S
        <<"\",\"quad_value\":\""<<quad_string(q.first)<<"\",\"quad_error\":\""<<quad_string(q.second)
        <<"\",\"mp_value\":\""<<mp.first.str(380,std::ios_base::scientific)<<"\"}";
}
int main(int argc,char**argv){try{
#ifdef C8_BENCH_DIRECT_PROFILE
    bench_profile::install();
#endif
    if(argc>3)throw std::runtime_error("usage: performance_harness [graph_list|-] [nearest|downward|upward|towardzero]");
    std::string rounding=argc==3?argv[2]:"nearest";int mode=FE_TONEAREST;
    if(rounding=="downward")mode=FE_DOWNWARD;else if(rounding=="upward")mode=FE_UPWARD;
    else if(rounding=="towardzero")mode=FE_TOWARDZERO;else if(rounding!="nearest")throw std::runtime_error("bad rounding mode");
    if(std::fesetround(mode))throw std::runtime_error("cannot select rounding mode");
    std::cout<<std::setprecision(std::numeric_limits<ld>::max_digits10)
             <<"{\"schema\":\"c8-direct-performance-regression-1\",\"backend\":\""<<mp_backend<<"\",\"rounding\":\""<<rounding<<"\",\"rows\":[";
    bool comma=false;
    for(int L:{2,3,7,8}){
        auto g=algebra_fixture(L);Scratch s;s.resize(g);std::array<ld,32>u{};std::array<ld,7>logs{};
        for(int j=0;j<32;++j)u[j]=ld(3+(11*j)%29)/32;
        for(int j=1;j<=6;++j)logs[j]=ld(j-3)/(j*17);
        for(int layout=0;layout<3;++layout){int level=-1;auto v=sample(g,u.data(),8-L,logs,level,layout,s);
            if(comma)std::cout<<',';comma=true;
            std::cout<<"{\"kind\":\"sample\",\"L\":"<<L<<",\"layout\":"<<layout<<",\"level\":"<<level<<",\"values\":";
            vector_json(v,8-L);std::cout<<'}';}
    }
    auto cancelled=algebra_fixture(8,true);std::array<ld,16>lx{};
    for(int j=8;j<16;++j)lx[j]=-50; // finite cancellation requires >113 significant bits
    Scratch cs;cs.resize(cancelled);auto cancellation=evaluate(cancelled,lx.data(),0,cs);
    if(cancellation.level!=2||cancellation.y==0)throw std::runtime_error("required severe-cancellation MP branch was not exercised");
    point_json(cancelled,lx,99,comma);
    auto ordinary=algebra_fixture(8);lx.fill(0);lx[0]=-820; // nonmoderate LD reference path
    point_json(ordinary,lx,98,comma);
    lx.fill(-620); // nonzero common rescaling; still moderate after shifting
    point_json(ordinary,lx,97,comma);
    if(argc>=2&&std::string(argv[1])!="-"){std::ifstream f(argv[1]);if(!f)throw std::runtime_error("cannot open graph list");std::string path;
        while(f>>path){auto g=load_graph(path,.8L);
            for(int k=0;k<4;++k){lx.fill(0);for(int j=0;j<g.E;++j)lx[j]=logl(ld(3+(j*11+g.id)%29)/32)-(j<g.L?k*270.L:0);
                point_json(g,lx,k,comma);}}
    }
    std::cout<<"]}\n";
#ifdef C8_BENCH_DIRECT_PROFILE
    bench_profile::write();
#endif
    return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
