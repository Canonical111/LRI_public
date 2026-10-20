#!/bin/bash
# Native validation jobs of Stage 3a (PLAN.md Verification "Expanse"; J-INSPECT, J-VAL-2, J-VAL-4, J-RUN1), one script:
#   C8_JOB=val1      J-VAL-1 (the plan's `make test` on the cluster export, run step by step): the builds (make all,
#                    the decimal worker, c7ref, inspect, test-builds), tests/check_build.py on the four build records,
#                    make test-python's tests in five parallel streams (unit_orchestration one test function per step,
#                    with the Linux fingerprint and subprocess spies, A-ORC-13's platform class; check_inputs, members,
#                    workflow/staging --fake, ...; the Mac fakes of the admission engine end SITE_REFUSED, see
#                    pstep), then tests/validate.py (subset) and tests/class_b.py, tests/workflow.py and tests/staging.py
#                    with the real workers (--plan-role validation, D.5), tests/vendored_isolated.py --in-place with
#                    this job's A-ASM-3 record, tests/check_vendored.py --no-review-record (A-ASM-1 on the export).
#                    Since Stage 2b pinned the L8 packs, val1 works in the L8 work copy with the store's packs linked in
#                    (Stage 3b below; check_inputs, class_b, workflow and staging read them).
#                    Plan: template, -t 01:00:00 (this workflow: shared -c 32 --mem=64G).
#   C8_JOB=inspect   make inputs-inspect (L <= 7 now; Stage 2b adds L8): bin/c8d3_inspect over every packed kernel
#                    and gen3's size probe -> inspect/inspect.json, then make inputs merges the fields into
#                    inputs/inventory.json (+ manifest). The three files are copied to the evidence for the
#                    generated-data commit. Plan: shared -c 16 --mem=32G -t 01:00:00.
#   C8_JOB=val2      J-VAL-2, L <= 7 parts: the builds (bin/c8d3_{gmp,decimal}, make c7ref, inspect, test-builds),
#                    tests/check_build.py on the four build records, tests/validate.py --full (A-KER-1..3, A-RPL-1 on
#                    the L2 graph and all C7(3) kernels, A-RPL-2 on them), tests/class_b.py (A-KER-6 (a)-(e), A-KER-7),
#                    tests/inspect_check.py (A-KER-5, when the inventory carries the inspect fields) and
#                    tests/check_points.py (A-RPL-5 L <= 7 hard, A-KER-7's 450-digit fixture), and a smoke of
#                    tests/forced_tiers.py (the A-RPL-4 tool on 8 L7 kernels per sector; the gate is J-VAL-3). Plan: template,
#                    -c 64 --mem=120G -t 03:00:00 (this workflow: -t 01:00:00).
#   C8_JOB=val3a     the J-VAL-3 parts of tests/validate.py that need no L8 data, as a check of the tools at L <= 7:
#                    --bk8 (A-RPL-3 at L7) and --l2-control (A-IN-6); the gates themselves are G3b's (J-VAL-3).
#                    Shared or debug, -c 32 --mem=60G -t 00:30:00.
#   C8_JOB=val4      J-VAL-4 (L <= 7): make sanitize; tests/sanitize.py --selftest --parsers --runs --max-loop 7
#                    (A-KER-4's parts for L <= 7; L8 joins in Stage 3b). Plan: shared -c 32 --mem=60G -t 03:00:00.
#   C8_JOB=run1      J-RUN1: bin/c8d3_gmp and make c7ref; tests/run1_replay.py on the pinned run1 archive (A-RPL-7
#                    G-RUN1 T1-T5), tests/archived_stream_replay.py (make test-replay) with the C8 worker in order-7
#                    mode, and tests/test_pilot_report.py --run1 (A-DES-3's run1 part: run1's 27 of 590 power-L7 graphs
#                    and P8_hat 1.078-1.103 from the archive). Plan: compute --exclusive -t 01:30:00 (this workflow:
#                    shared -c 64 --mem=120G -t 01:00:00).
#   C8_JOB=repair3a  Stage 3a repair round 1, the parts the round changed (shared -c 64 --mem=120G -t 01:00:00): the
#                    builds and check_build; tests/validate.py --full --parts identity,g_c7 (A-RPL-1 with the nondirect
#                    totals and the shift case on the A-L18 hunk, A-RPL-2 on the C7(3) kernels); tests/inspect_check.py
#                    (A-KER-5, >= 100 graphs); tests/class_b.py --parts e (A-KER-6 (e), with the new zero-channel L7
#                    kernels of the d=3 payload when C8_D3_PAYLOAD and C8_D3_PIN are set); tests/test_pilot_report.py
#                    --run1; the G-RUN1 selection seed 20261004 registered in $C8_SEEDS (created if absent; HD6).
#   C8_JOB=repair3b  Stage 3a repair round 2 (A-DES-3's real-tail part; shared -c 16 --mem=32G -t 00:30:00): the C8 workers,
#                    inspect and test-builds; tests/class_b.py --parts e --zero-channel-tails (every zero-channel kernel of
#                    (e), with the new L7 ones when C8_D3_PAYLOAD and C8_D3_PIN are set, integrated in the pilot shape: both
#                    campaigns, 8 replicates x 32,768 points nested at 4,096); tests/test_pilot_report.py --zero-channel on
#                    those rows (pilot_report's tail_stats, screen_graph, confirm_graph: finite or "undefined", no NaN);
#                    $C8_SEEDS copied byte for byte to the evidence (the designs/forbidden_seeds.json mirror, HD6).
# Stage 3b (needs G2b: the inputs pin the L8 packs). The L8 jobs work in a copy of the export on Lustre
# ($C8_ROOT/work/<job>_<id>) with the store's L8 packs hard-linked in (`make link-l8 STORE=$C8_STORE`, no 8.8 GB copy);
# val1/val2/val3/val4 remove it after a full pass, sweep1 and argmax keep it (their campaigns name it):
#   C8_JOB=val2      J-VAL-2 with L8: the builds, check_build, validate.py --full (A-RPL-1 on the L2 graph and every L <= 7
#                    kernel, A-RPL-2 on all 3,773 L <= 7 kernels: the 262 new L7 ones included), class_b.py (A-KER-6
#                    (a)-(f), L8 in (a) and (f)), inspect_check.py, check_points.py (A-RPL-5 L3-L7 hard, L8 in contract
#                    mode), the forced_tiers.py smoke, check_inputs.py (A-IN-5 with the L8 packs), workflow.py and
#                    staging.py with the real workers (--plan-role validation, D.5), compat_run1.py.
#                    Plan: shared -c 64 --mem=120G (this workflow: -t 01:15:00).
#   C8_JOB=val3      J-VAL-3 (compute --exclusive --mem=240G -t 02:00:00): the builds, then three streams at once:
#                    forced_tiers.py (A-RPL-4 at L7 and L8; C8_FT_THREADS, default 128, C8_FT_MAX_SECONDS, default 1200 s
#                    per sector and loop); thread_identity.py (A-RPL-6) then validate.py --bk8
#                    --l2-control (A-RPL-3 at L7 and L8, A-IN-6); merge_scale.py --rows 1000000 (A-ORC-6's cluster
#                    part), assembly_checks.py --exact and compat_run1.py (A-ASM-3/4 on the cluster), prefix_check.py
#                    --real (A-DES-8 (e)).
#   C8_JOB=val4      J-VAL-4 with L8: make sanitize; sanitize.py --selftest --parsers --runs --max-loop 8 (A-KER-4).
#                    Plan: shared -c 32 --mem=60G (this workflow: -t 01:30:00).
#   C8_JOB=sweep1    J-SWEEP-1 (compute --exclusive --mem=240G -t 01:00:00; `raw --dir $C8_SWEEP_RUN`): bin/c8d3_gmp and
#                    bin/c8d3_decimal, check_build, tools/sweep.py $C8_SWEEP_RUN --seed $C8_SWEEP_SEED (bootstrap basis,
#                    --bootstrap-chunk 512 --shards 32, one lane per NUMA domain; plan, run, merge, make_cost_model.py ->
#                    $EV/$C8_SITE_MODEL, the site's model name from slurm/site.sh c8_site_cpu: Expanse
#                    gmp_expanse_epyc7742_c8.json; the plan reserves the seed in $C8_SEEDS before anything runs,
#                    --reserve-seed, S2-002), seeds.py add (HD6; idempotent), assemble.py on the test campaign (A-IN-7),
#                    cost_identity.py check of the model against the binary, cost_summary.py, and the binaries the model
#                    measured copied to $C8_STORE/baseline/<sha12>/ (the c8-stage3 baseline, bin/baseline/).
#   C8_JOB=argmaxre  J-ARGMAX's step 4 again on its merged campaign $C8_ARGMAX_RUN (tests/argmax_run.py --reinspect; no new
#                    point; records y and jac of every argmax point too) with cost_models/$C8_SITE_MODEL. Plan: debug -c 4
#                    --mem=8G -t 00:15:00.
#   C8_JOB=argmax    J-ARGMAX (shared -c 32 --mem=64G -t 00:45:00; `raw --dir $C8_ARGMAX_RUN`) on the export of the
#                    data-only commit that carries J-SWEEP-1's model as cost_models/$C8_SITE_MODEL (Expanse
#                    gmp_expanse_epyc7742_c8.json): the
#                    rebuilt bin/c8d3_gmp checked against the model (cost_identity.py check --model --exe, J-BLD's check)
#                    and against the stored baseline; tests/argmax_run.py $C8_ARGMAX_RUN --seed $C8_ARGMAX_SEED (A-DES-6);
#                    accounting.py on the sweep campaign (from its work copy $C8_SWEEP_PKG) and cost_summary.py with it.
# Stage 5 (PLAN D.14, J-SWEEP-2, J-BLD; docs/HPC.md "Stage 5: the calibration refresh and the campaign build"), either site:
#   C8_JOB=sweep2    J-SWEEP-2, the calibration refresh of the final binary (symmetry: -p amdq -c 64 --mem=240G -t 01:00:00;
#                    Expanse: compute --exclusive --mem=240G -t 01:00:00; `raw --role sweep2 --dir $C8_SWEEP_RUN`):
#                    C8_SWEEP_RUN (a new $C8_ROOT/runs/<name>), C8_SWEEP_SEED (fresh); optional C8_SWEEP_PREV
#                    (cost_models/<file>.json; default cost_models/$C8_SITE_MODEL when the export has it, else
#                    cost_models/gmp_expanse_epyc7742_c8.json, the package's first measured model) and C8_SWEEP_LANES
#                    (default: Expanse 16, P4's 16 x 8; symmetry numa, 8 x 8 on NPS4; an inherited C8_LANES is ignored).
#                    In the L8 work copy $C8_ROOT/work/sweep2_<id>: bin/c8d3_{gmp,decimal}, check_build, sweep.py
#                    --choose-only (basis.log), sweep.py --refresh PREV --output $EV/$C8_SITE_MODEL --report
#                    $EV/refresh_report.json (role cost_refresh; basis measured, prior_model at F = 2 or bootstrap from
#                    PREV's HD11 fields; --reserve-seed $C8_SEEDS: the seed reserved before anything runs, S2-002),
#                    seeds.py add (HD6; idempotent), cost_identity.py check --host-cpu --mp-check on of the fresh
#                    model, refresh_record.json (both executables, PREV, the basis), assemble.py (A-IN-7), cost_summary.py.
#                    Nothing goes to $C8_STORE/baseline. Evidence: $C8_ROOT/evidence/<sha12>/sweep2_<id>/ (never
#                    overwritten); the data-only commit takes $EV/$C8_SITE_MODEL into cost_models/ and $EV into benchmarks/.
#   C8_JOB=bld       J-BLD on the export of a data-only commit (symmetry: -p amddebugq -c 64 --mem=240G -t 00:30:00;
#                    Expanse: shared -c 32 --mem=60G -t 00:20:00), built IN PLACE ($C8_PACKAGE itself; once per export,
#                    before any plan on it): C8_BLD_BASE_PKG (the sha12 of the code commit's export in $C8_ROOT/pkg/;
#                    never the data export itself, 64); optional C8_SWEEP_RUN and C8_SWEEP_PKG together. The BASE
#                    export's tools/cost_identity.py data-only (only cost_models/, benchmarks/ and the carry set may
#                    differ, the seed mirror only grows; first, nothing written before it), make link-l8, make
#                    verify-inputs, bin/c8d3_{gmp,decimal}, check_build, cost_identity.py check --model
#                    cost_models/$C8_SITE_MODEL --exe bin/c8d3_gmp --host-cpu --mp-check on (HD11), model_record.json;
#                    with C8_SWEEP_*: the sweep's accounting.py and cost_summary.py --accounting (bookkeeping). A failed
#                    build or check moves bin/ to bin.bld_failed_<id> (no plan or lane uses an unchecked binary; PLAN risk
#                    32); a failed bookkeeping step alone keeps bin/ and names the two commands to rerun. Every copy of
#                    an export (every other mode's, opt's variant and PREV, basestore's BASE) skips a built export's bin/
#                    and L8 pack links (copy_export).
# Stage 4a (PLAN "Performance plan", Profiling first; A-PERF-1; on the c8-stage3 baseline: every job checks that the
# rebuilt bin/c8d3_gmp is the site's baseline, Expanse 24adff54..., reference/baseline_c8_stage3.json, and stops otherwise). The L8
# packs are hard-linked into a Lustre work copy as above; perf.data and staged graphs stay on node-local $C8_SCRATCH:
#   C8_JOB=profbuild the tools on a small allocation before any profile job (shared -c 16 --mem=32G -t 00:30:00): the
#                    builds (bin/c8d3_gmp, make profile ratiohist c7ref) and the baseline check, the fixtures
#                    (prepare_benchmarks.py --order 8 verify and --stage-check of every fixture graph from the packs,
#                    --order 7), perf's availability, and smoke runs of every profile mode on tiny cuts of the blocks
#                    (--smoke-tasks/--smoke-points, --fake-topology --no-pin: a function test, never a measurement).
#   C8_JOB=prof1     J-PROF-1 (compute --exclusive --mem=240G -t 01:00:00): FIRST, with nothing else on the node,
#                    tests/merge_scale.py's scale part (--rows 1000000 --jobs 16 --run-jobs 16; the clean merge rates of
#                    Stage 3b repair round 2); then the builds; perf_profile.py fe (the f_E repeat), p1 (P1: perf record on
#                    socket 0, tier timers on socket 1, 64 threads each) and mpcheck (the MP self-check overhead).
#   C8_JOB=prof2     J-PROF-2 (compute --exclusive --mem=240G -t 01:00:00): benchmark.py --lane-shapes
#                    8x16,4x32,2x64,1x128,16x8 (P4; J-E0's sysfs shows 8 NUMA domains x 16 cores, so no 32x4).
#   C8_JOB=prof3     J-PROF-3 (compute --exclusive --mem=240G -t 00:45:00): perf_profile.py p2 (P2: perf stat IPC) and
#                    benchmark.py --interleave-probe (P2's second measure), then p3 (P3: ratio histograms at .8 and .7).
# Stage 4b (PLAN "Performance plan", default-path optimizations, each gated by A-PERF-2; A-RPL-1/2/4/6/8). The L8 packs
# are hard-linked into a Lustre work copy as above:
#   C8_JOB=optsmoke  the Stage-4b tools on a small allocation before the first J-OPT (shared -c 16 --mem=32G -t 00:30:00):
#                    the builds (bin/c8d3_{gmp,decimal}, make quaddiff when the commit has it), `make baseline`, and smoke
#                    runs (never measurements) of validate.py --l8self (--l8self-sizes 2,6,4), tests/first_error.py (1
#                    repeat), tools/opt_speed.py (--sample-sizes 2,6,4, --fake-topology 1x2x8 --no-pin, 1 repeat),
#                    tests/thread_identity.py (blocks at 1 and 8 threads, the 2 and 16 lane splits) and, with quaddiff,
#                    tests/quad_differential.py (2^20 pairs per operation, 2^14 under the sanitizers).
#   C8_JOB=opt       J-OPT-<R> (compute --exclusive --mem=240G -t 01:00:00): one optimization's A-PERF-2 gate on the export
#                    of its commit. C8_OPT_STEP names it (R5a, R5b, 4, 6, 8, 7, or final for G4b); after the first kept
#                    change the previous binary PREV is either C8_OPT_PREV, the sha12 of the last kept commit whose
#                    binaries an earlier opt job stored in $C8_STORE/opt/<sha12>/ (SHA256SUMS checked), or
#                    C8_OPT_PREV_PKG, the sha12 of the last kept commit's export in $C8_ROOT/pkg/, whose
#                    bin/c8d3_{gmp,decimal} the job builds first on the same node (so jobs of successive changes can run
#                    at the same time). The builds (bin/c8d3_{gmp,decimal}, make c7ref, make
#                    quaddiff when the commit has it), check_build, `make baseline` (bin/baseline = c8-stage3, checked).
#                    Then the EXACT GATES, C8_OPT_GATES (comma list; default validate_full,l8self,thread_identity):
#                      validate_full    validate.py --full: identity, G-C7 and G-JET on the L2 graph and every L <= 7 kernel
#                                       (A-RPL-1/2 full), bad inputs, orders, chunk splits; concurrently with
#                      l8self           validate.py --parts none --l8self bin/baseline (A-RPL-8 G-L8SELF, both backends);
#                      first_error      tests/first_error.py --baseline bin/baseline (R5a's error order);
#                      same_binary      the rebuilt bin/c8d3_{gmp,decimal} equal $C8_STORE/opt/$C8_OPT_PREV's (a tools-only
#                                       change: A-RPL-1/2/8 hold by identity);
#                      thread_identity  tests/thread_identity.py (A-RPL-6, with the 16 x 8 default lanes of R5b);
#                      inspect_check    tests/inspect_check.py (A-KER-5);
#                      quaddiff         tests/quad_differential.py at 128 threads (#4's proof);
#                      forced_tiers     tests/forced_tiers.py (A-RPL-4) and tests/record_compare.py against the Stage-3
#                                       J-VAL-3 record in benchmarks/expanse_2026-10-c8/stage_3b/.
#                    Then, only when every gate passed, the speed: tools/opt_speed.py (A-PERF-2; nothing else on the node)
#                    with B0 = bin/baseline/c8d3_gmp, PREV = the stored c8d3_gmp of C8_OPT_PREV and CAND = bin/c8d3_gmp, steps
#                    <STEP> = PREV:CAND (B0:CAND without PREV), cumulative = B0:CAND and prev_vs_stage3 = B0:PREV;
#                    C8_OPT_SHAPES (e.g. B0=8x16,PREV=8x16) gives binaries another lane shape (R5b). Last, the candidate's
#                    binaries and build records go read-only to $C8_STORE/opt/<sha12>/ with SHA256SUMS (never overwritten).
#                    C8_OPT_VARIANT_OPTFLAGS (#7, opt-in; e.g. "-O3 -march=x86-64-v3", STRICT kept): after the gates, the
#                    same source is also built with those OPTFLAGS in a second Lustre work copy, gated by validate.py --full
#                    and --l8self there (A-RPL-1/2/8), and timed as VAR (step 7 = CAND:VAR); never stored, never default.
#                    Evidence: $C8_ROOT/evidence/<sha12>/opt_<STEP>/.
# Symmetry (Amendment A1; J-BASE-sym and the symmetry baseline, A1 repair round 2):
#   C8_JOB=basestore J-BASE-sym: the c8-stage3 commit's bin/c8d3_{gmp,decimal} built with this site's toolchain on this
#                    node from its export C8_BASE_PKG (the sha12 of $C8_ROOT/pkg/<sha12>, a git archive of the commit of
#                    reference/baseline_c8_stage3.json), tests/check_build.py with the site's expectations, then the
#                    binaries and build records copied read-only to $C8_STORE/baseline/<C8_BASE_PKG>/ with SHA256SUMS
#                    (never overwritten); `tools/baseline.py record --site <site>` pins them in the site's record.
#                    Symmetry: -p amddebugq -c 64 --mem=240G -t 00:59:00 (cn112 and the CPU pin's nodes excluded by slurm_submit.py).
# Every job first passes the CPU pin (slurm/site.sh c8_cpu_guard, HD11: symmetry's AMD jobs on EPYC 7543, Expanse's on EPYC
# 7742; 68 before anything is written, the argument checks stay 64 and come first; environment.txt records cpu_expect,
# site_model, cpu_source and cpu_read, so a set C8_PROC test seam shows as "TEST SEAM" there and as a WARNING in the log). Every job takes its site's rules from slurm/site.sh: the node-local scratch (Expanse /scratch/$USER/job_<id>, symmetry
# /local1/$USER/job_<id>, $SLURM_TMPDIR first), the toolchain check_build.py expects (Expanse g++ 13.3.0 with the Spack
# GMP by RPATH; symmetry g++ 11.4.0 with the system GMP 6.2.1 in /usr/lib/x86_64-linux-gnu, no RPATH; Boost 1.77 on
# both), the SITE_REFUSED text; and the c8-stage3 baseline B0 from tools/baseline.py (the site's record; a site without
# one fails the jobs that need it: an Expanse binary is never a symmetry baseline, HD9).
# class_b.py also takes the d=3 payload in val2 when C8_D3_PAYLOAD (the published tree) and C8_D3_PIN (the sha256 of its
# MANIFEST_d3.json, the A.5 gate record's pin) are set in the submitting shell.
# Every job builds in a private copy of the export (node-local $C8_SCRATCH/pkg, or $C8_ROOT/work/<job>_<id> for the L8
# jobs), so concurrent jobs on one export never share bin/; c7ref and the C8 workers of a job are built and compared on
# the same node (HD9). Evidence: $C8_ROOT/evidence/<sha12>/<job>/ (environment, make log, build records, one JSON per
# test, summary.json). Each step's status is recorded and the job continues; it exits 1 if any step failed.
# Submission (login node, after `source ~/c8d3/env.sh`, with C8_PACKAGE=$C8_ROOT/pkg/<sha12> exported):
#   C8_JOB=val2 python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role val2 --dir $C8_ROOT/evidence/<sha12>/val2 -- \
#     -A yun124 -p shared --nodes=1 --ntasks=1 -c 64 --mem=120G -t 01:00:00 --no-requeue \
#     -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/native_job.sh
# On symmetry (no -A; one whole AMD node, --exclude=cn112 and the CPU pin's nodes added by slurm_submit.py; amddebugq at
# most 1 h, amdq 24 h):
#   C8_JOB=val1 python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role val1 --dir $C8_ROOT/evidence/<sha12>/val1 -- \
#     -p amddebugq --nodes=1 --ntasks=1 -c 64 --mem=240G -t 00:59:00 -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/native_job.sh
# No #SBATCH lines: the options above are the job's (slurm_submit.py names it and sets the comment, D.11).
set -eo pipefail
if [ -z "${C8_ENV_SETUP:-}" ] || [ ! -r "$C8_ENV_SETUP" ]; then
  echo "native_job: C8_ENV_SETUP is not set or not readable (source ~/c8d3/env.sh before submitting)" >&2; exit 64
fi
source "$C8_ENV_SETUP"
set -u
: "${C8_PACKAGE:?C8_PACKAGE (the git archive export of the commit under test)}" "${C8_ROOT:?}" "${C8_STORE:?}" "${C8_JOB:?C8_JOB=val1|inspect|val2|val3|val3a|val4|run1|repair3a|repair3b|smoke3b|sweep1|argmax|argmaxre|profbuild|prof1|prof2|prof3|optsmoke|opt|basestore|sweep2|bld}"
: "${SLURM_JOB_ID:?native_job runs inside a Slurm job}"
case "$C8_JOB" in val1|inspect|val2|val3|val3a|val4|run1|repair3a|repair3b|smoke3b|sweep1|argmax|argmaxre|profbuild|prof1|prof2|prof3|optsmoke|opt|basestore|sweep2|bld) ;; *) echo "native_job: C8_JOB must be val1, inspect, val2, val3, val3a, val4, run1, repair3a, repair3b, smoke3b, sweep1, argmax, argmaxre, profbuild, prof1, prof2, prof3, optsmoke, opt, basestore, sweep2 or bld" >&2; exit 64 ;; esac
if [ "$C8_JOB" = argmaxre ]; then
  [ -f "${C8_ARGMAX_RUN:-}/manifest.json" ] && [[ "${C8_ARGMAX_SEED:-}" =~ ^[0-9]+$ ]] || { echo "native_job: argmaxre needs C8_ARGMAX_RUN (a merged argmax campaign) and its C8_ARGMAX_SEED" >&2; exit 64; }
fi
if [ "$C8_JOB" = sweep1 ]; then
  case "${C8_SWEEP_RUN:-}" in "$C8_ROOT"/runs/?*) ;; *) echo "native_job: sweep1 needs C8_SWEEP_RUN=\$C8_ROOT/runs/<name> (a new campaign directory)" >&2; exit 64 ;; esac
  [ ! -e "$C8_SWEEP_RUN" ] || { echo "native_job: $C8_SWEEP_RUN exists (use a new campaign directory)" >&2; exit 64; }
  [[ "${C8_SWEEP_SEED:-}" =~ ^[0-9]+$ ]] || { echo "native_job: sweep1 needs C8_SWEEP_SEED (a fresh random seed)" >&2; exit 64; }
fi
if [ "$C8_JOB" = opt ]; then
  [[ "${C8_OPT_STEP:-}" =~ ^(R5a|R5b|4|6|8|7|final)$ ]] || { echo "native_job: opt needs C8_OPT_STEP (R5a, R5b, 4, 6, 8, 7 or final)" >&2; exit 64; }
  if [ -n "${C8_OPT_PREV:-}" ]; then
    [[ "$C8_OPT_PREV" =~ ^[0-9a-f]{12}$ ]] && [ -f "$C8_STORE/opt/$C8_OPT_PREV/SHA256SUMS" ] || { echo "native_job: C8_OPT_PREV must be the sha12 of a stored candidate (\$C8_STORE/opt/<sha12>/SHA256SUMS)" >&2; exit 64; }
  fi
  if [ -n "${C8_OPT_PREV_PKG:-}" ]; then
    [ -z "${C8_OPT_PREV:-}" ] || { echo "native_job: give C8_OPT_PREV or C8_OPT_PREV_PKG, not both" >&2; exit 64; }
    [[ "$C8_OPT_PREV_PKG" =~ ^[0-9a-f]{12}$ ]] && [ -f "$C8_ROOT/pkg/$C8_OPT_PREV_PKG/Makefile" ] || { echo "native_job: C8_OPT_PREV_PKG must be the sha12 of an export in \$C8_ROOT/pkg/" >&2; exit 64; }
  fi
  [[ "${C8_OPT_GATES:-validate_full}" =~ ^(validate_full|l8self|first_error|same_binary|thread_identity|inspect_check|quaddiff|forced_tiers)(,(validate_full|l8self|first_error|same_binary|thread_identity|inspect_check|quaddiff|forced_tiers))*$ ]] \
    || { echo "native_job: C8_OPT_GATES is a comma list of validate_full, l8self, first_error, same_binary, thread_identity, inspect_check, quaddiff, forced_tiers" >&2; exit 64; }
  [[ "${C8_OPT_VARIANT_OPTFLAGS:-}" =~ ^[-=_.,+a-zA-Z0-9\ ]*$ ]] || { echo "native_job: C8_OPT_VARIANT_OPTFLAGS holds compiler flags only" >&2; exit 64; }
  [[ "${C8_OPT_SHAPES:-}" =~ ^((B0|PREV|CAND)=[0-9]+x[0-9]+(,(B0|PREV|CAND)=[0-9]+x[0-9]+)*)?$ ]] || { echo "native_job: C8_OPT_SHAPES is NAME=NxT,... with NAME in B0, PREV, CAND" >&2; exit 64; }
  case ",${C8_OPT_GATES:-}," in *,same_binary,*) [ -n "${C8_OPT_PREV:-}${C8_OPT_PREV_PKG:-}" ] || { echo "native_job: the same_binary gate needs C8_OPT_PREV or C8_OPT_PREV_PKG" >&2; exit 64; } ;; esac
fi
if [ "$C8_JOB" = basestore ]; then
  [[ "${C8_BASE_PKG:-}" =~ ^[0-9a-f]{12}$ ]] && [ -f "$C8_ROOT/pkg/$C8_BASE_PKG/Makefile" ] || { echo "native_job: basestore needs C8_BASE_PKG, the sha12 of the c8-stage3 commit's export in \$C8_ROOT/pkg/" >&2; exit 64; }
  [ ! -e "$C8_STORE/baseline/$C8_BASE_PKG" ] || { echo "native_job: $C8_STORE/baseline/$C8_BASE_PKG exists (never overwritten)" >&2; exit 64; }
fi
if [ "$C8_JOB" = argmax ]; then
  case "${C8_ARGMAX_RUN:-}" in "$C8_ROOT"/runs/?*) ;; *) echo "native_job: argmax needs C8_ARGMAX_RUN=\$C8_ROOT/runs/<name> (a new campaign directory)" >&2; exit 64 ;; esac
  [ ! -e "$C8_ARGMAX_RUN" ] || { echo "native_job: $C8_ARGMAX_RUN exists (use a new campaign directory)" >&2; exit 64; }
  [[ "${C8_ARGMAX_SEED:-}" =~ ^[0-9]+$ ]] || { echo "native_job: argmax needs C8_ARGMAX_SEED (a fresh random seed)" >&2; exit 64; }
  [ -f "${C8_SWEEP_RUN:-}/manifest.json" ] && [ -d "${C8_SWEEP_PKG:-}/tools" ] || { echo "native_job: argmax needs C8_SWEEP_RUN (the merged sweep campaign) and C8_SWEEP_PKG (its work copy)" >&2; exit 64; }
  [ -f "$C8_STORE/baseline/${C8_BASELINE_SHA12:-}/SHA256SUMS" ] || { echo "native_job: argmax needs C8_BASELINE_SHA12 (the sweep commit; \$C8_STORE/baseline/<sha12>/SHA256SUMS)" >&2; exit 64; }
fi
if [ "$C8_JOB" = sweep2 ]; then   # J-SWEEP-2 (D.14): 64 before anything is written
  case "${C8_SWEEP_RUN:-}" in */..|*/../*|*/./*) echo "native_job: sweep2: C8_SWEEP_RUN=$C8_SWEEP_RUN has a . or .. component" >&2; exit 64 ;; "$C8_ROOT"/runs/?*) ;; *) echo "native_job: sweep2 needs C8_SWEEP_RUN=\$C8_ROOT/runs/<name> (a new campaign directory)" >&2; exit 64 ;; esac
  [ ! -e "$C8_SWEEP_RUN" ] || { echo "native_job: $C8_SWEEP_RUN exists (use a new campaign directory)" >&2; exit 64; }
  [[ "${C8_SWEEP_SEED:-}" =~ ^[0-9]+$ ]] || { echo "native_job: sweep2 needs C8_SWEEP_SEED (a fresh random seed)" >&2; exit 64; }
  if [ -n "${C8_SWEEP_PREV:-}" ]; then [[ "$C8_SWEEP_PREV" =~ ^cost_models/[A-Za-z0-9_.-]+\.json$ ]] || { echo "native_job: sweep2: C8_SWEEP_PREV must be cost_models/<file>.json of the export (got $C8_SWEEP_PREV)" >&2; exit 64; }; fi
  if [ -n "${C8_SWEEP_LANES:-}" ]; then [[ "$C8_SWEEP_LANES" =~ ^(numa(:[1-9][0-9]*)?|socket|[1-9][0-9]*)$ ]] || { echo "native_job: sweep2: C8_SWEEP_LANES must be numa, numa:<k>, socket or a lane count (tools/lanes.py; got $C8_SWEEP_LANES)" >&2; exit 64; }; fi
  [ -f "${C8_SEEDS:-}" ] || { echo "native_job: sweep2 needs C8_SEEDS, the site's forbidden-seed log (env.sh; HD6)" >&2; exit 64; }
fi
if [ "$C8_JOB" = bld ]; then   # J-BLD: 64 before anything is written
  [[ "${C8_BLD_BASE_PKG:-}" =~ ^[0-9a-f]{12}$ ]] && [ -f "$C8_ROOT/pkg/$C8_BLD_BASE_PKG/Makefile" ] || { echo "native_job: bld needs C8_BLD_BASE_PKG, the sha12 of the code commit's export in \$C8_ROOT/pkg/ (the data-only export's base)" >&2; exit 64; }
  # the base is another export than the one under test (a tree compared with itself would pass anything), and its own
  # tools/cost_identity.py runs the comparison (a data export's changed copy of that tool cannot approve itself)
  if [ "$C8_BLD_BASE_PKG" = "$(basename "$C8_PACKAGE")" ] || [ "$C8_ROOT/pkg/$C8_BLD_BASE_PKG" -ef "$C8_PACKAGE" ]; then
    echo "native_job: bld: C8_BLD_BASE_PKG=$C8_BLD_BASE_PKG is the data export itself ($C8_PACKAGE): give the code commit's export, the base of the data-only commit" >&2; exit 64
  fi
  grep -q '^def data_only' "$C8_ROOT/pkg/$C8_BLD_BASE_PKG/tools/cost_identity.py" 2>/dev/null || { echo "native_job: bld: the base export's tools/cost_identity.py has no data-only check (the base must be the Stage-5 code commit or a later one)" >&2; exit 64; }
  if [ -n "${C8_SWEEP_RUN:-}${C8_SWEEP_PKG:-}" ]; then
    [ -f "${C8_SWEEP_RUN:-}/manifest.json" ] && [ -d "${C8_SWEEP_PKG:-}/tools" ] || { echo "native_job: bld takes C8_SWEEP_RUN (the merged sweep campaign) and C8_SWEEP_PKG (its kept work copy) together, or neither" >&2; exit 64; }
  fi
fi
D3ARGS=()
if [ -n "${C8_D3_PAYLOAD:-}" ] || [ -n "${C8_D3_PIN:-}" ]; then
  [ -d "${C8_D3_PAYLOAD:-}" ] && [ ${#C8_D3_PIN} -eq 64 ] || { echo "native_job: C8_D3_PAYLOAD must be a payload tree and C8_D3_PIN its 64-hex pin" >&2; exit 64; }
  D3ARGS=(--d3-payload "$C8_D3_PAYLOAD" --d3-pin "$C8_D3_PIN")
fi
# The site's rules (slurm/site.sh): the CPU pin (68 on another CPU; HD11), its toolchain expectations (64 off expanse and
# symmetry), the Stage-5 checks that need the site's model name (64), then the node-local scratch.
source "$C8_PACKAGE/slurm/site.sh"
c8_cpu_guard
c8_toolchain_args
if [ "$C8_JOB" = sweep2 ]; then   # PREV (D.14): C8_SWEEP_PREV, else the site's model of this export, else the package's first measured model
  if [ -n "${C8_SWEEP_PREV:-}" ]; then PREV="$C8_SWEEP_PREV"
  elif [ -f "$C8_PACKAGE/cost_models/$C8_SITE_MODEL" ]; then PREV="cost_models/$C8_SITE_MODEL"
  else PREV=cost_models/gmp_expanse_epyc7742_c8.json; fi
  [ -f "$C8_PACKAGE/$PREV" ] || { echo "native_job: sweep2: the previous model $PREV is not in the export $C8_PACKAGE" >&2; exit 64; }
  case "$C8_SITE" in expanse) SWEEP_LANES="${C8_SWEEP_LANES:-16}" ;; *) SWEEP_LANES="${C8_SWEEP_LANES:-numa}" ;; esac   # Expanse: P4's 16 x 8; symmetry: 8 x 8 (D8)
fi
if [ "$C8_JOB" = bld ]; then
  [ -f "$C8_PACKAGE/cost_models/$C8_SITE_MODEL" ] || { echo "native_job: bld: $C8_PACKAGE/cost_models/$C8_SITE_MODEL is missing (the data-only commit carries the site's measured model)" >&2; exit 64; }
  [ ! -e "$C8_PACKAGE/bin/c8d3_gmp" ] || { echo "native_job: bld: $C8_PACKAGE/bin/c8d3_gmp exists: J-BLD builds an export once; after a failed J-BLD its bin/ was moved aside" >&2; exit 64; }
fi
c8_set_scratch
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}" PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
SHA12=$(basename "$C8_PACKAGE")
case "$SHA12" in *[!0-9a-f]*|'') echo "native_job: C8_PACKAGE must be \$C8_ROOT/pkg/<sha12> (got $C8_PACKAGE)" >&2; exit 64 ;; esac
[ ${#SHA12} -eq 12 ] || { echo "native_job: C8_PACKAGE must end in a 12-hex commit (got $SHA12)" >&2; exit 64; }
EV="$C8_ROOT/evidence/$SHA12/$C8_JOB"
if [ "$C8_JOB" = opt ]; then EV="$C8_ROOT/evidence/$SHA12/opt_$C8_OPT_STEP"; fi   # one commit may carry several opt jobs (7, final)
case "$C8_JOB" in sweep2|bld) EV="$C8_ROOT/evidence/$SHA12/${C8_JOB}_$SLURM_JOB_ID" ;; esac   # a repeat on the same export never overwrites (PLAN risk 32)
mkdir -p "$EV" "$C8_SCRATCH"
export TMPDIR="$C8_SCRATCH/tmp"
mkdir -p "$TMPDIR"
W="$C8_SCRATCH/pkg"
# Stage 3b: the L8 jobs (val1 too, since Stage 2b pinned the packs) work in a copy under $C8_ROOT (Lustre on Expanse,
# BeeGFS on symmetry), so the store's L8 packs can be hard-linked in (same filesystem).
case "$C8_JOB" in val1|val2|val3|val4|smoke3b|sweep1|sweep2|argmax|profbuild|prof1|prof2|prof3|optsmoke|opt) W="$C8_ROOT/work/${C8_JOB}_$SLURM_JOB_ID"; L8WORK=1 ;; *) L8WORK=0 ;; esac
if [ "$C8_JOB" = bld ]; then W="$C8_PACKAGE"; fi   # J-BLD builds the export itself, in place (no copy, no work directory)
[ "$L8WORK" = 0 ] || [ ! -e "$W" ] || { echo "native_job: $W exists" >&2; exit 64; }
stamp() { echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*"; }
STATUS=()
step() {   # step NAME CMD...: runs CMD in the package copy, logs to $EV/NAME.log, records PASS/FAIL and the seconds
  local name=$1; shift; local t0=$(date +%s) rc=0
  stamp "$name: $*"
  ( cd "$W" && "$@" ) > "$EV/$name.log" 2>&1 || rc=$?
  local dt=$(( $(date +%s) - t0 ))
  if [ $rc -eq 0 ]; then STATUS+=("{\"step\":\"$name\",\"status\":\"PASS\",\"seconds\":$dt}"); stamp "$name PASS ($dt s)";
  else STATUS+=("{\"step\":\"$name\",\"status\":\"FAIL\",\"rc\":$rc,\"seconds\":$dt}"); stamp "$name FAIL rc=$rc ($dt s)"; tail -n 25 "$EV/$name.log"; fi
}
# The Mac fakes of the admission engine (C8_SITE=fake: the fake Slurm of tests/c8pkg.py and tests/fake_slurm/, the
# ledger and lock tests) cannot run on a cluster node: A-ORC-17's site detection (Expanse: a /expanse/lustre mount or
# SLURM_CLUSTER_NAME=expanse; symmetry: the BeeGFS mount at /mnt/beegfs) refuses C8_SITE=fake there by design (64),
# whatever the environment says. A val1 step that fails with exactly that refusal ("this host is <site> but C8_SITE is
# 'fake'", tools/ledger.py) is recorded SITE_REFUSED (expected; its evidence is the Mac run), not FAIL.
SITE_REFUSAL="$(c8_site_refusal)"
pstep() {   # pstep NAME CMD...: step for a background stream; its status goes to $EV/status.d/NAME.json
  local name=$1; shift; local t0=$(date +%s) rc=0
  ( cd "$W" && "$@" ) > "$EV/$name.log" 2>&1 || rc=$?
  local dt=$(( $(date +%s) - t0 ))
  if [ $rc -eq 0 ]; then echo "{\"step\":\"$name\",\"status\":\"PASS\",\"seconds\":$dt}" > "$EV/status.d/$name.json"; stamp "$name PASS ($dt s)";
  elif grep -qF "$SITE_REFUSAL" "$EV/$name.log"; then
    echo "{\"step\":\"$name\",\"status\":\"SITE_REFUSED\",\"rc\":$rc,\"seconds\":$dt}" > "$EV/status.d/$name.json"; stamp "$name SITE_REFUSED rc=$rc ($dt s)";
  else echo "{\"step\":\"$name\",\"status\":\"FAIL\",\"rc\":$rc,\"seconds\":$dt}" > "$EV/status.d/$name.json"; stamp "$name FAIL rc=$rc ($dt s)"; tail -n 8 "$EV/$name.log"; fi
}
stamp "native_job $C8_JOB on $(hostname), job $SLURM_JOB_ID, package $SHA12, $OMP_NUM_THREADS threads, scratch $C8_SCRATCH"
{
  echo "host: $(hostname)"; echo "job: $SLURM_JOB_ID"; echo "package: $C8_PACKAGE"; echo "machine: $(uname -m)"
  echo "site: ${C8_SITE:-}"; echo "scratch: $C8_SCRATCH"; echo "tmpdir: $TMPDIR"; echo "threads: $OMP_NUM_THREADS"
  lscpu | grep -E 'Model name|^CPU\(s\)|NUMA node'
  echo "g++: $(g++ --version | head -n 1)"; echo "python: $(python3 --version 2>&1)"; echo "LDFLAGS: ${LDFLAGS:-}"
  echo "C8_GMP: ${C8_GMP:-}"; echo "C8_BOOST: ${C8_BOOST:-}"; echo "CPATH: ${CPATH:-}"; echo "toolchain expectations: ${C8_TOOLCHAIN_ARGS[*]}"
  echo "cpu_expect: $C8_CPU_EXPECT"; echo "site_model: $C8_SITE_MODEL"; echo "cpu_source: ${C8_CPU_SOURCE:-}"; echo "cpu_read: ${C8_CPU_READ:-}"
  if [ "$C8_JOB" = sweep2 ]; then echo "sweep_prev: $PREV"; echo "sweep_lanes: $SWEEP_LANES"; fi
} > "$EV/environment.txt"
cat "$EV/environment.txt"
copy_export() {   # copy_export SRC DST: every copy of an export (W of every mode but bld; opt's variant and PREV copies, basestore's BASE copy)
  local s=$1 d=$2 built=0 x
  mkdir -p "$d" || return
  for x in "$s/bin" "$s"/bin.bld_failed_* "$s/inputs/packs/free_L8.pack" "$s/inputs/packs/power_L8.pack"; do if [ -e "$x" ] || [ -L "$x" ]; then built=1; fi; done
  if [ "$built" = 0 ]; then cp -a "$s/." "$d/"; return; fi   # a pristine export (git archive): exactly as before
  stamp "built export: bin/ and the L8 pack links are not copied (rebuilt and re-linked in the copy)"
  tar -C "$s" --exclude=./bin --exclude='./bin.bld_failed_*' --exclude=./inputs/packs/free_L8.pack --exclude=./inputs/packs/power_L8.pack -cf - . | tar -C "$d" -xpf -
}
if [ "$C8_JOB" = bld ]; then stamp "building the export in place: $W"
else
  stamp "copying the export to $W"
  mkdir -p "$W"
  copy_export "$C8_PACKAGE" "$W"
fi
MK="make -j $OMP_NUM_THREADS CXX=g++"
# This site's c8-stage3 baseline (tools/baseline.py sha: reference/baseline_c8_stage3.json on Expanse, 24adff54...;
# reference/baseline_c8_stage3_symmetry.json on symmetry, 3a9a556b..., J-BASE-sym 570275): B0 of the profile and speed jobs.
BASE_SHA=$( (cd "$W" && python3 -B tools/baseline.py sha c8d3_gmp) 2>"$EV/baseline_record.log" || true)
[[ "$BASE_SHA" =~ ^[0-9a-f]{64}$ ]] || BASE_SHA=""
B8="${BASE_SHA:0:8}"
if [ "$L8WORK" = 1 ]; then
  step link_l8 make link-l8 PYTHON=python3 STORE="$C8_STORE"
  ( cd "$W" && ls -li inputs/packs/ ) > "$EV/packs_listing.txt" 2>&1 || true
fi
BUILDINFO_ARGS=("${C8_TOOLCHAIN_ARGS[@]}")   # the site's toolchain (slurm/site.sh)
case "$C8_JOB" in
val1)
  step make_native $MK all bin/c8d3_decimal c7ref inspect test-builds
  step check_build python3 -B tests/check_build.py "${BUILDINFO_ARGS[@]}" --output "$EV/check_build.json" bin/c8d3_gmp.buildinfo.json \
       bin/c8d3_decimal.buildinfo.json bin/ref/c7d3_gmp.buildinfo.json bin/ref/c7d3_decimal.buildinfo.json
  mkdir -p "$EV/status.d"; rm -f "$EV"/status.d/*.json
  stamp "make test-python's tests in four streams"
  ( for t in seeds_and_nets seed_logs_two_sites allocation selection_files chunking_synthetic roles first_sweep_bootstrap blocks_plan_level \
             atomic_and_guards per_index_and_spies merge_and_safety zero_task_groups lanes lanes_submission done_markers \
             recovery_merge arrays_and_recovery vendor_pin seed_reservations reserve_required plan_staging lane_sigterm; do pstep "uo_$t" python3 -B tests/unit_orchestration.py --only "$t"; done ) &
  ( pstep integration_3a python3 -B tests/integration_3a.py
    pstep native_static python3 -B tests/native_static.py; pstep check_build_selftest python3 -B tests/check_build.py --selftest
    pstep ast_scan python3 -B tests/ast_scan.py ) &
  ( pstep test_pipeline python3 -B tests/test_pipeline.py; pstep cost_refresh_test python3 -B tests/cost_refresh_test.py
    pstep prefix_check python3 -B tests/prefix_check.py; pstep test_pilot_report python3 -B tests/test_pilot_report.py
    pstep design_fallback_test python3 -B tests/design_fallback_test.py; pstep members_test python3 -B tests/members_test.py
    pstep verify_result_tamper python3 -B tests/verify_result_tamper.py; pstep compat_run1 python3 -B tests/compat_run1.py --output "$EV/compat_run1.json"
    pstep assembly_checks python3 -B tests/assembly_checks.py --exact; pstep blocks_test python3 -B tests/blocks_test.py
    pstep archived_replay python3 -B tests/archived_replay.py; pstep test_delivery_verifier python3 -B tests/test_delivery_verifier.py
    pstep thru_report_test python3 -B tests/thru_report_test.py; pstep drill_select_test python3 -B tests/drill_select_test.py ) &
  ( pstep merge_scale python3 -B tests/merge_scale.py --output "$EV/merge_scale.json"; pstep test_submit python3 -B tests/test_submit.py
    pstep test_ledger python3 -B tests/test_ledger.py ) &
  ( pstep check_inputs python3 -B tests/check_inputs.py --output "$EV/check_inputs.json"
    pstep check_vendored python3 -B tests/check_vendored.py --no-review-record --output "$EV/check_vendored.json"
    pstep workflow_fake python3 -B tests/workflow.py --fake --output "$EV/workflow_fake.json"
    pstep staging_fake python3 -B tests/staging.py --fake --output "$EV/staging_fake.json"
    pstep gen3_test python3 -B gen3/test_gen3.py ) &
  wait
  for f in "$EV"/status.d/*.json; do STATUS+=("$(cat "$f")"); done
  step uo_list_complete python3 -B -c "import sys;sys.path.insert(0,'tests');import unit_orchestration as u;w='seeds_and_nets seed_logs_two_sites allocation selection_files chunking_synthetic roles first_sweep_bootstrap blocks_plan_level atomic_and_guards per_index_and_spies merge_and_safety zero_task_groups lanes lanes_submission done_markers recovery_merge arrays_and_recovery vendor_pin seed_reservations reserve_required plan_staging lane_sigterm'.split();sys.exit(0 if u.TESTS==w else 1)"
  step validate_subset python3 -B tests/validate.py --output "$EV/validate_subset.json"
  step class_b python3 -B tests/class_b.py --output "$EV/class_b.json"
  step workflow python3 -B tests/workflow.py --output "$EV/workflow.json"
  step staging python3 -B tests/staging.py --output "$EV/staging.json"
  step vendored_isolated env -u PYTHONPYCACHEPREFIX PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -B tests/vendored_isolated.py --in-place \
       --asm3-record "$EV/compat_run1.json" --output "$EV/vendored_isolated.json"
  ;;
inspect)
  step make_inspect $MK bin/c8d3_inspect bin/gen3/size_probe
  step inputs_inspect make inputs-inspect PYTHON=python3
  mkdir -p "$EV/generated/inspect" "$EV/generated/inputs"
  cp "$W/inspect/inspect.json" "$EV/generated/inspect/" 2>/dev/null || true
  cp "$W/inputs/inventory.json" "$W/inputs/manifest.json" "$EV/generated/inputs/" 2>/dev/null || true
  step inspect_check_static python3 -B tests/inspect_check.py --no-worker --output "$EV/inspect_check_static.json"
  ;;
val2)
  step make_native $MK bin/c8d3_gmp bin/c8d3_decimal c7ref inspect test-builds
  step check_build python3 -B tests/check_build.py "${BUILDINFO_ARGS[@]}" --output "$EV/check_build.json" bin/c8d3_gmp.buildinfo.json \
       bin/c8d3_decimal.buildinfo.json bin/ref/c7d3_gmp.buildinfo.json bin/ref/c7d3_decimal.buildinfo.json
  step validate_full python3 -B tests/validate.py --full --output "$EV/validate_full.json"
  step class_b python3 -B tests/class_b.py ${D3ARGS[@]+"${D3ARGS[@]}"} --output "$EV/class_b.json"
  if python3 -c "import json,sys;sys.exit(0 if json.load(open('$W/inputs/inventory.json'))['inspect_complete'] else 1)"; then
    step inspect_check python3 -B tests/inspect_check.py --output "$EV/inspect_check.json"
  else stamp "inspect_check skipped: the inventory has no inspect fields at this commit"; fi
  step check_points python3 -B tests/check_points.py --output "$EV/check_points.json"
  step forced_tiers_smoke python3 -B tests/forced_tiers.py --smoke --output "$EV/forced_tiers_smoke.json"
  if [ "$L8WORK" = 1 ] && [ -f "$W/inputs/packs/free_L8.pack" ]; then
    step check_inputs python3 -B tests/check_inputs.py --output "$EV/check_inputs.json"
    step workflow python3 -B tests/workflow.py --output "$EV/workflow.json"
    step staging python3 -B tests/staging.py --output "$EV/staging.json"
    step compat_run1 python3 -B tests/compat_run1.py --output "$EV/compat_run1.json"
  fi
  ;;
val3)
  step make_native $MK bin/c8d3_gmp bin/c8d3_decimal c7ref inspect
  mkdir -p "$EV/status.d"; rm -f "$EV"/status.d/*.json
  stamp "J-VAL-3 in three streams"
  # forced_tiers' 450-digit reference costs about 1.4 s per L8 point and thread (smoke3b 54676968): it takes every core
  # (the other streams are short and only slow it while they run)
  ( pstep forced_tiers python3 -B tests/forced_tiers.py --threads "${C8_FT_THREADS:-128}" --max-seconds "${C8_FT_MAX_SECONDS:-1200}" --output "$EV/forced_tiers.json" ) &
  ( pstep thread_identity python3 -B tests/thread_identity.py --threads 32 --output "$EV/thread_identity.json"
    pstep validate_bk8_l2 python3 -B tests/validate.py --parts identity --bk8 --l2-control --threads 32 --output "$EV/validate_bk8_l2.json" ) &
  ( pstep merge_scale python3 -B tests/merge_scale.py --rows 1000000 --jobs 16 --run-jobs 16 --output "$EV/merge_scale.json"
    pstep assembly_checks python3 -B tests/assembly_checks.py --exact
    pstep compat_run1 python3 -B tests/compat_run1.py --output "$EV/compat_run1.json"
    pstep prefix_check_real python3 -B tests/prefix_check.py --real --threads 16 --output "$EV/prefix_check_real.json" ) &
  wait
  for f in "$EV"/status.d/*.json; do STATUS+=("$(cat "$f")"); done
  ;;
val4)
  step make_sanitize $MK sanitize
  MAXL=7; [ "$L8WORK" = 1 ] && [ -f "$W/inputs/packs/free_L8.pack" ] && MAXL=8
  step sanitize python3 -B tests/sanitize.py --selftest --parsers --runs --max-loop "$MAXL" --output "$EV/sanitize.json"
  ;;
smoke3b)
  step make_native $MK bin/c8d3_gmp bin/c8d3_decimal inspect test-builds
  step forced_tiers_l8 python3 -B tests/forced_tiers.py --loops 8 --l8-graphs 24 --l8-points 8 --min-quad 400 --min-mp 40 --max-points 64 --max-seconds 240 \
       --output "$EV/forced_tiers_l8_small.json"
  step thread_identity_small python3 -B tests/thread_identity.py --threads-list 1,8 --splits 2,4 --backends gmp --parts blocks,chunks --output "$EV/thread_identity_small.json"
  step class_b_f python3 -B tests/class_b.py --parts f --output "$EV/class_b_f.json"
  step check_points python3 -B tests/check_points.py --output "$EV/check_points.json"
  step prefix_check_real python3 -B tests/prefix_check.py --real --output "$EV/prefix_check_real.json"
  step sweep_choose python3 -B tools/sweep.py "$C8_ROOT/runs/never-created" --seed 1 --choose-only
  ;;
argmaxre)
  step make_native $MK bin/c8d3_inspect
  step argmax_reinspect python3 -B tests/argmax_run.py "$C8_ARGMAX_RUN" --reinspect --cost-model "cost_models/$C8_SITE_MODEL" --seed "$C8_ARGMAX_SEED" \
       --output "$EV/argmax_L7"
  ;;
sweep1)
  MODEL="$EV/$C8_SITE_MODEL"
  step make_native $MK bin/c8d3_gmp bin/c8d3_decimal
  step check_build python3 -B tests/check_build.py "${BUILDINFO_ARGS[@]}" --output "$EV/check_build.json" bin/c8d3_gmp.buildinfo.json bin/c8d3_decimal.buildinfo.json
  step sweep python3 -B tools/sweep.py "$C8_SWEEP_RUN" --seed "$C8_SWEEP_SEED" --output "$MODEL" --forbid-seeds-from "$C8_SEEDS" --reserve-seed "$C8_SEEDS" --scratch "$C8_SCRATCH"
  if [ -f "$C8_SWEEP_RUN/manifest.json" ]; then step seeds_add python3 -B tools/seeds.py add "$C8_SWEEP_RUN"; fi
  if [ -f "$MODEL" ]; then
    step assemble python3 -B tools/assemble.py "$C8_SWEEP_RUN" --bootstrap 1024
    cp "$C8_SWEEP_RUN"/C8_test_result.json "$EV/" 2>/dev/null || true
    step cost_identity python3 -B tools/cost_identity.py check --model "$MODEL" --exe bin/c8d3_gmp
    step cost_summary python3 -B tools/cost_summary.py "$C8_SWEEP_RUN" "$MODEL" --symmetry-model cost_models/gmp_symmetry_epyc7532.json --output "$EV/cost_summary.json"
    BASE="$C8_STORE/baseline/$SHA12"
    step baseline bash -c 'set -e; b="$0"; [ ! -e "$b" ] || { echo "$b exists (never overwritten)"; exit 1; }; mkdir -p "$b.tmp"
      for f in c8d3_gmp c8d3_gmp.buildinfo.json c8d3_decimal c8d3_decimal.buildinfo.json; do cp -p "bin/$f" "$b.tmp/$f"; done
      ( cd "$b.tmp" && sha256sum c8d3_gmp c8d3_gmp.buildinfo.json c8d3_decimal c8d3_decimal.buildinfo.json > SHA256SUMS ); chmod a-w "$b.tmp"/*; mv "$b.tmp" "$b"; cat "$b/SHA256SUMS"' "$BASE"
    cp "$BASE/SHA256SUMS" "$EV/baseline_SHA256SUMS" 2>/dev/null || true
  fi
  ( cd "$W" && python3 -B tools/production.py status "$C8_SWEEP_RUN" ) > "$EV/sweep_status.txt" 2>&1 || true
  cp "$C8_SWEEP_RUN"/manifest.json "$EV/sweep_manifest.json" 2>/dev/null || true
  for g in "$C8_SWEEP_RUN"/groups/*/; do n=$(basename "$g"); mkdir -p "$EV/groups/$n"; cp "$g"merged.json "$g"graph_costs.csv "$g"graph_promotions.csv "$EV/groups/$n/" 2>/dev/null || true; done
  cp "$C8_SEEDS" "$EV/forbidden_seeds.json"
  ;;
argmax)
  step make_native $MK bin/c8d3_gmp inspect
  step check_build python3 -B tests/check_build.py "${BUILDINFO_ARGS[@]}" --output "$EV/check_build.json" bin/c8d3_gmp.buildinfo.json
  step cost_identity_exe python3 -B tools/cost_identity.py check --model "cost_models/$C8_SITE_MODEL" --exe bin/c8d3_gmp
  step baseline_identity bash -c 'b=$(sha256sum bin/c8d3_gmp | cut -d" " -f1); echo "rebuilt bin/c8d3_gmp $b"; cat "$0/SHA256SUMS"; grep -q "^$b  c8d3_gmp\$" "$0/SHA256SUMS"' "$C8_STORE/baseline/$C8_BASELINE_SHA12"
  if [ -n "$BASE_SHA" ]; then
    step baseline_install make baseline PYTHON=python3 STORE="$C8_STORE"
    step baseline_equal bash -c 'cmp bin/c8d3_gmp bin/baseline/c8d3_gmp && echo "bin/c8d3_gmp (rebuilt) = bin/baseline/c8d3_gmp"'
  fi
  step argmax python3 -B tests/argmax_run.py "$C8_ARGMAX_RUN" --cost-model "cost_models/$C8_SITE_MODEL" --seed "$C8_ARGMAX_SEED" \
       --output "$EV/argmax_L7" --threads "$OMP_NUM_THREADS" --scratch "$C8_SCRATCH"
  step sweep_accounting bash -c 'cd "$0" && python3 -B tools/accounting.py "$1" --json > "$2"' "$C8_SWEEP_PKG" "$C8_SWEEP_RUN" "$EV/sweep_accounting.json"
  step cost_summary python3 -B tools/cost_summary.py "$C8_SWEEP_RUN" "cost_models/$C8_SITE_MODEL" --symmetry-model cost_models/gmp_symmetry_epyc7532.json \
       --accounting "$EV/sweep_accounting.json" --output "$EV/cost_summary.json"
  cp "$C8_SEEDS" "$EV/forbidden_seeds.json"
  ;;
sweep2)
  # J-SWEEP-2 (D.14): the refresh of this binary from PREV; the fresh model, refresh_report.json and the evidence the
  # data-only commit takes (cost_models/$C8_SITE_MODEL byte-identical, $EV under benchmarks/<site dir>/stage5_<sha12>/)
  MODEL="$EV/$C8_SITE_MODEL"
  step make_native $MK bin/c8d3_gmp bin/c8d3_decimal
  step check_build python3 -B tests/check_build.py "${BUILDINFO_ARGS[@]}" --output "$EV/check_build.json" bin/c8d3_gmp.buildinfo.json bin/c8d3_decimal.buildinfo.json
  if printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then stamp "sweep2: build or check_build failed: no sweep"
  else
    step basis python3 -B tools/sweep.py "$C8_SWEEP_RUN" --seed "$C8_SWEEP_SEED" --refresh "$PREV" --choose-only
    step sweep env C8_LANES="$SWEEP_LANES" python3 -B tools/sweep.py "$C8_SWEEP_RUN" --seed "$C8_SWEEP_SEED" --refresh "$PREV" --output "$MODEL" \
         --report "$EV/refresh_report.json" --forbid-seeds-from "$C8_SEEDS" --reserve-seed "$C8_SEEDS" --scratch "$C8_SCRATCH"
  fi
  if [ -f "$C8_SWEEP_RUN/manifest.json" ]; then step seeds_add python3 -B tools/seeds.py add "$C8_SWEEP_RUN"; fi   # HD6, whatever happened after the plan
  if [ -f "$MODEL" ]; then
    step model_identity python3 -B tools/cost_identity.py check --model "$MODEL" --exe bin/c8d3_gmp --host-cpu --mp-check on
    # both executable identities, PREV and the basis (D.14); fails unless the plan, the manifest and the model agree
    REFRESH_PY='import hashlib,json,sys
run,model,basis,prev,out=sys.argv[1:6];h=lambda p:hashlib.sha256(open(p,"rb").read()).hexdigest()
m=json.load(open(run+"/manifest.json"));M=json.load(open(model));P=json.load(open(prev));exe=h("bin/c8d3_gmp")
b=next((json.loads(l)for l in open(basis)if l.startswith("{")),{})
chk={"manifest_plan_role_cost_refresh":m.get("plan_role")=="cost_refresh","manifest_executable_is_bin_c8d3_gmp":m.get("executable_sha256")==exe,
     "model_plan_role_cost_refresh":(M.get("source")or{}).get("plan_role")=="cost_refresh","model_basis_is_basis_log":bool(b.get("basis"))and(M.get("scheduled_with")or{}).get("basis")==b.get("basis")}
rec={"schema":"c8-d3-refresh-record-1","run":run,"manifest_sha256":h(run+"/manifest.json"),"plan_role":m.get("plan_role"),"cost_basis":m.get("cost_basis"),
     "executable_sha256":exe,"manifest_executable_sha256":m.get("executable_sha256"),"model":model,"model_sha256":h(model),"model_executable_sha256":M.get("executable_sha256"),
     "model_cpu_model":M.get("cpu_model"),"scheduled_with":M.get("scheduled_with"),"basis":b,"previous_model":prev,"previous_model_sha256":h(prev),
     "previous_executable_sha256":P.get("executable_sha256"),"checks":chk,"ok":all(chk.values())}
open(out,"w").write(json.dumps(rec,indent=1)+"\n");print(json.dumps(rec));sys.exit(0 if rec["ok"]else 1)'
    step refresh_record python3 -B -c "$REFRESH_PY" "$C8_SWEEP_RUN" "$MODEL" "$EV/basis.log" "$PREV" "$EV/refresh_record.json"
    step assemble python3 -B tools/assemble.py "$C8_SWEEP_RUN" --bootstrap 1024
    cp "$C8_SWEEP_RUN"/C8_test_result.json "$EV/" 2>/dev/null || true
    step cost_summary python3 -B tools/cost_summary.py "$C8_SWEEP_RUN" "$MODEL" --symmetry-model cost_models/gmp_symmetry_epyc7532.json --output "$EV/cost_summary.json"
  fi
  ( cd "$W" && python3 -B tools/production.py status "$C8_SWEEP_RUN" ) > "$EV/sweep_status.txt" 2>&1 || true
  cp "$C8_SWEEP_RUN"/manifest.json "$EV/sweep_manifest.json" 2>/dev/null || true
  for g in "$C8_SWEEP_RUN"/groups/*/; do [ -d "$g" ] || continue; n=$(basename "$g"); mkdir -p "$EV/groups/$n"; cp "$g"merged.json "$g"graph_costs.csv "$g"graph_promotions.csv "$EV/groups/$n/" 2>/dev/null || true; done
  cp "$C8_SEEDS" "$EV/forbidden_seeds.json"
  ;;
bld)
  # J-BLD: the data-only check first (nothing is written in the export before it), then the L8 links, the input check
  # that `plan` runs, the workers, check_build and HD11's three fields of the committed model on this CPU class
  step data_only_diff python3 -B "$C8_ROOT/pkg/$C8_BLD_BASE_PKG/tools/cost_identity.py" data-only --base "$C8_ROOT/pkg/$C8_BLD_BASE_PKG" --data "$C8_PACKAGE" \
       --output "$EV/data_only_diff.json"   # the BASE export's tool: the tree under test never judges itself
  if printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then stamp "bld: not a data-only export of $C8_BLD_BASE_PKG: nothing linked or built"
  else
    step link_l8 make link-l8 PYTHON=python3 STORE="$C8_STORE"
    step verify_inputs make verify-inputs PYTHON=python3
    step make_native $MK PYTHON=python3 bin/c8d3_gmp bin/c8d3_decimal
    step check_build python3 -B tests/check_build.py "${BUILDINFO_ARGS[@]}" --output "$EV/check_build.json" bin/c8d3_gmp.buildinfo.json bin/c8d3_decimal.buildinfo.json
    step model_identity python3 -B tools/cost_identity.py check --model "cost_models/$C8_SITE_MODEL" --exe bin/c8d3_gmp --host-cpu --mp-check on
    MODEL_PY='import hashlib,json,sys
p,out=sys.argv[1:3];b=open(p,"rb").read();m=json.loads(b);src=m.get("source")or{}
chk={"measured":m.get("measured")is True,"schema_c8_d3_cost_model_1":m.get("schema")=="c8-d3-cost-model-1","source_plan_role_cost_sweep_or_cost_refresh":src.get("plan_role")in("cost_sweep","cost_refresh")}
rec={"schema":"c8-d3-model-record-1","model":p,"sha256":hashlib.sha256(b).hexdigest(),**{k:m.get(k)for k in("executable_sha256","cpu_model","mp_check","lane_shape","job_ids","scheduled_with","source")},
     "checks":chk,"ok":all(chk.values())}
open(out,"w").write(json.dumps(rec,indent=1)+"\n");print(json.dumps(rec));sys.exit(0 if rec["ok"]else 1)'
    step model_record python3 -B -c "$MODEL_PY" "cost_models/$C8_SITE_MODEL" "$EV/model_record.json"
    # the build and its checks (link_l8 ... model_record) decide whether bin/ may stay; the sweep's bookkeeping below does not
    BLD_FAIL=0; if printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then BLD_FAIL=1; fi
    if [ -n "${C8_SWEEP_RUN:-}" ]; then   # A-ORC-9's sweep part, after the sweep job has ended (bookkeeping only)
      step sweep_accounting bash -c 'cd "$0" && python3 -B tools/accounting.py "$1" --json > "$2"' "$C8_SWEEP_PKG" "$C8_SWEEP_RUN" "$EV/sweep_accounting.json"
      step cost_summary python3 -B tools/cost_summary.py "$C8_SWEEP_RUN" "cost_models/$C8_SITE_MODEL" --symmetry-model cost_models/gmp_symmetry_epyc7532.json \
           --accounting "$EV/sweep_accounting.json" --output "$EV/cost_summary.json"
    fi
    if [ "$BLD_FAIL" = 1 ]; then
      if [ -e "$C8_PACKAGE/bin" ]; then mv "$C8_PACKAGE/bin" "$C8_PACKAGE/bin.bld_failed_$SLURM_JOB_ID"; ASIDE="bin/ moved aside to $C8_PACKAGE/bin.bld_failed_$SLURM_JOB_ID"; else ASIDE="no bin/ was produced"; fi
      stamp "bld FAILED: $ASIDE (no plan or lane worker may use an unchecked binary); PLAN risk 32: repeat the refresh on this export (sweep2 with C8_PACKAGE=$C8_PACKAGE), a new data-only commit, a new J-BLD"
    elif printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then
      stamp "export built in place: $C8_PACKAGE (bin/, inputs/packs L8 links; the build, check_build and the HD11 identity passed, bin/ kept); only the sweep's bookkeeping (sweep_accounting, cost_summary) failed: no risk-32 loop and no new J-BLD (this export refuses a second one). Rerun just those two, on a login node or in a short raw job: (cd $C8_SWEEP_PKG && python3 -B tools/accounting.py $C8_SWEEP_RUN --json > $EV/sweep_accounting_rerun.json) && (cd $C8_PACKAGE && python3 -B tools/cost_summary.py $C8_SWEEP_RUN cost_models/$C8_SITE_MODEL --symmetry-model cost_models/gmp_symmetry_epyc7532.json --accounting $EV/sweep_accounting_rerun.json --output $EV/cost_summary_rerun.json)"
    else stamp "export built in place: $C8_PACKAGE (bin/, inputs/packs L8 links); every later Stage-5 plan and lane worker of this commit runs from it"; fi
  fi
  ;;
profbuild|prof1|prof2|prof3)
  [ -n "$BASE_SHA" ] || STATUS+=("{\"step\":\"baseline_record\",\"status\":\"FAIL\",\"rc\":65,\"seconds\":0}")   # no c8-stage3 record for this site
  P8="$C8_SCRATCH/prof"; mkdir -p "$P8"
  snapshot() { { echo "== $1 $(date '+%Y-%m-%dT%H:%M:%S%z')"; uptime; ps -eo user,pid,pcpu,rss,etimes,comm --sort=-pcpu | head -n 15; } >> "$EV/node_load.txt" 2>&1; }
  { hostname; lscpu; numactl --hardware 2>&1; echo "perf: $(command -v perf || echo missing) $(perf --version 2>&1)"
    echo "perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)"; echo "kptr_restrict $(cat /proc/sys/kernel/kptr_restrict)"
    for x in ltrace readelf objcopy addr2line numastat; do echo "$x: $(command -v $x || echo missing)"; done; } > "$EV/node.txt" 2>&1
  snapshot start
  if [ "$C8_JOB" = prof1 ]; then
    # the clean merge rates: the job's first step, nothing else running on the node (Stage 3b repair round 2)
    step merge_scale_clean python3 -B tests/merge_scale.py --rows 1000000 --jobs 16 --run-jobs 16 --skip-many-shards --skip-memory-scaling \
         --output "$EV/merge_scale_clean.json"
    step merge_scale_clean_r2 python3 -B tests/merge_scale.py --rows 1000000 --jobs 16 --run-jobs 16 --skip-many-shards --skip-memory-scaling \
         --output "$EV/merge_scale_clean_r2.json"
    snapshot after_merge_scale
  fi
  case "$C8_JOB" in
    profbuild) TARGETS="bin/c8d3_gmp bin/c8d3_gmp_prof bin/c8d3_gmp_ratiohist c7ref" ;;
    prof1) TARGETS="bin/c8d3_gmp bin/c8d3_gmp_prof c7ref" ;;
    prof2) TARGETS="bin/c8d3_gmp" ;;
    prof3) TARGETS="bin/c8d3_gmp bin/c8d3_gmp_ratiohist" ;;
  esac
  step make_native $MK $TARGETS
  step baseline_identity bash -c 'b=$(sha256sum bin/c8d3_gmp | cut -d" " -f1); echo "rebuilt bin/c8d3_gmp $b, c8-stage3 baseline $0"; [ "$b" = "$0" ]' "$BASE_SHA"
  if printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then stamp "build or baseline identity failed: no profile runs"
  else
    step fixtures8_verify python3 -B tools/prepare_benchmarks.py --order 8
    step fixtures7_verify python3 -B tools/prepare_benchmarks.py --order 7
    case "$C8_JOB" in
    profbuild)
      step fixtures8_stage python3 -B tools/prepare_benchmarks.py --order 8 --stage-check "$P8/stagecheck"
      SM=(--smoke-tasks 24 --smoke-points 64 --fake-topology 1x2x8 --no-pin --scratch "$P8")
      step smoke_p1 python3 -B tools/perf_profile.py p1 --output "$EV/smoke_p1" --threads 8 --blocks strat_free_L7,strat_power_L8 --expect-sha256 "$B8" "${SM[@]}"
      step smoke_mpcheck python3 -B tools/perf_profile.py mpcheck --output "$EV/smoke_mpcheck" --threads 8 --blocks strat_free_L7,strat_power_L8 "${SM[@]}"
      step smoke_p2 python3 -B tools/perf_profile.py p2 --output "$EV/smoke_p2" --threads 8 --blocks nopromo_free_L8 --serial-seconds 2 "${SM[@]}"
      step smoke_p3 python3 -B tools/perf_profile.py p3 --output "$EV/smoke_p3" --threads 8 --blocks random_power_L8 "${SM[@]}"
      step smoke_fe python3 -B tools/perf_profile.py fe --output "$EV/smoke_fe" --repeats 1 --loaded-threads 8 --fake-topology 1x2x8 --no-pin --scratch "$P8"
      step smoke_probe python3 -B tools/benchmark.py --interleave-probe --output "$EV/smoke_probe" --probe-graphs nopromo_free_L8:1,strat_power_L8:1 \
           --probe-points 256 --probe-repeats 1 --fake-topology 1x2x8 --no-pin --scratch "$P8"
      step smoke_p4 python3 -B tools/benchmark.py --lane-shapes 2x8,1x16 --fraction 0.004 --output "$EV/smoke_p4" --expect-sha256 "$B8" \
           --fake-topology 1x2x8 --no-pin --scratch "$P8"
      ;;
    prof1)
      snapshot before_fe
      step fe python3 -B tools/perf_profile.py fe --output "$EV/fe" --repeats 3 --scratch "$P8"
      step p1 python3 -B tools/perf_profile.py p1 --output "$EV/p1" --threads 64 --expect-sha256 "$B8" --scratch "$P8"
      step mpcheck python3 -B tools/perf_profile.py mpcheck --output "$EV/mpcheck" --threads 64 --scratch "$P8"
      ;;
    prof2)
      step p4 python3 -B tools/benchmark.py --lane-shapes "${C8_P4_SHAPES:-8x16,4x32,2x64,1x128,16x8}" --output "$EV/p4" --expect-sha256 "$B8" --scratch "$P8"
      ;;
    prof3)
      step p2 python3 -B tools/perf_profile.py p2 --output "$EV/p2" --threads 64 --expect-sha256 "$B8" --scratch "$P8"
      step probe python3 -B tools/benchmark.py --interleave-probe --output "$EV/probe" --scratch "$P8"
      step p3 python3 -B tools/perf_profile.py p3 --output "$EV/p3" --scratch "$P8"
      ;;
    esac
  fi
  snapshot end
  ;;
optsmoke|opt)
  [ -n "$BASE_SHA" ] || STATUS+=("{\"step\":\"baseline_record\",\"status\":\"FAIL\",\"rc\":65,\"seconds\":0}")   # no c8-stage3 record for this site
  P8="$C8_SCRATCH/opt"; mkdir -p "$P8"
  snapshot() { { echo "== $1 $(date '+%Y-%m-%dT%H:%M:%S%z')"; uptime; ps -eo user,pid,pcpu,rss,etimes,comm --sort=-pcpu | head -n 15; } >> "$EV/node_load.txt" 2>&1; }
  { hostname; lscpu; numactl --hardware 2>&1; } > "$EV/node.txt" 2>&1
  snapshot start
  QD=""; grep -q '^quaddiff:' "$W/Makefile" && QD=quaddiff
  TARGETS="bin/c8d3_gmp bin/c8d3_decimal $QD"; [ "$C8_JOB" = opt ] && TARGETS="$TARGETS c7ref"
  case ",${C8_OPT_GATES:-}," in *,inspect_check,*) TARGETS="$TARGETS inspect test-builds" ;; esac
  step make_native $MK $TARGETS
  step check_build python3 -B tests/check_build.py "${BUILDINFO_ARGS[@]}" --output "$EV/check_build.json" bin/c8d3_gmp.buildinfo.json bin/c8d3_decimal.buildinfo.json
  step baseline_install make baseline PYTHON=python3 STORE="$C8_STORE"
  step baseline_identity bash -c 'b=$(sha256sum bin/baseline/c8d3_gmp | cut -d" " -f1); echo "bin/baseline/c8d3_gmp $b, c8-stage3 $0"; [ "$b" = "$0" ]' "$BASE_SHA"
  ( cd "$W" && sha256sum bin/c8d3_gmp bin/c8d3_decimal bin/baseline/c8d3_gmp bin/baseline/c8d3_decimal ) | tee "$EV/candidate.sha256"
  PREVBIN=""
  if [ -n "${C8_OPT_PREV:-}" ]; then
    PREVBIN="$C8_STORE/opt/$C8_OPT_PREV"
    step prev_identity bash -c 'cd "$0" && sha256sum -c SHA256SUMS' "$PREVBIN"
  elif [ -n "${C8_OPT_PREV_PKG:-}" ]; then
    PB="$C8_SCRATCH/prev_$C8_OPT_PREV_PKG"; mkdir -p "$PB"; copy_export "$C8_ROOT/pkg/$C8_OPT_PREV_PKG" "$PB"   # never a built export's bin/: PREV is rebuilt here
    step prev_build bash -c 'cd "$0" && make -j 32 CXX=g++ PYTHON=python3 bin/c8d3_gmp bin/c8d3_decimal && sha256sum bin/c8d3_gmp bin/c8d3_decimal' "$PB"
    PREVBIN="$PB/bin"; ( cd "$PB/bin" && sha256sum c8d3_gmp c8d3_decimal ) > "$EV/prev_build.sha256" 2>&1 || true
  fi
  if printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then stamp "build, baseline or previous-binary check failed: no gate runs"
  elif [ "$C8_JOB" = optsmoke ]; then
    SM=(--fake-topology 1x2x8 --no-pin)
    step smoke_l8self python3 -B tests/validate.py --parts none --l8self bin/baseline --l8self-sizes 2,6,4 --jobs 2 --threads 4 --output "$EV/smoke_l8self.json"
    step smoke_first_error python3 -B tests/first_error.py --baseline bin/baseline --repeats 1 --threads 1,4 --output "$EV/smoke_first_error.json"
    step smoke_speed python3 -B tools/opt_speed.py --exe B0=bin/baseline/c8d3_gmp --exe CAND=bin/c8d3_gmp --step smoke=B0:CAND --shape 2x8 --shape-of B0=1x16 \
         --expect B0="$B8" --sample-sizes 2,6,4 --repeats 1 "${SM[@]}" --output "$EV/smoke_speed" --scratch "$P8"
    step smoke_thread_identity python3 -B tests/thread_identity.py --threads-list 1,8 --splits 2,16 --backends gmp --parts blocks --output "$EV/smoke_thread_identity.json"
    if [ -n "$QD" ]; then
      step smoke_quaddiff python3 -B tests/quad_differential.py --pairs 1048576 --min-pairs 1048576 --min-stream-pairs 262144 --ubsan-pairs 16384 --ranges-graphs 4 --ranges-points 64 \
           --threads "$OMP_NUM_THREADS" --scratch "$P8" --output "$EV/smoke_quad_differential.json"
    fi
  else
    GATES=",${C8_OPT_GATES:-validate_full,l8self,thread_identity},"
    mkdir -p "$EV/status.d"; rm -f "$EV"/status.d/*.json
    stamp "J-OPT $C8_OPT_STEP: exact gates ${GATES//,/ }"
    case "$GATES" in *,validate_full,*) ( pstep validate_full python3 -B tests/validate.py --full --threads 64 --output "$EV/validate_full.json" ) & ;; esac
    case "$GATES" in *,l8self,*) ( pstep l8self python3 -B tests/validate.py --parts none --l8self bin/baseline --jobs 16 --threads 4 --output "$EV/l8self.json" ) & ;; esac
    wait
    for f in "$EV"/status.d/*.json; do [ -f "$f" ] && STATUS+=("$(cat "$f")"); done
    case "$GATES" in *,same_binary,*) step same_binary bash -c 'for b in c8d3_gmp c8d3_decimal; do x=$(sha256sum "bin/$b" | cut -d" " -f1); y=$(sha256sum "$0/$b" | cut -d" " -f1); echo "$b rebuilt $x, stored $y"; [ "$x" = "$y" ] || exit 1; done' "$PREVBIN" ;; esac
    case "$GATES" in *,first_error,*) step first_error python3 -B tests/first_error.py --baseline bin/baseline --output "$EV/first_error.json" ;; esac
    case "$GATES" in *,thread_identity,*) step thread_identity python3 -B tests/thread_identity.py --splits numa,numa:2,numa:4,16 --output "$EV/thread_identity.json" ;; esac
    case "$GATES" in *,inspect_check,*) step inspect_check python3 -B tests/inspect_check.py --output "$EV/inspect_check.json" ;; esac
    case "$GATES" in *,quaddiff,*) step quad_differential python3 -B tests/quad_differential.py --threads 128 --scratch "$P8" --output "$EV/quad_differential.json" ;; esac
    case "$GATES" in *,forced_tiers,*)
      step forced_tiers python3 -B tests/forced_tiers.py --threads 128 --max-seconds 1200 --output "$EV/forced_tiers.json"
      VAL3=$( (cd "$W" && python3 -B tools/baseline.py val3) 2>>"$EV/baseline_record.log" || true)   # this site's Stage-3 J-VAL-3 record
      step forced_tiers_vs_stage3 python3 -B tests/record_compare.py --kind forced_tiers "$EV/forced_tiers.json" \
           "${VAL3:-no-J-VAL-3-record-for-site-${C8_SITE}}" --output "$EV/forced_tiers_vs_stage3.json" ;;
    esac
    VW=""
    if [ -n "${C8_OPT_VARIANT_OPTFLAGS:-}" ] && ! printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then
      # #7 (opt-in): the same source with OPTFLAGS=$C8_OPT_VARIANT_OPTFLAGS (STRICT kept), in a second Lustre work copy
      VW="$C8_ROOT/work/${C8_JOB}_${SLURM_JOB_ID}_variant"; W0=$W
      step variant_copy copy_export "$C8_PACKAGE" "$VW"   # never a built export's bin/: the OPTFLAGS variant is rebuilt
      W=$VW
      step variant_link_l8 make link-l8 PYTHON=python3 STORE="$C8_STORE"
      step variant_build bash -c 'make -j 32 CXX=g++ PYTHON=python3 OPTFLAGS="$0" bin/c8d3_gmp bin/c8d3_decimal && mkdir -p bin/ref bin/baseline \
        && cp -p "$1"/bin/ref/c7d3_* bin/ref/ && cp -p "$1"/bin/baseline/* bin/baseline/ && sha256sum bin/c8d3_gmp bin/c8d3_decimal' "$C8_OPT_VARIANT_OPTFLAGS" "$W0"
      ( cd "$VW" && sha256sum bin/c8d3_gmp bin/c8d3_decimal ) > "$EV/variant.sha256" 2>&1 || true
      ( pstep variant_validate_full python3 -B tests/validate.py --full --threads 64 --output "$EV/variant_validate_full.json" ) &
      ( pstep variant_l8self python3 -B tests/validate.py --parts none --l8self bin/baseline --jobs 16 --threads 4 --output "$EV/variant_l8self.json" ) &
      wait
      for f in "$EV"/status.d/variant_*.json; do [ -f "$f" ] && STATUS+=("$(cat "$f")"); done
      W=$W0
    fi
    snapshot after_gates
    if printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then stamp "J-OPT $C8_OPT_STEP: an exact gate failed: no speed measurement (the change is reverted)"
    else
      SPEED=(--exe B0=bin/baseline/c8d3_gmp)
      if [ -n "$PREVBIN" ]; then
        SPEED+=(--exe PREV="$PREVBIN/c8d3_gmp" --exe CAND=bin/c8d3_gmp --step "$C8_OPT_STEP=PREV:CAND" --step cumulative=B0:CAND --step prev_vs_stage3=B0:PREV)
      else
        SPEED+=(--exe CAND=bin/c8d3_gmp --step "$C8_OPT_STEP=B0:CAND")
      fi
      if [ -n "$VW" ]; then SPEED+=(--exe VAR="$VW/bin/c8d3_gmp" --step "7=CAND:VAR"); fi
      IFS=',' read -ra SH <<< "${C8_OPT_SHAPES:-}"; for s in "${SH[@]}"; do [ -n "$s" ] && SPEED+=(--shape-of "$s"); done
      step speed python3 -B tools/opt_speed.py "${SPEED[@]}" --expect B0="$B8" --repeats 3 --shape 16x8 --output "$EV/speed" --scratch "$P8"
      snapshot after_speed
      if ! printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then
        OPTD="$C8_STORE/opt/$SHA12"
        step store_candidate bash -c 'd="$0"; [ ! -e "$d" ] || { echo "$d exists (never overwritten)"; exit 1; }; mkdir -p "$d.tmp"
          for f in c8d3_gmp c8d3_gmp.buildinfo.json c8d3_decimal c8d3_decimal.buildinfo.json; do cp -p "bin/$f" "$d.tmp/$f"; done
          ( cd "$d.tmp" && sha256sum c8d3_gmp c8d3_gmp.buildinfo.json c8d3_decimal c8d3_decimal.buildinfo.json > SHA256SUMS ); chmod a-w "$d.tmp"/*; mv "$d.tmp" "$d"; cat "$d/SHA256SUMS"' "$OPTD"
        cp "$OPTD/SHA256SUMS" "$EV/stored_SHA256SUMS" 2>/dev/null || true
        if [ -n "$VW" ]; then rm -rf "$VW"; stamp "variant work copy $VW removed"; fi
      fi
    fi
  fi
  snapshot end
  ;;
val3a)
  step make_native $MK bin/c8d3_gmp bin/c8d3_decimal c7ref
  step validate_bk8_l2 python3 -B tests/validate.py --parts identity --bk8 --l2-control --output "$EV/validate_bk8_l2.json"
  ;;
run1)
  step make_native $MK bin/c8d3_gmp c7ref
  step run1_replay python3 -B tests/run1_replay.py --archive "$C8_STORE/run1-20260930-m4096_full.tgz" \
       --sha256 08969c109598e31173fefb003e3703b2433fccb404ca1476646db0805130fc80 --work "$C8_SCRATCH" --output "$EV/run1_replay.json"
  step test_replay python3 -B tests/archived_stream_replay.py --exe bin/c8d3_gmp --output "$EV/archived_stream_replay.json"
  step test_pilot_report_run1 python3 -B tests/test_pilot_report.py --run1 --archive "$C8_STORE/run1-20260930-m4096_full.tgz" \
       --output "$EV/test_pilot_report_run1.json"
  ;;
repair3a)
  step make_native $MK bin/c8d3_gmp bin/c8d3_decimal c7ref inspect test-builds
  step check_build python3 -B tests/check_build.py "${BUILDINFO_ARGS[@]}" --output "$EV/check_build.json" bin/c8d3_gmp.buildinfo.json \
       bin/c8d3_decimal.buildinfo.json bin/ref/c7d3_gmp.buildinfo.json bin/ref/c7d3_decimal.buildinfo.json
  step validate_g_c7 python3 -B tests/validate.py --full --parts identity,g_c7 --output "$EV/validate_g_c7.json"
  step inspect_check python3 -B tests/inspect_check.py --output "$EV/inspect_check.json"
  step class_b_e python3 -B tests/class_b.py --parts e ${D3ARGS[@]+"${D3ARGS[@]}"} --output "$EV/class_b_e.json"
  step test_pilot_report_run1 python3 -B tests/test_pilot_report.py --run1 --archive "$C8_STORE/run1-20260930-m4096_full.tgz" \
       --output "$EV/test_pilot_report_run1.json"
  : "${C8_SEEDS:?C8_SEEDS (env.sh)}"
  if [ ! -e "$C8_SEEDS" ]; then step seeds_init python3 -B tools/seeds.py init --log "$C8_SEEDS"; fi
  step seeds_register python3 -B tools/seeds.py add --seed 20261004 --label 'G-RUN1 selection (tests/run1_replay.py --seed, J-RUN1; PLAN F tolerance policy)' --log "$C8_SEEDS"
  ( cd "$W" && python3 -B tools/seeds.py list --log "$C8_SEEDS" ) > "$EV/forbidden_seeds.json" 2>&1 || true
  ;;
basestore)
  BP="$C8_SCRATCH/base_$C8_BASE_PKG"; mkdir -p "$BP"; copy_export "$C8_ROOT/pkg/$C8_BASE_PKG" "$BP"   # never a built export's bin/: B0 is rebuilt here
  step base_build bash -c 'cd "$0" && make -j "$1" CXX=g++ PYTHON=python3 bin/c8d3_gmp bin/c8d3_decimal && sha256sum bin/c8d3_gmp bin/c8d3_decimal' "$BP" "$OMP_NUM_THREADS"
  step base_check_build python3 -B tests/check_build.py "${BUILDINFO_ARGS[@]}" --output "$EV/base_check_build.json" "$BP/bin/c8d3_gmp.buildinfo.json" \
       "$BP/bin/c8d3_decimal.buildinfo.json"
  if printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then stamp "basestore: build or check_build failed: nothing stored"
  else
    BASE="$C8_STORE/baseline/$C8_BASE_PKG"
    step base_store bash -c 'b="$0"; s="$1"; [ ! -e "$b" ] || { echo "$b exists (never overwritten)"; exit 1; }; mkdir -p "$b.tmp"
      for f in c8d3_gmp c8d3_gmp.buildinfo.json c8d3_decimal c8d3_decimal.buildinfo.json; do cp -p "$s/$f" "$b.tmp/$f"; done
      ( cd "$b.tmp" && sha256sum c8d3_gmp c8d3_gmp.buildinfo.json c8d3_decimal c8d3_decimal.buildinfo.json > SHA256SUMS ); chmod a-w "$b.tmp"/*; mv "$b.tmp" "$b"; cat "$b/SHA256SUMS"' "$BASE" "$BP/bin"
    cp "$BASE/SHA256SUMS" "$EV/base_SHA256SUMS" 2>/dev/null || true
    stamp "record it (with the site's J-VAL-3 record): python3 -B tools/baseline.py record $EV/base_SHA256SUMS --site ${C8_SITE} --commit <the full sha of $C8_BASE_PKG> --job $SLURM_JOB_ID --forced-tiers-record <benchmarks/.../val3/forced_tiers.json>"
  fi
  ;;
repair3b)
  step make_native $MK bin/c8d3_gmp bin/c8d3_decimal inspect test-builds
  step class_b_e_tails python3 -B tests/class_b.py --parts e ${D3ARGS[@]+"${D3ARGS[@]}"} --zero-channel-tails "$EV/zero_channel_tails.json" \
       --output "$EV/class_b_e.json"
  step test_pilot_report_zero_channel python3 -B tests/test_pilot_report.py --zero-channel "$EV/zero_channel_tails.json" \
       --output "$EV/test_pilot_report_zero_channel.json"
  : "${C8_SEEDS:?C8_SEEDS (env.sh)}"
  step seeds_copy cp "$C8_SEEDS" "$EV/forbidden_seeds.json"
  ;;
esac
mkdir -p "$EV/buildinfo"
for f in $(cd "$W" && find bin -name '*.buildinfo.json' 2>/dev/null); do mkdir -p "$EV/buildinfo/$(dirname "$f")"; cp "$W/$f" "$EV/buildinfo/$f"; done
( cd "$W" && find bin -type f ! -name '*.json' ! -name '*.txt' -exec sha256sum {} + 2>/dev/null ) > "$EV/binaries.sha256" || true
{ printf '{"job":"%s","slurm_job":"%s","host":"%s","package":"%s","steps":[' "$C8_JOB" "$SLURM_JOB_ID" "$(hostname)" "$SHA12"
  (IFS=,; printf '%s' "${STATUS[*]}"); printf ']}\n'; } > "$EV/summary.json"
cat "$EV/summary.json"
if printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then stamp "native_job $C8_JOB: FAILED steps (see $EV)$([ "$L8WORK" = 1 ] && echo "; work copy kept: $W")"; exit 1; fi
case "$C8_JOB" in val1|val2|val3|val4|smoke3b|profbuild|prof1|prof2|prof3|optsmoke|opt) rm -rf "$W"; stamp "work copy $W removed" ;; sweep1|sweep2|argmax) stamp "work copy kept (its campaign names it): $W" ;; esac
if printf '%s\n' "${STATUS[@]}" | grep -q '"SITE_REFUSED"'; then stamp "native_job $C8_JOB: SITE_REFUSED steps are the Mac fakes of the admission engine (expected on a cluster node)"; fi
stamp "native_job $C8_JOB: all steps passed ($EV)"
