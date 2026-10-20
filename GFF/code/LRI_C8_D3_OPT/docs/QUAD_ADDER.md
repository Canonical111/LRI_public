# Exact positive binary128 addition

`src/positive_quad.hpp` replaces only the additions in the binary128 evaluation
of positive denominator polynomials. It does **not** replace signed forest sums,
products, square roots, divisions, logarithms, exponentials, or multiprecision
arithmetic. The worker requires round-to-nearest, ties-to-even (`FE_TONEAREST`).

## Representation and rounding argument

For a positive normal IEEE binary128 number, write the stored integer
significand as `M = 2^112 + fraction`. It contains all 113 significant bits.
The fast path extracts both exponent/significand pairs without floating-point
conversion. It aligns the smaller operand with **three extra bits**, retaining
a sticky bit if any discarded bit is nonzero. The aligned integer addition
therefore preserves the information needed to choose the correctly rounded
113-bit result.

A positive sum can require at most one normalization shift. That shift also
preserves sticky information. The three low bits then distinguish less than,
exactly, and greater than half an ulp. An exact half-ulp increments the result
only when its retained least-significant bit is odd. Carry from rounding is
renormalized before the bits are packed into the output.

When the exponent separation exceeds 113, the smaller operand is strictly
less than half an ulp of the larger operand, so the larger representable
operand is the correctly rounded answer. Separations at the half-ulp boundary
still go through guard/round/sticky handling.

Zeros, subnormal operands, negative operands, NaNs, infinities, and possible
overflow are delegated to the original compiler/runtime addition. There is no
approximation of small terms at reduced precision: terms that disappear are
exactly those discarded by correctly rounded binary128 addition.

## Checks and deployment

The fixed-seed arithmetic suite includes 12,051,840 cases. It compares the
128-bit representations for 12,051,344 non-NaN results; the other 496 cases
check that both results are NaNs. The structured cases exercise exponent
boundaries, mantissa carries, near-half-ulp rounding, and argument reversal.

The real-graph regression additionally compares complete emitted coefficient
vectors, maximum contributions, and both precision-promotion counters against
the original worker. See `verification/performance/` for the records.

The integer-adder argument is not a substitute for testing a new compiler or
architecture. Run the suite on every deployment architecture. Defining
`C8_REFERENCE_QUAD_ADD` restores the compiler's addition while leaving bounded
graph residency and scratch reuse available. The chosen addition backend is
reported by `--describe`.
