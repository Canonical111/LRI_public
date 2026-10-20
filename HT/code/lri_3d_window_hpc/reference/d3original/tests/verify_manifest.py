#!/usr/bin/env python3
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    n=0
    for line in (ROOT/'MANIFEST.sha256').read_text().splitlines():
        expected,name=line.split('  ',1);path=ROOT/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise SystemExit('Integrity failure: '+name)
        n+=1
    print(f'PASS: {n} release files verified')
if __name__=='__main__':main()
