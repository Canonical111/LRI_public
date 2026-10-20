"""MPI launch prefixes for the site launchers named in sites/<site>.sh (HT3D_MPI_LAUNCHERS).

  srun --mpi=<plugin>   direct launch; --kill-on-bad-exit=1 ends the step when one rank dies
  mpirun                Open MPI's ORTE inside the allocation (plm/slurm starts the daemons);
                        an abnormal rank exit terminates the job
symmetry's Debian Open MPI 4.1.2 has neither a usable PMIx match for Slurm's pmix_v3 plugin
nor an s2 (PMI2) component, so only mpirun gives a real world there (probe 571617).
"""
import shlex


def prefix(launcher, *, nodes, per_node, cpus, bind):
    """Command prefix that starts nodes*per_node ranks, per_node per node, cpus cores each."""
    parts = shlex.split(launcher)
    ntasks = int(nodes)*int(per_node)
    if parts and parts[0] == 'srun':
        return parts + ['--kill-on-bad-exit=1', f'--nodes={nodes}', f'--ntasks={ntasks}',
                        f'--ntasks-per-node={per_node}', f'--cpus-per-task={cpus}',
                        '--cpu-bind=cores' if bind else '--cpu-bind=none']
    if parts == ['mpirun']:
        mapping = f'ppr:{per_node}:node:PE={cpus}' if bind else f'ppr:{per_node}:node'
        return parts + ['-np', str(ntasks), '--map-by', mapping, '--bind-to', 'core' if bind else 'none']
    raise ValueError(f'unsupported MPI launcher {launcher!r}')
