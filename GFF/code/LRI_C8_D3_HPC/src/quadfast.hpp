#pragma once
// R3a (PLAN "Performance plan", Stage 4b): correctly rounded binary128 addition, subtraction and multiplication as
// inline integer code on 64-bit limbs, bit for bit equal to libgcc's soft-fp __addtf3, __subtf3 and __multf3 in
// round-to-nearest-even. The kernel always runs in round-to-nearest: no source file touches the FP environment, and
// libquadmath's expq restores the caller's environment.
//
// Fast path: both operands normal (finite, nonzero, biased exponent 1..0x7FFE) and a normal, finite result. Everything
// else is computed by libgcc itself, through the out-of-line slow_* helpers below, with the operands as given:
// a zero, subnormal, infinite or NaN operand, an exact zero sum (its sign follows the IEEE rule), and a result that
// would be subnormal or overflow. Only calculate_shared<Q> (src/kernel.hpp, its T = Q statements) uses it; division,
// conversions, comparisons and expq stay libgcc/libquadmath. The operations work on the bit patterns (unsigned
// __int128, i.e. two 64-bit registers) and so do the libgcc fallbacks, so no operand passes through an SSE register.
//
// Exception flags: the fast path raises none (libgcc raises inexact). The kernel never reads the flags, and no result
// depends on them.
//
// Method.
// - Effective addition (the kernel's sums of positive products), on 64-bit words: the smaller significand B is shifted
//   right by the exponent difference d, its shifted-out bits kept in a separate word `ext` (their top 64 bits, any lower
//   nonzero bit ORed into bit 0). The larger operand has no bits there, so A + (B >> d) is exact and ext is the exact
//   fraction of an ulp below it, to the sticky bit: nearest-even rounds up when ext > 2^63, or ext == 2^63 and the sum is
//   odd. A carry to 2^113 moves one bit into the rounding (round bit = the sum's last bit, sticky = ext != 0). d >= 114
//   leaves less than half an ulp, so the result is the larger operand.
// - Effective subtraction and multiplication: the exact result is brought to a 128-bit working value W with the hidden
//   bit at bit 125 (or 126 after a carry), i.e. the 113-bit significand and 13 work bits, every lower nonzero bit ORed
//   into bit 0 (sticky); round_pack() renormalizes a carry (ORing the shifted-out bit in again) and rounds to
//   nearest-even at bit 13. When bits are lost, the computed W' is odd and the exact value lies strictly inside
//   (W'-1, W'+1), which holds no multiple of 2; every rounding boundary (the result's ulp and its midpoints) is a
//   multiple of 2^11 or coarser, also after the at most 1-bit shifts, so W' and the exact value round alike.
//   Subtraction takes the larger magnitude first and shifts the smaller significand right with the sticky bit (a bit
//   is lost exactly when d exceeds its trailing-zero count); for d >= 2 the difference exceeds 2^124 and needs at most
//   a 1-bit left shift, while massive cancellation (a larger shift) needs d <= 1, where nothing was lost and the
//   difference is exact; an exact zero goes to libgcc. Multiplication forms the exact 226-bit product from four
//   64x64->128 partial products and shifts it right by 99, the lost bits as sticky.
// - Packing adds the significand (2^112..2^113, hidden bit included) to the exponent field minus 1, so a rounding carry
//   to 2^113 increments the exponent by itself; overflow is checked on the packed exponent.
// tests/quad_differential.cpp checks all three against libgcc on >= 10^9 random pairs per operation and on edge lists
// (ties, carries, sticky bits at every alignment, cancellation, signed zeros, the subnormal and overflow boundaries,
// inf/NaN); tests/quad_ranges.cpp records the operand ranges the kernel's binary128 tier sees.
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <utility>
// Test hook (tests/quad_ranges.cpp): a program that defines C8_QUADFAST_OBSERVE(op,a,b) before including this header sees
// every operand pair of the three operations. Undefined (every worker build), it expands to nothing.
#ifndef C8_QUADFAST_OBSERVE
#define C8_QUADFAST_OBSERVE(op,a,b) ((void)0)
#endif
namespace quadfast {
using F=__float128;
using u128=unsigned __int128;
static_assert(sizeof(F)==16&&sizeof(u128)==16,"binary128 and unsigned __int128 are 16 bytes");
#if defined(__FLT128_MANT_DIG__) && defined(__FLT128_MAX_EXP__)
static_assert(__FLT128_MANT_DIG__==113&&__FLT128_MAX_EXP__==16384,"__float128 is IEEE binary128");
#endif
constexpr u128 ONE=1;
constexpr u128 HIDDEN=ONE<<112;     // the implicit leading bit of a normal significand
constexpr u128 FRAC=HIDDEN-1;       // the 112 stored fraction bits
constexpr u128 SIGN=ONE<<127;
constexpr int EXP_INF=0x7FFF;       // biased exponent of inf and NaN
constexpr int BIAS=16383;
constexpr int WORK=13;              // work bits below the significand in W
#define C8_QF_INLINE __attribute__((always_inline)) inline
#define C8_QF_UNLIKELY(x) __builtin_expect(!!(x),0)
C8_QF_INLINE u128 bits(const F&x){u128 u;std::memcpy(&u,&x,sizeof u);return u;}
C8_QF_INLINE F value(u128 u){F x;std::memcpy(&x,&u,sizeof x);return x;}
C8_QF_INLINE int clz(u128 x){const uint64_t h=uint64_t(x>>64);return h?__builtin_clzll(h):64+__builtin_clzll(uint64_t(x));}  // x != 0
C8_QF_INLINE int ctz(u128 x){const uint64_t l=uint64_t(x);return l?__builtin_ctzll(l):64+__builtin_ctzll(uint64_t(x>>64));}  // x != 0
// The two 64-bit words of a binary128 pattern (the low word, then sign/exponent/top 48 fraction bits).
struct Words {uint64_t lo,hi;};
C8_QF_INLINE Words words(u128 u){return {uint64_t(u),uint64_t(u>>64)};}
C8_QF_INLINE u128 join(uint64_t lo,uint64_t hi){return (u128(hi)<<64)|lo;}
constexpr uint64_t S64=uint64_t(1)<<63;        // sign bit of the high word
constexpr uint64_t H48=uint64_t(1)<<48;        // hidden bit (bit 112) in the high word
constexpr uint64_t F48=H48-1;                  // the 48 fraction bits of the high word
// libgcc's own operations, out of line (noipa: a real call with the operands as given, never folded or specialized).
// They take and return the bit patterns, so the inline code never moves an operand through an SSE register.
__attribute__((noipa,cold)) inline u128 slow_add(u128 a,u128 b){return bits(value(a)+value(b));}
__attribute__((noipa,cold)) inline u128 slow_sub(u128 a,u128 b){return bits(value(a)-value(b));}
__attribute__((noipa,cold)) inline u128 slow_mul(u128 a,u128 b){return bits(value(a)*value(b));}

// W: hidden bit at 125 (or 126), WORK work bits, sticky in bit 0; e1: the biased exponent minus 1 for the hidden bit at
// 125. Rounds to nearest-even and packs with the sign; false when the result is not normal and finite.
C8_QF_INLINE bool round_pack(u128 W,int e1,u128 sign,u128&r){
    const int c=int(W>>126);                                       // hidden bit at 126: one renormalizing shift
    W=c?((W>>1)|(W&1)):W;
    const unsigned ex=unsigned(e1+c);                              // biased exponent - 1
    if(C8_QF_UNLIKELY(ex>=unsigned(EXP_INF)))return false;         // subnormal range (e1+c < 0) or overflow
    W+=((ONE<<(WORK-1))-1)+((W>>WORK)&1);                          // nearest, ties to even
    const u128 m=(u128(ex)<<112)+(W>>WORK);                        // the significand (2^112..2^113) adds 1 or 2 to ex
    if(C8_QF_UNLIKELY((m>>112)>=u128(EXP_INF)))return false;       // overflow
    r=sign|m;
    return true;
}
// The bits of a+b (Sub=false) or a-b (Sub=true), given as bit patterns, when both operands are normal and the result is
// normal; false (r untouched) otherwise, and the caller then asks libgcc.
template<bool Sub> C8_QF_INLINE bool addsub_fast(u128 a,u128 b,u128&r){
    Words x=words(a),y=words(b);
    if(Sub)y.hi^=S64;
    if(((x.hi^y.hi)&S64)==0){
        // Effective addition on 64-bit words (Method, above): the larger exponent first (equal exponents: either order).
        uint64_t xh=x.hi&~S64,yh=y.hi&~S64;
        if(xh<yh){std::swap(x,y);std::swap(xh,yh);}
        const int ea=int(xh>>48),eb=int(yh>>48);
        if(C8_QF_UNLIKELY(eb==0||ea==EXP_INF))return false;       // a zero/subnormal operand, or inf/NaN
        const unsigned d=unsigned(ea-eb);
        if(C8_QF_UNLIKELY(d>=114)){r=join(x.lo,x.hi);return true;}
        const uint64_t bh=(yh&F48)|H48,bl=y.lo;
        uint64_t sh,sl,ext;
        if(d<64){                                                  // (v<<1)<<(63-d) = v<<(64-d), and 0 for d = 0
            ext=(bl<<1)<<(63-d);sl=(bl>>d)|((bh<<1)<<(63-d));sh=bh>>d;
        }else{
            const unsigned e=d-64;
            ext=(bl>>e)|((bh<<1)<<(63-e));sl=bh>>e;sh=0;
            ext|=uint64_t(((bl<<1)<<(63-e))!=0);                   // sticky: B's bits below the top 64 shifted out
        }
        uint64_t lo=x.lo+sl,hi=((xh&F48)|H48)+sh+uint64_t(lo<sl);
        int e1=ea-1;                                               // biased exponent - 1 for the hidden bit at 112
        if(C8_QF_UNLIKELY(hi>>49)){                                // sum >= 2^113: one bit right, into the rounding
            const uint64_t half=lo&1;lo=(lo>>1)|(hi<<63);hi>>=1;e1=ea;
            const uint64_t up=half&(uint64_t(ext!=0)|(lo&1));lo+=up;hi+=uint64_t(lo<up);
        }else{
            const uint64_t up=uint64_t(ext>S64-(lo&1));            // ext > 2^63, or ext == 2^63 and lo odd
            lo+=up;hi+=uint64_t(lo<up);
        }
        const uint64_t rh=hi+(uint64_t(e1)<<48);                  // the significand (2^112..2^113) adds 1 or 2 to e1
        if(C8_QF_UNLIKELY((rh>>48)>=uint64_t(EXP_INF)))return false;   // overflow
        r=join(lo,rh|(x.hi&S64));
        return true;
    }
    // Effective subtraction (128-bit working value, WORK work bits, round_pack): |a| >= |b|.
    u128 ua=(u128(x.hi)<<64)|x.lo,ub=(u128(y.hi)<<64)|y.lo;
    u128 xa=ua&~SIGN,xb=ub&~SIGN;
    if(xa<xb){std::swap(ua,ub);std::swap(xa,xb);}
    const int ea=int(xa>>112),eb=int(xb>>112);
    if(C8_QF_UNLIKELY(eb==0||ea==EXP_INF))return false;
    const u128 A=((xa&FRAC)|HIDDEN)<<WORK,B=((xb&FRAC)|HIDDEN)<<WORK;
    const int d=std::min(ea-eb,127);
    const u128 W=A-((B>>d)|u128(d>ctz(B)));
    if(C8_QF_UNLIKELY(W==0))return false;                          // exact zero: libgcc gives its signed zero
    const int s=clz(W)-2;                                          // hidden bit back to bit 125
    return round_pack(W<<s,ea-1-s,ua&SIGN,r);
}
// The bits of a*b, given as bit patterns, when both operands are normal and the result is normal; false (r untouched)
// otherwise.
C8_QF_INLINE bool mul_fast(u128 ua,u128 ub,u128&r){
    const int ea=int(ua>>112)&EXP_INF,eb=int(ub>>112)&EXP_INF;
    if(C8_QF_UNLIKELY(unsigned(ea-1)>=unsigned(EXP_INF-1)||unsigned(eb-1)>=unsigned(EXP_INF-1)))return false;
    const u128 ma=(ua&FRAC)|HIDDEN,mb=(ub&FRAC)|HIDDEN;           // 113-bit significands
    const uint64_t a0=uint64_t(ma),a1=uint64_t(ma>>64),b0=uint64_t(mb),b1=uint64_t(mb>>64);
    const u128 p00=u128(a0)*b0,p01=u128(a0)*b1,p10=u128(a1)*b0,p11=u128(a1)*b1;
    const u128 mid=p01+p10+(p00>>64);                              // < 2^114 + 2^64
    const u128 hi=p11+(mid>>64);                                   // P >> 128, in [2^96, 2^98)
    const uint64_t l1=uint64_t(mid),l0=uint64_t(p00);              // P mod 2^128 = l1:l0
    const uint64_t lost=(l1&((uint64_t(1)<<35)-1))|l0;            // P mod 2^99
    const u128 W=(hi<<29)|(l1>>35)|u128(lost!=0);                  // P >> 99 with the sticky bit, in [2^125, 2^127)
    return round_pack(W,ea+eb-BIAS-1,(ua^ub)&SIGN,r);
}
// The operations the kernel calls: the fast path, else libgcc on the same operands.
C8_QF_INLINE F add(const F&a,const F&b){C8_QUADFAST_OBSERVE('+',a,b);const u128 x=bits(a),y=bits(b);u128 r;if(C8_QF_UNLIKELY(!addsub_fast<false>(x,y,r)))r=slow_add(x,y);return value(r);}
C8_QF_INLINE F sub(const F&a,const F&b){C8_QUADFAST_OBSERVE('-',a,b);const u128 x=bits(a),y=bits(b);u128 r;if(C8_QF_UNLIKELY(!addsub_fast<true>(x,y,r)))r=slow_sub(x,y);return value(r);}
C8_QF_INLINE F mul(const F&a,const F&b){C8_QUADFAST_OBSERVE('*',a,b);const u128 x=bits(a),y=bits(b);u128 r;if(C8_QF_UNLIKELY(!mul_fast(x,y,r)))r=slow_mul(x,y);return value(r);}
#undef C8_QF_INLINE
#undef C8_QF_UNLIKELY
}  // namespace quadfast
