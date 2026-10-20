# PLAN: Expanse release of the 2D dressed-window HT (ht2d) and its production campaign

Revision 7, 2026-10-07 (rev 6 APPROVED in round 6; rev 7 adds the user-requested x=1/8 benchmark, the HF-01 fixed-point fallback and the inspection-1 design points IR-01–IR-08). Host and builder: Claude Code. Plan reviewer and final inspector: Codex (gpt-6-astra, xhigh).
Repo: `lri_2d_window_hpc` (local git). The baseline commit `4afd379` is the unmodified
`lri_2d_window_hpc_optimized.zip` (sha256 71b9a64a…) plus a `.gitignore`.

## 1. Goal and acceptance criteria

**Goal.**
- Make the supplied 2D dressed-window HT package (0.2.0rc1) safe and efficient to run on SDSC Expanse (account
  yun124), without changing its physics, tolerances or numerical algorithms.
- Then run a production campaign there: Δ_ε(Δσ) along continuous cutoff ladders, with nested local-basis checks.

**Acceptance criteria (observable).**
- **A1. Physics unchanged.**
  - With identical arguments the numerical path is unchanged.
  - The inherited 54 tests pass on an Expanse compute node.
  - A replay of the reference L=8 and L=10 window records reproduces Delta_thermal and the 10 scalar gaps to
    ≤ 1e-9 absolute. Expected differences are about 1e-12; the gate is deliberately loose relative to that.
- **A2. No Lustre dependence.**
  - Code, inputs, outputs, claims, checkpoints and logs live under `/home/zzheng8/lri2d_window`.
  - Each job extracts a checksummed release tarball into node-local `/scratch/$USER/job_$SLURM_JOB_ID`, and the
    Numba cache lives there too.
  - Nothing is read from or written to `/expanse/lustre`. This follows the user's instruction of 2026-10-07 and the
    documented Expanse Lustre problems.
- **A3. Continuation is enforced.**
  - Every production point at cutoff L ≥ L0+2 is seeded from the accepted record of the same chain at L−2.
  - The driver refuses a predecessor that is missing, unaccepted, checksum-invalid or belongs to another chain or
    configuration.
  - Nested-size checks at L are seeded from the main record at the same L.
- **A4. Walltime safety.** There are three distinct outcomes after USR1 (F25):
  1. **Graceful stop.** If the stop reaches a Newton boundary first, the point checkpoints and exits 75, releases
     its claims, and the chain exits 75.
  2. **Completed publication.** If the solve, and any diagnostics, were already finishing, the complete record is
     published (exit 0) and the chain stops before the next point with exit 75.
  3. **Wall kill.** If the stop arrives inside an uninterruptible segment (final check or diagnostics) that
     outlasts the lead, Slurm kills the job at the wall and its claims stay fail-closed.

  In every case the USR1 trap has already queued one continuation. That continuation:
  - confirms PREV terminal by sacct (UNKNOWN → exit 75, manual check);
  - recovers only PREV-owned claims under the recovery protocol;
  - resumes from the last Newton checkpoint.

  The manual recovery tool covers hard kills with no continuation. Live drills on Expanse demonstrate all of these
  paths (G3), including the combined USR1, wall-kill, automatic-continuation and recovery path.
- **A5. Validated release.**
  - The campaign spec binds the release tarball's sha256, the source sha256 and a passing Expanse validation
    receipt.
  - Submission refuses on any mismatch.
- **A6. Reviewed and running.**
  - The Codex plan review has approved this plan.
  - The final code has had a fresh Codex inspection, and findings are fixed or explicitly dispositioned.
  - The campaign is submitted, with log paths reported and a check about 10 minutes after start.

## 2. Review of the supplied package (host review, 2026-10-07)

**Numerics.** The package is a careful performance port of the reference 2D research code.
- **Local evidence.** 54 tests and the replay and benchmark audits pass locally.
- **Expanse evidence:**
  - The same 54 tests pass on an Expanse compute node (debug job 54736100, 17 s).
  - L=14 at x=0.25 with nz16, the consistent window and diagnostics=all gives identical spectra on the tensor and
    gram backends (ΔΔ_E = 5e-13).
- I found no physics defect. The items below are HPC and deployment findings.

| ID | Finding (file) | Consequence | Disposition |
|---|---|---|---|
| R1 | `cluster/array.sbatch` has no account or partition, uses `SLURM_TMPDIR` (absent on Expanse), writes `logs/` relative to the submit cwd, and runs code from the shared tree | not runnable as-is on Expanse; code read from a shared FS | new `cluster/expanse/` layer (§3) |
| R2 | The stop lead is 180 s. Stops happen only at Newton boundaries; the final 5-root check and the J=1,2 diagnostics cannot be interrupted | at large L a stop request arrives mid-iteration or mid-diagnostics; SIGKILL at the wall leaves stale claims | lead time sized from calibration per job class (§3.4), plus a sacct-verified claim recovery (§3.5) |
| R3 | A stop request that arrives after the solve and diagnostics have **completed** still raises SafeStop and discards them ("Stopped before final publication"). The unconditional stop right after `s.solve()` also discards a finished solve when no diagnostics or training remain. | hours of finished work are thrown away at large L | change (F12): (a) the post-solve stop is raised only when diagnostics or training still remain; (b) the stop after diagnostics is removed. A complete record is published with exit 0, and the record carries `stop_requested_at_publication`. Newton-boundary checkpoint semantics are unchanged. |
| R4 | Continuation needs the predecessor output as `--seed`, but `make_manifest.py` hashes inputs at freeze time | a frozen array cannot express an L-ladder whose seeds do not exist yet | new chain driver (§3.3): the seed content is still hashed into the request by `hpc.py` at run time, and the predecessor is validated against the frozen chain spec |
| R5 | `--backend auto` picks gram for L>12. On Expanse at L=14 with 16 threads, gram is **4.0× slower** than tensor (116.5 s vs 28.8 s full point with diagnostics; matvec 10 ms vs 0.5 ms), for 20 vs 11 MB of operator storage | auto is the wrong default where memory is plentiful (256 GB nodes) | the campaign passes `--backend tensor` explicitly, with gram as the documented fallback when the tensor memory estimate exceeds the job memory. The code default is not changed. |
| R6 | `--max-bath-states` defaults to 2,000,000. Full circle-bath dimensions are 1.37M (L=20), 3.81M (22), 10.2M (24) and 26.8M (26) | L ≥ 22 fails the guard | pass an explicit `--max-bath-states` per L in the campaign spec (an explicit guard, not removed) |
| R7 | The request digest binds `threads`, `memory_limit_gib` and runtime versions | a resubmission with different resources cannot reuse a checkpoint | keep (strict). The chain spec fixes resources per step; a resource change needs a new spec. |
| R8 | The diagnostics' `projected_translation` loops in Python over the J-sector states | some cost at large L | measured in calibration; acceptable unless it dominates |
| HF-01 | Found by the live drill: the optimized ground-only top fixed point is followed by a k0-root re-check. At x=0.35, L=8, nz16 (reference seed) the two eigensolves differ by more than the unchanged 1e-11 gate, and the point aborts deterministically at any thread count. The reference algorithm iterates with the k0-root solve and passes. | some grid points (here x=0.35) cannot run at all | change in `solver.py`: if the re-check misses the gate, continue the same Newton fixed-point iteration with the k0-root solve (the reference algorithm) until the unchanged gate holds, or raise. The exact-window cache recomputes instead of aborting. The record carries `top_expanded_fallback_iterations`. The validation replay adds x=0.35, L=8. |
| R10 | `hpc.py` rejects x = 1/8 (strict `1/8 < x`) | the user asked for the s* = 7/4 crossover benchmark at x = 1/8 | admit `1/8 ≤ x < 1/2` in the guard only; nothing in the Hamiltonian is singular there. |
| R9 | The teachers are the shipped L=6 density artifacts (keep 20) | adequacy at L ≫ 12 is not certified | nested nz12/nz16/nz20 checks at every L, plus an independent moving-basis reference (§4.3). There is no automatic retraining; flagged points are reported. |

## 3. Expanse adaptation (new files under `cluster/expanse/`; numerical modules untouched except R3)

### 3.1 Storage layout (home only)
```
/home/zzheng8/lri2d_window/
  envs/<env_id>/                immutable Python 3.11.5 venv: numpy 2.3.5, scipy 1.17.0, numba 0.65.1, llvmlite 0.47.0,
                                threadpoolctl 3.6.0, pytest 9.0.2. env_id = first 16 hex of sha256(python version +
                                sorted `pip freeze`). Made read-only (chmod -R a-w) after creation (F6). The calibration
                                venv ~/lri2d_window/venv is NOT used for production.
  releases/<commit>.tar         git-archive tarball, plus <commit>.sha256 (per-file sha256, sha256sum -c format)
  releases/<commit>.json        install record: tar sha256, source_sha256, venv freeze sha256
  validation/<jobid>/receipt.json
  inputs/<campaign>/            teachers and initial seeds copied once from the release (stable absolute paths)
  campaigns/<campaign>/spec.json, SUBMITTED.jsonl, chains/<chain>/{L*_z*.json, *.checkpoint.json, *.claim,
                                chain_state.json}, claims_archive/
  logs/                         Slurm .out files
```
- Output records are small JSON files: kB to a few MB each, so a few hundred MB for the whole campaign.
- Home NFS is POSIX enough for the package's single-writer protocol: atomic `mkdir` claims, `os.replace`
  publication, `fsync`.

### 3.2 Release and validation
- **`cluster/expanse/install.sh`**, run on the login node (cheap):
  - builds `git archive` and the per-file sha256 manifest;
  - copies both to `releases/`;
  - creates (once) the immutable env `envs/<env_id>/` from `cluster/expanse/requirements-expanse.txt` (exact pins),
    computes env_id, and makes the env read-only;
  - writes the install record: tar sha256, manifest sha256, source_sha256, env_id.
- **`cluster/expanse/envcheck.py`** recomputes env_id inside any allocation, using the same rule. It is used by
  validation, chain jobs and continuations (F6).
- **`cluster/expanse/validate.sbatch`**, a `shared` job with 16 cores and 32 GB:
  1. stage and verify the tarball;
  2. run pytest on the inherited 54 tests plus the new tests;
  3. replay the reference window records (L=8 and L=10 nz16 at x ∈ {0.126, 0.25, 0.495}), seeded with their own
     theta, comparing Delta_thermal and the 10 scalar gaps (≤ 1e-9);
  4. write `validation/<jobid>/receipt.json`: passed, tar sha256, source_sha256, env_id, runtime versions, node,
     per-check results.

  Any failure means `passed=false`.

### 3.3 Chain driver `cluster/expanse/chain.py`

**Campaign spec.** `campaign.py freeze` writes `spec.json` (schema `ht2d-expanse-campaign-v1`), which is never
overwritten.

Freeze validates:
- the **effective** per-chain Slurm resources after overrides (F17): account yun124, partition shared,
  1 ≤ cpus ≤ 128, mem_gb ≤ 240, 1 h ≤ time ≤ 48 h, 1800 s ≤ lead_s ≤ min(65535, wall/2), 0 ≤ max_cont ≤ 2,
  and threads == cpus;
- the time format (F21): only `[D-]HH:MM:SS` is accepted (a bare number would mean minutes to Slurm), and the
  normalized `D-HH:MM:SS` of the validated value is what gets frozen and rendered;
- every **seed_from edge** (F18): the referenced step exists, has the same x, and is at the target's first cutoff.
  A chain gives either an initial seed or a seed_from edge, never both.

The spec binds:
- the release tar sha256, the per-file manifest sha256 and source_sha256;
- env_id (it must equal the receipt's);
- the receipt path and sha256;
- per chain: x, the L ladder, the basis file and sha256, the initial seed file and sha256 (used only for the first
  L), and the per-step argv templates (nz, osc, backend, threads, memory, max-bath-states, diagnostics, tolerances);
- the check steps (nz, diagnostics, which L).

**What `chain.py --spec S --chain C` does:**
1. Verifies:
   - the spec checksum, the source hash of the staged code, env_id, the receipt, and the basis and initial-seed
     hashes;
   - **exclusive chain ownership** (F3): it atomically creates `chains/C/chain.claim/` with owner.json (job id, host,
     pid, token). If the claim exists, it exits 73 without writing any state. The claim is removed only by its owner
     on exit, or by `recover_claims.py` after sacct confirms that the owner job is terminal.
2. For each L in order, runs the main step, then that L's check steps.
   - Each step is a subprocess `code/hpc_run.py … --resume` with `HT2D_FROZEN_SOURCE` and `HT2D_FROZEN_INPUTS` set
     (basis, plus the seed actually used). This is the same TOCTOU protection as `run_item.py`.
3. Uses this seed rule:
   - The first L uses the frozen initial seed.
   - Main step L uses `chains/C/L{L-2}_z{nzmain}.json`.
   - Check step (L, nz) uses `chains/C/L{L}_z{nzmain}.json`.
4. Validates the seed before use. There are two separate paths (F1):
   - **Initial seed** (first L only). It is a frozen file with a declared `origin` in the spec (F9):
     - `reference_same_L`: a shipped reference record (old schema without request_digest) whose `bath_cut` must
       equal L0;
     - `teacher_L0m2`: a stage-T teacher record. Its `bath_cut` must equal L0−2, its sha256 must equal the chain's
       basis sha256 (the teacher is the basis), and it must carry `basis_artifact.training_L == L0−2`.

     Common checks:
     - its sha256 must equal the spec's;
     - it must contain a finite two-component `theta`;
     - its `delta` must equal x to 1e-12.
     
     No envelope validation is attempted.
   - **Continuation and check seed** (a production predecessor). Checks:
     - `validate_record(row, row['request_digest'])` must pass (record checksum and gates);
     - fast identity checks: x, L, nz, basis sha256, backend, window and mode, and source_sha256;
     - **exact frozen request with a validated lineage** (F15): the record must validate against the COMPLETE
       request of its frozen step. The seed hash used for that request is never taken from the current file. It is
       the frozen `initial_seed.sha256` for an initial seed, or the hash returned by recursively validating the
       predecessor step, back to the frozen initial seed. The record's `configuration.seed_sha256` must equal it.
       Validation results are memoized within one run. The check runs under the **frozen interpreter**
       (`spec.env.python`) from the verified release (F20). `status.py`, `collect.py` and `submit.py` first call
       `require_frozen_env`, which compares the release source hash and runs envcheck under the frozen
       interpreter. An unusable environment raises `EnvUnavailable`, which is distinct from an invalid record.
       This uses the driver's own `hpc_run.py <full frozen argv> --check-only` in a subprocess, with the same
       HT2D_FROZEN_* environment. The full argv includes the step's own seed path, so seed provenance is covered, as
       are diagnostics, tolerances, oscillator and basis mode, resources and runtime versions. The same check is
       used for predecessors, for completion (`continuation.chain_complete`), and by `status.py` and `collect.py`.
   - **Bytes are hashed once** (F13). Each validator returns the sha256 of the exact bytes it validated. That hash
     (and, for initial seeds, the frozen spec hash) is passed unchanged in `HT2D_FROZEN_INPUTS`. The child re-reads
     the file and refuses if the bytes differ.
   - Any seed or integrity refusal, for a main or a check step, stops the chain with exit 65 (F19). This includes
     the point driver's own refusals. `hpc.py` now raises `IntegrityError` and exits **65** for changed source or
     inputs, a corrupt or incompatible checkpoint, and an invalid existing output, in both reuse and check-only.
     Ordinary numerical failures stay exit 1. `failed_checks` records only check steps that were attempted and
     failed with a non-integrity, non-stop code.
5. Handles outcomes:
   - An accepted step is reused (hpc.py prints REUSE).
   - A failed check step is recorded and the main ladder continues.
   - A failed main step stops the chain (exit 66), because its successors depend on it.
   - Exit codes 73 (claimed) and 75 (safe stop) propagate.
6. Forwards USR1, TERM and INT to the running child and stops before launching the next step.
7. **Per-job state** (F3). The owner job atomically writes `chains/C/state/<SLURM_JOB_ID>.json` (complete /
   stopped / failed, last step, exit code). A duplicate that fails to take the chain claim writes nothing.
   - "Complete" is never inferred from a state file alone. `chain.py` and `status.py` decide completion by
     validating every main-step record and attempting every check step.
8. **Attempt history** (F7). Before relaunching a step whose `*.checkpoint.json` exists, `chain.py` copies it to
   `chains/C/history/<step>.<jobid>.<n>.checkpoint.json`. hpc.py overwrites the checkpoint on resume and does not
   carry earlier histories, so this keeps every interrupted attempt's history, including per-iteration Jacobian
   conditions.
   - `collect.py` merges the archived histories with the final record's history. The tuning-Jacobian-condition flag
     uses the maximum over all attempts.
   - Solver decisions are unchanged. hpc.py and solver.py are not modified for this.

### 3.4 Job script `cluster/expanse/chain.sbatch`
- **Resources:** `-A yun124 -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=T --mem=M -t W
  --signal=B:USR1@LEAD`, with T, M, W and LEAD per job class from the spec and calibration.
- **Environment:**
  - modules `cpu/0.15.4` and `slurm/expanse/23.02.7` (for in-job `sbatch`/`sacct`);
  - no `set -u` (it breaks /etc/bashrc);
  - `OPENBLAS/MKL/OMP/BLIS_NUM_THREADS=1`, `NUMBA_NUM_THREADS=T`,
    `NUMBA_CACHE_DIR=/scratch/$USER/job_$SLURM_JOB_ID/numba`.
- **Staging** (F5). `submit.py` passes `HT2D_SPEC` and `HT2D_SPEC_SHA256` through `--export`; continuations inherit
  them. Before extracting anything, the job:
  1. checks `sha256(spec) == HT2D_SPEC_SHA256`, using coreutils sha256sum and a small inline parser run under
     /usr/bin/python3 -I, not code from the release;
  2. reads the tar path and tar sha256 from the spec and checks `sha256(tar)` against it;
  3. extracts the tar to node-local scratch and runs `sha256sum -c` against the per-file manifest, whose own sha256 is
     also bound in the spec;
  4. runs `envcheck.py` against the spec's env_id (F6).

  Any mismatch exits 74 before any release script runs.
- **Execution:** run `chain.py` in the background and wait in a loop, so trapped signals run.
- **Continuation**, following the hpc-clusters wall-time pattern; non-array jobs only, one job per chain:
  1. The USR1 trap forwards USR1 to the chain and submits **one** continuation (`--dependency=afterany:$JOBID`,
     `PREV=$JOBID`, continuation count+1, at most `max_cont`). `max_cont` is one frozen spec field
     (`slurm.max_cont = 2`), used by submission, by the in-job limit and by the budget (F11).
  2. The continuation then:
     - confirms through sacct (5 retries; UNKNOWN exits 75 for a manual check) that PREV is terminal;
     - checks that no other job of the same name is pending or running (squeue with retries; a failure exits 75);
     - **always** runs `recover_claims.py --apply --owner-job PREV --scope chains/C` (F2, F10), which covers the chain
       claim and every point claim owned by PREV;
     - verifies that no claim owned by PREV remains (exit 75 for a manual check otherwise);
     - reads **only** `chains/C/state/PREV.json` (F3):
       - `complete` → success (exit 0, nothing to run) **only if** every main-step record validates
         (`check_predecessor`) and every check step has either a validating record or an entry in that state's
         `failed_checks` (F10). Otherwise it is treated like `stopped`.
       - `failed` → exit 0 with a message (needs a human);
       - `stopped` → resume;
       - missing (PREV was hard-killed, timed out mid-step, or died before writing) → treat as killed and resume;
     - resumes.
- **Sizing.** LEAD = clamp(1.5 × the longest Newton iteration at the chain's Lmax, 1800 s, wall/4), from
  calibration.
  - **Why not the full final segment.** Calibration shows that the uninterruptible final 5-root check plus
    diagnostics is about half of a point's time: 600 s of 1221 s at L=20, x=0.25. At L=24 that is several hours,
    so covering it fully would waste a large part of every allocation.
  - **What happens instead.** A stop arriving inside that segment may be followed by SIGKILL at the wall. The
    continuation queued by the USR1 trap then confirms PREV terminal, recovers PREV's claims and resumes from the
    Newton checkpoint (at the converged theta). The loss is that segment only.
  - W ≤ 48 h, and `max_cont = 2` (spec field) continuations per chain.

### 3.4a Hardening from final inspection 1 (IR-01 to IR-07)
- **IR-01, snapshot-bound exact checks.** The exact-request check passes the sha256 of the parent's validated
  output bytes as `HT2D_EXPECT_OUTPUT_SHA256`. In check-only mode `hpc.py` reads the output once, requires that
  hash, and validates those same bytes.
- **IR-02, explicit scheduler options.** Every sbatch call, initial (`submit.py`) and continuation (`chain.sbatch`),
  passes all frozen options explicitly: -A, -p, nodes, cpus, mem, -t, --signal, -J, -o. It runs with every
  `SBATCH_*` variable removed from the environment.
- **IR-03, verified runtime at every entry point.** `chain.py`, `continuation.py`, `submit.py`, `status.py` and
  `collect.py` call `verify_runtime(spec)` before acquiring any claim or reporting. That checks an unchanged and
  passing receipt covering the release and environment, the release source hash, and envcheck under the frozen
  interpreter. Points are launched with the frozen interpreter.
- **IR-04, persisted-JSON shape.** Parent-side loaders read each persisted JSON once and require an object. Read,
  decode, shape and gate failures become SpecError, reported as INVALID or as an exit-65 refusal.
- **IR-05, archived checkpoints.** These are merged into the reported Jacobian maximum only if they are checksummed
  envelopes of the same request. Others are listed in `flags.txt` and never abort collection.
- **IR-06, exclusive freeze.** Freeze takes exclusive ownership by atomically creating a NEW campaign directory
  before copying anything. The spec is published no-clobber (temp file plus hard link).
- **IR-07, executable step graph.** Freeze requires nonempty ladders and unique step outputs. Every seed must be
  rooted in a frozen initial seed, a teacher step, or a seed_from edge to a rooted chain; chains of seed_from, and
  therefore cycles, are rejected.

### 3.5 Claim recovery `cluster/expanse/recover_claims.py`
- **Serialization (F14).** Recovery of a chain directory is serialized by an atomic `recovery.lock` directory. Both
  the automatic (continuation) and the manual entry points take it. If the lock is held, they exit 75; a stale lock
  needs a human.
- **Atomic retirement.** Under the lock, a claim qualifies only if its owner token is **re-read and found
  unchanged after** sacct has confirmed the owner job terminal (F14).
  - **Why claim writers need no lock.** A dead owner cannot release its claim, and no writer can `mkdir` a claim
    directory that exists. So between that re-read and the atomic `rename` into `claims_archive/`, the claim cannot
    change hands. A claim that an alive owner released, and B re-acquired, while sacct was being queried shows a new
    or missing token at the re-read and is left alone.
  - **Defence in depth.** The moved token is checked once more; on a mismatch the directory is renamed back.
  - Claims without a token are never touched. `claims_under` excludes `claims_archive/` (F24).
- Lists the `*.claim/owner.json` files under a chain or campaign.
- A claim is archived (owner.json moved to `claims_archive/`) and removed only if:
  - its `slurm_job_id` is terminal according to sacct (COMPLETED/FAILED/CANCELLED/TIMEOUT/NODE_FAIL/OUT_OF_MEMORY/
    PREEMPTED, after up to 5 queries); and
  - when `--owner-job` is given, it matches.
- Claims without a job id, with an UNKNOWN state, or owned by a live job are never touched.
- `--dry-run` is the default; `--apply` is required to remove anything.

### 3.6 Submission and monitoring
- **`cluster/expanse/submit.py --spec S [--chains …] [--dry-run]`:**
  - checks the receipt, the spec and the release;
  - prints a survey (`sinfo` shared states; yun124 usage by user and state);
  - submits one non-array job per chain (job name `ht2d-<campaign>-<chain>`);
  - refuses if a job with that name is already pending or running;
  - **defers** a `seed_from` chain (the moving-basis references) until its predecessor record passes the
    exact-request validation (F16). Deferred chains are listed in `DEFERRED.jsonl` and submitted later with
    `--chains`. They are never started early to fail with exit 65;
  - appends to `SUBMITTED.jsonl` and prints `tail -f` lines.
- **Partition:** `shared` only. The account's 32-running cap on `normal`/`compute` does not apply there. Concurrency
  on shared is self-limited to the number of chains (≤ 40 jobs). This leaves the normal-QOS slots untouched for
  collaborators.
- **`cluster/expanse/status.py --spec S`:** per chain, the accepted steps, the current step and its last
  checkpoint iteration and residual, claims, `chain_state`, and the last job's sacct state.
- **`cluster/expanse/collect.py --spec S`:** a CSV of (x, L, nz, Delta_thermal, scalar gaps, tuning and eigen
  residuals, window fixed-point residual, diagnostics W_A with overlap and ambiguity flags, timings, RSS) plus the
  nested-size differences.
  - Every ambiguous identification (overlap < 0.5) is also written to `flags.txt`, with chain, L, nz, family,
    branch and overlap (F22).
  - Every report (`points/descendants/nested.csv`, `flags.txt`) is regenerated on every run, with headers even
    when empty, and replaced atomically (F23).
  - Reported values are read from the validated bytes.
- `status.py` lists jobs from `SUBMITTED.jsonl` **and** `CONTINUATIONS.jsonl` (F24).

### 3.7 Tests (local plus validation job)
New tests in `tests/test_expanse.py`:
- **Spec and chain:**
  - spec freeze, immutability and checksum;
  - chain seed rule and predecessor validation: tampered, unaccepted, wrong chain, or wrong nz/basis are refused;
  - a failed check step does not stop the main ladder; a failed main step does;
  - exit-code propagation (65/66/73/75);
  - USR1 forwarding stops at a boundary (fake child).
- **Claims:** `recover_claims` with a fake sacct (terminal → archived; RUNNING or UNKNOWN → untouched;
  owner-job mismatch → untouched; `--apply` required).
- **Initial seed (F1, F9):** both declared origins are accepted when consistent (reference at L0; teacher at L0−2
  equal to the basis file). A wrong hash, missing or non-finite theta, wrong delta, a bath_cut inconsistent with the
  origin, or a teacher that is not the basis is refused. A production predecessor without an envelope is refused.
- **Continuation (F10):** a `complete` state with a stale chain claim leads to recovery and then success; a
  `complete` state with a missing or corrupt main record does not succeed; a check step with neither a record nor a
  failed_checks entry does not succeed.
- **R3 (F12):** a stop during the final scalar check with diagnostics='none' and no training publishes the record
  (exit 0); a stop after the solve with diagnostics pending still exits 75.
- **Chain ownership and state (F3):** a second driver on the same chain exits 73 and writes no state file; the
  continuation logic reads only PREV's state; a missing PREV state leads to recovery and resume.
- **History (F7):** an interrupted then resumed step leaves an archived checkpoint, and `collect.py` reports the
  maximum condition over both attempts.
- **Staging and environment (F5, F6):** the tar/spec/manifest sha256 mismatch paths and the env_id mismatch exit 74
  (run as a shell-level test with temp files).
- **Round-3 regressions:**
  - F13: a seed mutated after validation is refused by the child ("Inputs changed").
  - F14: a held recovery lock means exit 75; an ownership change between inspection and rename is moved back.
  - F15: a record of the same (L, nz) but another request (diagnostics) is refused.
  - F17: the slurm policy rejects compute, > 240 GB, > 48 h, a short lead and max_cont > 2.
  - F18: cross-x, wrong-L and missing-step edges are rejected.
  - F19: a seed failure on a check step gives exit 65; malformed persisted values (null or non-object
    checkpoints, non-object or partial outputs, unreadable or malformed inputs) are `IntegrityError` and exit 65
    end to end, with no `failed_checks` entry (round 5).

  Fix round 1 adds tests for HF-01, IR-01 to IR-08, the frozen guess and the x=1/8 guard. 100 tests pass with
  the frozen environment (job 54741586).
- **R3 behaviour:** a stop request after a complete record publishes it and exits 0; a stop during the Newton
  phase still exits 75.

## 4. Campaign

### 4.1 Grid (x = Δσ = (2−s)/2; 1/8 < x < 1/2)
- **Proposed** (awaiting the user's confirmation): the 10 reference points plus two strong-coupling points.

  | x | **0.125** | 0.126 | 0.135 | 0.15 | 0.175 | 0.2 | 0.25 | 0.3 | 0.35 | 0.4 | 0.45 | 0.475 | 0.495 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | s | 1.75 | 1.748 | 1.73 | 1.7 | 1.65 | 1.6 | 1.5 | 1.4 | 1.3 | 1.2 | 1.1 | 1.05 | 1.01 |

  The user confirmed this 13-chain grid on 2026-10-07: "yes add it" for 0.125, and "sounds good" for 0.135 and
  0.175.

- **x = 0.125 is an s* crossover benchmark, not a curve point.**
  - At s = s* = 7/4 the long-range model meets 2D Ising (Δ_E → 1) with marginal, logarithmic corrections, so a
    slow drift is expected rather than a clean extrapolation.
  - Its teacher (stage T, campaign teach2) has no same-x prior row. It therefore uses a frozen explicit `guess`
    equal to the shipped `teacher_L6_x0.126` theta (an adjacent-x continuation used only to train the basis).
  - The guess is a spec field of an unseeded teacher main step, validated as two finite numbers, and visible in
    the record's configuration. It is not allowed anywhere else.

- The 10 reference points match the 2D MC production values s = 1.05…1.7, plus one point near each endpoint.
- **New points (0.135, 0.175):**
  - Their L=6 teachers are trained in stage T with exactly the reference recipe: moving 24/192 local basis,
    consistent window, `--train-keep 20`, `--diagnostics none`.
  - The initial guess is the package's own default seed rule: the `inputs/prior_2d_points.json` row at the same x and
    nearest cutoff. Both x values have prior rows at L=6–12.
  - Both points are checked against the shipped teachers' recipe output fields (primary residuals, window gate)
    before use.

### 4.2 Ladder, local sizes, diagnostics
- **Main ladder per chain:** L = 8, 10, 12, …, Lmax with nz=16 from the chain's teacher, `--backend tensor`,
  `--diagnostics all`, the consistent window, and default tolerances (eig 1e-12, residual 1e-8, tuning 3e-11).
- **First step:** L=8, seeded from the reference `window_L8_z16` record's theta. For the new points it is seeded from
  the stage-T teacher theta. At L=8–12 the chain reproduces the reference curve, which is a regression check.
- **Lmax rule (from calibration):** the largest even L ≤ 26 that satisfies both of these (F4):
  - **Time:** the measured or extrapolated time of the slowest step at that L is ≤ 12 h on the chosen T. The slowest
    step is usually the nz20 check with diagnostics=all.
  - **Memory:** the job's **requested** memory M = ceil(1.3 × the largest step peak RSS + 4 GB) is ≤ 240 GB. This
    is below shared's MaxMemPerNode of 249325 MB and the ~243 GiB usable per standard node.

  If a larger L would need more, Lmax stops there. Changing partition policy (large-shared) is a separate user
  decision and not part of this plan. Calibration measures nz16 and nz20, both with diagnostics=all, at the two
  largest candidate L. Calibration at x=0.25 is in
  progress (job 54736192, L=14→24 chained); a strong-coupling calibration point is added if its time differs
  materially.
- **Nested checks at every L:** nz=20 with `--diagnostics all`, and nz=12 with `--diagnostics none`, both seeded
  from the nz=16 record at the same L.
- **Calibration evidence (Expanse, tensor, nz16, diagnostics=all, 32 threads, x=0.25):**

  | L | time (s) | peak RSS (GB) |
  |---|---|---|
  | 16 | 132 | 0.50 |
  | 18 | 392 | 1.10 |
  | 20 | 1221 | 2.94 |

  - Growth per +2 in L is ≈ 3.1× in time and ≈ 2.7× in RSS.
  - x=0.126, L=14 takes 86 s (nz16) and 114 s (nz20). Strong coupling is ≈ 2–3× slower (more Newton steps). The
    nz20 − nz16 thermal difference is 5e-14.
  - Jobs 54737271 and 54737250 continue to L=24 and L=22 respectively.
- **Lmax = 24 for every chain** (rule above).
  - Extrapolated L=24: x=0.25 nz16 ≈ 3.5 h at 32 threads; strong coupling nz20 ≈ 10 h. RSS ≈ 25–30 GB, so
    M = 64 GB. All are within the 12 h / 240 GB rule.
  - L=26 would be ≈ 3× L=24 (strong-coupling nz20 ≈ 30 h) and fails the rule.
  - Extending to L=26 is a possible follow-up campaign, not part of this plan.
- **Independent local reference:** a moving-basis nz=32/osc=256 consistent-window point (no density artifact) at
  L=14 for x ∈ {0.126, 0.25, 0.4}, seeded from the nz16 L=14 record. This repeats the reference's L=10–12 check
  one step higher.

### 4.3 Branch safety
- No step is ever seeded from a non-adjacent L or a different x, apart from the stage-T solves for the two new
  points.
- `collect.py` flags these:
  - a thermal-gap jump |ΔΔ_E(L→L+2)| > 3× the previous step's, above a documented numerical-noise floor of 1e-10
    (replays agree to about 1e-12; IR-08);
  - a tuning-Jacobian condition number > 1e8;
  - any ambiguous primary overlap.

  Flags go to the human, who decides; there is no automatic re-seeding.

### 4.4 Resources and budget
- **Job classes** (filled from calibration before the freeze):
  - small, L ≤ 16: in-chain steps;
  - the chain job's resources are those of its largest step.
- **Frozen values:**

  | Job type | Cores | Memory | Wall | Lead | max_cont | Notes |
  |---|---|---|---|---|---|---|
  | Production chains | 64 (speed over SU, user rule) | 64 GB | 2-00:00:00 | 7200 s | 2 | |
  | Moving-basis references | 32 | 32 GB | 0-12:00:00 | 1800 s | 1 | L=14 only |
  | Stage-T teachers | 8 | 16 GB | 0-02:00:00 | 1800 s | 0 | |

  - Production charge is max(64, 64/1.96) = 64 SU per hour.
  - Expected production time per chain ≈ 15 h (weak coupling) to 35 h (strong coupling).
- **Budget** (F8). Shared charging per job-hour is max(T, M/(1.96 GB)) SU, using 257400 MB / 128 cores.
  - Expected consumption (all steps finish in the first allocation) = Σ_chains (actual hours × that rate). It is
    estimated from calibration before the freeze and stated in the review log and the submission report.
  - Upper bound = (13 chains × (1 + max_cont) allocations × 48 h × 64 SU/h) + (3 references × 2 × 12 h × 32)
    + (validation, drills and stage T ≈ 2k SU) ≈ 119.8k + 2.3k + 2k ≈ 124k SU. That is ≈ 0.6% of the 22.08 M SU
    allocation, and is reported before submission.
  - Expected ≈ 13 × 25 h × 64 ≈ 21k SU.
- **Storage:** home only, < 1 GB.

### 4.5 Order of operations
| Stage | Content |
|---|---|
| S0 | Implement §3 and the R3 change. Commit on a `expanse` branch. Local pytest. |
| S1 | `install.sh`, then `validate.sbatch`. The receipt must pass (G1, G2). |
| S2 | Drills on the debug or shared partition (G3). |
| S3 | Stage T: teach1 (x=0.135, 0.175; default same-x prior seeds) is already done. teach2 (x=0.125, frozen guess) runs on the final release. |
| S4 | Freeze the spec and submit 13 chain jobs (plus 3 moving-basis reference jobs, dependent on the L=14 nz16 records). |
| S5 | Monitor, harvest, collect. |

## 5. Validation gates
- **G1:** the inherited 54 tests and the new tests pass on an Expanse compute node, through the receipt.
- **G2:** the reference replay matches to ≤ 1e-9 (§3.2) in the same receipt.
- **G3:** drills on Expanse (recorded in `campaigns/drill1/DRILLS.md`):
  1. `scancel --signal=USR1 --batch` on a running chain job → exit 75, checkpoint kept, claims released,
     continuation job created and resumed to completion;
  2. `scancel --signal=KILL` → stale claim; `recover_claims --dry-run` lists it, `--apply` archives it after sacct
     confirms the job is terminal, and a resume completes;
  3. a second submit of the same chain is refused by `submit.py`. A hand-made duplicate job exits 73 at the claim
     or is refused by the continuation guard.
  4. **The combined path (F25).**
     - While a point is in its final check or diagnostics (the checkpoint history already shows convergence), send
       `scancel --signal=USR1 --batch <job>`. The trap queues the continuation, and the point keeps computing.
     - Then `scancel --signal=KILL <job>`, standing in for the wall kill: no state file is written, and the claims
       stay fail-closed.
     - The queued continuation must confirm PREV terminal, recover PREV's chain claim and point claim, and resume
       from the converged checkpoint. It must then publish the record and complete the chain.
- **G4:** the first production records at L=8, 10 and 12 agree with the reference `window_L{8,10,12}` values to
  ≤ 1e-9 where the reference exists.

## 6. Verification commands
- **Local:** `python -m pytest tests/ -q` (inherited plus `tests/test_expanse.py`).
- **Expanse:**
  ```
  bash cluster/expanse/install.sh
  sbatch cluster/expanse/validate.sbatch <commit>
  python cluster/expanse/campaign.py freeze …
  python cluster/expanse/submit.py --spec … --dry-run
  ```
  Then the drill recipe in `cluster/expanse/README.md`.
- **Expected:** `receipt.json` passed=true; drills logged in `campaigns/drill/DRILLS.md`; `status.py` shows chains
  progressing.

## 7. Non-goals
- No change to the Hamiltonian, the window prescription, the tolerances, the eigensolvers or the precision. No
  physics fitting or extrapolation in this loop.
- No MPI, GPU or Lustre usage, and no use of the `compute` partition.
- No raw-prescription (`--window none`) production runs. The reference already has raw L=10, and raw is not
  supported on the density path.
- No automatic branch selection or retraining.

## 8. Risks
- **Calibration extrapolation:** large-L time and memory may exceed estimates. Mitigations: per-step walltime
  checkpoints, continuations, and the Lmax rule applied before the freeze.
- **NFS home under load:** small files and few writers keep the risk low. Publication stays atomic.
- **The R3 change is a code change in `hpc.py`:** it is covered by new tests and by Codex inspection.
- **Strong-coupling branch jumps at large L:** flagged for a human decision, never auto-fixed.
