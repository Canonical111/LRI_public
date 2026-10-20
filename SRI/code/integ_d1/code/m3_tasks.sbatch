#!/bin/bash
#SBATCH --job-name=integ-m3
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --exclude=cn112
#SBATCH --mem=60G
#SBATCH --time=12:00:00
#SBATCH --output=<SCRATCH>/lri_integ/logs/%x_%j.out
# usage: sbatch [--export=ALL,CE=./ce_<build>] m3_tasks.sbatch TASKFILE
# TASKFILE lines: OUTNAME engine-args...  -> results/m3/OUTNAME.out (+ OUTNAME.out.fp)
# Fix round 1 (MSC-007/008):
#  - an existing output is reused only if its fingerprint file matches (engine binary sha256, build id, input sha256,
#    args), its recorded output sha256 equals the file's, and the output header validates (input, build, args,
#    sector range); otherwise the job stops: choose a new destination (fix round 2, MSC-014);
#  - every failure (cd, mkdir, engine exit status, incomplete output) stops the job with a nonzero exit status;
#  - the engine writes OUTNAME.out.partial and renames it after fsync; the fingerprint is published atomically.
PY=<HOME>/envs/lri_c2/py3.13-mamba/bin/python
cd <SCRATCH>/lri_integ/code/m3 || { echo "FAIL: cannot cd"; exit 1; }
CE=${CE:-./ce}
[ -x "$CE" ] || { echo "FAIL: engine $CE not executable"; exit 1; }
[ -f "$1" ] || { echo "FAIL: task file $1 missing"; exit 1; }
cesha=$(sha256sum "$CE" | cut -d' ' -f1) || { echo "FAIL: cannot hash engine"; exit 1; }
build=$("$CE" -version) || { echo "FAIL: engine has no build id"; exit 1; }
export OMP_NUM_THREADS=${OMP_THREADS:-40}
export OMP_PROC_BIND=spread
echo "node $(hostname) start $(date) engine $CE sha256 $cesha build $build"; lscpu | grep -E 'Model name|^CPU\(s\)'
while read -r name args; do
  [ -z "$name" ] && continue
  out=../../results/m3/$name.out
  err=../../logs/m3_$name.err
  inp=$(echo " $args " | sed -n 's/.* -i \([^ ]*\) .*/\1/p')
  [ -n "$inp" ] && [ -f "$inp" ] || { echo "FAIL $name: input '$inp' missing"; exit 1; }
  insha=$(sha256sum "$inp" | cut -d' ' -f1) || { echo "FAIL $name: cannot hash input"; exit 1; }
  fp="engine_sha256=$cesha build=$build input_sha256=$insha args=$args"
  if [ -e "$out" ] || [ -e "$out.fp" ]; then
    # reuse only if the fingerprint (engine, build, input, args) matches, the recorded output hash equals the file's
    # hash, and the output's own header carries the same input, build, arguments and sector range (MSC-014)
    if [ -f "$out" ] && [ -f "$out.fp" ] && [ "$(head -1 "$out.fp")" = "$fp" ] \
       && [ "$(sed -n 2p "$out.fp")" = "output_sha256=$(sha256sum "$out" | cut -d' ' -f1)" ] \
       && $PY validate_output.py "$out" "$insha" "$build" $args >/dev/null; then
      echo "reuse $name (fingerprint and content hash match, output valid)"; continue
    fi
    echo "FAIL $name: $out exists with a different or missing fingerprint; refusing to reuse, choose a new destination"; exit 1
  fi
  mkdir -p "$(dirname "$out")" || { echo "FAIL $name: mkdir $(dirname "$out")"; exit 1; }
  mkdir -p "$(dirname "$err")" || { echo "FAIL $name: mkdir $(dirname "$err")"; exit 1; }
  echo "run $name: $args  $(date)"
  "$CE" -o "$out" $args 2> "$err"
  rc=$?
  if [ $rc -ne 0 ]; then echo "FAIL $name: engine exit status $rc (see $err)"; exit 1; fi
  $PY validate_output.py "$out" "$insha" "$build" $args || { echo "FAIL $name: output incomplete or inconsistent"; exit 1; }
  osha=$(sha256sum "$out" | cut -d' ' -f1) || { echo "FAIL $name: cannot hash output"; exit 1; }
  printf '%s\noutput_sha256=%s\n' "$fp" "$osha" > "$out.fp.tmp" || { echo "FAIL $name: cannot write fingerprint"; exit 1; }
  $PY -c 'import os, sys; f = open(sys.argv[1], "rb"); os.fsync(f.fileno())' "$out.fp.tmp" || { echo "FAIL $name: fsync"; exit 1; }
  mv "$out.fp.tmp" "$out.fp" || { echo "FAIL $name: cannot publish fingerprint"; exit 1; }
  echo "done $name $(date) $(tail -2 "$out" | head -1)"
done < "$1"
echo "end $(date)"
