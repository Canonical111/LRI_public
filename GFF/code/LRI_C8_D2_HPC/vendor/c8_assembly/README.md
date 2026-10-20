# LRI_C8_shared/assembly: the eighth-order assembly (shared item (b))

- **Owner:** session C63d. **Checker:** C62d.
- **Date:** 2026-10-03.
- **Scope:** the general-d order-8 assembly used by LRI_C8_D3_HPC and LRI_C8_D2_HPC (vendored byte-identically, hash
  pinned), its exact checks, the order-8 low-loop inputs and the power-sector protocol.
- **Unchanged:** `NOTE_C63d_to_C62d_2026-10-03.md` is left as it was.

Markers: [V] means verified here by the code in this folder; [R] means read in the cited source; [I] means inferred,
not verified. `N:` is a line of
`GFF/LRI_condensed_note/long_range_ising_condensed.tex` (md5 85f9a1ec039543e2d7ea70654a1aac10).
Line citations into files outside this folder (`LRI_C8_D3_HPC_loop/RECON.md`, `LRI_C8_D2_HPC_loop/RECON.md` and
`PLAN.md`) refer to the versions read when each item was written. Those files keep changing, so a cited line may
have moved; the cited content is what counts.

## Contents and md5

| File | md5 | What it is |
|---|---|---|
| `order8_assembly.py` | `bdf84d47f24976732ce9e87dea26e7e5` | `coefficients(vals, B2, order, half_d)` (order 7 or 8, half_d = d/2; float, complex or exact object/Fraction mode); `jacobians` (complex step, as delivered; float B2 only); `campaign_moments` (exactly two campaigns, loops exactly 3..K) and `sector_assembly` (the delivered covariance propagation and power split; any sector key order; a prefix plan K < order reports orders 0..K only, `max_order` = K); gates `top_slot_gate`, `loop7_gate`, `affinity_gate` (float or exact), `power_null_rows`; `ms8_rows`, `ms8_value`. sha256 `2127196f2c712700617834bf157b881b802bd32d67e6a5c8dbb17b1425bc1d77` |
| `exact_check.py` | `6f04d40e09cbcb78ab54c60986ba374c` | Independent exact-rational checks. Two exact routes from the note's RG equations; ms_n polynomials (sympy) against the note, ms7 and C62d's ms8; exact top-slot, loop-7 and affinity gates; the power bookkeeping identity and the MS order-4/5 power differences |
| `exact_check_results.json` | `3c5b337b8a1b10d7e374c5506bf22ed6` | Deterministic output of `python3 exact_check.py --write` |
| `prepare_low8.py` | `ac3cc558a9ca2639999dd842c28c497e` | The prepare_low generator, extended to order 8 and to any d |
| `inputs_d3/two_loop.json` | `4e497df018a5b5c9a7c79029e88a11f3` | d=3 B2, z^0..z^6. sha256 `6c31bf7fcea49e1c16b52c82ca117502932a0f6a890e5d58b4846b3cb91fbffc` |
| `inputs_d3/gamma_d3_8.txt` | `080475725c8c00302eda28a3e6ecca37` | d=3 Gamma rows L=2..8. sha256 `f868fbe27855ea0474e633e221629d5c5c1011b7dd07c2d6a4df6853b4b7293d` |
| `inputs_d3/checks.json` | `fccced3ae56b65f2ddd16c2070d5ab40` | Contour records, reference contour, direct-series check of B2, Gamma check of every printed digit, order-7 byte regressions |
| `inputs_d2_check/two_loop.json` | `c101463cf393b47320976ec8a2010ee1` | d=2 cross-check copy of B2, z^0..z^6. sha256 `565c388025a414746541040c34660c942a88e364c5fcf4fe8093927b100b00ad` |
| `inputs_d2_check/gamma_d2_8.txt` | `b68eb33c887f4cc4a1b8770b2e576fed` | d=2 cross-check Gamma rows L=2..8. sha256 `2ace6971bdbcf13bf15c74311443a302fd971923633e91261323a1283128fefd` |
| `inputs_d2_check/checks.json` | `b851b8353228bf5a866bf3d183276311` | As for d=3, plus the comparison with C62d's b_{2,6} |
| `POWER_PROTOCOL.md` | `fd9d2e92f6e88b49660679a1290a566e` | Δ_p definition, pre-registered null rows 3–7, order 8 reported, why there is no analytic order-8 compensation |
| `tests/test_order8_assembly.py` | `ab6475e0cad4fa7c34a24b82d60e072b` | 30 tests covering items 1–4 and the repair-round guards (about 26 s) |

README.md is not in the table (it cannot contain its own hash). `NOTE_C63d_to_C62d_2026-10-03.md` (md5
27095cf541370a45bb156d6ca935f314) and `STATUS_WIP.md` (md5 4c2423ee30fb047072918ed4299a4024) are unchanged. Earlier
md5s of `order8_assembly.py`: 53a0aaff9252e99503995f60897a00ce (before repair round 1), 90e0347c3d6460218b1c5664e740187c
(round 1) and 55fbc6ee94ed62bb28433cbe123d64f5 (round 2). The float and complex outputs of each later version are
byte-identical to those of the one before (400 random cases, orders 7 and 8, both d), for every input the earlier
version accepted and the later one still accepts (round 3 refuses loop sets other than 3..K; see its dispositions).

## How to run

The tests ran in the Mac's `sage` conda env (Python 3.10.12, numpy 1.24.4, sympy 1.12, mpmath 1.3.0), with pytest
9.1.1 installed in a scratch venv layered on that env. Any Python with numpy, sympy and mpmath works.

```
cd LRI_C8_shared/assembly
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_order8_assembly.py   # 30 passed in ~26 s
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_order8_assembly.py    # same tests without pytest
PYTHONDONTWRITEBYTECODE=1 python3 exact_check.py [--fast] [--write] # ~6 s; --write refreshes exact_check_results.json
PYTHONDONTWRITEBYTECODE=1 python3 prepare_low8.py                   # regenerate inputs, compare byte for byte (exit 1 on a difference); ~5 s
PYTHONDONTWRITEBYTECODE=1 python3 prepare_low8.py --write           # rewrite inputs_d3/ and inputs_d2_check/
```

- **Always set `PYTHONDONTWRITEBYTECODE=1` (and `-p no:cacheprovider` for pytest).** pytest compiles the test module
  before its own guard (`sys.dont_write_bytecode = True`, line 13) runs, so without the variable it would write
  `tests/__pycache__`, and without `-p no:cacheprovider` a `.pytest_cache`. `exact_check.py` sets
  `sys.dont_write_bytecode` itself before importing `order8_assembly` (repair round 3), so even a plain
  `python3 exact_check.py` writes nothing [V, `test_exact_check_writes_no_bytecode`].
- `test_exact_check_writes_no_bytecode` runs two subprocesses in a temporary directory (`tempfile`, honours
  `TMPDIR`). Its control step writes a `__pycache__` there on purpose; the directory is removed at the end.

- **Delivered packages are never imported.** The tests execute the delivered `assemble.py` from its source text with
  a stub `common` module, so they write no bytecode into LRI_C7_D3_HPC or LRI_C7_D2_HPC.
  - `test_no_bytecode_written_into_delivered_packages` asserts this. It compares the `.pyc` and `__pycache__`
    entries of both packages before and after loading.
  - **Do not check this with plain `git status`.** `__pycache__` is ignored there (D3 `.git/info/exclude:8`, D2
    `.gitignore:2`). Use `git status --porcelain --ignored` or `find LRI_C7_D3_HPC LRI_C7_D2_HPC -name __pycache__`.
  - The earlier statement "both git trees were clean" used plain `git status` and missed the files listed under
    "Repair round 2", disposition 2. They are not from this test suite.
  - Scratch scripts must not put a delivered `tools/` directory on `sys.path` unless they run with `python3 -B` or
    set `sys.dont_write_bytecode = True` first.
- **Where the delivered files are found.** `tests/test_order8_assembly.py`, `exact_check.py` and `prepare_low8.py`
  all read them under `$LRI_ROOT`, by default the directory two levels above this folder (Agent_LRI).
- **Skipping (a vendored copy).** Nine tests need the delivered C7 packages, the C7 production folders or C62d's
  RECON, and skip when those are absent. Checked [V] on a copy of this folder in the scratchpad (repair round 3):
  - without `LRI_ROOT`: 21 passed, 9 skipped (pytest);
  - with `LRI_ROOT=/Users/zheng/Documents/Agent_LRI`: 30 passed;
  - `prepare_low8.py` there: all six files identical with `LRI_ROOT`. Without it, the order-7 regression fields of
    `checks.json` are null, so the two `checks.json` files are reported DIFFERENT (exit 1); the other four files
    are identical.

## Usage

```python
from fractions import Fraction
from order8_assembly import (coefficients, jacobians, campaign_moments, sector_assembly, top_slot_gate, loop7_gate,
                             affinity_gate, power_null_rows, ms8_rows, ms8_value)
C  = coefficients(vals, B2, 8, 1.5)   # d=3; half_d=1 for d=2
J  = jacobians(vals, B2, 8, 1.5)
top_slot_gate(J, 8); loop7_gate(J, B2, 8); affinity_gate(vals, B2, 8, 1.5)   # raise ArithmeticError on failure
means, vc = campaign_moments(ar, range(3, 9))   # ar[sector][campaign][L]; campaigns {'a', 'b'}, loops exactly 3..K, else ValueError
r  = sector_assembly(means, vc, B2, 8, 1.5)      # r['max_order'] = K; a prefix plan (K < 8) reports orders 0..K only
Cx = coefficients(frac_vals, frac_B2, 8, Fraction(3, 2))   # exact mode: object array of Fractions
affinity_gate(frac_vals, frac_B2, 8, Fraction(3, 2))       # exact second differences, loops 5..8 (210 pairs, ~4 s)
ms8_value({'A': A, 'b3': b3, ..., 'c8': c8})                # C8 of the constant-coefficient MS polynomial
```

**Inputs:**
- `vals[L]`, L = 3..order: the b jet z^0..z^{k−1} followed by the c jet, with k = order+1−L. Lengths at order 8:
  12, 10, 8, 6, 4, 2.
- `B2`: z^0..z^{order−2} at least, as floats, as the strings of two_loop.json (read as float), or as rationals in an
  object array (exact mode, below).
- `half_d`: int, float or Fraction.
- **Exact mode.** It is entered when a `vals` vector has object dtype (for example a list of Fractions), or when `B2`
  has object dtype with at least one int or Fraction element: an object array of Fractions or Python ints, or a list
  holding a Fraction (numpy makes it an object array). Every input number then becomes a Fraction (floats by their
  exact binary value) and the same algorithm runs in rational arithmetic. The float and complex path is the
  delivered one and never enters this branch.
- **A plain list or array of ints is not exact mode** (repair round 3, documentation). numpy makes it an int64 array,
  which takes the float path: float64 output, bit-identical to the same B2 given as floats, accepted by `jacobians`,
  and `affinity_gate` runs in float mode. Use `np.array(ints, dtype=object)` or Fractions for exact mode
  [V, `test_b2_int_inputs_documented_mode`].
- **Exact-mode B2 is for `coefficients` and `affinity_gate` only** (repair round 2). A complex step cannot pass through
  exact mode, so `jacobians` and `sector_assembly` raise ValueError for a B2 in exact mode. They do the same
  for a complex B2 with a nonzero imaginary part. Pass a float B2 there; rational `means` are read as complex floats,
  as delivered.
- **Campaigns.** `campaign_moments` uses the delivered fixed weights 1/2 and 1/4. Those are right only for two
  campaigns, so it raises ValueError unless both sectors {'free', 'power'} have exactly the campaigns {'a', 'b'}.
  Every campaign must hold every requested loop as a finite 2-d array with at least two replicates, as in the
  delivered wrappers. `sector_assembly` raises ValueError when the loop keys of `means` and `vc` differ between
  sectors.
- **Loop-set rule** (repair round 3; delivered D3 `assemble.py:81-82`, D2 `:89`). `loops` must be exactly 3..K with
  5 ≤ K ≤ 8 (any iteration order, no repeats), and every campaign must hold exactly those loops. An extra loop in
  `ar` (for example order-8 data passed with `range(3, 8)`), a missing loop, a non-contiguous set such as {3, 4, 6},
  or campaigns with different K raise ValueError. `sector_assembly` applies the same rule with 5 ≤ K ≤ order.
- **Prefix plans.** For K < order, `sector_assembly` reports orders 0..K only, as the delivered D3 `calculate` does
  (`:124-133`): the coefficient and error vectors, the covariances, the rows of `J`/`Jf` and the contribution matrices
  are cut to K+1. Every result carries `max_order` (= K), `loops` and `order`.
- **Key order.** Both helpers combine the sectors in the delivered order (free, power) and the loops in the order
  3..K, whatever the key order of their inputs. A power-first `ar` or `means`/`vc` gives pickle-identical results
  [V, `test_loop_set_rule_and_sector_order`].
- The fixed point, C_0 = d/2 and the −½δ_{n1} shift of C_1 (so C_1 = −1/6) follow the delivered functions (`LRI_C7_D3_HPC/tools/assemble.py:41-57`,
  `LRI_C7_D2_HPC/tools/assemble.py:28-43`).

**Gates and tables:**
- `affinity_gate(means, B2, order, half_d)`:
  - Float means: J_L for L = 5..order must be unchanged (to 1e-10 of max|J_L|) when only the loop-5..order jets
    are moved by δ = 10^-2 (|m| + 1)·N(0,1), with a fixed seed. Loops 2–4 legitimately move J_5..J_8 (see §3), so
    they are not perturbed. The linear-response residual is reported but not gated.
  - An identically zero (or non-finite) J_L fails the float gate. The top slot alone gives
    dC_order/db_{L,order−L} = −1/3^{L+1} ≠ 0.
  - Exact mode, when a `means` vector has object dtype or `B2` is in exact mode (object dtype with an int or
    Fraction; not a plain int list): all exact second differences over the slot pairs of loops 5..order must
    vanish. Float means then enter by their binary values.
- `ms8_rows(general=False)`: rows (Fraction coefficient, {symbol: power}) of 19683·C8. There are 34 rows with
  b2 = −6A, c2 = −A, or 45 with `general=True` (free b2, c2).
- `ms8_value(env)`: that polynomial divided by 19683. The table is fixed in the file and tested against the
  independent sympy derivation of `exact_check.py`.

## Results [V]

### 1. Order-7 regressions

- **Bitwise identity on identical inputs** (same machine, `tobytes` equality), against both delivered functions:
  - 150 random cases per d: real, complex-step and prefix-plan inputs, plus Jacobians;
  - a 7-entry B2 is truncated, so at order 7 it gives bits identical to its 6-entry prefix.
- **Production inputs:**
  - The means recomputed from `groups/*/merged.json` equal the published `means` bit for bit (d=2 and d=3).
  - On them, `coefficients` and the delivered functions agree bit for bit.
  - `sector_assembly` and the delivered `calculate` (d=3) or `combine` (d=2), bootstrap off, agree bit for bit in
    `coefficients`, `standard_errors`, `covariance`, `power_differences` and `power_difference_errors`.
- **Against the published values** (computed on symmetry), both the delivered code and this code give on this Mac:

  | | Published | This Mac | Difference |
  |---|---|---|---|
  | C7(3) | −220.35448047392794 | −220.35448047392805 | 4 ulp |
  | C7(2) | −3876.1260927949925 | −3876.1260927949916 | 2 ulp |

  - All other fields agree to ≤ 1e-12 of their scale.
  - This is the CPU-dependent NumPy rounding already documented: `LRI_C7_D3_HPC/tools/assemble.py:242-245`; C7(2)
    "reproduces C7 to 9e-13", `LRI_C7_D2_HPC_production/CAMPAIGN.md:100-101`.
  - Bit identity with the published numbers needs the production CPU type.

### 2. Exact-rational inversion (`exact_check.py`)

- **Route L** is the bivariate Lagrange formula, done:bivariateLagrange N:9046-9051 = d3six:lagrange N:9221-9226.
  **Route F** solves β(g_*, ε) = 0 coefficient by coefficient (N:8912-8915, N:10388).
  - Both take general independent b_L and c_L, including c_2.
  - They agree exactly in 64 order-8 and 16 order-7 random cases.
- **Float code against exact,** on random rational inputs: maximum error relative to the coefficient vector's scale
  is 7.0e-16 at order 8 (64 cases) and 2.1e-16 at order 7 (16 cases).
- **`coefficients` in exact mode equals route L exactly** (`test_fraction_mode_equals_exact_lagrange`). This holds
  in 24 order-8 and 12 order-7 random cases, with half_d as int, float or Fraction, B2 as a list or an object
  array, and prefix plans. It also holds when only B2 is rational (float `vals` then enter by their binary values).
- **`ms8_rows` equals the sympy ms8** (34 rows A-substituted; 45 general) and C62d's embedded polynomial.
  `coefficients` in Fractions equals `ms8_value` exactly in 16 random constant-coefficient cases
  (`test_ms8_rows_table`).
- **ms_n, constant-coefficient MS** (eq:Lagrange N:232, with b2 = −6A_d and c2 = −A_d at N:2273). All comparisons
  are symbolically **equal**:

  | Order | Compared with |
  |---|---|
  | C2 | A/9 (gd:C03, N:2264) |
  | C3 | (A² + R − 8Q)/108 with gd:bc3 (N:2265, N:2273-2275) |
  | C4 | eq:C4RG (N:250-251) and gd:C4 (N:2653-2654) |
  | C5 | eq:C5RG (N:253-256) and gd:C5 (N:2655-2660) |
  | C6 | c6:RGassembly (N:7492-7499) |
  | C7 | delivered `ms7` (`LRI_C7_D2_HPC/reference/LRI_C7_d2_progress/code/check_assembly.py:53-55`) and C63d's recon 3^8 C7 |
  | C8 | C62d's 19683 C8 (`LRI_C8_D2_HPC_loop/RECON.md:91-95`; embedded copy and the live file) and C63d's recon 3^9 C8 (`LRI_C8_D3_HPC_loop/recon/theory.md:263-266`) |

  - ms8 has 34 monomials after the A substitution and 45 with general b2, c2.
  - Both exact routes with z-independent jets reproduce ms_2..ms_8 exactly (8 cases). The float code agrees to 1e-12
    (6 cases).
- **Verdict:** C62d's ms8 polynomial equals the independently derived ms8 exactly; there is no difference.
  `19683 ms8 = 82368A^7 − 25344A^5 b3 + 28512A^5 c3 − 5280A^4 b4 + 7920A^4 c4 + 1980A^3 b3^2 − 3960A^3 b3c3 − 960A^3 b5
  + 1800A^3 c5 + 540A^2 b3b4 − 720A^2 b3c4 − 540A^2 b4c3 − 144A^2 b6 + 324A^2 c6 − (100/3)A b3^3 + 90A b3^2c3 + 54A b3b5
  − 90A b3c5 + 27A b4^2 − 72A b4c4 − 54A b5c3 − 16A b7 + 42A c7 − 5b3^2b4 + 6b3^2c4 + 9b3b4c3 + 3b3b6 − 6b3c6 + 3b4b5
  − 5b4c5 − 4b5c4 − 3b6c3 + 3c8 − b8`.

### 3. Gates

- **Top slot, exact:** for L = 2..8, C8(x + e_top) − C8(x) = (−1, +3)/3^{L+1} at 4 random general points (order 7: 2
  points), and no lower C_n changes.
  - Float `top_slot_gate` passes at d=2 and d=3, orders 7 and 8.
  - A corrupted Jacobian (one entry × (1 + 1e-9)) fails it.
  - The loop-2 top slot through B2 (c2 = B2/6) gives dC8/db_{2,6} = −1/54.
- **Loop-7 entry, exact:**
  - In general, dC8/d(b_{7,0}, c_{7,0}) = (3b_{2,0} − 2c_{2,0}, −7b_{2,0})/3^9 (8 points); with c2 = b2/6 this is
    (−16A_d, 42A_d)/19683.
  - A_d = ψ0(d/2) + ψ0(1) − 2ψ0(d/4) (gd:blocks, N:2247):
    - **A_2 = 4 log 2** (N:7822) = 2.7725887222397812377…;
    - **A_3 = 2 + 4 log 2 − π** (N:8781) = 1.6309960686499879992….
  - Both equal −b_{2,0}/6 of the two_loop inputs to < 1e-55.
  - Float `loop7_gate` passes; the ratio dc/db is −2.625.
- **Affinity, exact:** all second differences of C_0..C_8 vanish over the 210 slot pairs of loops 5..8 (78 pairs over
  loops 5..7 at order 7).
  - Nonzero controls at order 8: (3,3) −133753/688905; (3,4) 2573/91854; (4b,4c) 8/2187; (3,5) 10/2187;
    (2,6) −449/137781; (4,5) 1/6561. The (4,5) term is zero at order 7: all 48 loop-4 × loop-5 exact slot pairs
    vanish there, and moving loop 4 leaves J_5 unchanged [V, `test_affinity_loop4_control_order_dependence`].
  - `affinity_gate` (`test_affinity_gate`):
    - It passes in float mode at d=2 and d=3, orders 7 and 8. The deviations were exactly 0 in 20 float gates (a
      scratchpad probe). [I] The likely reason is that the real parts of the loop ≥ 5 jets never meet the imaginary
      step within the truncation.
    - It passes in exact mode at order 8 (210 pairs).
    - Moving loop 4 changes J_5, and `loops=[4, 5]` fails the gate. This is why only loops ≥ 5 are perturbed.
    - An injected 10^-3·b_{5,0}² in C8 (a monkeypatched `coefficients`) fails the gate in both modes.
- **Slot shift (extra):** dC8/d(slot j) = dC7/d(slot j−1) at the same point (float, all loops 3..7).
- **Power bookkeeping:** R8 involves only A and loops 3..6 (29 monomials), and the order-8 Δ_p identity holds exactly
  (POWER_PROTOCOL §4).
  - The MS order-4 power difference vanishes identically with d3six:lowerPower. The d=2 done:powerSums are that
    formula at M_2 = −4, N_2 = 4 − A_2 (60 digits).
  - MS order 5 (repair round 2): 729 Δ_p[5] = [M(57A² + 12AN + 24Q − 3R) + 4(3c5 − b5)^p]/4 identically, using
    lowerPower and gd:bc3.
    - At d=2 it gives Δ_p[5] = −3.32e-21, with the done:powerSums b5^p, c5^p (N:8711-8712), Q_2 (N:2407) and R_2 = 0.
    - That is below the 1.78e-20 resolution of the printed digits. The lower-order part alone is −1.0775357715….
    - POWER_PROTOCOL §2 now lists order 5 at d=2 as an MS numerical zero.

### 4. Low-loop inputs (`prepare_low8.py`)

**Order-7 byte regressions** (both d; recorded in `checks.json`):
- With order=7, the generalized generator reproduces `LRI_C7_D3_HPC/inputs/two_loop.json`,
  `LRI_C7_D3_HPC/inputs/gamma_d3_7.txt`, `LRI_C7_D2_HPC/inputs/two_loop.json` and `LRI_C7_D2_HPC/inputs/gamma_d2_7.txt`
  **byte for byte**. The d=2 files come from the general-d formulas with the delivered d=2 settings.
- In the order-8 files, the first six B2 strings are identical to the delivered ones.
- For L = 2..7, the gamma tokens n_L and a_{L,0..5} are identical. The label changes from 7−L to 8−L, and a_{L,6} is
  appended; that is the only formatting difference.

**The two-loop z^6 coefficient b_{2,6}:**

| | d=3 (65 digits) | d=2 (75 digits) |
|---|---|---|
| Value | −29.258124480916806558671227221989158045345679248109116199844574934 | −266.520967961359381732252192619089800949020036292157482004691324613197558131 |
| Contours | r = 0.04 / 64 nodes and r = 0.07 / 80 nodes | r = .05 / 80 nodes and r = .08 / 96 nodes |
| z^6 agreement | 2.68e-56 | 3.08e-66 |
| All 7 entries agree within | 2.7e-56 | 3.1e-66 |
| Stored value vs the 95-digit reference contour (r = 0.2, 192 nodes) | 1.7e-57 | 7.7e-68 |
| Stored value vs a direct Taylor series at 130 digits (`series_check`, no contour) | 1.72e-57 | 7.71e-68 |
| Reference contour vs that series | 3.3e-91 | 9.7e-92 |
| Significant digits of the stored z^6 (from the series check) | 58.2 | 69.5 |

- The asserted tolerance is 10^−(dps−10).
- **Measured accuracy** (repair round 3) [V, `checks.json` → `two_loop.series_check`]: the stored z^6 differs from
  the 95-digit reference by 1.7e-57 at d=3, about 58 significant digits (56 correct decimal places; corrected in
  repair round 4), and by 7.7e-68 at d=2, about 69 significant digits (66 correct decimal places). The series, by
  `mpmath.taylor` of the same numerator at 130 digits, confirms the reference to 3.3e-91 (d=3) and 9.7e-92 (d=2).
  The significant digits of all seven stored entries are listed there: 65.0 down to 58.2 (d=3) and 74.8 down to
  69.5 (d=2).
- The earlier statement "only about 56 of the 65 printed digits" came from the two-contour difference 2.68e-56, which
  is dominated by the r = 0.04 contour, not by the stored r = 0.07 one. It understated the accuracy.
- The d=2 value agrees with C62d's printed −266.52096796135938173225219261908980094902 (`RECON.md:31`) to 3.6e-41,
  i.e. to all printed digits.

**Gamma L=8 row** (`gamma_d3_8.txt`, label 0):
- n_8 = −0.0294339666459244136780932879797953140826225771447904744031925
  = −2Γ(3/2)^8/Γ(3/4)^16 (relative difference 1.4e-60, 0.41 units in the last printed digit).
- a_{8,0..6} = 0.0, 4.48940341506019476074364171927370050390766173869080937453283,
  11.1784008446464611155253202262517127676292468055742776012149,
  −25.1603846897097983413508609806655660729168195196409021588164,
  69.1112856567811626553015813830238554323689388279341490498141,
  −212.304810390528333318757194341887306360105551115037872160849,
  694.483249297217187535288988664211378269547271392887699650418.
- At d=2: n_8 = −0.00021078078330698733266345745456202017439259741343046145244134481387 = −2/π^8.
- **Every printed digit is certified** (repair round 3) [V, `checks.json` → `gamma.cauchy_check`, asserted by
  `prepare_low8.py`]:
  - All 42 jets per d (L = 2..8, j = 1..6) are checked against two independent Cauchy contours of log G at dps + 35
    working digits (100 at d=3, 110 at d=2): radius 0.041 with 128 nodes and radius 0.03 with 160 nodes. The two
    contours agree to 4.9e-93 (d=3) and 9.7e-100 (d=2).
  - Every printed a_{L,j} differs from the check value by at most 0.4947 (d=3) and 0.4838 (d=2) units in its last
    printed digit, so each is the correctly rounded value at its 60 (d=3) or 65 (d=2) printed digits. The largest absolute
    differences are 4.1e-58 and 3.3e-63; the relative ones 3.75e-60 and 3.75e-65.
  - Every n_L is likewise correctly rounded against its closed form (0.4831 and 0.4822 units).
- The earlier 64-node check reached only 3.3e-49, because of aliasing from the log Γ(1+4z) branch point at z = −1/4
  (L=8). With 128 nodes the aliasing is about 4^6 (4 · 0.041)^128 / 134 ≈ 1e-99.
- The gamma files themselves are unchanged (md5 above), and their order-7 regeneration is still byte-identical to the
  delivered `gamma_d3_7.txt` and `gamma_d2_7.txt`.

**C8 at the C7 production means,** with the new top slots and loop 8 set to zero. This is a regression value only,
not the complete C7-level part of C8: the C7 L7 z^0 means lack the s_G = 4 classes (see below). The SE comes from
the C7 replicate covariances. Asserted in `test_order8_assembly_on_c7_production_point`.

| d | Value | Note |
|---|---|---|
| 2 | −192710.59 ± 8.20 | Reproduces the arithmetic of C62d's "−192,711 ± 8" (`RECON.md:100`) |
| 3 | −6237.09 ± 0.33 | Reproduces the arithmetic of C63d's recon value (`LRI_C8_D3_HPC_loop/RECON.md:45`) |

- **Why the label changed (repair round 1).** The C7 productions skipped the loop-7 zero-channel classes:
  - d=2: `mass_numerator==4` at L=7 (`LRI_C7_D2_HPC/tools/prepare_inputs.py:36`) [R];
  - d=3: 2,298 + 590 L7 kernels instead of 2,441 + 709, i.e. +143 free and +119 power s_G = 4 kernels
    (`LRI_C8_D3_HPC_loop/RECON.md:39-40`, `NOTE_C63d_to_C62d_2026-10-03.md:15`) [R].
- **What is complete.** For an s_G = 4 class 3c = b, so the published b_{7,0} and c_{7,0} means are individually
  incomplete; only 3c_{7,0} − b_{7,0} is complete. C8 weighs them as (−16A, 42A)/19683
  = 14A(3c − b)/19683 − 2A b/19683.
- **The loop-7 z^0 share at these means** [V, asserted in the same test]:

  | d | (−16A b70 + 42A c70)/19683 | 14A(3c70 − b70)/19683 (complete) | −2A b70/19683 (uses the incomplete b70) |
  |---|---|---|---|
  | 2 | −81,617.05 | −69,021.37 | −12,595.68 |
  | 3 | −1,977.92 | −1,667.13 | −310.79 |

- **Not quantified here** [I]. The missing classes add −2A W/19683, where W is their total b_{7,0} weight. No C7
  data give W, and it may well exceed the quoted SEs (±8.2, ±0.33).
- **Consequence.** The cancellation and expected-value estimates built on these numbers inherit the omission. That
  covers C62d's `RECON.md:100` and C63d's `LRI_C8_D3_HPC_loop/RECON.md:44-47`.

## Differences from C62d's statements (`LRI_C8_D2_HPC_loop/RECON.md`, md5 3bb715b1f748ebbaa6eefc97949b18fa)

1. **Gamma columns.**
   - C62d proposes "6 log values per row" for `gamma_d2_8.txt` (`RECON.md:164-167`).
   - These files carry 7 (a_{L,0..6}), following `LRI_C8_D3_HPC_loop/RECON.md:108,365`: the d=3 L=2 control at K=6
     needs a_{2,6}.
   - The two C8 workers' gamma readers must agree on the column count. This needs a joint decision.
2. **Contour settings at d=2.**
   - C62d states radii 0.05/0.08 with 64/80 nodes at 60 digits, agreeing to 1.9e-53 (`RECON.md:168`).
   - The delivered d=2 generator used 80/96 nodes at 75 digits (`LRI_C7_D2_HPC/reference/LRI_C7_d2_progress/code/prepare.py:5,18`).
   - Only the delivered settings reproduce the existing six entries byte for byte, because str(mpf) prints dps
     digits. The b_{2,6} values agree to C62d's printed digits either way.
3. **Minor.**
   - C62d cites `ms7` at `check_assembly.py:55-57`; the function is at lines 53-55.
   - `RECON.md:291` still lists "C82d writes, C63d reviews" for `order8_assembly.py`. The NOTE in this folder
     supersedes it.
   - The delivered d=2 `two_loop.json` has only a `B2` key. The d=2 check copy here adds `dimension` and `order`;
     the format of C8(2)'s own file is C62d's choice.
4. **The cancellation estimate at `RECON.md:100` inherits the C7 s_G = 4 omission** (repair round 1).
   - "The part already fixed by C7-level jets is −192,711 ± 8" evaluates C8 at the C7 production means.
   - The arithmetic is right (§4 above), but the C7 L7 z^0 means lack the s_G = 4 classes, which C8 weighs by
     −2A w_A/19683 each. So it is not the complete C7-level part.
   - The "+2.35e5 from the new top slots" and the relative-error inflation built on it carry the same caveat.
   - C62d should relabel it as C63d did here. C63d's own `LRI_C8_D3_HPC_loop/RECON.md:44-47` has the same flaw (see
     Dispositions).
5. **Affinity gate of A-ASM-4** (`LRI_C8_D2_HPC_loop/PLAN.md:661`, md5 e17a2966da8a867075aa54fa0440cdd6).
   - The plan reads "for L = 5..8, J_L at the means and at the means + δ agree to 1e-10".
   - This holds only if δ moves the loop-5..8 jets alone. A δ on loops 3 or 4 moves J_5..J_8 legitimately: the exact
     controls (3,5) = 10/2187, (4,5) = 1/6561 and (2,6) are nonzero, and `test_affinity_gate` shows J_5 moving.
   - `affinity_gate` perturbs loops 5..order only. Please make A-ASM-4 say so.
6. **Everything else checked agrees:**
   - the ms8 polynomial;
   - the top-slot rule (−1, +3)/3^(L+1), L = 3..8;
   - (−16A, 42A)/19683 with A = 4 log 2 and the ratio −2.625;
   - affinity in loops 5–8, and nonlinearity in loops 3–4;
   - the order-7 path bitwise equal to both delivered functions;
   - the C7(2) production reassembled unchanged, up to the 2-ulp CPU rounding above;
   - n_8(2) = −2/π^8.

## What C62d should check

1. Run the tests (`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests/test_order8_assembly.py`)
   and `PYTHONDONTWRITEBYTECODE=1 python3 prepare_low8.py` on your side. Then confirm the md5s above, and the sha256
   of `order8_assembly.py` that you pin.
2. Read `order8_assembly.coefficients` against `LRI_C7_D2_HPC/tools/assemble.py:28-43`. The only intended changes
   are `N = order+1`, `k = N−L`, `ga[0] += half_d`, B2 truncation to order−1 entries, complex B2 for the loop-2
   step, and the exact (object/Fraction) branch. That branch only swaps the constants 0, 1/2 and d/2 for Fractions
   and converts the inputs; the float path still runs `np.zeros(1)`, `.5` and the delivered operation order.
   Check `affinity_gate`, `ms8_rows` and `ms8_value` against `LRI_C8_D2_HPC_loop/PLAN.md:446-448` and A-ASM-4.
3. Read `exact_check.lagrange` and `fixed_point` against N:9046-9051 and N:8912-8915. They must stay independent of
   the float code.
4. Check that the ms8 comparison uses your RECON text (embedded copy plus the live file). Rerun it if you edit
   `RECON.md:91-95`.
5. Decide jointly:
   - the gamma column count (difference 1);
   - your d=2 contour settings (difference 2);
   - whether `inputs_d2_check/two_loop.json` and `gamma_d2_8.txt` should become your package inputs, or stay a
     cross-check of your own generator;
   - the vendored interface (repair round 1). `order8_assembly.py` now has the `PLAN.md:446-448` interface:
     - `coefficients` in float, complex and object/Fraction dtypes, with half_d as int, float or Fraction;
     - `top_slot_gate`, `loop7_gate`, `affinity_gate`;
     - `ms8_rows`.
     The exact-rational Lagrange cross-check stays in `exact_check.py`, so that it stays independent of the float
     code. Agree whether to vendor `exact_check.py` too; it needs only sympy and mpmath, honours `LRI_ROOT`, and
     omits the ms7 and live-RECON comparisons when those files are absent. Also agree the A-ASM-4 δ restriction
     (difference 5).
6. Review `POWER_PROTOCOL.md` (null rows 3–7 flagged "not proved zero", order 8 reported only) before any C8(2)
   pilot data exist. Repair round 2 changed it in two places: the order-5 row is split by d (d=2 is an MS numerical
   zero), and the order-8 pull is reported as a diagnostic. Repair round 3 corrected the §3 wording and citation
   only (the vanishing of the top-order correction is "not proved"; the note states no conjecture for d=2/3).
7. **Bytecode in your delivered package** (repair round 2). `LRI_C7_D2_HPC/tools/__pycache__/assemble.cpython-314.pyc`
   and `common.cpython-314.pyc` were born 2026-10-03 11:13:21 [V, `stat`].
   - They are cpython-3.14 files; this session's Python is 3.10. [I] They probably came from your session b6520403.
     Its scratch scripts put `LRI_C7_D2_HPC/tools` on `sys.path`, and some do so without `dont_write_bytecode`
     (e.g. `scratchpad/intel.py:2`) [V].
   - They are git-ignored (`.gitignore:2`), so plain `git status` does not show them.
   - Please remove them, or have the owner do so.
8. **Shared helper contract** (repair rounds 2 and 3). `campaign_moments` now refuses anything but exactly the
   campaigns {'a', 'b'} in both sectors, and `jacobians`/`sector_assembly` refuse an exact-mode B2. If A-ASM-6
   (partial combinations) needs other weights, it needs its own weighting function; do not pass one campaign to
   this one. Round 3 adds the delivered loop-set rule (loops exactly 3..K, 5 ≤ K ≤ order, in both helpers) and
   prefix-plan truncation in `sector_assembly` (orders 0..K only, `max_order` = K). A caller that reads index 8 of a
   K < 8 result now gets an IndexError instead of a number that silently lacks loops K+1..8.

## Repair round 1: dispositions (2026-10-03)

1. **[minor] "The part fixed by C7-level jets" label (§4, test docstring). Applied, except for one file.**
   - The README entry is now "C8 at the C7 production means … regression value only". "Confirms C62d's …" now reads
     "Reproduces the arithmetic of …". The docstring of `test_order8_assembly_on_c7_production_point` says the same.
   - The numbers are unchanged and kept as regression values.
   - The loop-7 z^0 share is quantified [V] and asserted in that test, and split into its complete part and its
     incomplete-b70 part (§4).
   - C62d is told under "Differences" item 4.
   - **Not applied:** the correction of `LRI_C8_D3_HPC_loop/RECON.md:44-47` (md5
     1018fb306b1dae7c6fd99034cd063c0f). That file is outside this track's only writable folder,
     LRI_C8_shared/assembly/ (project rule).
   - **Erratum for the C63d lead session to apply there:**
     - Replace "the part fixed by C7-level jets (plus b_{2,6}) is **−6,237.09 ± 0.33**" with "C8 at the C7
       production means, with the new top slots and L8 zero, is −6,237.09 ± 0.33 (a regression value: the C7 L7
       z^0 means lack the s_G = 4 classes, so this is not the complete C7-level part; their share −2A W/19683 is
       unknown)".
     - Mark the "5× cancellation" and the expected-value band as resting on it.
2. **[major] Interface of `LRI_C8_D2_HPC_loop/PLAN.md:446-448` (Fraction dtype, `affinity_gate`, `ms8_rows`).
   Applied (option 1).**
   - `_b2` keeps object arrays holding a rational exact. Only strings, or object arrays without rationals, are cast
     to float, as before.
   - `coefficients` has an exact branch for object/Fraction inputs and accepts any real `half_d`, Fraction included.
   - New `affinity_gate` (float and exact), `ms8_rows`, `ms8_value` and `MS8_SCALE`.
   - The float/complex path keeps the delivered operations. Re-run [V]:
     - `test_order7_bitwise_random` and `test_order7_production_reassembly` still pass, bit for bit, against both
       delivered functions;
     - the exact branch equals the independent route L exactly (`test_fraction_mode_equals_exact_lagrange`).
   - Added to "Decide jointly", together with the A-ASM-4 δ restriction (Differences item 5).
3. **[minor] `LRI_ROOT` ignored by `exact_check.py` and `prepare_low8.py`; `test_ms_polynomials` had no skip.
   Applied.**
   - Both modules now read `LRI = Path(os.environ.get('LRI_ROOT', HERE.parents[1]))`.
   - `test_ms_polynomials` now runs only the embedded comparisons, which need no file. The delivered ms7 and the
     live C62d RECON moved to `test_ms_polynomials_against_delivered_files`, which calls `need()` on both files.
   - Re-run from a copy in the scratchpad: without `LRI_ROOT`, 15 passed and 7 skipped (exit 0); with it, 22
     passed. In place, 22 passed.
4. **[minor] POWER_PROTOCOL §4 said the analytic route "was used once, for C6(3)". Applied.**
   - It now reads "used at sixth order at both d: C6(2) (prec:d2production2026, N:9449-9453; N:9872) and C6(3)
     (prec:d3production2026, N:9528-9530)".
   - The test citations are corrected too: d=3 is N:10821-10823 (was N:10819-10822); d=2 is N:10665-10667.
   - A revision line at the top of POWER_PROTOCOL records that the rule is unchanged.

## Repair round 2: dispositions (2026-10-03)

1. **[minor] A rational B2 gave silently zero Jacobians, and the affinity gate passed on them. Applied.**
   - `jacobians` raises ValueError when B2 holds a rational. It does the same for a complex B2 with a nonzero
     imaginary part, which would add its own step.
   - `affinity_gate` enters exact mode when `means` **or** B2 holds a rational.
   - The float gate raises ArithmeticError when max|J0[L]| is 0 or not finite. The `scale > 0 else` fallback is
     gone.
   - `sector_assembly` therefore raises a clear ValueError instead of a TypeError. `loop7_gate` reads A_d from a
     Fraction b_{2,0}.
   - Docstrings and "Usage" state that a rational B2 is for `coefficients` and `affinity_gate` only.
   - New test `test_rational_b2_guards` covers float means with a Fraction B2:
     - `jacobians` and `sector_assembly` refuse it;
     - the gate runs exact (210 pairs) and fails on the injected 10^-3·b_{5,0}²;
     - zero Jacobians fail the float gate.
   - It fails on the pre-repair module [V].
2. **[minor] `__pycache__` in the delivered D3 package. Partly applied; the removal itself is rejected for this
   track.**
   - Confirmed [V]: `LRI_C7_D3_HPC/tools/__pycache__/assemble.cpython-310.pyc` and `common.cpython-310.pyc` were born
     2026-10-03 11:15:01, the same second as this session's `scratchpad/asm8.py`. That script put
     `LRI_C7_D3_HPC/tools` on `sys.path` and imported `assemble`. The causation is [I], but strong.
   - Running `python3 -B tools/verify_delivery.py --strict` in LRI_C7_D3_HPC lists 8 unexpected files [V]: these two
     and six `.DS_Store` files.
   - **Not done here:** removing them. That is a write outside LRI_C8_shared/assembly/, which this track's rules
     forbid. **The C63d lead must delete `LRI_C7_D3_HPC/tools/__pycache__/`** and rerun
     `verify_delivery.py --strict`.
   - Done here:
     - `asm8.py` in the scratchpad now sets `sys.dont_write_bytecode = True` before the `sys.path` insert. No other
       scratch script of this session imports a delivered `tools/` module.
     - README "How to run" now says to check with `git status --porcelain --ignored` or `find`, not plain
       `git status`.
     - New test `test_no_bytecode_written_into_delivered_packages`.
     - C62d is told about the D2 cpython-314 files ("What C62d should check", item 7).
3. **[minor] `campaign_moments` accepted one or three campaigns. Applied.**
   - It raises ValueError unless the sectors are {'free', 'power'} and each has exactly the campaigns {'a', 'b'},
     every campaign holds every requested loop, and each block is a finite 2-d array with at least two replicates.
     This follows the delivered checks (`LRI_C7_D3_HPC/tools/assemble.py:76-85`, `LRI_C7_D2_HPC/tools/assemble.py:85-91`).
   - "On the vc keys" in `sector_assembly`: that function sees sectors and loops, not campaigns. It already required
     the sectors `free`, `power` in order. It now also requires equal loop key sets in `means['free']`,
     `means['power']`, `vc['free']` and `vc['power']`.
   - New test `test_campaign_moments_requires_two_campaigns` covers one and three campaigns, a missing sector, a
     missing loop, one replicate, and mismatched vc keys. It fails on the pre-repair module [V].
4. **[minor] POWER_PROTOCOL §3 said the order-8 Δ_p had "no null hypothesis". Applied (first option).**
   - §3 now says its vanishing is not proved, as at order 7. (Round 2 wrote "conjectured (N:10220-10221)"; that
     citation is the d=1 C7 section and says such a conjecture is not imposed. Corrected in repair round 3,
     disposition 1.)
   - Its pull is reported as a diagnostic only, with no flag or threshold. It never changes C8.
   - The C7 comparison with previous values (N:10663-10665, N:10820-10821) is cited, with the reason there is none
     at C8.
   - `power_null_rows(...)['top']` now carries `pull` (None when SE = 0) and no `flag`. The C7 top pulls, +1.14 (d=3)
     and −1.22 (d=2), are asserted and shown in the protocol table.
   - A revision line records the change before any C8 data. There is none on this Mac [V]; cluster state was not
     checked [I].
5. **[minor] Order-5 row listed as "measured only" at both d. Applied.**
   - The verifiers' formula is reproduced [V, sympy, now in `exact_check.power_bookkeeping`]:
     729 Δ_p[5] = [M(57A² + 12AN + 24Q − 3R) + 4(3c5 − b5)^p]/4.
   - At d=2 it gives Δ_p[5] = −3.32e-21, against a printed-digit resolution of 1.78e-20 [V, 60 digits]. The test
     asserts it.
   - The row is split: d=2 is "MS numerical zero (numerical check, not a theorem)"; d=3 stays "measured only"
     (N:8822-8827).
   - The "must be investigated" sentence now covers order 5 at d=2.

**Unchanged by this round [V]:**
- Float and complex outputs of `coefficients`, `jacobians`, `campaign_moments`, `sector_assembly`, `affinity_gate`
  and `loop7_gate` are byte-identical to the round-1 module (md5 90e0347c3d6460218b1c5664e740187c). Checked on 400
  random cases at orders 7 and 8, both d.
- The order-7 bitwise and production tests still pass against both delivered functions.
- `prepare_low8.py` reproduces all six input files byte for byte.
- `exact_check_results.json` differs from round 1 only by `module_md5` and the four new order-5 fields.

## Repair round 3: dispositions (2026-10-03)

The 12 residual issues of `LRI_C8_D3_HPC_loop/recon/phase1_asm_residual_issues.json`, in that file's order. Items 1
and 10, 2 and 7, and 4 and 8 are the same defect found by two verifiers; each pair has one fix. Note citations are
to md5 85f9a1ec039543e2d7ea70654a1aac10 and were re-read for this round [R].

1. **[minor] POWER_PROTOCOL cites the d=1 C7 "conjecture" sentence for d=2/3. Applied (second suggested option).**
   - What the note says [R, grep]: the only "conjecture" is N:10220-10221, in the d=1 C7 section (app:C7complete,
     N:9880), and it is a conjecture that is *not imposed*. The d=2 and d=3 C7 sections say only that "no power
     correction is forced to vanish" (N:10655-10656, N:10811-10812) and that the lower rows "are consistent with
     zero but do not prove a cancellation at seventh order" (N:10659-10661, N:10817-10818). The d=1 C8 section
     (app:C8complete, N:10826-10968) integrates the power sector explicitly (N:10886-10896) and says nothing about
     the vanishing of an eighth-order power correction.
   - POWER_PROTOCOL §3 now says the vanishing is "not proved" and quotes those sentences. The round-2 revision line
     no longer says "conjectured", and a round-3 revision line records the change. The rule, the null rows, the flag
     threshold and the diagnostic-only top pull are unchanged.
   - `power_null_rows`: the docstring and the emitted `role` string are corrected in the same way. The role now
     reads "its vanishing is not proved (the d=2/3 C7 sections only report the lower rows as consistent with zero,
     N:10659-10661, N:10817-10818)". `test_power_bookkeeping_and_null_rows` asserts this.
   - Round-2 disposition 4 above is corrected in place, with a pointer here.
2. **[nit] B2 given as a list or array of ints takes the float path, not the documented exact mode. Applied
   (documentation).**
   - Chosen over treating int dtype as exact, which would turn float64 outputs of inputs that are accepted today
     into Fractions and break the "float outputs unchanged" rule.
   - Module docstring, `_b2_holds_rational`, `jacobians` and `affinity_gate` docstrings, and README "Usage" now say:
     exact mode needs B2 with object dtype holding an int or Fraction; a plain list or array of ints is int64 and
     stays on the float path.
   - New test `test_b2_int_inputs_documented_mode` [V]. For int lists, int64 and int32 arrays, the output is float64
     and bit-identical to the same B2 as floats, and so are the Jacobians. `_b2_holds_rational` is False and
     `affinity_gate` runs in float mode. An object array of ints, or a list holding a Fraction, gives Fractions, and
     `jacobians` refuses it.
3. **[nit] `affinity_gate` docstring did not say that (4,5) is an order-8 control. Applied.**
   - The docstring now reads "(3,5) and (2,6) are nonzero at orders 7 and 8; (4,5) is nonzero at order 8 only".
     POWER_PROTOCOL §5 says the same.
   - [V] New test `test_affinity_loop4_control_order_dependence`:
     - at order 7 all 48 loop-4 × loop-5 exact slot pairs give zero second differences, and moving loop 4 leaves J_5
       unchanged (relative change 0.0);
     - at order 8 some of the 80 pairs are nonzero, and J_5 moves.
4. **[nit] `exact_check.py` could write `__pycache__`; README told C62d to run pytest without the guards. Applied.**
   - `float_vs_exact` sets `sys.dont_write_bytecode = True` before it imports `order8_assembly`
     (`exact_check.py:409-411`); the module docstring says so.
   - [V] On scratch copies, with `PYTHONDONTWRITEBYTECODE` unset, `python3 exact_check.py --fast`:
     - with the round-2 file: writes `__pycache__/order8_assembly.cpython-310.pyc`;
     - with the round-3 file: writes nothing.
     The live `exact_check.py --write` of this round also ran without the variable and left no `__pycache__`.
   - [V] pytest 9.1.1 on a scratch copy: without the variable and without `-p no:cacheprovider` it writes
     `tests/__pycache__/test_order8_assembly.cpython-310-pytest-9.1.1.pyc` and `.pytest_cache`; with both it writes
     nothing. This confirms the issue's [I].
   - "What C62d should check" item 1 now gives the full command, and "How to run" explains both guards.
   - New test `test_exact_check_writes_no_bytecode`. It runs `exact_check.float_vs_exact` in a subprocess on a
     temporary copy with the variable unset and asserts no bytecode. A control step asserts that a plain import does
     write some, so the test is not vacuous.
5. **[minor] `campaign_moments`/`sector_assembly` did not apply the delivered loop-set rule. Applied.**
   - New `_loop_set` follows D3 `assemble.py:81-82` (D2 `:89` is the K = 7 case): loops exactly 3..K,
     5 ≤ K ≤ 8 for `campaign_moments` and 5 ≤ K ≤ order for `sector_assembly`, with no repeats and no non-integers.
   - `campaign_moments` requires `set(ar[s][t]) == {3..K}` for every campaign. An extra loop, a missing loop, a
     non-contiguous set or unequal K now raise ValueError.
   - `sector_assembly` takes K from the means. For K < order (a prefix plan) it cuts every order-indexed output to
     orders 0..K, as the delivered D3 `calculate` does (`:124-133`). Every result now carries `max_order`, `loops`
     and `order`.
   - [V] The verifiers' probe `loopset.py` (order-8 data, `loops=range(3, 8)`, which used to give C8 = 8.218455
     instead of 8.219399) now stops with ValueError. So does the {3, 4, 6} case, which used to give C7 = 3.197.
   - New tests:
     - `test_loop_set_rule_and_sector_order` covers an extra loop, non-contiguous sets, K < 5, K > 8, repeats,
       bools, strings, an empty list, unequal K between campaigns, a non-contiguous set and K > order in
       `sector_assembly`, and the order-8 prefix plan K = 6 (7-entry outputs, bit-equal to the first 7 entries of
       the full-length computation);
     - `test_prefix_plans_against_delivered_d3` checks prefix plans K = 5 and 6, and K = 7, at order 7 against the
       delivered D3 `calculate`, bit for bit, on all seven reported fields.
   - Side change: the means and covariances use `np.asarray(x[L])`, so list replicates work as in the validation.
     It is bit-identical for arrays.
6. **[nit] The helpers did not compose for a power-first `ar`. Applied.**
   - `campaign_moments` keys and sums its output in the order free, power. `sector_assembly` accepts the two sectors
     in either key order and combines them in the order free, power, with loops in the order 3..K.
   - [V] Results are pickle-identical for power-first or loop-reversed inputs (test above).
   - [V] On the C7(2) and C7(3) productions with a power-first `ar`, the result equals the delivered `combine` and
     `calculate` bit for bit: C7(2) = −3876.1260927949916 and C7(3) = −220.35448047392805, with all five delivered
     fields equal (scratchpad `r3/powerfirst.py`).
7. **[nit] Same defect as item 2 (module docstring, `_b2_holds_rational`, README:88-89). Applied with item 2.**
8. **[nit] Same defect as item 4 (`exact_check.py:408`). Applied with item 4.**
9. **[nit] `LRI_C8_D3_HPC_loop/RECON.md` cites stale lines for `power_null_rows`. Not applied here.**
   - That file is the C63d lead's and lies outside `assembly/`, the only folder this track may write.
   - It has been revised since the issue was raised: it now cites `order8_assembly.py:343-361` (RECON.md:1311,
     :1351), `:356-358` and `POWER_PROTOCOL.md:91-105` (RECON.md:572) [R].
   - Round 3 moved them again:
     - `power_null_rows` is now `order8_assembly.py:391-412`, and its `top` dict is at `:408-411`;
     - POWER_PROTOCOL §3 is now `:100-123`, and its `['top']` code line is `:121`.
   - **For the lead:** cite these by name (`order8_assembly.power_null_rows`, POWER_PROTOCOL §3), not by line, or
     update the lines when RECON.md is next edited.
10. **[minor] Same defect as item 1 (POWER_PROTOCOL:14, :95-96; `order8_assembly.py:346`, `:357`; README:447).
    Applied with item 1.** The suggested wording is used almost verbatim in POWER_PROTOCOL §3, with the d=2/3
    sentences quoted in full.
11. **[nit] README understated the b_{2,6} accuracy ("about 56 of 65 digits"). Applied.**
    - The [I] estimate is replaced by the measured figures (§4 table and the bullet under it): stored z^6 against
      the 95-digit reference is 1.7e-57 at d=3 (about 58 significant digits, 56 correct decimal places) and 7.7e-68
      at d=2 (about 69 significant digits). Round 3 printed "57 correct decimal places" here; corrected in place in
      repair round 4 (below).
    - The independent series check is now part of `prepare_low8.py` (`series_check`, `mpmath.taylor` at 130 digits)
      and is recorded in `checks.json`. It gives the same differences, 1.72e-57 and 7.71e-68, and confirms the
      reference contour to 3.3e-91 and 9.7e-92 [V].
12. **[nit] The gamma self-check certified only 3.3e-49 while the rows print 60 and 65 digits. Applied (certified
    rather than shortened).**
    - `gamma_cauchy_check` now uses two contours at dps + 35 digits: radius 0.041 with 128 nodes and radius 0.03 with
      160 nodes. It asserts that the two contours agree to 1e-80 (measured: 4.9e-93 at d=3, 9.7e-100 at d=2) and that
      every printed n_L and a_{L,j} is within half a unit of its last printed digit (measured: at most 0.4947 and
      0.4838 units). Every printed token is therefore correctly rounded. The 1e-46 bound is replaced by this
      assertion.
    - The gamma files and both `two_loop.json` files are unchanged (same md5 and sha256). The order-7 regeneration is
      still byte-identical to the delivered `gamma_d3_7.txt` and `gamma_d2_7.txt`, and to both delivered
      `two_loop.json`. Only the two `checks.json` files changed, by the new check records.

**Unchanged by this round [V]:**
- **Float and complex outputs.** `coefficients`, `jacobians`, `campaign_moments`, `sector_assembly` (every key of the
  round-2 result), `affinity_gate`, `top_slot_gate` and `loop7_gate` give the same bytes as the round-2 module (md5
  55fbc6ee94ed62bb28433cbe123d64f5).
  - Checked on the same 400 random cases as before: the round-2 script `r2/prepost.py`, seed 777, rerun as
    `r3/prepost.py`.
  - Also on 160 further cases with pickled whole results.
  - The only differences are the three new keys `order`, `max_order` and `loops`, the refusals of item 5, the
    prefix-plan truncation of item 5, and the power-first inputs that item 6 now accepts.
- **Order-7 regressions.** The bitwise and production tests still pass against both delivered functions.
- **Data files.** `prepare_low8.py` reproduces `two_loop.json` and the gamma files byte for byte. Its order-7
  regressions still pass.
- **`exact_check_results.json`.** It differs from round 2 only in `module_md5`.
- **Tests.**
  - pytest 9.1.1: 30 passed in about 26 s, run in place with `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`. The
    plain runner also gives 30 PASS.
  - Vendored copy: 21 passed and 9 skipped without `LRI_ROOT`; 30 passed with it.
  - Run against the round-2 files (scratch copy), the new and extended tests fail wherever the round-2 behaviour
    was wrong: 5 failures (loop-set rule, prefix plans, bytecode, null-row wording, certified digits). The two
    documentation tests (int B2, (4,5) control) pass on both, as they should, since they pin behaviour that was
    already right.
- **No stray files.** No `__pycache__`, `.pyc` or `.pytest_cache` exists anywhere in `LRI_C8_shared/` after these
  runs. `NOTE_C63d_to_C62d_2026-10-03.md` and `STATUS_WIP.md` are untouched.

## Repair round 4: disposition (2026-10-03)

One item, raised by the round-3 verification.

1. **[minor] README:270 and :621 said the d=3 stored b_{2,6} has "57 correct decimal places". Applied: it is 56.**
   - [V] From `inputs_d3/checks.json` → `two_loop` (`b26` against `reference_B2[6]`, the 95-digit contour that the
     130-digit series confirms to 3.3e-91): the stored value has 63 decimals, and the first one that differs from
     the reference is decimal 57 (stored 4, reference 2). |stored − reference| = 1.72e-57, which is 3.44 half-units
     at decimal 57 and 0.34 at decimal 56. So the value is correct to 56 decimal places; rounded to 57 they differ
     (…99845 against …99843).
   - "About 58 significant digits" stays: 2 integer digits plus 56 decimals, and −log10(1.72e-57 / 29.26) = 58.2,
     as `series_check.stored_significant_digits` records.
   - Both places now say 56. The bullet under the §4 table also gives the d=2 count: 7.7e-68 on 266.52 is 66
     correct decimal places (1.54 half-units at decimal 67), about 69 significant digits (69.5) [V, same check].
   - Check script: scratchpad `r4/b26_decimals.py` (reads only `checks.json` and `two_loop.json`).

**Unchanged by this round [V]:** only `README.md` changed; every other file keeps its md5 from the table above
(`order8_assembly.py` is still `bdf84d47…`).
- pytest 9.1.1: 30 passed in 24.9 s, in place with `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`.
- `exact_check.py` output equals `exact_check_results.json` byte for byte (all exact checks passed, 5.6 s).
- `prepare_low8.py` reproduces all six input files byte for byte.
- The 400-case check (`r3/prepost.py`, seed 777, against the round-2 module 55fbc6ee…) and the 160 pickled
  cases still pass with no mismatch, so the float and complex outputs are unchanged.
- No `__pycache__`, `.pyc` or `.pytest_cache` in `LRI_C8_shared/`. `NOTE_C63d_to_C62d_2026-10-03.md` and
  `STATUS_WIP.md` are untouched.
