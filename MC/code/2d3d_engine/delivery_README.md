# Long-range Ising MC: precision and large-volume package, v2

Research software / 18 September 2026. Classical ferromagnetic, isotropic, fully periodized long-range Ising in d=2 or d=3. This package improves the earlier exploratory simulator and adds a multi-temperature analysis. It does **not** contain a newly established infinite-volume CFT curve.

The numerical conventions are

\[
H=-\sum_{i<j} J_L(i-j) S_iS_j,\qquad
J_L(r)=\sum_{n\in\mathbb Z^d}|r+Ln|^{-d-s},\quad r\not\equiv0\pmod L,
\]
\[
\Delta_\sigma=(d-s)/2,\qquad
\Delta_\epsilon^{\rm eff}(L)=d-\log_2[U'_{2L}(\beta_\times)/U'_L(\beta_\times)],
\qquad U_L(\beta_\times)=U_{2L}(\beta_\times).
\]

Here L is **linear size**, N=L^d, prime is a derivative in inverse temperature, and U=1-<m^4>/(3<m^2>^2). Finite-size effective dimensions and their statistical errors are not continuum dimensions and total errors. No perturbative or bootstrap dimension is used to fit the MC data. The default nearest-neighbor addition is zero.

## 1. Deliverables and tested scope

- `code/src/`: improved C++17 simulation, exact periodic-image *sampling without a full N-entry coupling table*, grouped local Poisson events, xoshiro256++ and alternate mt19937_64 build.
- `code/prepare.py`, `run_pack.py`, `submit.py`, `array.slurm`, `merge_shards.py`: immutable globally numbered campaigns, independent chains on one allocated node, disjoint multi-cluster shards, signal-aware restart, conflict detection and deduplication.
- `code/pack_histograms.py`, `multihist.py`, `precision_analysis.py`: exact integer-count grouping, multi-temperature MBAR equations, analytic thermal derivatives, a joint stratified block bootstrap, overlap and autocorrelation diagnostics.
- `code/allocate.py`: pilot-based allocation of measurements to a size pair for a specified **statistical** error only.
- `tests/`: actual exact-enumeration, restart, analysis, and scheduling tests. `benchmarks/`: timings and resident-memory measurements. `results/`: fresh multi-temperature pilot analyses and diagnostics.
- `reference/lri_mc_v1.cpp`: the unchanged old simulation source used in paired timing tests. `reference/dimension_curve.csv`: the previous exploratory finite-size estimates.

The short large-lattice stress tests reached **8192^2 spins in 2D and 512^3 spins in 3D**. Only twenty sweeps were performed at each extreme size: these are computational-reach tests, not equilibrium simulations. See `RESULTS.md` and the machine-readable benchmark tables. The full fresh pilots use three temperatures and two independent hot/cold chains per size; their retained raw data are in a separate data archive.

Local process execution has been tested. The Slurm script has been syntax/command checked, but has **not** been run on your cluster. There is no GPU kernel or distributed union-find: one chain uses one CPU core. Multiple chains are independent and may run on different machines. Performance under a full node's memory contention must be benchmarked there.

## 2. Build and validate

Linux/POSIX, little-endian IEEE binary64, g++/clang++ with C++17, Python >=3.10, NumPy and SciPy are required. The timing script additionally uses `/usr/bin/time`.

```bash
cd lri_precision_v2
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r code/requirements.txt
cd code
make -j2
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
make test
```

The default compilation is portable `-O3 -std=c++17`; it deliberately does not enable fast-math or `-march=native`. Compile and retain the executable on each cluster. An active checkpoint is tied to the exact executable hash and compatible C++ standard library. Do not recompile a binary in place during an active campaign. For the alternate random-number generator use `prepare.py --rng mt`, then `bin/lri_mt` is selected automatically.

The exact tests enumerate all 65,536 configurations on a 4x4 square and 256 on a 2x2x2 cube, including moment/derivative tests and one nonzero nearest-neighbor-addition example. The restart test preserves the cached state of **all** Poisson distributions, not just the RNG. Statistical tests are stochastic diagnostics with disclosed seeds, not mathematical proofs of arbitrary large runs.

Run benchmarks **inside a compute-node allocation**, not on a login node:

```bash
python3 benchmark_v2.py --dim 2 --s 1.4 --beta 0.167784 \
  --sizes 128 512 1024 --engines reference hybrid \
  --seconds-per-case 5 --repeats 3 --out ../node_benchmark_2d
python3 benchmark_v2.py --dim 3 --s 1.8 --beta 0.100108 \
  --sizes 32 64 128 --engines reference hybrid \
  --seconds-per-case 5 --repeats 3 --out ../node_benchmark_3d
```

Use a new output directory for each benchmark. A completed directory is not a fresh repeat. For large stress tests use only `--engines hybrid` to avoid constructing the old full kernel. Paired benchmarks use the same **basic four-column record format** for both engines; production uses the richer eight-column format.

## 3. Why the new sampler represents the same Hamiltonian

Fukui--Todo [1] samples independent Poisson events and joins an event's two sites only when their spins agree. The following reorganization changes how events are sampled, not the FK bond ensemble or Swendsen--Wang transition kernel.

Let the core be the integer cube C0=[-B,B-1]^d, B=16 by default. Nonzero core vectors have their exact Euclidean weight |r|^(-d-s). The remaining lattice is a union of disjoint shells C_(k+1)\C_k, with C_k=[-B2^k,B2^k-1]^d. Each shell contains

\[
(4^d-2^d)(B2^k)^d
\]

vectors. The weight at every one is bounded by (B2^k)^(-d-s), so its envelope mass is

\[
M_k=(4^d-2^d)B^{-s}2^{-ks},\qquad
\sum_{k\ge0}M_k=\frac{(4^d-2^d)B^{-s}}{1-2^{-s}}.
\]

A small alias table samples the core or aggregate tail. A geometric draw chooses k; a uniform shell vector is accepted with probability (|r|/(B2^k))^(-d-s). It is folded **coordinatewise** modulo L, and zero-displacement self images are discarded (their energies are constants). If an oriented infinite-lattice vector is proposed at rate beta*N*|r|^(-d-s), a specified site gets rate beta*|r|^(-d-s). Summing the two orientations and all images gives the required 2*beta*J_L rate for each unordered finite-volume bond.

The `hybrid` sampler further splits the eight (2D) or twenty-six (3D) nearest cube offsets into separate Poisson processes. This removes most alias lookups and improves locality. Repeated events, including cycles that make no new union, are counted in K. Dropping them would give incorrect thermal derivatives and reweighting.

There is no user-chosen radial cutoff and no L^d coupling table. This is exact at the distributional construction level; like the rest of the simulator, its implementation has ordinary finite-precision random-number and floating-point limitations. Shell sampling uses a finite-resolution 53-bit uniform, not arbitrary-precision random reals. Parameters B and near-radius affect runtime only, not the intended model. Default B=16 and near-radius=1 were tested; they are not proven globally optimal on all CPUs.

Working spin/union-find arrays occupy about 6N bytes; checkpoint serialization causes additional peak memory. The preparer budgets 10N+16 MB conservatively. The measured peak is reported separately. The engine supports power-of-two L and N<=2^28; the preparer accepts only **interior** LRI points. Exact endpoints need marginal/logarithmic finite-size treatment.

## 4. Measurement and reweighting details

If c_j is a cluster's size divided by N, define S_(2k)=sum_j c_j^(2k). Conditional on the FK graph, the improved moments are

\[
 m_2=S_2,\quad m_4=3S_2^2-2S_4,
\]
\[
 m_6=15S_2^3-30S_2S_4+16S_6,
\]
\[
 m_8=105S_2^4-420S_2^2S_4+140S_4^2+448S_2S_6-272S_8.
\]

Raw `samples.bin` is little-endian float64, eight columns per sweep (64 bytes):

```
K_active, m2_improved, m4_improved, m2_sampled,
m6_improved, m8_improved, largest_cluster_fraction, number_of_clusters
```

`--record basic` writes the first four only; it cannot feed the new U6/U8 multihistogram path. Metadata and committed record counts are in `status.json` and `DONE.json`. The JSON metadata version and internal checkpoint-magic version are separate identifiers.

For a graph observable A with no explicit beta dependence,

\[
\partial_\beta\langle A\rangle=\operatorname{Cov}(A,K)/\beta,
\qquad w(\beta;\beta_0)\propto(\beta/\beta_0)^K.
\]

The second derivative is obtained from centered K cumulants, including the derivative of 1/beta. Grouping **equal integer K** values is lossless for this temperature dependence; it is not finite-width energy binning. `multihist.py` solves the MBAR/multiple-histogram equations [2], pools all simulated temperatures, and differentiates the normalized expectations analytically. Raw counts determine the point estimate. The code does not apply independent-sample MBAR error formulas to correlated trajectories or claim statistically optimal variance for arbitrarily unequal autocorrelations.

Each bootstrap draws contiguous blocks within each independent chain, then refits **all temperature free energies, the crossing, and both slopes**. A lattice size is resampled once per replicate, so adjacent pairs' covariance is preserved. Both hot and cold replicas are retained, not selected by agreement with a desired answer. The analysis reports Y=L^(d-s)<m2>, U4, U6, U8 thermal slope dimensions at the U4 crossing. A singular temperature solve, absent or multiple crossing, low importance overlap, or a negative slope ratio is rejected and counted as a failure, not silently replaced by a best-looking root.

Importance-weight ESS is not the number of independent Markov samples. The diagnostics also estimate integrated autocorrelation times for K, m2, an m2-derivative score, and a Binder-slope influence score. Reblock on at least two larger block sizes and inspect individual-chain drifts and hot/cold agreement. These diagnostics cannot prove equilibration or rule out an unsampled slow mode.

Higher moments permit future controlled observable combinations, but **no tuned cancellation of finite-size corrections is claimed** here. Horita et al. [3] demonstrate why endpoint Binder convergence and correction terms require special care.

## 5. Prepare a multi-temperature pilot

Empirical old crossing centers are supplied in `reference/largest_pair_crossing_centers.csv`; they are not known infinite-volume critical temperatures. A center file has columns `d,s,L,beta`; a blank L supplies a fallback for all sizes. A size-specific entry takes priority. Use the largest measured crossing as a provisional search center only.

Example 2D pilot at Delta_sigma=0.3, covering substantially larger sizes:

```bash
python3 prepare.py --out ../p2d --dim 2 --delta-sigma 0.30 \
  --sizes 32 64 128 256 512 --replicas 4 \
  --measurements 100000 --warmup 20000 \
  --beta-points 5 --beta-halfwidth 0.001 \
  --window-exponent 0.8 --reference-length 32 \
  --centers ../results/new_crossing_centers.csv
```

Example 3D pilot at Delta_sigma=0.6:

```bash
python3 prepare.py --out ../p3d --dim 3 --delta-sigma 0.60 \
  --sizes 8 16 32 64 128 --replicas 4 \
  --measurements 100000 --warmup 20000 \
  --beta-points 5 --beta-halfwidth 0.0005 \
  --window-exponent 1.2 --reference-length 16 \
  --centers ../results/new_crossing_centers.csv
```

These two examples use the new pilot crossing centers; the old reference CSV covers the other previously surveyed points. The temperature-window exponents are **pilot sampling choices, not fitted or imposed thermal dimensions**. There is no universal width: inspect adjacent histogram overlap and root bracketing. Approximately |Delta log beta|*sd(K) of order one is a useful spacing diagnostic. Increase the number of intermediate temperatures when histogram overlap is insufficient. Widen/recenter rather than extrapolate when the crossing lies outside the shared simulated bracket. A short pilot may bracket beta but not yet determine a thermal slope precisely.

`--dry-run` prints task, storage, spin-sweep, and estimated memory budgets. A new immutable campaign namespace is generated automatically. Do not independently run `prepare.py` on several clusters expecting the same task numbering or independent duplicated data: **prepare once, then copy the same manifest to every cluster**.

## 6. Run on one node or several clusters

Within a compute allocation:

```bash
python3 run_pack.py ../p2d --workers 16
```

Workers are serial chains pinned to distinct CPUs in the allocation's affinity mask. The code suppresses nested BLAS/OpenMP threads. Use one worker per **physical** core initially; affinity masks can include SMT siblings. `--no-pin` leaves placement to the site. Benchmark several workers on the real node because cache/memory contention may limit ensemble scaling.

For Slurm:

```bash
python3 submit.py ../p2d \
  --workers-per-job 16 --tasks-per-job 64 --concurrency 8 \
  --mem 16G --time 08:00:00 \
  --account YOUR_ACCOUNT --partition YOUR_CPU_PARTITION --dry-run
```

Remove `--dry-run` after inspecting the command. Memory is **per job**, not per chain; allocate workers times peak chain memory with overhead. Account, partition, CPU constraints, limits, permissions and Python environment must match your site. An array slot runs a balanced list of chains sequentially across the assigned workers.

For three clusters, copy the **same prepared campaign**, then use respectively:

```bash
# Cluster A: global task IDs congruent to 0 modulo 3
python3 submit.py ../p2d --shards 3 --shard 0 --workers-per-job 16 \
  --tasks-per-job 64 --concurrency 8 --account ACCOUNT_A --partition CPU_A
# Cluster B: same manifest, IDs congruent to 1 modulo 3
python3 submit.py ../p2d --shards 3 --shard 1 --workers-per-job 16 \
  --tasks-per-job 64 --concurrency 8 --account ACCOUNT_B --partition CPU_B
# Cluster C: same manifest, IDs congruent to 2 modulo 3
python3 submit.py ../p2d --shards 3 --shard 2 --workers-per-job 16 \
  --tasks-per-job 64 --concurrency 8 --account ACCOUNT_C --partition CPU_C
```

The same `--shards` and `--shard` options work with `run_pack.py` in another scheduler's allocation. Do not run overlapping shards or migrate a partly completed chain to a different executable. Distinct campaigns have namespace-separated seeds; replicas within one campaign have distinct SHA256-derived seeds and alternating hot/cold starts. Hash-derived seeds are a practical stream-separation scheme, not a proof that pseudorandom streams cannot overlap.

The Slurm wrapper requests a pre-walltime USR1 signal and forwards it to every running child. The child flushes data and atomically checkpoints. Exit 75 means safely stopped and resumable. `--auto-requeue` asks Slurm to requeue after that stop; it is **optional and subject to site permissions** [4]. Without it, resubmit the same command. Filesystem durability/locking assumes working POSIX flock, fsync, and atomic rename semantics. Disjoint task IDs are the primary protection against duplicate work across clusters.

To extend to a new **total** count:

```bash
python3 submit.py ../p2d --measurements 2000000 --workers-per-job 16 \
  --tasks-per-job 64 --concurrency 8
```

Do not change the manifest in place. On restart, any raw records after the committed checkpoint are truncated; warmup and measurements are not double-counted. The exact RNG and all cached Poisson state are restored. Old v1 checkpoints are deliberately incompatible; start new v2 chains. Old four-column trajectories remain available to the legacy analysis but cannot supply unmeasured sixth/eighth moments.

After bringing the cluster outputs to one filesystem, merge completed chains:

```bash
python3 merge_shards.py --out ../merged2d \
  --sources /copied/clusterA/p2d /copied/clusterB/p2d /copied/clusterC/p2d --copy
```

No remote transfer is performed by this command. Without `--copy`, it symlinks chains (inputs must remain accessible). Identical duplicate trajectories are counted once; conflicting trajectories with the same task ID raise an error. It verifies manifest identity and completed raw lengths and reports missing task IDs. Only completed chains are merged/packed by the production analysis path.

## 7. Analyze, reblock and export provisional centers

```bash
python3 pack_histograms.py ../merged2d --block 2000
python3 precision_analysis.py ../merged2d/hist_b2000/index.json \
  --dim 2 --s 1.4 --bootstrap 500 --out ../analysis2d_b2000

python3 pack_histograms.py ../merged2d --block 4000
python3 precision_analysis.py ../merged2d/hist_b4000/index.json \
  --dim 2 --s 1.4 --bootstrap 500 --out ../analysis2d_b4000

python3 export_centers.py ../analysis2d_b4000/results.json --out ../tuned_centers.csv
```

Read `results.json`, not only `dimensions.csv`: it contains all observable estimates, covariance, overlap diagnostics, bootstrap failures, chain drift and score-autocorrelation diagnostics. Compare at least Y- and U4-based dimensions and multiple successive size pairs. For final quoted errors use more bootstrap draws than the small local demonstration, confirm block-size stability, and retain independent-seed checks. Resampling errors do not include finite-size bias.

Packing stores exact integer-K counts and moment sums separately within every block. This can reduce data volume, but the achieved ratio depends on the model and size. Keep raw records until block-size stability and reproducibility are established. A million extended-format measurements is **64 MB per chain** regardless of lattice size. A campaign with 1000 chains at ten million sweeps uses 640 GB before compression; plan filesystem quotas and inode counts as well as CPU time.

`fit_fss.py` and `quotients.py` are preserved legacy exploratory tools. Their presence is not evidence that one-power finite-size fits describe the new precision data. The primary v2 path deliberately reports finite-size dimensions without forcing a smooth continuum curve or matching known endpoints.

## 8. Allocate cluster time based on the measured slope error

For fixed size pair and fixed temperature proportions, estimate

\[
\mathrm{Var}(\Delta_\epsilon^{\rm eff})\simeq A_L/M_L+A_{2L}/M_{2L}.
\]

The tool bootstraps one size at a time while fixing the other, refitting the crossing each time. If c_i is measured seconds per sweep, minimizing total cost at statistical variance sigma^2 gives

\[
M_i=\frac{\sum_j\sqrt{A_jc_j}}{\sigma^2}\sqrt{A_i/c_i}.
\]

Example; substitute **your compute-node** sweep costs:

```bash
python3 allocate.py ../merged2d/hist_b4000/index.json --dim 2 --s 1.4 \
  --L 64 --target-stat 0.001 --seconds-per-sweep 0.00013 0.00052 \
  --bootstrap 500 --out ../effort_2d.json
```

This estimate assumes the same sizes, equilibrium regime, temperature proportions, and asymptotic error scaling. It excludes warmup, hardware changes, finite-size extrapolation error, and unknown slow autocorrelation tails. Do not interpret it as a guarantee of a 0.001 continuum dimension. Reassess after each extension; running vastly more at an inadequate size does not solve finite-size bias.

## 9. Large-volume strategy and limitations

A useful first precision campaign extends 2D to L=256,512,1024 and 3D to L=64,128, with overlapping temperatures and 8--16 independent replicas as resources permit. This is a proposed run plan, not an already completed result. The extreme executable sizes are not necessarily sensible first production targets: one million sweeps at the measured 512^3 stress-test speed would take approximately 3860 single-core hours for **one** chain, before thermalization and possible critical slowing down.

The core speedup does not remove the Swendsen--Wang autocorrelation physics: reorganizing independent Poisson events leaves the intended transition kernel unchanged. Statistical gain must be assessed as error squared times CPU cost, not only sweeps per second. New multi-temperature analysis and extra independent samples must not be credited wholly to a faster kernel.

Optional `--nn-extra kappa` adds a ferromagnetic nearest-neighbor interaction. It is a possible route to studying correction amplitudes, **not a tuned improved action**. Each kappa requires a separate temperature pilot and extrapolation; the analysis refuses to mix kappas. Do not choose kappa by matching the desired CFT dimension. There is no demonstrated uniform 10^-3 continuum accuracy near either endpoint in this delivery.

## 10. Reproduce the reported local tests

`RESULTS.md` records the actual commands and numerical summaries. `tests/orchestration_validation.json` contains 1/2/4-worker timings, schedule-independent raw hashes, interrupt/resume verification, and duplicate-merge checks. The original short benchmarks, saved in `benchmarks`, are not suitable for autocorrelation estimation. Pilot manifests are supplied with reports; raw trajectories are in the optional pilot-data ZIP. Build the same source to run new statistically equivalent chains; reproducing a past checkpoint byte-for-byte requires its exact saved executable and standard library.

Optional local orchestration test (starts four short L=64 cubic chains; run in an allocation with >=4 CPUs):

```bash
python3 test_orchestration.py
```

Tests and benchmark reruns require fresh corresponding output directories. Archived summaries are retained for provenance; move them aside before rerunning test paths that intentionally reject overwriting.

## References

[1] K. Fukui and S. Todo, *Order-N Cluster Monte Carlo Method for Spin Systems with Long-range Interactions*, J. Comput. Phys. 228, 2629 (2009), https://arxiv.org/abs/0802.0272 . The present envelope/grouped sampling implementation is our adaptation, not code taken from that paper.

[2] M. R. Shirts and J. D. Chodera, *Statistically optimal analysis of samples from multiple equilibrium states*, J. Chem. Phys. 129, 124105 (2008), https://arxiv.org/abs/0801.1426 . We implement the estimator's equations with exact integer-K grouping and use a Markov-chain block bootstrap instead of iid uncertainty formulas.

[3] T. Horita, H. Suwa and S. Todo, *Upper and Lower Critical Decay Exponents of Ising Ferromagnets with Long-range Interaction*, Phys. Rev. E 95, 012143 (2017), https://arxiv.org/abs/1605.09496 . Its tuned combined Binder quantities are not automatically implemented by storing higher moments here.

[4] Official Slurm sbatch documentation, https://slurm.schedmd.com/sbatch.html , consulted 18 September 2026. Site configuration controls actual scheduling and requeue behavior.

[5] D. Blackman and S. Vigna, xoshiro256++ source and public-domain notice: https://prng.di.unimi.it/xoshiro256plusplus.c . SplitMix64 initializes the state. This is not a cryptographic RNG.
