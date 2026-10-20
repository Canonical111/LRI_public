#include "../src/kernel.hpp"
#include <iostream>
#include <string>

static size_t checks=0, dense_bytes=0, stored_bytes=0;

void check_values(const Graph&g,const std::vector<ld>&expected) {
    for(size_t i=0;i<expected.size();++i){
        ld actual=g.proposal_alpha(unsigned(i));
        if(actual!=expected[i] || std::signbit(actual)!=std::signbit(expected[i]))
            throw std::runtime_error("Rate palette changed an original long-double value");
        ++checks;
    }
}

void synthetic_checks() {
    for(ld scale:{.8L,.9L}){
        Graph g;g.L=8;g.E=16;g.alpha.resize(1u<<16);
        for(size_t i=0;i<g.alpha.size();++i)g.alpha[i]=(ld(i%16)+1)/2*scale;
        g.alpha.front()=g.alpha.back()=0;
        auto expected=g.alpha;compact_sampling_rates(g);check_values(g,expected);
#ifndef C8_DISABLE_RATE_PALETTE
        if(!g.alpha.empty() || g.alpha.capacity()!=0 || g.alpha_palette.size()!=17 || g.alpha_index.size()!=expected.size())
            throw std::runtime_error("Expected exact compact rate storage");
#endif
        compact_sampling_rates(g);check_values(g,expected); // Idempotent.
    }
    Graph unusual;unusual.L=8;unusual.E=16;unusual.alpha.resize(1u<<16);
    for(size_t i=0;i<unusual.alpha.size();++i)unusual.alpha[i]=ld(i%257+1);
    auto expected=unusual.alpha;compact_sampling_rates(unusual);check_values(unusual,expected);
    if(!unusual.alpha_index.empty() || unusual.alpha!=expected)
        throw std::runtime_error("A table with more than256 values must retain dense storage");
    Graph lower;lower.L=7;lower.E=14;lower.alpha.assign(1u<<14,.425L);
    expected=lower.alpha;compact_sampling_rates(lower);check_values(lower,expected);
    if(!lower.alpha_index.empty() || lower.alpha!=expected)
        throw std::runtime_error("Lower-order tables must retain their existing storage");
    Graph signed_zero;signed_zero.L=8;signed_zero.E=16;signed_zero.alpha.assign(1u<<16,.5L);
    signed_zero.alpha[0]=-0.L;expected=signed_zero.alpha;
    compact_sampling_rates(signed_zero);check_values(signed_zero,expected);
    if(!signed_zero.alpha_index.empty())throw std::runtime_error("Negative-zero table must remain dense");
}

std::vector<ld> original_scaled_rates(const std::string&path,ld scale) {
    std::ifstream f(path);std::string magic;int L,id,M,T,n,value;ld wa,wb;
    f>>magic>>L>>id>>wa>>wb>>M>>T;
    for(int i=0;i<M;++i)f>>value;
    for(int t=0;t<T;++t){f>>n;for(int i=0;i<n+2*L;++i)f>>value;}
    f>>n;std::vector<ld> values(n);
    for(ld&x:values){f>>x;x*=scale;}
    if(!f)throw std::runtime_error("Cannot independently read rate table");
    return values;
}

int main(int argc,char**argv) {
    try {
        synthetic_checks();int graphs=0;
        if(argc!=2)throw std::runtime_error("Usage: rate_palette graph_list");
        std::ifstream list(argv[1]);if(!list)throw std::runtime_error("Cannot read graph list");
        std::string path;
        while(list>>path)for(ld scale:{.8L,.9L}){
            auto g=load_graph(path,scale);auto expected=original_scaled_rates(path,scale);
            check_values(g,expected);++graphs;
            dense_bytes+=expected.size()*sizeof(ld);
            stored_bytes+=g.alpha.capacity()*sizeof(ld)+g.alpha_palette.capacity()*sizeof(ld)+g.alpha_index.capacity();
        }
        std::cout<<"{\"status\":\"passed\",\"exact_rate_values_checked\":"<<checks
            <<",\"physical_graph_rate_pairs\":"<<graphs<<",\"dense_rate_bytes\":"<<dense_bytes
            <<",\"stored_rate_bytes\":"<<stored_bytes<<",\"palette_enabled\":"
#ifndef C8_DISABLE_RATE_PALETTE
            <<"true"
#else
            <<"false"
#endif
            <<"}\n";
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
