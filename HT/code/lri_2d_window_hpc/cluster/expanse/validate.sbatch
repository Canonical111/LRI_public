#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 02:00:00
#SBATCH -J ht2d-validate
# usage: sbatch -o ROOT/logs/%x_%j.out validate.sbatch ROOT RELEASE_JSON ENV_PYTHON
# Stages the release from $HOME into node-local scratch (no Lustre), verifies tar and
# per-file sha256, then writes ROOT/validation/<jobid>/receipt.json.
set -o pipefail
module purge >/dev/null 2>&1; module load cpu/0.15.4 slurm/expanse/23.02.7 >/dev/null 2>&1
ROOT=$1; REL=$2; ENVPY=$3
# Snapshot the release record, tarball and manifest ONCE; everything below (hash checks, extraction,
# tests and the receipt's hashes) uses only these snapshots (IR3-01).
STAGE=/scratch/${USER}/job_${SLURM_JOB_ID}; mkdir -p "$STAGE"
cp -- "$REL" "$STAGE/release.json" || exit 74
read -r TAR TARSHA MAN MANSHA < <(/usr/bin/python3 -I -c '
import json,sys;r=json.load(open(sys.argv[1]));print(r["tar"],r["tar_sha256"],r["manifest"],r["manifest_sha256"])' "$STAGE/release.json") || exit 74
cp -- "$TAR" "$STAGE/release.tar" && cp -- "$MAN" "$STAGE/release.sha256" || exit 74
echo "${TARSHA}  ${STAGE}/release.tar" | sha256sum -c --quiet - || { echo "tar sha256 mismatch"; exit 74; }
echo "${MANSHA}  ${STAGE}/release.sha256" | sha256sum -c --quiet - || { echo "manifest sha256 mismatch"; exit 74; }
tar -xf "$STAGE/release.tar" -C "$STAGE" && ( cd "$STAGE" && sha256sum -c --quiet release.sha256 ) || { echo "staging corrupted"; exit 74; }
export NUMBA_CACHE_DIR=$STAGE/numba; mkdir -p "$NUMBA_CACHE_DIR"
OUT=$ROOT/validation/$SLURM_JOB_ID; mkdir -p "$OUT"
echo "host $(hostname) release $TAR env $ENVPY"
"$ENVPY" -E -s "$STAGE/ht2d/cluster/expanse/validate.py" --tar "$STAGE/release.tar" --manifest "$STAGE/release.sha256" --tar-path "$TAR" \
   --workdir "$OUT/work" --receipt "$OUT/receipt.json" --threads "${SLURM_CPUS_PER_TASK:-4}"
