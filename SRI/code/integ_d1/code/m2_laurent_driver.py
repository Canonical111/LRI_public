"""M2: two-bubble cluster J2^{(k)}(K), k = 0..3, on the circle K = 1 - r e^{i theta} (half circle by conjugation),
streamed to a .jsonl file; Laurent coefficients are assembled afterwards by m2_gate.py.
Fix round 1 (MSC-007): every record carries a run fingerprint (level, dps, radius, npts, Cauchy parameters and the
sha256 of two_bubble.py and of this driver). Resuming into an existing file is allowed only if every existing record
has exactly the current fingerprint; otherwise the run stops and a new destination is required. Records are flushed
and fsynced one by one.
usage: python m2_laurent_driver.py OUT.jsonl LEVEL DPS RAD NPTS [NPROC [PARITY]]"""
import sys, os, time, json, hashlib, multiprocessing as mpc
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
LEVEL, DPS, RAD, NPTS = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], int(sys.argv[5])
CAUCHY = ('0.1', 40)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


FP = dict(level=LEVEL, dps=DPS, rad=RAD, npts=NPTS, cauchy_rad=CAUCHY[0], cauchy_npts=CAUCHY[1],
          two_bubble_sha256=sha(os.path.join(HERE, 'two_bubble.py')), driver_sha256=sha(os.path.abspath(__file__)))


def task(j):
    mp.mp.dps = DPS
    from two_bubble import J2
    w = mp.mpf(RAD) * mp.expjpi(2 * mp.mpf(j) / NPTS)
    t0 = time.time()
    J = J2(1 - w, level=LEVEL, cauchy=(mp.mpf(CAUCHY[0]), CAUCHY[1]))
    if not all(mp.isfinite(x) for x in J):
        raise RuntimeError(f'nonfinite J2 at j={j}')
    return dict(j=j, w=[str(mp.re(w)), str(mp.im(w))], J=[[str(mp.re(x)), str(mp.im(x))] for x in J],
                level=LEVEL, dps=DPS, rad=RAD, npts=NPTS, fp=FP, time=time.time() - t0)


if __name__ == '__main__':
    done = set()
    if os.path.exists(sys.argv[1]):
        for n, line in enumerate(open(sys.argv[1]), 1):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                sys.exit(f'{sys.argv[1]}:{n}: unreadable record (truncated write?); use a new destination')
            if rec.get('fp') != FP:
                sys.exit(f'{sys.argv[1]}:{n}: record fingerprint differs from this run '
                         f'(or legacy record without fingerprint); refusing to resume, use a new destination')
            if rec['j'] in done:
                sys.exit(f'{sys.argv[1]}: point {rec["j"]} twice')
            done.add(rec['j'])
    PAR = int(sys.argv[7]) if len(sys.argv) > 7 else -1                # optional parity split across nodes
    todo = [j for j in range(NPTS // 2 + 1) if j not in done and (PAR < 0 or j % 2 == PAR)]   # j, NPTS-j conjugate
    with mpc.Pool(int(sys.argv[6]) if len(sys.argv) > 6 else 40) as pool, open(sys.argv[1], 'a') as fh:
        for r in pool.imap_unordered(task, todo):
            fh.write(json.dumps(r) + '\n'); fh.flush(); os.fsync(fh.fileno())
            print(f"j={r['j']} t={r['time']:.0f}s", flush=True)
