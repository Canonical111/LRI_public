#pragma once
// xoshiro256++ (Blackman/Vigna), public-domain transition from
// https://prng.di.unimi.it/xoshiro256plusplus.c . SplitMix64 seeding.
// This is a simulation PRNG, not a cryptographic generator.
#include <cstdint>
#include <istream>
#include <ostream>
#include <limits>
struct Xoshiro256pp {
    using result_type=uint64_t;
    uint64_t s[4];
    static uint64_t rotl(uint64_t x,int k) {return (x<<k)|(x>>(64-k));}
    explicit Xoshiro256pp(uint64_t seed=1) {
        for(auto& v:s){uint64_t z=(seed+=0x9e3779b97f4a7c15ULL);
          z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;
          z=(z^(z>>27))*0x94d049bb133111ebULL;v=z^(z>>31);}
    }
    static constexpr uint64_t min(){return 0;}
    static constexpr uint64_t max(){return std::numeric_limits<uint64_t>::max();}
    uint64_t operator()(){
        uint64_t r=rotl(s[0]+s[3],23)+s[0],t=s[1]<<17;
        s[2]^=s[0];s[3]^=s[1];s[1]^=s[2];s[0]^=s[3];s[2]^=t;s[3]=rotl(s[3],45);
        return r;
    }
    friend std::ostream& operator<<(std::ostream& o,const Xoshiro256pp& r){
        return o<<r.s[0]<<' '<<r.s[1]<<' '<<r.s[2]<<' '<<r.s[3];
    }
    friend std::istream& operator>>(std::istream& i,Xoshiro256pp& r){
        i>>r.s[0]>>r.s[1]>>r.s[2]>>r.s[3];
        if(!(r.s[0]|r.s[1]|r.s[2]|r.s[3]))i.setstate(std::ios::failbit);
        return i;
    }
};
