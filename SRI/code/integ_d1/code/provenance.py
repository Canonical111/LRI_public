"""Provenance helpers (fix round 1, MSC-009).

- Frozen records (blind flow-coefficient files) are listed in results/frozen_records.json with their sha256 and the
  commit that froze them. verify_frozen() rejects any record whose bytes changed.
- Step-0 maps (response/base JSON) carry a 'provenance' block: the generator script and its sha256, the sha256 of
  every upstream file they were built from, and the numerical parameters. load_step0() rejects a map whose generator
  or upstream inputs changed since it was built (stale map).
- write_once_json() publishes a JSON file atomically (tmp + fsync + rename) and never overwrites an existing file
  with different content."""
import os, json, hashlib, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.normpath(os.path.join(HERE, '..', 'results'))
REGISTRY = os.path.join(RES, 'frozen_records.json')


class ProvenanceError(RuntimeError):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def atomic_write_text(path, text):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.tmp_', suffix=os.path.basename(path))
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp): os.unlink(tmp)
        raise


def write_once_text(path, text):
    """Publish `text` at path without ever replacing an existing file (MSC-015): the content goes to a fsynced
    temporary file that is hard-linked to the final name (os.link fails atomically if the name exists, so of two
    concurrent writers exactly one wins); if the name exists, its bytes must equal `text`, else ProvenanceError.
    Returns True if this call created the file."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.tmp_', suffix=os.path.basename(path))
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text); f.flush(); os.fsync(f.fileno())
        try:
            os.link(tmp, path)
            created = True
        except FileExistsError:
            created = False
    finally:
        os.unlink(tmp)
    if not created and open(path).read() != text:
        raise ProvenanceError(f'{path} exists with different content; refusing to overwrite '
                              '(frozen or earlier record): choose a new tag/destination')
    if created:
        dfd = os.open(d, os.O_RDONLY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    return created


import contextlib, fcntl


@contextlib.contextmanager
def publication_lock():
    """Exclusive lock around a multi-file publication (record + sidecar + registry) in this repository's results/.
    The repository lives on the Mac, so a local flock is sufficient; it is not meant for cross-node use."""
    lp = os.path.join(RES, '.publication.lock')
    fd = os.open(lp, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def publish_unit(files, register=None):
    """Publish several files as one unit under the publication lock: every file is written once (write_once_text);
    if any existing file differs, nothing new is published (the check runs on all files before any is created).
    register: optional (name, commit, note) to add the first file to the frozen-record registry."""
    with publication_lock():
        for path, text in files:
            if os.path.exists(path) and open(path).read() != text:
                raise ProvenanceError(f'{path} exists with different content; nothing published')
        created = [write_once_text(path, text) for path, text in files]
        if register:
            name, commit, note = register
            register_frozen(name, sha256_file(os.path.join(RES, name)), commit, note)
        return created


def registry():
    return json.load(open(REGISTRY)) if os.path.exists(REGISTRY) else {}


def verify_frozen(name, expect_sha=None):
    """Check results/<name> against the frozen-record registry (and optionally an explicit hash)."""
    reg = registry()
    if name not in reg:
        raise ProvenanceError(f'{name} is not a registered frozen record')
    path = os.path.join(RES, name)
    sha = sha256_file(path)
    if sha != reg[name]['sha256']:
        raise ProvenanceError(f'{name}: sha256 {sha} != frozen {reg[name]["sha256"]}')
    if expect_sha is not None and sha != expect_sha:
        raise ProvenanceError(f'{name}: sha256 {sha} != expected {expect_sha}')
    return sha


def register_frozen(name, sha, commit, note=''):
    """Add a record to the registry (only if absent; an existing entry must agree). Call under publication_lock()
    (publish_unit does) when other writers may be active."""
    reg = registry()
    if name in reg:
        if reg[name]['sha256'] != sha:
            raise ProvenanceError(f'registry already holds {name} with a different hash')
        return
    reg[name] = {'sha256': sha, 'frozen_in_commit': commit, 'note': note}
    atomic_write_text(REGISTRY, json.dumps(reg, indent=1, sort_keys=True) + '\n')


def mark_superseded(name, by, reason):
    """Mark a frozen record as superseded by a newer version (fix round 3). The record file and its hash stay
    untouched; the registry entry gains 'superseded_by' and 'superseded_reason' (set once; a second call must agree).
    The successor must already be registered."""
    with publication_lock():
        reg = registry()
        if name not in reg or by not in reg:
            raise ProvenanceError(f'cannot supersede {name} by {by}: both must be registered')
        ent = reg[name]
        if 'superseded_by' in ent:
            if ent['superseded_by'] != by:
                raise ProvenanceError(f'{name} is already superseded by {ent["superseded_by"]}')
            return
        ent['superseded_by'] = by; ent['superseded_reason'] = reason
        atomic_write_text(REGISTRY, json.dumps(reg, indent=1, sort_keys=True) + '\n')


def is_current(name):
    """registered and not superseded"""
    ent = registry().get(name)
    return ent is not None and 'superseded_by' not in ent


def protected_paths():
    """the registry and every registered record (and its provenance sidecar): never opened for writing by tools"""
    out = {os.path.realpath(REGISTRY)}
    for name in registry():
        rp = os.path.realpath(os.path.join(RES, name)); out.add(rp)
        out.add(os.path.realpath(os.path.join(RES, name.replace('.json', '.provenance.json'))))
    return out


def safe_create_report(path):
    """MSC-031: create a NEW report file exclusively (O_CREAT|O_EXCL|O_NOFOLLOW); refuse symlinks, existing files, the
    registry and any registered record or sidecar. Returns a text file object; raises ProvenanceError otherwise."""
    if os.path.islink(path):
        raise ProvenanceError(f'refusing symlinked report path {path}')
    if os.path.realpath(path) in protected_paths():
        raise ProvenanceError(f'refusing to write a report onto a registered record or the registry: {path}')
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o644)
    except FileExistsError:
        raise ProvenanceError(f'refusing to overwrite an existing file {path}')
    except OSError as e:
        raise ProvenanceError(f'cannot create report {path}: {e}')
    return os.fdopen(fd, 'w')


def committed_blob_ok(path):
    """MSC-032: the working file equals the blob committed when it was first added (git); returns (ok, commit, blob)"""
    import subprocess
    root = os.path.dirname(RES)
    rel = os.path.relpath(path, root)
    if not os.path.isfile(path):
        return False, None, None
    log = subprocess.run(['git', '-C', root, 'log', '--diff-filter=A', '--format=%h', '--', rel], capture_output=True, text=True).stdout.split()
    if not log:
        return False, None, None
    commit = log[-1]
    want = subprocess.run(['git', '-C', root, 'rev-parse', f'{commit}:{rel}'], capture_output=True, text=True).stdout.strip()
    got = subprocess.run(['git', '-C', root, 'hash-object', path], capture_output=True, text=True).stdout.strip()
    return bool(want) and want == got, commit, got


def step0_provenance(generator, upstream, params):
    """generator: script path; upstream: list of file paths; params: dict of numerical parameters."""
    return {'generator': os.path.basename(generator), 'generator_sha256': sha256_file(generator),
            'upstream': {os.path.relpath(p, RES) if os.path.abspath(p).startswith(RES) else os.path.basename(p): sha256_file(p)
                         for p in upstream},
            'params': params}


def load_step0(name):
    """Load results/<name> written with a provenance block and reject stale maps."""
    path = os.path.join(RES, name)
    obj = json.load(open(path))
    if not isinstance(obj, dict) or 'provenance' not in obj or 'data' not in obj:
        raise ProvenanceError(f'{name} has no provenance block (pre-fix-round-1 format): regenerate it')
    pv = obj['provenance']
    gen = os.path.join(HERE, pv['generator'])
    if sha256_file(gen) != pv['generator_sha256']:
        raise ProvenanceError(f'{name} is stale: {pv["generator"]} changed since the map was built')
    for rel, sha in pv['upstream'].items():
        p = os.path.join(RES, rel)
        if not os.path.exists(p):
            raise ProvenanceError(f'{name}: upstream {rel} missing')
        if sha256_file(p) != sha:
            raise ProvenanceError(f'{name}: upstream {rel} changed since the map was built')
    return obj['data'], pv
