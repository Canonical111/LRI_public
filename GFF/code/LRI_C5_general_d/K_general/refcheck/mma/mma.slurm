#!/bin/bash
#SBATCH --partition=amdq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:30:00
#SBATCH --output=%x-%j.out
cd $HOME/kgen_refcheck/mma
/cm/shared/apps/Wolfram/Wolfram/15.0/Executables/wolframscript -file perspin_check_arg.wls "$1" "$2"
