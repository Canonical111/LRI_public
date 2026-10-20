# Slurm templates for a rerun of the independent C8(3) campaign

These templates replace the package's site layer (`tools/submit.py`, `slurm/*.sh`, `docs/CLUSTERS.md`), which ships
verbatim as the record of what ran but encodes one user's allocation, caps and node exclusions. The templates run the
same science commands with the production options of `prod1`. Nothing here was run in this form; the production ran
the package's own scripts through `tools/submit.py` (see `../PROVENANCE.md`).

1. `cp env.sh.template env.sh`, fill it, and `export C8_ENV=$PWD/env.sh`.
2. `make -f public.mk fetch-data` in the package folder (graph payloads and the delivered pilot; 8.98 GB unpacked).
3. `sbatch build_test.slurm`: builds `bin/` in place on the lane CPU model and runs `make -f public.mk test`.
4. `sbatch plan.slurm` with `<NAME>`, `<FRESH_SEED>`, `<LANES>` filled (1 h 41 min on Lustre for prod1).
5. `sbatch lanes.slurm` with `<NODES>` = `<LANES>`/16 (prod1: 6 nodes, 12 h 44 min, 76.4 node-h). Resubmit it to
   continue; or use `index_tail.slurm` and then `lanes.slurm` on the `<NAME>_tail` index with 1 node for a short tail.
6. `sbatch --dependency=afterok:<lanes job> assemble.slurm` (46 s). Then compare the new `C8_result_<job>.json` with
   `../../results/C8_3_check/runs/prod1/C8_result_54838171.json`: a fresh seed gives an independent estimate, which
   should agree within the combined sampling errors (prod1: 1600.98 +- 3.97), not bit for bit.

Placeholders: `<ACCOUNT>`, `<PARTITION_SHARED>` (a partition for 4-32 cores), `<PARTITION_NODE>` (whole nodes),
`<NODES>`, `<NODE_MEM>` (prod1: 240G on 256 GB nodes), `<NAME>`, `<FRESH_SEED>`, `<LANES>`, and in env.sh
`<LOAD_MODULES>`, `<BOOST_ROOT>`, `<GMP_ROOT>`, `<VENV>`, `<GFF>`, `<RUN_ROOT>`, `<SCRATCH>`.

The lane layout assumes 128-core nodes (16 lanes x 8 threads). For other node sizes keep 8 threads per lane and set
`--ntasks-per-node` = cores / 8; the index's lane count must equal nodes x lanes per node.
