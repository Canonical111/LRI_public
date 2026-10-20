#!/usr/bin/env python3
"""Independent check of the checkpoint-review native changes on x86-64 Linux (canonical GCC 11.4 or personal desktop GCC 10.2), verifier's own driver.

  native_check.py NEW OLD OUT.json
NEW and OLD are `git archive` exports of ffbc8af (HEAD) and 601b102, each built with `make all gmp inspect` (NEW also
`make c7ref`). Steps (each recorded, every one runs):
  1. default executables old vs new: sha256 of bin/c8d2_decimal and bin/c8d2_gmp equal (make-built);
  2. the preprocessed translation units (g++ -E -P with the Makefile's flags, default and -DC8_USE_GMP) old vs new are
     byte-identical, so no compiler can give a different default binary; with -DC8_ORDER_TRACE they differ (sanity);
  3. the inspector prints the same lines old vs new on every L3..L7 graph of both sectors, TMPDIR left empty;
  4. CK-K03: tests/validate.py inspector_tempdir on L7 (free, power) passes with the new inspector, fails with 601b102's;
  5. CK-K03, verifier's own probes: SIGINT, SIGHUP, SIGQUIT, SIGALRM, SIGXCPU, SIGPIPE all clean up; SIGKILL leaves the
     private directory (documented); an unwritable or missing TMPDIR is an error exit (2) that creates nothing; a bad
     thread count (0, 4097) is refused; two concurrent runs get different private directories; a symlink planted at the
     601b102 predictable name is never followed (its target unchanged);
  6. T-04: validate.inspector_order on L7 (both sectors) passes; three mutants of src/c8d2_integrate.cpp fail with
     "executed order differs": comparator reversed, loop ignoring the order, and (verifier's own) the cost key without
     the addends factor.
"""
import hashlib, json, os, shutil, signal, stat, subprocess, sys, tempfile, time, traceback
from pathlib import Path

NEW, OLD, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
WORK = Path(os.environ.get('TMPDIR', '/tmp')) / 'native_check'
WORK.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(NEW / 'tests'), str(NEW / 'tools')]
import validate as V  # noqa: E402

R = {'host': os.uname().nodename, 'gxx': subprocess.run(['g++', '--version'], capture_output=True, text=True).stdout.splitlines()[0],
     'new': str(NEW), 'old': str(OLD)}
FLAGS = ['-O3', '-std=c++17', '-fopenmp', '-ffp-contract=off', '-fno-fast-math']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def step(name, fn):
    t0 = time.time()
    try:
        R[name] = dict(ok=True, result=fn())
    except BaseException as e:  # noqa: BLE001
        R[name] = dict(ok=False, error=f'{type(e).__name__}: {e}'[:3000], traceback=traceback.format_exc()[-3000:])
    R[name]['seconds'] = round(time.time() - t0, 1)
    print(name, 'OK' if R[name]['ok'] else 'FAILED', R[name].get('error', '')[:600], flush=True)
    OUT.write_text(json.dumps(R, indent=1, default=str) + '\n')


def default_binaries():
    out = {}
    for b in ('decimal', 'gmp'):
        n, o = sha(NEW / f'bin/c8d2_{b}'), sha(OLD / f'bin/c8d2_{b}')
        out[b] = dict(new=n, old=o, identical=n == o)
    out['inspect'] = dict(new=sha(NEW / 'bin/c8d2_inspect'), old=sha(OLD / 'bin/c8d2_inspect'), note='CK-K03 changes the inspector (not a default worker)')
    if not (out['decimal']['identical'] and out['gmp']['identical']):
        raise AssertionError(f'default binaries differ: {out}')
    return out


def preprocessed():
    out = {}
    for name, defs in (('decimal', []), ('gmp', ['-DC8_USE_GMP']), ('order_trace', ['-DC8_ORDER_TRACE'])):
        res = {}
        for tag, root in (('new', NEW), ('old', OLD)):
            p = subprocess.run(['g++', '-E', '-P', *FLAGS, *defs, str(root / 'src/c8d2_integrate.cpp')], capture_output=True, cwd=root)
            if p.returncode:
                raise RuntimeError(f'{tag} {name}: {p.stderr[-500:]}')
            res[tag] = p.stdout
        same = res['new'] == res['old']
        out[name] = dict(bytes=len(res['new']), sha256_new=hashlib.sha256(res['new']).hexdigest(), sha256_old=hashlib.sha256(res['old']).hexdigest(), identical=same)
    if not (out['decimal']['identical'] and out['gmp']['identical']) or out['order_trace']['identical']:
        raise AssertionError(f'preprocessed units: {out}')
    return out


def inspector_outputs():
    inv = V.inventory()
    res = {}
    for sector in ('free', 'power'):
        for L in range(3, 8):
            rows = inv[sector][str(L)]
            with tempfile.TemporaryDirectory(dir=WORK) as td:
                idx = Path(td) / 'idx.txt'
                idx.write_text(''.join(f'{r["id"]} {L} {r["offset"]} {r["length"]}\n' for r in rows))
                tmp = Path(td) / 'tmp'
                tmp.mkdir()
                outs = {}
                for tag, root in (('new', NEW), ('old', OLD)):
                    p = subprocess.run([str(root / 'bin/c8d2_inspect'), str(NEW / f'inputs/packs/{sector}_L{L}.pack'), str(idx), '8'],
                                       capture_output=True, text=True, env={**os.environ, 'TMPDIR': str(tmp)})
                    if p.returncode:
                        raise RuntimeError(f'{tag} inspector {sector} L{L}: {p.stderr[-500:]}')
                    outs[tag] = p.stdout
                    if tag == 'new' and list(tmp.iterdir()):
                        raise AssertionError(f'new inspector left {list(tmp.iterdir())}')
                if outs['new'] != outs['old']:
                    raise AssertionError(f'{sector} L{L}: inspector output differs old vs new')
                res[f'{sector}_L{L}'] = dict(graphs=len(rows), identical=True, sha256=hashlib.sha256(outs['new'].encode()).hexdigest()[:16])
    return res


def with_root(root, fn):
    saved, savedinv = V.ROOT, V._INV
    V.ROOT, V._INV = root, None
    try:
        return fn()
    finally:
        V.ROOT, V._INV = saved, savedinv


def tree(name, inspect=None, edit=None):
    root = WORK / name
    if root.exists():
        shutil.rmtree(root)
    (root / 'bin').mkdir(parents=True)
    (root / 'inputs').symlink_to(NEW / 'inputs')
    shutil.copy2(inspect or NEW / 'bin/c8d2_inspect', root / 'bin/c8d2_inspect')
    shutil.copy2(NEW / 'bin/c8d2_decimal', root / 'bin/c8d2_decimal')
    shutil.copytree(NEW / 'src', root / 'src')
    if edit:
        p = root / 'src/c8d2_integrate.cpp'
        s = p.read_text()
        a, b = edit
        if s.count(a) != 1:
            raise AssertionError(f'mutant anchor not unique: {a!r}')
        p.write_text(s.replace(a, b, 1))
    return root


def tempdir(sector, inspect=None):
    root = tree(f'tree_tmp_{sector}_{"old" if inspect else "new"}', inspect=inspect)
    with tempfile.TemporaryDirectory(dir=WORK) as td:
        return with_root(root, lambda: V.inspector_tempdir(Path(td), sector, 7))


def tempdir_old(sector):
    try:
        tempdir(sector, OLD / 'bin/c8d2_inspect')
    except AssertionError as e:
        return dict(expected_failure=str(e)[:500])
    raise AssertionError('the 601b102 inspector passed the CK-K03 test')


# ---- verifier's own CK-K03 probes
def own_probes():
    inspect = NEW / 'bin/c8d2_inspect'
    inv = V.inventory()
    rows = {r['id']: r for r in inv['free']['7']}
    g = V.by_cost('free', 7)[0]
    pack = NEW / 'inputs/packs/free_L7.pack'
    out = {}
    with tempfile.TemporaryDirectory(dir=WORK) as td:
        td = Path(td)
        longidx = td / 'long.txt'
        longidx.write_text(f'{g} 7 {rows[g]["offset"]} {rows[g]["length"]}\n' * 100000)
        one = td / 'one.txt'
        one.write_text(f'{g} 7 {rows[g]["offset"]} {rows[g]["length"]}\n')

        def fresh(name):
            d = td / name
            d.mkdir()
            return d

        def wait_dir(tmp, proc, threads):
            t0 = time.time()
            while time.time() - t0 < 120:
                if proc.poll() is not None:
                    raise AssertionError(f'ended early ({proc.returncode})')
                ents = list(tmp.iterdir())
                if len(ents) == 1 and ents[0].is_dir() and len(list(ents[0].iterdir())) == threads:
                    return ents[0]
                time.sleep(0.01)
            raise AssertionError('no private directory appeared')

        sigs = {}
        for sig in (signal.SIGINT, signal.SIGHUP, signal.SIGQUIT, signal.SIGALRM, signal.SIGXCPU, signal.SIGPIPE):
            if signal.getsignal(sig) is signal.SIG_IGN and sig != signal.SIGPIPE:  # inherited as ignored: the child keeps ignoring it
                sigs[sig.name] = 'skipped (ignored by this process)'
                continue
            tmp = fresh(f'sig_{sig.name}')
            # a fresh session with default dispositions (Popen restores SIGPIPE; SIGINT may be ignored in a batch job)
            proc = subprocess.Popen(['/bin/sh', '-c', 'trap - INT HUP QUIT ALRM XCPU PIPE; ulimit -c 0; exec "$0" "$@"', str(inspect), str(pack), str(longidx), '3'],
                                    env={**os.environ, 'TMPDIR': str(tmp)}, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                    restore_signals=True, start_new_session=True)
            try:
                d = wait_dir(tmp, proc, 3)
                proc.send_signal(sig)
                rc = proc.wait(timeout=60)
                sigs[sig.name] = dict(exit=rc, private_dir=d.name, left_behind=sorted(x.name for x in tmp.iterdir()))
                if rc != -sig or list(tmp.iterdir()):
                    raise AssertionError(f'{sig.name}: exit {rc}, left {sigs[sig.name]["left_behind"]}')
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
        out['signals'] = sigs
        tmp = fresh('sigkill')
        proc = subprocess.Popen([str(inspect), str(pack), str(longidx), '2'], env={**os.environ, 'TMPDIR': str(tmp)}, stdout=subprocess.DEVNULL)
        d = wait_dir(tmp, proc, 2)
        proc.kill()
        proc.wait()
        left = sorted(x.name for x in tmp.iterdir())
        out['SIGKILL'] = dict(left_behind=left, mode=oct(stat.S_IMODE(os.lstat(d).st_mode)), note='documented: only SIGKILL leaves the directory')
        if left != [d.name] or stat.S_IMODE(os.lstat(d).st_mode) != 0o700:
            raise AssertionError(f'SIGKILL: {out["SIGKILL"]}')
        # error exits that create nothing
        ro = fresh('readonly')
        ro.chmod(0o500)
        p = subprocess.run([str(inspect), str(pack), str(one), '2'], env={**os.environ, 'TMPDIR': str(ro)}, capture_output=True, text=True)
        ro.chmod(0o700)
        out['unwritable_tmpdir'] = dict(exit=p.returncode, stderr=p.stderr.strip()[-200:], left=sorted(x.name for x in ro.iterdir()))
        if p.returncode != 2 or 'private directory' not in p.stderr or list(ro.iterdir()) or p.stdout:
            raise AssertionError(f'unwritable TMPDIR: {out["unwritable_tmpdir"]}')
        p = subprocess.run([str(inspect), str(pack), str(one), '2'], env={**os.environ, 'TMPDIR': str(td / 'missing')}, capture_output=True, text=True)
        out['missing_tmpdir'] = dict(exit=p.returncode, stderr=p.stderr.strip()[-200:])
        if p.returncode != 2 or (td / 'missing').exists() or p.stdout:
            raise AssertionError(f'missing TMPDIR: {out["missing_tmpdir"]}')
        for n in ('0', '4097'):
            tmp = fresh(f'threads_{n}')
            p = subprocess.run([str(inspect), str(pack), str(one), n], env={**os.environ, 'TMPDIR': str(tmp)}, capture_output=True, text=True)
            out[f'threads_{n}'] = dict(exit=p.returncode, stderr=p.stderr.strip()[-200:])
            if p.returncode == 0 or list(tmp.iterdir()):
                raise AssertionError(f'threads {n}: {out[f"threads_{n}"]}')
        # two concurrent runs: different private directories in one TMPDIR
        tmp = fresh('concurrent')
        procs = [subprocess.Popen([str(inspect), str(pack), str(longidx), '1'], env={**os.environ, 'TMPDIR': str(tmp)}, stdout=subprocess.DEVNULL) for _ in range(2)]
        try:
            t0 = time.time()
            while time.time() - t0 < 60 and len([x for x in tmp.iterdir() if x.is_dir() and any(x.iterdir())]) < 2:
                time.sleep(0.01)
            names = sorted(x.name for x in tmp.iterdir())
        finally:
            for q in procs:
                q.terminate()
                q.wait()
        out['concurrent'] = dict(private_dirs=names, left_after_SIGTERM=sorted(x.name for x in tmp.iterdir()))
        if len(names) != 2 or names[0] == names[1] or list(tmp.iterdir()):
            raise AssertionError(f'concurrent: {out["concurrent"]}')
        # a symlink planted at the 601b102 predictable name of thread 0 of the next pid is never followed
        tmp = fresh('planted')
        victim = td / 'victim.txt'
        victim.write_text('do not touch\n')
        p = subprocess.Popen(['/bin/sh', '-c', 'sleep 1; exec "$0" "$@"', str(inspect), str(pack), str(one), '2'], env={**os.environ, 'TMPDIR': str(tmp)},
                             stdout=subprocess.PIPE, text=True)
        for t in range(2):
            (tmp / f'c8d2_inspect.{p.pid}.{t}.txt').symlink_to(victim)
        so, _ = p.communicate(timeout=60)
        out['planted_symlink'] = dict(exit=p.returncode, lines=len(so.splitlines()), victim_unchanged=victim.read_text() == 'do not touch\n',
                                      left=sorted(x.name for x in tmp.iterdir()))
        if p.returncode != 0 or victim.read_text() != 'do not touch\n' or sorted(x.name for x in tmp.iterdir()) != [f'c8d2_inspect.{p.pid}.{t}.txt' for t in range(2)]:
            raise AssertionError(f'planted symlink: {out["planted_symlink"]}')
        # the 601b102 inspector follows that symlink (the defect, shown on the old binary)
        victim.write_text('do not touch\n')
        tmp2 = fresh('planted_old')
        p = subprocess.Popen(['/bin/sh', '-c', 'sleep 1; exec "$0" "$@"', str(OLD / 'bin/c8d2_inspect'), str(pack), str(one), '1'], env={**os.environ, 'TMPDIR': str(tmp2)},
                             stdout=subprocess.PIPE, text=True)
        (tmp2 / f'c8d2_inspect.{p.pid}.0.txt').symlink_to(victim)
        p.communicate(timeout=60)
        out['planted_symlink_old_inspector'] = dict(exit=p.returncode, victim_changed=victim.read_text() != 'do not touch\n')
    return out


def order(root=None):
    with tempfile.TemporaryDirectory(dir=WORK) as td:
        fn = lambda: V.inspector_order(Path(td), loops=(7,))  # noqa: E731
        return with_root(root, fn) if root else fn()


def order_mutant(name, edit):
    root = tree(name, edit=edit)
    try:
        order(root)
    except AssertionError as e:
        if 'executed order differs' not in str(e):
            raise
        return dict(expected_failure=str(e)[:400])
    raise AssertionError(f'{name}: a wrong native order passed A-KER-5')


step('default_binaries_old_vs_new', default_binaries)
step('preprocessed_units_old_vs_new', preprocessed)
step('inspector_outputs_identical_L3_L7', inspector_outputs)
step('ck_k03_validate_tempdir_free_L7', lambda: tempdir('free'))
step('ck_k03_validate_tempdir_power_L7', lambda: tempdir('power'))
step('ck_k03_validate_tempdir_old_inspector_fails', lambda: tempdir_old('free'))
step('ck_k03_verifier_probes', own_probes)
step('t04_inspector_order_L7', order)
step('t04_mutant_comparator_reversed', lambda: order_mutant('mut_cmp', ('return cost(a)>cost(b);', 'return cost(a)<cost(b);')))
step('t04_mutant_loop_ignores_order', lambda: order_mutant('mut_loop', ('int ti=order_of[oi];', 'int ti=oi;(void)order_of;')))
step('t04_mutant_cost_without_addends', lambda: order_mutant('mut_key', ('return ld(t.end-t.begin)*loaded.at(t.graph).addends.size();', 'return ld(t.end-t.begin);')))
R['all_ok'] = all(v.get('ok') for v in R.values() if isinstance(v, dict) and 'ok' in v)
OUT.write_text(json.dumps(R, indent=1, default=str) + '\n')
shutil.rmtree(WORK, ignore_errors=True)
print('ALL OK' if R['all_ok'] else 'SOME FAILED', flush=True)
sys.exit(0 if R['all_ok'] else 1)
