#!/usr/bin/env python3
"""In-job helpers for the Expanse launch layer (standard library only).

  monitor  -- CMD...   run CMD, sample the memory of its process tree, the job's
                       memory cgroup and the scratch usage; write a JSON summary
                       (wall time, CPU time, peak RSS/PSS, cgroup peak, scratch
                       peak) and optional JSON-lines samples; exit with CMD's code
  check-env            compare installed versions with requirements-tested.txt
  task-info            print shell assignments describing one plan row
  grid-info            print the grid key and its source-tagged Lustre directory name
  scratch-need         node-local bytes a grid or task job needs (with margin)
  receipt              assemble a job receipt (site, node, CPU vendor/model, topology,
                       thread settings, phases, monitors, Slurm environment)
  cores                physical cores in this process's allowed CPU set
  topology             packages, cores and NUMA nodes of the allowed CPUs
  grid-workers         grid worker count from cores and the memory limit
  sources-hash         sha256 binding the scientific sources (exported by submit.py)
  published-check      strict status of a published row or grid (see manifests.py)

Nothing here touches the scientific numerics.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import shlex
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]
# Never more than one physical package per process (hpc-clusters rule): the cap
# is the package size found in sysfs (64 on Expanse, 32/20 on symmetry AMD/Intel),
# and in any case at most 64.
MAX_THREADS_PER_PROCESS = 64


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


# ---------------------------------------------------------------- process tree

def _children_map() -> dict[int, list[int]]:
    kids: dict[int, list[int]] = {}
    if not os.path.isdir('/proc'):      # not Linux: only the direct child is known
        return kids
    for entry in os.scandir('/proc'):
        if not entry.name.isdigit():
            continue
        try:
            with open(f'/proc/{entry.name}/stat') as f:
                text = f.read()
            ppid = int(text.rsplit(')', 1)[1].split()[1])
        except (OSError, IndexError, ValueError):
            continue
        kids.setdefault(ppid, []).append(int(entry.name))
    return kids


def tree_pids(root: int) -> list[int]:
    kids, out, todo = _children_map(), [], [root]
    while todo:
        pid = todo.pop()
        out.append(pid)
        todo.extend(kids.get(pid, []))
    return out


def _status_kib(pid: int, field: str) -> int:
    try:
        with open(f'/proc/{pid}/status') as f:
            for line in f:
                if line.startswith(field + ':'):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _pss_kib(pid: int) -> int:
    try:
        with open(f'/proc/{pid}/smaps_rollup') as f:
            for line in f:
                if line.startswith('Pss:'):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return 0


# ---------------------------------------------------------------- memory cgroup

def job_cgroup() -> dict | None:
    """Locate the Slurm job-level memory cgroup (v1 or v2), if readable."""
    try:
        lines = Path('/proc/self/cgroup').read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        parts = line.split(':', 2)
        if len(parts) != 3:
            continue
        _, controllers, rel = parts
        if 'memory' in controllers.split(','):
            base, version = Path('/sys/fs/cgroup/memory'), 1
        elif controllers == '' and parts[0] == '0':
            base, version = Path('/sys/fs/cgroup'), 2
        else:
            continue
        path = base / rel.lstrip('/')
        probe = path
        while probe != base and not probe.name.startswith('job_'):
            probe = probe.parent
        path = probe if probe.name.startswith('job_') else path
        if path.is_dir():
            return {'version': version, 'path': str(path)}
    return None


def _read_int(path: Path) -> int | None:
    try:
        text = path.read_text().strip()
        return None if text == 'max' else int(text)
    except (OSError, ValueError):
        return None


def cgroup_sample(cg: dict | None) -> dict:
    if not cg:
        return {}
    p = Path(cg['path'])
    stat = {}
    try:
        for line in (p / 'memory.stat').read_text().splitlines():
            k, v = line.split()
            stat[k] = int(v)
    except (OSError, ValueError):
        pass
    if cg['version'] == 1:
        return {'usage': _read_int(p / 'memory.usage_in_bytes'), 'peak': _read_int(p / 'memory.max_usage_in_bytes'),
                'limit': _read_int(p / 'memory.limit_in_bytes'),
                'anon': stat.get('total_rss'), 'file': stat.get('total_cache')}
    return {'usage': _read_int(p / 'memory.current'), 'peak': _read_int(p / 'memory.peak'),
            'limit': _read_int(p / 'memory.max'), 'anon': stat.get('anon'), 'file': stat.get('file')}


# ---------------------------------------------------------------- disk usage

def allocated_bytes(path: Path) -> int:
    """Allocated (not apparent) bytes below path; sparse memory maps count as written."""
    total = 0
    stack = [path]
    while stack:
        try:
            with os.scandir(stack.pop()) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(Path(e.path))
                        elif e.is_file(follow_symlinks=False):
                            total += e.stat(follow_symlinks=False).st_blocks * 512
                    except OSError:
                        pass
        except OSError:
            pass
    return total


def fs_used(path: Path) -> int | None:
    try:
        s = os.statvfs(path)
        return (s.f_blocks - s.f_bfree) * s.f_frsize
    except OSError:
        return None


# ---------------------------------------------------------------- monitor

def monitor(a: argparse.Namespace) -> int:
    cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not cmd:
        raise SystemExit('monitor: no command given')
    cg = job_cgroup()
    watch = Path(a.watch) if a.watch else None
    fs0 = fs_used(watch) if watch else None
    start, t0 = now(), time.monotonic()
    proc = subprocess.Popen(cmd)
    stop = {'signal': None}

    def forward(signum, _frame):
        stop['signal'] = signum
        try:
            proc.send_signal(signum)
        except OSError:
            pass
    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1):
        signal.signal(s, forward)

    peaks = {'tree_rss_bytes': 0, 'tree_pss_bytes': 0, 'max_processes': 0, 'cgroup_usage_bytes': 0,
             'cgroup_anon_bytes': 0, 'scratch_dir_allocated_bytes': 0, 'filesystem_used_delta_bytes': 0}
    samples = open(a.samples, 'a') if a.samples else None
    # Reap only through os.wait4 (never proc.poll/wait), which also returns the
    # child's resource usage including its waited-for descendants.
    reaped = None
    while reaped is None:
        pids = tree_pids(proc.pid)
        rss = sum(_status_kib(p, 'VmRSS') for p in pids) * 1024
        pss = sum(_pss_kib(p) for p in pids) * 1024
        cgs = cgroup_sample(cg)
        row = {'t': round(time.monotonic() - t0, 1), 'processes': len(pids), 'tree_rss': rss, 'tree_pss': pss,
               'cgroup_usage': cgs.get('usage'), 'cgroup_anon': cgs.get('anon'), 'cgroup_file': cgs.get('file')}
        if watch:
            row['scratch_dir_allocated'] = allocated_bytes(watch)
            used = fs_used(watch)
            row['filesystem_used_delta'] = None if used is None or fs0 is None else used - fs0
        for key, val in [('tree_rss_bytes', rss), ('tree_pss_bytes', pss), ('max_processes', len(pids)),
                         ('cgroup_usage_bytes', cgs.get('usage')), ('cgroup_anon_bytes', cgs.get('anon')),
                         ('scratch_dir_allocated_bytes', row.get('scratch_dir_allocated')),
                         ('filesystem_used_delta_bytes', row.get('filesystem_used_delta'))]:
            if val is not None:
                peaks[key] = max(peaks[key], val)
        if samples:
            samples.write(json.dumps(row) + '\n')
            samples.flush()
        # Sleep in small steps so that short commands finish promptly.
        deadline = time.monotonic() + a.interval
        while reaped is None and time.monotonic() < deadline:
            pid, status, ru = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                reaped = (status, ru)
            else:
                time.sleep(min(0.5, a.interval))
    wall = time.monotonic() - t0
    status, rusage = reaped
    code = os.waitstatus_to_exitcode(status)
    maxrss = rusage.ru_maxrss * (1 if sys.platform == 'darwin' else 1024)   # Linux reports KiB
    cgs = cgroup_sample(cg)
    summary = {'label': a.label, 'command': cmd, 'started_utc': start, 'finished_utc': now(),
               'wall_seconds': round(wall, 3), 'exit_code': code, 'forwarded_signal': stop['signal'],
               'cpu_user_seconds': rusage.ru_utime, 'cpu_system_seconds': rusage.ru_stime,
               'mean_busy_cores': round((rusage.ru_utime + rusage.ru_stime) / wall, 2) if wall > 0 else None,
               'largest_process_maxrss_bytes': maxrss,
               'sampled_peaks': peaks, 'sample_interval_seconds': a.interval,
               'cgroup': cg, 'cgroup_peak_bytes_job_lifetime': cgs.get('peak'), 'cgroup_limit_bytes': cgs.get('limit'),
               'notes': 'tree_* are sums over the command and all descendants (sampled; PSS avoids double counting '
                        'fork-shared pages). cgroup_* cover the whole Slurm job and include page cache. '
                        'largest_process_maxrss is what /usr/bin/time -v reports.'}
    if a.summary:
        Path(a.summary).write_text(json.dumps(summary, indent=2) + '\n')
    print(f"MONITOR {a.label}: exit={code} wall={wall:.1f}s cpu={rusage.ru_utime + rusage.ru_stime:.1f}s "
          f"tree_pss_peak={peaks['tree_pss_bytes'] / 2**30:.2f}GiB tree_rss_peak={peaks['tree_rss_bytes'] / 2**30:.2f}GiB "
          f"largest_maxrss={maxrss / 2**30:.2f}GiB cgroup_anon_peak={peaks['cgroup_anon_bytes'] / 2**30:.2f}GiB "
          f"scratch_peak={peaks['scratch_dir_allocated_bytes'] / 1e9:.2f}GB", flush=True)
    return code


# ---------------------------------------------------------------- environment

def read_requirements(path: Path) -> dict[str, str]:
    wanted = {}
    for line in path.read_text().splitlines():
        line = line.split('#', 1)[0].strip()
        if line:
            name, version = line.split('==')
            wanted[name.strip()] = version.strip()
    return wanted


def check_env(a: argparse.Namespace) -> int:
    from importlib import metadata
    wanted = read_requirements(Path(a.requirements))
    found = {}
    for name in wanted:
        try:
            found[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            found[name] = None
    bad = {n: [wanted[n], found[n]] for n in wanted if found[n] != wanted[n]}
    out = {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
           'required': wanted, 'installed': found, 'mismatches': bad}
    text = json.dumps(out, indent=2) + '\n'
    if a.out:
        Path(a.out).write_text(text)
    print(text, end='')
    return 78 if bad else 0


# ---------------------------------------------------------------- plan rows

def sources_digest(run_task) -> str:
    """sha256 of the scientific source hashes (code/hamiltonian/*.py) as JSON."""
    import hashlib
    return hashlib.sha256(json.dumps(run_task.source_hashes(), sort_keys=True).encode()).hexdigest()


def grid_dir_name(run_task, cutoff: int, oversample: int, radius_cost: float) -> str:
    """Directory of a published grid: run_task's grid key plus a tag of the
    scientific sources, so grids made by different code never share a directory."""
    return f'{run_task.grid_key(cutoff, oversample, radius_cost)}_src{sources_digest(run_task)[:12]}'


def sources_hash_cmd(a: argparse.Namespace) -> int:
    sys.path.insert(0, str(PKG / 'cluster'))
    import run_task
    print(sources_digest(run_task))
    return 0


def published_check(a: argparse.Namespace) -> int:
    """Exit 0 if the published directory is complete, 3 if absent, 74 if corrupt
    (problems on stderr). Rows need --plan/--index; grids hash the array too."""
    import manifests
    directory = Path(a.dir)
    if a.kind == 'row':
        sys.path.insert(0, str(PKG / 'cluster'))
        import run_task
        _, jobs = run_task.load_plan(Path(a.plan))
        status, problems = manifests.row_status(directory, jobs[a.index])
    else:
        status, problems = manifests.grid_status(directory, hash_array=True)
    print(status)
    for x in problems:
        print(f'  {directory}: {x}', file=sys.stderr)
    return {'complete': 0, 'absent': 3}.get(status, 74)


def grid_info(a: argparse.Namespace) -> int:
    sys.path.insert(0, str(PKG / 'cluster'))
    import run_task
    values = {'GRID_KEY': run_task.grid_key(a.cutoff, a.oversample, a.radius_cost),
              'GRID_DIR': grid_dir_name(run_task, a.cutoff, a.oversample, a.radius_cost)}
    for k, v in values.items():
        print(f'{k}={shlex.quote(str(v))}')
    return 0


def task_info(a: argparse.Namespace) -> int:
    """Shell assignments for one plan row, using run_task.py's own naming."""
    sys.path.insert(0, str(PKG / 'cluster'))
    import run_task
    plan = Path(a.plan)
    _, jobs = run_task.load_plan(plan)
    if not 0 <= a.index < len(jobs):
        raise SystemExit(f'task index {a.index} outside 0..{len(jobs) - 1}')
    job = jobs[a.index]
    dry = subprocess.run([sys.executable, str(PKG / 'cluster/run_task.py'), 'run', '--plan', str(plan),
                          '--task-index', str(a.index), '--work-root', '/nonexistent/work',
                          '--output-root', '/nonexistent/out', '--dry-run'],
                         check=True, capture_output=True, text=True)
    info = json.loads(dry.stdout)
    values = {'TASK_NAME': info['task'], 'TASK_ID': job['id'], 'TASK_N': job['cutoff'],
              'GRID_DIR': grid_dir_name(run_task, job['cutoff'], job['oversample'], job['radius_cost']),
              'TASK_ORDER': job['order'], 'TASK_LAMBDAS': ' '.join(map(str, job['lambda'])),
              'GRID_KEY': run_task.grid_key(job['cutoff'], job['oversample'], job['radius_cost']),
              'GRID_OVERSAMPLE': job['oversample'], 'GRID_RADIUS_COST': job['radius_cost'],
              'TASK_STAGE': job.get('stage', '')}
    for k, v in values.items():
        print(f'{k}={shlex.quote(str(v))}')
    return 0


def scratch_need(a: argparse.Namespace) -> int:
    """Node-local bytes: grid jobs hold the stored grid and its temporary array at
    once; task jobs hold the staged grid. Plus the package, outputs and a margin."""
    sys.path.insert(0, str(PKG / 'cluster'))
    from resource_estimate import estimate
    e = estimate(a.cutoff, a.oversample)
    if a.kind == 'grid':
        need = e['coefficient_bytes'] + e['temporary_bytes']
    else:
        need = e['coefficient_bytes']
    need = int(need * (1 + a.margin)) + 2 * 10**9
    print(need)
    return 0


# ---------------------------------------------------------------- receipts

def receipt(a: argparse.Namespace) -> int:
    phases = []
    if a.phases and Path(a.phases).is_file():
        for line in Path(a.phases).read_text().splitlines():
            name, t0, t1, code = line.split()
            phases.append({'phase': name, 'start_epoch': float(t0), 'end_epoch': float(t1),
                           'seconds': round(float(t1) - float(t0), 3), 'exit_code': int(code)})
    monitors = {}
    for m in a.monitor or []:
        p = Path(m)
        if p.is_file():
            monitors[p.stem] = json.loads(p.read_text())
    slurm = {k: v for k, v in os.environ.items() if k.startswith('SLURM_') and k in {
        'SLURM_JOB_ID', 'SLURM_ARRAY_JOB_ID', 'SLURM_ARRAY_TASK_ID', 'SLURM_JOB_NAME', 'SLURM_JOB_PARTITION',
        'SLURM_JOB_ACCOUNT', 'SLURM_CPUS_ON_NODE', 'SLURM_CPUS_PER_TASK', 'SLURM_MEM_PER_NODE',
        'SLURM_JOB_NODELIST', 'SLURM_SUBMIT_DIR', 'SLURM_JOB_QOS'}}
    lri = {k: v for k, v in os.environ.items() if k.startswith('LRI_')}
    stage_info = None
    if a.package and (Path(a.package) / 'STAGE_INFO.json').is_file():
        stage_info = json.loads((Path(a.package) / 'STAGE_INFO.json').read_text())
    extra = {}
    for item in a.extra or []:
        k, _, v = item.partition('=')
        extra[k] = v
    topo = topology()
    threads = {k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                                               'NUMEXPR_NUM_THREADS', 'LRI_WORKERS', 'LRI_FFT_WORKERS')}
    out = {'kind': a.kind, 'status': a.status, 'written_utc': now(), 'site': os.environ.get('LRI_SITE', 'unknown'),
           'host': platform.node(), 'cpu_vendor': topo['vendor'], 'cpu_model': topo['model'],
           'topology': topo, 'thread_environment': threads,
           'slurm': slurm, 'lri_environment': lri, 'package': stage_info, 'phases': phases,
           'monitors': monitors, 'extra': extra}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(a.out).with_name(Path(a.out).name + '.writing')
    tmp.write_text(json.dumps(out, indent=2) + '\n')
    os.replace(tmp, a.out)
    print('RECEIPT', a.out)
    return 0


def _cpu_info() -> dict:
    info = {'vendor': None, 'model': platform.processor() or None}
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            key, _, value = line.partition(':')
            key = key.strip()
            if key == 'vendor_id' and info['vendor'] is None:
                info['vendor'] = value.strip()
            elif key == 'model name':
                info['model'] = value.strip()
                break
    except OSError:
        pass
    return info


def topology() -> dict:
    """Packages, cores and NUMA nodes of the CPUs this process may use.

    Read from sysfs inside the job (Slurm reports NUMA domains as sockets on the
    AMD nodes, so scontrol is not used). Intel ids are interleaved between
    packages, so pinning is expressed by NUMA node, never by CPU-id ranges."""
    getaff = getattr(os, 'sched_getaffinity', None)
    allowed = sorted(getaff(0)) if getaff else list(range(os.cpu_count() or 1))
    packages: dict = {}
    for cpu in allowed:
        base = Path(f'/sys/devices/system/cpu/cpu{cpu}')
        try:
            pkg = int((base / 'topology/physical_package_id').read_text())
            core = int((base / 'topology/core_id').read_text())
        except (OSError, ValueError):
            pkg, core = 0, cpu
        nodes = sorted(int(n.name[4:]) for n in base.glob('node[0-9]*'))
        entry = packages.setdefault(pkg, {'package': pkg, 'cpus': [], 'cores': set(), 'numa_nodes': set()})
        entry['cpus'].append(cpu)
        entry['cores'].add(core)
        entry['numa_nodes'].update(nodes)
    total_per_package = {}
    for pkg in packages:   # all cores of the package, allowed or not
        cores_all = set()
        for t in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/topology/physical_package_id'):
            try:
                if int(t.read_text()) == pkg:
                    cores_all.add(int((t.parent / 'core_id').read_text()))
            except (OSError, ValueError):
                pass
        total_per_package[pkg] = len(cores_all) or len(packages[pkg]['cores'])
    out = []
    for pkg in sorted(packages):
        e = packages[pkg]
        out.append({'package': pkg, 'allowed_cpus': len(e['cpus']), 'allowed_cores': len(e['cores']),
                    'package_cores': total_per_package[pkg], 'numa_nodes': sorted(e['numa_nodes'])})
    cpu = _cpu_info()
    return {'vendor': cpu['vendor'], 'model': cpu['model'], 'allowed_cpus': len(allowed),
            'physical_cores': sum(p['allowed_cores'] for p in out), 'packages': out}


def physical_cores() -> int:
    """Distinct physical cores in the allowed CPU set."""
    return topology()['physical_cores']


def per_process_cap(topo: dict) -> int:
    """Threads one process may use: never more than one physical package."""
    package = max((p['package_cores'] for p in topo['packages']), default=1)
    return min(package, MAX_THREADS_PER_PROCESS)


def cores(a: argparse.Namespace) -> int:
    topo = topology()
    budget = min(topo['physical_cores'], int(os.environ.get('SLURM_CPUS_ON_NODE', topo['physical_cores'])))
    print(min(budget, per_process_cap(topo)) if a.per_process else budget)
    return 0


def topology_cmd(a: argparse.Namespace) -> int:
    topo = topology()
    if a.json:
        print(json.dumps(topo, indent=2))
        return 0
    lines = {'TOPO_VENDOR': topo['vendor'] or 'unknown', 'TOPO_MODEL': topo['model'] or 'unknown',
             'TOPO_PACKAGES': len(topo['packages']), 'TOPO_PHYSICAL_CORES': topo['physical_cores'],
             'TOPO_PER_PROCESS': per_process_cap(topo)}
    for i, p in enumerate(topo['packages']):
        lines[f'TOPO_PKG{i}_ID'] = p['package']
        lines[f'TOPO_PKG{i}_CORES'] = p['allowed_cores']
        lines[f'TOPO_PKG{i}_NODES'] = ','.join(map(str, p['numa_nodes']))
    for k, v in lines.items():
        print(f'{k}={shlex.quote(str(v))}')
    return 0


def grid_workers_cap(cutoff: int, oversample: int, mem_bytes: float, fraction: float = 0.8) -> int:
    """Largest worker count whose modelled anonymous memory (see submit.py:
    21 complex (M, M) arrays per worker + 4 in the parent) stays below fraction x mem."""
    sys.path.insert(0, str(PKG / 'cluster'))
    from resource_estimate import estimate
    unit = 16 * estimate(cutoff, oversample)['M'] ** 2
    return max(0, int((fraction * mem_bytes / unit - 4) // 21))


def grid_workers(a: argparse.Namespace) -> int:
    """Worker count for a grid job: min(per-process cores, memory cap)."""
    cap = grid_workers_cap(a.cutoff, a.oversample, a.mem_mb * 2**20)
    print(max(1, min(a.cores, cap)) if cap >= 1 else 0)
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='action', required=True)
    m = sub.add_parser('monitor')
    m.add_argument('--label', default='command')
    m.add_argument('--summary')
    m.add_argument('--samples')
    m.add_argument('--watch', help='Directory whose allocated size is sampled (node-local stage).')
    m.add_argument('--interval', type=float, default=20.0)
    m.add_argument('command', nargs=argparse.REMAINDER)
    e = sub.add_parser('check-env')
    e.add_argument('--requirements', default=str(PKG / 'requirements-tested.txt'))
    e.add_argument('--out')
    t = sub.add_parser('task-info')
    t.add_argument('--plan', required=True)
    t.add_argument('--index', type=int, required=True)
    g = sub.add_parser('grid-info')
    g.add_argument('--cutoff', type=int, required=True)
    g.add_argument('--oversample', type=int, required=True)
    g.add_argument('--radius-cost', type=float, required=True)
    s = sub.add_parser('scratch-need')
    s.add_argument('--kind', choices=['grid', 'task'], required=True)
    s.add_argument('--cutoff', type=int, required=True)
    s.add_argument('--oversample', type=int, required=True)
    s.add_argument('--margin', type=float, default=0.10)
    r = sub.add_parser('receipt')
    r.add_argument('--kind', required=True)
    r.add_argument('--status', required=True)
    r.add_argument('--out', required=True)
    r.add_argument('--phases')
    r.add_argument('--monitor', nargs='*')
    r.add_argument('--package')
    r.add_argument('--extra', nargs='*')
    c = sub.add_parser('cores')
    c.add_argument('--per-process', action='store_true', help='Cap at one physical package (and 64).')
    t2 = sub.add_parser('topology')
    t2.add_argument('--json', action='store_true', help='JSON instead of shell assignments.')
    sh = sub.add_parser('sources-hash', help='sha256 of the scientific source hashes of this package')
    pc = sub.add_parser('published-check', help='complete (0) / absent (3) / corrupt (74)')
    pc.add_argument('--kind', choices=['row', 'grid'], required=True)
    pc.add_argument('--dir', required=True)
    pc.add_argument('--plan')
    pc.add_argument('--index', type=int)
    w = sub.add_parser('grid-workers')
    w.add_argument('--cutoff', type=int, required=True)
    w.add_argument('--oversample', type=int, required=True)
    w.add_argument('--mem-mb', type=float, required=True)
    w.add_argument('--cores', type=int, required=True)
    a = p.parse_args()
    handler = {'monitor': monitor, 'check-env': check_env, 'task-info': task_info, 'grid-info': grid_info,
               'scratch-need': scratch_need, 'receipt': receipt, 'cores': cores, 'topology': topology_cmd,
               'grid-workers': grid_workers, 'sources-hash': sources_hash_cmd,
               'published-check': published_check}[a.action]
    if a.action == 'published-check' and a.kind == 'row' and (a.plan is None or a.index is None):
        p.error('published-check --kind row needs --plan and --index')
    sys.exit(handler(a))


if __name__ == '__main__':
    main()
