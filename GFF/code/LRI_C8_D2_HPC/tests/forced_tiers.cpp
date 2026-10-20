// A-RPL-5 precision-policy check per tier (tests/forced_tiers.py drives it). For every graph of LIST (all of loop
// order L) and every point index in [BEGIN, END), the point is generated exactly as the worker generates it (the Sobol
// net of replicate 0, the worker's seed mixing, sample() at layout 0) and then evaluated in EVERY tier: the long-double
// first pass that evaluate() uses (calculate_products, or calculate_reference<ld> for non-moderate points), binary128
// (calculate_shared<Q>), the build's MP backend (calculate_shared<MP,false>), in a gmp build also decimal300 on the
// MP-promoted points, and an independent 450-digit value (cpp_dec_float<450>; see independent()).
// Gates: (a) points accepted in long double: |f - f450| <= 1e-15 err_ld; accepted in binary128: |f_q - f450| <=
// 1e-29 err_q; (b) every MP value: |f_mp - f450|/(1 + err450) <= 1e-280; (c) the tier decisions recomputed from the
// forced values equal evaluate()'s level. Prints one JSON object; exits 2 on unreadable input. Gate violations are
// counted and the first ones listed, never hidden.
//   forced_tiers L LIST NET BEGIN END SEED THREADS
#include "../src/kernel.hpp"
#include <cstdio>
#include <iostream>
#include <random>
#include <sstream>
#include <omp.h>
using Ref=boost::multiprecision::number<boost::multiprecision::cpp_dec_float<450>>;
using Dec300=boost::multiprecision::number<boost::multiprecision::cpp_dec_float<300>>;
struct Net {
    int dim,bits;const std::vector<uint64_t>&direction;std::vector<uint64_t>state;
    Net(int d,int b,const std::vector<uint64_t>&v,uint64_t seed,uint64_t begin):dim(d),bits(b),direction(v),state(d){
        std::mt19937_64 rng(seed);for(auto&s:state)s=rng()>>(64-bits);
        uint64_t gray=begin^(begin>>1);while(gray){int k=__builtin_ctzll(gray);gray&=gray-1;for(int j=0;j<dim;++j)state[j]^=direction[j*bits+k];}}
    void point(ld*u)const {for(int j=0;j<dim;++j)u[j]=(ld(state[j])+.5L)/ld(uint64_t(1)<<bits);}
};
// The 450-digit value: x_j = exp(lx_j), xs_j = exp(lx_j - shift/L), every monomial the direct product of its mask's
// xs_j (lowest index first; no shared prefix products), every term's denominator and numerator summed directly (no
// shared sums). A 450-digit exponential costs about 230 multiplications, so per-mask exponentials (tests/
// point_checks.cpp's choice) would dominate at L8 (up to 4,032 masks per point).
static std::pair<Ref,Ref> independent(const Graph&g,const ld*lx,ld shift){
    std::vector<Ref>x(g.E),xs(g.E),mons(g.masks.size());Ref S=0;const Ref sh=Ref(shift)/g.L;
    for(int j=0;j<g.E;++j){x[j]=exp(Ref(lx[j]));S+=x[j];xs[j]=shift==0?x[j]:exp(Ref(lx[j])-sh);}
    for(size_t k=0;k<g.masks.size();++k){Ref z=1;unsigned m=g.masks[k];while(m){int j=__builtin_ctz(m);m&=m-1;z*=xs[j];}mons[k]=z;}
    Ref v=0,err=0;for(const auto&t:g.terms){Ref U=0,n=0,a=0;for(int i:t.ids)U+=mons[i];for(int j=0;j<g.E;++j){Ref z=Ref(t.co[j])*x[j];n+=z;a+=abs(z);}v+=n/U;err+=a/U;}return{v/S,err/S};
}
static Ref ref_of(Q q){char buf[96];quadmath_snprintf(buf,sizeof buf,"%.45Qe",q);return Ref(buf);}
template<class M> static Ref ref_of_mp(const M&m){return Ref(m.str(440,std::ios_base::scientific));}
// floor(log10(x)) bins for the reported distributions: bin b counts x in [10^-b, 10^(1-b)); 0 and anything below
// 1e-500 in the last bin.
constexpr int BINS=502;
static int bin_of(const Ref&x){if(!(x>0))return BINS-1;Ref e=-floor(log10(x));if(e<0)return 0;if(e>BINS-2)return BINS-1;return e.convert_to<int>();}
struct Stats {
    unsigned long long points=0,level[3]{},decision_mismatch=0,ld_viol=0,q_viol=0,mp_viol=0,dec_viol=0,nonmoderate=0,nondirect=0;
    Ref ld_max=0,q_max=0,mp_max=0,mp_max_promoted=0,dec_max=0,ld_rel_max=0,q_rel_max=0;
    unsigned long long h_ld[BINS]{},h_q[BINS]{},h_mp[BINS]{},h_ld_all[BINS]{},h_q_all[BINS]{};
    std::vector<std::string> first;
    void add(const Stats&o){points+=o.points;for(int k=0;k<3;++k)level[k]+=o.level[k];decision_mismatch+=o.decision_mismatch;ld_viol+=o.ld_viol;q_viol+=o.q_viol;mp_viol+=o.mp_viol;dec_viol+=o.dec_viol;
        nonmoderate+=o.nonmoderate;nondirect+=o.nondirect;
        if(o.ld_max>ld_max)ld_max=o.ld_max;if(o.q_max>q_max)q_max=o.q_max;if(o.mp_max>mp_max)mp_max=o.mp_max;if(o.mp_max_promoted>mp_max_promoted)mp_max_promoted=o.mp_max_promoted;if(o.dec_max>dec_max)dec_max=o.dec_max;
        if(o.ld_rel_max>ld_rel_max)ld_rel_max=o.ld_rel_max;if(o.q_rel_max>q_rel_max)q_rel_max=o.q_rel_max;
        for(int b=0;b<BINS;++b){h_ld[b]+=o.h_ld[b];h_q[b]+=o.h_q[b];h_mp[b]+=o.h_mp[b];h_ld_all[b]+=o.h_ld_all[b];h_q_all[b]+=o.h_q_all[b];}
        for(auto&s:o.first)if(first.size()<20)first.push_back(s);}
};
static void hist(std::ostream&f,const char*name,const unsigned long long*h){
    f<<",\""<<name<<"\":{";bool first=true;for(int b=0;b<BINS;++b)if(h[b]){if(!first)f<<',';first=false;f<<'"'<<(b==BINS-1?std::string("zero_or_below"):std::to_string(-b))<<"\":"<<h[b];}f<<'}';}
int main(int argc,char**argv){try{
    if(argc!=8){std::cerr<<"forced_tiers L LIST NET BEGIN END SEED THREADS\n";return 1;}
    int L=std::stoi(argv[1]);uint64_t begin=std::stoull(argv[4]),end=std::stoull(argv[5]),seed=std::stoull(argv[6]);int threads=std::stoi(argv[7]);
    if(L<2||L>LMAX||begin>=end||threads<1)throw std::runtime_error("bad arguments");
    std::vector<Graph>graphs;{std::ifstream list(argv[2]);std::string path;while(list>>path){graphs.push_back(load_graph(path,.8L));if(graphs.back().L!=L)throw std::runtime_error("graph of another L: "+path);}}
    std::ifstream netf(argv[3],std::ios::binary);uint32_t head[3]={0,0,0};netf.read(reinterpret_cast<char*>(head),sizeof head);
    int dim=head[1],bits=head[2];if(!netf||head[0]<1||dim!=4*L-1||bits<32||bits>60||end>(uint64_t(1)<<bits))throw std::runtime_error("bad net");
    std::vector<uint64_t>dir(size_t(dim)*bits);netf.read(reinterpret_cast<char*>(dir.data()),dir.size()*8);if(!netf)throw std::runtime_error("truncated net");
    const uint64_t n=end-begin;const uint64_t total=uint64_t(graphs.size())*n;
    Stats all;std::string error;
    #pragma omp parallel num_threads(threads)
    {
        Stats st;Scratch s;
        #pragma omp for schedule(dynamic,1)
        for(uint64_t w=0;w<total;++w){try{
            const Graph&g=graphs[w/n];uint64_t i=begin+w%n;s.resize(g);
            Net net(dim,bits,dir,seed+0x9e3779b97f4a7c15ULL*1+0xbf58476d1ce4e5b9ULL*(g.id+1),i);std::array<ld,DIMMAX>u{};net.point(u.data());
            std::array<ld,NLOGS>logs{};int level=0;sample(g,u.data(),0,logs,level,0,s);
            std::array<ld,EMAX>lx{};for(int j=0;j<g.E;++j)lx[j]=s.lx[j];
            // evaluate()'s shift and moderate rule, then every tier
            ld shift=0;bool direct=true;for(int j=0;j<g.E;++j)if(lx[j]<-600||lx[j]>0)direct=false;
            if(!direct){shift=-std::numeric_limits<ld>::infinity();for(auto mask:g.masks){ld v=0;while(mask){int j=__builtin_ctz(mask);mask&=mask-1;v+=lx[j];}shift=std::max(shift,v);}}
            bool moderate=true;for(int j=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;
            auto v=moderate?calculate_products(g,lx.data(),shift,s):calculate_reference<ld>(g,lx.data(),shift);
            auto q=calculate_shared<Q>(g,lx.data(),shift);auto m=calculate_shared<MP,false>(g,lx.data(),shift);auto r=independent(g,lx.data(),shift);
            ld ratio=absolute(v.first)/(v.second+1e-4900L);int decided=ratio<1e-9L?(absolute(q.first)<Q(1e-23L)*q.second?2:1):0;
            st.points++;st.level[level]++;st.nonmoderate+=!moderate;st.nondirect+=!direct;
            auto note=[&](const std::string&what){if(st.first.size()<20){std::ostringstream o;o<<"graph "<<g.id<<" point "<<i<<": "<<what;st.first.push_back(o.str());}};
            if(decided!=level){st.decision_mismatch++;note("decision "+std::to_string(decided)+" != evaluate() level "+std::to_string(level));}
            Ref eld=abs(Ref(v.first)-r.first),eq=abs(ref_of(q.first)-r.first);
            Ref sld=v.second>0?eld/Ref(v.second):Ref(0),sq=q.second>0?eq/ref_of(q.second):Ref(0);
            st.h_ld_all[bin_of(sld)]++;st.h_q_all[bin_of(sq)]++;
            if(level==0){st.h_ld[bin_of(sld)]++;if(sld>st.ld_max)st.ld_max=sld;if(eld>Ref("1e-15")*Ref(v.second)){st.ld_viol++;note("long-double accepted value off by more than 1e-15 err");}
                if(r.first!=0){Ref rel=eld/abs(r.first);if(rel>st.ld_rel_max)st.ld_rel_max=rel;}}
            if(level==1){st.h_q[bin_of(sq)]++;if(sq>st.q_max)st.q_max=sq;if(eq>Ref("1e-29")*ref_of(q.second)){st.q_viol++;note("binary128 accepted value off by more than 1e-29 err");}
                if(r.first!=0){Ref rel=eq/abs(r.first);if(rel>st.q_rel_max)st.q_rel_max=rel;}}
            Ref emp=abs(ref_of_mp(m.first)-r.first)/(1+r.second);st.h_mp[bin_of(emp)]++;if(emp>st.mp_max)st.mp_max=emp;if(level==2&&emp>st.mp_max_promoted)st.mp_max_promoted=emp;
            if(emp>Ref("1e-280")){st.mp_viol++;note("MP value off by more than 1e-280 (1+err)");}
#ifdef C8_USE_GMP
            if(level==2){auto dm=calculate_shared<Dec300,false>(g,lx.data(),shift);Ref edec=abs(ref_of_mp(dm.first)-r.first)/(1+r.second);if(edec>st.dec_max)st.dec_max=edec;
                if(edec>Ref("1e-280")){st.dec_viol++;note("decimal300 value off by more than 1e-280 (1+err)");}}
#endif
        }catch(const std::exception&e){
            #pragma omp critical
            {if(error.empty())error=e.what();}
        }}
        #pragma omp critical
        {all.add(st);}
    }
    if(!error.empty())throw std::runtime_error(error);
    auto num=[](const Ref&x){return x.str(6,std::ios_base::scientific);};
    std::ostream&f=std::cout;
    f<<"{\"L\":"<<L<<",\"graphs\":"<<graphs.size()<<",\"begin\":"<<begin<<",\"end\":"<<end<<",\"mp_backend\":\""<<mp_backend<<"\",\"points\":"<<all.points
     <<",\"level\":["<<all.level[0]<<','<<all.level[1]<<','<<all.level[2]<<"],\"nonmoderate\":"<<all.nonmoderate<<",\"nondirect\":"<<all.nondirect
     <<",\"decision_mismatch\":"<<all.decision_mismatch<<",\"ld_violations\":"<<all.ld_viol<<",\"quad_violations\":"<<all.q_viol<<",\"mp_violations\":"<<all.mp_viol<<",\"decimal300_violations\":"<<all.dec_viol
     <<",\"max_ld_error_over_err\":\""<<num(all.ld_max)<<"\",\"max_quad_error_over_err\":\""<<num(all.q_max)<<"\",\"max_mp_error_scaled\":\""<<num(all.mp_max)<<"\",\"max_mp_error_scaled_promoted\":\""<<num(all.mp_max_promoted)
     <<"\",\"max_decimal300_error_scaled\":\""<<num(all.dec_max)<<"\",\"max_relative_error_ld_accepted\":\""<<num(all.ld_rel_max)<<"\",\"max_relative_error_quad_accepted\":\""<<num(all.q_rel_max)<<"\"";
    hist(f,"hist_ld_accepted",all.h_ld);hist(f,"hist_quad_accepted",all.h_q);hist(f,"hist_mp_scaled",all.h_mp);hist(f,"hist_ld_all",all.h_ld_all);hist(f,"hist_quad_all",all.h_q_all);
    f<<",\"first_violations\":[";for(size_t k=0;k<all.first.size();++k){if(k)f<<',';f<<'"'<<all.first[k]<<'"';}f<<"]}\n";
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
