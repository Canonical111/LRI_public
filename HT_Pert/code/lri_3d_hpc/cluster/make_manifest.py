#!/usr/bin/env python3
"""Regenerate RELEASE_MANIFEST.json (sha256 and size of every tracked file except itself).

Run in the repository after changing tracked files and before the release commit; the
format is the package's original 'sha256-file-manifest-v1'.
"""
import hashlib, json, subprocess, time
from pathlib import Path

root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())
files = sorted(f for f in subprocess.check_output(['git', '-C', str(root), 'ls-files'], text=True).split()
               if f != 'RELEASE_MANIFEST.json')
manifest = dict(format='sha256-file-manifest-v1', date=time.strftime('%Y-%m-%d'),
                release='3D Hamiltonian-truncation coefficient HPC optimization, Expanse/symmetry port',
                files={f: dict(bytes=(root/f).stat().st_size,
                               sha256=hashlib.sha256((root/f).read_bytes()).hexdigest()) for f in files})
(root/'RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print(f'{len(files)} files')
