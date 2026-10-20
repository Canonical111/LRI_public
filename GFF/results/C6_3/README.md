# C6(3): production records

C6(3) = 33.5754 ± 0.0005 (estimator 33.57542664131543, sampling SE 0.0001185495235; four sampling SEs rounded up to a
multiple of 0.0001, Amendment 1 of `CAMPAIGN.md`). Sampling allowance only; see the note, Section 26.

- `CAMPAIGN.md`: the plan, launch log, pre-registered reporting rule, completion, result, Amendment 1 and errata.
- `results_run-20260929-m8192/`:
  - `C6_result.json`: the result;
  - `manifest.json`: the frozen plan;
  - per group `<campaign>_L<loop>/`: `config.json`, `merged.json` (64 replicate jet vectors) and
    `graph_replicates.csv`.

  These files are byte-identical to the production and bound to each other by SHA-256. Do not edit them.
- `run-20260929-m8192_full.tgz.sha256`: the checksum of the complete run directory. The run directory itself is
  hosted at `GFF/data/C6_3/` (`make fetch-data`, 74 MB).

Code and commands: `GFF/code/LRI_C6_D3_HPC/` (commit `1c6dfb3`), `public/README.md` there.
`make -f public.mk replay` recomputes every quoted number from these records.
