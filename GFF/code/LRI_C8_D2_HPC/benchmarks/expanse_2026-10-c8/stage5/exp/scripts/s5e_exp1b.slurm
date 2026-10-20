#!/bin/bash
#SBATCH -A <ACCOUNT> -p debug -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-s5e-exp1b
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 5, J-EXP-1 follow-up on the same partition and node type (debug, one whole 128-core node). J-EXP-1 (54676864)
# built the export byte-identically and passed tests/validate.py, but `make test` stopped at tests/unit_orchestration.py,
# whose test group `lanes` failed: its lane worker runs with C8_LANES=2 on the job's whole affinity set, which on a
# 128-core node gives lanes of 64 cores, more than the test plan's checkpoint_tasks=8, and lanes.py refuses (64) as
# designed. Earlier Expanse J-VAL-1 runs used 16-CPU shared jobs (lanes of 8). make then skipped the rest of the list.
# This job runs EVERY command of `make test` (taken from `make -n test`, so word for word make's), one by one, each to
# the end with its own record and exit code, on the export built by J-EXP-1 (bin/ unchanged, checked), and then the
# `lanes` group alone twice: with the whole affinity set (expected: the same refusal) and under `taskset -c 0-15`
# (16 CPUs: 2 lanes of 8, the geometry of the earlier passing runs).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL s5e_exp1b.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s5eexp1b.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) partition ${SLURM_JOB_PARTITION:-?} at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)|^CPU\(s\)' "$E/node.txt"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp"
sha256sum $X | tee "$E/binaries_before.sha256"
mkdir "$E/test"
make -n test OUTPUT="$E/test" > "$E/make_n_test.txt" 2>&1 || { echo "make -n test failed"; cat "$E/make_n_test.txt"; exit 3; }
grep -E '^OPENBLAS_NUM_THREADS=1 python3 -B (tests|gen)/' "$E/make_n_test.txt" > "$E/commands.txt"
echo "$(wc -l < "$E/commands.txt") commands of make test:"; cut -c1-160 "$E/commands.txt"
status=0; i=0
while IFS= read -r cmd; do
  i=$((i+1)); name=$(echo "$cmd" | sed -E 's#.* -B (tests|gen)/([a-z_0-9]+)\.py.*#\2#'); t=$(date +%s)
  echo "== [$i] $name $(date -Is)"; bash -c "$cmd" > "$E/$i.$name.log" 2>&1; c=$?
  echo "== [$i] $name exit $c after $(( $(date +%s) - t )) s"; grep -E '^FAIL' "$E/$i.$name.log" | cut -c1-200 | head -5
  echo "$i $name $c $(( $(date +%s) - t ))" >> "$E/exits.txt"; [ $c -eq 0 ] || status=1
done < "$E/commands.txt"
echo "== lanes group alone, whole affinity ($(nproc) CPUs) $(date -Is)"
python3 -B tests/unit_orchestration.py --only lanes --output "$E/lanes_full.json" > "$E/lanes_full.log" 2>&1; a=$?
echo "exit $a"; grep -E '^PASS|^FAIL|^C8: ' "$E/lanes_full.log" | head -4 | cut -c1-240
echo "== lanes group alone, taskset -c 0-15 $(date -Is)"
taskset -c 0-15 python3 -B tests/unit_orchestration.py --only lanes --output "$E/lanes_taskset16.json" > "$E/lanes_taskset16.log" 2>&1; b=$?
echo "exit $b"; grep -E '^PASS|^FAIL|^C8: ' "$E/lanes_taskset16.log" | head -4 | cut -c1-240
echo "lanes_full $a" >> "$E/exits.txt"; echo "lanes_taskset16 $b" >> "$E/exits.txt"
sha256sum $X > "$E/binaries_after.sha256"
cmp -s "$E/binaries_before.sha256" "$E/binaries_after.sha256" && echo "executables unchanged" || { echo "executables CHANGED" >&2; status=3; }
rm -rf "$TMPDIR"
echo "finished $(date -Is), make-test commands status $status, lanes full $a, lanes taskset16 $b"
[ $b -eq 0 ] || status=1
exit $status
