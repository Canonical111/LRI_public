# Reviews of lri_2d_window_indep (summary)

No Codex review. The check's independence rests on how it was written: the model was implemented from the method
description alone, without importing or reading the production code, with different numerics (README). It is not blind:
the writer was the Claude Code session that had ported the production package. Its
self-tests (`test_indep.py`) check the vertices against a brute-force Fock-space construction at N = 5 and the eigen-
solver against dense diagonalization; it then reproduced the production record at Δσ = 0.25, N = 8 to 4e-14 before the
cluster runs.

What the coordinator verified: the agreement is limited by the independent zero-mode truncation K, not by either code
(the differences fall with K: at N = 16, Δσ = 0.125, 6e-9 at K = 24 against 1e-12 at K ≥ 32; at N = 22, K = 32 they
grow about 9× per step with one sign); re-tuning from shifted seeds returns to the production root.

Overruled recommendations: none.
