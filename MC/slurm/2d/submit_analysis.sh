#!/bin/bash
# Queue pack -> analysis array -> evaluation behind the production array and its checked continuation (DEPS=<jobA>:<jobA_cont>).
DEPS=${DEPS:?afterany dependency list: the production array job ids, e.g. <JOB_A>:<JOB_A_CONT>}
set -u
cd <CODE_2D>
P=$(sbatch --parsable --dependency=afterany:$DEPS prod_pack.slurm) || exit 1; echo "pack job $P (afterany:$DEPS)"
A=$(sbatch --parsable --dependency=afterok:$P prod_analysis.slurm) || exit 1; echo "analysis array $A (afterok:$P)"
E=$(sbatch --parsable --dependency=afterany:$A prod_evaluate.slurm) || exit 1; echo "evaluation job $E (afterany:$A)"
squeue -u $USER -h -o "%i %j %T %M %P %E" | grep -E "lri2d_(pack|an|eval)"
