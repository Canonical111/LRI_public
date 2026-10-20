#!/usr/bin/env python3
"""The only supported way to submit HT3D jobs on Expanse and symmetry (login node, light work).

Run from a verified reference copy of a release (see RUNBOOK.md) with cluster/env.sh sourced:

  submit.py plan --cutoff L                         preflight counts and suggested resources
  submit.py validate [--partition P] [--time T]     single-node receipt for this release
  submit.py validate-mpi --store S --gates G [--nodes 2 --ranks-per-node 2 --cpus 4 ...]
  submit.py init NAME --receipt R [--mpi-receipt M] freeze a campaign (refuses an existing one)
  submit.py run NAME --cutoff L --stages S1,S2,... --cpus C --mem M --time T [--partition P]
                [--lanes K] [--threads T] [--blas-threads B] [--array N] [--solve-cutoffs ...]
                [--schemes ...] [--after JOBID,...] [--exclude NODES] [--dry-run]
  submit.py solve-mpi NAME --cutoff L --nodes N --ranks-per-node R --cpus C --time T [...]
  submit.py status NAME --cutoff L [--solve-cutoffs ...]

Every sbatch call gets all resources on its command line, an environment scrubbed of
SBATCH_*/SLURM_*/thread/Python/MPI variables (they override #SBATCH lines or leak into the job),
explicit HT3D_EXPECT_* values that the job checks against its real allocation, absolute log
paths, --no-requeue and --kill-on-invalid-dep=yes. Campaign submissions hold a mkdir mutex on
the campaign directory, refuse while any live job of the same campaign and cutoff is not
named in --after (a failed squeue refuses too), refuse a campaign frozen for another release
or site, and append to <campaign>/ledger.jsonl. Numbers, times and names are checked as exact
strings before use.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT/'code'), str(ROOT/'vendor'), str(HERE)]

LIVE = ('PENDING', 'RUNNING', 'REQUEUED', 'SUSPENDED', 'CONFIGURING', 'COMPLETING', 'RESIZING',
        'STAGE_OUT', 'SIGNALING', 'REQUEUE_HOLD', 'REQUEUE_FED', 'RESV_DEL_HOLD', 'STOPPED')
SCRUB = ('SBATCH_', 'SQUEUE_', 'SLURM_', 'SALLOC_', 'SRUN_', 'HT3D_EXPECT_', 'OMP_', 'GOMP_', 'OPENBLAS_',
         'MKL_', 'BLIS_', 'NUMBA_', 'I_MPI_', 'OMPI_', 'PMI_', 'PMIX_', 'PYTHON', 'CONDA_', 'UCX_',
         'TMPDIR')   # env.sh points TMPDIR at login-node scratch; slurmstepd would try to use it
# Partitions per site: the CPU model behind each (all nodes), whether it is whole-node, and
# the memory a job may request per node.
PARTITIONS = {
    'expanse': {
        'shared': dict(cpu='AMD EPYC 7742 64-Core Processor', whole_node=False, max_cpus=128, max_mem_gb=243),
        'compute': dict(cpu='AMD EPYC 7742 64-Core Processor', whole_node=True, max_cpus=128, max_mem_gb=240),
        'large-shared': dict(cpu='AMD EPYC 7742 64-Core Processor', whole_node=False, max_cpus=128, max_mem_gb=2000),
        'debug': dict(cpu='AMD EPYC 7742 64-Core Processor', whole_node=False, max_cpus=128, max_mem_gb=243),
    },
    'symmetry': {
        'amdq': dict(cpu='AMD EPYC 7532 32-Core Processor', whole_node=True, max_cpus=64, max_mem_gb=245,
                     exclude='cn112'),
        'amddebugq': dict(cpu='AMD EPYC 7532 32-Core Processor', whole_node=True, max_cpus=64, max_mem_gb=245,
                          exclude='cn112'),
        'amdpreq': dict(cpu='AMD EPYC 7532 32-Core Processor', whole_node=True, max_cpus=64, max_mem_gb=245,
                        exclude='cn112'),
    },
}
NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$')
POS = re.compile(r'^[1-9][0-9]{0,5}$')
EVEN = re.compile(r'^(0|[1-9][0-9]?)$')
MEM = re.compile(r'^[1-9][0-9]{0,4}G$')
TIME = re.compile(r'^([0-9]{1,2}-)?[0-9]{1,2}:[0-9]{2}:[0-9]{2}$')
JOBS = re.compile(r'^[0-9]+(,[0-9]+)*$')
NODES = re.compile(r'^[A-Za-z0-9,\[\]-]+$')


def die(message, code=2):
    print(f'submit: {message}', file=sys.stderr)
    sys.exit(code)


def exact(pattern, label):
    def parse(text):
        if not pattern.fullmatch(text):
            raise argparse.ArgumentTypeError(f'{label}: {text!r} is not an exact {pattern.pattern}')
        return text
    return parse


def even_cutoff(text):
    exact(EVEN, 'cutoff')(text)
    if int(text) % 2:
        raise argparse.ArgumentTypeError(f'cutoff {text} is odd')
    return int(text)


def site():
    value = os.environ.get('HT3D_SITE')
    if value not in PARTITIONS:
        die('source cluster/env.sh first (HT3D_SITE unset or unknown)')
    return value


def release():
    """This reference copy's release: verified RELEASE.sha256 and the installed tarball."""
    sha = (ROOT/'GIT_SHA').read_text().strip() if (ROOT/'GIT_SHA').exists() else None
    if not sha:
        die(f'{ROOT} is not an installed release (no GIT_SHA); see RUNBOOK.md')
    check = subprocess.run(['sha256sum', '-c', '--quiet', '--strict', 'RELEASE.sha256'], cwd=ROOT,
                           capture_output=True, text=True)
    if check.returncode:
        die(f'reference copy {ROOT} does not verify: {check.stdout[-300:]}{check.stderr[-300:]}')
    tar = Path(os.environ['HT3D_DATA'])/'releases'/f'{sha[:12]}.tar'
    record = Path(str(tar) + '.sha256')
    if not tar.is_file() or not record.is_file():
        die(f'no installed tarball {tar} (+ .sha256)')
    want = record.read_text().split()[0]
    have = hashlib.sha256(tar.read_bytes()).hexdigest()
    if have != want:
        die(f'{tar} sha256 {have} != recorded {want}')
    # The tarball must be this very release, member by member: every regular file must be listed
    # in the verified reference copy's RELEASE.sha256 with the same sha256 (RELEASE.sha256 itself
    # byte-equal), each exactly once, nothing else but directories, and nothing listed missing.
    import tarfile
    listing = {}
    for line in (ROOT/'RELEASE.sha256').read_text().splitlines():
        digest, _, name = line.partition('  ')
        listing[name] = digest
    seen = set()
    with tarfile.open(tar) as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.isfile() or member.name in seen:
                die(f'{tar}: unexpected or duplicate member {member.name}')
            seen.add(member.name)
            data = archive.extractfile(member).read()
            if member.name == 'RELEASE.sha256':
                if data != (ROOT/'RELEASE.sha256').read_bytes():
                    die(f'{tar}: RELEASE.sha256 differs from the reference copy {ROOT}')
            elif listing.get(member.name) != hashlib.sha256(data).hexdigest():
                die(f'{tar}: member {member.name} is not the reference copy\'s')
    if seen != set(listing) | {'RELEASE.sha256'}:
        die(f'{tar}: members missing: {sorted(set(listing) - seen)[:5]}')
    fingerprint = hashlib.sha256((ROOT/'RELEASE.sha256').read_bytes()).hexdigest()
    return dict(git_sha=sha, tar=str(tar), tar_sha256=want, fingerprint=fingerprint)


def squeue_live():
    """{job_id: (name, state)} of this user's non-terminal jobs, keyed by the submitted id
    (an array's parent id stands for all its elements, which is what sbatch returned and what
    --dependency on it covers); any query failure refuses."""
    try:
        proc = subprocess.run(['squeue', '-h', '-u', os.environ['USER'], '--states=all', '-o', '%F|%j|%T'],
                              capture_output=True, text=True, timeout=120, env=scrubbed_env({}))
    except (OSError, subprocess.TimeoutExpired) as exc:
        die(f'squeue failed ({exc}); not submitting')
    if proc.returncode:
        die(f'squeue failed ({proc.stderr.strip()}); not submitting')
    out = {}
    for line in proc.stdout.splitlines():
        parent, name, state = line.split('|', 2)
        if state.split()[0] in LIVE:
            out[parent] = (name, state)
    return out


def scrubbed_env(extra):
    # SLURM_CONF locates the cluster configuration (Expanse's slurm module sets it); keep it.
    env = {k: v for k, v in os.environ.items() if not k.startswith(SCRUB) or k == 'SLURM_CONF'}
    env = {k: v for k, v in env.items() if not (k.startswith('HT3D_') and k not in
           ('HT3D_SITE', 'HT3D_DATA', 'HT3D_VENV', 'HT3D_LOCK_ROOT', 'HT3D_ACCOUNT'))}
    env.update({k: str(v) for k, v in extra.items()})
    return env


@contextlib.contextmanager
def mutex(directory):
    lock = Path(directory)/'.submit.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        owner = (lock/'owner').read_text() if (lock/'owner').exists() else '?'
        die(f'another submission holds {lock} ({owner.strip()}); remove it only if no submit.py is running')
    try:
        (lock/'owner').write_text(f'{socket.gethostname()} {os.getpid()} {time.strftime("%Y-%m-%dT%H:%M:%S%z")}\n')
        yield
    finally:
        for item in lock.iterdir():
            item.unlink()
        lock.rmdir()


def sbatch(args, script, extra_env, dry_run):
    command = ['sbatch', '--parsable'] + args + [str(script)]
    print('$ ' + ' '.join(shlex.quote(c) for c in command))
    for k in sorted(extra_env):
        print(f'  {k}={extra_env[k]}')
    if dry_run:
        return None
    proc = subprocess.run(command, capture_output=True, text=True, env=scrubbed_env(extra_env), timeout=300)
    if proc.returncode:
        die(f'sbatch failed: {proc.stderr.strip()}')
    job = proc.stdout.strip().split(';')[0]
    if not job.isdigit():
        die(f'unexpected sbatch output {proc.stdout!r}')
    return job


def resources(site_name, partition, nodes, ntasks, cpus, mem, time_limit, exclude):
    """sbatch resource arguments, the HT3D_EXPECT_* values and the partition record.
    Whole-node partitions always get every core of each node (cpus=None fills it in);
    elsewhere cpus is required."""
    spec = PARTITIONS[site_name].get(partition)
    if spec is None:
        die(f'partition {partition} is not allowed on {site_name} (allowed: {sorted(PARTITIONS[site_name])})')
    if int(ntasks) % int(nodes):
        die(f'{ntasks} tasks do not divide evenly over {nodes} nodes')
    per_node = int(ntasks)//int(nodes)
    if cpus is None:
        if not spec['whole_node']:
            die(f'--cpus is required on {partition}')
        if spec['max_cpus'] % per_node:
            die(f'{per_node} tasks per node do not divide the {spec["max_cpus"]} cores of {partition}')
        cpus = str(spec['max_cpus']//per_node)
    if spec['whole_node'] and int(cpus)*per_node != spec['max_cpus']:
        die(f'{partition} allocates whole nodes: tasks per node x cpus must be {spec["max_cpus"]}, '
            f'not {per_node} x {cpus}')
    if int(cpus)*per_node > spec['max_cpus']:
        die(f'{per_node} tasks x {cpus} cpus exceed {spec["max_cpus"]} per node on {partition}')
    if int(mem[:-1]) > spec['max_mem_gb']:
        die(f'--mem {mem} exceeds {spec["max_mem_gb"]}G on {partition}')
    args = [f'--partition={partition}', f'--nodes={nodes}', f'--ntasks={ntasks}',
            f'--cpus-per-task={cpus}', f'--mem={mem}', f'--time={time_limit}', '--no-requeue',
            '--kill-on-invalid-dep=yes', '--export=ALL']
    args.append(f'--ntasks-per-node={per_node}')
    if spec['whole_node']:
        args.append('--exclusive')
    if os.environ.get('HT3D_ACCOUNT'):
        args.append(f'--account={os.environ["HT3D_ACCOUNT"]}')
    # Site exclusions (symmetry cn112, another CPU model) always apply; --exclude adds to them.
    excluded = ','.join(x for x in (spec.get('exclude'), exclude) if x)
    if excluded:
        args.append(f'--exclude={excluded}')
    expect = dict(HT3D_EXPECT_PARTITION=partition, HT3D_EXPECT_NODES=nodes, HT3D_EXPECT_NTASKS=ntasks,
                  HT3D_EXPECT_CPUS=cpus, HT3D_EXPECT_MEM_MB=int(mem[:-1])*1024)
    return args, expect, spec


@contextlib.contextmanager
def account_guard(site_name, partition, new_jobs):
    """Expanse user rule: at most 22 queued+running compute jobs on the account (array
    elements counted one by one, this submission included), checked and submitted under a
    data-root mutex so two of our submissions cannot both pass the check."""
    if not (site_name == 'expanse' and partition == 'compute'):
        yield
        return
    with mutex(Path(os.environ['HT3D_DATA'])/'account'):
        try:
            proc = subprocess.run(['squeue', '-h', '-r', '-A', os.environ.get('HT3D_ACCOUNT') or 'yun124',
                                   '-p', 'compute', '-t', 'PENDING,RUNNING,CONFIGURING,COMPLETING,SUSPENDED',
                                   '-o', '%i'], capture_output=True, text=True, timeout=120, env=scrubbed_env({}))
        except (OSError, subprocess.TimeoutExpired) as exc:
            die(f'squeue -A failed ({exc}); not submitting')
        if proc.returncode:
            die('squeue -A failed; not submitting')
        current = len(proc.stdout.split())
        if current + int(new_jobs) > 22:
            die(f'account has {current} compute jobs; {new_jobs} more would exceed 22 '
                '(leave 10 of 32 normal-QOS slots free)')
        yield


def ledger(campaign_dir, entry):
    path = Path(campaign_dir)/'ledger.jsonl'
    with open(path, 'a') as out:
        out.write(json.dumps(entry, sort_keys=True) + '\n')
        out.flush()
        os.fsync(out.fileno())


def ledger_jobs(campaign_dir, cutoff):
    """{job id: array size or None} of this campaign's ledger entries for one cutoff."""
    path = Path(campaign_dir)/'ledger.jsonl'
    if not path.exists():
        return {}
    return {e['job']: (int(e['array']) if e.get('array') else None)
            for e in map(json.loads, path.read_text().splitlines())
            if e.get('cutoff') == cutoff and e.get('job')}


def accounting_state(job, array_size=None):
    """'COMPLETED' only if sacct reports exactly the expected rows (the job itself, or each of
    its array elements <job>_0..<job>_{n-1}) all COMPLETED with exit 0:0; otherwise the
    state(s) seen, or 'UNKNOWN' when sacct fails, misses an element or adds another row."""
    try:
        proc = subprocess.run(['sacct', '-j', job, '-X', '-n', '-P', '-o', 'JobID,State,ExitCode'],
                              capture_output=True, text=True, timeout=120, env=scrubbed_env({}))
    except (OSError, subprocess.TimeoutExpired):
        return 'UNKNOWN'
    rows = [line.split('|') for line in proc.stdout.splitlines() if line.strip()]
    rows = [r for r in rows if len(r) >= 3 and (r[0] == job or r[0].startswith(job + '_'))]
    expected = {job} if array_size is None else {f'{job}_{i}' for i in range(array_size)}
    if proc.returncode or not rows or sorted(r[0] for r in rows) != sorted(expected):
        return 'UNKNOWN' if proc.returncode or not rows else \
            'UNKNOWN(rows ' + ','.join(sorted(r[0] for r in rows)) + ')'
    states = {(r[1].split()[0], r[2]) for r in rows}
    if states == {('COMPLETED', '0:0')}:
        return 'COMPLETED'
    return ','.join(sorted(f'{s}({e})' for s, e in states))


def live_campaign_jobs(campaign_dir, cutoff, live):
    """Live jobs of this campaign and cutoff: by job-name prefix and by ledger job ids."""
    prefix = f'ht3d.{Path(campaign_dir).name}.L{cutoff}.'
    ids = set()
    path = Path(campaign_dir)/'ledger.jsonl'
    if path.exists():
        for line in path.read_text().splitlines():
            entry = json.loads(line)
            if entry.get('cutoff') == cutoff and entry.get('job'):
                ids.add(entry['job'])
    return {job: info for job, info in live.items() if info[0].startswith(prefix) or job in ids}


def load_campaign(name):
    if not NAME.fullmatch(name):
        die(f'campaign name {name!r} must match {NAME.pattern}')
    root = Path(os.environ['HT3D_DATA'])/'campaigns'/name
    path = root/'campaign.json'
    if not path.exists():
        die(f'no campaign {root} (submit.py init first)')
    return root, json.loads(path.read_text())


def check_release(campaign, rel):
    frozen = campaign['release']
    if (any(frozen.get(k) != rel[k] for k in ('fingerprint', 'tar_sha256', 'git_sha'))
            or campaign['site'] != site()):
        die(f'campaign frozen for release {frozen.get("git_sha", "?")[:12]} on {campaign["site"]}; '
            f'this is {rel["git_sha"][:12]} on {site()}')
    from ht3d_stage import lock_filesystem_problem
    problem = lock_filesystem_problem(campaign['site'], campaign['lock_dir'])
    if problem:
        die(problem)


def logdir(root):
    path = Path(root)/'logs'
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------- commands

def cmd_plan(a):
    from ht3d.basis import graph_requirements
    need = graph_requirements(a.cutoff)
    print(json.dumps(need, indent=1))
    print(f"graph arrays {need['graph_array_bytes']/2**30:.3f} GiB; prepare needs roughly 3-6x that "
          'plus projector SVD workspace. See RUNBOOK.md "Sizing" for measured and suggested resources.')


def cmd_validate(a):
    s = site()
    rel = release()
    root = Path(os.environ['HT3D_DATA'])/'validation'
    partition = a.partition or ('shared' if s == 'expanse' else 'amddebugq')
    whole = PARTITIONS[s].get(partition, {}).get('whole_node')
    args, expect, _ = resources(s, partition, '1', '4', None if whole else '4', a.mem, a.time, a.exclude)
    with mutex(root):
        live = squeue_live()
        name = f'ht3d.validate.{rel["git_sha"][:12]}'
        busy = {j: i for j, i in live.items() if i[0] == name}
        if busy:
            die(f'a validation of this release is live: {busy}')
        env = dict(HT3D_SITE=s, HT3D_RELEASE_TAR=rel['tar'], HT3D_RELEASE_SHA256=rel['tar_sha256'],
                   HT3D_EXPECT_FINGERPRINT=rel['fingerprint'], **expect)
        with account_guard(s, partition, 1):
            job = sbatch(args + [f'--job-name={name}', f'--output={logdir(root)}/%x_%j.out',
                                 f'--chdir={root}'], job_script('validate.sbatch'), env, a.dry_run)
        if job:
            with open(root/'submissions.txt', 'a') as out:
                out.write(f'{job} {name} {time.strftime("%Y-%m-%dT%H:%M:%S%z")} validate {partition}\n')
            print(f'submitted {job}; log {root}/logs/{name}_{job}.out; '
                  f'receipt {root}/{rel["git_sha"][:12]}_{job}/receipt.json')


def cmd_validate_mpi(a):
    s = site()
    rel = release()
    root = Path(os.environ['HT3D_DATA'])/'validation'
    if int(a.nodes) < 2:
        die('validate-mpi checks multi-node behaviour: --nodes must be at least 2')
    # symmetry amddebugq allows one node per job, so two-node validation uses amdq.
    partition = a.partition or ('debug' if s == 'expanse' else 'amdq')
    ntasks = str(int(a.nodes)*int(a.ranks_per_node))
    whole = PARTITIONS[s].get(partition, {}).get('whole_node')
    args, expect, _ = resources(s, partition, a.nodes, ntasks, a.cpus or (None if whole else '4'),
                                a.mem, a.time, a.exclude)
    store, gates = Path(a.store).resolve(), Path(a.gates).resolve()
    if not (store/'manifest.json').exists() or not all((gates/f'{x}_c14.json').exists() for x in ('raw', 'consistent')):
        die('--store must be a finished L>=14 store and --gates hold raw_c14.json and consistent_c14.json')
    with mutex(root):
        live = squeue_live()
        name = f'ht3d.validate-mpi.{rel["git_sha"][:12]}'
        if any(i[0] == name for i in live.values()):
            die('a multi-node validation of this release is live')
        env = dict(HT3D_SITE=s, HT3D_RELEASE_TAR=rel['tar'], HT3D_RELEASE_SHA256=rel['tar_sha256'],
                   HT3D_EXPECT_FINGERPRINT=rel['fingerprint'],
                   HT3D_MPI_MODE='validate', HT3D_STORE=store, HT3D_SERIAL_GATES=gates, **expect)
        with account_guard(s, partition, 1):
            job = sbatch(args + [f'--job-name={name}', f'--output={logdir(root)}/%x_%j.out', f'--chdir={root}'],
                         job_script('mpi.sbatch'), env, a.dry_run)
        if job:
            print(f'submitted {job}; log {root}/logs/{name}_{job}.out')


def read_receipt(path, rel, kind):
    data = json.loads(Path(path).read_text())
    if data.get('format') != kind or data.get('passed') is not True:
        die(f'{path} is not a passing {kind}')
    if (data['release'].get('fingerprint') != rel['fingerprint'] or
            data['release'].get('tar_sha256') != rel['tar_sha256'] or data['site'] != site()):
        die(f'{path} is for release {data["release"]["git_sha"][:12]} on {data["site"]}')
    return data


def cmd_init(a):
    s = site()
    rel = release()
    receipt = read_receipt(a.receipt, rel, 'ht3d-receipt-v1')
    partition = receipt['partition']
    spec = PARTITIONS[s].get(partition)
    if spec is None or spec['cpu'] != receipt['cpu_class'].get('model name'):
        die(f'receipt node class {receipt["cpu_class"]} on {partition} is not a known production class')
    mpi = read_receipt(a.mpi_receipt, rel, 'ht3d-mpi-receipt-v1') if a.mpi_receipt else None
    from ht3d_stage import environment_identity
    if not (receipt.get('environment') or {}).get('fingerprint'):
        die(f'{a.receipt} records no environment fingerprint; validate again with this release')
    if environment_identity()[1] != receipt['environment']['fingerprint']:
        die('this login environment differs from the one the receipt validated (HT3D_VENV, packages, compiler)')
    if mpi and (mpi.get('environment') or {}).get('fingerprint') != receipt['environment']['fingerprint']:
        die(f'{a.mpi_receipt} was not made in the environment of {a.receipt}; validate MPI again')
    if not NAME.fullmatch(a.name):
        die(f'campaign name must match {NAME.pattern}')
    root = Path(os.environ['HT3D_DATA'])/'campaigns'/a.name
    if root.exists():
        die(f'{root} exists; a campaign is frozen once created')
    lock_root = str(Path(os.environ['HT3D_LOCK_ROOT']).resolve())
    if receipt.get('lock_root') != lock_root:
        die(f'HT3D_LOCK_ROOT {lock_root} is not the lock root the receipt validated ({receipt.get("lock_root")})')
    from ht3d_stage import lock_filesystem_problem
    problem = lock_filesystem_problem(s, Path(lock_root)/a.name)
    if problem:
        die(problem)
    root.mkdir(parents=True)
    for sub in ('prepared', 'stores'):
        (root/sub).mkdir()
        if s == 'expanse':   # progressive layout: small files one stripe, multi-GB arrays eight
            subprocess.run(['lfs', 'setstripe', '-E', '64M', '-c', '1', '-E', '-1', '-c', '8', '-S', '16M',
                            str(root/sub)], check=False)
    campaign = dict(format='ht3d-campaign-v1', name=a.name, site=s, created=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                    release=rel, order=8, degree=6, dtype='longdouble',
                    lock_dir=str(Path(os.environ['HT3D_LOCK_ROOT'])/a.name),
                    cpu_class=receipt['cpu_class'], receipt=dict(path=str(Path(a.receipt).resolve()),
                                                                 job=receipt['job'], partition=partition,
                                                                 store_L14_value_fingerprint=receipt.get(
                                                                     'store_L14_value_fingerprint')),
                    environment=receipt['environment'],
                    mpi_launcher=mpi['mpi_launcher'] if mpi else None,
                    mpi_receipt=str(Path(a.mpi_receipt).resolve()) if mpi else None,
                    no_layout_cache=bool(a.no_layout_cache))
    (root/'campaign.json').write_text(json.dumps(campaign, indent=1) + '\n')
    print(f'campaign {root} frozen: release {rel["git_sha"][:12]}, cpu class {receipt["cpu_class"]}, '
          f'MPI launcher {campaign["mpi_launcher"]}')


def cmd_run(a):
    s = site()
    rel = release()
    root, campaign = load_campaign(a.name)
    check_release(campaign, rel)
    from ht3d_stage import STAGES, stage_status
    stages = a.stages.split(',')
    if any(x not in STAGES for x in stages) or len(set(stages)) != len(stages):
        die(f'--stages must be distinct names from {",".join(STAGES)}')
    partition = a.partition or ('shared' if s == 'expanse' else 'amdq')
    spec = PARTITIONS[s].get(partition)
    if 'prepare' in stages and spec and spec['cpu'] != campaign['cpu_class'].get('model name'):
        die(f'prepare must run on the campaign CPU class {campaign["cpu_class"]}, not {partition}')
    if a.array and (len(stages) != 1 or stages[0] not in ('images', 'matrix')):
        # matrix tasks read every particle sector's images: submit the matrix array with
        # --after <image array> so the whole image array is a barrier
        die('--array takes exactly one stage, images or matrix')
    args, expect, spec = resources(s, partition, '1', '1', a.cpus, a.mem, a.time, a.exclude)
    cpus = expect['HT3D_EXPECT_CPUS']
    threads = a.threads or cpus
    if int(threads) > int(cpus) or int(a.blas_threads) > int(cpus) or int(a.lanes) > int(cpus):
        die('--threads, --blas-threads and --lanes must not exceed the job\'s cpus')
    status = stage_status(root, a.cutoff, a.schemes, [int(c) for c in a.solve_cutoffs] if a.solve_cutoffs else None)
    # An explicitly requested verify always runs: it is a fresh integrity check, and an old
    # marker says nothing about the arrays' current bytes.
    todo = [x for x in stages if status.get(x) != 'done' or x == 'verify']
    print(f'status L{a.cutoff}: {json.dumps(status)}')
    if not todo:
        print('nothing to do: every requested stage is complete')
        return
    tag = '+'.join(todo)
    name = f'ht3d.{a.name}.L{a.cutoff}.{tag}'
    with mutex(root):
        live = squeue_live()
        mine = live_campaign_jobs(root, a.cutoff, live)
        named = set(a.after.split(',')) if a.after else set()
        stray = {j: i for j, i in mine.items() if j not in named}
        if stray:
            die(f'live jobs of {a.name} L{a.cutoff} not named in --after: {stray}')
        after = named & set(mine)          # live predecessors: keep the afterok dependency
        ended = named - after              # must be this campaign's, and confirmed successful
        owned = ledger_jobs(root, a.cutoff)
        for job in sorted(ended):
            if job not in owned:
                die(f'--after {job} is neither a live job nor a ledger job of {a.name} L{a.cutoff}')
            state = accounting_state(job, owned[job])
            if state != 'COMPLETED':
                die(f'--after {job} ended {state}; only a confirmed COMPLETED predecessor may be dropped')
            print(f'--after {job}: COMPLETED (sacct); no dependency needed')
        env = dict(HT3D_SITE=s, HT3D_RELEASE_TAR=rel['tar'], HT3D_RELEASE_SHA256=rel['tar_sha256'],
                   HT3D_EXPECT_FINGERPRINT=rel['fingerprint'],
                   HT3D_CAMPAIGN=root, HT3D_CUTOFF=a.cutoff, HT3D_STAGES=','.join(todo), HT3D_LANES=a.lanes,
                   HT3D_THREADS=threads, HT3D_BLAS_THREADS=a.blas_threads,
                   HT3D_SHARDS=a.array or '1', **expect)
        if a.solve_cutoffs:
            env['HT3D_SOLVE_CUTOFFS'] = ' '.join(a.solve_cutoffs)
        env['HT3D_SCHEMES'] = ' '.join(a.schemes)
        extra = [f'--job-name={name}', f'--output={logdir(root)}/%x_%A_%a.out' if a.array else
                 f'--output={logdir(root)}/%x_%j.out', f'--chdir={root}']
        if a.array:
            extra.append(f'--array=0-{int(a.array)-1}%{a.throttle}')
        if after:
            extra.append('--dependency=afterok:' + ':'.join(sorted(after)))
        with account_guard(s, partition, a.array or 1):
            job = sbatch(args + extra, job_script('stages.sbatch'), env, a.dry_run)
        if job:
            ledger(root, dict(job=job, name=name, cutoff=a.cutoff, stages=todo, partition=partition,
                              cpus=cpus, mem=a.mem, time=a.time, lanes=a.lanes, threads=threads,
                              blas_threads=a.blas_threads, array=a.array, after=sorted(after),
                              release=rel['git_sha'], submitted=time.strftime('%Y-%m-%dT%H:%M:%S%z')))
            su = max(int(cpus), int(a.mem[:-1])/2) * hours(a.time) * (int(a.array) if a.array else 1)
            print(f'submitted {job} ({tag}); log {root}/logs/{name}_{job}{"_<i>" if a.array else ""}.out')
            if s == 'expanse' and not spec['whole_node']:
                print(f'Expanse charge at most ~{su:.0f} SU if it runs to its time limit')


def cmd_solve_mpi(a):
    s = site()
    rel = release()
    root, campaign = load_campaign(a.name)
    check_release(campaign, rel)
    if not campaign.get('mpi_launcher'):
        die('campaign has no validated MPI launcher (init with --mpi-receipt)')
    partition = a.partition or ('compute' if s == 'expanse' else 'amdq')
    ntasks = str(int(a.nodes)*int(a.ranks_per_node))
    args, expect, _ = resources(s, partition, a.nodes, ntasks, a.cpus, a.mem, a.time, a.exclude)
    name = f'ht3d.{a.name}.L{a.cutoff}.solve-mpi'
    with mutex(root):
        live = squeue_live()
        mine = live_campaign_jobs(root, a.cutoff, live)
        if mine:
            die(f'live jobs of {a.name} L{a.cutoff}: {mine}')
        env = dict(HT3D_SITE=s, HT3D_RELEASE_TAR=rel['tar'], HT3D_RELEASE_SHA256=rel['tar_sha256'],
                   HT3D_EXPECT_FINGERPRINT=rel['fingerprint'],
                   HT3D_MPI_MODE='solve', HT3D_CAMPAIGN=root, HT3D_CUTOFF=a.cutoff,
                   HT3D_SCHEMES=' '.join(a.schemes), **expect)
        if a.solve_cutoffs:
            env['HT3D_SOLVE_CUTOFFS'] = ' '.join(a.solve_cutoffs)
        with account_guard(s, partition, 1):
            job = sbatch(args + [f'--job-name={name}', f'--output={logdir(root)}/%x_%j.out', f'--chdir={root}'],
                         job_script('mpi.sbatch'), env, a.dry_run)
        if job:
            ledger(root, dict(job=job, name=name, cutoff=a.cutoff, stages=['solve-mpi'], partition=partition,
                              nodes=a.nodes, ranks_per_node=a.ranks_per_node, cpus=expect['HT3D_EXPECT_CPUS'],
                              mem=a.mem,
                              time=a.time, release=rel['git_sha'], submitted=time.strftime('%Y-%m-%dT%H:%M:%S%z')))
            print(f'submitted {job}; log {root}/logs/{name}_{job}.out')


def cmd_status(a):
    from ht3d_stage import stage_status
    root, campaign = load_campaign(a.name)
    print(json.dumps(stage_status(root, a.cutoff, a.schemes,
                                  [int(c) for c in a.solve_cutoffs] if a.solve_cutoffs else None), indent=1))
    live = squeue_live()
    for job, info in sorted(live_campaign_jobs(root, a.cutoff, live).items()):
        print(f'live {job} {info[0]} {info[1]}')


def hours(text):
    days, _, rest = text.rpartition('-')
    h, m, s = map(int, rest.split(':'))
    return (int(days) if days else 0)*24 + h + m/60 + s/3600


def job_script(name):
    # sbatch reads the job script from this verified reference copy; the job then checks the
    # release tarball itself and runs only the staged, verified copy.
    return HERE/name


def main():
    sys.stdout.reconfigure(line_buffering=True)   # keep stdout and stderr in order
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    pos, mem, tlim = exact(POS, 'number'), exact(MEM, 'memory'), exact(TIME, 'time')
    x = sub.add_parser('plan')
    x.add_argument('--cutoff', type=even_cutoff, required=True)
    x = sub.add_parser('validate')
    x.add_argument('--partition')
    x.add_argument('--mem', type=mem, default='64G')
    x.add_argument('--time', type=tlim, default='01:00:00')
    x.add_argument('--exclude', type=exact(NODES, 'nodes'))
    x.add_argument('--dry-run', action='store_true')
    x = sub.add_parser('validate-mpi')
    x.add_argument('--store', required=True)
    x.add_argument('--gates', required=True)
    x.add_argument('--partition')
    x.add_argument('--nodes', type=pos, default='2')
    x.add_argument('--ranks-per-node', type=pos, default='2')
    x.add_argument('--cpus', type=pos, help='per rank; default 4, or the whole node on whole-node partitions')
    x.add_argument('--mem', type=mem, default='64G')
    x.add_argument('--time', type=tlim, default='00:30:00')
    x.add_argument('--exclude', type=exact(NODES, 'nodes'))
    x.add_argument('--dry-run', action='store_true')
    x = sub.add_parser('init')
    x.add_argument('name')
    x.add_argument('--receipt', required=True)
    x.add_argument('--mpi-receipt')
    x.add_argument('--no-layout-cache', action='store_true')
    x = sub.add_parser('run')
    x.add_argument('name')
    x.add_argument('--cutoff', type=even_cutoff, required=True)
    x.add_argument('--stages', required=True)
    x.add_argument('--cpus', type=pos, help='required except on whole-node partitions (all cores)')
    x.add_argument('--mem', type=mem, required=True)
    x.add_argument('--time', type=tlim, required=True)
    x.add_argument('--partition')
    x.add_argument('--lanes', type=pos, default='1')
    x.add_argument('--threads', type=pos)
    x.add_argument('--blas-threads', type=pos, default='1')
    x.add_argument('--array', type=pos)
    x.add_argument('--throttle', type=pos, default='8')
    x.add_argument('--solve-cutoffs', type=lambda t: str(even_cutoff(t)), nargs='+')
    x.add_argument('--schemes', nargs='+', choices=('raw', 'consistent'), default=['raw', 'consistent'])
    x.add_argument('--after', type=exact(JOBS, 'job ids'))
    x.add_argument('--exclude', type=exact(NODES, 'nodes'))
    x.add_argument('--dry-run', action='store_true')
    x = sub.add_parser('solve-mpi')
    x.add_argument('name')
    x.add_argument('--cutoff', type=even_cutoff, required=True)
    x.add_argument('--nodes', type=pos, required=True)
    x.add_argument('--ranks-per-node', type=pos, required=True)
    x.add_argument('--cpus', type=pos, help='per rank; required except on whole-node partitions')
    x.add_argument('--mem', type=mem, required=True)
    x.add_argument('--time', type=tlim, required=True)
    x.add_argument('--partition')
    x.add_argument('--solve-cutoffs', type=lambda t: str(even_cutoff(t)), nargs='+')
    x.add_argument('--schemes', nargs='+', choices=('raw', 'consistent'), default=['raw', 'consistent'])
    x.add_argument('--exclude', type=exact(NODES, 'nodes'))
    x.add_argument('--dry-run', action='store_true')
    x = sub.add_parser('status')
    x.add_argument('name')
    x.add_argument('--cutoff', type=even_cutoff, required=True)
    x.add_argument('--solve-cutoffs', type=lambda t: str(even_cutoff(t)), nargs='+')
    x.add_argument('--schemes', nargs='+', choices=('raw', 'consistent'), default=['raw', 'consistent'])
    a = p.parse_args()
    {'plan': cmd_plan, 'validate': cmd_validate, 'validate-mpi': cmd_validate_mpi, 'init': cmd_init,
     'run': cmd_run, 'solve-mpi': cmd_solve_mpi, 'status': cmd_status}[a.command](a)


if __name__ == '__main__':
    main()
