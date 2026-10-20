#!/usr/bin/env python3
"""Compile unmodified physics in temporary copies, with nonprinting audit hooks."""
import argparse
import gzip
import shutil
import subprocess
from common import ROOT, PARTS, AUDIT_TEX, dumps, macro_names, log_summary, save_json, run

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*')
    args=ap.parse_args()
    report_path=ROOT/'reports/standalone_builds.json'
    import json
    results=json.loads(report_path.read_text()) if report_path.exists() else {}
    for p in PARTS:
        tag=p['tag']
        if args.only and tag not in args.only: continue
        src=ROOT/'sources'/tag
        dest=ROOT/'build/standalone'/tag
        # This directory is an owned temporary build. Never let a removed
        # optional source survive and change an IfFileExists branch.
        if dest.exists(): shutil.rmtree(dest)
        shutil.copytree(src,dest,dirs_exist_ok=True)
        f=dest/(p['main']+'.tex')
        s=f.read_text(); names=macro_names(src)
        # Audit positions delimit title/contents without changing visible text.
        extra='\\usepackage{etoolbox}\n'+AUDIT_TEX+'\n\\def\\AuditPart{'+tag+'}\n'
        extra+=r'\let\AuditToc\tableofcontents'+'\n'
        extra+=r'\renewcommand{\tableofcontents}{\AuditPosition{toc-start}\AuditToc\AuditPosition{toc-end}}'+'\n'
        s=s.replace(r'\begin{document}',extra+'\n'+r'\begin{document}'+'\n'+dumps(names,'start'),1)
        s=s.replace(r'\end{document}',dumps(names,'end')+'\n'+r'\end{document}')
        f.write_text(s)
        print('Building standalone',tag,flush=True)
        with (dest/'console.txt').open('w') as log:
            cp=subprocess.run(['latexmk','-pdf','-synctex=1','-interaction=nonstopmode','-halt-on-error',f.name],cwd=dest,stdout=log,stderr=subprocess.STDOUT)
        if cp.returncode:
            print((dest/'console.txt').read_text()[-3500:],flush=True)
            raise SystemExit(cp.returncode)
        assert (dest/(p['main']+'.pdf')).stat().st_size
        with gzip.open(dest/(p['main']+'.synctex.gz'),'rb') as syn: assert syn.read(16)
        results[tag]=log_summary(dest/(p['main']+'.log'))
        save_json(report_path,results)
        print(tag,results[tag]['pages'],'pages;',results[tag]['overfull_boxes'],'overfull boxes',flush=True)

if __name__=='__main__': main()
