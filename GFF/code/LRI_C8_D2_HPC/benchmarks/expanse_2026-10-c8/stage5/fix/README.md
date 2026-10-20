# G5 fixes on Expanse (2026-10-05): BLOCKED, nothing submitted

Planned in this workflow, after the merge of `fix-g5` into `c8` (e7e6589) and the job-script commit 2b3a923:
1. **One export** of 2b3a9233353d to `$C8_DATA/pkg/2b3a9233353d` (`scripts/fxe.sh export`, checked file by file), the
   L8 packs re-hashed and hard-linked from `pkg/7aac898add43`.
2. **J-EXP-1 rerun** on `debug` (`scripts/fxe_exp1.slurm`: `make && make gmp`, `make c7ref`, `make inspect`,
   `tests/check_venv.py --strict`, `make test`; F1-F4), with A-RPL-8: the default executables must stay
   `99a51c1d…` (decimal) and `1d2a2181…` (gmp), since `src/` is unchanged.
3. **The user-required dd+mp256 J-FLAG gate** on one `compute` node with `--exclude=<NODE>`
   (`scripts/fxe_flag.slurm`: `make gmp NUMERICS=dd,mp256`, A-RPL-8 before and after, then
   `tests/numerics_flags.py --profile dd+mp256` at full scale, F1-F5, F2's fixed base seed registered in `$C8_SEEDS`).

**None of this ran.** At about 15:16 UTC (08:16 PDT) Expanse's Lustre stopped answering on the login node: `lfs quota`,
`ls` and `stat` of `<SCRATCH>/temp_project/c8d2` hung (a command searching `$PATH`, which lists a
directory on `/expanse/lustre/projects`, hung as well), while commands that touch no Lustre path (`echo`,
`/bin/date`, `/usr/bin/cat /proc/loadavg`: load 32.6 at 15:43 UTC) answered. Those hung commands kept their sessions
on the shared ssh ControlMaster open, and from about 15:55 UTC the login node refused every new session on it
("mux_client_request_session: session request failed: Session open refused by peer"). The master itself stayed up
(`ssh -O check expanse`: "Master running"). By the workflow's rule no new login was opened (probes since 16:03 UTC use
`-o BatchMode=yes`, which fails at once with "Permission denied" instead of prompting). Probe times and answers:
`probes.txt`.

**Moved to symmetry (user rule of 2026-10-05, after this workflow stopped):** "symmetry is back, so for the moment only
use expanse if symmetry is not enough". The dd+mp256 J-FLAG gate (item 3) runs on symmetry, so `fxe_flag.slurm` is not
to be submitted; it stays in the repository as the record of the plan.

Owed on Expanse, once a session opens again (each script is committed and is in the export), and only these:
1. **The J-EXP-1 rerun (A-EXP-3; symmetry cannot substitute):** `bash benchmarks/expanse_2026-10-c8/stage5/fix/scripts/fxe.sh export`,
   then `fxe.sh exp1 $C8_DATA/pkg/<sha12>` of the commit then current (F1-F4 on Expanse's GCC 13.3 and its zen2 nodes).
2. **The two-log seed sync** of the seeds added on symmetry since the last sync
   (`benchmarks/symmetry_2026-10-c8/stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`;
   `benchmarks/symmetry_2026-10-c8/stage5/scripts/seedsync.sh`).
3. ~~The deletion of the 30 obsolete exports~~ **Done** by the host on 2026-10-05 at 10:40 PDT (user-approved,
   "Delete the 30"; the list in `../g4cfix/README.md`, "D6"): 29 deleted after re-grepping every evidence file;
   `pkg/d46e7360fe88` kept, because the completed gate job 54669708 read it as its B2f source tree and the approval
   covered unreferenced exports only. Lustre: 1,651,026 → 1,474,822 files (`../../README.md`, "Stage 5 fix round,
   close-out and the export deletion").

The H7E-R survey runs before every sbatch. Expected cost: about 45 SU for J-EXP-1 (a 128-core debug node for about
20 min); the seed sync runs on the login node. Items 1 and 2 are still owed (status: `../../README.md`, "Stage 5 fix
round, close-out and the export deletion").

No Expanse job, file or export was created or removed by this workflow; 0 SU.
