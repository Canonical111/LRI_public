#!/usr/bin/env python3
"""Cross-node flock drill (two srun tasks on two nodes): task 0 holds an exclusive flock on
argv[1] for argv[2] seconds; task 1 waits, then must fail a non-blocking attempt.
Prints one JSON line per task; exit 0 only if the observed behaviour is cluster-wide locking."""
import fcntl, json, os, socket, sys, time
path, hold = sys.argv[1], float(sys.argv[2])
rank = int(os.environ['SLURM_PROCID'])
with open(path, 'a+b') as f:
    if rank == 0:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        print(json.dumps(dict(rank=0, host=socket.gethostname(), held=True)), flush=True)
        time.sleep(hold)
        sys.exit(0)
    time.sleep(hold/3)
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        blocked = False
    except BlockingIOError:
        blocked = True
    print(json.dumps(dict(rank=rank, host=socket.gethostname(), blocked=blocked)), flush=True)
    sys.exit(0 if blocked else 1)
