#pragma once
#include "alias.hpp"
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>
// Positive infinite-lattice displacements; total proposal rate = 2*beta*N*mass.
// The negative displacements are absorbed by reversal of the uniform source site.
// Core: r=1,...,B-1. Tail shells: 2^b <= r < 2^(b+1), b=log2(B)+k.
// Shell bound r^(-1-s) <= 2^(-b(1+s)); masses 2^(-b*s).
// Each accepted displacement is folded modulo L; self images are discarded.
// Wide-shell implementation retains the low modulo bits even for b>64.
struct LineEnvelope {
    Alias core;
    int L=0,basebits=0;double s=0,mass=0,tail_mass=0;
    std::vector<uint32_t> near_disp;
    std::vector<double> near_weight;
    void build(int length,double exponent,int B,int R,bool backbone,double nn_extra){
        if(!(exponent>0.5&&exponent<1.0))throw std::runtime_error("line sampler requires 1/2<s<1");
        if(B<4||B>4096||(B&(B-1)))throw std::runtime_error("line core radius: power of two in [4,4096]");
        if(R<0||R>=B)throw std::runtime_error("near radius must be < core radius");
        L=length;s=exponent;basebits=0;while((1<<basebits)<B)++basebits;
        std::vector<double>w;std::vector<uint32_t>v;long double sum=0;
        for(int r=1;r<B;++r){
            double z=std::pow(double(r),-1.0-s)+(r==1?nn_extra:0.0);
            if(backbone&&r==1)continue;
            if(r<=R){ if((r&(L-1))!=0){near_disp.push_back(r&(L-1));near_weight.push_back(2*z);}continue;}
            w.push_back(z);v.push_back(uint32_t(r&(L-1)));sum+=z;
        }
        tail_mass=std::pow(double(B),-s)/(-std::expm1(-s*std::log(2.0)));
        w.push_back(tail_mass);v.push_back(UINT32_MAX);sum+=tail_mass;
        mass=double(sum);core.build(w,v);
    }
    template<class R> uint32_t shell(R& rng,int b)const{
        if(b<0||b>127)throw std::runtime_error("tail shell outside supported integer range");
        uint64_t low;double norm;
        if(b<64){
            const uint64_t top=uint64_t(1)<<b;
            low=top+(rng()&(top-1));norm=std::ldexp(double(low),-b);
        }else{
            low=rng();const int h=b-64;
            uint64_t high=h?(rng()&((uint64_t(1)<<h)-1)):0;
            norm=1.0+std::ldexp(double(high),-h)+std::ldexp(double(low),-b);
        }
        const uint32_t disp=uint32_t(low&uint64_t(L-1));
        return double(rng()>>11)*0x1p-53<std::pow(norm,-1.0-s)?disp:UINT32_MAX;
    }
    template<class R> inline uint32_t draw(R& rng)const{
        const uint32_t r=core.draw(rng);if(r!=UINT32_MAX)return r;
        // 53-bit U in (0,1]; shell law geometric. Probability beyond the largest
        // representable shell is <2^-53 of tail proposals, not a spatial cutoff.
        const double u=(double(rng()>>11)+1.0)*0x1p-53;
        const int k=int(-std::log(u)/(s*0.693147180559945309417232121458));
        return shell(rng,basebits+k);
    }
};

// Small fixed-mean Poisson inverse CDF. Exactly one uniform per aligned nearest
// neighbor, rather than random-position events and repeated union/find calls.
// CDFs use long double, inverse query a 53-bit uniform. Remaining unrepresented
// tail is bounded during construction (<1e-20); finite RNG/CDF resolution is
// an ordinary numerical discretization, not an interaction-range truncation.
struct SmallPoisson {
    std::vector<double> cdf;
    uint8_t first[256]{};
    explicit SmallPoisson(double mu){
        if(!(mu>0&&mu<=32))throw std::runtime_error("backbone needs 0<2*beta*(1+nn-extra)<=32");
        long double p=std::exp(-static_cast<long double>(mu)),acc=p;
        cdf.push_back(double(acc));
        for(int k=1;k<256;++k){
            p*=static_cast<long double>(mu)/k;acc+=p;
            cdf.push_back(double(acc));
            if(k>mu&&p*mu/(k+1-mu)<1e-20L){cdf.back()=1.0;
                int j=0;for(int z=0;z<256;++z){while(j+1<int(cdf.size())&&double(z)/256>=cdf[j])++j;first[z]=uint8_t(j);}return;}
        }
        throw std::runtime_error("small Poisson CDF construction failed");
    }
    template<class R> inline int draw(R& rng)const{
        const uint64_t word=rng();const double u=double(word>>11)*0x1p-53;int k=first[word>>56];
        while(k+1<int(cdf.size())&&u>=cdf[k])++k;
        return k;
    }
};
