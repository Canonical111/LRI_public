"""Compare what `make replay` recomputed in the workspace with the released files and with verify/expected.json.

Usage  python verify/verify.py [--work .work] [--paper ../paper]   (run from NRG/; `make replay` calls it)
Writes WORK/reproduced/VERIFY.md and exits 1 if any check fails.

Checks
  V0  code/lri_spin_boson_hpc/src/lri_spin        its SHA-256 equals the source hash of the receipt (and so of every record)
  V1  results/*.json                              same structure; floats to |a-b| <= 1e-8 + 1e-6 |b|; fitted exponents omega
                                                  and fit residuals to 1e-3 relative; cross-check fits (not adopted) to 1e-5,
                                                  their fit counts not compared
      results/*.md                                same text; numbers equal or within one unit of their last printed digit
  V2  note/tables/*.tex                           same text; numbers equal or within one unit of their last printed digit
  V3  independent_check_compare/*.json, *.md      JSON floats to |a-b| <= 1e-14 + 1e-12 |b|; .md as V1 with an absolute
                                                  allowance of 1e-14 (the chain comparison is recomputed with the production
                                                  closed form, whose last bits depend on the platform's libm)
  V4  method_comparison/comparison.json           same structure, floats to |a-b| <= 1e-9 + 1e-9 |b|; .md as V1
  V5  note/figures/*.pdf                          regenerated (non-empty); figures are not compared byte for byte
  V6  note/lri_nrg_1d_note.tex                    every \\nrg macro defined, every \\input and \\includegraphics present
  V7  verify/expected.json                        the published values, each with its tolerance
  V8  verify/quoted_numbers.json                  every NRG number the paper prints (results_map.md), its text recomputed from
                                                  the regenerated note macros, note tables, results and comparison: equal, or
                                                  (compare "digit") numbers within one unit of their last printed digit, exponents
                                                  equal; statements the paper makes without a number, recomputed as facts (e.g. the
                                                  dual series through C^SR_n(1) against Delta_E at Delta_sigma = 0.01, with the
                                                  coefficients of the paper). One more row compares the listed texts with ../paper (numbers.tex, and
                                                  every \\NRG macro that main.tex and sections/ print, and no other); SKIP if
                                                  ../paper is absent

Why tolerances and not byte identity. The extrapolations (code/analysis/estimator.py) are least-squares fits; different
NumPy/SciPy builds and CPUs give them last-bit differences, which the fits amplify to about 1e-10 in the values and up to
about 1e-4 relative in fitted exponents where these are poorly determined (on a plateau). With the reference stack (Python 3.10, NumPy 2.2.6, SciPy 1.15.3) the
files are byte-identical; with NumPy 1.24 / SciPy 1.11 they are not, and every printed number of the note still agrees.
"""
import argparse,json,math,re,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
NUM=re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?')
# C^SR_1(1) .. C^SR_8(1) of the short-range dual series Delta_E = 1 + sum_n C^SR_n(1) Delta_sigma^(n/2) (paper Eqs. eq:sr-closed,
# eq:sr-C8; C^SR_8(1) is the conjectured closed form)
Z2,Z3,Z4,Z5,Z6,Z7=math.pi**2/6,1.2020569031595942,math.pi**4/90,1.0369277551433699,math.pi**6/945,1.0083492773819228
SR_C=(-2.,.5,39/16+2*Z2,4-4*Z2-8*Z3,11249/1024-361/16*Z2+24*Z3+49/2*Z4,26-38*Z2+104*Z3-80*Z4-272*Z5+112*Z2*Z3,
      1798583/32768-90637/1024*Z2+453/4*Z3-16835/64*Z4+1224*Z5-540*Z2*Z3+4335/8*Z6-320*Z3**2,
      88-178*Z2+110*Z3+113*Z4+4892*Z5-2376*Z2*Z3-8630/3*Z6+1872*Z3**2-12168*Z7+6048*Z2*Z5+1536*Z3*Z4)


def same_bytes(a,b):
    return a.is_file() and b.is_file() and a.read_bytes()==b.read_bytes()


def close(x,y,atol,rtol,path=()):
    if isinstance(x,dict) and isinstance(y,dict):
        return x.keys()==y.keys() and all(close(x[k],y[k],atol,rtol,path+(k,)) for k in x)
    if isinstance(x,list) and isinstance(y,list):return len(x)==len(y) and all(close(a,b,atol,rtol,path) for a,b in zip(x,y))
    lax='crosschecks' in path
    if lax and path and path[-1] in ('n','tried'):return True
    if isinstance(x,(int,float)) and isinstance(y,(int,float)) and not isinstance(x,bool) and not isinstance(y,bool) \
            and (isinstance(x,float) or isinstance(y,float) or lax):
        if math.isnan(x) or math.isnan(y):return math.isnan(x) and math.isnan(y)
        if path and path[-1] in ('omega','max_abs_residual'):return abs(x-y)<=1e-9+1e-3*abs(y)   # poorly determined fit parameters
        a,r=(1e-5,0.) if lax else (atol,rtol)
        return abs(x-y)<=a+r*abs(y)
    return x==y


def unit(tok):
    m=re.fullmatch(r'[-+]?(\d*)\.?(\d*)(?:[eE]([-+]?\d+))?',tok)
    return 10.0**((int(m.group(3)) if m.group(3) else 0)-len(m.group(2)))


def first_diff(s,t):
    for i,(u,v) in enumerate(zip(s.splitlines(),t.splitlines())):
        if u!=v:return f'line {i+1}: {u[:80]!r} vs {v[:80]!r}'
    return 'line count differs'


def same_text(a,b,atol=0.):
    """Equal up to numbers that differ by at most one unit of their last printed digit (or by atol)."""
    if not (a.is_file() and b.is_file()):return False,'missing'
    return same_str(a.read_text(),b.read_text(),atol)


def same_str(s,t,atol=0.):
    """same_text for two strings."""
    if s==t:return True,'identical'
    if NUM.split(s)!=NUM.split(t):return False,'text differs: '+first_diff(s,t)
    x,y=NUM.findall(s),NUM.findall(t)
    if len(x)!=len(y):return False,'text differs: '+first_diff(s,t)
    bad=[(p,q) for p,q in zip(x,y) if p!=q and abs(float(p)-float(q))>max(1.000001*max(unit(p),unit(q)),atol)]
    return (not bad),(f'{sum(1 for p,q in zip(x,y) if p!=q)} numbers within one unit of the last digit' if not bad else
                      'numbers differ: '+', '.join(f'{p} vs {q}' for p,q in bad[:3]))


def pick(rows,key):
    m=[r for r in rows if all(r.get(k)==v for k,v in key.items())]
    if len(m)!=1:raise KeyError(f'{key}: {len(m)} matches')
    return m[0]


def tex_macros(text):
    """{name: body} of every \\newcommand{\\name}{body} (balanced braces)."""
    out={}
    for m in re.finditer(r'\\newcommand\{\\([A-Za-z]+)\}\{',text):
        i=j=m.end();depth=1
        while depth:
            if text[j]=='\\':j+=2;continue
            depth+={'{':1,'}':-1}.get(text[j],0);j+=1
        out[m.group(1)]=text[i:j-1]
    return out


def quoted_text(src,W):
    """The text of one paper number, recomputed from the files `make replay` regenerated in W (verify/quoted_numbers.json)."""
    if 'macro' in src:return src.get('wrap','{}').format(tex_macros((W/'note'/'tables'/'numbers.tex').read_text())[src['macro']])
    F=json.loads((W/'results'/'ds13_final.json').read_text());name=src['rule']
    if name=='n_points':return str(len(F))
    if name=='nc_points':   # the points not converged in chain depth are those closest to s = 1/2
        nc=[x['ds'] for x in F if x['status']!='final']
        if sorted(nc,reverse=True)!=sorted((x['ds'] for x in F),reverse=True)[:len(nc)]:return 'not the points closest to s=1/2'
        return f"{len(nc)}: {', '.join(f'{d:g}' for d in nc)}"
    if name=='dual_series': # Delta_sigma = 0.01: D_n = Delta_E - (1 + sum_(k<=n) C^SR_k(1) Delta_sigma^(k/2)), against delta_tot
        x=[r for r in F if r['ds']==0.01][0];u=x['total'];t=[c*0.01**((k+1)/2) for k,c in enumerate(SR_C)]
        D=[abs(x['Delta_E']-1-sum(t[:n])) for n in range(2,6)]
        return (f"size of D_n falls for n = 2..5: {'yes' if all(a>b for a,b in zip(D,D[1:])) else 'no'}; size of D_5 {D[-1]/u:.1f} delta_tot; "
                f"C^SR_6 term {abs(t[5])/u:.1f} delta_tot; C^SR_7, C^SR_8 terms at most {max(abs(t[6]),abs(t[7]))/u:.1f} delta_tot")
    raise KeyError(name)


def exact_exponents(s):
    """Hide the digits of exponents ^{...} from NUM, so that same_str compares them exactly."""
    return re.sub(r'\^\{([^}]*)\}',lambda m:'^{'+m.group(1).translate(str.maketrans('0123456789+-','abcdefghijPM'))+'}',s)


def paper_check(Q,paper):
    """verify/quoted_numbers.json against the paper: same macro texts, every \\NRG macro the paper prints is listed, and
    every listed macro is still printed."""
    num=paper/'numbers.tex'
    if not num.is_file():return None,f'{paper} not found (NRG/ copied without the paper): not compared'
    P=tex_macros(num.read_text());listed={e['macro']:e['printed'] for e in Q['numbers'] if 'macro' in e}
    used=set()
    for f in [paper/'main.tex']+sorted((paper/'sections').glob('*.tex')):
        if f.is_file():used|=set(re.findall(r'\\(NRG[A-Za-z]+)',re.sub(r'(?<!\\)%.*','',f.read_text())))
    bad=([f'\\{m} not listed' for m in sorted(used-set(listed))]+[f'\\{m} listed but no longer printed' for m in sorted(set(listed)-used)]+
         [f'\\{m}: paper {P.get(m)!r}, listed {t!r}' for m,t in listed.items() if P.get(m)!=t])
    return not bad,('; '.join(bad[:4]) if bad else f'{len(used)} NRG macros printed, all listed with the same text')


def main():
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--work',type=Path,default=ROOT/'.work')
    ap.add_argument('--paper',type=Path,default=ROOT.parent/'paper',help='the paper folder of the repository (default: ../paper)')
    a=ap.parse_args();W=a.work.resolve();ap_paper=a.paper;out=[]
    def rec(cid,what,ok,detail=''):out.append((cid,what,'PASS' if ok else 'FAIL',detail))
    # V0: the solver source that `make test` and the records refer to
    try:
        sys.path.insert(0,str(ROOT/'code'/'lri_spin_boson_hpc'/'src'))
        from lri_spin.io import source_hash,read_record
        h=source_hash();r=read_record(ROOT/'inputs'/'validation_receipt'/'receipt.json')['source_sha256']
        rec('V0','solver source hash against the receipt',h==r,f'{h[:12]}… vs {r[:12]}…')
    except Exception as exc:rec('V0','solver source hash against the receipt',False,f'error: {exc}')
    # V1
    for f in sorted((ROOT/'results').glob('*')):
        g=W/'results'/f.name
        if f.suffix=='.json':
            ok=g.is_file() and close(json.loads(f.read_text()),json.loads(g.read_text()),1e-8,1e-6)
            rec('V1',f'results/{f.name}',ok,'floats to 1e-8 + 1e-6 relative')
        else:
            ok,d=same_text(f,g);rec('V1',f'results/{f.name}',ok,d)
    # V2
    files=sorted((ROOT/'note'/'tables').glob('*.tex'));res=[(f.name,)+same_text(f,W/'note'/'tables'/f.name) for f in files]
    bad=[f'{n} ({d})' for n,ok,d in res if not ok];nid=sum(1 for _,ok,d in res if ok and d=='identical')
    rec('V2',f'note/tables/*.tex ({len(files)} files)',files and not bad,
        'differs: '+'; '.join(bad) if bad else f'{nid} identical, {len(files)-nid} within one unit of the last digit')
    # V3
    for f in sorted((ROOT/'independent_check_compare').glob('*.json')):
        g=W/'independent_check_compare'/f.name
        ok=g.is_file() and close(json.loads(f.read_text()),json.loads(g.read_text()),1e-14,1e-12)
        rec('V3',f'independent_check_compare/{f.name}',ok,'floats to 1e-14 + 1e-12 relative')
    for f in sorted((ROOT/'independent_check_compare').glob('*.md')):
        ok,d=same_text(f,W/'independent_check_compare'/f.name,atol=1e-14);rec('V3',f'independent_check_compare/{f.name}',ok,d)
    # V4
    a=json.loads((ROOT/'method_comparison'/'comparison.json').read_text());p=W/'method_comparison'/'comparison.json'
    rec('V4','method_comparison/comparison.json',p.is_file() and close(a,json.loads(p.read_text()),1e-9,1e-9),'floats to 1e-9 + 1e-9 relative')
    ok,d=same_text(ROOT/'method_comparison'/'comparison.md',W/'method_comparison'/'comparison.md');rec('V4','method_comparison/comparison.md',ok,d)
    # V5
    figs=sorted((ROOT/'note'/'figures').glob('*.pdf'))
    miss=[f.name for f in figs if not ((W/'note'/'figures'/f.name).is_file() and (W/'note'/'figures'/f.name).stat().st_size>0)]
    rec('V5',f'note/figures/*.pdf ({len(figs)} files)',figs and not miss,'not regenerated: '+', '.join(miss) if miss else 'all regenerated')
    # V6
    tex=(ROOT/'note'/'lri_nrg_1d_note.tex').read_text()
    defined=set(re.findall(r'\\newcommand\{\\(nrg[A-Za-z]+)\}',(ROOT/'note'/'tables'/'numbers.tex').read_text()))
    used=set(re.findall(r'\\(nrg[A-Za-z]+)',tex))
    inputs=re.findall(r'\\input\{(tables/[^}]+)\}',tex);graphics=re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',tex)
    bad=sorted(used-defined)+[t for t in inputs if not (ROOT/'note'/t).is_file()]+[g for g in graphics if not (ROOT/'note'/g).is_file()]
    rec('V6',f'note: {len(used)} macros, {len(inputs)} tables, {len(graphics)} figures',not bad,'missing: '+', '.join(bad) if bad else 'all present')
    # V7
    E=json.loads((HERE/'expected.json').read_text())
    for e in E['values']:
        try:
            rows=json.loads((W/e['file']).read_text());r=pick(rows,e['key']) if e.get('key') else rows;got=r[e['field']]
            tol=e.get('atol');diff=abs(got-e['value']);ok=diff<=tol
            rec('V7',e['name'],ok,f"{got!r} vs {e['value']!r} (|diff| {diff:.1e}, tol {tol:g})")
        except Exception as exc:rec('V7',e['name'],False,f'error: {exc}')
    # V8: the paper's NRG numbers (results_map.md), recomputed from the regenerated files
    Q=json.loads((HERE/'quoted_numbers.json').read_text())
    for e in Q['numbers']:
        what=e['id']+(f" \\{e['macro']}" if 'macro' in e else '')
        try:
            got=quoted_text(e['source'],W)
            ok,d=(got==e['printed'],'equal' if got==e['printed'] else 'differs') if e['compare']=='exact' else same_str(exact_exponents(got),exact_exponents(e['printed']))
            rec('V8',what,ok,f'{got!r} vs printed {e["printed"]!r} ({d})')
        except Exception as exc:rec('V8',what,False,f'error: {exc}')
    ok,d=paper_check(Q,ap_paper)
    out.append(('V8','verify/quoted_numbers.json against the paper (paper/numbers.tex, main.tex, sections/)','SKIP' if ok is None else
                'PASS' if ok else 'FAIL',d))
    n_bad=sum(1 for r in out if r[2]=='FAIL');n_skip=sum(1 for r in out if r[2]=='SKIP');n_ok=len(out)-n_bad-n_skip
    tally=f'{n_ok} PASS, {n_bad} FAIL'+(f', {n_skip} SKIP' if n_skip else '')
    md=['# VERIFY: `make replay` against the released files','',tally,'',
        '| check | what | result | detail |','|---|---|---|---|']+[f'| {c} | {w} | {s} | {d} |' for c,w,s,d in out]
    (W/'reproduced').mkdir(parents=True,exist_ok=True);(W/'reproduced'/'VERIFY.md').write_text('\n'.join(md)+'\n')
    for c,w,s,d in out:
        if c not in ('V7','V8') or s!='PASS' or w.startswith('verify/quoted'):print(f'{c}  {s}  {w}  {d}')
    n8=[r for r in out if r[0]=='V8' and not r[1].startswith('verify/quoted')]
    print(f"V8  {sum(1 for r in n8 if r[2]=='PASS')} of {len(n8)} paper numbers recomputed (details in VERIFY.md)")
    print(f'VERIFY: {tally}  ->  {W/"reproduced"/"VERIFY.md"}')
    sys.exit(1 if n_bad else 0)


if __name__=='__main__':
    main()
