#pragma once
// The worker's point stream (PLAN.md C.2, C.7), shared by src/c8d3_integrate.cpp and src/c8d3_inspect.cpp (--point),
// so a regenerated point is the worker's bit for bit: the Sobol net (a6ce987 src/c7d3_integrate.cpp:11-18, unchanged
// arithmetic; the constructor refuses a start index outside the period, S1-04), the per-(replicate, graph) digital-shift
// seed (:51, unchanged values, S1-05), the optional frozen grid (:38-41, :54, unchanged arithmetic) and the checked net
// and grid readers (C.2: every stream is tested before its values are used, and every
// error names its file).
#include "kernel.hpp"
#include <map>
#include <random>
#include <set>
struct Net {
    int dim,bits;const std::vector<uint64_t>&direction;std::vector<uint64_t>state;
    Net(int d,int b,const std::vector<uint64_t>&v,uint64_t seed,uint64_t begin):dim(d),bits(b),direction(v),state(d){
        if(bits<64&&(begin>>bits)!=0)throw std::runtime_error("Sobol period exceeded (start index "+std::to_string(begin)+" >= 2^"+std::to_string(bits)+")");
        std::mt19937_64 rng(seed);for(auto&s:state)s=rng()>>(64-bits);
        uint64_t gray=begin^(begin>>1);while(gray){int k=__builtin_ctzll(gray);gray&=gray-1;for(int j=0;j<dim;++j)state[j]^=direction[j*bits+k];}}
    void next(uint64_t n){int k=__builtin_ctzll(n);if(k>=bits)throw std::runtime_error("Sobol period exceeded");for(int j=0;j<dim;++j)state[j]^=direction[j*bits+k];}
    void point(ld*u)const {for(int j=0;j<dim;++j)u[j]=(ld(state[j])+.5L)/ld(uint64_t(1)<<bits);}
};
// a6ce987 src/c7d3_integrate.cpp:51's stream seed; S1-05: uint64_t(id)+1 == (id+1) mod 2^64 for every int id < INT_MAX (no stream changes), no overflow at INT_MAX.
inline uint64_t stream_seed(uint64_t seed,uint64_t rep,int id){return seed+0x9e3779b97f4a7c15ULL*(rep+1)+0xbf58476d1ce4e5b9ULL*(uint64_t(id)+1);}
// The net file: header (B, dim, bits) as three little-endian uint32, then B direction matrices of dim*bits uint64.
struct NetFile {int B=0,dim=0,bits=0;std::map<uint64_t,std::vector<uint64_t>>directions;};
inline NetFile read_net(const std::string&path,int layout,int L,const std::set<uint64_t>&reps){
    std::ifstream netf(path,std::ios::binary);if(!netf)throw std::runtime_error(path+": cannot open the net file");
    uint32_t head[3]={0,0,0};netf.read(reinterpret_cast<char*>(head),sizeof(head));
    if(!netf)throw std::runtime_error(path+": truncated net header ("+std::to_string(netf.gcount())+" of 12 bytes)");
    NetFile n;n.B=head[0];n.dim=head[1];n.bits=head[2];
    if(head[1]>uint32_t(DIMMAX))throw std::runtime_error(path+": net dimension "+std::to_string(head[1])+" exceeds DIMMAX="+std::to_string(DIMMAX));
    if(reps.empty()||n.B<2||n.dim!=(layout==2?2*L:4*L-1)||n.bits<32||n.bits>60||*reps.rbegin()>=uint64_t(n.B))
        throw std::runtime_error(path+": bad net header (B "+std::to_string(head[0])+", dim "+std::to_string(head[1])+", bits "+std::to_string(head[2])
                                 +") for L "+std::to_string(L)+", layout "+std::to_string(layout)+" (dim "+std::to_string(layout==2?2*L:4*L-1)+" and 32 <= bits <= 60 required, and every replicate < B)");
    netf.seekg(0,std::ios::end);if(uint64_t(netf.tellg())!=12+uint64_t(n.B)*n.dim*n.bits*8)throw std::runtime_error(path+": net file size mismatch");
    for(auto rep:reps){auto&v=n.directions[rep];v.resize(n.dim*n.bits);netf.seekg(12+rep*n.dim*n.bits*8);netf.read(reinterpret_cast<char*>(v.data()),v.size()*8);
        if(!netf)throw std::runtime_error(path+": truncated direction matrix of replicate "+std::to_string(rep));
        for(auto x:v)if(x>=(uint64_t(1)<<n.bits))throw std::runtime_error(path+": invalid direction number in replicate "+std::to_string(rep));}
    return n;
}
// Optional frozen grid: "n e nb", then n rows "id" + e axes of nb+1 = 33 knots. Reading it does not silently normalize
// its endpoints.
using Grid=std::vector<std::array<ld,33>>;
inline std::map<uint64_t,Grid> read_grid(const std::string&path,int L,const std::set<uint64_t>&graphs){
    std::ifstream gf(path);if(!gf)throw std::runtime_error(path+": cannot open the grid file");
    int n=0,e=0,nb=0;gf>>n>>e>>nb;if(!gf)throw std::runtime_error(path+": truncated or malformed grid header");
    if(n<1||e!=2*L-1||nb!=32)throw std::runtime_error(path+": invalid grid header (n "+std::to_string(n)+", e "+std::to_string(e)+", nb "+std::to_string(nb)+"; e = 2L-1 and nb = 32 required)");
    std::set<int>seen;std::map<uint64_t,Grid>grids;
    for(int k=0;k<n;++k){int id=0;if(!(gf>>id))throw std::runtime_error(path+": truncated or malformed grid row "+std::to_string(k)+" id");
        if(!seen.insert(id).second)throw std::runtime_error(path+": duplicate grid graph "+std::to_string(id));
        Grid gr(e);for(auto&axis:gr){for(auto&x:axis)if(!(gf>>x))throw std::runtime_error(path+": truncated or malformed grid row "+std::to_string(k)+" (graph "+std::to_string(id)+")");
            for(int j=0;j<32;++j)if(!std::isfinite(axis[j])||!std::isfinite(axis[j+1])||axis[j+1]<=axis[j])throw std::runtime_error(path+": nonmonotonic grid (graph "+std::to_string(id)+")");
            if(fabsl(axis[0])>1e-12L||fabsl(axis[32]-1)>1e-12L)throw std::runtime_error(path+": grid endpoints outside tolerance (graph "+std::to_string(id)+")");}
        if(graphs.count(id))grids.emplace(id,std::move(gr));}
    if(grids.size()!=graphs.size())throw std::runtime_error(path+": missing grid rows");
    return grids;
}
// One point's coordinates through the grid: a6ce987 src/c7d3_integrate.cpp:54, the same arithmetic. Returns the
// Jacobian (1 without a grid).
inline ld apply_grid(const Grid*grid,int E,int layout,ld*u){
    ld jac=1;
    if(grid)for(int j=0;j<E-1;++j){int ix=layout==0?2*j+1:(layout==2?j+1:j);ld y=u[ix]*32;int bin=std::min(31,int(y));const auto&axis=(*grid)[j];ld w=axis[bin+1]-axis[bin];u[ix]=axis[bin]+w*(y-bin);jac*=32*w;}
    return jac;
}
