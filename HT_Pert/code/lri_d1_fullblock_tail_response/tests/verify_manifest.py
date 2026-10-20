from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    n=0
    for line in (ROOT/'MANIFEST.sha256').read_text().splitlines():
        digest,name=line.split('  ',1);p=(ROOT/name).resolve()
        assert p.is_relative_to(ROOT) and p.is_file(),name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
        n+=1
    print(n,'manifest files verified')
if __name__=='__main__':main()
