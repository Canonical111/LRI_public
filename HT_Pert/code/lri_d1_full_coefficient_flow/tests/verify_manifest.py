from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    rows=(ROOT/'MANIFEST.sha256').read_text().splitlines()
    for line in rows:
        expected,rel=line.split('  ',1);p=(ROOT/rel).resolve()
        if not p.is_relative_to(ROOT):raise ValueError('Unsafe manifest path')
        assert p.is_file(),rel
        assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,rel
    print(f'Verified {len(rows)} manifest entries.')
if __name__=='__main__':main()
