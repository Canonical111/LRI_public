"""Scratch packages for the C8(3) orchestration tests (Stage 3a; PLAN F). Nothing here writes into the package.

make(td) builds <td>/pkg: a copy of tools/, slurm/, references/, cost_models/, the vendored assembly (hard links),
reference/records/*/config.json, tests/fixtures/{run1_groups.json,cost_model_synthetic.json}, the HD6 mirror
designs/forbidden_seeds.json (as in every export: a non-test plan on symmetry checks against it, A1) and a SYNTHETIC
complete inputs/ (schema c8-d3-hpc-inputs-1, l7_complete and l8_present true): per sector and loop L = 3..8 a few
synthetic G-files (magic C7D3GRAPH1, the fake worker reads nothing else), labelled synthetic in the manifest, with
synthetic inspect fields (products, segments, addends, numerators, kernel_bytes, fmax) and varied monomials/terms so
that the pilot strata (sector x T bin x M tertile) are populated. The low-loop files are the package's real ones and
the vendored pins are copied from the real manifest, so prepare_inputs.verify() accepts the inputs. The manifest's
"synthetic" label (prepare_inputs.SYNTHETIC_INPUTS_LABEL, no H1 or d3 pin) alone makes every plan test-only; a NON-test
plan is possible in the scratch package through a test seam only (R2-S1-02), never through the manifest: tool() runs
`production.py plan` with the validator injected in-process (INJECT; any C8_SITE, real sites included), and env() adds
the environment's seam SEAM to every C8_SITE=fake environment, for the plans the fake Slurm's jobs and the tests'
own subprocesses make (prepare_inputs honours it under C8_SITE=fake on a host that is no real site); either skips
inventory_complete (recorded in the plan's input-gate result). bin/c8d3_{gmp,decimal} are tests/fake_worker.py.
"""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SECTORS=('free','power')
DEFAULT_COUNTS={'free':{3:2,4:2,5:3,6:3,7:4,8:6},'power':{3:1,4:2,5:2,6:3,7:3,8:5}}
if str(ROOT/'tools')not in sys.path:sys.path.append(str(ROOT/'tools'))
from prepare_inputs import SYNTHETIC_INPUTS_LABEL as LABEL, SYNTHETIC_SEAM  # noqa: E402  (S4-003, R2-S1-02)
SEAM={SYNTHETIC_SEAM:'1'}   # the environment's test seam (honoured under C8_SITE=fake off the real sites)

def link(src,dst):
    try:os.link(src,dst)
    except OSError:shutil.copy2(src,dst)

def _sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def gfile(sector:str,L:int,gid:int)->bytes:
    """A synthetic G-file: L = loops, E = 2L, 4 masks, 2 terms (the fake worker only checks that it exists)."""
    return (f'C7D3GRAPH1 {L} {gid} 1.5 {"0.5"if sector=="power"else"0"}\n4 2\n'+''.join(f'{(1<<L)-1+k}\n'for k in range(4))+
            f'synthetic {sector} L{L} G{gid}\n').encode()

def build_inputs(d:Path,counts=None,l8=True,primitives=None)->dict:
    """Synthetic complete inputs in d (inputs/ of a scratch package)."""
    counts=counts or DEFAULT_COUNTS;d.mkdir(parents=True,exist_ok=True);(d/'packs').mkdir(exist_ok=True);(d/'order7').mkdir(exist_ok=True)
    real=json.loads((ROOT/'inputs/manifest.json').read_bytes())
    pins={}
    for n in ('two_loop.json','gamma_d3_8.txt'):shutil.copy2(ROOT/'inputs'/n,d/n);pins[n]=_sha((d/n).read_bytes())
    for n in ('two_loop.json','gamma_d3_7.txt'):shutil.copy2(ROOT/'inputs/order7'/n,d/'order7'/n);pins[f'order7/{n}']=_sha((d/'order7'/n).read_bytes())
    inv={'inspect_complete':True,'synthetic':LABEL}
    for s in SECTORS:
        inv[s]={}
        for L in range(3,9):
            if L==8 and not l8:continue
            n=counts[s][L];off=0;pack=b'';rows=[]
            nprim=(primitives or{}).get((s,L),(2 if L==8 else 1 if L==7 else 0)if s=='free'else 0)
            for gid in range(n):
                data=gfile(s,L,gid);M=4+(gid*7)%60;T=1+(gid*37)%140
                A=1000*L*L+137*gid;kb=(2**20)*(1+gid%5)
                rows.append({'id':gid,'primitive':gid<nprim,'s_G':4 if gid%7==3 else 6,'wa':'1.5','wb':'0.5','offset':off,'length':len(data),'sha256':_sha(data),
                             'monomials':M,'terms':T,'cost':max(1,M*T),'products':A//2,'segments':3+gid%4,'addends':A-A//2,'numerators':2+gid%3,
                             'kernel_bytes':kb,'fmax':1+gid%3,'double_lift':gid%2})
                pack+=data;off+=len(data)
            (d/f'packs/{s}_L{L}.pack').write_bytes(pack);pins[f'packs/{s}_L{L}.pack']=_sha(pack);inv[s][str(L)]=rows
    data=(json.dumps(inv,indent=1)+'\n').encode();(d/'inventory.json').write_bytes(data);pins['inventory.json']=_sha(data)
    cnt={s:{str(L):len(inv[s][str(L)])for L in range(3,9)if str(L)in inv[s]}for s in SECTORS}
    m={'schema':'c8-d3-hpc-inputs-1','dimension':3,'order':8,'epsilon':'2s-3','sha256':pins,'counts':cnt,'kernels':sum(sum(v.values())for v in cnt.values()),
       'l7_complete':True,'l8_present':bool(l8),'inspect_complete':True,'synthetic':LABEL,
       'vendored_assembly_handoff_sha256':real['vendored_assembly_handoff_sha256'],'vendored_assembly':real['vendored_assembly'],
       'inventory8_d2_manifest_sha256':None,'d3_payload_manifest_sha256':None}
    (d/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    return m

def install_fake_bin(pkg:Path,python=sys.executable)->None:
    (pkg/'bin').mkdir(exist_ok=True)
    for exe in ('c8d3_gmp','c8d3_decimal'):
        f=pkg/'bin'/exe
        if f.exists():f.unlink()
        f.write_text(f'#!{python}\n'+(ROOT/'tests/fake_worker.py').read_text());f.chmod(0o755)

def make(td:Path,name='pkg',counts=None,l8=True,primitives=None)->Path:
    pkg=Path(td)/name;(pkg/'tools').mkdir(parents=True)
    for f in (ROOT/'tools').iterdir():
        if f.is_file()and f.suffix in('.py','.json'):shutil.copy2(f,pkg/'tools'/f.name)
    for d in ('slurm','references','cost_models'):shutil.copytree(ROOT/d,pkg/d)
    shutil.copytree(ROOT/'vendor',pkg/'vendor',copy_function=link)
    for f in (ROOT/'reference/records').glob('*/config.json'):
        (pkg/'reference/records'/f.parent.name).mkdir(parents=True,exist_ok=True);shutil.copy2(f,pkg/'reference/records'/f.parent.name/'config.json')
    for rel in ('reference/c8d3_recon/out/l8cost.log','reference/SHA256SUMS_c8'):
        (pkg/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,pkg/rel)
    (pkg/'tests/fixtures').mkdir(parents=True)
    for n in ('run1_groups.json','cost_model_synthetic.json'):
        if (ROOT/'tests/fixtures'/n).exists():shutil.copy2(ROOT/'tests/fixtures'/n,pkg/'tests/fixtures'/n)
    (pkg/'designs').mkdir();shutil.copy2(ROOT/'designs/forbidden_seeds.json',pkg/'designs/forbidden_seeds.json')   # the HD6 mirror, as in an export (A1)
    build_inputs(pkg/'inputs',counts,l8,primitives);install_fake_bin(pkg)
    return pkg

CLEAN_ENV=('SLURM_ARRAY_TASK_ID','C8_INDEX_OFFSET','SLURM_TMPDIR','SLURM_JOB_ID','SLURM_JOB_NAME','C8_LANES','C8_LANE_SECONDS','C8_FAKE_FAIL','C8_FAKE_SLEEP',
           'C8_FAKE_LOG','C8_INPUTS','C8_SITE','C8_ROOT','C8_SCRATCH','C8_TEST_IO_FAULT','C8_FAKE_INTEGRAND','C8_FAKE_SPP','C8_FAKE_SPP_FILE','C8_FAKE_RUNTIME_GMP_LIBRARY','C8_ALLOW_NO_L8','C8_FAKE_OMP_EFF',
           'C8_LANE_DRILL','C8_TIME_POLICY','C8_RESERVATION','C8_BUDGET_LINE','PYTHONPATH','PYTHONPYCACHEPREFIX',
           # a real site's job environment (val1): slurm/common.sh sources C8_ENV_SETUP (~/c8d3/env.sh), which would put
           # the site's C8_SITE, C8_ROOT and C8_SEEDS back under a scratch package's job script (symmetry val1 570678)
           'C8_ENV_SETUP','C8_SEEDS',SYNTHETIC_SEAM)

def env(**extra)->dict:
    e={k:v for k,v in os.environ.items()if k not in CLEAN_ENV};e['PYTHONDONTWRITEBYTECODE']='1';e['OPENBLAS_NUM_THREADS']='1'
    e.update({k:str(v)for k,v in extra.items()if v is not None})
    if e.get('C8_SITE')=='fake':e={**SEAM,**e}   # R2-S1-02: the fakes' plans (jobs, subprocesses) may use the synthetic inputs
    return e

# R2-S1-02: the injected validator. tool() runs a plan's main() in a process whose prepare_inputs.synthetic_seam this
# driver replaces (test code only; nothing in the package sets it): these synthetic inputs, exactly, skip
# inventory_complete, under any C8_SITE and on any host (val1 runs these tests on the real sites, where the environment's
# seam is refused). Everything else is the script's own run (sys.path[0] its directory). The tool must have main(argv).
INJECT=r'''
import importlib,sys
sys.dont_write_bytecode=True;sys.path[0]=sys.argv[1]
import prepare_inputs as pi
pi.synthetic_seam=lambda env,m:(m.get('synthetic')==pi.SYNTHETIC_INPUTS_LABEL and m.get('inventory8_d2_manifest_sha256')is None
                                and m.get('d3_payload_manifest_sha256')is None)
sys.argv=sys.argv[2:];sys.exit(importlib.import_module(sys.argv[0][:-3]).main(sys.argv[1:]))
'''

def tool(pkg:Path,script:str,*args,check=True,inject=None,**extra):
    """Run tools/<script> of the scratch package (no inherited Slurm or C8 settings unless given). inject: run it under
    INJECT's validator (R2-S1-02); by default exactly for `production.py plan`."""
    if inject is None:inject=script=='production.py'and bool(args)and str(args[0])=='plan'
    cmd=['-c',INJECT,str(Path(pkg)/'tools'),script]if inject else[str(Path(pkg)/'tools'/script)]
    cp=subprocess.run([sys.executable,'-B',*cmd,*map(str,args)],capture_output=True,text=True,env=env(**extra),preexec_fn=lambda:os.umask(0o022))
    if check and cp.returncode:raise AssertionError(f'{script} {list(map(str,args))} failed ({cp.returncode}):\n{cp.stderr[-3000:]}\n{cp.stdout[-1500:]}')
    return cp

def manifest(d:Path)->dict:return json.loads((Path(d)/'manifest.json').read_text())
def config(d:Path,g:str)->dict:return json.loads((Path(d)/'groups'/g/'config.json').read_text())

def run_all(pkg:Path,d:Path,threads=2,**extra)->None:
    for j in manifest(d)['jobs']:tool(pkg,'production.py','run',d,'--index',j['id'],'--threads',threads,**extra)

def tree(d:Path)->dict:
    return {str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(Path(d).rglob('*'))if p.is_file()}

# ---------------------------------------------------------------- the stateful fake Slurm as executables (A-ORC-17's fake)
BASE_RES='mode=reservation;id=H7E-R;run=11;sub=27;acct_run=32;shared=32;dev_nodes=4'

class SlurmSite:
    """tests/fake_slurm's executables on PATH (sbatch, squeue, sacct, scancel, scontrol, sinfo, sprio, timeout) with one
    state file, a C8_ROOT with an empty ledger, and the admission settings of env.sh.example (C8_SITE=fake)."""
    def __init__(self,td:Path,name='site'):
        sys.path.insert(0,str(ROOT/'tests'))
        from fake_slurm.core import Fake,install
        self.dir=Path(td)/name;self.dir.mkdir(parents=True,exist_ok=True);self.bin=install(self.dir/'bin')
        self.fake=Fake(str(self.dir/'slurm.json'),str(self.dir/'events.jsonl'),str(self.dir/'clock.json'))
        (self.dir/'clock.json').write_text('{"offset": 0}')
        self.root=self.dir/'c8root';(self.root/'runs').mkdir(parents=True);(self.root/'ledger.jsonl').write_bytes(b'')
    def env(self,**extra)->dict:
        e={'PATH':f'{self.bin}:{os.environ["PATH"]}','C8_SITE':'fake','C8_ROOT':str(self.root),'C8_RESERVATION':BASE_RES,'C8_COMPUTE_CAP':'4',
           'C8_BUDGET_LINE':'dev','C8_LOCK_WAIT':'5','USER':'zzheng8',**self.fake.env()}
        e.update({k:str(v)for k,v in extra.items()if v is not None})
        return e
    def run_dir(self,name)->Path:return self.root/'runs'/name
    def submit(self,pkg:Path,*args,**extra):
        return tool(pkg,'slurm_submit.py',*args,check=False,**self.env(**extra))
    def jobs(self)->list:return self.fake.jobs()
    def history(self,cmd='sbatch')->list:return [h for h in self.fake.state()['history']if h['cmd']==cmd]
