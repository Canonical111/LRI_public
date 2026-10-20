#pragma once
// Correctly-rounded IEEE binary128 addition for nonnegative normal operands.
// Used ONLY for positive denominator sums. All other cases use the compiler
// runtime. The worker checks FE_TONEAREST before calling this fast path.
// Integer significands retain guard, round, and sticky bits; no precision is lost.
#include <cstdint>
#include <utility>
#include <cstring>
#include <cfenv>
using u128 = __uint128_t;
#ifdef C8_REFERENCE_QUAD_ADD
inline constexpr const char* quad_add_backend="compiler-runtime";
#else
inline constexpr const char* quad_add_backend="positive-binary128-rne";
#endif
inline __float128 positive_quad_add(__float128 a, __float128 b) noexcept {
#ifdef C8_REFERENCE_QUAD_ADD
    return a+b;
#else
    u128 ua,ub; std::memcpy(&ua,&a,16); std::memcpy(&ub,&b,16);
    constexpr u128 hidden=u128(1)<<112;
    constexpr u128 fraction=hidden-1;
    // bit 127 is the sign. The exponent of a positive normal lies in 1..32766.
    unsigned ea=unsigned(ua>>112), eb=unsigned(ub>>112);
    if(ea==0 || eb==0 || ea>=32767 || eb>=32767) return a+b;
    if(ea<eb){std::swap(ua,ub);std::swap(ea,eb);}
    unsigned distance=ea-eb;
    // The smaller operand is strictly below half an ulp of the larger one.
    if(distance>113){__float128 out;std::memcpy(&out,&ua,16);return out;}
    u128 ma=((ua&fraction)|hidden)<<3;
    u128 mb=((ub&fraction)|hidden)<<3;
    if(distance){u128 discarded=mb&((u128(1)<<distance)-1);mb=(mb>>distance)|(discarded!=0);}
    u128 sum=ma+mb;
    if(sum&(hidden<<4)){sum=(sum>>1)|(sum&1);++ea;}
    unsigned tail=unsigned(sum&7);u128 rounded=sum>>3;
    rounded+=(tail>4 || (tail==4 && (rounded&1)));
    if(rounded&(hidden<<1)){rounded>>=1;++ea;}
    if(ea>=32767) return a+b;
    u128 result=(u128(ea)<<112)|(rounded&fraction);
    __float128 out;std::memcpy(&out,&result,16);return out;
#endif
}
