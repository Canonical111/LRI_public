#!/usr/bin/env python3
"""Build the standalone note without leaving TeX auxiliary files in the archive."""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 tex=ROOT/'note/C6_progress_note.tex'
 exe=shutil.which('pdflatex')
 if not exe:raise SystemExit('pdflatex is required. Install TeX Live and the packages listed in the source.')
 logs=[]
 with tempfile.TemporaryDirectory(prefix='c6_latex_') as td:
  wd=Path(td);shutil.copy2(tex,wd/tex.name)
  env=dict(os.environ,SOURCE_DATE_EPOCH='1791331200',FORCE_SOURCE_DATE='1')
  for run in range(3):
   p=subprocess.run([exe,'-interaction=nonstopmode','-halt-on-error',tex.name],cwd=wd,env=env,text=True,errors="replace",stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   logs.append(p.stdout)
   if p.returncode:
    err=ROOT/'outputs/latex_failure.txt';err.write_text(p.stdout)
    raise SystemExit('LaTeX failed. See outputs/latex_failure.txt; no new PDF installed.')
  log=(wd/'C6_progress_note.log').read_text(errors='replace')
  warnings=[x for x in log.splitlines() if any(s in x for s in ('Overfull','LaTeX Warning','Package hyperref Warning'))]
  shutil.copy2(wd/'C6_progress_note.pdf',ROOT/'note/C6_progress_note.pdf')
  meta={'engine':subprocess.run([exe,'--version'],text=True,errors="replace",stdout=subprocess.PIPE).stdout.splitlines()[0],'runs':3,'source_sha256':hashlib.sha256(tex.read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256((ROOT/'note/C6_progress_note.pdf').read_bytes()).hexdigest(),'warnings':warnings,'self_contained_tex':True,'external_figure_files_required':False,'shell_escape_used':False}
  (ROOT/'outputs/build_report.json').write_text(json.dumps(meta,indent=2)+'\n')
  print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
