#!/bin/bash
#SBATCH --job-name=integ-m3sc
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --exclude=cn112
#SBATCH --mem=150G
#SBATCH --time=12:00:00
#SBATCH --output=<SCRATCH>/lri_integ/logs/%x_%j.out
# Independent sector check (MSC-011). usage: sbatch [--export=ALL,SC=./sc_<build>] sector_check.sbatch OUTDIR "SECTORS" Kre Kim LEVEL [extra checker args]
# Each sector result goes to OUTDIR/sec<NNN>.txt (temporary file, then rename) with OUTDIR/sec<NNN>.txt.fp holding the
# runner fingerprint (checker sha256, build, input sha256, exact arguments) and the output sha256 (fix round 2, MSC-013).
# An existing result is reused only if fingerprint, output hash and completeness check out; otherwise the job stops.
cd <SCRATCH>/lri_integ/code/m3 || { echo "FAIL: cannot cd"; exit 1; }
SC=${SC:-./sc}
[ -x "$SC" ] || { echo "FAIL: checker $SC missing"; exit 1; }
out=$1; secs=$2; Kre=$3; Kim=$4; lev=$5; shift 5
mkdir -p "$out" || { echo "FAIL: mkdir $out"; exit 1; }
scsha=$(sha256sum "$SC" | cut -d' ' -f1) || exit 1
build=$("$SC" -version) || { echo "FAIL: checker has no build id"; exit 1; }
insha=$(sha256sum n3.txt | cut -d' ' -f1) || exit 1
export OMP_NUM_THREADS=40 OMP_PROC_BIND=spread
echo "node $(hostname) start $(date) checker $SC sha256 $scsha build $build input sha256 $insha"
for s in $secs; do
  f=$(printf "%s/sec%03d.txt" "$out" "$s")
  fp="checker_sha256=$scsha build=$build input_sha256=$insha args=n3.txt $s $Kre $Kim -level $lev $*"
  if [ -e "$f" ] || [ -e "$f.fp" ]; then
    if [ -f "$f" ] && [ -f "$f.fp" ] && [ "$(head -1 "$f.fp")" = "$fp" ] \
       && [ "$(sed -n 2p "$f.fp")" = "output_sha256=$(sha256sum "$f" | cut -d' ' -f1)" ] \
       && grep -q '^A00 ' "$f" && grep -q '^# complete' "$f" && grep -q "^# fingerprint input_sha256 $insha build $build " "$f"; then
      echo "reuse $f (fingerprint matches)"; continue
    fi
    echo "FAIL: $f exists with a different or missing fingerprint; choose a new output directory"; exit 1
  fi
  t0=$(date +%s)
  "$SC" n3.txt "$s" "$Kre" "$Kim" -level "$lev" "$@" > "$f.tmp" 2> "$f.err"
  rc=$?
  if [ $rc -ne 0 ] || ! grep -q '^A00 ' "$f.tmp" || ! grep -q '^# complete' "$f.tmp"; then echo "FAIL sector $s (exit $rc), see $f.err"; exit 1; fi
  mv "$f.tmp" "$f" || { echo "FAIL: cannot publish $f"; exit 1; }
  printf '%s\noutput_sha256=%s\n' "$fp" "$(sha256sum "$f" | cut -d' ' -f1)" > "$f.fp.tmp" && mv "$f.fp.tmp" "$f.fp" || { echo "FAIL: fingerprint"; exit 1; }
  echo "sector $s done in $(( $(date +%s) - t0 )) s"
done
echo "end $(date)"
