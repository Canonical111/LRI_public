# Data of lri_3d_c4_exact

Everything `make -f public.mk replay` and `make -f public.mk test` read is in git; nothing is hosted.

- **The package's own results (`results/`, about 3 MB, in the package's git history):** the production outputs,
  written by the package's drivers (`PROVENANCE.md` lists the job of each):
  - `c4_L200.npz`, `c4_L300.npz`, `c4_L600.npz`: C2..C4 raw and consistent, r, g, energies at every even L;
  - `windows_L8000.npz`, `offdiag_L400.npz`, `offdiag_L8000.npz`, `dchi_L120/600/1000.npz`: the window shifts;
  - `c5_L12.npz`, `c5_L20.npz`: C2..C5 in every scheme;
  - `c5raw_all_L20/L40.npz`, `c5raw_sp_L20.npz`: raw C5;
  - `dC5_L200/L600.npz`: the scheme shifts at eps^5;
  - `eps5/legw_L400.npz`: the leg response S(L);
  - `eps5/C5_schemes.npz`: C5 per scheme at L <= 40;
  - `brute/`, `brute_zm_L6.json`, `tag/`, `eps5/desc_L*.json`: brute force and descendant checks;
  - `regress/`: the regression logs of the final engine.
  None of these files is bound by a checksum. Several were written on the symmetry cluster; the text logs in
  `regress/` name its nodes and paths and are scrubbed for publication.
- **Read from the sibling package:** `../lri_3d_hpc/results/reference_coefficients_L14.json` (the original code's
  results, L <= 14) and `../lri_3d_hpc/reference/` (its operators, for the brute force).
- **Read from the records:** `../../data/HT_3d/pert3d/results` (the production campaign, L = 16..20).
- **The fit summaries** `fits/*.txt` are outputs of the package's scripts on `results/`; the replay regenerates them.

Not shipped: the job-log tails `results/eps5/joblogs/` (operational; the jobs are listed in `PROVENANCE.md`), the
memory and timing probes (`profile4.py`, `eps5/prof5.py`, `eps5/prof_heavy.py`, `eps5/memprobe*.py`,
`results/regress/memprobe_L12_20.txt`), and the engine's task caches (rebuildable, not read).

Scrubbed for publication (cluster paths, user and node names replaced by placeholders; no checksum list binds them, and
no target reads them): `README.md`, `results/regress/log_574029.txt`, `results/regress/log_574030.txt`,
`results/regress/log_574365_boxes_L40.txt`, `results/regress/L40_boxes_before_restart.txt`. Every other shipped file
is byte-identical to git commit `d5afa4f`.
