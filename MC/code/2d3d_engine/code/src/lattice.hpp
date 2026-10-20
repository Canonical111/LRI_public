#pragma once
#include "alias.hpp"
#include <cmath>
#include <vector>
#include <stdexcept>
// Infinite-lattice Poisson envelope. No L^d kernel/alias table, no radial cutoff.
// Core C0=[-B,B-1]^d (minus 0) uses exact |r|^{-d-s} weights.
// Shell C_{k+1}\C_k has (4^d-2^d)(B*2^k)^d lattice points and
// bound |r|^{-d-s} <= (B*2^k)^{-d-s}. Thus shell masses are geometric.
// Fold an accepted infinite-lattice displacement coordinatewise modulo L;
// discarded self images are constants. Thin BEFORE checking spin alignment.
struct LatticeEnvelope {
    Alias core;int dim=0,lb=0,L=0,basebits=0;double s=0,mass=0,tail_mass=0;std::vector<uint32_t> near_disp;std::vector<double> near_weight;
    void build(int d,int length,double exponent,int B,double nn_extra,bool hybrid=false,int near_radius=1){
        if(d<2||d>3||exponent<=1||exponent>=2)throw std::runtime_error("lattice envelope supports d=2,3 and 1<s<2");
        if(B<1||B>32||(B&(B-1)))throw std::runtime_error("lattice core-radius must be a power of two, 1..32");
        dim=d;L=length;s=exponent;while((1<<lb)<L)++lb;
        while((1<<basebits)<B)++basebits;
        std::vector<double> w;std::vector<uint32_t> val;
        int side=2*B,vol=1;for(int a=0;a<d;++a)vol*=side;
        long double total=0;
        for(int v=0;v<vol;++v){int n=v,r2=0;uint32_t disp=0;bool near=true;
            for(int a=0;a<d;++a){int c=n%side-B;n/=side;r2+=c*c;near=near&&(std::abs(c)<=near_radius);disp|=(uint32_t(c)&uint32_t(L-1))<<(a*lb);}
            if(r2==0)continue;
            double weight=std::pow(double(r2),-(d+s)/2);if(r2==1)weight+=nn_extra;
            if(hybrid&&near){if(disp){near_disp.push_back(disp);near_weight.push_back(weight);}continue;}
            w.push_back(weight);val.push_back(disp);total+=weight;
        }
        // B=1 excludes +e_a from core; insist on B>=2 when adding NN terms.
        if(nn_extra>0&&B<2)throw std::runtime_error("nn-extra requires core-radius>=2");
        tail_mass=(std::pow(4.,d)-std::pow(2.,d))*std::pow(double(B),-s)/(-std::expm1(-s*std::log(2.)));
        w.push_back(tail_mass);val.push_back(UINT32_MAX);total+=tail_mass;
        mass=double(total);core.build(w,val);
    }
    template<class R> inline uint32_t draw(R& rng)const{
        uint32_t r=core.draw(rng);if(r!=UINT32_MAX)return r;
        // U in (0,1]; geometric shell. For the supported s>1 and B<=32,
        // the 53-bit uniform guarantees integer coordinates fit int64_t.
        double u=(double(rng()>>11)+1.0)*0x1p-53;
        int k=int(-std::log(u)/(s*0.693147180559945309417232121458));
        int b=basebits+k;int64_t B=int64_t(1)<<b;
        int64_t coords[3];bool inner;
        do{inner=true;
            for(int a=0;a<dim;++a){coords[a]=int64_t(rng()>>(64-(b+2)))-2*B;
                inner=inner&&(coords[a]>=-B&&coords[a]<B);}
        }while(inner);
        double norm=0,scale=std::ldexp(1.0,-b);uint32_t disp=0;
        for(int a=0;a<dim;++a){double c=double(coords[a])*scale;norm+=c*c;
            disp|=(uint32_t(uint64_t(coords[a])&uint64_t(L-1)))<<(a*lb);}
        double accept=std::pow(norm,-(dim+s)/2);
        return double(rng()>>11)*0x1p-53<accept?disp:UINT32_MAX;
    }
};
