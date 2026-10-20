"""Verify immutable release files before regeneration changes output records."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    count=0
    for line in (ROOT/'MANIFEST.sha256').read_text().splitlines():
        expected,relative=line.split('  ',1)
        path=(ROOT/relative).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Unsafe manifest path: '+relative)
        if not path.is_file():raise FileNotFoundError(path)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise AssertionError('Checksum mismatch: '+relative)
        count+=1
    print(f'Verified {count} files.')
if __name__=='__main__':main()
