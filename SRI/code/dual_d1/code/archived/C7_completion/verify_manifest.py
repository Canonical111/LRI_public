from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parent
m=json.loads((r/"MANIFEST.json").read_text())
for row in m["files"]:
 p=r/row["path"]
 assert p.is_file(),p
 assert hashlib.sha256(p.read_bytes()).hexdigest()==row["sha256"],p
print("All",len(m["files"]),"manifested files match their SHA-256 hashes.")
