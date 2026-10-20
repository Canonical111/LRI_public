# Deep-cancellation fixture (PLAN.md A-KER-7)

`L3/G0.txt` is a synthetic L = 3 G-file (E = 6), not a graph: three masks of popcount 3 (7, 56, 21) and two terms over
the same three monomials with opposite numerators (+x_0 and -x_0), whose monomial lists are written in opposite orders
(0 1 2 and 2 1 0). The kernel's trie therefore sums U_0 = (m_0 + m_1) + m_2 and U_1 = (m_2 + m_1) + m_0: equal in
exact arithmetic, different in their last bits in every floating format. The forest sum n/U_0^{3/2} - n/U_1^{3/2} is
zero in exact arithmetic and cancels to the rounding level of each tier at every point, so every point fails the
long-double and binary128 tests and reaches the MP tier, where |v|/err is at the rounding level of the format or, as
observed on Expanse for both gmp350 and decimal300 at every sampled point, exactly 0 (log10 = -inf, recorded as
mp_min_log10 "-inf"): below the mp_alarm level -320 either way. The rates are all 1 (0 at the empty and the full subset); the weights 1.5 and 0.25 (s_G = 2) keep
max_abs nonzero.

Used by `tests/point_checks.cpp --deep` (the 450-digit check) and `tests/class_b.py` (the worker's `mp_alarm` with
`--mp-check on` and `stride16`).
