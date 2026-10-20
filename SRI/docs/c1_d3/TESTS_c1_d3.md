# Tests: c1_d3 (simulated export, 2026-10-15)

Simulated export: the repository's `.maintainer/export.py` copied into a scratch `sim/.maintainer/` with source_root
<PROJECT>, the real global_exclude, the three c1_d3 entries (the delivery, `review_indep/`, the overlay) and entries for
`SRI/verify/` and `SRI/results/`; `export.py --apply`. `SRI/code/c1_d3` has 286 files (274 of the delivery, 4 in
`review_indep/`, 8 of the overlay), 6.5 MB, 3.69 MB packed with `tar czf` (the tested archive, with `SRI/verify` and
`SRI/results`: sha256 65d72572...). It was copied to symmetry and unpacked into node-local storage
`/local1/<USER>/<job>/SRI` (a path containing "local1"). Interpreter: the acceptance venv
(`<SCRATCH>/lri_public_test/venv_all/bin/python`: Python 3.12.9, NumPy 2.3.5, SciPy 1.17.1, mpmath 1.3.0,
threadpoolctl 3.7.0, matplotlib 3.11.2, sympy 1.14), read-only. Commands from `SRI/code/c1_d3/`:
`make -f public.mk test PY=<venv python>`, then `replay` and `replay-full` side by side (one core each). No script the
replays run filters paths by substring (only `__pycache__`, `.venv`, `.git` and the `checkpoint_` prefix).

| Job | Partition, node | CPU | make test | make replay | make replay-full |
|---|---|---|---|---|---|
| 575654 (final tree) | sharedq, <NODE> | Intel Xeon Gold 6148 | PASS 8/8, 15 s | PASS 19 + 5 INFO, 511 s | PASS 10/10, 1426 s |
| 575655 (final tree) | amddebugq, <NODE> | AMD EPYC 7532 | PASS 8/8, 14 s | PASS 19 + 5 INFO, 535 s | PASS 10/10, 1490 s |
| 575650, 575651 | sharedq, amddebugq | | cancelled by me while running (the tree changed: wording of comments and a header) | | |
| 575626, 575627 | sharedq <NODE>, amddebugq <NODE> | Intel, AMD | PASS | PASS 17 + 3 INFO (before `review_indep/`) | PASS |
| 575591, 575592 | sharedq <NODE>, amddebugq <NODE> | Intel, AMD | PASS | Intel PASS; AMD FAIL: the CSV comparison read JSON-list cells as strings and flagged 1e-16 differences; fixed | Intel PASS |

After 575654/575655 one file changed: `review_indep/README.md` (new text of the overlay; not in `SNAPSHOT.sha256`, read
by no script), whose last paragraph now gives the AMD values as well. Every other file of the final export is
byte-identical to the tested archive (`diff -r`).

Agreement with the shipped full run: on Intel the rerun is bit-identical (every JSON, NPZ and CSV value; the only
difference is a 2.2e-19 LP value). On AMD the largest differences are 1.4e-10 (precision JSON), 3.0e-9 (refinement
JSON, a sampled nonlinearity ratio), 9.8e-5 absolute in the LP arrays (0.03 of the tolerance), 2.6e-13 in
`current_summary.json`, 1.6e-12 in the CSV tables and 4.8e-13 in the box-scenario endpoints.

Quoted rows (both CPUs): `\SRthreeCone` PASS (0.2731524238 -> 0.2732); `\SRthreeConeRange` PASS ([0.269, 0.276] ->
[0.2690, 0.2760]); `\SRthreeConeBRRZ` INFO (literature, cited); tab:sr d = 3 row PASS; inputs S, E_SR PASS;
`/retained/C1` of `current_summary.json` PASS; cited check "Two independent implementations agree to 10^{-12}" PASS:

| | Intel (575654) | AMD (575655) |
|---|---|---|
| implementation A (`review_indep/indep`), c_1 | 0.27315242382605887 (diff 4.2e-14), 35 s | 0.27315242382607535 (5.8e-14), 31 s |
| implementation B (`review_indep/physics_review`), c_1 | 0.273152423826311 (2.9e-13), 21 s | 0.2731524238264792 (4.6e-13), 20 s |
| package rerun, c_1 | 0.27315242382601645 | 0.27315242382601695 |
| A - B, c_1 | 2.5e-13 | 4.0e-13 |
| a0, relative: A, B, A - B | 1.6e-13, 1.3e-12, 1.2e-12 | 2.3e-13, 2.1e-12, 1.8e-12 |
| b0, relative: A, B, A - B | 5.7e-15, 2.5e-13, 2.4e-13 | 1.4e-14, 3.8e-13, 3.7e-13 |

Tolerance: absolute 1e-12 on c_1 for A, B and A - B. The package's same-domain consistency check (INFO): relative
1.5e-13 (a0), 1.0e-13 (b0), 5e-14 (c_1).

The checksum checks were also exercised on a local copy: a scrubbed file fails unless it is listed in
`public/SCRUBBED.txt` or re-pinned in a `RE-PINNED.json` map, and passes in both of those cases.
