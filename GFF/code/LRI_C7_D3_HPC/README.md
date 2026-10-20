# C7(3): optimized full-coefficient HPC package

Calculate C0 through C7 in dimension THREE, epsilon=2s-3, including both the
power-free and power-containing sectors. This release supplies validated
software and archived-data reproduction, not a new precision estimate.

## Verify and build

Run the integrity check BEFORE generating local build outputs:

    python3 tools/verify_delivery.py --strict
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install -r requirements.txt
    make -j4
    make test
    make -j4 decimal
    make test-full
    python3 tests/staging.py
    python3 tools/reassemble_reference.py

Default GMP350 matches original d=3 production. Optional decimal300 has lower
final-tier precision and must be selected deliberately. No precision threshold,
forest term or endpoint contribution is removed. The measured quotient-reuse
candidate did not reliably improve throughput and is kept only under experiments/.
The production native kernel is byte-identical to the original. The exploratory
exponential cache is NOT shipped. Requires GNU C++17/OpenMP, Boost, libquadmath and GMP;
no architecture-specific executable is delivered. Do not use fast-math or Ofast.

## Plan higher statistics

    export C7_PACKAGE="$PWD"
    export C7_RUN="/scratch/$USER/c7-d3-highprecision"
    python3 tools/production.py plan "$C7_RUN" \
      --seed 2026093003 --backend gmp --replicates 64 --multiplier 4 \
      --primitive-mode recompute --primitive-points 65536 \
      --shards 32 --threads 8 --chunk-points 65536 --checkpoint-tasks 32

Planning does not launch integrations. Twenty groups cover two independent
campaigns, both sectors and loops 3--7, with all required lower-loop Taylor jets.
Submit slurm/run_array.sh after adapting account, partition and resource limits.
The job index addresses manifest.json jobs. MPI is not required.

After all jobs finish:

    python3 tools/production.py merge "$C7_RUN" --scratch /tmp
    python3 tools/assemble.py "$C7_RUN" --bootstrap 4096

The output includes full covariance, power correction, per-loop errors,
independent-campaign comparison and bootstrap diagnostics. No new empirical
physical allowance is assigned automatically. Default primitive mode recomputes
all primitive strata; retained mode adds the archived primitive mean/error once.

## Contents

src/: optimized native worker. tools/: indexed packs, planning, checkpoints,
merging, analysis and benchmarks. tests/: numerical and workflow regressions.
inputs/: actual dimension-three kernels, low-loop data and frozen allocation.
reference/: complete original numerical package, byte-for-byte preserved.
docs/: numerical contract, cluster runbook and measured performance.
benchmarks/: matched timing, precision, workflow and reassembly evidence.
DELIVERY_MANIFEST.json and SHA256SUMS: complete integrity inventory.

The old inventory's d=2 offsets/hashes are never used for staging: input
preparation rebuilds them from actual d=3 graph payloads. Work identities use
campaign, loop, graph, replicate and point interval, not node/thread IDs.
Keep complete power-of-two Sobol nets; chunks are not independent replicates.

Archived-data regression reproduces C7(3)=-227.61810947469945 with sampling
SE=3.8273968756607397. The accepted empirical report remains -228 +/- 16.
No new high-statistics integration or independent scientific derivation was
performed for this software release. Local thread benchmarks are not evidence
of actual multi-node throughput. Rebuild and validate on the destination cluster.
