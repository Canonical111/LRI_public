#!/usr/bin/env python3
"""Check source preservation, macro isolation, figures, and extracted PDF text.

Uses only Python's standard library, plus the external Poppler executables.
Never normalizes arbitrary scientific numbers away.
"""
import argparse
from collections import Counter
import difflib
import gzip
import json
import re
import subprocess
import textwrap
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from common import ROOT, PARTS, command_arg, digest, log_summary, save_json, uncomment

def equivalent_sources(p):
    """Independent inverse audit of all physics bodies and input files.

    Only reference namespaces, resolved file paths, the moved title/contents,
    and the inner-part command are normalized. Numbers and prose are untouched.
    """
    tag=p['tag']; src=ROOT/'sources'/tag; dst=ROOT/'parts'/tag
    differences=[]
    keys=re.compile(r'\\(label|ref|eqref|cref|Cref|autoref|pageref|nameref|cite[a-zA-Z]*|nocite|bibitem)(\*?\s*(?:\[[^]]*\]\s*)*)\{([^{}]+)\}')
    paths=re.compile(r'\\(input|include|inputrows|IfFileExists|includegraphics|widefig)(\*?\s*(?:\[[^]]*\]\s*)*)\{([^{}]+)\}')
    def normalize_source(s,derived):
        s=uncomment(s)
        if derived:
            def key(m):
                return '\\'+m[1]+m[2]+'{'+','.join(v.removeprefix(tag+':') for v in m[3].split(','))+'}'
            s=keys.sub(key,s)
            s=s.replace('\\hyperref['+tag+':','\\hyperref[')
            s=s.replace(r'\SourcePart{',r'\part{')
        def path(m):
            v=m[3]
            if '#' in v or '\\' in v: return m[0]
            if derived: v=v.removeprefix('parts/'+tag+'/')
            matches=[]
            for d in ('','sections','sections/d2','sections/d3','figures','tables'):
                for ext in ([''] if Path(v).suffix else ['', '.tex','.pdf','.png']):
                    f=src/d/(v+ext)
                    if f.is_file(): matches.append(f.relative_to(src).as_posix())
            v=matches[0] if matches else v if Path(v).suffix else v+'.tex'
            return '\\'+m[1]+m[2]+'{'+v+'}'
        s=paths.sub(path,s)
        return s.strip()
    for f in sorted(src.rglob('*.tex')):
        original=f.read_text(); derived=(dst/f.relative_to(src)).read_text()
        if f.name==p['main']+'.tex':
            original=original.split(r'\begin{document}',1)[1].rsplit(r'\end{document}',1)[0]
            original=original.replace(r'\maketitle','').replace(r'\tableofcontents','')
        a=normalize_source(original,False); b=normalize_source(derived,True)
        if a!=b:
            differences.append({'file':f.relative_to(src).as_posix(),
              'diff':list(difflib.unified_diff(a.splitlines(),b.splitlines(),lineterm=''))})
    return differences

def audit(path):
    obj={'macros':{},'outside':{},'events':{},'positions':{},'ranges':{}}
    tag=path.parent.name if path.parent.name in {p['tag'] for p in PARTS} else None
    for line in path.read_text().splitlines():
        fields=line.split('|')
        if fields[0]=='MACRO':
            phase,name,value=line.split('|',3)[1:]
            if phase.startswith('outside-'):
                tag=phase.rsplit('-',1)[1]
                obj['outside'].setdefault(phase,{})[name]=value
            else: obj['macros'].setdefault(tag,{}).setdefault(phase,{})[name]=value
        elif fields[0]=='EVENT':
            val='|'.join(fields[2:]).strip()
            val=re.sub(r'parts/'+fields[1]+r'/', '',val)
            val=re.sub(r'/+', '/', val)
            obj['events'].setdefault(fields[1],[]).append(val)
        elif fields[0]=='POS': obj['positions'][fields[1]]=(int(fields[2]),float(fields[4])/65536*72/72.27)
        elif fields[0] in ('PART_BEGIN','PART_END'):
            obj['ranges'].setdefault(fields[1],{})[fields[0]]=int(fields[2])
    return obj

def bbox(pdf,cache):
    if not cache.exists() or cache.stat().st_mtime<pdf.stat().st_mtime:
        subprocess.run(['pdftotext','-raw','-bbox',str(pdf),str(cache)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    # Poppler can emit control-code glyphs from legacy math fonts. Preserve
    # distinct codes in the private-use range so XML parsing does not erase them.
    xml=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',lambda m:chr(0xe000+ord(m[0])),cache.read_text())
    doc=ET.fromstring(xml)
    return list(doc.iter('{http://www.w3.org/1999/xhtml}page'))

def roman(n):
    out=''
    for v,r in ((1000,'m'),(900,'cm'),(500,'d'),(400,'cd'),(100,'c'),(90,'xc'),(50,'l'),(40,'xl'),(10,'x'),(9,'ix'),(5,'v'),(4,'iv'),(1,'i')):
        while n>=v: out+=r; n-=v
    return out

def lines_from(pages,first=1,last=None,positions=None,page_offset=0,roman_folios=False):
    lines=[]; last=last or len(pages)
    for n in range(first,last+1):
        page=pages[n-1]; height=float(page.attrib['height'])
        words=list(page.iter('{http://www.w3.org/1999/xhtml}word'))
        last_y=None; last_x=None; current=[]
        for line in words:
            y0=float(line.attrib['yMin']); y1=float(line.attrib['yMax'])
            text=''.join(line.itertext())
            if y0<48: continue  # running head, above every source text block
            folio=roman(n) if roman_folios else str(n-page_offset)
            if y1>height-42 and text==folio: continue  # page number only
            if positions:
                p0,bottom0=positions['toc-start']; p1,bottom1=positions['toc-end']
                begin=height-bottom0; end=height-bottom1
                if p0<n<p1: continue
                # The final position is a baseline: descenders extend below it.
                # Use the word's top, so the last contents line is not retained.
                if p0==p1==n and y0>=begin-1 and y0<=end: continue
                if n==p0 and p0<p1 and y0>=begin-1: continue
                if n==p1 and p0<p1 and y0<=end: continue
            x=float(line.attrib['xMin'])
            if last_y is not None and abs(y0-last_y)>3 and x<last_x:
                lines.append(' '.join(current)); current=[]
            current.append(text); last_y=y0; last_x=x
        if current: lines.append(' '.join(current))
    return lines

def body_only(lines,tag):
    front=next((p for p in PARTS if p['tag']==tag and p.get('front')),None)
    if front:
        # The opening part has no title or abstract: its text starts after its own
        # unnumbered heading, which both builds print.
        heading=command_arg((ROOT/'sources'/tag/(front['main']+'.tex')).read_text(),'section*')
        for i,line in enumerate(lines):
            if line.strip()==heading: return lines[i+1:]
    elif tag == 'htp':
        for i,line in enumerate(lines):
            if re.fullmatch(r'(?:1\s+)?Summary',line): return lines[i+1:]
    else:
        for i,line in enumerate(lines):
            if line.strip()=='Abstract': return lines[i+1:]
    raise ValueError('Cannot locate the start of the physics text for '+tag)

def normalize(lines):
    s='\n'.join(lines)
    s=unicodedata.normalize('NFKC',s).replace('\u00ad','')
    # PDF line wrapping/hyphenation and ligatures, not numeric values.
    s=re.sub(r'(?<=[A-Za-z])[-‐]\s*\n\s*(?=[A-Za-z])','',s)
    s=re.sub(r'\s+',' ',s).strip()
    return s

def compact_text(text, tag):
    # Full whitespace normalization also joins URLs split by xurl. Preserve
    # every digit and sign; only alphabetic discretionary/compound hyphens
    # are normalized, with the verbatim source audit as an independent guard.
    s=re.sub(r'\s+','',text)
    s=re.sub(r'(?<=[A-Za-z])-(?=[A-Za-z0-9])|(?<=[A-Za-z0-9])-(?=[A-Za-z])','',s)
    headers={
      'htp':['resultvaluepkgrecordscommandtolerance','package(code/)d,rolecontent,records,cost'],
      'ht':['resultvaluepkgrecordscommandtolerance'],
      'nrg':['termmeaning'],
      'mc':['d=2series,continuedsseries∆εω0[interval]χ2/dofσfixedσprofiledeligible',
            'd=3series,continuedsseries∆εω0[interval]χ2/dofσfixedσprofiledeligible'],
    }
    removed={}
    for header in headers.get(tag,[]):
        removed[header]=s.count(header)
        s=s.replace(header,'')
    return s,removed

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--allow-differences',action='store_true',help='write diagnostics while developing; does not mark them passed')
    args=ap.parse_args()
    out=ROOT/'reports'; cache=ROOT/'build/text'; cache.mkdir(parents=True,exist_ok=True)
    pdf=ROOT/'lri_combined_notes.pdf'
    with gzip.open(ROOT/'lri_combined_notes.synctex.gz','rb') as f: assert f.read(16)
    combined=audit(ROOT/'lri_combined_notes.audit'); all_pages=bbox(pdf,cache/'combined-raw.html')
    offset=len(all_pages)-combined['ranges']['rs']['PART_END']
    source_manifest=json.loads((out/'source_manifest.json').read_text())
    totals={}; failures=[]
    for p in PARTS:
        tag=p['tag']; folder=ROOT/'build/standalone'/tag
        standalone=audit(folder/(p['main']+'.audit'))
        spages=bbox(folder/(p['main']+'.pdf'),cache/(tag+'-raw.html'))
        # The opening part sits in the roman front matter, where the page counter is the physical page.
        shift=0 if p.get('front') else offset
        ranges=combined['ranges'][tag]; first=ranges['PART_BEGIN']+shift; last=ranges['PART_END']+shift
        before=combined['outside']['outside-before-'+tag]; after=combined['outside']['outside-after-'+tag]
        leak=[name for name in before if before[name]!=after.get(name)]
        changed=[]
        for phase in ('start','end'):
            expected=standalone['macros'][tag][phase]; actual=combined['macros'][tag][phase]
            changed += [phase+':'+name for name in expected if expected[name]!=actual.get(name)]
        expected_events=standalone['events'].get(tag,[]); actual_events=combined['events'].get(tag,[])
        # Figure draw events and exact original bytes provide independent checks.
        assets=[]
        source_changed=[]
        for name,record in source_manifest[tag]['files'].items():
            source=ROOT/'sources'/tag/name
            if digest(source)!=record['sha256']: source_changed.append(name)
            if source.suffix.lower()!='.tex':
                target=ROOT/'parts'/tag/name
                assets.append(name)
                if digest(target)!=record['sha256']: source_changed.append('copied:'+name)
        a=normalize(body_only(lines_from(spages,positions=standalone['positions']),tag))
        b=normalize(body_only(lines_from(all_pages,first,last,page_offset=offset,roman_folios=bool(p.get('front'))),tag))
        (cache/(tag+'-standalone.txt')).write_text(a+'\n')
        (cache/(tag+'-combined.txt')).write_text(b+'\n')
        ca,ha=compact_text(a,tag); cb,hb=compact_text(b,tag)
        # A normalized line is a 100-character chunk, after whitespace and
        # running/continuation-header normalization. Entire diffs are retained.
        al=textwrap.wrap(ca,width=100,break_long_words=True,break_on_hyphens=False)
        bl=textwrap.wrap(cb,width=100,break_long_words=True,break_on_hyphens=False)
        diff=list(difflib.unified_diff(al,bl,fromfile='standalone/'+tag,tofile='combined/'+tag,lineterm=''))
        differing=sum(1 for line in diff if line.startswith(('+','-')) and not line.startswith(('+++','---')))
        (out/(tag+'_text_diff.txt')).write_text('\n'.join(diff)+'\n')
        # Identical character inventory is not sufficient alone: combine it
        # with the inverse source audit, runtime macro checks and figure events.
        missing=dict(Counter(ca)-Counter(cb)); added=dict(Counter(cb)-Counter(ca))
        at=re.findall(r'[A-Za-z_]+|\d+(?:\.\d+)*|.',ca)
        bt=re.findall(r'[A-Za-z_]+|\d+(?:\.\d+)*|.',cb)
        sm=difflib.SequenceMatcher(None,at,bt,autojunk=True)
        edits=[{'kind':op,'standalone':''.join(at[i:j]),'combined':''.join(bt[k:l]),
                'explanation':'UNREVIEWED'} for op,i,j,k,l in sm.get_opcodes() if op!='equal']
        source_text_diff=equivalent_sources(p)
        save_json(out/(tag+'_source_differences.json'),source_text_diff)
        invariant=not(leak or changed or source_changed or source_text_diff or expected_events!=actual_events or missing or added)
        for e in edits:
            if invariant:
                e['explanation']=('PDF reading-order difference caused by float, footnote, or table placement after pagination. '
                    'The complete part has exactly the same non-whitespace character inventory after the recorded header normalization; '
                    'the independent inverse-source check preserves prose, numbers, and source order exactly, '
                    'all runtime macro fingerprints agree, and every figure draw event agrees. '
                    'No text replacement or numerical correction was made.')
        save_json(out/(tag+'_text_differences.json'),edits)
        status=invariant
        totals[tag]={'physical_pages':[first,last],'standalone_pages':len(spages),
            'differing_normalized_lines':differing,'token_difference_blocks':len(edits),
            'macro_definitions_checked':len(standalone['macros'][tag]['start']),
            'macro_fingerprint_differences':changed,'leaked_definitions':leak,
            'figure_events_standalone':dict(Counter(expected_events)),
            'figure_events_combined':dict(Counter(actual_events)),
            'figure_events_identical':expected_events==actual_events,
            'figure_assets_checked':len(assets),'changed_source_or_asset_files':source_changed,
            'physics_source_files_differing':len(source_text_diff),
            'continuation_headers_removed':{'standalone':ha,'combined':hb},
            'unbalanced_pdf_characters':{'standalone_only':missing,'combined_only':added},
            'remaining_differences_explained':invariant,
            'passed':status}
        if not status: failures.append(tag)
        print(tag,totals[tag]['physical_pages'],'line differences',differing,'token blocks',len(edits),
              'macro differences',len(changed),'leaks',len(leak),'figures match',expected_events==actual_events,flush=True)
    save_json(out/'checks.json',{'pages':len(all_pages),'front_matter_pages':offset,'parts':totals})
    build=log_summary(ROOT/'lri_combined_notes.log'); save_json(out/'combined_build.json',build)
    if any(build[k] for k in ('errors','undefined_references','undefined_citations','multiply_defined_labels','duplicate_destinations')): failures.append('build')
    if failures and not args.allow_differences: raise SystemExit('Checks need attention: '+', '.join(failures))

if __name__=='__main__': main()
