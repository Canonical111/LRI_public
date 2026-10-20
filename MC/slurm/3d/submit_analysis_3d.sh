#!/bin/bash
# Queue the 3D post-processing behind the production arrays: pack (SNAP = pack job id) -> analysis array (afterok) -> evaluation (afterany).
set -u
cd <CODE_3D>/cluster
DEPS=${DEPS:?afterany dependency list: the production array job ids, e.g. <JOB_A>:<JOB_A_CONT>}
P=$(sbatch --parsable --dependency=afterany:$DEPS prod_pack_3d.slurm) || exit 1; echo "pack job $P (afterany:$DEPS) -> snapshot SNAP=$P"
A=$(sbatch --parsable --dependency=afterok:$P --export=ALL,SNAP=$P prod_analysis_3d.slurm) || exit 1; echo "analysis array $A (afterok:$P, SNAP=$P)"
E=$(sbatch --parsable --dependency=afterany:$A --export=ALL,SNAP=$P prod_evaluate_3d.slurm) || exit 1; echo "evaluation job $E (afterany:$A, SNAP=$P)"
echo "$(date) post-processing queued: pack $P, analysis $A, evaluate $E, SNAP=$P" >> <SCRATCH>/lri3d/prod3d/logs/submitted.txt
squeue -u $USER -h -o "%i %j %T %M %P %E" | grep -E "lri3d_(pack|an|eval)"
