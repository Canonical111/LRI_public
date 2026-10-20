#!/usr/bin/env python3
"""Recompute a C8(2) result from its own fields and compare the whole result tree (PLAN component E; C7I-02,
C7I-11; A-ASM-7). combine.py and verify_delivery call it.

What is recomputed (and compared leaf by leaf with the stored value):
  * from the stored means (and inputs/two_loop.json, whose sha256 must equal the result's assembly.two_loop_sha256),
    with the vendored assembly: the coefficients C = F(free + power), the power-free coefficients and the power
    differences, C_full, power_free_C and power_correction, and the gates (top-slot, loop-7, float affinity) at the
    means;
  * from the stored covariance: the standard errors and sampling_standard_error; from the stored power difference
    errors: power_correction_se; from these, the lower-order checks and the power null checks (with the PP8 markers);
  * from error_by_loop's variances: the shares and SEs, whose variances must sum to Var(C_order);
  * the module, HANDOFF, two-loop and POWER_PROTOCOL hashes;
  * for a combination (combine.py; O10): from the stored per-batch values, the batch count, dof = count - 1, the
    chi-square about the combined C_order (null for one batch), final (all planned batches) and the status text.
What is checked by an identity, because the result holds no statistics to recompute it from (O10): power_free_se and
power_free_correction_covariance must satisfy Var(C_full) = power_free_se^2 + power_correction_se^2 +
2 power_free_correction_covariance (the [order, order] element of V_C = V_pf + V_Delta + cross + cross^T, sector
assembly), to 1e-10 of the largest of its terms.
What is fixed (X16, Stage-6 fix round 1): dimension 2, epsilon "2s-2" and assembly.half_d = assemble.HALF_D (1), the
values the recomputation itself runs at (d = 2, d/2 = 1), so a result labelled with another dimension, epsilon or
half_d (whose numbers would then not be what was recomputed) fails; the expected tree carries the fixed values.
What has exact key sets and shapes only (closed schemas; an added or deleted key fails): power_protocol, assembly,
campaigns, bootstrap, means, error_by_loop, the half streams, the coefficient vectors, the covariance, a combination's
batches block (count, planned, per_batch [label, C_order_full, sampling_se], chi2_about_combined, dof) and its
metadata (final, status, design, inputs_manifest_sha256, numerics, rates_identity, all present together), and a
test-only result's test_partial block (exactly the physical keys, plus that combination block for a combination).
A changed input (a mean, say) is caught through what it feeds: a change that keeps every derived value within the
tolerance below is consistent with the result by definition. The expected tree is the stored tree with every
recomputed block replaced. The comparison then requires, leaf by leaf: floats equal to a relative 1e-10 of their
sibling scale (the largest |float| among the leaf and its siblings, at least 1e-2 inside the gates and the power null
checks, whose rounding-level diagnostics differ between machines); every other leaf identical; the same keys
everywhere; and the top-level keys equal to the keys assemble.py writes (plus the campaign and combination metadata it
may add). A test-only result is checked the same way under test_partial, and every key of test_partial is null at the
top level.
Rounding-level leaves on any BLAS kernel family (F6, Stage 5). The affinity gate's linear_response_residual[k] is
|C_k(m+delta) - C_k(m) - sum_L J_L(m) delta_L|, rounding noise of three quantities whose sums run in the BLAS kernels
the machine selects (the vendored gemv J_L @ delta_L, and np.convolve, which numpy evaluates with the BLAS ddot, inside
the coefficients; OpenBLAS DYNAMIC_ARCH picks AVX2 kernels on the AMD nodes and AVX-512 ones on the Intel login nodes).
Each stored residual[k] must therefore equal its recomputation within RESIDUAL_ULPS eps M_k, eps = 2^-52 and
M_k = |C_k(m)| + |C_k(m+delta)| + sum_L |J_L(m)| |delta_L| (the magnitudes the residual is a difference of, with the
gate's own perturbation delta: rel_step and seed are the vendored affinity_gate's defaults, read from its signature).
RESIDUAL_ULPS = 64 is about 10x the largest spread measured: 13 Stage-5 results assembled on AMD Zen 2 and Zen 3 nodes
and recomputed on the Mac (arm64) differ by at most 6.5 eps M_k (drill drA; at most 2.6 for the others), and the
smoke's residual[8] (1.82e-12 assembled on AMD, 8.64e-12 recomputed with the AVX-512 kernels of a Cascade Lake login
node) by 0.47 eps M_8. A residual is reported by the vendored gate and never gated, so the bound keeps the stored value honest
and nothing more. The power null checks (/power_null_checks and /test_partial/power_null_checks: at order 3 the power
difference is a rounding-level difference of two O(1) coefficients, exactly zero by the weights) get the 1e-2 scale
floor of the gates, so rounding-level values there match to an absolute 1e-12, the vendored protocol's own rounding
threshold (ORDER3_ROUNDING).
Types and tolerance sources (Y11, Stage-6 fix round 2, S6D-R2-03). The expected tree starts as a copy of the stored
result, so a copied value must never set the tolerance of a recomputed one: a metadata field stored as a huge number
(scope = 1e30, say) used to become a sibling float of C<n>_full and widen its tolerance to 1e20. Now (1) every field's
type is validated before anything is recomputed (field_types): the metadata (scope, schema, epsilon, the hashes, backend,
numerics, rates_identity, status, design, ...) are strings, flags booleans, counts integers, build/allocation/merged
hashes objects, every stored number finite and not a boolean; (2) the tolerance scale of a leaf comes only from
designated scientific fields (scale_keys): at the root of a result block the coefficient family C<n>_full,
power_free_C<n> and power_correction (recomputed from the means; power_correction is their difference), every other
root leaf (the standard errors, the copied power_free_se and power_free_correction_covariance, any metadata) only its
own magnitude; inside the blocks the recomputation replaces whole (gates, lower_order_checks, power_null_checks) all
their siblings, which are all recomputed; everywhere else (error_by_loop rows, whose variance is copied; campaigns;
bootstrap; batches; metadata objects) the leaf's own magnitude; and the floats of one list its elements (each list is
wholly recomputed or wholly copied). (3) The variance identity's tolerance is bounded by the stored statistics
themselves: power_free_correction_covariance must satisfy the Cauchy-Schwarz bound |cov| <= power_free_se x
power_correction_se (a covariance of the sector assembly), so huge cancelling values cannot pass the identity at a
loose tolerance.
Pulls (R3, Stage-6 residual after fix round 2). A pull is a ratio p = (x - r)/sigma, sigma = sqrt(s^2 + t^2): a power
null row's and the top row's p = delta/se (r = t = 0), a lower-order row's p = (estimate - reference)/sqrt(sampling_se^2 +
reference_se^2), its secondary's the same with the secondary reference. Its inputs x and s are leaves compared with
tolerances tau_x and tau_s (the rule above: REL x their scale, at least the 1e-2 floor inside power_null_checks), so a
result whose x and s pass may hold any x' = x + dx, |dx| <= tau_x, s' = s + ds, |ds| <= tau_s, and its pull
p' = (x' - r)/sigma' then differs from the recomputed p by
  |p' - p| <= |x' - x|/sigma' + |x - r| |1/sigma' - 1/sigma| <= tau_x/sigma_min + |p| sigma (1/sigma_min - 1/sigma_max),
sigma_min = sqrt(max(s - tau_s, 0)^2 + t^2), sigma_max = sqrt((s + tau_s)^2 + t^2) (infinite when sigma_min = 0). That
bound (pull_bound) is the pull's tolerance when it exceeds REL x its scale: the comparison with a fixed relative
tolerance amplified a rounding-level difference of delta by 1/se (the design-chain partial of Stage 5 failed on the Mac
with a null row's pull 4e-10 relative apart while its delta was 3.6e-15 absolute apart, within its 6e-12 tolerance).
Because the bound is loose by design, every stored pull must ALSO be the pull of its own stored inputs (pull_problems:
to a relative PULL_REL, i.e. the same IEEE operations; the assembler computes it from exactly those floats), so a pull
changed alone is rejected however small the change.
Covariance (Z8, Stage-6 fix round 3, S6D-R3-01). The recomputation uses only the covariance's diagonal (the standard
errors) and its [order, order] element, so its off-diagonal elements were copied unchecked: a result with
covariance[3][8] = 1e30 and covariance[8][3] unchanged verified. The stored matrix C must now be a covariance matrix to
rounding (covariance_problems, before anything is recomputed). The assembler forms C = sum over sectors and loops of
J V J^T (V a replicate covariance, positive semidefinite), whose floating-point evaluation is symmetric and PSD up to
rounding relative to the entries' own scale sqrt(c_ii c_jj), so the checks are in correlation units: with D the
largest variance, tau^2 = EPS D its rounding unit, s_k = sqrt(max(c_kk, 0)) and t_k = max(s_k, tau) (tau stands in for
a zero variance: the rows of the orders below 3 are exactly zero), (a) |c_ij - c_ji| <= COV_REL t_i t_j, (b) c_kk >=
-COV_REL t_k^2 and (c) the smallest eigenvalue of T^-1 (C + C^T)/2 T^-1 >= -m COV_REL, m = order + 1 (an entrywise
perturbation of at most COV_REL moves an eigenvalue by at most m COV_REL). COV_REL = 1e-10, REL's relative tolerance:
the 16 stored results (benchmarks/ and tests/fixtures/verify_result_cross_machine/, assembled on AMD and Intel nodes)
are asymmetric by at most 11.5 eps (2.6e-15) of sqrt(c_ii c_jj), and their correlation matrices' smallest eigenvalue is
at least 0.02 (orders 3..8; the zero rows of orders 0..2 exactly zero). The same class (sign_problems): the copied
standard errors (power_difference_errors, the campaigns' sampling_se, the bootstrap's full_se and correction_se) must be
>= 0 and every error_by_loop variance >= -REL Var(C_order).
Usage: python3 -B tools/verify_result.py RESULT.json [--output FILE]; exit status 0 when the result verifies."""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble as asm  # noqa: E402
from common import ROOT, digest  # noqa: E402

REL = 1e-10
# X16: the fixed scientific labels of a C8(2) result, the values assemble.combine writes and the recomputation runs at
DIMENSION = 2
EPSILON = '2s-2'
assert asm.HALF_D * 2 == DIMENSION, 'assemble.HALF_D is d/2 of the dimension this verifier fixes'

GATE_SCALE_FLOOR = 1e-2  # gate diagnostics hold rounding-level floats (about 1e-16) that differ between machines
FLOORED = ('/gates', '/test_partial/gates', '/power_null_checks', '/test_partial/power_null_checks')  # F6: null checks too
RESIDUAL_ULPS = 64  # linear_response_residual[k]: within 64 eps M_k (module docstring); largest spread measured 6.5 (F6)
EPS = 2.0 ** -52
PULL_REL = 1e-12  # R3: a stored pull equals the pull of its own stored inputs to this relative (the same IEEE operations)
COV_REL = 1e-10  # Z8: the covariance's rounding tolerance in correlation units (module docstring, "Covariance"); largest
#                  asymmetry measured on the 16 stored results 11.5 eps = 2.6e-15
CORE = ('schema', 'dimension', 'order', 'epsilon', 'sampling_standard_error', 'coefficients', 'standard_errors',
        'covariance', 'power_free_se', 'power_correction', 'power_correction_se', 'power_free_correction_covariance',
        'power_differences', 'power_difference_errors', 'means', 'error_by_loop', 'campaigns', 'half_streams', 'bootstrap',
        'lower_order_checks', 'power_null_checks', 'gates', 'power_protocol', 'assembly', 'scope')
OPTIONAL = {'source_manifest_sha256', 'merged_sha256', 'backend', 'build', 'test_only', 'allocation', 'final',
            'accepted_tool_changes', 'test_partial', 'batches', 'status', 'design', 'numerics', 'rates_identity',
            'inputs_manifest_sha256'}
# The metadata of a combination (combine.py), present together (closed schema; O10).
COMBINED = {'batches', 'final', 'status', 'design', 'inputs_manifest_sha256', 'numerics', 'rates_identity'}
BATCH_KEYS = {'count', 'planned', 'per_batch', 'chi2_about_combined', 'dof'}


def core_keys(order: int) -> set:
    return set(CORE) | {f'C{order}_full', f'power_free_C{order}'}


def combination_status(count: int, planned: int) -> str:
    """The status text of a combination of `count` of `planned` batches (combine.py writes it; verify recomputes it)."""
    if count < planned:
        return f'PARTIAL combination of {count} of {planned} planned batches: interim, not the final result'
    return f'final combination of all {count} planned batches'


def _number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def residual_scale(means: dict, J: dict, B2, n: int) -> list[float]:
    """M_k = |C_k(m)| + |C_k(m+delta)| + sum_L |J_L(m)| |delta_L| for the affinity gate's own perturbation of the loops
    5..n (assemble.gates' loops), delta_L = rel_step (|m_L| + 1) N(0, 1) drawn in loop order from default_rng(seed),
    with rel_step and seed the defaults of the vendored affinity_gate (F6; module docstring)."""
    oa = asm.vendored()
    sig = inspect.signature(oa.affinity_gate)
    rel, seed = sig.parameters['rel_step'].default, sig.parameters['seed'].default
    rng = np.random.default_rng(seed)
    pert = {k: np.asarray(v).copy() for k, v in means.items()}
    S = np.zeros(n + 1)
    for L in [L for L in range(5, n + 1) if L in means]:
        a = np.asarray(means[L])
        d = rel * (np.abs(a) + 1) * rng.standard_normal(a.shape)
        pert[L] = a + d
        S += np.abs(np.asarray(J[L], float)) @ np.abs(d)
    c0 = np.abs(oa.coefficients(means, B2, n, asm.HALF_D))
    c1 = np.abs(oa.coefficients(pert, B2, n, asm.HALF_D))
    return [float(x) for x in c0 + c1 + S]


def recompute(block: dict) -> dict:
    """The stored block with every derivable field replaced by its recomputation."""
    return _recompute(block)[0]


def _recompute(block: dict) -> tuple[dict, dict]:
    """(recomputed block, absolute bounds of its rounding-level leaves by path: linear_response_residual[k] within
    RESIDUAL_ULPS eps M_k; F6)."""
    oa = asm.vendored()
    out = json.loads(json.dumps(block))
    out['dimension'], out['epsilon'] = DIMENSION, EPSILON  # X16: fixed labels, compared leaf by leaf (type included)
    n = int(block['order'])
    B2, b2sha = asm.two_loop()
    if block['assembly']['two_loop_sha256'] != b2sha:
        raise ValueError('the result was assembled with another inputs/two_loop.json')
    loops = range(3, n + 1)
    means = {s: {L: np.asarray(block['means'][s][str(L)], float) for L in loops} for s in asm.SECTORS}
    tot = {L: means['free'][L] + means['power'][L] for L in loops}
    mu = oa.coefficients(tot, B2, n, asm.HALF_D)
    pf = oa.coefficients(means['free'], B2, n, asm.HALF_D)
    out['coefficients'] = mu.tolist()
    out['power_differences'] = (mu - pf).tolist()
    out[f'C{n}_full'] = float(mu[n])
    out[f'power_free_C{n}'] = float(pf[n])
    out['power_correction'] = float(mu[n] - pf[n])
    cov = np.asarray(block['covariance'], float)
    se = np.sqrt(np.maximum(0, np.diag(cov)))
    out['standard_errors'] = se.tolist()
    out['sampling_standard_error'] = float(se[n])
    dse = np.asarray(block['power_difference_errors'], float)
    out['power_correction_se'] = float(dse[n])
    out['lower_order_checks'] = asm.lower_order_checks(mu, se, n)
    out['power_null_checks'] = asm.power_null_checks(mu - pf, dse, n)
    J = oa.jacobians(tot, B2, n, asm.HALF_D)
    out['gates'] = asm.gates(tot, J, B2, n)
    bounds = {f'/gates/affinity/linear_response_residual[{k}]': RESIDUAL_ULPS * EPS * m
              for k, m in enumerate(residual_scale(tot, J, B2, n))}
    bounds.update(pull_bounds(out))  # R3: a pull's tolerance follows from its inputs' tolerances
    var = float(cov[n, n])
    # O10: power_free_se and power_free_correction_covariance are not recomputable from the result; they must satisfy
    # the variance identity of the sector assembly at [n, n] (with the stored covariance and power_correction_se).
    pfse, cross = float(block['power_free_se']), float(block['power_free_correction_covariance'])
    # Y11: a covariance of the sector assembly obeys Cauchy-Schwarz, which bounds the identity's terms by the statistics
    # (so huge cancelling values cannot meet the identity at a tolerance they widened themselves)
    if not (pfse >= 0 and abs(cross) <= pfse * abs(float(dse[n])) * (1 + 1e-9) + 1e-300):
        raise ArithmeticError(f'power_free_correction_covariance {cross!r} exceeds power_free_se x power_correction_se = '
                              f'{pfse * abs(float(dse[n]))!r} (Cauchy-Schwarz; a negative power_free_se is no standard error)')
    terms = (pfse * pfse, float(dse[n]) ** 2, 2 * cross)
    if not all(map(math.isfinite, terms)) or not abs(sum(terms) - var) <= REL * max(abs(var), *map(abs, terms), 1e-300):
        raise ArithmeticError(f'variance identity fails: power_free_se^2 + power_correction_se^2 + 2 power_free_correction_covariance = '
                              f'{sum(terms)!r}, Var(C{n}_full) = {var!r}')
    if 'batches' in block:  # O10: the combination's statistics from its stored per-batch values
        b = block['batches']
        per = b['per_batch']
        c = out[f'C{n}_full']
        k = len(per)
        chi2 = sum((float(x[f'C{n}_full']) - c) ** 2 / float(x['sampling_se']) ** 2 for x in per) if k > 1 else None
        out['batches'] = dict(b, count=k, dof=k - 1, chi2_about_combined=chi2)
        out['final'] = k == b['planned']
        out['status'] = combination_status(k, b['planned'])
    ebl = block['error_by_loop']
    tsum = 0.
    for s in ebl:
        for L, row in ebl[s].items():
            v = float(row['variance'])
            tsum += v
            out['error_by_loop'][s][L] = dict(variance=v, share=v / var if var > 0 else None, se=math.sqrt(max(0., v)))
    if not abs(tsum - var) <= REL * max(abs(var), 1e-300):
        raise ArithmeticError(f'error_by_loop variances sum to {tsum}, not Var(C{n}) = {var}')
    out['power_protocol'] = dict(block['power_protocol'], sha256=asm.power_protocol_sha256())
    out['assembly'] = dict(block['assembly'], module_sha256=digest(asm.VENDOR / 'order8_assembly.py'),
                           handoff_sha256=digest(asm.VENDOR / 'HANDOFF_assembly.json'), two_loop_sha256=b2sha, half_d=asm.HALF_D)
    return out, bounds


def leaf_tolerance(row: dict, key: str, row_path: str) -> float:
    """The tolerance compare() applies to the expected float row[key] at row_path/key: REL x max(|row[key]|, its scale
    keys' floats (scale_keys), GATE_SCALE_FLOOR on a FLOORED path)."""
    sib = max([abs(row[j]) for j in scale_keys(row_path, key, row) if isinstance(row[j], float) and math.isfinite(row[j])] + [0.])
    return REL * max(abs(float(row[key])), sib, GATE_SCALE_FLOOR if f'{row_path}/{key}'.startswith(FLOORED) else 0.)


def pull_bound(p: float, tau_x: float, s: float, tau_s: float, t: float = 0.) -> float:
    """R3: the largest |p' - p| of a pull p = (x - r)/sqrt(s^2 + t^2) when x moves by at most tau_x and s by at most tau_s
    (r and t fixed): tau_x/sigma_min + |p| sigma (1/sigma_min - 1/sigma_max) (module docstring, "Pulls"); inf when
    sigma_min = 0 (the stored pull is then held by pull_problems alone)."""
    sigma = math.hypot(s, t)
    smin, smax = math.hypot(max(s - tau_s, 0.), t), math.hypot(s + tau_s, t)
    if not smin > 0:
        return math.inf
    return tau_x / smin + abs(p) * sigma * (1 / smin - 1 / smax)


def pull_rows(block: dict):
    """(path, row, pull key, x, s, t) for every pull of a result block whose row holds numbers: the power null rows and
    the top row (x = delta, s = se), the lower-order rows (x = estimate, s = sampling_se, t = reference_se) and their
    secondary rows (the parent's estimate and sampling_se, the secondary's reference_se). x, s and t are (row, key)."""
    pnc = block.get('power_null_checks')
    if isinstance(pnc, dict):
        for i, row in enumerate(pnc.get('null_rows') or []):
            yield f'/power_null_checks/null_rows[{i}]', row, ('delta', row), ('se', row), None, None
        yield '/power_null_checks/top', pnc.get('top'), ('delta', pnc.get('top')), ('se', pnc.get('top')), None, None
    for i, row in enumerate(block.get('lower_order_checks') or []):
        path = f'/lower_order_checks[{i}]'
        yield path, row, ('estimate', row), ('sampling_se', row), ('reference_se', row), ('reference', row)
        if isinstance(row, dict) and isinstance(row.get('secondary'), dict):
            sec = row['secondary']
            yield f'{path}/secondary', sec, ('estimate', row), ('sampling_se', row), ('reference_se', sec), ('reference', sec)


def _num(v) -> bool:
    return isinstance(v, float) and not isinstance(v, bool) and math.isfinite(v)


def pull_bounds(expected: dict) -> dict:
    """R3: {path of a pull: pull_bound(...)} for every numeric pull of the expected (recomputed) block, its inputs'
    tolerances taken as compare() takes them (leaf_tolerance at the inputs' own rows)."""
    out = {}
    for path, row, (xk, xrow), (sk, srow), t, _ in pull_rows(expected):
        if not (isinstance(row, dict) and _num(row.get('pull')) and _num(xrow.get(xk)) and _num(srow.get(sk))):
            continue
        xpath = path.rsplit('/secondary', 1)[0] if xrow is not row else path
        tv = float(t[1][t[0]]) if t is not None and _num(t[1].get(t[0])) else 0.
        out[f'{path}/pull'] = pull_bound(row['pull'], leaf_tolerance(xrow, xk, xpath), float(srow[sk]), leaf_tolerance(srow, sk, xpath), tv)
    return out


def pull_problems(block: dict) -> list[str]:
    """R3: every stored numeric pull must be the pull of its own stored inputs (a power row's delta/se, as the vendored
    power_null_rows computes it; a lower-order row's (estimate - reference)/sqrt(sampling_se^2 + reference_se^2), as
    assemble.pull does) to a relative PULL_REL; a numeric pull whose stored inputs give none (se zero) is rejected. The
    shapes and the inputs themselves are compared with the recomputation (compare)."""
    p = []
    for path, row, (xk, xrow), (sk, srow), t, r in pull_rows(block):
        if not isinstance(row, dict) or not isinstance(xrow, dict) or row.get('pull') is None:
            continue
        x, s = xrow.get(xk), srow.get(sk)
        tv = t[1].get(t[0]) if t is not None else 0.
        rv = r[1].get(r[0]) if r is not None else 0.
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (x, s, tv, rv, row['pull'])):
            continue  # a malformed row: the comparison with the recomputation reports it
        if t is None:  # a power row: the vendored power_null_rows' d / s
            want = x / s if s > 0 else None
        else:  # a lower-order row: assemble.pull
            sigma = math.sqrt(s * s + tv * tv)
            want = (x - rv) / sigma if sigma > 0 else None
        if want is None or not abs(row['pull'] - want) <= PULL_REL * abs(want):
            p.append(f'{path}/pull: {row["pull"]!r} is not the pull of its stored inputs ({want!r})')
    return p


RECOMPUTED_BLOCKS = ('/gates', '/lower_order_checks', '/power_null_checks')  # replaced whole by the recomputation
COEFFICIENT_FAMILY = re.compile(r'C\d+_full|power_free_C\d+|power_correction')


def scale_keys(path: str, key: str, b: dict) -> tuple:
    """Y11: the keys of the dict b (at path) whose expected floats set the tolerance scale of b[key], besides the leaf's
    own magnitude: at a block root the coefficient family (C<n>_full, power_free_C<n>, power_correction: recomputed from
    the means) for a member of it, nothing for any other root leaf; inside a block the recomputation replaces whole
    (RECOMPUTED_BLOCKS) every sibling; nothing anywhere else (copied or partly copied objects: a copied value never
    widens a recomputed leaf's tolerance)."""
    rel = path[len('/test_partial'):] if path.startswith('/test_partial') else path
    if rel == '':
        fam = tuple(k for k in b if COEFFICIENT_FAMILY.fullmatch(k))
        return fam if key in fam else ()
    if rel.startswith(RECOMPUTED_BLOCKS):
        return tuple(b)
    return ()


def compare(a, b, path: str, problems: list, scale: float | None = None, bounds: dict | None = None) -> None:
    """a = stored, b = expected. bounds: absolute tolerances of named rounding-level leaves (F6). A dict leaf's scale
    comes from its designated siblings only (scale_keys, Y11); a list's from its elements."""
    if isinstance(b, dict):
        if not isinstance(a, dict):
            problems.append(f'{path}: not an object')
            return
        for k in sorted(set(a) ^ set(b)):
            problems.append(f'{path}/{k}: {"added" if k in a else "deleted"} key')
        for k in sorted(set(a) & set(b)):
            sib = max([abs(b[j]) for j in scale_keys(path, k, b) if isinstance(b[j], float) and math.isfinite(b[j])] + [0.])
            compare(a[k], b[k], f'{path}/{k}', problems, sib, bounds)
    elif isinstance(b, list):
        if not isinstance(a, list) or len(a) != len(b):
            problems.append(f'{path}: list length or type differs')
            return
        sib = max([abs(v) for v in b if isinstance(v, float) and math.isfinite(v)] + [0.])
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, f'{path}[{i}]', problems, sib, bounds)
    elif isinstance(b, float) and not isinstance(b, bool):
        if not isinstance(a, (float, int)) or isinstance(a, bool):
            problems.append(f'{path}: not a number')
            return
        s = max(abs(b), scale or 0., GATE_SCALE_FLOOR if path.startswith(FLOORED) else 0.)
        tol = max(REL * s, (bounds or {}).get(path, 0.))
        if not (abs(a - b) <= tol or a == b):
            problems.append(f'{path}: {a!r} differs from the recomputed {b!r}')
    elif type(a) is not type(b) or a != b:
        problems.append(f'{path}: {a!r} differs from the expected {b!r}')


def verify(result: dict) -> list[str]:
    problems: list[str] = []
    n = result.get('order')
    if n not in (7, 8) or result.get('schema') != asm.RESULT_SCHEMA:
        return [f'not a {asm.RESULT_SCHEMA} result of order 7 or 8']
    keys = set(result)
    missing = sorted(core_keys(n) - keys)
    extra = sorted(keys - core_keys(n) - OPTIONAL)
    problems += [f'/{k}: deleted key' for k in missing] + [f'/{k}: unknown key' for k in extra]
    if result.get('test_only'):
        part = result.get('test_partial')
        if not isinstance(part, dict):
            return problems + ['/test_partial: missing for a test-only result']
        # Y11: the top-level metadata of a test-only result (the block below holds test_partial and META)
        _types('', {k: v for k, v in result.items() if k not in part and k not in asm.META}, META_TYPES, problems)
        physical = core_keys(n) - set(asm.META)
        want = physical | COMBINED if set(part) & COMBINED else physical  # closed schema (O10)
        problems += [f'/test_partial/{k}: {"added" if k in part else "deleted"} key' for k in sorted(set(part) ^ want)]
        for k in sorted(physical | set(part)):
            if result.get(k) is not None:
                problems.append(f'/{k}: a test-only result must hold no physical value at the top level')
        block = dict(part, **{k: result[k] for k in asm.META if k in result})
        problems += [f'/test_partial{p[0:]}' for p in _check_block(block)]
    else:
        problems += _check_block(result)
    if 'batches' not in result and 'final' in result and result['final'] is not (not result.get('test_only')):
        problems.append(f'/final: {result["final"]!r}, but an assembled campaign result is final exactly when it is not test-only')
    return problems


def schema_problems(block: dict) -> list[str]:
    """Exact key sets and shapes of the blocks that are not recomputed (an added or deleted key there fails too)."""
    n = int(block['order'])
    Ls = {str(L) for L in range(3, n + 1)}
    p: list[str] = []

    def keys(path: str, obj, want: set) -> None:
        if not isinstance(obj, dict) or set(obj) != want:
            got = set(obj) if isinstance(obj, dict) else set()
            p.append(f'{path}: keys {sorted(got ^ want)} added or deleted')

    def vec(path: str, obj, length: int) -> None:
        if not isinstance(obj, list) or len(obj) != length or not all(_number(x) for x in obj):
            p.append(f'{path}: not a list of {length} finite numbers')

    keys('/power_protocol', block.get('power_protocol'), {'sha256', 'path', 'requirements'})
    keys('/assembly', block.get('assembly'), {'module', 'module_sha256', 'handoff_sha256', 'two_loop_sha256', 'half_d'})
    keys('/campaigns', block.get('campaigns'), {'a', 'b'})
    for t in ('a', 'b'):
        keys(f'/campaigns/{t}', (block.get('campaigns') or {}).get(t), {f'C{n}', 'sampling_se'})
    if block.get('bootstrap') is not None:
        keys('/bootstrap', block['bootstrap'], {'replicates', 'seed', 'full_se', 'correction_se', 'bias', 'diagnostic_only'})
    for top in ('means', 'error_by_loop'):
        keys(f'/{top}', block.get(top), {'free', 'power'})
        for sct in ('free', 'power'):
            keys(f'/{top}/{sct}', (block.get(top) or {}).get(sct), Ls)
    for sct in ('free', 'power'):
        for L in Ls:
            vec(f'/means/{sct}/{L}', ((block.get('means') or {}).get(sct) or {}).get(L), 2 * (n + 1 - int(L)))
            keys(f'/error_by_loop/{sct}/{L}', ((block.get('error_by_loop') or {}).get(sct) or {}).get(L), {'variance', 'share', 'se'})
    for k in ('coefficients', 'standard_errors', 'power_differences', 'power_difference_errors'):
        vec(f'/{k}', block.get(k), n + 1)
    hs = block.get('half_streams')
    if not isinstance(hs, list) or len(hs) != 2:
        p.append('/half_streams: not two half streams')
    else:
        for i, x in enumerate(hs):
            vec(f'/half_streams[{i}]', x, n + 1)
    cov = block.get('covariance')
    if not isinstance(cov, list) or len(cov) != n + 1:
        p.append('/covariance: not (order+1) rows')
    else:
        before = len(p)
        for i, row in enumerate(cov):
            vec(f'/covariance[{i}]', row, n + 1)
        if len(p) == before:  # Z8: a covariance matrix (symmetric, nonnegative diagonal, PSD; within rounding)
            p += covariance_problems(cov)
    for k in ('power_free_se', 'power_free_correction_covariance'):
        if not _number(block.get(k)):
            p.append(f'/{k}: not a finite number')
    p += sign_problems(block, n)
    if set(block) & {'batches', 'status'}:  # a combination: its metadata together, its batches block closed (O10)
        p += [f'/{k}: deleted key (a combination carries {", ".join(sorted(COMBINED))})' for k in sorted(COMBINED - set(block))]
        b = block.get('batches')
        keys('/batches', b, BATCH_KEYS)
        if isinstance(b, dict):
            per = b.get('per_batch')
            if not isinstance(per, list) or not per:
                p.append('/batches/per_batch: not a non-empty list')
            else:
                for i, x in enumerate(per):
                    keys(f'/batches/per_batch[{i}]', x, {'label', f'C{n}_full', 'sampling_se'})
                    if isinstance(x, dict):
                        if not isinstance(x.get('label'), str) or not x['label']:
                            p.append(f'/batches/per_batch[{i}]/label: not a non-empty string')
                        if not _number(x.get(f'C{n}_full')) or not _number(x.get('sampling_se')) or not x['sampling_se'] > 0:
                            p.append(f'/batches/per_batch[{i}]: C{n}_full and a positive sampling_se must be finite numbers')
                labels = [x.get('label') for x in per if isinstance(x, dict)]
                if len(set(labels)) != len(labels):
                    p.append('/batches/per_batch: labels repeat')
            for k in ('count', 'planned', 'dof'):
                if not isinstance(b.get(k), int) or isinstance(b.get(k), bool):
                    p.append(f'/batches/{k}: not an integer')
            if isinstance(b.get('planned'), int) and isinstance(per, list) and not 1 <= len(per) <= b['planned']:
                p.append(f'/batches: {len(per)} batches of {b["planned"]} planned')
            if not (b.get('chi2_about_combined') is None or _number(b.get('chi2_about_combined'))):
                p.append('/batches/chi2_about_combined: neither null nor a finite number')
        if not isinstance(block.get('final'), bool) or not isinstance(block.get('status'), str):
            p.append('/final, /status: a combination has a boolean final and a status text')
    p += field_types(block, n)
    return p


def covariance_problems(cov) -> list[str]:
    """Z8 (Stage-6 fix round 3, S6D-R3-01): the stored covariance must be a covariance matrix to rounding (module
    docstring, "Covariance"): with D the largest diagonal entry (0 if none is positive), tau^2 = EPS D the rounding unit
    of the largest variance, s_k = sqrt(max(c_kk, 0)) and t_k = max(s_k, tau), (a) symmetric: |c_ij - c_ji| <= COV_REL
    t_i t_j; (b) a nonnegative diagonal: c_kk >= -COV_REL t_k^2; (c) positive semidefinite: the smallest eigenvalue of
    T^-1 (C + C^T)/2 T^-1 (the correlation matrix, the rounding unit standing in for a zero variance) is >= -m COV_REL,
    m the dimension. With no positive variance (D = 0) every entry must be zero. The matrix's shape and finiteness
    are checked before (schema_problems). Empty when it is a covariance."""
    C = np.asarray(cov, float)
    m = len(C)
    D = max(float(np.max(np.diag(C))), 0.) if m else 0.
    if D == 0.:
        return [] if not np.any(C) else ['/covariance: no variance is positive, yet an entry is not zero (not a covariance; Z8)']
    s = np.sqrt(np.maximum(np.diag(C), 0.))
    t = np.maximum(s, math.sqrt(EPS * D))
    p: list[str] = []
    for i in range(m):
        if not C[i, i] >= -COV_REL * t[i] * t[i]:
            p.append(f'/covariance[{i}][{i}]: {C[i, i]!r} is a negative variance (beyond the rounding tolerance '
                     f'{COV_REL * t[i] * t[i]:.3g}; Z8)')
        for j in range(i + 1, m):
            if not abs(C[i, j] - C[j, i]) <= COV_REL * t[i] * t[j]:
                p.append(f'/covariance[{i}][{j}]: {C[i, j]!r} differs from its transpose element [{j}][{i}] = {C[j, i]!r} beyond the rounding '
                         f'tolerance {COV_REL * t[i] * t[j]:.3g} (not symmetric; Z8)')
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        R = (C / 2 + C.T / 2) / np.outer(t, t)
    if not np.isfinite(R).all():
        return p + ['/covariance: entries far beyond sqrt(c_ii c_jj) overflow its correlation matrix (not a covariance; Z8)']
    lam = float(np.linalg.eigvalsh(R)[0])
    if not lam >= -m * COV_REL:
        p.append(f'/covariance: not positive semidefinite (the smallest eigenvalue of its correlation matrix is {lam:.6g} < '
                 f'-{m * COV_REL:.3g}; Z8)')
    return p


def sign_problems(block: dict, n: int) -> list[str]:
    """Z8's class (Stage-6 fix round 3): the copied statistics that cannot be negative. power_difference_errors,
    campaigns.<a|b>.sampling_se and the bootstrap's full_se and correction_se are standard errors (square roots or
    standard deviations in the assembler), so >= 0 exactly; an error_by_loop variance is the [order, order] element of
    one sector and loop's term J V J^T, so >= 0 to rounding: >= -REL Var(C_order), the tolerance of the identity that
    the variances sum to Var(C_order). Malformed fields are left to the shape and type checks."""
    p: list[str] = []
    dse = block.get('power_difference_errors')
    if isinstance(dse, list):
        p += [f'/power_difference_errors[{k}]: {v!r} is a negative standard error (Z8)' for k, v in enumerate(dse) if _number(v) and v < 0]
    for t in ('a', 'b'):
        x = ((block.get('campaigns') or {}).get(t) or {}).get('sampling_se') if isinstance(block.get('campaigns'), dict) else None
        if _number(x) and x < 0:
            p.append(f'/campaigns/{t}/sampling_se: {x!r} is a negative standard error (Z8)')
    bs = block.get('bootstrap')
    if isinstance(bs, dict):
        for k in ('full_se', 'correction_se'):
            if isinstance(bs.get(k), list):
                p += [f'/bootstrap/{k}[{i}]: {v!r} is a negative standard deviation (Z8)' for i, v in enumerate(bs[k]) if _number(v) and v < 0]
    cov, ebl = block.get('covariance'), block.get('error_by_loop')
    var = cov[n][n] if isinstance(cov, list) and len(cov) > n and isinstance(cov[n], list) and len(cov[n]) > n else None
    if _number(var) and isinstance(ebl, dict):
        for s, rows in sorted(ebl.items()):
            for L, row in sorted((rows or {}).items()) if isinstance(rows, dict) else ():
                v = row.get('variance') if isinstance(row, dict) else None
                if _number(v) and not v >= -REL * abs(var):
                    p.append(f'/error_by_loop/{s}/{L}/variance: {v!r} is a negative variance (beyond -{REL:g} Var(C{n}); Z8)')
    return p


def _types(path: str, obj, want: dict, p: list) -> None:
    """Y11: obj[k] must be of want[k] (a predicate and its description) for every k of want present in obj."""
    if not isinstance(obj, dict):
        return
    for k, (ok, what) in want.items():
        if k in obj and not ok(obj[k]):
            p.append(f'{path}/{k}: {obj[k]!r:.60} is not {what}')


STR = (lambda x: isinstance(x, str), 'a string')
STR_OR_NONE = (lambda x: x is None or isinstance(x, str), 'a string or null')
NUM = (_number, 'a finite number')
NUM_OR_NONE = (lambda x: x is None or _number(x), 'a finite number or null')
INT = (lambda x: isinstance(x, int) and not isinstance(x, bool), 'an integer')
BOOL = (lambda x: isinstance(x, bool), 'a boolean')
OBJ_OR_NONE = (lambda x: x is None or isinstance(x, dict), 'an object or null')
# The metadata of a result (assemble.py, combine.py): never numbers that could stand beside a recomputed float (Y11).
META_TYPES = {'schema': STR, 'epsilon': STR, 'scope': STR, 'dimension': INT, 'order': INT, 'source_manifest_sha256': STR,
              'merged_sha256': (lambda x: isinstance(x, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in x.items()),
                                'an object of sha256 strings'),
              'backend': STR, 'build': OBJ_OR_NONE, 'test_only': BOOL, 'allocation': OBJ_OR_NONE, 'final': BOOL,
              'accepted_tool_changes': OBJ_OR_NONE, 'status': STR, 'design': STR_OR_NONE, 'numerics': STR, 'rates_identity': STR,
              'inputs_manifest_sha256': STR_OR_NONE}


def field_types(block: dict, n: int) -> list[str]:
    """Y11: the types of a result block's fields, validated before anything is recomputed: the metadata (META_TYPES),
    the scientific root numbers, the campaign, error_by_loop, bootstrap, power_protocol and assembly fields."""
    p: list[str] = []
    _types('', block, dict(META_TYPES, **{f'C{n}_full': NUM, f'power_free_C{n}': NUM, 'power_correction': NUM,
                                          'power_correction_se': NUM, 'sampling_standard_error': NUM}), p)
    for t in ('a', 'b'):
        _types(f'/campaigns/{t}', (block.get('campaigns') or {}).get(t), {f'C{n}': NUM, 'sampling_se': NUM}, p)
    for sct, rows in (block.get('error_by_loop') or {}).items() if isinstance(block.get('error_by_loop'), dict) else ():
        for L, row in (rows or {}).items() if isinstance(rows, dict) else ():
            _types(f'/error_by_loop/{sct}/{L}', row, {'variance': NUM, 'share': NUM_OR_NONE, 'se': NUM}, p)
    bs = block.get('bootstrap')
    if isinstance(bs, dict):
        _types('/bootstrap', bs, {'replicates': INT, 'seed': INT, 'diagnostic_only': BOOL}, p)
        for k in ('full_se', 'correction_se', 'bias'):
            if not isinstance(bs.get(k), list) or len(bs[k]) != n + 1 or not all(_number(x) for x in bs[k]):
                p.append(f'/bootstrap/{k}: not a list of {n + 1} finite numbers')
    _types('/power_protocol', block.get('power_protocol'), {'sha256': STR, 'path': STR, 'requirements': STR}, p)
    _types('/assembly', block.get('assembly'), {'module': STR, 'module_sha256': STR, 'handoff_sha256': STR, 'two_loop_sha256': STR,
                                                'half_d': INT}, p)
    return p


def _check_block(block: dict) -> list[str]:
    problems: list[str] = []
    for k in ('means', 'covariance', 'power_difference_errors', 'error_by_loop', 'assembly', 'power_protocol', 'order'):
        if k not in block:
            return [f'/{k}: missing, nothing can be recomputed']
    problems += schema_problems(block)
    if problems:
        return problems
    try:
        expected, bounds = _recompute(block)
    except (ValueError, ArithmeticError, KeyError, TypeError) as e:
        return [f'recomputation failed: {type(e).__name__}: {e}']
    compare(block, expected, '', problems, bounds=bounds)
    problems += pull_problems(block)  # R3
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('result', type=Path)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    data = a.result.read_bytes()  # Z9's class: the sha256 recorded is that of the bytes verified, read once
    problems = verify(json.loads(data))
    rec = dict(schema='c8-d2-verify-result-1', result=str(a.result), result_sha256=hashlib.sha256(data).hexdigest(),
               verified=not problems, problems=problems[:200], problem_count=len(problems))
    if a.output:
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('verified', 'problem_count')} | {'first': problems[:5]}, indent=1))
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
