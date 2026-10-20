# 1D cross-check at Δσ = 0.15, 0.175: is it already nuisance-aware? (exploratory, existing records only)

Exploratory check, existing 1D records only (NOT a protocol decision; FIT_MODEL_V3 and the 1D report are unchanged)..

Script sha256 b897390a2334…, select_model.py 6f366196e94d…, 2026-09-30_20:24:44. Recorded per-draw crossing values reproduced to < 1e-12.

| Δσ | series | ω′ central (per-draw 16/50/84 %) | σ crossing, ω′ per draw | σ crossing, fixed ω′ | ratio |
|---|---|---|---|---|---|
| 0.15 | xc0.45_star | 0.32 (0.31/0.32/0.32) | 0.00067 | 0.00061 | 1.10 |
| 0.15 | xc0.45_plus | 0.31 (0.30/0.31/0.32) | 0.00080 | 0.00067 | 1.19 |
| 0.175 | xc0.6_star | 0.27 (0.26/0.27/0.27) | 0.00081 | 0.00070 | 1.16 |
| 0.175 | xc0.6_plus | 0.27 (0.26/0.27/0.27) | 0.00085 | 0.00072 | 1.18 |

| Δσ | fit − crossing | σ(global fit) | σ_D (recorded: ω′ per draw) → z | σ_D with fixed ω′ → z |
|---|---|---|---|---|
| 0.15 | +0.00143 | 0.00041 | 0.00068 → +2.10 | 0.00062 → +2.30 |
| 0.175 | +0.00155 | 0.00035 | 0.00078 → +2.00 | 0.00067 → +2.30 |
