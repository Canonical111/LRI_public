#!/usr/bin/env python3
"""Audit packaged source identity, Python syntax, Wolfram delimiters and reruns.

This is an integrity/transcription audit, not a mathematical or Wolfram-kernel
verification. The report is deterministic for unchanged inputs. Manifest status
is printed separately so writing the report cannot invalidate its own checksum.
"""
from __future__ import annotations
import argparse, ast, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def wolfram_balance(text: str) -> tuple[bool,str]:
    """Check delimiters outside strings and nested (* comments *)."""
    pairs={']':'[','}':'{',')':'('}; stack=[]; i=0; comments=0; string=False
    while i<len(text):
        if comments:
            if text.startswith('(*',i): comments+=1; i+=2
            elif text.startswith('*)',i): comments-=1; i+=2
            else: i+=1
            continue
        c=text[i]
        if string:
            if c=='\\': i+=2; continue
            if c=='"': string=False
            i+=1; continue
        if text.startswith('(*',i): comments=1; i+=2; continue
        if c=='"': string=True
        elif c in '[{(': stack.append(c)
        elif c in ']})':
            if not stack or stack.pop()!=pairs[c]: return False,f'unmatched {c} at offset {i}'
        i+=1
    return (not stack and not string and not comments, 'balanced' if not stack and not string and not comments else 'unclosed delimiter/string/comment')

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--skip-manifest',action='store_true',help='Use after intentionally rerunning/modifying generated outputs')
    args=ap.parse_args(); errors=[]
    required=['README.md','requirements.txt','note/C6_progress_note.tex','note/C6_progress_note.pdf','inputs/canonical/recommended_real_nine.json','inputs/upstream_reduced_setup.md','code/wolfram/C6Project.wl','outputs/reassembly.json','outputs/build_report.json','outputs/tables/wheel_convergence.csv','outputs/figures/wheel_convergence.pdf','provenance/source_manifest.json']
    for f in required:
        if not (ROOT/f).is_file(): errors.append('missing '+f)
    syntax=[]
    for p in sorted(ROOT.rglob('*.py')):
        if '.venv' in p.parts: continue
        try: ast.parse(p.read_text(),filename=str(p.relative_to(ROOT))); syntax.append(str(p.relative_to(ROOT)))
        except (SyntaxError,UnicodeDecodeError) as ex: errors.append('Python syntax '+str(p.relative_to(ROOT))+': '+str(ex))
    wl=[]
    for p in sorted((ROOT/'code/wolfram').glob('*')):
        if p.suffix in ('.wl','.wlt'):
            ok,msg=wolfram_balance(p.read_text()); wl.append({'file':str(p.relative_to(ROOT)),'balanced':ok})
            if not ok: errors.append(str(p.relative_to(ROOT))+': '+msg)
    src=json.loads((ROOT/'provenance/source_manifest.json').read_text()); patches={p['path']:p for p in json.loads((ROOT/'provenance/portability_patches.json').read_text())}
    patched=[]
    for rec in src:
        rel=rec['packaged_path']; p=ROOT/rel
        if not p.is_file(): errors.append('source missing '+rel); continue
        if digest(p)==rec['sha256']: continue
        patch=patches.get(rel)
        if patch and hashlib.sha256(p.read_text().replace(patch['new'],patch['old']).encode()).hexdigest()==rec['sha256']:
            patched.append(rel)
        else: errors.append('source hash mismatch '+rel)
    tasks=[]
    for p in sorted((ROOT/'outputs/rerun').glob('*/execution.json')):
        d=json.loads(p.read_text()); tasks.append({'id':d['id'],'status':d['status']})
        if d['status']!='passed': errors.append('task not passed '+d['id'])
    if len(tasks)!=31: errors.append(f'expected 31 selected task records, found {len(tasks)}')
    comp=json.loads((ROOT/'outputs/build_report.json').read_text())
    if comp.get('warnings'): errors.append('LaTeX warnings: '+repr(comp['warnings']))
    for name,key in [('C6_progress_note.tex','source_sha256'),('C6_progress_note.pdf','pdf_sha256')]:
        if digest(ROOT/'note'/name)!=comp.get(key): errors.append('LaTeX build hash mismatch '+name)
    assembly=json.loads((ROOT/'outputs/reassembly.json').read_text())
    if not all(assembly['exact_checks'].values()): errors.append('reassembly exact check failure')
    forbidden=[]
    for p in ROOT.rglob('*'):
        if '.venv' in p.parts: continue
        if p.is_file() and (p.suffix.lower() in {'.pyc','.pyo','.aux','.log','.out','.toc','.ttf','.otf','.woff','.woff2','.zip'} or '__pycache__' in p.parts): forbidden.append(str(p.relative_to(ROOT)))
    if forbidden: errors.append('temporary/font/nested-archive files '+repr(forbidden))
    new_scripts=['reproduce.py','make_outputs.py','make_figures.py','build_note.py']
    for name in new_scripts:
        text=(ROOT/'code'/name).read_text()
        if re.search(r"Path\(['\"]/mnt/data",text): errors.append('absolute runtime dependency '+name)
    report={'scope':'Integrity and static syntax/transcription checks, not Wolfram execution or a new physical/mathematical proof.','all_structural_checks_passed':not errors,'source_records_checked':len(src),'documented_patched_sources':patched,'python_files_parsed':len(syntax),'wolfram_static_checks':wl,'selected_task_records':tasks,'selected_tasks_passed':len([t for t in tasks if t['status']=='passed']),'latex_warnings':comp.get('warnings'),'reassembly_exact_checks':assembly['exact_checks'],'errors':errors}
    out=ROOT/'outputs/package_audit.json'; out.write_text(json.dumps(report,indent=2)+'\n')
    manifest_errors=[]; manifest=ROOT/'MANIFEST.sha256'
    if not args.skip_manifest and manifest.exists():
        for line in manifest.read_text().splitlines():
            h,rel=line.split('  ',1); p=ROOT/rel
            if not p.is_file() or digest(p)!=h: manifest_errors.append(rel)
    status='skipped' if args.skip_manifest else 'not-yet-created' if not manifest.exists() else 'passed' if not manifest_errors else 'failed'
    print(json.dumps({'report':str(out.relative_to(ROOT)),'all_structural_checks_passed':not errors,'selected_tasks_passed':report['selected_tasks_passed'],'python_files_parsed':len(syntax),'manifest_status':status,'manifest_mismatches':manifest_errors,'errors':errors},indent=2))
    return 1 if errors or manifest_errors else 0
if __name__=='__main__': raise SystemExit(main())
