"""Shared manifest validation: safe IDs, known fields and contained paths before any write."""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
from .config import Config
from .campaign import ID_RE,RESERVED
from .workflow import plan
from .io import identity,read_record
from .validation import validate_result

FIELDS={'id','kind','config','alpha','bracket','fraction','atol','maxiter','sector_workers',
        'memory_limit_gib','backend','with_tangent'}
KINDS=('critical','flow','tangent')
DEFAULT_MEMORY_GIB=4.


def check_id(name):
    if not isinstance(name,str) or not ID_RE.fullmatch(name):raise ValueError(f'Unsafe item ID: {name!r}')
    if name in RESERVED:raise ValueError(f'Reserved campaign name used as item ID: {name!r}')
    return name


def contained(root,name):
    """Item folder of `name` under root: a plain directory (or absent), never a symlink or file."""
    root=Path(root).resolve();lexical=root/check_id(name);path=lexical.resolve()
    if lexical.is_symlink() or path.parent!=root:raise ValueError(f'Item path is a symlink or escapes its root: {name!r}')
    if path.exists() and not path.is_dir():raise ValueError(f'Item path exists and is not a directory: {name!r}')
    return path


def _finite(v,what):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError(f'Invalid {what}: {v!r}')
    return float(v)


def config_of(item):
    try:cfg=Config(**item['config'])
    except TypeError as exc:raise ValueError(f'{item.get("id")}: invalid config ({exc})') from None
    cfg.check();return cfg


def reservation_gib(item):
    cfg=config_of(item)
    est=plan(cfg,item.get('sector_workers',1))['estimated_gib_with_margin']
    return max(float(item.get('memory_limit_gib',DEFAULT_MEMORY_GIB)),est)


def cost(item):
    """Relative work estimate used only for balancing lanes."""
    cfg=config_of(item);base=float(cfg.keep*cfg.nb)**3*cfg.nsites
    if item['kind']=='flow':return base
    if item['kind']=='tangent':return 3*base
    lo,hi=item.get('bracket',[.01,2.]);atol=item.get('atol',5e-14)
    steps=min(item.get('maxiter',48),math.ceil(math.log2(max(hi-lo,1e-300)/atol))+1)
    return base*(steps+4)+(3*base if item.get('with_tangent',True) else 0)


def expected_identity(item,source,runtime):
    """The result identity the workflow writes for this item, on the validated runtime."""
    cfg=config_of(item);backend=item.get('backend','ordered');sw=item.get('sector_workers',1)
    if item['kind']=='critical':
        ident=identity(cfg,None,'critical',backend,sw,bracket=list(item.get('bracket',[.01,2.])),
                       fraction=item.get('fraction',.3),atol=item.get('atol',5e-14),maxiter=item.get('maxiter',48),
                       with_tangent=item.get('with_tangent',True))
    else:
        ident=identity(cfg,float(item['alpha']),item['kind'],backend,sw,observers=True)
    ident['source_sha256']=source;ident['runtime']=runtime
    return ident


def result_checker(item,source,runtime):
    """check(path): raises unless the record is intact, belongs to this item and passes the gates."""
    ident=expected_identity(item,source,runtime);cfg=config_of(item)

    def check(path):
        r=read_record(path,ident)
        if item['kind']=='critical':
            validate_result(r['critical_flow'],cfg)
            if item.get('with_tangent',True):validate_result(r['tangent'],cfg,tangent=True)
        else:validate_result(r,cfg,tangent=item['kind']=='tangent',observers=True)
        return r
    return check


def validate_item(item,root=None):
    if not isinstance(item,dict):raise ValueError('Manifest item must be an object')
    extra=set(item)-FIELDS
    if extra:raise ValueError(f'Unrecognized manifest field(s) {sorted(extra)}')
    check_id(item.get('id'))
    if item.get('kind') not in KINDS:raise ValueError(f'{item["id"]}: unknown kind {item.get("kind")!r}')
    if not isinstance(item.get('config'),dict):raise ValueError(f'{item["id"]}: missing config')
    cfg=config_of(item)
    if item['kind']=='critical':
        b=item.get('bracket',[.01,2.])
        if not (isinstance(b,list) and len(b)==2):raise ValueError(f'{item["id"]}: invalid bracket')
        lo,hi=(_finite(x,'bracket') for x in b)
        if not 0<lo<hi:raise ValueError(f'{item["id"]}: invalid bracket')
        if not 0<_finite(item.get('fraction',.3),'fraction')<1:raise ValueError(f'{item["id"]}: invalid fraction')
        if not _finite(item.get('atol',5e-14),'atol')>0:raise ValueError(f'{item["id"]}: invalid atol')
        m=item.get('maxiter',48)
        if isinstance(m,bool) or not isinstance(m,int) or not 1<=m<=200:raise ValueError(f'{item["id"]}: invalid maxiter')
        if not isinstance(item.get('with_tangent',True),bool):raise ValueError(f'{item["id"]}: invalid with_tangent')
    else:
        if 'alpha' not in item:raise ValueError(f'{item["id"]}: alpha required')
        a=_finite(item['alpha'],'alpha')
        if a<0 or (item['kind']=='tangent' and a<=0):raise ValueError(f'{item["id"]}: invalid alpha')
    sw=item.get('sector_workers',1)
    if sw not in (1,2) or isinstance(sw,bool):raise ValueError(f'{item["id"]}: invalid sector_workers')
    backend=item.get('backend','ordered')
    if backend not in ('ordered','dense','banded'):raise ValueError(f'{item["id"]}: invalid backend')
    if backend=='ordered' and sw!=1:raise ValueError(f'{item["id"]}: ordered backend needs sector_workers=1')
    mem=_finite(item.get('memory_limit_gib',DEFAULT_MEMORY_GIB),'memory_limit_gib')
    est=plan(cfg,sw)['estimated_gib_with_margin']
    if not mem>=est:raise ValueError(f'{item["id"]}: memory_limit_gib {mem} below plan estimate {est:.3f}')
    if root is not None:contained(root,item['id'])
    return item


def validate_items(items,root=None):
    if not isinstance(items,list) or not items:raise ValueError('Manifest needs a non-empty item list')
    for item in items:validate_item(item,root)
    ids=[i['id'] for i in items]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate manifest IDs')
    return items


def load_manifest(path,root=None,sha256=None):
    blob=Path(path).read_bytes()
    if sha256 is not None and hashlib.sha256(blob).hexdigest()!=sha256:raise ValueError(f'{path} differs from its submitted hash')
    m=json.loads(blob)
    if not isinstance(m,dict) or 'items' not in m:raise ValueError('Not a frozen manifest')
    validate_items(m['items'],root)
    return m
