# RECON: the C8(2) HPC package (long-range Ising, d=2, eighth order)

I did not write this to `/Users/zheng/Documents/Agent_LRI/LRI_C8_D2_HPC_loop/RECON.md`, because subagents may not write report files. The full text is returned here.

**Sources.**
- Five recon readers: c7d2-architecture, c8d1-generalization, method-order8-d2, perf-profile and inventory-source. Only perf-profile was saved to disk (`LRI_C8_D2_HPC_loop/recon/perf-profile.md`).
- My own read-only checks:
  - `LRI_C7_D2_HPC/src/kernel.hpp:160-179` and `src/c7d2_integrate.cpp:10,34` (precision tiers and jet arrays);
  - `LRI_C7_D3_HPC/tools/assemble.py:41-57` (d=3 assembly);
  - `LRI_C7_D3_HPC/tools/lanes.py` and `slurm/lane_worker.sh` (lane mode);
  - the symmetry hardware reference in the hpc-clusters skill.
- No heavy runs were made, and no package or the note was edited.

**C8(1) (the user's reference).** `LRI_C8_HPC` gives C8(1) = 8,066,723 ± 8,015 (SE), about 1e-3 relative. It is used here for five things:
- the 9-vertex class inventory (`inputs8/classes8.txt`);
- the 128-bit generator code patterns;
- independent cross-check sets: articulation classes, primitives and the zero-dimensional sum check;
- the assembly generalization pattern (`c8lib.coefficients`, the `affine8` top-loop gate);
- the design and Neyman-allocation machinery (`design8.py`) and the lessons from its review (R01–R26).

It is not a performance reference: it used a d=1 radial scheme, deleted the profiling tools, and ran at low pilot efficiency.

---

## 0. Executive summary

1. **The method is unchanged from C7(2), one order higher.**
   - Same finite zero-momentum scheme and mixed local-mass-forest kernel (note `c7d2:kernel`, `c7d2:normalization`).
   - Loop L carries its Taylor jet through z^(8−L): z^5 at L=3 down to z^0 at L=8.
   - The power sector is integrated explicitly, with Δ_pC8 = F8(f+p) − F8(f).
   - The only new analytic input is the two-loop jet b_{2,6} = −266.52096796135938173225219261908980094902.
2. **The workload is about 7× larger in kernels and about 30× in arithmetic.**
   - There are 24,173 kernels in total (C7: 3,511).
   - Loop 8 has 16,064 power-free kernels (248 primitive) and 4,336 power kernels. Loop 7 grows to 3,150: the s_G=4 classes (143 power-free + 119 power) that C7 skipped must now be integrated, because ∂C8/∂(b7, c7) ∝ (−16A, 42A), not (−1, 3).
   - Σ M·T is 1.46e9 at free L8, against 4.9e7 at C7's free L7.
3. **The inventory is cheap and mostly done.**
   - C8(1)'s `classes8.txt` (26,540 classes) is the d=2 L8 class list; classes1..7 are byte-identical across the packages.
   - Only the d=2 builders need porting: 128-bit keys, 9 vertices, the parity rate rule.
   - A probe port already reproduces the C7 L6/L7 counts and pack sizes exactly.
   - Generation is under 0.5 core-h. The I/O is about 7.5 GB of text packs.
4. **The native code will silently corrupt memory at L=8 unless arrays are resized.**
   - Affected arrays: `std::array<ld,14>` at `kernel.hpp:53,54,132`, `std::array<ld,28> u` at `c7d2_integrate.cpp:52` (31 dimensions needed), and `lx[14]` in `tests/point_checks.cpp:13`.
   - The builders have the same problem: `uint64_t` keys (5,068 of the L8 keys exceed 64 bits), plus `deg[8]` and `p[8]`.
   - Today only the `L>7` guards prevent this.
   - Fix: one `constexpr` LMAX/ORDER that sizes every array, plus `static_assert`s.
5. **The bottleneck is the precision fallback, not orchestration.**
   - C7(2) production split: 31.9% long double, 44.6% binary128, 23.4% gmp350. Orchestration losses were 5.4% in total, mostly the OpenMP block barrier.
   - At L8 a free point is expected to cost about 10× an L7 one (range 6–16×). Binary128 would take about two thirds of the CPU.
6. **Cost at C7(2)-comparable relative precision (1.35e-4, about ±6 absolute) is high.**
   - About 4.4–5.1e5 core-h with today's kernel and Neyman allocation; uncertain by about ×3.
   - About 2–3e5 core-h after the kernel speedups that keep results bitwise identical.
   - That is 1–3 weeks of most of symmetry's AMD partition.
   - 2.5e-4 (±11) costs about 150k today (60–95k optimized). 5e-4 costs about 37k. C8(1)-like 1e-3 costs about 9k.
   - The target is a user decision, best taken after an L8 pilot of 100–300 core-h.
7. **Shared with C63d (C8(3)):**
   - the d=2 L8 kernel files (d=3 derives from them through `regenerate_rates.cpp`);
   - the order-8 assembly (identical except a d/2 offset);
   - the ms8 check polynomial (valid for any d);
   - the decision to integrate the power sector explicitly (no analytic order-8 compensation exists at either d);
   - the precision-tier kernel optimizations (the d=3 `kernel.hpp` has identical tier code);
   - the lane mode (already in `LRI_C7_D3_HPC`).

   Proposed split: section 2.

---

## 1. What the C8(2) package must contain

### 1.1 Method and assembly

**RG structure.**
- β = −zg + Σ_{L=1..8} b̂_L(z) g^(L+1) and γ_r = Σ ĉ_L(z) g^L, with b̂_1=3, ĉ_1=1, ĉ_2=b̂_2/6.
- Δ_E = 1 − ε/2 + γ_r(g*, ε).
- The extraction formula `done:bivariateLagrange` is valid for general n.

**Assembly code change** (`tools/assemble.py:28-43`):
- N=8 becomes 9; `k=8-L` becomes `9-L`; `range(3,8)` becomes `range(3,9)`; shapes `2*(9-L)`.
- The C7(3) function (`LRI_C7_D3_HPC/tools/assemble.py:41-57`) is identical except `ga[0]+=1.5` instead of `+=1`, i.e. ga[0] += d/2. One shared `coefficients(vals, B2, order, half_d)` serves both dimensions.

**Structure, verified by complex step on the C7(2) production means:**
- Every loop's new top slot enters additively: ∂C8/∂(b_{L,8−L}, c_{L,8−L}) = (−1, +3)/3^(L+1) for L=3..8.
  - Loop 8 needs only the zeroth moment of the w_H = 3w_B − w_A weighted kernels.
  - C8(1) used the same rule as a gate (`affine8.py:54`).
- Loop 7 enters with ∂C8/∂(b_{7,0}, c_{7,0}) = (−16A, 42A)/19683, with A = 4 log 2. The ratio is −2.625.
- C8 is affine in loops 5–8 (exact rational second differences vanish) and nonlinear in loops 3–4 (b3³, b4², b3·b6, …).
  - Keep the complex-step Jacobian covariance.
  - The relative SEs of loops 3 and 4 are about 1e-6 and 3e-6, so the nonlinearity bias is far below the noise.

**New check polynomial (constant-coefficient MS, any d, with b2 = −6A_d, c2 = −A_d).** Derived with sympy; it reproduces the C4/C5 formulas, `c6:RGassembly` and `ms7` in `reference/LRI_C7_d2_progress/code/check_assembly.py:55-57`.
```
19683 C8 = 3c8 - b8 + 42A c7 - 16A b7 + 324A^2 c6 - 144A^2 b6 + 3b3 b6 - 6b3 c6 - 3b6 c3
 + 1800A^3 c5 - 960A^3 b5 + 54A b3 b5 - 90A b3 c5 - 54A b5 c3 + 3b4 b5 - 5b4 c5 - 4b5 c4
 + 82368A^7 - 25344A^5 b3 + 28512A^5 c3 - 5280A^4 b4 + 7920A^4 c4 + 1980A^3 b3^2
 - 3960A^3 b3 c3 + 540A^2 b3 b4 - 720A^2 b3 c4 - 540A^2 b4 c3 - (100/3)A b3^3 + 90A b3^2 c3
 + 27A b4^2 - 72A b4 c4 - 5b3^2 b4 + 6b3^2 c4 + 9b3 b4 c3
```

**Expected value.**
- The ratio method gives C8(2) ≈ +46,100 (fits span 45.7k–46.8k); slot extrapolation gives about +42k.
- There is a large cancellation: the part already fixed by C7-level jets is −192,711 ± 8; the new top slots add about +2.35e5. The extrapolated slots are L7 j1 ≈ +8.9e4, L6 j2 ≈ +6.6e4 and L8 j0 ≈ +5.5e4.
- The relative error of C8 is inflated accordingly.

### 1.2 Workload

L8 counts come from the probe port of the builders. They must be confirmed by the generalized builder.

| | L3 | L4 | L5 | L6 | L7 (C7 → C8) | L8 (new) |
|---|---|---|---|---|---|---|
| power-free kernels | 5 | 16 | 76 | 395 | 2,298 → **2,441** (44 primitive; +143 with s_G=4) | **16,064** (248 primitive) |
| power kernels | 1 | 3 | 20 | 107 | 590 → **709** (+119 with s_G=4) | **4,336** |
| jet slots per channel (C8) | 6 | 5 | 4 | 3 | 2 | 1 (only 3c−b is used) |

L8 coverage of all 26,540 classes, each assigned exactly once:

| Category | Classes |
|---|---:|
| zero channel (s_G=4) | 2,254 |
| exact zeros with nonzero channel weight | 3,886 (2,170 free + 1,716 power) |
| primitive | 248 |
| free nonprimitive | 15,816 |
| power | 4,336 |

The exact power-free zeros equal C8(1)'s power-free articulation set exactly: 2,511 at L8 and 454 at L7.

L8 sizes:

| Quantity | free | power |
|---|---|---|
| spanning-tree masks M, mean / max | 2,054 / 4,032 | 1,227 / 2,640 |
| forest terms T, mean / max | 55 / 280 | 52 / 224 |
| largest M·T | 617k | 364k |
| text pack | ~6.1 GB | ~1.4 GB |

- A text G-file is about 380 KB: 197 KB of 2^16-entry rate table, 173 KB of term bases, 12 KB of masks.
- In-kernel memory is about 3–4 MB per graph (alpha, dp and choice_total, each 2^16 entries in long double).
- A 1,024-graph block needs about 3–4 GB per lane.

### 1.3 Components and the changes from C7(2)

The package should be a new repository, `LRI_C8_D2_HPC`, created as a branch from `LRI_C7_D2_HPC@a55958f`. Its review base commit should be "C7(2) package + d=2 L8 inventory", which keeps the Codex diff focused, as C8(1) did.

**A. `gen/`: inventory generator (new to the package)**
- Port `reference/LRI_C7_d2_progress/code/build_schwinger.cpp`, `reference/power_mass/code/build_power_mass.cpp` and `power_mass/code/check_edge_forests.cpp`:
  - `unsigned __int128` keys with the checked decimal `readu128` / `u128s` from `LRI_C8_HPC/gen/build_coordinate_forests.cpp`;
  - `deg[9]`, `p[9]`, `adj/seen/low[9]`; 36 vertex pairs;
  - `num_threads(4)` replaced by the OpenMP default;
  - the free builder's rate rule (line 28) switched to the parity floor `max(|S| odd ? 1 : 2, twice)/2`. This reproduces the frozen L7 free rates (`verification/parity_rate_update.json`); the generic rule does not.
- Keep the magic `C7D2GRAPH1` and the text format: the format does not depend on order, and keeping it keeps L3–L7 byte-identical.
- Input: `LRI_C8_HPC/inputs8/classes8.txt` (sha256 `7ff5c278…f57e`).
- Independent cross-checks:
  - `LRI_C8_HPC/gen/zero_dim_check.py`, which does not depend on d;
  - `inputs8/L8_inventory.txt` metadata (D_G, s_G, log/power subgraph masks) against the builder's JSON;
  - zeros against `inputs8/verification/forest_subsets.json`;
  - the 248 primitives;
  - Fraction Kirchhoff checks on a sample (`validate_kernels.py` / `validate_kirchhoff.py` patterns, range 3..8);
  - `check_edge_forests` at n=9 on all 7,231 L8 power classes.
- The free L≤6 rates are legacy tables (`LRI_C6_D2_HPC`, relabelled through `legacy_mapping.json`) and cannot be regenerated. Reuse those files byte for byte.

**B. `inputs/`**
- Packs:
  - free and power L3–L6 reused byte for byte;
  - L7 rebuilt to include the 262 s_G=4 kernels (the G-files already exist in `reference/LRI_C7_d2_progress/inputs/L7`, 2,441 files, and `reference/power_mass/inputs/L7`, 709 files);
  - L8 new.
- `gamma_d2_8.txt`:
  - rows L=2..8, label 8−L;
  - norm 2(−1)^(L+1)/π^L (L=8: −2.107807833069873e−4);
  - 6 log values per row, ℓ_j = [(L/2)^j ψ_{j−1}(1) − 2L·4^−j ψ_{j−1}(1/2)]/j!. Five used values suffice for K ≤ 5.
- `two_loop.json` with 7 entries (z^0..z^6). The new b_{2,6} comes from Cauchy contours at radii 0.05 and 0.08 (64 and 80 nodes, 60 digits). The two agree to 1.9e-53 and reproduce the existing 6 entries to ≤1e-54.
  - The generator change is `prepare.py:20`, `range(1,7)` → `range(1,8)`.
  - The test should assert the two-contour agreement.
- `inventory.json` and `manifest.json`:
  - schema `c8-d2-hpc-inputs-1`, order 8, `range(3,9)`;
  - the s_G=4 skip only at L=8 (`prepare_inputs.py:36`);
  - cost proxy: consider `addends.size()`, which the kernel already uses for in-block ordering.
- A frozen design bundle replaces `allocation.json`, `production_plan.json` and `primitive_allocation_c7d2.json`:
  - per-graph Neyman counts for all strata, taken from an independent pilot;
  - the 248 L8 primitives included in it;
  - gradient SCALE 3^9 = 19683;
  - "retained" primitive mode dropped (there is no L8 archive).
- Reference values:
  - C3–C5 exact;
  - C6(2) = 362.36647176375726 ± 0.00080;
  - C7(2) = −3876.1260927949925 ± 0.5244496690956952 (new pull row).

**C. `src/`: native kernel**
- Constants: `constexpr LMAX=8, ORDER=8, EMAX=2*LMAX, KMAX=ORDER-3, DIMMAX=4*LMAX-1`, with `static_assert`s.
- Resize:
  - `kernel.hpp:53` (x, xs, lx, lt), `:54` (order) and `:132` (`PromotedScratch`) to EMAX;
  - `c7d2_integrate.cpp:52` u to ≥ 31;
  - `tests/point_checks.cpp:13` to 16.
- Guards: L ≤ 8 at `kernel.hpp:101` and `c7d2_integrate.cpp:25`.
- `c7d2_integrate.cpp:34`: `K=8-L`, gamma loop l=2..8, `kl!=8-l`.
- `--describe`: order 8 and new schemas, which `production.py:266,415` check.
- `Row::value[12]` and `std::array<ld,6>` jets already suffice, since 2(9−L) ≤ 12 and K ≤ 5. The c8d1 reader's "14/7" is not needed. Still derive them from the constants.
- Header limits M ≤ 16384 and T ≤ 10000 are fine (L8 maxima 4,032 and 280).
- Parallelize graph loading with OpenMP over graphs. It is deterministic because graphs are independent, and when done by each lane's own threads it also fixes NUMA first-touch.
- **Keep:** thresholds 1e-9 / 1e-23 (`kernel.hpp:162-163`), the backends gmp_float<350> and cpp_dec_float<300>, rates 0.8 / 0.9, layout 0, the stream-mixing constants and the task format.

**D. `tools/` and `slurm/`: orchestration**
- `production.py`:
  - 24 groups (2 campaigns × 2 sectors × L3..8);
  - seed prefix `c8-d2|`;
  - a registry that forbids the C7(2) 2026 seeds and all pilot seeds;
  - jet width `2*(9-L)` at `:422,567`;
  - the L8 primitives are top-loop strata; the L7 primitives become ordinary strata;
  - **chunking by cost** instead of a fixed `--chunk-points` (`:291`), targeting a maximum task time of 30–120 s (C8(1) R26);
  - campaign tag `c8:`.
- **Lane mode:** port `LRI_C7_D3_HPC/tools/lanes.py` and `slurm/lane_worker.sh`. They provide whole-node jobs, heaviest-first claims through no-clobber hard links, deadline-aware skips (est/(T·0.9)·1.5 + 300 s), failure records and stale-claim release. Add NUMA-bound lane shapes; 8×8 on AMD with NPS=4 is the candidate.
- Per-group parallel merge, as the production's external `sym_merge.slurm` did.
- `run_array.sh`: whole-node memory (`--mem=245G` on amdq) instead of 4G.
- `slurm_submit.py` and `common.py`: renames only.
- New `tools/design.py`, ported from C8(1) `design8.py`:
  - per-graph σ² projected on the C8 row;
  - a σ floor of 3% of the median;
  - a per-graph floor of **at least 4,096 points**, against the replicate skew C8(1) saw at 64 points;
  - powers of two;
  - group multiplier split into replicates (r ≤ 128) and a sample multiplier;
  - an integer budget gate from `sacct`, including retries;
  - atomic bundle publication.
- `assemble.py` additions:
  - the order-8 path;
  - top-slot rule gate (hard failure);
  - affinity gate;
  - ms8 check rows;
  - pulls C3..C7;
  - Δ_p null tests at orders 3..7, with order 8 reported;
  - partial vs final combination (C8(1) R23).
- Keep the profiling and benchmark tools; C8(1) deleted them and should not be copied here.

**E. `tests/`**
- C7-vs-C8 bitwise replay at L3..L7:
  - The kernel decides promotion on the integrand value before the jets are formed (`kernel.hpp:160-163` vs `:175-179`). So jet slots 0..7−L in both channels must be **bitwise equal** to the C7 binary's.
  - The test must account for the c-channel offset moving from 8−L to 9−L.
  - The c8d1 concern about "promotion on the maximum over slots" does not apply to this kernel.
- At L8 there is no reference worker, so the checks are:
  - 450-digit point checks (scaled error < 1e-280);
  - forced binary128 and forced gmp350 comparisons on a sample of graphs;
  - kernel regeneration gates.
- Thread invariance at 64, 16 and 8×8 lanes.
- `unit_orchestration.py` updated: 24 groups, 248 primitives, net dimension 31.
- `check_inputs.py`: byte-identical regeneration of the inputs.
- `compat`: the C7(2) 2026 production reassembled through the order-7 path.
- Assembly regressions:
  - the order-7 function is bitwise equal to the delivered one;
  - at order 8 the function agrees with an independent exact-rational Lagrange inversion.
- A fake-integrator end-to-end test and an AST scan for unreachable code after a raise (C8(1) R22/R25).

**F. Docs**
- README and CHANGELOG from day one; C8(1) never updated its CHANGELOG.
- PERFORMANCE with measured L8 numbers. Today's says "supported through seven loops only".
- HPC documentation for symmetry lanes.

### 1.4 Where the readers disagree, and what this RECON adopts

| Point | Readers | Adopted |
|---|---|---|
| Number of L8 power kernels | ~3.6–3.9k (perf extrapolation), ~4.3k (ratio), 4,336 (probe port reproducing C7 L6/L7 exactly; matches method-order8-d2) | 4,336, provisional until the generalized builder confirms it |
| Jet array sizes | 12/6 enough (c7d2-architecture) vs 14/7 needed (c8d1) | 12/6 suffice; size from constants anyway |
| Staging cache per job | Recommended (c7d2-architecture) | Low priority: staging plus Python was 0.09% at L7, and L8 blocks are longer. Measure first. |
| Cost at ~1e-4 relative | ~1e5 core-h (method-order8-d2) vs ~5.1e5 (perf-profile) | The 1e5 figure omits the ×230 growth of the top-loop metric. My independent slot-level check gives 4.4e5 (section 4). |

---

## 2. Shared with C63d's C8(3) work, and a proposed split

**Inventory.**
- The combinatorics, polynomials and weights do not depend on d; only the rate line does.
- `LRI_C7_D3_HPC` built its kernels from the d=2 G-files with `reference/src/regenerate_rates.cpp`: quarter-unit rates 3|S|+4ν−6h with a mod-4 floor. It works for any E; only the magic string and `num_threads(3)` are hard-coded.
- d=3 also lacks the L7 s_G=4 kernels (its inputs hold 2,298 + 590), so C63d needs the same +262 kernels at L7.

**Assembly.**
- Identical apart from ga[0] += d/2 and the d-specific B2 jet. C63d needs its own 7th two-loop coefficient.
- The ms8 polynomial, the top-slot rule (−1, +3)/3^(L+1) and the loop-7 entry (−16A_d, 42A_d)/19683 hold at any d.

**Power-sector compensation.**
- No analytic compensation exists at order 8 for either d. `app:C6d2Complete` / `app:C6d3Complete` are sixth-order MS constructions; C7(2) and C7(3) both integrated explicitly.
- The finite-scheme null tests are consistent with zero at orders 4–7. The MS C6 tests give 1e-34 at d=2 and 1e-89 at d=3.
- A cancellation is plausible but not proven, and the parts do not cancel slot by slot. Both packages should keep explicit integration and report Δ_p, not use it.

**Kernel.**
- The d=3 `kernel.hpp` (183 lines) has the identical tier structure: `calculate_shared` at `:143`, the 1e-9 / 1e-23 thresholds at `:166`, gmp_float<350> / cpp_dec_float<300>.
- The array-size fixes and the binary128 and MP tier optimizations are the same patches.

**Proposed split:**

| Item | Owner | Consumer and handoff |
|---|---|---|
| Generalized d=2 builders (128-bit, n=9, parity rule), `check_edge_forests` at n=9, L3–L7 regression, L8 generation on symmetry, all inventory gates | **C82d** (this package) | Publishes a frozen, hashed `inventory8_d2/` (G-files, inventory.json, SHA256SUMS). C63d pins the hash. |
| `regenerate_rates.cpp` for L8 (magic string, threads), d=3 rate audit and `check_dimension.py` at L8 | **C63d** | Consumes the C82d hash. |
| Pack format decision (keep text, or add a lossless binary pack with a round-trip test) | Joint; C82d proposes | Both packages use the same format. |
| `order8_assembly.py`: `coefficients(vals, B2, order, half_d)`, exact-rational Lagrange cross-check, ms8 rows, top-slot and affinity gates, order-7 regressions against both delivered functions | **C82d** writes, **C63d** reviews | Vendored byte-identically, with the hash pinned in both manifests. |
| 7th two-loop coefficient | Each for its own d | — |
| Power-sector protocol: Δ_p = F8(f+p) − F8(f), null rows at orders 3–7, reporting rule | Joint text, one owner (C63d, which has the d=3 analytic MS history) | Both. |
| Lane mode | Already in `LRI_C7_D3_HPC` | C82d ports it. |
| Tier optimizations R3a (binary128) and R4a (MP allocations) | Whoever lands first | The other applies the patch; each package proves bitwise replay independently. |
| Pilot-to-Neyman design tool (`design8` port) | **C82d** | C63d reuses it. |
| amdq scheduling | Joint | Both campaigns compete for 29 amdq nodes. Agree windows before production. |

---

## 3. Performance profile and ranked optimization plan

### 3.1 Where the C7(2) production time went

Run: symmetry `run1-20260930-m4096`, 28 whole-node jobs, 6.64 h, 2,048 checkpoints, 1.28M task rows.

**Accounting:** 9,416 core-h allocated; 8,892 task core-h (94.4%).

| Loss | Share of allocation |
|---|---:|
| OpenMP barrier and imbalance | 5.0% |
| serial graph load | 0.27% |
| Python and staging | 0.09% |
| lane tail | 0.18% |

**Tier split** (non-negative least squares per graph, R² = 0.998):

| Tier | Share of CPU | Cost relative to a first-pass evaluation |
|---|---:|---:|
| long double | 31.9% | 1× |
| binary128 | 44.6% | ~10× |
| gmp350 | 23.4% | ~55× |

**By part:**

| Part | Share of CPU | µs per point | quad / MP promotion |
|---|---:|---:|---|
| power L7 | 48.3% | 122.6 | 57.4% / 4.47% |
| free L7, non-primitive | 23.2% | 56.4 | 16.1% / 0.73% |
| free L7, primitives | 14.4% | 12.2 | 0 |

- Free graphs "switch on" the fallbacks between L6 and L7: quad promotion ×150, cost per point ×9.2.
- Within L7, quad promotion rises from 5% to 51–58% across graph-size quintiles. The mean L8 graph is larger than the largest L7 graphs.

**Variance versus CPU:**
- Free L7 carries 97.8% of Var(C7).
- Power took 59.9% of the CPU for 0.76% of the variance.
- The primitives took 14.4% of the CPU for 7e-5 of the variance.

**Randomized QMC** converges at α ≈ 0.53, essentially Monte Carlo. The edge-ordering choice in `sample()` (`kernel.hpp:168-170`) is a step function of u, so the integrand is discontinuous. Monte Carlo scaling is the right planning model.

**Lane width:**
- AMD 64-thread lanes ran at 0.915–0.95 OpenMP efficiency; power L6 only 0.856. Intel 20-thread lanes ran at 0.99.
- The AMD nodes are NPS=4 with 8 NUMA domains. The master thread loads every graph (`c7d2_integrate.cpp:36`), so first touch puts all tables in one domain.

### 3.2 Projections to L8

**Cost per point, free non-primitive.** Per-evaluation fit at the L8 mean size of about 31k operations: first pass ~61 µs, binary128 ~720 µs, gmp350 ~2.7 ms.

| Scenario | quad / MP promotion | µs per point | vs L7 | base / quad / MP time |
|---|---|---:|---:|---|
| optimistic | 30% / 1.5% | ~320 | ×5.7 | 19 / 68 / 13 |
| **central** | 55% / 4.5% | **~580** | **×10.3** | **10 / 68 / 21** |
| pessimistic | 75% / 10% | ~880 | ×15.6 | 7 / 62 / 31 |

Power L8 is expected at about 400–750 µs per point.

**Growth of the top-loop metric (relative variance × core-h at the Neyman optimum) from L7 to L8:**

| Factor | Central | Range |
|---|---:|---|
| graphs², N² | ×45 | ×42–49 |
| cost per point, κ | ×10.3 | ×5.7–15.6 |
| per-graph relative variance, σ² | ×0.5 | ×0.25–0.85 |
| **Product** | **≈ ×230** | **×60–650** |

### 3.3 Ranked changes (gain at L8)

"Bitwise" means the change must pass the exact replay gate (`validate --full`, both backends) and the thread-identity check. Items marked FLAG change numerics and need explicit user approval plus validation.

| # | Change | Evidence | Expected gain | Numerics |
|---|---|---|---|---|
| R1 | Use the existing recipe: power divisor (16), Neyman primitives (512 points) | Power 59.9% of CPU for 0.76% of variance | ×3.0 at fixed SE | None per stratum |
| R2 | Per-graph Neyman for every stratum, frozen from an independent pilot (powers of two, ≥4,096 points per graph) | Production per-graph variances: free L7 ×1.46 (non-primitive) / ×2.33 (all); power L7 ×1.97 | ×1.4–1.9 on top of R1 (5–10% optimistic) | Allocation only |
| R3a | Faster binary128 +, −, ×, ÷ that stay correctly rounded (inlined 64-bit-limb code, or SLEEF quad after proving correct rounding); interleave 2–4 promoted points; keep libquadmath `expq` | 19 ns per op, plus ~27 µs per evaluation in 2E `expq` (`kernel.hpp:143-144`) | ×1.3–1.7 overall | Bitwise if correctly rounded; must be demonstrated |
| R4a | gmp350 tier: preallocated `mpf_t`, in-place operations, no temporaries | 0.53–0.69 ms fixed cost per MP evaluation; <5% of points but 23% of CPU | Part of ×1.15–1.25 | Probably bitwise (same precision); verify |
| R5 | NUMA-bound lanes (8×8 on AMD), cost-based chunking (30–120 s tasks), lane-parallel graph loading | 64-thread lanes 0.856–0.95; 5% barrier loss | ×1.05 | Neutral |
| R6 | Evaluate 2–4 points in lock-step in `calculate_products` to break the serial x87 addition chains | 1.44 ns per addend fits latency-bound chains (confirm IPC); ~27.5k addends per point at L8 | ×1.03–1.1 | Interleaving bitwise; a max-plus shift would be FLAG (~1e-19 relative) |
| R3b | Double-double (106 bits, AVX2/FMA) instead of binary128, with the 1e-23 test retuned | — | Tier ×4–8 | **FLAG** |
| R4b | Staged 256-bit tier with a ratio test, escalating to 350 digits only on failure | — | — | **FLAG**: precision-policy change |
| R4c | One exponential instead of E (`xs_j = x_j·exp(−shift/L)`) | — | — | **FLAG**: rounding at 1e-34 / 1e-350 |
| R4d | Non-string MP → long double conversion (Boost 1.77) | — | — | **FLAG**: ~1 ulp of long double |
| R7 | Rate per sector or per graph from the pilot | Rate 0.9 is 9% (free) / 20% (power) cheaper per point for +4% SE | ×1.0–1.15 | **FLAG**: integrand changes; still unbiased |
| R8 | Route promotion-heavy work to AMD | Intel 6148 is 1.32–1.40× slower on power | A few % | Neutral |
| R9 | Better QMC nets | α ≈ 0.53, discontinuous integrand | ~×1 | FLAG (new streams) |

- **Not recommended:** lowering the 1e-9 / 1e-23 thresholds (a silent precision cut, which the rules forbid), or a SIMD double first pass (it loses 11 bits and causes more promotions).
- **Order:** R1+R2 → R5 → R3a → R4a → R6. FLAG items only after user approval and replay-gate evidence.
- Unflagged kernel work (R3a, R4a, R5, R6) is expected to give ÷1.6–2.5 overall. R3b would roughly double that and is the largest single numerics decision to put to the user.

### 3.4 Profiling before optimizing (amddebugq, ≤1 h each, one node)

1. `perf record -g` on one free-L7 and one power-L7 1,024-task block at 64 threads, gmp build. This splits the time between `__addtf3/__multf3/__divtf3`, `expq`, `mpf_*`, malloc, `expl`, the string conversion, `calculate_reference<ld>` (`kernel.hpp:108`) and the shift loop (`:158`).
2. `perf stat` (IPC, x87 uops, cache misses) on a primitive-only block, to confirm the first pass is latency-bound.
3. A diagnostic build that histograms log10(|q|/err) for points that fail the quad test, to size R4b if it is ever approved.
4. A lane-shape test: 1×64, 2×32, 4×16, 8×8, NUMA-bound.
5. After stage 1: repeat 1 and 4 on L8 blocks; measure L8 promotion rates and µs per point per graph. This replaces the ×5.7–15.6 range.

---

## 4. Cost estimate (core-hours) for C8(2)

All figures use |C8| ≈ 4.6e4, so C7(2)'s relative precision of 1.35e-4 means an absolute SE of about 6.2.

**Method A (perf-profile).**
- Start from the free L7 non-primitive Neyman-optimal metric, 2.71e-5 core-h × relative variance.
- Multiply by ×230 for L8 and by ×1.5 for everything else (power at divisor 16, L7 with K=1, lower loops, primitives).

**Method B (independent cross-check, using method-order8-d2 slot data).**
- At C7(2) production samples, loop 7 alone would give C8 an SE of about 13.6: about 8.0 through (b7, c7) at j0 and about 11 from the new j1 slot, combined in quadrature. That sample cost about 1,550 core-h with Neyman allocation, so M7 ≈ 2.9e5 core-h × SE².
- L8 top slot: the C7 L7 top slot had relative SE 9.8e-5 for 1,415 Neyman core-h. Apply ×230 and a slot magnitude of about 5.5e4, giving M8 ≈ 9.4e6 core-h × SE².
- Optimal split: cost = (√M7 + √M8)²/SE² = 1.30e7/SE². At SE 6.2 that is 3.4e5 core-h, or about 4.4e5 with ×1.3 for power and lower loops. About 85% goes to L8.
- Methods A and B agree.

| Target relative SE | Absolute SE | Today's kernel, R1+R2 (central; range ×÷3) | With unflagged kernel work (÷1.6–2.5) | Wall on 16 amdq nodes (1,024 cores), today / optimized |
|---:|---:|---:|---:|---:|
| 1.0e-3 (C8(1)-like) | ~45 | ~9k | 4–6k | 0.4 d / 0.2 d |
| 5.0e-4 | ~22 | ~37k | 15–23k | 1.5 d / 0.8 d |
| 2.5e-4 (4-SE allowance ≈ 0.1%) | ~11 | ~150k | 60–95k | 6 d / 3 d |
| **1.35e-4 (C7(2)-comparable)** | **~6** | **~4.4–5.1e5** (1.3e5–1.5e6) | **~2–3e5** | **18–21 d / 8–13 d** |

**Overheads and capacity:**
- An L8 pilot that meets the 4,096-point floor costs about 11 core-h per replicate per campaign for free L8 at the central cost, so about 100–300 core-h with R=8. Development, profiling and validation add about 1–2k core-h.
- Budget a 1.5× margin: C8(1)'s realized per-batch SE was 1.56× its pilot prediction.
- Symmetry has 29 amdq nodes (1,856 cores, 24 h wall, at most 16 nodes per job). Single-node lane jobs avoid the per-job cap; C7(2) ran 28 at once (14 AMD + 14 Intel).
- Sustained 1,500–2,000 cores would shorten these walls by 1.5–2×, but would compete with C63d.

**Recommendation.** C7(2)-comparable precision is feasible only with R1–R6 and roughly two weeks of most of symmetry's AMD nodes. Plan for 2.5e-4 by default, and decide the final target after the L8 pilot pins κ and σ² (today's uncertainty is ×3).

---

## 5. Risks and open questions

**Correctness risks**
1. **Silent stack overflows** if the L guards are lifted before the arrays are resized (`kernel.hpp:53,54,132`; `c7d2_integrate.cpp:52`; `point_checks.cpp:13`). Mitigation: constants plus `static_assert`, and an ASan/UBSan build in CI.
2. **Silent garbage in the builders on 72-bit keys:** `f>>r.key` sets failbit, and every later read fails too. Mitigation: a checked `readu128`, a check that rows read equals NG, and a regression proving L1–L7 byte-identical.
3. **L7 rate provenance:** free L7 needs the parity rule, and free L≤6 rates are legacy and cannot be regenerated. Mitigation: reuse those files byte for byte, and regression-compare the parity-rule L7 rate lines.
4. **L8 importance-rate adequacy:** an infinite-variance tail would not show in the mean. The margin of +1/2 per power face is independent of h, which argues for finite variance. Mitigation: pilot tail diagnostics (kurtosis, largest-weight share), half-stream and campaign comparisons.
5. **Pilot skew at low points per graph** (C8(1): about 4σ low at 64 points). Mitigation: a floor of at least 4,096 points per graph in the pilot and in production; the pilot never enters the estimate; pilot seeds forbidden in production.
6. **Power-sector cancellation is unproven.** Integrate explicitly; report Δ_p at orders 3–8.
7. **Nonlinearity in loops 3–4:** the bias is negligible at relative SEs around 1e-6. Keep the complex-step covariance and a bootstrap check.
8. **MP-tier conversion and rounding** under Boost 1.77: replay-gate tolerances are decimal backend exact, gmp equal when mp=0 and ≤1e-30 otherwise. Any R4 change must keep these or be flagged.

**Performance and operational risks**
9. **The promotion rate at L8 may be pessimistic** (75% / 10%), which adds ×1.5 to cost. Only the pilot resolves this.
10. **Memory:** the default `--mem=4G` in `slurm/run_array.sh:6` runs out at L8 (about 3–4 GB per lane block). Use whole nodes, `--mem=245G`.
11. **Packs of ~7.5 GB of text,** plus about 9 GB more at d=3. Hashing only the staged graphs of each block is affordable. Decide jointly with C63d whether a binary pack (rates as uint8, bases as bitsets; ~10× smaller) is worth a new format and its round-trip test.
12. **24 h wall:** tasks must be bounded by cost, and lanes must skip indices that do not fit, which the lanes.py deadline logic already does.
13. **Contention for amdq with C63d,** and amdq saturation (58 pending on 2026-09-15). Per the user rule: amdq first, then defq/preq (with requeue); longq only if strictly necessary.
14. **Bootstrap and merge scale:** about 1M task rows per L8 group. Merge groups in parallel, and keep the bootstrap memory bounded (C8(1) R24).

**Open questions for the user**
- **(a) Target precision** (section 4 table).
- **(b) Approval of FLAG numerics changes,** above all R3b (double-double tier) and R4b (staged MP), which could make C7(2)-level precision realistic.
- **(c) Expanse as overflow capacity?** The brief says symmetry.
- **(d) Pack format** (text vs binary).
- **(e) Generator ownership and amdq windows** with C63d.
- **(f) Confirm dropping the "retained" primitive mode,** and treating the L7 primitives as ordinary strata.
- **(g) Should the order-8 power correction be published as a result or only as a check?**

---

## 6. Staged plan

Each stage ends at a hard gate. All numerics beyond quick checks run on symmetry through Slurm, never on the Mac.

**Stage 0: setup (no compute)**
- Create `LRI_C8_D2_HPC` from `LRI_C7_D2_HPC@a55958f` as branch `c8`.
- Start the CHANGELOG and README.
- Pin `classes8.txt` by sha256.
- Agree the section-2 split with C63d.

**Stage 1: inventory (C82d owns; C63d consumes)**
- Port the three builders (section 1.3 A).
- Local regression on L3–L7 (seconds): polynomial parts byte-identical in both sectors; L7 free parity-rule rates and all power rates byte-identical; free L≤6 rates reused.
- One amdq or sharedq job for L8: under 0.5 core-h, about 8 GB on disk.
- **Gates:**
  - Σw_A = 49985915/768 and Σw_B = 33994099/6912 (`zero_dim_check.py`);
  - power-free zeros equal the C8(1) power-free articulation set (2,511);
  - 248 primitives;
  - 16,064 free and 4,336 power kernels at L8, and all 26,540 classes assigned exactly once;
  - builder metadata equal to `inputs8/L8_inventory.txt`;
  - Fraction Kirchhoff sample;
  - `check_edge_forests` at n=9 on all 7,231 power classes.
- Publish the hashed `inventory8_d2/`.

**Stage 2: assembly and low-loop inputs**
- `order8_assembly.py` (shared).
- `two_loop.json` with 7 entries (two-contour test) and `gamma_d2_8.txt`.
- **Gates:**
  - order-7 path bitwise equal to the delivered d=2 and d=3 functions;
  - order-8 equal to an independent exact-rational Lagrange inversion;
  - top-slot rule (−1, +3)/3^(L+1) and the L7 (−16A, 42A)/19683 gate;
  - affinity in loops ≥ 5;
  - ms8 reproduces C4–C6 and `ms7`;
  - C7(2) production reassembled unchanged.

**Stage 3: kernel and orchestration generalization (section 1.3 C–E)**
- Constants and resized arrays, K=8−L, gamma 2..8, schemas.
- 24 groups, cost-based chunking, lane-mode port, parallel graph load, whole-node memory, `design.py`, updated tests.
- **Gates:**
  - C7-vs-C8 bitwise replay of the common slots at L3–L7 (both backends);
  - L8 450-digit point checks and forced-tier comparisons;
  - thread invariance;
  - fake-worker and fake-Slurm end-to-end;
  - ASan/UBSan clean at L8.
- Optional early Codex review of the C7→C8 diff here, before any pilot compute.

**Stage 4: profile, then pilot**
- Section 3.4 profiles 1–4 on amddebugq; then L8 block profiles.
- Independent-seed pilot over all 24 groups (100–300 core-h).
- Freeze the Neyman design bundle with a 1.5× margin.
- Present cost against target to the user and get the decision on (a) and (b).
- Run the design tool on real pilot output before the final review (C8(1) lesson 3.2).

**Stage 5: optimization, in rank order**
- R1+R2 (allocation), then R5 (lanes and chunking), then R3a (binary128), then R4a (MP), then R6 (interleaving). FLAG items only if approved.
- **Gate per change:** full replay gate, thread identity, and a measured speedup on amddebugq against the stage-4 baseline. A change that fails replay is reverted.

**Stage 6: validation on symmetry**
- An end-to-end mini-campaign through plan → lanes → merge → assemble on amdq, a few nodes for a few hours with all 24 groups.
- Check `sacct` efficiency ≥ 0.9 per group.
- Lower-order pulls C3–C7 at their expected sizes; Δ_p null rows at orders 3–7; half-stream and campaign comparisons.
- A refreshed cost model from measured L8 rows (`calibration.json`).
- Write PERFORMANCE and HPC docs.

**Stage 7: Codex review**
- Run claudex-loop with `--model gpt-6-astra --effort xhigh` on the focused diff from the review base, as a worktree with one commit per round (the C8(1) pattern).
- Fix rounds until approved; record which last fixes were not inspected.
- Production only after explicit user authorisation of the target precision, budget and node windows.
---

## Errata and additions (2026-10-03, after C63d's note `assembly/NOTE_C63d_to_C62d_2026-10-03b.md`)

**Accepted corrections from C63d.**
- (a) Method B normalization. The L7 top-slot SE of 9.8e-5 is relative to |C_L|. Relative to the slot it is 9.72e-5
  of |D_{7,0}(2)|, while relative to |C7(2)| it is 1.34e-4. With one normalization, M8(2) ≈ 1.23e7 (not 9.4e6), and
  Method B's cost at fixed SE grows ×1.26 (1.30e7 → 1.63e7 /SE²). The §4 table should be read with that factor on
  Method B. Method A is unaffected.
- (b) The L8 power maxima (M 2,640, T 224, M·T 364k) are over all 4,891 finite power kernels. Over the 4,336
  integrated ones they are 2,272, 192 and 313k.
- (c) L8 class keys need at most 69 bits, not 72. 72 bits is the capacity for 2 × 36 pairs.
- (d) The ×484 = ×34·×21·×0.83 decomposition leaves a residual of ×0.82: the 6.88 → 145 µs figures are unweighted
  per-graph means, not (mean √c)², so ×21 overstates the metric-consistent κ(L6→L7).
- **Quadrature.** The L7 contributions of 8.0 and 11 (§4 Method B) are strongly anti-correlated (c ≈ −0.93), so the
  L7 variance is ≈21, not 185 (×8.7 smaller).

The L8 pilot replaces all these estimates (decision D-target).

**Heavy-tail check on C7(2) run1** (C63d's suggestion; `recon/tailcheck.py`, `recon/tailcheck_c7d2.json`).
- Method: the per-graph tail index is estimated by a GEV fit to the replicate maxima of `max_abs` (64 replicates per
  campaign). A graph is flagged when ξ > 0.42 in both campaigns.
- Results:

  | Group | Flagged graphs | Note |
  |---|---|---|
  | power L7 | 0 / 590 | single-campaign maxima reach ξ ≈ 0.8, never for the same graph in both campaigns, consistent with fit noise at n = 64 |
  | free L7 | 0 / 2,298 | |
  | power L6 | 0 / 86 | |
  | free L6 | 1 / 367 | 0.52% of that group's variance |

- At d=2 there are far fewer heavy tails than C63d's 27/590 power-L7 graphs at d=3, as expected from the 1/2 margin.
  C63d's exact estimator may differ from this GEV fit.
