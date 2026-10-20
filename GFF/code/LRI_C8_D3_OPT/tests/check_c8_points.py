#!/usr/bin/env python3
"""Re-run the archived selection of twelve actual C8 forest precision checks."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, default=ROOT/'verification/new_graphs.json')
    parser.add_argument('--graph-root', type=Path, default=ROOT/'inputs')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    selected = json.loads(args.selection.read_text())
    paths = []
    for row in selected['graphs']:
        path = args.graph_root/row['sector']/f"L{row['L']}"/f"G{row['id']}.txt"
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError(f'Graph hash changed: {path}')
        paths.append(path.resolve())
    with tempfile.NamedTemporaryFile('w', prefix='c8_points_', dir=ROOT/'bin') as f:
        f.write('\n'.join(map(str, paths))+'\n')
        f.flush()
        cp = subprocess.run([str(ROOT/'bin/point_checks_gmp'), f.name], check=True,
                            capture_output=True, text=True)
    result = json.loads(cp.stdout)
    if result['checks'] != 4*len(paths):
        raise AssertionError('not every selected graph/point was checked')
    if args.output:
        args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
