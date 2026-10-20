# Integration with the reviewed Expanse campaign

The supplied HPC report describes acceptance, claim, failure-classification, and
Expanse launch changes after the originally retained `lri_hpc` package. The actual
`c0c30783db5d...` source revision was NOT supplied. This archive therefore cannot
claim to incorporate or independently re-review those changes.

It installs a separate `lri_eh` namespace, so `pip install -e .` does not overwrite
`lri_hpc`. Retained legacy files under `reference/` exist only for numerical tests.
The copied internal `_core` is isolated from the campaign's production namespace.

Recommended site review sequence:

1. Verify MANIFEST_SHA256.json and compare the numerical changes described in
   ALGORITHM.md with the preserved original code. Run the full local suite.
2. Run `slurm/validate.sbatch` on the target compute environment. Inspect the tests
   and smoke gates and retain its source/dependency-bound receipt.
3. Reuse the existing campaign's reviewed environment, claim policy and failure
   classification where appropriate. Review any interface adapter; don't replace
   the production directory with this archive or reuse its raw checkpoints.
4. Calibrate the NEW correction task at two or more cutoffs and several thread
   counts (for example 4, 16, 32). The raw thermal memory/time model is not the
   correction task's model. Treat planner sizes as conservative engineering
   estimates, not measured Expanse resource consumption.
5. Test one intentionally interrupted item; confirm completed-reference reuse,
   bounded attempts, no duplicate live claim, and rejection of corrupted output.
   Confirm flock on the actual Lustre path. Explicitly test inherited scheduler
   signals and CPU affinity before long runs.
6. Freeze the addon source and create validation-gated manifests. Update the
   external site's account/expiry configuration; no historical expiry is embedded
   in this package.
7. Export only accepted records and join by cutoff with explicit raw/addon source
   fingerprints. Do not silently mix degrees or apply the correction twice.

The new Slurm templates are generic and have not been executed on Expanse here.
Their mechanisms were reviewed against official Slurm documentation, while the
POSIX claim/restart logic was exercised locally. Single-cutoff MPI and GPU kernels
are not enabled. Independent cutoffs scale across nodes through arrays/lanes.

Primary implementation documentation consulted:
- https://numba.readthedocs.io/en/stable/user/parallel.html
- https://numba.readthedocs.io/en/stable/developer/caching.html
- https://slurm.schedmd.com/job_array.html
- https://slurm.schedmd.com/sbatch.html

No numerical tolerances were relaxed for speed, and the physical correction was
not changed. This is software optimization and operational hardening, not new
matching physics. A target-cluster validation receipt is an acceptance prerequisite,
not a claim of independent scientific certification.
