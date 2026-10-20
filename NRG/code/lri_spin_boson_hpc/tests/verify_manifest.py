"""Verify distribution files; this is integrity checking, not scientific validation."""
from pathlib import Path
import hashlib
import json


def main():
    root=Path(__file__).resolve().parents[1]
    record=json.loads((root/'MANIFEST.sha256.json').read_text())
    errors=[]
    for name,expected in record['files'].items():
        path=root/name
        if not path.is_file():errors.append('missing: '+name)
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            errors.append('changed: '+name)
    if errors:raise SystemExit('\n'.join(errors))
    print('Verified',len(record['files']),'distribution files')

if __name__=='__main__':main()
