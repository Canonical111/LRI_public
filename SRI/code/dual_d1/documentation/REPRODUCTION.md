# Reproduction guide and evidence boundaries

## 1. Three different reproduction levels

**Saved-data/certificate verification** checks exact algebra, complete retained
terminal sums, certificate rows, source hashes and the connection from beta
inputs to the claimed result. It does not independently rederive all primitive
integrals. This is the default level and is supported by the supplied drivers.

**Numerical period replay** starts from a complete exact expression in regularized
iterated-integral constants and evaluates the constants again. It changes neither
the kernel nor the exact-expression derivation. Two different precisions and
continuation settings test numerical consistency but are not a rigorous enclosure.

**Raw integral regeneration** starts from the regulated ordered-domain kernel or
an explicitly identified complete checkpoint and performs integrations again.
Replaying a terminal checkpoint is not labelled a full raw-kernel reintegration.
The main note and this guide mark the available start points.

## 2. Reconstructing the virtual layouts

The distribution removes byte-identical duplicates and separates archived code
from archived data. Every retained logical pathname appears in
`reproduction/layout.json`. The `stored` field identifies the one immutable copy.
For example, a certificate used by two historical packages may be stored only once
but is restored at both required locations by the materializer.

```bash
python code/prepare_workflows.py --workflow baseline
python code/prepare_workflows.py --workflow c7-proof
python code/prepare_workflows.py --workflow c8-candidate
```

The generated directories are under `work/`. They contain ordinary copies, not
hardlinks into the immutable distribution. `--destination /some/path` changes the
working root. `--workflow all` recreates all retained logical paths; most users do
not need that amount of scratch space. De-duplication applies to delivery, while a
fully materialized workspace may contain multiple necessary logical copies.

`--rebase-scratch` replaces `/mnt/data/` in generated **Python program text** with
the chosen working root. It never changes the immutable archived code or symbolic
expressions. Numerical manifest drivers also accept explicitly supplied input
paths. Historical JSON metadata may still record original provenance paths. Do
not interpret such a path as a downloadable or currently existing input.

For legacy helpers that genuinely require the original absolute hierarchy, an
alternative is to mount the generated `work/` tree at `/mnt/data` in a Linux
container. This avoids editing their path-dependent code. An optional Dockerfile
is supplied as an environment recipe, but the Docker build itself was not tested
in this consolidation; the native Linux Python/compiler workflows were tested.

## 3. Exact certificate workflows

```bash
python code/reproduce.py --task certificates
```

The C5/D3 verifier contains its small exact certificate. The C6 verifier embeds
its complete certificate; explicit JSON certificate rows are also retained. The
C7 verifier reads the ordinary-word target and certificates at weights 2–6,
regenerates source identities, and checks all multipliers, including product
terms. It must end with an empty exact residual, not a small numerical value.
The final C7 certificate has 588,878 rows and expands approximately 147 million
word terms over all weights. This can take several minutes and substantial RAM;
no timing or resource requirement should be inferred from the small C5 check.

The C7 input-map program independently reconstructs its 25,212-word target from
all 25 archived exact beta inputs. This prevents an unrelated target certificate
from being mistaken for a proof of the coefficient. The proof remains about the
specified archived matched calculation, not about all possible renormalization
prescriptions or a proof of the physical duality.

Intermediate modular matrices, decomposable-quotient caches and duplicate
accepted-stage certificates are omitted. The complete final certificate, analytic
relation generator and exact target are sufficient to reproduce the proof check.
Discovery source is retained for inspection but is not trusted by that check.

## 4. Latest full C8 numerical workflow

```bash
python code/reproduce.py --task c8-saved
python code/reproduce.py --task c8-numerical
```

These reconstruct `work/C8_zeta_candidate`. Its default saved checker rebuilds the
full P6 expression from all 64 terminal outputs and compares every coefficient.
The complete numerical replays solve the suffix-triangular differential system
and use asymptotic matching, with no old numerical period table as input.

The exact scalar relation is

```text
C8 = Cfixed - P6/2
Cfixed = 878.353653726563794093781271241865882423221643307740...
P6     = 1261.944897843140491372852392951531767542124984173610...
```

`Cfixed` is assembled from prior numerical beta-input records. It is not an exact
rational constant. The characteristic-polynomial/full-Jacobian check treats those
records as exact decimal strings only to test the algebra. The short zeta formula
has not been supplied as an exact period identity for all of C8.

For the P8 positive-weight divergence check:

```bash
python code/reproduce.py --task c8-positive-check
```

All outcomes are written to generated work directories and
`outputs/verification/replayed/`. No generated PASS is substituted for a command
that times out or fails.

## 5. Full P6 raw-source regeneration

```bash
python -m pip install -r requirements-raw.txt
python code/prepare_workflows.py --workflow p6-source --rebase-scratch
cd work/C8_P6_exact_sources
python P6_full/build_native.py
cd P6_full/engine
export R6_NATIVE=1 R6_ACCEL=1 R6_LINEAR=1 R6_MOD=1
export OPENBLAS_NUM_THREADS=1
```

The complete latest moving-letter checkpoint `../moving_total.jsonl` is retained
as the start input for independent terminal replay:

```bash
python final_fibration.py ../moving_total.jsonl ../terminal_replay 64
python precompute_terminal_apart.py ../terminal_replay
for i in $(seq 0 63); do
  python evaluate_terminal_bucket.py ../terminal_replay "$i" 5 0 1
done
```

The 64 completed outputs canonically reconstruct the supplied P6 expression. The
endpoint method must keep both lower and upper endpoint constants and proper
rational terms. It does not set logarithms to zero.

For a clean source regeneration, move any generated `B6_vd_f*/` copies aside and
run the source constructors for faces 1, 2, 3:

```bash
python boundary_mixed.py --n 6 --face 1 --deriv vd --sources
python boundary_mixed.py --n 6 --face 2 --deriv vd --sources
python boundary_mixed.py --n 6 --face 3 --deriv vd --sources
python run_mixed_stage2.py
python bucket_source_sum.py split ../weighted_spec.json ../weighted_s2 32
```

The retained queue drivers `run_moving.py` and `finish_moving_sum.py` generate the
later moving source. They may reuse complete hash-matched results: move only
generated output folders aside for a strictly fresh replay. Do not delete the
only reference copy. Sequential stages removed during consolidation must be
regenerated before invoking a legacy checker that expects them. Expanded TSV
buckets are scratch products and intentionally absent; the generators and their
complete input are present.

The `predict_P6_divergences.py` script reconstructs lower-moment predictions from
retained lower moments. This is independent of the desired P6 finite-power residue.

## 6. Full P8 and ninth-order source workflows

```bash
python code/prepare_workflows.py --workflow p8-source --rebase-scratch
cd work/P8_final_run
```

The complete starting moving source is retained under
`F3_six_kink_completion/P8_moving5_sum/moving_total.jsonl`. The source one stage
earlier also survives as the explicit F3_P8 checkpoint. From the P8 working root:

```bash
python terminal_fibration.py \
  F3_six_kink_completion/P8_moving5_sum/moving_total.jsonl \
  F3_six_kink_completion/terminal_replay 256
python F3_six_kink_completion/engine/precompute_terminal_apart.py \
  F3_six_kink_completion/terminal_replay
for i in $(seq 0 255); do
  python evaluate_terminal_bucket.py \
    F3_six_kink_completion/terminal_replay "$i" 7 0 1
done
```

All 256 terminal outputs are required. They are inputs to the exact canonical
sum, not independent approximations to it. The scalar minus-sign follows from
`P8 = -[epsilon^0 log(epsilon)^0](-epsilon d/depsilon) partial_v Q8`.

For the ninth-order terms, retain the supplied F4_A9, F4_Z8, F4_EA7 and F4_EZ6
sources and use their corresponding full final-integration programs. The
`fibration_defect.py` audit and endpoint-offset restoration must not be skipped:
the earlier rational projection alone does not determine the full scalar. The
accepted corrected EZ6 multiplicity is preserved in the final outputs.

## 7. Rational C8 and previous stages

`--workflow c8-rational` restores the rational C8 sources and the separate R6/R8
records. The shorter complete assembly is

```text
C8^(0) = -111389/24 + (3/4)*(-910891/6) + (1/4)*(1423087/3) = 88.
```

The full-Jacobian route substitutes all 35 rational beta inputs and obtains
`T4^(0)=11`. The current `reproduce_summary.py` rechecks that algebra independently.
For raw regeneration the relevant programs are `tail_boundary.py`,
`endpoint_odd.py`, `finite_lower.py`, and the source-regeneration checkers in
`workspace/R8_work/engine`. Their source parameters are explicitly specified in
the main note. Original whole-snapshot manifest checks are not the curated
manifest: use the top-level checker, and regenerate omitted stages before using
original all-stage replay commands.

`--workflow baseline`, `f1`, `f2-f3` and `c7` restore earlier exact calculation
packages. Their detailed historical notes and source code remain available.
Superseded numerical checkpoints are not used by the current coefficient table.

## 8. Known limits of the surviving record

1. **C8's analytic short-form proof is open.** The supplied candidate and its
   numerical recognition are not a complete exact target/certificate.
2. **Six full beta inputs** W, S, L3, M21, M12 and N2 enter the latest assembly
   from numerical records. Separate complete exact unprojected expressions for
   all six were not reconstructed in the latest source package. Recovering or
   regenerating them is needed for a complete common C8 period target.
3. **F2 raw-stage provenance:** its complete U expression and numerical evaluator
   survive, but 258 intermediate files listed by an earlier coverage manifest are
   unavailable. The final scalar can be replayed; that manifest alone cannot
   serve as a fresh full raw-kernel verification. Its highest logarithm has a
   separate analytic check; a complete fresh subleading-log check is not claimed.
4. No rigorous interval enclosure for the complete high-order numerical answer
   has been supplied. Sampled independent checks do not prove the accuracy of
   every target period.
5. Exact certificate checks, numerical consistency and regulator matching do not
   independently establish physical duality or all-orders two-coupling closure.

These gaps are not hidden as missing-zero data. They are the documented boundary
between current supported reproduction and a further research task.
