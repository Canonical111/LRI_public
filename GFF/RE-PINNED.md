# Files changed after production

These shipped files differ from the bytes that ran or were recorded: the authors' personal machine names were
replaced (author's rule: only the symmetry cluster and SDSC Expanse are named). The edits touch comments,
docstrings and machine-label fields only, so no number, input or code path changes. Each package's `public/SCRUBBED.txt` lists them, and
its verifiers treat them as scrubbed.

| File (under `GFF/`) | Original sha256 | Published sha256 | Edit |
|---|---|---|---|
| `code/LRI_C8_D2_HPC/slurm/env.sh.example` | `8ced5dac04f8920e1e30f5d5ff81f6bb73f6da83e99406b649d384c2e13bcabf` | `677b464da6233c68e50f92ea2fc78de0608d997ff9696ed8fbae5a5e8f1d6675` | comment line 38 only: the names of three personal workstations replaced by "personal desktops" |
| `code/LRI_C8_D2_HPC/tests/merge_scale.py` | `3a36da798ea4987e3db59f397d6ac17fee650fa654eb8a604a1f77eff0b01dde` | `24600a14c5f1a71230513e916271ef675f5382f88f76373d902f816ea9a351b6` | docstring only, two places: a personal machine's name replaced by "a personal desktop" |
| `code/LRI_C8_D3_HPC/benchmarks/symmetry_2026-10-c8/stage5_59d4922/smk4/thru_report_s6.json` | `2e06c877e667a7602a7d1784bd95d02f61c809984cb80cf0cbbe4cb66db8d075` | `4361ef4ddc55b6a356e78d8a98e681d151104665ee85cf78451c6e6fbc92d3ce` | rederived.made_on node only: a personal machine's name replaced by "personal desktop" (thru_report_test ignores the field) |
| `code/LRI_C8_D3_HPC/benchmarks/symmetry_2026-10-c8/stage5_59d4922/smk4/thru_report_s6b.json` | `1893d779dabf7a7894acee4653d888d607e83481b8234478b66e2001f08e45aa` | `dc09b503e0e16e928276cf68cd9c253a0d8f9135b1401779e89d7eadcb7a37fd` | rederived.made_on node only: a personal machine's name replaced by "personal desktop" (thru_report_test ignores the field) |
