"""Freeze an Expanse campaign spec from a human-written request. Never overwrites.

Usage:
  python campaign.py freeze --request REQ.json --release RELEASE.json --env-python ENV/bin/python
                            --receipt RECEIPT.json --root CAMPAIGN_DIR

The request names chains (x, ladder, basis/seed SOURCE files, main step, checks,
optional seed_from) plus common numerical options and Slurm resources. Basis and
initial-seed files are copied into CAMPAIGN_DIR/inputs/<chain>/ (stable home paths)
and bound by sha256. The receipt must have passed for the same tar, source and env.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,re,shutil,subprocess,sys,time,uuid
from pathlib import Path
from common import SPEC_SCHEMA,SpecError,atomic_json,digest,find_step,steps

ALLOWED_DIAG={'none','first','all'}
COMMON_KEYS=('backend','threads','memory_limit_gib','eig_tol','residual_tol','tuning_tol','ncv','maxiter')
SLURM_KEYS=('account','partition','cpus','mem_gb','time','lead_s','max_cont')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


WALL_RE=re.compile(r'^(?:(\d+)-)?(\d{1,3}):([0-5]\d):([0-5]\d)$')


def wall_seconds(s):
    """Strict Slurm duration: [D-]HH:MM:SS only (a bare number would mean MINUTES to Slurm; F21)."""
    m=WALL_RE.match(str(s))
    if not m:raise SpecError(f'time {s!r} must be [D-]HH:MM:SS')
    d,h,mi,se=(int(v or 0) for v in m.groups())
    return d*86400+h*3600+mi*60+se


def canonical_wall(seconds):
    return f'{seconds//86400}-{seconds%86400//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}'


def check_slurm(name,cs):
    """Policy on the values actually submitted: shared only, <=240 GB, <=48 h, sane lead/continuations."""
    for k in SLURM_KEYS:
        if k not in cs:raise SpecError(f'{name}: slurm.{k} missing')
    if cs['account']!='<ACCOUNT>':raise SpecError(f'{name}: account must be <ACCOUNT>')
    if cs['partition']!='shared':raise SpecError(f'{name}: this layer submits to the shared partition only')
    if not 1<=int(cs['cpus'])<=128:raise SpecError(f'{name}: cpus must be in [1,128]')
    if not 1<=int(cs['mem_gb'])<=240:raise SpecError(f'{name}: mem_gb must be in [1,240] (shared MaxMemPerNode)')
    w=wall_seconds(cs['time'])
    if not 3600<=w<=48*3600:raise SpecError(f'{name}: time must be within [1 h, 48 h]')
    if not 1800<=int(cs['lead_s'])<=min(65535,w//2):raise SpecError(f'{name}: lead_s must be in [1800, min(65535, wall/2)]')
    if not 0<=int(cs['max_cont'])<=2:raise SpecError(f'{name}: max_cont must be 0, 1 or 2')
    cs['time']=canonical_wall(w)          # render exactly the validated duration


def bath_dimension(L):
    # Same exact count as ht2d.basis.dimension (copied to avoid importing numba here).
    dp=[0]*(L+1);dp[0]=1
    for n in range(1,L+1):
        for _ in range(n+1):
            for k in range(n,L+1):dp[k]+=dp[k-n]
    return sum(dp)


def publish_noclobber(path,data):
    """Write to a temp file, then hard-link into place: fails instead of replacing an existing spec."""
    tmp=Path(str(path)+f'.{uuid.uuid4().hex}.tmp')
    atomic_json(tmp,data)
    try:os.link(tmp,path)
    finally:tmp.unlink(missing_ok=True)


def check_edges(spec):
    """The step graph is executable (IR-07): nonempty ladders, unique step outputs, and every seed
    rooted in a frozen initial seed, a teacher step (train_keep, optional frozen guess), or a seed_from
    edge to a chain that is itself ROOTED (no chains of seed_from, hence no cycles; F18 rules too)."""
    chains=spec['chains'];outputs=set()
    for name,c in chains.items():
        if not c['ladder']:raise SpecError(f'{name}: empty ladder')
        for s in steps(spec,name):
            if s['output'] in outputs:raise SpecError(f'{name}: duplicate step output {s["output"]}')
            outputs.add(s['output'])
        for part in [c['main'],*c.get('checks',[])]:
            g=part.get('guess')
            if g is not None:
                if part is not c['main'] or not c['main'].get('train_keep') or c.get('initial_seed') or c.get('seed_from'):
                    raise SpecError(f'{name}: a frozen guess is only allowed on an unseeded teacher main step')
                if not (isinstance(g,list) and len(g)==2 and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in g)):
                    raise SpecError(f'{name}: guess must be two finite numbers')
        if c.get('seed_from'):
            ref=c['seed_from']
            if ref['chain'] not in chains or ref['chain']==name:raise SpecError(f'{name}: seed_from unknown chain')
            if chains[ref['chain']]['x']!=c['x']:raise SpecError(f'{name}: cross-x seed_from is forbidden')
            if int(ref['L'])!=c['ladder'][0]:raise SpecError(f'{name}: seed_from L must equal its first cutoff')
            find_step(spec,ref['chain'],int(ref['L']),int(ref['nz']))
            if c.get('initial_seed'):raise SpecError(f'{name}: give either seed_from or an initial seed')
            if chains[ref['chain']].get('seed_from'):raise SpecError(f'{name}: seed_from must point to a rooted chain (no chains/cycles)')
        elif not c.get('initial_seed') and not c['main'].get('train_keep'):
            raise SpecError(f'{name}: needs an initial seed, a seed_from edge, or is a teacher (train_keep)')


def env_identity(python):
    p=subprocess.run([python,'-E','-s',str(Path(__file__).with_name('envcheck.py'))],capture_output=True,text=True,check=True)
    return json.loads(p.stdout)['env_id']


def freeze(req,release,env_python,receipt_path,root):
    # Absolute paths for everything a later job or tool resolves (IR2-05). abspath (not resolve) keeps
    # the venv interpreter symlink, which is what selects the frozen environment.
    env_python=os.path.abspath(env_python);receipt_path=os.path.abspath(receipt_path)
    for k in ('tar','manifest'):
        if not os.path.isabs(release[k]):raise SpecError(f'release {k} path must be absolute')
    req={**req,'logs':os.path.abspath(req['logs'])}
    root=Path(root).resolve();spec_path=root/'spec.json'
    # Exclusive ownership BEFORE touching anything (IR-06): the campaign directory must not exist and
    # is created atomically; a losing concurrent freeze fails here without modifying any file.
    root.parent.mkdir(parents=True,exist_ok=True)
    try:os.mkdir(root)
    except FileExistsError:raise FileExistsError(f'{root} exists; campaigns are frozen once into a NEW directory') from None
    for k in ('tar','tar_sha256','manifest','manifest_sha256','source_sha256'):
        if k not in release:raise SpecError(f'release record lacks {k}')
    if sha(release['tar'])!=release['tar_sha256'] or sha(release['manifest'])!=release['manifest_sha256']:
        raise SpecError('Release tar/manifest differ from the release record')
    env_id=env_identity(env_python)
    receipt=json.loads(Path(receipt_path).read_text())
    if not (receipt.get('passed') is True and receipt.get('tar_sha256')==release['tar_sha256']
            and receipt.get('manifest_sha256')==release['manifest_sha256']
            and receipt.get('source_sha256')==release['source_sha256'] and receipt.get('env_id')==env_id):
        raise SpecError('Receipt did not pass for this release and environment')
    slurm=req['slurm']
    chains={}
    for name,c in req['chains'].items():
        if not name.replace('.','').replace('_','').replace('-','').isalnum():raise SpecError(f'bad chain name {name}')
        common={**req['common'],**c.get('common',{})}
        for k in COMMON_KEYS:
            if k not in common:raise SpecError(f'common.{k} missing for {name}')
        cs={**slurm,**c.get('slurm',{})};check_slurm(name,cs)   # the EFFECTIVE resources (F17)
        if int(common['threads'])!=int(cs['cpus']):raise SpecError(f'{name}: threads must equal slurm cpus')
        if float(common['memory_limit_gib'])>=float(cs['mem_gb']):raise SpecError(f'{name}: memory_limit_gib must be below mem_gb')
        ladder=[int(L) for L in c['ladder']]
        if ladder!=sorted(set(ladder)) or any(L%2 for L in ladder) or (len(ladder)>1 and any(b-a!=2 for a,b in zip(ladder,ladder[1:]))):
            raise SpecError(f'{name}: ladder must be consecutive even cutoffs')
        for part in [c['main'],*c.get('checks',[])]:
            if part['diagnostics'] not in ALLOWED_DIAG:raise SpecError('bad diagnostics')
        inputs=root/'inputs'/name;inputs.mkdir(parents=True,exist_ok=True)
        out={'x':float(c['x']),'ladder':ladder,'main':c['main'],'checks':c.get('checks',[]),'common':common,'slurm':cs,
             'max_bath_states':{str(L):max(2_000_000,bath_dimension(L)) for L in ladder}}
        if c.get('basis_src'):
            dst=inputs/Path(c['basis_src']).name;shutil.copy2(c['basis_src'],dst)
            out['basis']={'path':str(dst),'sha256':sha(dst),'source':str(Path(c['basis_src']).resolve())}
        if c.get('initial_seed_src'):
            dst=inputs/('seed_'+Path(c['initial_seed_src']).name);shutil.copy2(c['initial_seed_src'],dst)
            out['initial_seed']={'path':str(dst),'sha256':sha(dst),'origin':c['initial_seed_origin'],
                                 'source':str(Path(c['initial_seed_src']).resolve())}
        if c.get('seed_from'):out['seed_from']={k:c['seed_from'][k] for k in ('chain','L','nz')}
        chains[name]=out
    spec={'schema':SPEC_SCHEMA,'campaign':req['campaign'],'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
          'root':str(root),'logs':req['logs'],
          'release':{k:release[k] for k in ('commit','tar','tar_sha256','manifest','manifest_sha256','source_sha256')},
          'env':{'python':env_python,'env_id':env_id},
          'receipt':{'path':receipt_path,'sha256':sha(receipt_path)},
          'chains':chains}
    spec['sha256']=digest(spec)
    check_edges(spec)
    publish_noclobber(spec_path,spec)
    return spec_path,hashlib.sha256(spec_path.read_bytes()).hexdigest()


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='cmd',required=True)
    f=sub.add_parser('freeze');f.add_argument('--request',required=True);f.add_argument('--release',required=True)
    f.add_argument('--env-python',required=True);f.add_argument('--receipt',required=True);f.add_argument('--root',required=True)
    a=ap.parse_args(argv)
    req=json.loads(Path(a.request).read_text());rel=json.loads(Path(a.release).read_text())
    path,s=freeze(req,rel,a.env_python,a.receipt,a.root)
    print(f'frozen {path}\nsha256 {s}');return 0


if __name__=='__main__':raise SystemExit(main())
