#!/bin/bash
#SBATCH --nodes=1
#SBATCH -J c2aux
# c2aux: auxiliary inputs of the arbitrary-N continuum analysis (PLAN_ANALYSIS.md
# M1/M2/M2b): code/continuum/aux_inputs.py on node-local scratch, staged from ONE
# package tarball whose sha256 is checked twice. Hand-written job (not the
# package's sitekit layer), so its job names use the prefix c2aux-, never the
# package prefixes lri_c2_ / c2ham-.
#
# Submit from the verified code copy (make_tarball.sh --upload), e.g. on Expanse:
#   L=<SCRATCH>/temp_project/lri_c2
#   sbatch -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=4 --mem=64G \
#     -t 02:00:00 -J c2aux-m1m2b -o $L/logs/%x_%j.out \
#     --export=ALL,C2AUX_PKG_TAR=$L/pkg/<name>.tar,C2AUX_PKG_SHA256=<sha256>,\
#   C2AUX_ENV=$HOME/envs/lri_c2/py3.13.5,C2AUX_DEST_ROOT=$L/continuum_aux,C2AUX_WORKERS=4 \
#     code/continuum/aux_job.sbatch
# On symmetry (whole nodes; only when the partition has idle nodes; amdq first, defq fallback):
#   export PATH=$PATH:/cm/shared/apps/slurm/current/bin; L=<SCRATCH>/lri_c2
#   sbatch -p defq --nodes=1 --exclusive --mem=170G -t 02:00:00 -J c2aux-m1m2b -o $L/logs/%x_%j.out \
#     --export=ALL,C2AUX_PKG_TAR=$L/pkg/<name>.tar,C2AUX_PKG_SHA256=<sha256>,\
#   C2AUX_ENV=$HOME/envs/lri_c2/py3.13-mamba,C2AUX_MODULES=python/3.13-mamba,C2AUX_NODE_SCRATCH=/local1/$USER,\
#   C2AUX_DEST_ROOT=$L/continuum_aux,C2AUX_WORKERS=8 code/continuum/aux_job.sbatch
#
# Output: $C2AUX_DEST_ROOT/c2aux_<job id>/ (aux_k*_a*.json, aux_receipt.json,
# env_check.json, STAGE_INFO.json, SHA256SUMS), published atomically (copied to a
# hidden partial directory, verified, renamed).
# Deliberately no `set -u` (it breaks /etc/bashrc on Expanse) and no `set -e`:
# every step checks its status. Exit codes: 64 usage, 65 wrong package,
# 73 cannot create, 74 staging/checksum/publish I/O, 78 environment mismatch.
set -o pipefail
umask 022
log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }
die() { log "FATAL($1): $2" >&2; exit "$1"; }
[[ -n "${SLURM_JOB_ID:-}" ]] || die 64 "submit with sbatch"
for v in C2AUX_PKG_TAR C2AUX_PKG_SHA256 C2AUX_ENV C2AUX_DEST_ROOT C2AUX_WORKERS; do
    [[ -n "${!v:-}" ]] || die 64 "$v is not set"
done
[[ "$C2AUX_WORKERS" =~ ^[1-9][0-9]*$ ]] && (( C2AUX_WORKERS <= 64 )) || die 64 "C2AUX_WORKERS must be 1..64"

# ---- stage: ONE tarball -> node-local scratch, verified twice
T0=$(date +%s)
STAGE=${C2AUX_NODE_SCRATCH:-/scratch/$USER}/job_$SLURM_JOB_ID
mkdir -p "$STAGE" || die 73 "cannot create $STAGE"
TAR=$(basename "$C2AUX_PKG_TAR")
cp "$C2AUX_PKG_TAR" "$C2AUX_PKG_TAR.sha256" "$STAGE/" || die 74 "cannot copy $C2AUX_PKG_TAR(.sha256)"
( cd "$STAGE" && sha256sum -c --quiet "$TAR.sha256" ) || die 74 "tarball checksum mismatch"
[[ "$(sha256sum "$STAGE/$TAR" | cut -d' ' -f1)" == "$C2AUX_PKG_SHA256" ]] \
    || die 65 "staged tarball is not the submitted one (C2AUX_PKG_SHA256)"
tar -xf "$STAGE/$TAR" -C "$STAGE" || die 74 "cannot extract $TAR"
PKG=$STAGE/lri_c2
( cd "$PKG" && sha256sum -c --quiet STAGE_MANIFEST.sha256 ) || die 74 "staged files differ from STAGE_MANIFEST.sha256"
rm -f "$STAGE/$TAR"
cmp -s "$0" "$PKG/code/continuum/aux_job.sbatch" || die 64 "batch script $0 differs from the staged copy"
log "staged $TAR into $PKG ($(( $(date +%s) - T0 )) s)"

# ---- environment: pinned versions, one BLAS/OpenMP thread per process
if [[ -n "${C2AUX_MODULES:-}" ]]; then          # symmetry: python/3.13-mamba (the base of its venv)
    source /etc/profile.d/modules.sh 2>/dev/null || die 78 "cannot initialise environment modules"
    # shellcheck disable=SC2086
    module load ${C2AUX_MODULES//:/ } || die 78 "module load ${C2AUX_MODULES//:/ } failed"
fi
PY=$C2AUX_ENV/bin/python
[[ -x "$PY" ]] || die 78 "python environment missing: $C2AUX_ENV"
unset PYTHONPATH PYTHONHOME VIRTUAL_ENV
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
"$PY" "$PKG/cluster/sitekit/jobtools.py" check-env --requirements "$PKG/requirements-tested.txt" \
    --out "$STAGE/env_check.json" > /dev/null || die 78 "installed versions differ from requirements-tested.txt"
log "host=$(hostname) cpu=$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ //') cpus=${SLURM_CPUS_ON_NODE:-?} mem_MB=${SLURM_MEM_PER_NODE:-?} workers=$C2AUX_WORKERS"

# ---- compute
OUT=$STAGE/out
mkdir -p "$OUT" || die 73 "cannot create $OUT"
T1=$(date +%s)
"$PY" "$PKG/code/continuum/aux_inputs.py" run --out "$OUT" --workers "$C2AUX_WORKERS"
rc=$?
(( rc == 0 )) || die "$rc" "aux_inputs.py failed (exit $rc)"
log "compute done ($(( $(date +%s) - T1 )) s)"
cp "$STAGE/env_check.json" "$PKG/STAGE_INFO.json" "$OUT/" || die 74 "cannot copy receipts"
( cd "$OUT" && find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%P\0' | LC_ALL=C sort -z \
    | xargs -0 sha256sum > SHA256SUMS ) || die 74 "cannot write SHA256SUMS"

# ---- publish atomically on the shared filesystem
DEST=$C2AUX_DEST_ROOT/c2aux_$SLURM_JOB_ID
PART=$C2AUX_DEST_ROOT/.c2aux_$SLURM_JOB_ID.partial
[[ -e "$DEST" ]] && die 74 "$DEST already exists"
mkdir -p "$PART" || die 73 "cannot create $PART"
cp "$OUT"/* "$PART/" || die 74 "cannot copy outputs to $PART"
( cd "$PART" && sha256sum -c --quiet SHA256SUMS ) || die 74 "published copy does not verify"
mv "$PART" "$DEST" || die 74 "cannot rename $PART"
log "PUBLISHED $DEST ($(ls "$DEST" | wc -l) files); total $(( $(date +%s) - T0 )) s"
