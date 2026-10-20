#pragma once
// An exact-value specialization of IEEE binary128 addition for positive normal
// operands in round-to-nearest, ties-to-even mode. Denominator sums have this
// sign restriction. The caller must check the rounding mode outside its loop.
// Other operand classes use the compiler's full binary128 implementation.
// No polynomial is reassociated and no precision or exponent bits are dropped.
#include <cstring>
#include <cstdint>

namespace c8 {
using qword = unsigned __int128;
static_assert(sizeof(__float128) == sizeof(qword), "binary128 storage required");
#if defined(__FLT128_MANT_DIG__)
static_assert(__FLT128_MANT_DIG__ == 113 && __FLT128_MAX_EXP__ == 16384,
              "IEEE binary128 format required");
#endif

inline qword qbits(__float128 value) {
    qword bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}
inline __float128 qvalue(qword bits) {
    __float128 value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

inline __float128 add_positive_nearest(__float128 a, __float128 b) {
    qword aa = qbits(a), bb = qbits(b);
    constexpr qword hidden = qword(1) << 112;
    constexpr qword fraction = hidden - 1;
    // Positive IEEE encodings have the same unsigned and numerical ordering.
    if (aa < bb) { const qword tmp = aa; aa = bb; bb = tmp; }
    const unsigned ea = unsigned(aa >> 112), eb = unsigned(bb >> 112);
    // This also rejects every negative encoding (its high exponent bit is set),
    // NaN/infinity, and the exponent where a normal result might overflow.
    if (eb == 0 || ea >= 0x7ffeu || eb >= 0x7ffeu) return a + b;
    const unsigned distance = ea - eb;
    // Even the largest smaller operand is strictly below half an ulp here.
    if (distance > 113) return qvalue(aa);
    qword big = ((aa & fraction) | hidden) << 3;
    qword small = ((bb & fraction) | hidden) << 3;
    if (distance) {
        const qword lost = small & ((qword(1) << distance) - 1);
        small = (small >> distance) | qword(lost != 0);
    }
    qword sum = big + small;
    unsigned exponent = ea;
    if (sum & (hidden << 4)) {
        sum = (sum >> 1) | (sum & 1);  // retain sticky information
        ++exponent;
    }
    qword mantissa = sum >> 3;
    const unsigned round_bits = unsigned(sum & 7);
    if (round_bits > 4 || (round_bits == 4 && (mantissa & 1))) ++mantissa;
    if (mantissa & (hidden << 1)) { mantissa >>= 1; ++exponent; }
    return qvalue((qword(exponent) << 112) | (mantissa & fraction));
}
}  // namespace c8
