#!/usr/bin/env python3
"""Build the release tar that cluster jobs stage: `git archive` of HEAD of a clean tree.

Writes OUT/lri2d_coeff-<commit12>.tar, its .sha256 and a .json record (commit, sha256, solver source digest),
after checking every MANIFEST.sha256 entry against the tar. Copy all three to $LRI_COEFF_DATA/releases/ on the
cluster and unpack a login-node copy from the same tar (docs/CLUSTER.md). Standard library and git only.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,tarfile,datetime
ROOT=Path(__file__).resolve().parents[1]
PREFIX='lri_d2_coeff_hpc/'

def git(*a):return subprocess.run(['git','-C',str(ROOT),*a],check=True,capture_output=True,text=True).stdout
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if git('status','--porcelain','--untracked-files=no').strip():raise SystemExit('tracked files have uncommitted changes; commit first')
    commit=git('rev-parse','HEAD').strip();name=f'lri2d_coeff-{commit[:12]}';a.out.mkdir(parents=True,exist_ok=True)
    tar=a.out/f'{name}.tar'
    if tar.exists():raise SystemExit(f'{tar} exists')
    subprocess.run(['git','-C',str(ROOT),'archive','--format=tar',f'--prefix={PREFIX}','-o',str(tar.resolve()),commit],check=True)
    with tarfile.open(tar) as t:
        files={m.name:m for m in t.getmembers() if m.isfile()}
        data=lambda n:t.extractfile(files[n]).read()
        count=0
        for line in data(PREFIX+'MANIFEST.sha256').decode().splitlines():
            expected,rel=line.split('  ',1)
            if PREFIX+rel not in files or hashlib.sha256(data(PREFIX+rel)).hexdigest()!=expected:
                tar.unlink();raise SystemExit(f'MANIFEST.sha256 entry {rel} does not match the commit; regenerate the manifest')
            count+=1
        src={n.split('/')[-1]:hashlib.sha256(data(n)).hexdigest() for n in sorted(files) if n.count('/')==3 and n.startswith(PREFIX+'src/lri_coeff/') and n.endswith(('.py','.cpp'))}
    sha=hashlib.sha256(tar.read_bytes()).hexdigest()
    source=hashlib.sha256(json.dumps(src,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    (a.out/f'{name}.tar.sha256').write_text(f'{sha}  {tar.name}\n')
    rec=dict(name=tar.name,commit=commit,sha256=sha,source_digest=source,manifest_files=count,created=datetime.datetime.now().astimezone().isoformat(timespec='seconds'))
    (a.out/f'{name}.json').write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps(rec,indent=1))
if __name__=='__main__':main()
