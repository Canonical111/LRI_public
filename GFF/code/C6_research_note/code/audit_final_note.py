#!/usr/bin/env python3
"""Audit the trimmed note's definitions/references and protected equation bytes.

This verifies editorial invariance and source structure, not mathematical truth.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def equation(text: str, label: str) -> str:
    i=text.index('\\label{'+label+'}')
    candidates=[(text.rfind('\\begin{'+e+'}',0,i),e) for e in ('equation','align')]
    start,env=max(candidates)
    if start<0:
        raise ValueError('No containing display for '+label)
    end=text.index('\\end{'+env+'}',i)+len('\\end{'+env+'}')
    return re.sub(r'\s+','',text[start:end])

def main() -> int:
    tex=(ROOT/'note/C6_progress_note.tex').read_text()
    edit=json.loads((ROOT/'provenance/editorial_revision.json').read_text())
    labels=re.findall(r'\\label\{([^}]+)\}',tex)
    references=[]
    for group in re.findall(r'\\(?:[Cc]ref|eqref|ref)\{([^}]+)\}',tex):
        references.extend(group.split(','))
    cited=set()
    for group in re.findall(r'\\cite(?:\[[^\]]*\])?\{([^}]+)\}',tex):
        cited.update(group.split(','))
    bibliography=set(re.findall(r'\\bibitem\{([^}]+)\}',tex))
    protected={}
    for label,expected in edit['protected_equations'].items():
        actual=hashlib.sha256(equation(tex,label).encode()).hexdigest()
        protected[label]=actual==expected
    banned_titles=[
        'The Mathematica-built-in alternatives',
        'What related evaluations do not solve',
        'Chebyshev orthogonality removes the coupled summation index',
        'First moments are not the needed primitive',
        'The optional all-log-sine form',
        'Eight calls are possible, but not preferred here',
        'A basis audit: useful exclusions, not independence',
        'Other genuine reductions and the history of alternatives',
        'Open issues and next steps',
    ]
    checks={
        'missing_crossreferences':sorted(set(references)-set(labels)),
        'duplicate_labels':sorted({x for x in labels if labels.count(x)>1}),
        'missing_citations':sorted(cited-bibliography),
        'unused_bibliography_entries':sorted(bibliography-cited),
        'external_TeX_dependencies':re.findall(r'\\(?:input|include|includegraphics|bibliography)\s*(?:\[[^\]]*\])?\s*\{[^}]+\}',tex),
        'unremoved_section_titles':[s for s in banned_titles if s in tex],
        'protected_equations_unchanged':protected,
    }
    okay=all(not checks[k] for k in checks if k!='protected_equations_unchanged') and all(protected.values())
    report={'scope':__doc__.strip(),'all_passed':okay,'source_sha256':hashlib.sha256(tex.encode()).hexdigest(),**checks}
    (ROOT/'outputs/final_note_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if okay else 1

if __name__=='__main__': raise SystemExit(main())
