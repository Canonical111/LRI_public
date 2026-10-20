"""Cross-node item ownership for campaign roots on a shared filesystem.

flock is node-local on BeeGFS, so it cannot keep two nodes out of one item. A
campaign root (marked by `.campaign`) therefore adds an owner token per item.
Only the login-host submitter creates or replaces `<item>/.owner`; every
writer must present the current token. Each token carries a generation N and a
writer with generation N writes only inside `<item>/gNNNN/`, so a surviving
process of an older generation can never replace files of the current one.
Outside campaign roots nothing changes.
"""
from __future__ import annotations
import hashlib,json,os,re,shutil,tempfile
from pathlib import Path
from .io import _atomic,read_record,IntegrityError,canonical

MARK='.campaign'
OWNER='.owner'
ID_RE=re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}')
GEN_RE=re.compile(r'g(\d{4,})')
SKIP_SEED=('.claim.lock',)
RESERVED={'SUBMITTED.jsonl','lanes'}   # campaign metadata next to the item folders

class OwnershipError(RuntimeError):pass


def gen_name(generation):
    return f'g{int(generation):04d}'


def is_campaign_root(path):
    return (Path(path)/MARK).is_file()


def campaign_of(path):
    """(root, relative parts) when path lies inside a campaign root, else None."""
    p=Path(path).resolve()
    for candidate in (p,*p.parents):
        if is_campaign_root(candidate):
            return candidate,p.relative_to(candidate).parts
    return None


def read_owner(item):
    path=Path(item)/OWNER
    try:data=json.loads(path.read_text())
    except FileNotFoundError:raise OwnershipError(f'{item}: no owner file; items in a campaign root are created by the submitter') from None
    except (OSError,ValueError) as exc:raise OwnershipError(f'{path}: unreadable owner file ({exc})') from None
    if not (isinstance(data,dict) and isinstance(data.get('token'),str) and data['token']
            and isinstance(data.get('generation'),int) and data['generation']>=1):
        raise OwnershipError(f'{path}: malformed owner file')
    return data


def _owner_bytes(data):
    return json.dumps(data,indent=2,sort_keys=True).encode()+b'\n'


def item_digest(item):
    """Immutable definition of a manifest item; an ID never changes meaning in a campaign."""
    return hashlib.sha256(canonical(item)).hexdigest()


def publish_new(path,blob):
    """Publish a complete file only if none exists: write and fsync a temp, then link().

    link() fails with EEXIST instead of replacing, and is atomic in one BeeGFS
    directory, so a crash leaves either no file or the complete file.
    """
    path=Path(path);fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        os.link(tmp,path)
        dfd=os.open(path.parent,os.O_DIRECTORY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
    finally:
        os.unlink(tmp)


def create_owner(item,data):
    """First owner of an item; raises FileExistsError if any owner exists."""
    item=Path(item);item.mkdir(parents=True,exist_ok=True)
    publish_new(item/OWNER,_owner_bytes(data))


def replace_owner(item,data):
    """Only the submitter calls this, while holding the login-host submit lock."""
    _atomic(Path(item)/OWNER,lambda f:f.write(_owner_bytes(data)))


def remove_owner(item,token):
    """Undo a create whose sbatch failed; never removes another submission's owner."""
    try:
        if read_owner(item)['token']==token:os.unlink(Path(item)/OWNER)
    except OwnershipError:pass


def generations(item):
    out=[]
    try:entries=list(Path(item).iterdir())
    except FileNotFoundError:return out
    for d in entries:
        m=GEN_RE.fullmatch(d.name)
        if m and d.is_dir():out.append((int(m.group(1)),d))
    return sorted(out)


def _ignored(name):
    return name in SKIP_SEED or name.endswith('.tmp')


def _has_content(folder):
    for _,dirs,files in os.walk(folder):
        if any(not _ignored(f) for f in files):return True
    return False


def _copy_snapshot(source,dest):
    # Every file in a generation folder is replaced atomically and checksummed,
    # so each copied file is a complete snapshot even if an old writer lives.
    # Symlinks are never followed or copied.
    dest.mkdir()
    for top,dirs,files in os.walk(source):
        rel=Path(top).relative_to(source)
        dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(top,d))]
        for d in dirs:(dest/rel/d).mkdir(exist_ok=True)
        for f in files:
            src=Path(top)/f
            if _ignored(f) or src.is_symlink():continue
            try:shutil.copyfile(src,dest/rel/f,follow_symlinks=False)
            except FileNotFoundError:pass


def _no_links(folder):
    """A generation folder must be a real directory with no symlinks inside, or writes could leave it."""
    if folder.is_symlink() or not folder.is_dir():raise OwnershipError(f'{folder}: generation folder is not a plain directory')
    for top,dirs,files in os.walk(folder):
        for name in dirs+files:
            if os.path.islink(os.path.join(top,name)):raise OwnershipError(f'{os.path.join(top,name)}: symlink inside a generation folder')


def _alive(pid):
    try:os.kill(pid,0)
    except ProcessLookupError:return False
    except PermissionError:return True
    return True


def seed(item,generation):
    """Create gNNNN, copied from the newest earlier generation with content."""
    item=Path(item);target=item/gen_name(generation)
    if target.is_symlink():raise OwnershipError(f'{target}: generation folder is a symlink')
    if target.is_dir():_no_links(target);return target
    source=None
    for g,d in reversed(generations(item)):
        if g<generation and _has_content(d):source=d;break
    # Same generation means same job on one node, so local pids are meaningful.
    for stale in item.glob(target.name+'.seed-*'):
        pid=stale.name.rsplit('-',1)[-1]
        if pid.isdigit() and not _alive(int(pid)):shutil.rmtree(stale,ignore_errors=True)
    tmp=item/f'{target.name}.seed-{os.getpid()}'
    shutil.rmtree(tmp,ignore_errors=True)
    if source is None:tmp.mkdir()
    else:_copy_snapshot(source,tmp)
    try:os.rename(tmp,target)
    except OSError:
        shutil.rmtree(tmp,ignore_errors=True)
        if not target.is_dir():raise
    _no_links(target)
    return target


def resolve_target(folder,token=None):
    """Return (write folder, guard). guard is None outside campaign roots.

    Inside a campaign root the folder must be an item directly under the root,
    its owner token must equal `token`, and writes go to the token's generation
    folder. guard() re-reads the owner before each checkpoint and final write so
    a superseded process stops early; isolation, not guard(), provides safety.
    """
    found=campaign_of(folder)
    if found is None:return Path(folder),None
    if Path(os.path.abspath(folder)).is_symlink():raise OwnershipError(f'{folder}: item folder is a symlink')
    root,rel=found
    if len(rel)!=1 or not ID_RE.fullmatch(rel[0]) or rel[0] in RESERVED:
        raise OwnershipError(f'{folder}: inside campaign root {root}; only an item folder directly under the root can be written')
    item=root/rel[0]
    if item.is_symlink():raise OwnershipError(f'{item}: item folder is a symlink')
    owner=read_owner(item)
    if not token or owner['token']!=token:
        raise OwnershipError(f'{item}: owner token mismatch (set LRI_SPIN_OWNER_TOKEN; only the submitted lane may write)')
    generation=owner['generation']

    def guard():
        try:current=read_owner(item)
        except OwnershipError as exc:raise OwnershipError(f'{item}: superseded ({exc})') from None
        if current['token']!=token:
            raise OwnershipError(f'{item}: superseded by generation {current["generation"]}; stopping without writing')

    return seed(item,generation),guard


def refuse_campaign_destination(path):
    """Plain output commands (export, manifests, receipts) never write into campaign state."""
    found=campaign_of(path)
    if found is not None:
        raise OwnershipError(f'{path} is inside campaign root {found[0]}; write outputs elsewhere')


def classify_results(item,check):
    """Split gNNNN/result.json files into (matching, conflicting).

    check(path) raises when the record is corrupt or its identity/payload does
    not belong to the expected item definition; such records are conflicts.
    """
    matching,conflicting=[],[]
    for g,d in generations(item):
        p=d/'result.json'
        if not p.is_file():continue
        try:check(p);matching.append((g,p))
        except Exception as exc:conflicting.append((g,p,str(exc)))
    return matching,conflicting


def init_campaign(root,login_host):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    mark=root/MARK
    if mark.exists():
        data=json.loads(mark.read_text())
        if data.get('login_host')!=login_host:raise OwnershipError(f'{root} belongs to login host {data.get("login_host")}')
        return data
    import time
    data={'schema':1,'login_host':login_host,'created':time.time()}
    (root/'.submit.lock').touch()
    publish_new(mark,_owner_bytes(data))
    return data
