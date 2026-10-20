# Input contract: raw moment coefficients → `lri_framework`

This file is the agreed interface between the integration agents (`engine/`, `direct/`, and the
framework's own one-dimensional code) and the assembler `lri_framework.py` /
`run_framework.py`. Read it before producing data for the framework.

## 1. What a raw scalar is

A raw scalar is one coefficient `[eps^p l^k]` (with `l = log eps`) of the small-eps expansion of
one derivative of one raw ordered moment, at `v = 1`, `delta = 0`, `eta = 0`:

    <M><n>[_<deriv>][eps^<p> l^<k>]        e.g.  A5_vd[eps^0 l^1],  Q4_E[eps^1 l^0],  Z4[eps^-2 l^0]

* `M` is `A` (odd `n`), `Z` or `Q` (even `n`).
* `deriv` is a string of the letters `v`, `d`, `E`, in any order, with `E` at most once:
  * `v` is d/dv at v = 1;
  * `d` is d/d(delta) at delta = 0;
  * `E` is the endpoint-source derivative d/d(eta) at eta = 0.
* **Derivative convention** (default): the value is the plain derivative. `A3_dd` is
  d²A3/d(delta)², not the Taylor coefficient. `convention="taylor"` (CLI `--convention taylor`)
  accepts Taylor coefficients instead.
* **The endpoint source** `E` is two-sided:

      E I = ∫ W_n · Σ_i q_i [ f_delta(X_i) ± f_delta(1 − X_i) ],      q_i = (−1)^{i+1},
      f_delta(r) = (r^delta − 1)/delta    (f_0 = log r).

  The sign is `+` (U^odd) for `A` and `−` (U^even) for `Z` and `Q`.
* **`d` on an `E` atom also differentiates the `f_delta` inside the source.** For example
  `A3_dE` = d/d(delta) of the whole of `∫ W · source`, which is the engine's insertion
  `S2 E1 + E2/2`. The framework's exact two-kink sector follows this rule.
* Hard core: only consecutive gaps, `X_{i+1} − X_i ≥ eps`.
* `A1`, `Z2` and `Q2` (with all their derivatives) are exact and built into the framework. Do
  not supply them. If you do, they are only compared with the exact values, and any difference
  appears as a warning.

## 2. Which scalars are mandatory

Every name in `out/required_inputs_D4.json` (`flat_names`, 116 scalars, through C7) or in
`out/required_inputs_C8.json` (201 scalars, through C8) is **mandatory**. The 85 scalars that C8
needs beyond C7 are listed, by new input, in `out/C8_new_scalars.json` (phase 3), with the 45 our
engine has already computed and the 40 it has not. This includes:

* the positive-eps coefficients of A3, Q4 and Z4, for example `A3[eps^2 l^0]`,
  `A3_v[eps^2 l^1]` and `Q4[eps^2 l^1]`;
* **structural zeros.** If your pole analysis shows that a listed coefficient vanishes (for
  example `A3[eps^-1 l^1]`), report it explicitly as an exact zero:
  `{"value": "0", "sigma": "0", "exact": true}`.

The framework runs in **strict mode** by default. If any required scalar is absent, it raises
`MissingInputError` (CLI exit code 2) and names every absent scalar. An absent scalar is never
treated as zero. `strict=False` (CLI `--allow-missing`) computes what it can instead, and
reports every output that depends on an absent scalar as `MISSING`, with the names it needs.
The CLI option `--zero NAME` declares an exact zero by hand; the declaration is recorded in the
output.

Other rules:
* A coefficient below the structural lowest power must be zero. A nonzero one is an error.
* Log powers `k > 1` are ignored by the beta functions. They are kept only when
  `Framework(kmax=...)` asks for the higher-log check.
* A supplied scalar that no output needs is listed under `unused`.

## 3. File formats (all values are decimal strings or numbers)

### 3a. Canonical format `lri-framework-raw/1` (preferred)

```json
{
  "format": "lri-framework-raw/1",
  "convention": "derivative",
  "producer": {"component": "engine", "run": "runs/prod6"},
  "scalars": {
    "Q8[eps^0 l^1]":    {"reps": ["15442.513", "15442.471", "15442.502", "15442.488", "15442.495", "15442.480"],
                         "mean": "15442.4915", "sigma": "0.0061", "sys": "6e-11", "block": "Q8_base|k=0"},
    "A3[eps^0 l^1]":    {"value": "6", "sigma": "0", "exact": true},
    "A3[eps^-1 l^1]":   {"value": "0", "sigma": "0", "exact": true},
    "A3_dd[eps^0 l^1]": {"value": "-31.037482023148931616484414220263917", "sigma": "1e-30"}
  },
  "covariance": [
    {"names": ["A3_dd[eps^0 l^1]"], "matrix": [["1e-60"]]}
  ]
}
```

* **Replicated scalar** `{"reps": [x_1 … x_R], "mean"?, "sigma"?, "sys"?, "block"?}`.
  * `x_r` is a complete, unbiased estimate of the scalar from **replicate r alone**: random shift
    r, summed over all sectors and sector chunks, with the channels combined exactly as for the
    mean (the engine's `assemble_replicates`).
  * **`block`** names a replicate block, for the engine one job, for example
    `"Q8_base|k=0"`.
    * Within a block, replicate r of every scalar comes from the same random shift. The
      scalars are then correlated, and the framework keeps that correlation.
    * Different blocks must use independent random streams. The engine v2 derives a different
      seed for every (tier, group, k, chunk).
    * All scalars of a block share one R ≥ 2. The default block is `"default"`, which means one
      shared shift index for every replicated scalar.
  * `mean`, if given, must equal the mean of `reps` to within 1e-10 × max|x_r|.
  * `sigma`, if given, is the producer's statistical standard error. It is informational: it
    is compared with the replicate standard error, and the ratio appears in the metadata.
  * **`sys`** is an independent systematic error, for example the engine's precision floor. It
    is added in quadrature through the gradient.
  * A coefficient that does not depend on the shift may repeat its value R times, or be given as
    a fixed scalar.
* **Fixed scalar** `{"value", "sigma"?, "exact"?}`: an exact value, or an external value with an
  independent error. Fixed scalars are held constant in every replicate.
* **`covariance`** (optional) is a list of blocks `{"names": […], "matrix": [[…]]}`.
  * It is given in the file's convention and applies to the means.
  * A name may appear in at most one block. If a fixed scalar is in a block and also has a
    `sigma`, the two must agree.
  * For a replicated scalar, a covariance block replaces its replicate sample covariance in the
    linear estimate. Its `sys` is still added. The per-replicate standard error is unaffected.
* `null` for a value means not available. It counts as absent.
* A non-finite number (NaN or ±inf) anywhere is an error: a value, a replicate, a sigma, a
  `sys` or a covariance entry. Report a failed coefficient as `null`, never as NaN.

### 3b. Flat format (no replicates)

```json
{"A5_vd[eps^0 l^1]": "1.234", "Q4[eps^0 l^1]": ["-4.5", "1e-12"], "A3[eps^-1 l^1]": {"value": 0, "exact": true}}
```

An entry is a value, a `[value, sigma]` pair, or one of the dict entries of 3a, including
`{"reps": …}`. Independent sigmas can also come from `--sigmas file.json` (`{name: sigma}`). A
covariance can come from `--cov file.json` (`{"names": […], "matrix": […]}` or a list of
blocks).

### 3c. Engine `campaign.py collect` outputs (adapter `load_engine_results`)

The engine v2 `collect` writes two files. Both can be passed to `--raw`.
* **`framework_input.json`** is already in the canonical format of 3a. It has one replicate
  block per job (moment, eps power), a `sys` floor on every replicated scalar, and exact zeros.
  It is restricted to the needed coefficients. This is the preferred input.
* **`results.json` (v2, `"engine_pipeline": "v2"`)** is read by the adapter:

```json
{"engine_pipeline": "v2", "complete": true, "problems": [],
 "results":    {"Q8_base": {"0,1": [mean, err]}, "A3_base": {"-1,1": [0.0, 0.0]}},
 "replicates": {"Q8_base": {"0,1": [x_1, …, x_R]}},
 "errors":     {"Q8_base": {"0,1": {"stat": s, "floor": f, "l1": a, "block": "Q8_base|k=0", "zero": false}},
                "A3_base": {"-1,1": {"stat": 0, "floor": 0, "block": "A3_base|k=-1", "zero": true}}},
 "zeros":      ["A3[eps^-1 l^1]"]}
```

* Each coefficient becomes a replicated scalar `{"reps", "mean", "sigma": stat, "sys": floor,
  "block"}`.
* A coefficient with `errors[…]["zero"]`, or listed in `zeros`, becomes an exact zero. These are
  coefficients that the engine's pole analysis proves to vanish. An earlier draft listed them as
  `"structural_zeros": ["group:k,j"]`, and that layout is accepted too.
* `complete: false` or a non-empty `problems` list makes the CLI print a warning.
* On the same data, the two engine files give identical results through the framework (checked
  2026-10-03).

**Phase 1 (no `replicates`):** `{"results": {group: {"k,j": [mean, err]}}}` becomes
`[mean, err]` entries with independent errors. The phase-1 engine omitted structural zeros, so
strict mode lists them (A3[eps^-1 l^1], A3[eps^2 l^1] and Z4[eps^-2 l^1] for pilot5). They are
then declared with `--zero`. The archive-derived data omit the same three.

**Common to both:**
* `"k,j"` means eps^k l^j.
* A group name is the flat prefix, with `_base` meaning no derivative, for example `A3_base`,
  `A5_vE` or `Q4_dE`. A run suffix `_N<digits>` is stripped. The spec form, for example
  `EA5_vd`, is also accepted.
* `"zeros": [flat names]` is also accepted for proved structural zeros.

### 3d. Spec-agent layout (adapter `load_spec_raw`)

`{"A5_vd": {"-1": {"0": v, "1": v}}, "EA3_v": {…}, "Q8_base": {…}}`, or the archive layout
`{"raw": {atom: {p: {"coefficients_by_log_power": {…}}}}}`. Values may be pairs, and `null`
counts as absent.

## 4. What comes back

`run_framework.py --raw FILE [--raw FILE2 …] --order D4 --out result.json` merges all files.
A name given in two files is an error, and the formats are auto-detected.

**Replicate blocks of several files (phase 3).** A replicate block id that occurs in two files
would pair their replicates as one random shift. That is an error (CLI exit 4) unless the files
come from independent runs, for example the production and a later C8 run: then pass
`--independent-files` (`merge_inputs(..., independent=True)`), which renames every block to
`<file stem>:<block>`. `independent=False` keeps the ids (parts of one run).

The run returns:
* the 25 beta inputs (35 at order C8);
* the invariants D1–D4 and T1–T3 (T4 at order C8);
* C1–C7 (C8 = 8 T4 at order C8);
* the eq:C8assembly pieces (phase 3): `B_old8` at both orders; at order C8 also `B_done8`,
  `C8_asm` and `C8_partial` (section 4a);
* the difference from the claimed closed forms of D2–D4, C3–C7, and the pull (none for C8:
  the archive's C8 numbers are compared only in sealed comparison steps).

**Without replicates, or when replicate blocks have different R**, each output carries
`value` and `sigma`.
* `sigma` is the linear propagation g^T Σ g, using the exact gradients.
* Σ is built from:
  * the independent sigmas;
  * the systematic floors;
  * the covariance blocks;
  * for each replicate block b, its sample covariance divided by R_b.
* Different replicate blocks are taken as independent.

**With replicates and one common R**, the full nonlinear assembly is run once per replicate.
Replicate r of every block is paired by index; this is valid because blocks are independent. Each
output then carries:
* `value`, the assembly at the mean inputs, and `sigma_linear`, its linear error as above;
* `rep_mean` and `rep_se`: the mean and standard error, sd/√R, of the R per-replicate
  assemblies;
* `sigma_extra`: the linear error of what the replicates do not carry, that is the fixed
  scalars' errors and the systematic floors;
* `sigma_rep_total` = √(rep_se² + sigma_extra²);
* `nonlinearity` = rep_mean − value. It should be much smaller than rep_se.

The replicate standard error has R − 1 degrees of freedom, so with R = 6 it is itself uncertain
by about 30 %.

`sigma_linear` and `sigma_rep_total` agree exactly, up to the nonlinearity, when all replicated
scalars share one block. With several independent blocks they agree only statistically: the
per-replicate scatter contains cross-block sample covariances, whose expectation is zero.

**Replicate blocks with different R (phase 3).** By default the per-replicate assembly is
refused and only the linear errors are given. With `mixed_R="group"` (CLI `--mixed-R group`) the
blocks are grouped by R; each group g is assembled R_g times with only its own scalars varied (the
others at their means). Then rep_se² = Σ_g se_g² (the groups are independent),
nonlinearity = Σ_g (mean_g − value), rep_mean = value + nonlinearity, and each output carries its
Welch–Satterthwaite degrees of freedom (`dof`).

All gradients are taken with respect to the inputs in the file's convention
(`Result.gradient`).

### 4a. The C8 pieces (phase 3)

C8 = 8 T4 is affine in the ten new inputs, with the constant coefficients of eq:C8assembly
(`derive_C8.py`). The module reports, as outputs next to the C_n:

| output | definition | MISSING when |
|---|---|---|
| `B_old8` | appendix polynomial in the 25 old inputs (61 terms, `B_OLD_C8_TERMS`) | an old input is absent |
| `B_done8` | B_old + 4W + 2S + 3/32 L3 − 1/4 M21 + 1/2 M12 − 1/16 N2 | any of the six is absent |
| `C8_asm` | B_old + all ten terms of eq:C8assembly | any new input is absent |
| `C8_partial` | B_old + the terms of the new inputs that are available | an old input is absent |

* `C8_partial` never sets an absent input to zero: the absent ones are **not** included and are
  listed in `res.c8_info["partial_missing"]` with the scalars each needs. It is a partial sum,
  not an estimate of C8.
* Check made on every C8-order assembly: `C8_asm` equals 8 T4 recomputed with the exact tree data
  b3(0,0) = 1, h2 = −1. This is an algebraic identity, for values and gradients, at any point, and a
  failure raises. `c8_info["8T4_minus_8T4_exact_tree"]` gives the effect of the supplied tree data
  (the engine's A3[ε⁰ℓ¹] = 5.999999999999999 instead of the exact 6: 1.6e-12 on C8 at our point).
* `c8_combine(res, extra)` (CLI `--beta-extra FILE`) adds beta-level values of absent new inputs
  from an independent source, for example the framework's semi-analytic W:
  `{"W": ["-37.708111514952555112588560001910915", "1e-38"]}`. Their errors add in quadrature,
  and giving an input the assembly already computes is an error. For a `ReplicateResult` it also
  gives the per-replicate statistics, with the extras held fixed.

## 5. Python entry points

```python
import lri_framework as L
fw  = L.Framework("D4", dps=50)
rr  = fw.from_replicates("results.json")          # path, canonical dict, or flat dict; strict
res = fw.from_raw(L.merge_inputs([L.load_inputs("a.json"), L.load_inputs("b.json")], zeros=[...]))
fw.required_names()                               # the 116 mandatory raw names
fw8 = L.Framework("C8", dps=50)                   # 201 names; outputs also B_old8, B_done8, C8_asm, C8_partial
r8  = fw8.from_raw(data, strict=False)            # partial: absent new inputs MISSING, C8_partial + c8_info
rg  = fw8.from_replicates(data, mixed_R="group")  # replicate blocks with different R
L.c8_combine(rr, {"W": ["-37.7081115149525551125885600019109", "1e-38"]})   # beta-level extras
data = L.merge_inputs([L.load_inputs("prod.json"), L.load_inputs("c8.json")], independent=True)
```
