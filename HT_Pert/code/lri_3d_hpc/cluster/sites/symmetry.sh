# symmetry (Perimeter) site profile; sourced by cluster/env.sh, never executed.
# Verified 2026-10-08: amdq nodes cn083-110 are AMD EPYC 7532 (2 x 32 cores, 8 NUMA nodes,
# 256000 MB, no SMT); cn112 (amdq/largememq) is a different AMD model with AVX-512 and is
# excluded by default. BeeGFS flock is node-local, so locks live on NFS /home
# (local_lock=none: flock goes to the server and is cluster-wide). Node-local disk: /local1
# (84 GB). System g++ 11.4 and Debian OpenMPI 4.1.2 (/usr/bin/mpicc); no modules needed.
HT3D_SITE=symmetry
HT3D_DATA=${HT3D_DATA:-/mnt/beegfs/$USER/ht3d_pert}
HT3D_VENV=${HT3D_VENV:-$HT3D_DATA/venv-py3129-np253-sp1170-nb0680}
HT3D_LOCK_ROOT=${HT3D_LOCK_ROOT:-$HOME/ht3d_pert/locks}  # NFS: flock is cluster-wide
HT3D_ACCOUNT=${HT3D_ACCOUNT:-}
HT3D_MODULES=""
HT3D_MPI_LAUNCHERS="mpirun;srun --mpi=pmix;srun --mpi=pmi2"   # only mpirun works (probe 571617)

ht3d_site_init() {
  case ":$PATH:" in *:/cm/shared/apps/slurm/current/bin:*) ;;
    *) PATH=/cm/shared/apps/slurm/current/bin:$PATH; export PATH;; esac
  command -v sbatch >/dev/null 2>&1 || { echo "env: no Slurm commands on PATH" >&2; return 70; }
  return 0
}

ht3d_node_scratch() {   # created by the job script, removed by its EXIT trap
  echo "/local1/$USER/ht3d_${SLURM_JOB_ID:?}"
}
