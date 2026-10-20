from pathlib import Path
import hashlib
R=Path(__file__).resolve().parents[1];count=0
for line in (R/'MANIFEST.sha256').read_text().splitlines():
 expected,name=line.split('  ',1);p=R/name
 assert p.is_file(),name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
 count+=1
print(f'Verified {count} files.')
