"""Helpers of the dual_d1 public tools (new tool, 2026-10-15; standard library only, mpmath where stated).

- Exact polynomials in zeta values: a polynomial is {monomial: Fraction}; a monomial is the sorted tuple of the zeta
  arguments it multiplies ((), (2,), (3, 3), (2, 5), ...). to_pi() rewrites even zeta values through
  zeta(2) = pi^2/6, zeta(4) = pi^4/90, zeta(6) = pi^6/945, giving the unique form {(power of pi, odd zetas): Fraction}
  in which two expressions are compared exactly.
- tex_coefficients(): the coefficients C_n written in a TeX display (the paper's eq:sr-closed / eq:sr-C8, the
  compendium's eq:thermal-main / eq:C8-candidate-main, from the extract), as exact polynomials.
- py_poly(): the same for the Python/SymPy strings of the compendium records (data/coefficients.json "expression",
  C6_candidate.expr, the candidate string of verify_input_map.py, result.json).
- evaluate(): the value of a polynomial with mpmath at a given precision.
- Work copy: build_work() copies the shipped snapshot into <work>/compendium, restores the file the macOS copy lost
  (case collision, see DATA_dual_d1.md) when the work directory is case-sensitive, and restricts
  reproduction/layout.json and reproduction/MANIFEST.json of the COPY to the files that are present (the snapshot is
  pruned); the verbatim scripts then run unchanged on the copy.
- compendium_stand_in(): the compendium's TeX source is not shipped since 2026-10-17; public/compendium_extract.json
  keeps, verbatim and at their original line numbers, the four blocks that the checks parse (written by the
  maintenance tool make_compendium_extract.py). The stand-in has every block at its original line and blank lines
  elsewhere, so the parsers and the line numbers they report are those of the original.
"""
import ast, hashlib, json, os, re, shutil
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent          # code/dual_d1/public
PKG = HERE.parent                               # code/dual_d1 (the snapshot)
SRI = PKG.parent.parent                         # SRI/
EVEN = {2: (F(1, 6), 2), 4: (F(1, 90), 4), 6: (F(1, 945), 6)}

# ---------------------------------------------------------------------------------------------------- polynomials

def msort(m):
    """Standard order of a monomial: zeta arguments ascending, then the symbol 'pi'."""
    return tuple(sorted(m, key=lambda z: (isinstance(z, str), z if isinstance(z, int) else 0)))


def padd(a, b, s=F(1)):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, F(0)) + s*v
        if not out[k]:
            del out[k]
    return out


def pmul(a, b):
    out = {}
    for ka, va in a.items():
        for kb, vb in b.items():
            k = msort(ka + kb)
            out[k] = out.get(k, F(0)) + va*vb
            if not out[k]:
                del out[k]
    return out


def ppow(a, n):
    out = {(): F(1)}
    for _ in range(n):
        out = pmul(out, a)
    return out


def to_pi(p):
    """{zeta monomial: c} -> {(pi power, odd zetas): c}; zeta(2k) = r_k pi^(2k) for k = 1, 2, 3; 'pi' entries pass."""
    out = {}
    for mono, c in p.items():
        pw, odd, coef = 0, [], F(c)
        for z in mono:
            if z == 'pi':
                pw += 1
            elif z in EVEN:
                coef *= EVEN[z][0]; pw += EVEN[z][1]
            elif isinstance(z, int) and z % 2 == 1 and z >= 3:
                odd.append(z)
            else:
                raise ValueError('unsupported constant %r' % (z,))
        k = (pw, tuple(sorted(odd)))
        out[k] = out.get(k, F(0)) + coef
        if not out[k]:
            del out[k]
    return out


def weight(mono):
    return sum(z for z in mono if isinstance(z, int))


def rational_part(p):
    return p.get((), F(0))


def show(p):
    """Readable form of a zeta polynomial, in the paper's order (weight, then arguments)."""
    def mono(m):
        return '*'.join('zeta(%d)' % z for z in m) if m else '1'
    terms = sorted(p.items(), key=lambda kv: (weight(kv[0]), kv[0]))
    return ' + '.join('(%s)*%s' % (c, mono(m)) for m, c in terms)


def evaluate(p, mp):
    """Value of a zeta polynomial (mpmath module mp at its current precision)."""
    tot = mp.mpf(0)
    for mono, c in p.items():
        t = mp.mpf(c.numerator)/c.denominator
        for z in mono:
            t *= mp.pi if z == 'pi' else mp.zeta(z)
        tot += t
    return tot

# ---------------------------------------------------------------------------------------------------- TeX parser

_TERM = re.compile(r'\s*([+-]?)\s*(?:\\frac\{(\d+)\}\{(\d+)\}|\\frac(\d)(\d)|(\d+))?\s*((?:\\zeta\(\d+\)(?:\^\{?\d+\}?)?\s*)*)')
_ZETA = re.compile(r'\\zeta\((\d+)\)(?:\^\{?(\d+)\}?)?')


def tex_expr(s):
    """Exact polynomial of one TeX right-hand side: sums of [rational] x products of \\zeta(k)[^p]. Strict: any other
    token raises ValueError."""
    s = s.strip().rstrip('.,').strip()
    pos, out = 0, {}
    while pos < len(s):
        m = _TERM.match(s, pos)
        if not m or m.end() == pos:
            raise ValueError('cannot parse TeX at %r' % s[pos:pos+40])
        sign, fn, fd, sn, sd, integer, zetas = m.groups()
        if fn:
            c = F(int(fn), int(fd))
        elif sn:
            c = F(int(sn), int(sd))
        elif integer:
            c = F(int(integer))
        else:
            c = F(1)
        if not (fn or sn or integer or zetas.strip()):
            raise ValueError('empty term at %r' % s[pos:pos+40])
        if sign == '-':
            c = -c
        mono = []
        for z, p in _ZETA.findall(zetas):
            mono += [int(z)]*(int(p) if p else 1)
        if _ZETA.sub('', zetas).strip():
            raise ValueError('unexpected token in %r' % zetas)
        out = padd(out, {msort(mono): c})
        pos = m.end()
    return out


_CLEAN = [r'\\begin\{aligned\}', r'\\end\{aligned\}', r'\\begin\{align\}', r'\\end\{align\}', r'\\notag',
          r'\\label\{[^}]*\}', r'\\boxed\{', r'\\qquad', r'\\quad', r'\\\\', r'&', r'\{\}', r'\\,', r'\\left', r'\\right']


def tex_coefficients(tex):
    """{n: polynomial} for every 'C^{\\rm SR}_n=' (paper) or 'C_n=' / 'C_n^{\\rm cand}=' (compendium note) in tex."""
    t = tex
    for pat in _CLEAN:
        t = re.sub(pat, ' ', t)
    t = t.replace('\n', ' ')
    marks = list(re.finditer(r'C(?:\^\{\\rm SR\})?_(\d)(?:\(\d\))?(?:\^\{\\rm (?:cand|num)\})?\s*=', t))
    if not marks:
        raise ValueError('no coefficient found')
    out = {}
    for i, m in enumerate(marks):
        end = marks[i+1].start() if i+1 < len(marks) else len(t)
        body = t[m.end():end].strip().rstrip('}').strip().rstrip('.,').strip()
        n = int(m.group(1))
        if n in out:
            raise ValueError('C_%d twice' % n)
        out[n] = tex_expr(body)
    return out

# ---------------------------------------------------------------------------------------------------- Python strings

def py_poly(text, names=None):
    """Exact polynomial of a Python/SymPy expression string in integers, pi, zeta(k), Zk (= zeta(k)) and the given
    {name: polynomial} symbols; '^' is read as '**'. Restricted AST, no eval."""
    names = names or {}
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return {(): F(n.value)} if n.value else {}
        if isinstance(n, ast.Name):
            if n.id == 'pi':
                return {('pi',): F(1)}
            m = re.fullmatch(r'Z(\d+)', n.id)
            if m:
                return {(int(m.group(1)),): F(1)}
            if n.id in names:
                return names[n.id]
            raise ValueError('unknown name ' + n.id)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'zeta' and len(n.args) == 1 \
                and isinstance(n.args[0], ast.Constant):
            return {(int(n.args[0].value),): F(1)}
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = ev(n.operand)
            return {k: -c for k, c in v.items()} if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp):
            a = ev(n.left)
            if isinstance(n.op, ast.Pow):
                b = ev(n.right)
                assert set(b) <= {()}, 'non-integer power'
                return ppow(a, int(b.get((), 0)))
            b = ev(n.right)
            if isinstance(n.op, ast.Add):
                return padd(a, b)
            if isinstance(n.op, ast.Sub):
                return padd(a, b, F(-1))
            if isinstance(n.op, ast.Mult):
                return pmul(a, b)
            if isinstance(n.op, ast.Div):
                assert set(b) == {()}, 'division by a non-rational'
                return {k: c/b[()] for k, c in a.items()}
        raise ValueError('unsupported ' + ast.dump(n)[:80])
    return ev(ast.parse(text.replace('^', '**'), mode='eval'))

# ---------------------------------------------------------------------------------------------------- work copy

LOST = {  # the file the macOS copy of the compendium lost (case collision with A_check_symbolic.expr)
    'stored': 'data/archived/C6_closed_form/input_expressions/a_check_symbolic.expr',
    'shipped_as': 'public/restored/lowercase_a_check_symbolic.expr.txt',
    'sha256': '71471995155e08fbba4872817bf6cd0140f2bb4173067b765b05e104f54aac65',
}
HOSTED = 'hosted'   # <work>/hosted/<stored path>: files fetched by make fetch-data (C7 weight-6 certificate)
SKIP_TOP = {'public', '.work', 'public.mk', '__pycache__', 'work'}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def exact_exists(p):
    """True if a file with exactly this name (case included) exists."""
    p = Path(p)
    try:
        return p.name in os.listdir(p.parent) and p.is_file()
    except FileNotFoundError:
        return False


def case_sensitive(d):
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    a, b = d/'.case_probe_x', d/'.CASE_PROBE_X'
    for q in (a, b):
        if q.exists():
            q.unlink()
    a.write_text('a')
    ok = not b.exists()
    a.unlink()
    return ok


EXTRACT = HERE/'compendium_extract.json'


def compendium_stand_in():
    """(text, extract, bad): the stand-in for note/LRI_perturbation_compendium.tex rebuilt from public/
    compendium_extract.json, the extract itself, and the ids of blocks whose text does not match its recorded sha256."""
    d = json.loads(EXTRACT.read_text())
    out, bad = [''] * d['original']['lines'], []
    for b in d['blocks']:
        if hashlib.sha256('\n'.join(b['text']).encode()).hexdigest() != b['sha256']:
            bad.append(b['id'])
        for i, line in enumerate(b['text']):
            out[b['first_line'] - 1 + i] = line
    return '\n'.join(out), d, bad


def not_shipped():
    """Package paths listed in public/NOT_SHIPPED.txt (left out of the export; must be absent)."""
    f = HERE/'NOT_SHIPPED.txt'
    return [l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith('#')] if f.is_file() else []


def public_lists():
    """(scrubbed, repinned): paths listed in public/SCRUBBED.txt (written by the repository's scrub; presence only) and
    {path: published sha256} from public/RE-PINNED.json (files re-pinned by the package)."""
    sc, rp = set(), {}
    f = PKG/'public'/'SCRUBBED.txt'
    if f.is_file():
        sc = {l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith('#')}
    f = PKG/'public'/'RE-PINNED.json'
    if f.is_file():
        for r in json.loads(f.read_text()).get('files', []):
            rp[r['path']] = r['published_sha256']
    return sc, rp


def accepted(rel, original_sha, actual_sha, scrubbed, repinned):
    """A shipped file is accepted if it matches its original pin, its RE-PINNED published sha256, or is listed in
    SCRUBBED.txt (presence only)."""
    return actual_sha == original_sha or repinned.get(rel) == actual_sha or rel in scrubbed


def build_work(work, log=print):
    """Copy the snapshot to <work>/compendium (fresh), restore the lost file, add hosted files, prune the copy's
    layout.json and MANIFEST.json to the files present. Returns a report dict."""
    work = Path(work).resolve()
    dst = work/'compendium'
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for item in sorted(PKG.iterdir()):
        if item.name in SKIP_TOP or item.name == '.DS_Store':
            continue
        if item.is_dir():
            shutil.copytree(item, dst/item.name, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
        else:
            shutil.copy2(item, dst/item.name)
    rep = {'work_copy': str(dst), 'case_sensitive': case_sensitive(dst)}
    lost_src = PKG/LOST['shipped_as']
    if rep['case_sensitive'] and lost_src.is_file() and sha256(lost_src) == LOST['sha256']:
        shutil.copy2(lost_src, dst/LOST['stored'])
        rep['restored'] = LOST['stored']
    else:
        rep['restored'] = None
    hosted = work/HOSTED
    rep['hosted'] = []
    if hosted.is_dir():
        for f in sorted(hosted.rglob('*')):
            if f.is_file():
                rel = f.relative_to(hosted).as_posix()
                (dst/rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst/rel)
                rep['hosted'].append(rel)
    present = lambda rel: exact_exists(dst/rel)
    lay = json.loads((dst/'reproduction/layout.json').read_text())
    keep = [r for r in lay['files'] if present(r['stored'])]
    rep['layout'] = {'virtual_paths': len(lay['files']), 'kept': len(keep)}
    lay['files'] = keep
    lay['public_note'] = ('Work copy made by public/dual_lib.py: restricted to the virtual paths whose stored file is '
                          'present in the published snapshot (the original is reproduction/layout.json of the package).')
    (dst/'reproduction/layout.json').write_text(json.dumps(lay, indent=1) + '\n')
    man = json.loads((dst/'reproduction/MANIFEST.json').read_text())
    # the copy's layout.json is rewritten above, so its MANIFEST entry is dropped here; the shipped original is checked
    # against the same MANIFEST entry by the replay's snapshot section
    scrubbed, repinned = public_lists()
    mkeep = []
    for r in man['files']:
        if not present(r['path']) or r['path'] == 'reproduction/layout.json' or r['path'] in scrubbed:
            continue                      # scrubbed files: presence only (checked by the replay's snapshot section)
        if r['path'] in repinned:
            r = dict(r, sha256=repinned[r['path']])
        mkeep.append(r)
    rep['scrubbed_presence_only'] = sorted(p for p in scrubbed if present(p))
    rep['repinned'] = sorted(p for p in repinned if present(p))
    rep['manifest'] = {'files': len(man['files']), 'kept': len(mkeep)}
    man['files'] = mkeep
    man['count'] = len(mkeep)
    man['public_note'] = 'Work copy: restricted to the distributed files present in the published snapshot.'
    (dst/'reproduction/MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')
    (work/'workcopy_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    log('work copy: %s (case-sensitive %s; restored %s; hosted %d; layout %d of %d virtual paths; MANIFEST %d of %d '
        'files)' % (dst, rep['case_sensitive'], rep['restored'], len(rep['hosted']), rep['layout']['kept'],
                    rep['layout']['virtual_paths'], rep['manifest']['kept'], rep['manifest']['files']))
    return rep


def run(cmd, cwd, log_path, env_extra=None, timeout=None):
    """Run a command (list) in cwd with the environment the compendium's reproduce.py uses; output to log_path."""
    import subprocess, time
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='2')
    env.update(env_extra or {})
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    with open(log_path, 'w') as fp:
        r = subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=env, stdout=fp, stderr=subprocess.STDOUT,
                           timeout=timeout)
    return r.returncode, time.time() - t
