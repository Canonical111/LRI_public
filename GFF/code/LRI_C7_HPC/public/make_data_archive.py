#!/usr/bin/env python3
"""Build the hosted C7(1) record archive from the production campaign tree (maintainer tool; run where the data are).

Reads only. From <tree> (the production directory holding batches/ and primitive/) it selects, for the 399 batches
listed in results/C7_1/combined_assembly.json and the direct primitive campaign P1:

  batches/bNNN/{production.json, assembly.json, full_affine_assembly.json, C7_result.json}
  batches/bNNN/<campaign>/{manifest.json, merged/audit.json, merged/N*.json}      (the 24 campaigns of production.json)
  primitive/P1/{manifest.json, merged/audit.json, merged/N0.json}

and never checkpoints/, tasks_*.txt, sobol.net, inputs/, logs or quarantined files. Every selected file must exist;
every merged stream must match the SHA-256 recorded in results/C7_1/C7_final.json. It writes, under --out:
  c7_hpc/MANIFEST.sha256        sha256 and path of every archived file (relative to c7_hpc/)
  C7_1_merged_records.tar.gz    the files above, paths starting with c7_hpc/
  C7_1_merged_records.json      counts, sizes and the tarball's sha256 (for DATA.md and public/data_C7_1.json)
Run it in a batch job, not on a login node (about 35k small files are read; on Expanse Lustre allow 30-60 min).
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, tarfile, time
from pathlib import Path


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tree', type=Path, required=True, help='production directory containing batches/ and primitive/')
    ap.add_argument('--results', type=Path, default=Path(__file__).resolve().parents[3] / 'results/C7_1')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    tree = a.tree.resolve(); out = a.out.resolve(); stage = out / 'c7_hpc'
    fin = json.loads((a.results / 'C7_final.json').read_text()); ca = json.loads((a.results / 'combined_assembly.json').read_text())
    labels = [b['label'] for b in ca['batches']]
    files: list[str] = []
    for l in labels:
        b = f'batches/{l}'
        files += [f'{b}/{x}' for x in ('production.json', 'assembly.json', 'full_affine_assembly.json', 'C7_result.json')]
        prod = json.loads((tree / b / 'production.json').read_text())
        for c in prod['campaigns']:
            m = json.loads((tree / b / c / 'manifest.json').read_text())
            files += [f'{b}/{c}/manifest.json', f'{b}/{c}/merged/audit.json'] + [f'{b}/{c}/merged/N{N}.json' for N in m['degrees']]
    files += ['primitive/P1/manifest.json', 'primitive/P1/merged/audit.json', 'primitive/P1/merged/N0.json']
    missing = [f for f in files if not (tree / f).is_file()]
    if missing:
        sys.exit(f'{len(missing)} selected files missing, e.g. {missing[:5]}')
    want = {}
    for s in fin['sources']:
        for k in ('path', 'subtract'):
            if k in s:
                want[s[k].replace('../../', '', 1)] = s[k + '_sha256']
    t0 = time.time(); lines = []; size = 0
    for f in files:
        h = sha(tree / f); size += (tree / f).stat().st_size; lines.append(f'{h}  {f}')
        if f in want and want[f] != h:
            sys.exit(f'{f}: sha256 {h} differs from C7_final.json ({want[f]})')
    if set(want) - set(files):
        sys.exit('streams named by C7_final.json not selected: ' + ', '.join(sorted(set(want) - set(files))[:5]))
    stage.mkdir(parents=True, exist_ok=True)
    (stage / 'MANIFEST.sha256').write_text('\n'.join(lines) + '\n')
    tgz = out / 'C7_1_merged_records.tar.gz'
    with tarfile.open(tgz, 'w:gz', compresslevel=6) as t:
        t.add(stage / 'MANIFEST.sha256', arcname='c7_hpc/MANIFEST.sha256')
        for f in files:
            t.add(tree / f, arcname=f'c7_hpc/{f}', recursive=False)
    info = {'files': len(files) + 1, 'bytes_uncompressed': size, 'tarball': tgz.name, 'tarball_bytes': tgz.stat().st_size,
            'tarball_sha256': sha(tgz), 'manifest_sha256': sha(stage / 'MANIFEST.sha256'), 'batches': len(labels),
            'seconds': round(time.time() - t0, 1)}
    (out / 'C7_1_merged_records.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
