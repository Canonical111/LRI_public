"""Merge c6sum sector JSONL files into one level vector, with coverage and provenance guards.

Usage: python merge.py (OUT.json | --leveldir DIR) FILE.jsonl [FILE.jsonl ...] [--subset mod10|all]
With --leveldir the output is written to DIR/<canonical level name> (see level_name).

Every input must start with a c6sum header. All headers must agree on every field except the sector range
(first, stop). The sectors present must be exactly the expected set (all sectors, or the fixed subset
{s : s mod 10 == 0}), each exactly once. Values are parsed from their decimal text and summed in mpmath at 50
digits in sector order. The output records the per-sector values (as text), the totals, the common header
and the SHA256 of every input file.
"""
import sys, os, json, hashlib, argparse, math
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from pathlib import Path
import mpmath as mp

RANGE_KEYS = ('first', 'stop')


class MergeError(Exception):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_file(path):
    text = Path(path).read_text()
    if not text.endswith('\n'):
        raise MergeError(f'{path}: truncated last line (run still in progress or killed)')
    lines = text.splitlines()
    if not lines:
        raise MergeError(f'{path}: empty')
    header = json.loads(lines[0])
    if header.get('type') != 'header' or header.get('engine') != 'c6sum':
        raise MergeError(f'{path}: first line is not a c6sum header')
    sectors = {}; attempts = []
    for ln in lines[1:]:
        rec = json.loads(ln, parse_float=str, parse_int=str)
        if rec.get('type') == 'attempt':
            attempts.append(rec); continue
        if rec.get('type') != 'sector':
            raise MergeError(f'{path}: unexpected record {ln[:80]}')
        s = int(rec['sector'])
        if not (int(header['first']) <= s < int(header['stop'])):
            raise MergeError(f'{path}: sector {s} outside the header range')
        if s in sectors:
            raise MergeError(f'{path}: duplicate sector {s}')
        if s % int(header.get('mod', 1)):
            raise MergeError(f'{path}: sector {s} not in the header mod-{header.get("mod")} subset')
        vals = rec['values']
        for v in vals:
            x = float(v)
            if not math.isfinite(x):
                raise MergeError(f'{path}: non-finite value in sector {s}')
        sectors[s] = vals
    if not attempts:
        raise MergeError(f'{path}: no attempt record')
    return header, sectors, attempts


def merge(files, subset='all'):
    common = None; allsec = {}; digests = {}; attempts = {}
    for f in files:
        h, secs, att = read_file(f)
        attempts[str(f)] = att
        key = {k: v for k, v in h.items() if k not in RANGE_KEYS}
        if common is None:
            common = key
        elif key != common:
            diff = sorted(k for k in set(key) | set(common) if key.get(k) != common.get(k))
            raise MergeError(f'{f}: header differs from the first file in {diff}')
        for s, v in secs.items():
            if s in allsec:
                raise MergeError(f'sector {s} present in more than one file')
            allsec[s] = v
        digests[str(f)] = sha256(f)
    L = int(common['L']); mode = common['mode']
    if L not in (5, 6) or mode not in ('H', 'J'):
        raise MergeError(f'unsupported L={L} mode={mode}')
    total = math.factorial(L) // 2
    if int(common['sectors_total']) != total:
        raise MergeError(f"header sectors_total {common['sectors_total']} != L!/2 = {total}")
    if int(common.get('mod', 1)) != (1 if subset == 'all' else 10):
        raise MergeError(f"header mod {common.get('mod')} does not match subset {subset}")
    expected = set(range(total)) if subset == 'all' else {s for s in range(total) if s % 10 == 0}
    got = set(allsec)
    if got != expected:
        missing = sorted(expected - got); extra = sorted(got - expected)
        raise MergeError(f'coverage: missing {missing[:20]}{"..." if len(missing) > 20 else ""} ({len(missing)}), extra {extra[:20]} ({len(extra)})')
    n = 2 * (L + (1 if mode == 'J' else 0))
    bad = sorted(s for s, v in allsec.items() if len(v) != n)
    if bad:
        raise MergeError(f'vector length != {n} (2*(L+[mode==J])) in sectors {bad[:10]}')
    with mp.workdps(50):
        tot = [mp.mpf(0)] * n
        for s in sorted(allsec):
            for j, v in enumerate(allsec[s]):
                tot[j] += mp.mpf(v)
        totals = [mp.nstr(x, 35) for x in tot]
    return {'header': common, 'subset': subset, 'sectors': sorted(allsec), 'per_sector': {str(s): allsec[s] for s in sorted(allsec)},
            'totals': totals, 'inputs_sha256': digests, 'attempts': attempts}


from levelio import level_name  # noqa: E402  (shared canonical naming)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?'); ap.add_argument('files', nargs='+'); ap.add_argument('--subset', choices=['all', 'mod10'], default='all')
    ap.add_argument('--leveldir')
    a = ap.parse_args()
    files = a.files if a.leveldir else a.files
    if a.leveldir and a.out:
        files = [a.out] + files
    try:
        res = merge(files, a.subset)
    except MergeError as e:
        print(f'MERGE REFUSED: {e}', file=sys.stderr); sys.exit(1)
    outp = Path(a.leveldir) / level_name(res['header'], a.subset) if a.leveldir else Path(a.out)
    if outp.exists():
        print(f'MERGE REFUSED: {outp} exists (levels are write-once; remove it deliberately to redo)', file=sys.stderr); sys.exit(1)
    # Publish atomically and write-once: write and validate a temporary file in the same directory, then hard-link
    # it to the final name (fails if the name exists) and remove the temporary. An interrupted merge leaves only a
    # dot-prefixed temporary, which no reader treats as a level.
    tmp = outp.with_name(f'.{outp.name}.tmp{os.getpid()}')
    tmp.write_text(json.dumps(res, indent=1))
    try:
        if a.leveldir:
            from levelio import validate_level, LevelError
            import shutil
            chk = tmp.with_name(f'.{os.getpid()}.check'); chk.mkdir()
            try:
                shutil.copy(tmp, chk / outp.name); validate_level(chk / outp.name)
            finally:
                shutil.rmtree(chk)
        os.link(tmp, outp)
    except FileExistsError:
        print(f'MERGE REFUSED: {outp} appeared concurrently (write-once)', file=sys.stderr); sys.exit(1)
    except Exception as e:  # noqa: BLE001  (validation failure or no hard links)
        if type(e).__name__ == 'LevelError':
            print(f'MERGE REFUSED: merged record failed validation: {e}', file=sys.stderr); sys.exit(1)
        if isinstance(e, OSError) and not outp.exists():
            os.rename(tmp, outp)  # filesystem without hard links: rename (merges of one level are serialized by Slurm)
        else:
            raise
    finally:
        if tmp.exists():
            tmp.unlink()
    print(f'wrote {outp}')
    h = res['header']
    print(f"merged L={h['L']} N={h['N']} mode={h['mode']} stratum={h['stratum']} perturb={h['perturb']} comp={h['comp']} kind={h['kind']} sectors={len(res['sectors'])}")
    print('totals', ' '.join(res['totals']))


if __name__ == '__main__':
    main()
