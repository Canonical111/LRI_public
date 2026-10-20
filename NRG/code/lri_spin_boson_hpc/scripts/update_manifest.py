"""Regenerate MANIFEST.sha256.json from the git-tracked files (run before committing a release)."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parents[1]
files=subprocess.run(['git','ls-files'],cwd=root,capture_output=True,text=True,check=True).stdout.split()
files=sorted(f for f in files if f!='MANIFEST.sha256.json')
record={'schema':1,'meaning':'SHA-256 of distribution files; excludes this manifest and runtime caches. Not a physics certificate.',
        'files':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files}}
(root/'MANIFEST.sha256.json').write_text(json.dumps(record,indent=2)+'\n')
print('Recorded',len(files),'files')
