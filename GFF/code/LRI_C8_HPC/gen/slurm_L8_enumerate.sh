#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=16G -t 04:00:00
#SBATCH -J c8gen_enum8 -o /expanse/lustre/scratch/zzheng8/temp_project/c8_hpc/gen_work/logs/%x_%j.out
# Stage 2: enumerate the n=9 (L=8) classes with the regression-validated binary.
module purge; module load cpu/0.21.2a gcc/13.3.0 boost/1.86.0
set -eo pipefail
W=/expanse/lustre/scratch/zzheng8/temp_project/c8_hpc/gen_work; cd "$W"; mkdir -p out8
hostname; date
/usr/bin/time -f "enumerate L=8 wall %e s maxrss %M KB" bin/enumerate_classes 9 out8/classes8.txt 2> out8/enum_L8.err; tail -5 out8/enum_L8.err
head -1 out8/classes8.txt; date
