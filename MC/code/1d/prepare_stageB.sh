#!/bin/bash
# Stage B of the Δσ scan for one point: prepare $POINT/stageB (N = 131072, 262144, 524288; 5 β, 8 replicas, 2 M sweeps)
# from a forecast CSV (columns s,N,beta[,halfwidth]) and register it as the active grid for the three stage-B pairs.
# Usage on Expanse: prepare_stageB.sh POINT_DIR CENTRES_CSV SEED_BASE
# Widened sizes (halfwidth column larger than nominal) are prepared as separate one-size campaigns stageB_<N>.
set -euo pipefail
source /etc/profile.d/modules.sh; module purge; module load cpu/0.15.4 gcc/10.2.0 anaconda3 slurm/expanse/23.02.7
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
D=${1:?point dir}; CSV=${2:?centres csv}; SEED=${3:?seed base}
cd ~/lri_cluster
python3 - "$D" "$CSV" "$SEED" <<'PY'
import csv, json, subprocess, sys, os
import sys as _sys, os as _os; _sys.path.insert(0,_os.path.expanduser('~/lri_cluster')); import registry; from pathlib import Path
D, CSV, SEED = sys.argv[1], sys.argv[2], int(sys.argv[3])
rows = list(csv.DictReader(open(CSV))); s = float(rows[0]['s'])
def nominal(N): return 0.005 * (N / 1024) ** (-0.35)
groups = {}   # halfwidth -> rows (nominal ones share one campaign)
for r in rows:
    N = int(r['N']); h = float(r.get('halfwidth', nominal(N)) or nominal(N))
    key = 'stageB' if abs(h - nominal(N)) < 1e-9 else f'stageB_{N}'
    groups.setdefault(key, []).append((N, float(r['beta']), h))
reg = json.load(open(f'{D}/campaigns.json'))
names = {c['name'] for c in reg['campaigns']}
for i, (name, rr) in enumerate(sorted(groups.items())):
    if name in names: print(f'{name}: already registered, skipped'); continue
    sizes = [N for N, _, _ in rr]; cfile = f'{D}/centers_{name}.csv'
    open(cfile, 'w').write('s,N,beta\n' + ''.join(f'{s},{N},{b:.8f}\n' for N, b, _ in rr))
    if name == 'stageB': args = ['--beta-halfwidth', '0.005', '--window-exponent', '0.35']
    else: args = ['--beta-halfwidth', f'{rr[0][2]:.6f}', '--window-exponent', '0']
    cmd = ['python3', 'prepare.py', '--out', f'{D}/{name}', '--s', str(s), '--sizes', *map(str, sizes), '--replicas', '8',
           '--measurements', '2000000', '--warmup', '50000', '--beta-points', '5', *args, '--centers', cfile, '--seed-base', str(SEED + i)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode: print(f'{name}: prepare FAILED: {out.stderr.strip()[-300:]}'); sys.exit(1)
    plan = json.load(open(f'{D}/{name}/plan.json'))
    entry = {"name": name, "dir": name, "stage": "B", "seed_base": SEED + i, "s": [s], "sizes": sizes, "status": "prepared", "job_ids": [], "centres_from": os.path.basename(CSV)}
    def register(r, entry=entry, name=name, sizes=sizes):   # IR19-002: reload under the registry lock, append, atomic write
        if any(c['name'] == name for c in r['campaigns']): raise SystemExit(f'{name} already registered (concurrent preparation?)')
        r['campaigns'].append(entry)
        for N in sizes:   # append to the active list, never replace an active union (§4.7, IR5-003)
            cur = r['active'].get(f'{s}:{N}', []); cur = [cur] if isinstance(cur, str) else list(cur)
            if name not in cur: cur.append(name)
            r['active'][f'{s}:{N}'] = cur
    registry.locked_update(Path(f'{D}/campaigns.json'), register, validate=False)
    print(f'{os.path.basename(D)} {name}: {plan["tasks"]} tasks, sizes {sizes}, centres {[round(b,6) for _, b, _ in rr]}')
PY
python3 registry.py $D/campaigns.json --require all >/dev/null && echo "  registry OK (all 10 pairs active)"
