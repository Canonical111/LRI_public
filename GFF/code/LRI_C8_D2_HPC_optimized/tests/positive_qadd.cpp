// Exact-bit boundary and randomized regression against GCC's binary128 add.
#include "../src/positive_qadd.hpp"
#include <array>
#include <cfenv>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <random>
#include <vector>
#include <quadmath.h>

using c8::qword;
using Q = __float128;
__attribute__((noinline)) Q reference_add(Q a, Q b) { return a + b; }

int main() {
    if (std::fesetround(FE_TONEAREST) != 0) return 2;
    constexpr qword hidden = qword(1) << 112, frac = hidden - 1;
    std::uint64_t checks = 0;
    auto check = [&](qword a, qword b) {
        Q x = c8::qvalue(a), y = c8::qvalue(b);
        const auto expected = c8::qbits(reference_add(x,y));
        const auto actual = c8::qbits(c8::add_positive_nearest(x,y));
        ++checks;
        if (expected != actual) {
            std::cerr << "Mismatch at case " << checks << "\n";
            char aa[160],bb[160],rr[160],gg[160];
            quadmath_snprintf(aa,sizeof aa,"%Qa",x);quadmath_snprintf(bb,sizeof bb,"%Qa",y);
            quadmath_snprintf(rr,sizeof rr,"%Qa",c8::qvalue(expected));quadmath_snprintf(gg,sizeof gg,"%Qa",c8::qvalue(actual));
            std::cerr << aa << " + " << bb << " expected " << rr << " got " << gg << "\n";
            std::exit(1);
        }
    };
    const std::array<qword,12> mantissas{0,1,2,3,7,hidden/2-1,hidden/2,hidden/2+1,frac-3,frac-2,frac-1,frac};
    for (unsigned e : {1u,2u,3u,114u,115u,1023u,8192u,16383u,16384u,32764u,32765u,32766u}) {
        for (unsigned distance=0;distance<=116;++distance) if(e>distance) {
            for(auto ma:mantissas) for(auto mb:mantissas) {
                qword a=(qword(e)<<112)|ma,b=(qword(e-distance)<<112)|mb;
                check(a,b);check(b,a);
            }
        }
    }
    // Fallback classes, including signed zero, subnormals, infinities and NaNs.
    const std::array<qword,12> specials{0,qword(1)<<127,1,frac,hidden,
        qword(0x7fff)<<112,(qword(0x7fff)<<112)|1,(qword(0x7fff)<<112)|(hidden/2),
        qword(0xffff)<<112,(qword(0x8001)<<112)|1,qword(0xbfff)<<112,qword(0x7ffe)<<112};
    for(auto a:specials)for(auto b:specials){check(a,b);check(b,a);}
    std::mt19937_64 rng(0xC8D220261009ULL);
    for(std::uint64_t i=0;i<3000000;++i) {
        unsigned e=1+unsigned(rng()%32766),distance=unsigned(rng()%130);
        unsigned eb=e>distance?e-distance:1;
        qword a=(qword(e)<<112)|(((qword(rng())<<64)|rng())&frac);
        qword b=(qword(eb)<<112)|(((qword(rng())<<64)|rng())&frac);
        check(a,b);if(i%8==0)check(b,a);
    }
    // Repeat a realistic positive summation chain; the runtime benchmark uses
    // graph fixtures and is authoritative for application speedup.
    std::vector<Q> values(8192);
    for(auto&v:values) {
        const unsigned e=16383-unsigned(rng()%80);
        v=c8::qvalue((qword(e)<<112)|(((qword(rng())<<64)|rng())&frac));
    }
    auto run=[&](bool fast) {
        const auto start=std::chrono::steady_clock::now();Q sum=0;
        for(int repeat=0;repeat<128;++repeat) {
            sum=0;
            for(Q v:values)sum=fast?c8::add_positive_nearest(sum,v):reference_add(sum,v);
        }
        const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        return std::make_pair(sum,seconds);
    };
    const auto base=run(false),fast=run(true);
    if(c8::qbits(base.first)!=c8::qbits(fast.first))return 3;
    std::cout << "{\"passed\":true,\"exact_bit_checks\":"<<checks
              <<",\"chain_additions\":1048576,\"baseline_seconds\":"<<base.second
              <<",\"specialized_seconds\":"<<fast.second<<",\"speedup\":"<<base.second/fast.second<<"}\n";
}
