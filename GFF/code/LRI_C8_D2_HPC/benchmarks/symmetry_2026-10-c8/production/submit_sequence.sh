# C8(2) PRODUCTION on symmetry: the host's submit sequence (2026-10-06). NOT a script to run blindly: run it block by
# block on the symmetry login node (ssh symmetry), in a fresh shell, inside the 8-node window agreed with C63d (the
# DECISIONS line in LRI_C8_shared/inventory/DECISIONS.md written first, C63d told at open and at close). Nothing here was
# submitted by the preparation. Lane mode, docs/HPC.md "Lane mode" and "Pilot runbook" steps 2-4 (the same commands for
# a production batch, docs/DESIGN.md "Production batches"). Every value below is checked in README.md.

# ---------------------------------------------------------------------------------------------------------------------
# 0. Environment (W17: the site environment first; nothing else loaded: the library stack the survey fingerprinted)
# ---------------------------------------------------------------------------------------------------------------------
source ~/c8d2/env.sh
export C8_ENV_SETUP=$HOME/c8d2/env.sh
export C8_PACKAGE=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
export C8_RUN=/mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e
# the production pool: the 12 surveyed EPYC 7543 nodes with the production worker's runtime identity 04f1e51d...
#   cn093 cn094 cn098 cn099 cn100 cn101 cn102 cn103 cn104 cn108 cn109 cn110   (survey/survey.json)
# everything else in amdq is excluded (Zen 2 7532 nodes, unsurveyed nodes, cn105 down, cn112 by rule):
X=cn083,cn084,cn085,cn086,cn087,cn088,cn089,cn090,cn091,cn092,cn095,cn096,cn097,cn105,cn106,cn107,cn112
# (the list the preparation was given, which also excludes cn098 (down* until its reboot today) and leaves 11 pool
#  nodes, is equally valid:
#  X=cn083,cn084,cn086,cn088,cn089,cn090,cn091,cn095,cn096,cn097,cn098,cn105,cn106,cn107,cn112,cn085,cn087,cn092)
: "${C8_SEEDS:?source the site environment}" "${C8_PACKAGE:?}" "${C8_RUN:?}"
cat $C8_PACKAGE.commit                                            # ba68f401e46e4071ca5593ae40ec92a1755dcc98
sha256sum $C8_PACKAGE/bin/c8d2_gmp_dd+mp256 $C8_RUN/manifest.json  # a46f3060a27f... and be215e0e89bd...
echo "$LD_LIBRARY_PATH"                                           # /cm/local/apps/boost/1.77.0//lib64
env | grep -E '^(LD_PRELOAD|LD_AUDIT|LD_DYNAMIC_WEAK|GLIBC_TUNABLES)=' || echo "no loader override"   # W7: must print "no loader override"
env | grep -E '^DYLD_' || true                                    # nothing
module list 2>&1 | tr -s ' ' | head -5                            # boost/1.77.0 python/3.11 only (env.sh); no gcc/gmp module
python3 -c 'import sys;print(sys.executable)'                      # /home/zzheng1/c8d2/venv/bin/python3
echo "C8_AMDQ_CAP=$C8_AMDQ_CAP C8_SITE=$C8_SITE"                   # 4 symmetry (env.sh default; the window value is given on the submit line)

# ---------------------------------------------------------------------------------------------------------------------
# 1. Survey: say start-now vs queue
# ---------------------------------------------------------------------------------------------------------------------
sinfo -h -p amdq -o '%t %D'
sinfo -N -h -p amdq -o '%N %t' | sort | paste -sd' '              # at least 8 of the 12 pool nodes idle -> starts now
squeue -u $USER -h -r -o '%i|%T|%P|%q|%D|%u|%j'                  # no live c8d2-* line on amdq/amddebugq/amdpreq
squeue -h -o '%i %u %j %T %P %N' | grep ' c8d3-' || true          # C63d's jobs: inside their share of the window
scontrol show res | grep -E 'ReservationName|Nodes='              # shotinli_118 holds cn088-091 (excluded anyway)

# ---------------------------------------------------------------------------------------------------------------------
# 2. The 5-minute start-latency probe (an AMD-pool c8d2- job: it counts against the cap while live)
# ---------------------------------------------------------------------------------------------------------------------
sbatch -p amdq --exclude=$X -N 1 --ntasks=1 --cpus-per-task=64 --exclusive --mem=245G -t 00:05:00 \
  -J c8d2-prod-probe -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out --wrap 'hostname; date'
#   -> "Submitted batch job P". WAIT until it has ended (squeue -j P empty), then record the queue wait:
sacct -j P -X -o JobID,Submit,Start,End,State,NodeList            # COMPLETED on one of the 12 pool nodes
#   log: /mnt/beegfs/zzheng1/c8d2/logs/c8d2-prod-probe_P.out

# ---------------------------------------------------------------------------------------------------------------------
# 3. The campaign as planned
# ---------------------------------------------------------------------------------------------------------------------
python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN --fast
#   no WARNING about changed pinned tools; "1129 incomplete job indices: 0-1128"; CPU vendor and runtime identity not
#   pinned yet; exit 1 (plan/status_before_submit.txt)

# ---------------------------------------------------------------------------------------------------------------------
# 4. Round 1: 8 whole-node lane workers + 1 afterany merge = k 9 = C8_AMDQ_CAP (the window; C63d to confirm 9)
# ---------------------------------------------------------------------------------------------------------------------
C8_AMDQ_CAP=9 C8_SBATCH_ARGS="-p amdq --exclude=$X" C8_LANE_MEM=245G C8_LANE_TIME=24:00:00 C8_MERGE_TIME=02:00:00 \
  $C8_PACKAGE/slurm/submit.sh --lanes 8
#   expected output (format of the pilot's and J-SMK-2's):
#   C8: queue /mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e/lanes/queue.txt: 1129 incomplete indices, 12025.1 estimated core-hours
#   C8: admission {"amd_cap": 9, "amd_live": 0, "amd_live_jobs": [], "k": 9, "limits": {"c8d2 AMD-pool jobs (amdq, amddebugq, amdpreq)": {"new": 9, "room": 9}}, "new_jobs": {"lane": {"count": 8, "partitions": ["amdq"]}, "merge": {"count": 1, "partitions": ["amdq"]}}, "partitions": ["amdq"], "room": 9, "site": "symmetry"}
#   C8: partition amdq: <n> idle node(s)
#   C8: sbatch --test-only: sbatch: Job ... to start at ... using 64 processors on nodes cnNNN in partition amdq
#   lane worker <W1>; log /mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e/slurm_logs/lane-<W1>.log
#   ... (8 lines, W1..W8)
#   merge <M> (afterany:<W1>:...:<W8>); log .../slurm_logs/merge-<M>.log
#   status: /home/zzheng1/c8d2/venv/bin/python3 /mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e/tools/production.py status ... (more workers: slurm/submit.sh --lanes N)
#   A refusal (exit 65, "Largest admissible N for lanes N: n") submits nothing: the probe still live (n = 7) or the cap
#   not given (n = 3). Exit 64: an option outside the allowlist; 75: the site lock is held (another submission).

# ---------------------------------------------------------------------------------------------------------------------
# 5. During round 1 (rules: report the log paths; check each worker about 10 minutes after it starts)
# ---------------------------------------------------------------------------------------------------------------------
squeue -u $USER -o '%i %j %T %M %L %N'
tail -n 40 $C8_RUN/slurm_logs/lane-<W>.log      # "C8 lanes: job W ... on cnNNN (AMD EPYC 7543 ...); 8 lane(s) of [8, 8, 8, 8, 8, 8, 8, 8] CPUs ...;
                                                 #  86400 s left (squeue); memory limit 245.0 GiB (cgroup), largest index peak ... GiB"; no FAILED / refused
python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN --fast
ls $C8_RUN/lanes/failures/ | wc -l              # 0
python3 -c "import json;print(json.load(open('$C8_RUN/runtime_identity.json'))['key'])"   # 04f1e51dfc2e89b039f567261a341d5723806390bdd1a222245ac5c2584c360b
python3 -c "import json;d=json.load(open('$C8_RUN/cpu_vendor.json'));print(d['vendor'],d['model_name'])"  # AuthenticAMD AMD EPYC 7543 32-Core Processor
grep -h 'done in' $C8_RUN/slurm_logs/lane-*.log | tail -5   # "index I done in S s (estimate E s, class factor 1)": S/E about 0.9-1.0
# A worker that FAILED, NODE_FAILed or was cancelled early: the same submit line with --lanes 1 (or more, within the
# cap: live c8d2 jobs + N + 1 <= 9); it releases the stale claims and replaces the pending merge (A-ORC-10).

# ---------------------------------------------------------------------------------------------------------------------
# 6. After the 24 h limit: round 2 (the remainder; README section 4 gives the expected size)
# ---------------------------------------------------------------------------------------------------------------------
# a) confirm every round-1 job is terminal (never resubmit a merely PENDING job; a failed query means UNKNOWN):
sacct -j <W1>,<W2>,<W3>,<W4>,<W5>,<W6>,<W7>,<W8>,<M> -X -o JobID,JobName%16,State,Elapsed,ExitCode,NodeList
#    workers: COMPLETED (lanes found nothing more that fits the time left) or TIMEOUT; the round-1 merge: FAILED with
#    exit 65 and "C8: campaign incomplete" in its log (expected: it only checks completeness and stops)
squeue -u $USER -h -o '%i %j %T'                 # no live c8d2-* job
# b) what is left (read-only), and the size of round 2:
python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN --fast
C8_PACKAGE=$C8_PACKAGE python3 -B /mnt/beegfs/zzheng1/c8d2/work/prod-ba68f401e46e/prod_lanes.py remaining $C8_RUN --nodes 8
#    prints the incomplete indices and, for --lanes 1..8, the wall and whether one 24 h round finishes them
# c) submit: N from (b) (the smallest N whose wall is acceptable; k = N + 1 <= 9):
C8_AMDQ_CAP=9 C8_SBATCH_ARGS="-p amdq --exclude=$X" C8_LANE_MEM=245G C8_LANE_TIME=24:00:00 C8_MERGE_TIME=02:00:00 \
  $C8_PACKAGE/slurm/submit.sh --lanes N
#    "C8: queue ...: <left> incomplete indices"; stale claims of the timed-out workers released; N workers + 1 merge
# Earlier alternative: submit round 2 while round-1 workers are still ending, within the cap: N <= 9 - (live c8d2 jobs,
# the pending round-1 merge included) - 1 (admission_check.json scenario f: 2 live workers + the pending merge -> N <= 5).

# ---------------------------------------------------------------------------------------------------------------------
# 7. At the end (the last merge COMPLETED: production.py merge + assemble.py)
# ---------------------------------------------------------------------------------------------------------------------
mkdir -p /mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/prod1
python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN          # exit 0; "complete: every checkpoint block is committed"; 24 groups merged
python3 -B $C8_PACKAGE/tools/verify_result.py $C8_RUN/C8_result.json
python3 -B $C8_PACKAGE/tools/accounting.py $C8_RUN --output /mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/prod1/accounting.json   # complete only once every ledger job is terminal (X15)
python3 -B $C8_PACKAGE/tools/combine.py $C8_RUN --output /mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-final   # K = 1: C8_final.json
python3 -B $C8_PACKAGE/tools/design.py report --pilot $C8_RUN --json /mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/prod1/report.json \
  --tails-out /mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/prod1/tails.csv   # heavy tails at >= 32,768 points: confirms or clears the L8 screen (DESIGN.md step 2); run it in a sharedq job if it is slow
sacct -X --duplicates -j $(python3 -c "import json;print(','.join(sorted({str(json.loads(l)['jobid']) for l in open('$C8_RUN/submissions.jsonl')})))") \
  -o JobID,JobName%22,Partition,State,Submit,Start,End,Elapsed,ElapsedRaw,AllocCPUS,NodeList
# then: the window closed with a DECISIONS line (C63d told), and the two-log seed sync checked (PENDING_EXPANSE_SYNC.txt)
