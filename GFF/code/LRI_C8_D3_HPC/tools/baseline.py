#!/usr/bin/env python3
"""The Stage-3 baseline binaries bin/baseline/c8d3_{gmp,decimal} (PLAN A-RPL-8, tag c8-stage3; Stage 3b), per site.

  baseline.py record SHA256SUMS --commit SHA [--job ID] [--site S] [--forced-tiers-record PATH] [--output FILE]
  baseline.py install --store DIR [--site S]     (make baseline STORE=$C8_STORE)
  baseline.py check [--site S]                   bin/baseline/ against the record
  baseline.py sha [FILE] [--site S]              the recorded sha256 of FILE (default c8d3_gmp): the B0 of the speed and
                                                 profile jobs (native_job.sh)
  baseline.py val3 [--site S]                    the package path of the site's Stage-3 J-VAL-3 forced_tiers record
                                                 (tests/record_compare.py's reference in the forced_tiers gate)

The baseline is the default build that J-SWEEP-1 measured (its cost model's executable sha256): the sweep job copies
bin/c8d3_gmp, bin/c8d3_decimal and their build records, read-only, to $C8_STORE/baseline/<sha12 of the code commit>/
with a SHA256SUMS. `record` pins those sha256s in the site's record (committed with the model); the tag c8-stage3
marks a commit whose src/ and Makefile are those of the recorded commit. `install` copies the store's files into
bin/baseline/ of this package and verifies every sha256 against the record (a mismatch or a missing file refuses, 65,
and leaves bin/baseline/ untouched); `check` re-verifies an installed baseline. Every later kernel change is compared
with these binaries on the L8 sweep sample (A-RPL-8, Stage 4).

Sites (Amendment A1; HD9: bitwise gates hold within one toolchain only). The site is --site, else C8_SITE (expanse or
symmetry; fake, the Mac fakes, and unset use Expanse's record):
  * expanse   reference/baseline_c8_stage3.json: the c8-stage3 binaries of J-SWEEP-1 54676977 (g++ 13.3.0, the Spack
              GMP by RPATH; c8d3_gmp 24adff54...), store $C8_STORE/baseline/8b8778273bd9/ on Expanse's Lustre; J-VAL-3
              record benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/val3/forced_tiers.json.
  * symmetry  reference/baseline_c8_stage3_symmetry.json: the same commit's binaries built with symmetry's toolchain
              (g++ 11.4.0, the boost/1.77.0 headers, the system GMP 6.2.1) on an AMD AVX2 node and stored in symmetry's
              $C8_STORE/baseline/<sha12>/ (native_job.sh basestore, J-BASE-sym); its J-VAL-3 record is the symmetry
              J-VAL-3's (`forced_tiers_record`). Until that record is committed every reader refuses (65): an Expanse
              binary is never a symmetry baseline.
Python standard library only.
"""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RECORDS={'expanse':ROOT/'reference/baseline_c8_stage3.json','symmetry':ROOT/'reference/baseline_c8_stage3_symmetry.json'}
RECORD=RECORDS['expanse'];SCHEMA='c8-d3-baseline-1'
FILES=('c8d3_gmp','c8d3_gmp.buildinfo.json','c8d3_decimal','c8d3_decimal.buildinfo.json')
EXPANSE_VAL3='benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/val3/forced_tiers.json'

def sha(p:Path)->str:
    h=hashlib.sha256()
    with open(p,'rb')as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def sums(path:Path)->dict:
    out={}
    for line in Path(path).read_text().splitlines():
        h,_,name=line.partition('  ')
        if h:out[name.strip()]=h
    return out

def site_of(a=None,env=None)->str:
    s=getattr(a,'site',None)or(os.environ if env is None else env).get('C8_SITE')or'expanse'
    if s=='fake':return 'expanse'
    if s not in RECORDS:raise SystemExit(f'baseline: site {s!r} has no baseline record (expanse or symmetry)')
    return s

class NoRecord(Exception):pass

def load_record(site:str='expanse')->dict:
    path=RECORDS[site]
    if not path.is_file():
        raise NoRecord(f'baseline: no {site} baseline record ({path.relative_to(ROOT)}): the {site} c8-stage3 baseline has not been established '
                       f'(docs/HPC.md, "Symmetry", the baseline and the store); a binary of another site\'s toolchain is never used instead')
    r=json.loads(path.read_text())
    if r.get('schema')!=SCHEMA or set(r.get('files',{}))!=set(FILES):raise SystemExit(f'{path}: not a {SCHEMA} record of {", ".join(FILES)}')
    if r.get('site','expanse')!=site:raise SystemExit(f'{path}: records site {r.get("site")!r}, not {site}')
    return r

def record(a)->int:
    site=site_of(a);s=sums(a.sha256sums)
    if set(s)!=set(FILES):raise SystemExit(f'{a.sha256sums}: lists {sorted(s)}, need {list(FILES)}')
    if site!='expanse'and not a.forced_tiers_record:raise SystemExit(f'baseline record --site {site} needs --forced-tiers-record (that site\'s J-VAL-3 forced_tiers.json, a package path)')
    doc={'schema':SCHEMA,'tag':'c8-stage3','commit':a.commit,'store_dir':f'baseline/{a.commit[:12]}','files':{k:s[k]for k in FILES},
         'job':a.job,'role':'the default build J-SWEEP-1 measured (the first measured cost model\'s executable); A-RPL-8 compares every later kernel change with it'}
    if site!='expanse':
        doc.update(site=site,forced_tiers_record=a.forced_tiers_record,
                   role=f'the c8-stage3 commit built with {site}\'s toolchain on its AVX2 nodes (Amendment A1); A-RPL-8 on {site} compares every later kernel change with it')
    out=Path(a.output or RECORDS[site]);out.write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps(doc,indent=1));return 0

def install(a)->int:
    site=site_of(a);r=load_record(site);src=Path(a.store)/r['store_dir'];dst=ROOT/'bin/baseline'
    bad=[f for f in FILES if not (src/f).is_file()or sha(src/f)!=r['files'][f]]
    if bad:print(f'baseline install: {src}: {bad} missing or not at the recorded sha256 ({RECORDS[site].name}); bin/baseline/ untouched',file=sys.stderr);return 65
    dst.parent.mkdir(parents=True,exist_ok=True);tmp=Path(tempfile.mkdtemp(prefix='.baseline.',dir=dst.parent))
    for f in FILES:shutil.copy2(src/f,tmp/f)
    if [sha(tmp/f)for f in FILES]!=[r['files'][f]for f in FILES]:shutil.rmtree(tmp);print('baseline install: copy differs',file=sys.stderr);return 65
    if dst.exists():shutil.rmtree(dst)
    tmp.rename(dst);print(json.dumps({'installed':str(dst),'site':site,'commit':r['commit'],'files':r['files']},indent=1));return 0

def check(a)->int:
    site=site_of(a);r=load_record(site);dst=ROOT/'bin/baseline'
    bad=[f for f in FILES if not (dst/f).is_file()or sha(dst/f)!=r['files'][f]]
    if bad:print(f'baseline check: {bad} missing or not at the recorded sha256',file=sys.stderr);return 65
    print(json.dumps({'baseline':str(dst),'site':site,'commit':r['commit'],'status':'verified'}));return 0

def sha_of(a)->int:
    if a.file not in FILES:raise SystemExit(f'baseline sha: {a.file!r} is not one of {", ".join(FILES)}')
    print(load_record(site_of(a))['files'][a.file]);return 0

def val3(a)->int:
    site=site_of(a);r=load_record(site)
    p=EXPANSE_VAL3 if site=='expanse'else r.get('forced_tiers_record')
    if not p or not (ROOT/p).is_file():print(f'baseline val3: the {site} J-VAL-3 forced_tiers record {p!r} is missing',file=sys.stderr);return 65
    print(p);return 0

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='cmd',required=True)
    def sub(name,fn):
        q=s.add_parser(name);q.add_argument('--site',choices=sorted(RECORDS));q.set_defaults(fn=fn);return q
    q=sub('record',record);q.add_argument('sha256sums',type=Path);q.add_argument('--commit',required=True);q.add_argument('--job')
    q.add_argument('--forced-tiers-record');q.add_argument('--output')
    q=sub('install',install);q.add_argument('--store',required=True)
    sub('check',check)
    q=sub('sha',sha_of);q.add_argument('file',nargs='?',default='c8d3_gmp')
    sub('val3',val3)
    a=p.parse_args(argv)
    try:return a.fn(a)
    except NoRecord as e:print(e,file=sys.stderr);return 65

if __name__=='__main__':sys.exit(main())
