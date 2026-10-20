#!/usr/bin/env python3
"""Regenerate a book from the seven authoritative public notes (stdlib only)."""
import argparse
from collections import Counter
import json
import re
import shutil
from pathlib import Path
from common import ROOT, PARTS, AUDIT_TEX, digest, save_json, uncomment, command_arg, group, macro_names, dumps

PACKAGE_RE=re.compile(r'\\usepackage\s*(?:\[([^]]*)\])?\s*\{([^}]+)\}')
KEY_RE=re.compile(r'\\(label|ref|eqref|cref|Cref|autoref|pageref|nameref|cite[a-zA-Z]*|nocite|bibitem)(\*?\s*(?:\[[^]]*\]\s*)*)\{([^{}]+)\}')
PATH_RE=re.compile(r'\\(input|include|inputrows|IfFileExists|includegraphics|widefig)(\*?\s*(?:\[[^]]*\]\s*)*)\{([^{}]+)\}')
COPY_EXT={'.tex','.pdf','.png','.jpg','.jpeg','.eps','.bib','.sty','.cls'}

def snapshot(public):
    manifest={}
    recorded=ROOT/'reports/source_manifest.json'
    recorded=json.loads(recorded.read_text()) if recorded.exists() else {}
    for p in PARTS:
        tag=p['tag']; note_dir=p.get('note_dir','note'); src=public/p['folder']/note_dir; dst=ROOT/'sources'/tag
        folder=(p['folder']+'/'+note_dir).rstrip('/')
        if p.get('front') and not (src/(p['main']+'.tex')).exists() and tag in recorded:
            # The public release ships no paper/ folder (author decision, 19 October 2026). The opening
            # part is then rebuilt from its tracked snapshot, after every file is checked against its
            # recorded SHA-256.
            for name,record in recorded[tag]['files'].items():
                if not (dst/name).is_file() or digest(dst/name)!=record['sha256']:
                    raise ValueError(tag+': tracked snapshot differs from its record: '+name)
            manifest[tag]=recorded[tag]
            continue
        if not (src/(p['main']+'.tex')).exists(): raise FileNotFoundError(folder+'/'+p['main']+'.tex')
        if dst.exists(): shutil.rmtree(dst)
        dst.mkdir(parents=True)
        files={}
        for f in sorted(src.rglob('*')):
            if not f.is_file() or f.suffix.lower() not in COPY_EXT: continue
            if f.name==p['main']+'.pdf': continue
            rel=f.relative_to(src)
            out=dst/rel; out.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(f,out)
            files[str(rel)]={'sha256':digest(f),'bytes':f.stat().st_size}
        manifest[tag]={'authoritative_folder':folder,'files':files}
        if p.get('front'):
            manifest[tag].update(readme_used=None, readme_sha256=None)
            continue
        readme=src/'README.md'
        if not readme.exists(): readme=public/p['folder']/'README.md'
        manifest[tag].update(readme_used=str(readme.relative_to(public)), readme_sha256=digest(readme))
    save_json(ROOT/'reports/source_manifest.json',manifest)

def replace_command(s,name,replacement=''):
    pat=re.compile(r'\\'+name+r'\s*\{')
    while (m:=pat.search(s)):
        _,end=group(s,m.end()-1)
        s=s[:m.start()]+replacement+s[end:]
    return s

def transform(s,p,source,counts):
    tag=p['tag']
    # Operate on active source only; comments remain byte-for-byte.
    def active_transform(a):
        def key(m):
            if '#' in m[3]: raise ValueError('Dynamic reference key requires explicit support')
            vals=','.join(tag+':'+v.strip() if v.strip()!='*' else '*' for v in m[3].split(','))
            counts['labels_prefixed' if m[1]=='label' else 'bibliography_keys_prefixed' if m[1]=='bibitem' else 'reference_keys_prefixed']+=len(m[3].split(','))
            return '\\'+m[1]+m[2]+'{'+vals+'}'
        a=KEY_RE.sub(key,a)
        def hyper(m):
            counts['reference_keys_prefixed']+=1
            return r'\hyperref['+tag+':'+m[1]+']'
        a=re.sub(r'\\hyperref\[([^]]+)\]',hyper,a)
        def path(m):
            value=m[3]
            if '#' in value or '\\' in value: return m[0]
            suffixes=[''] if Path(value).suffix else ['', '.tex', '.pdf', '.png']
            dirs=['','sections','sections/d2','sections/d3','figures','tables']
            matches=[]
            for d in dirs:
                for ext in suffixes:
                    candidate=source/d/(value+ext)
                    if candidate.is_file() and candidate not in matches: matches.append(candidate)
            if not matches:
                if m[1] in ('includegraphics','widefig'):
                    raise FileNotFoundError(tag+': unresolved '+m[0])
                # Retain deliberately absent optional contributions and their guards.
                target=Path(value if Path(value).suffix else value+'.tex')
                counts['absent_optional_paths']+=1
            else:
                target=matches[0].relative_to(source)
            counts['paths_changed']+=1
            return '\\'+m[1]+m[2]+'{parts/'+tag+'/'+target.as_posix()+'}'
        a=PATH_RE.sub(path,a)
        return a
    # Preserve verbatim/listing bodies; commands printed there are not live TeX.
    chunks=re.split(r'(\\begin\{(?:lstlisting|verbatim)\}[\s\S]*?\\end\{(?:lstlisting|verbatim)\})',s)
    for i in range(0,len(chunks),2):
        lines=[]
        for line in chunks[i].splitlines(keepends=True):
            m=re.search(r'(?<!\\)%',line)
            if m: lines.append(active_transform(line[:m.start()])+line[m.start():])
            else: lines.append(active_transform(line))
        chunks[i]=''.join(lines)
        # Multiline citation optional arguments cannot be handled a line at a time.
        def multiline_key(m):
            if all(v.strip().startswith(tag+':') or v.strip()=='*' for v in m[3].split(',')):
                return m[0]
            counts['reference_keys_prefixed']+=len(m[3].split(','))
            return '\\'+m[1]+m[2]+'{'+','.join(tag+':'+v.strip() for v in m[3].split(','))+'}'
        chunks[i]=KEY_RE.sub(multiline_key,chunks[i])
    return ''.join(chunks)

def abstract_excerpt(s,tag):
    if tag in ('ht','htp'):
        s=(ROOT/'sources'/tag/'sections/s01_summary.tex').read_text()
        if tag=='ht': s=s.split(r'\paragraph{What is computed.}',1)[1]
        else: s=s.split(r'\label{sec:summary}',1)[1]
    else: s=s.split(r'\begin{abstract}',1)[1].split(r'\end{abstract}',1)[0]
    s=s.replace(r'\noindent','').strip()
    # Select complete opening sentences verbatim; no new physics is composed.
    n=2 if tag in ('gff','ht') else 1
    end=0
    for _ in range(n):
        m=re.search(r'\.(?=\s|$)',s[end:])
        if not m: raise ValueError('Missing summary sentence')
        end+=m.end()
    # Citations resolve only inside each part's own bibliography, so the preface excerpt omits them.
    out=re.sub(r'~?\\cite[a-zA-Z]*\*?(?:\[[^]]*\])*\{[^{}]*\}','',s[:end])
    return re.sub(r'\s+',' ',out).strip()

def generate():
    package_options={}; report={}; part_entries=[]; front_entries=[]; excerpts=[]
    all_names=set()
    for p in PARTS: all_names.update(macro_names(ROOT/'sources'/p['tag']))
    all_names.update({'theequation','cl@section','theHequation'})
    for p in PARTS:
        tag=p['tag']; src=ROOT/'sources'/tag; dst=ROOT/'parts'/tag
        if dst.exists(): shutil.rmtree(dst)
        shutil.copytree(src,dst)
        original=(src/(p['main']+'.tex')).read_text()
        pre,body=original.split(r'\begin{document}',1)
        body=body.rsplit(r'\end{document}',1)[0]
        title=command_arg(pre,'title'); author=command_arg(pre,'author'); date=command_arg(pre,'date')
        names=macro_names(src); counts=Counter()
        counts['macros_scoped']=len(names); counts['macros_renamed']=0
        pkgs=[]
        for m in PACKAGE_RE.finditer(uncomment(pre)):
            for pkg in m[2].split(','):
                pkg=pkg.strip(); pkgs.append(pkg)
                package_options.setdefault(pkg,set()).add(m[1] or '')
        for f in sorted(src.rglob('*.tex')):
            if f.name==p['main']+'.tex': continue
            (dst/f.relative_to(src)).write_text(transform(f.read_text(),p,src,counts))
        pre=PACKAGE_RE.sub('',pre)
        pre=re.sub(r'\\documentclass(?:\[[^]]*\])?\{[^}]*\}','',pre)
        for cmd in ['title','author','date']: pre=replace_command(pre,cmd)
        # The standalone source checksum and PDF metadata describe a different artifact.
        pre=re.sub(r'\\edef\\SRINoteSourceMDfive\{\\pdfmdfivesum file \{[^}]*\}\}', '',pre)
        pre=replace_command(pre,'pdfinfo')
        pre=replace_command(pre,'hypersetup')
        # Explicit paths make inputs independent of the current working directory.
        counts['input_search_paths_replaced']=len(re.findall(r'\\def\\input@path',pre))
        pre=re.sub(r'\\def\\input@path\{(?:\{[^}]*\})*\}', '',pre)
        counts['graphic_search_paths_rebased']=len(re.findall(r'\\graphicspath',pre))
        pre=re.sub(r'\\graphicspath\{(?:\{[^}]*\})*\}',r'\\graphicspath{{parts/'+tag+r'/figures/}{parts/'+tag+r'/sections/d2/}{parts/'+tag+r'/sections/d3/}}',pre)
        pre=transform(pre,p,src,counts)
        body=transform(body,p,src,counts)
        counts['title_commands_moved']=1; counts['local_tocs_removed']=body.count(r'\tableofcontents')
        body=body.replace(r'\maketitle','').replace(r'\tableofcontents','')
        # GFF has four inner article parts. Preserve their headings and Roman numbering.
        counts['inner_parts_preserved']=len(re.findall(r'\\part\s*\{',body))
        body=re.sub(r'\\part(?=\s*\{)',r'\\SourcePart',body)
        (dst/'preamble.tex').write_text('% Generated local preamble; edit authoritative sources instead.\n'+pre)
        (dst/(p['main']+'.tex')).write_text('% Generated body; only mechanical merging changes.\n'+body)
        wrapper='\\clearpage\n\\SaveStructuralState\n'+dumps(sorted(all_names),'outside-before-'+tag)+'\\begingroup\n'
        wrapper+=r'\BeginSourcePart{'+tag+'}{'+str(p['size'])+'}{'+p['paper']+'}{'+p['margin']+'}\n'
        if tag in ('htp','ht','ai'):  # sources in default OT1 Computer Modern (no fontenc, no lmodern)
            wrapper+=r'\UseSourceComputerModern'+'\n'
        wrapper+='\\input{parts/'+tag+'/preamble.tex}\n'
        wrapper+=r'\def\SourceAuthor{'+author+'}\n'+r'\def\SourceDate{'+date+'}\n'
        # The page counter, not \thepage: the opening part has roman folios.
        wrapper+=r'\immediate\write\CombinedAuditStream{PART_BEGIN|'+tag+r'|\number\value{page}}'+'\n'
        if p.get('front'):
            # Unnumbered opening part: no part page, so Parts I-VII keep their numbers;
            # the contents line repeats the source's own unnumbered heading.
            title=command_arg(body,'section*')
            wrapper+=r'\phantomsection\addcontentsline{toc}{part}{'+title+'}\n'
        else:
            wrapper+=r'\part{'+title+'}\n'
        wrapper+=dumps(names,'start')
        wrapper+=r'\label{combined:'+tag+':start}'+'\n'
        wrapper+='\\input{parts/'+tag+'/'+p['main']+'.tex}\n'
        wrapper+='\\clearpage\n'+dumps(names,'end')
        wrapper+=r'\immediate\write\CombinedAuditStream{PART_END|'+tag+r'|\number\numexpr\value{page}-1\relax}'+'\n'
        wrapper+='\\endgroup\n\\RestoreStructuralState\n'
        wrapper+=dumps(sorted(all_names),'outside-after-'+tag)
        wrapper+=r'\label{combined:'+tag+':after}'+'\n'
        (dst/'part.tex').write_text(wrapper)
        (front_entries if p.get('front') else part_entries).append('\\input{parts/'+tag+'/part.tex}')
        if not p.get('front'):
            excerpt=abstract_excerpt(original,tag)
            excerpts.append((p['folder'],excerpt))
        report[tag]={'title_tex':title,'macro_names':names,'packages':pkgs,'changes':dict(counts)}
    conflicts={pkg for pkg,opts in package_options.items() if len(opts)>1}
    for tag,entry in report.items():
        entry['option_conflicts_resolved']=sorted(set(entry['packages']) & conflicts)
        entry['changes']['package_option_conflicts_resolved']=len(entry['option_conflicts_resolved'])
        entry['changes']['structural_state_fields_restored']=3
        entry['changes']['theorem_names_renamed']=0
        entry['changes']['source_font_restored']=int(tag in ('htp','ht','ai'))
        entry['changes']['standalone_checksum_metadata_removed']=int(tag=='sri')
    save_json(ROOT/'reports/mechanical_changes.json',report)
    save_json(ROOT/'reports/package_options.json',{p:sorted(v) for p,v in package_options.items()})
    preface=r'''\chapter*{Preface}
These seven research notes accompany the study of the long-range Ising CFT.
The public repository accompanying the paper (\url{https://github.com/Canonical111/LRI_public}) supplies the code, data, and
replays in the seven folders named below; its root \texttt{README.md} and each
folder's \texttt{results\_map.md} give the entry points. The published folder notes
remain authoritative. Each paragraph below is an excerpt from that part's
own abstract or summary, with its citations left to that part. Numbering and bibliographies remain local to each part.
\begingroup
\newcommand{\De}{\Delta_{\mathcal E}}\newcommand{\Ds}{\Delta_\sigma}
\newcommand{\eps}{\epsilon}\newcommand{\code}[1]{\texttt{#1}}
'''
    for folder,excerpt in excerpts:
        preface+='\n\\paragraph{'+folder.replace('_',r'\_')+'.} '+excerpt+'\n'
    preface+='\\endgroup\n\\clearpage\n'
    (ROOT/'preface.tex').write_text(preface)
    loaded=set()
    for m in PACKAGE_RE.finditer(MASTER): loaded.update(x.strip() for x in m[2].split(','))
    extras=[]
    for pkg,opts in sorted(package_options.items()):
        if pkg in loaded: continue
        nonempty=opts-{''}
        if len(nonempty)>1: raise ValueError('Unreviewed options for new package '+pkg)
        opt=next(iter(nonempty),'')
        extras.append('\\usepackage'+('['+opt+']' if opt else '')+'{'+pkg+'}')
    master=MASTER.replace('%%EXTRA_PACKAGES%%','\n'.join(extras)).replace('%%AUDIT%%',AUDIT_TEX).replace('%%FRONT%%','\n'.join(front_entries)).replace('%%PARTS%%','\n'.join(part_entries))
    (ROOT/'lri_combined_notes.tex').write_text(master)
    print('Generated the opening part and seven note parts; source snapshots and mechanical counts recorded.' if any(p.get('front') for p in PARTS) else 'Generated seven parts; source snapshots and mechanical counts recorded.')

MASTER=r'''% Generated by tools/build_combined.py; do not hand-edit.
\documentclass[11pt,oneside,openany,notitlepage]{report}
\usepackage[margin=23mm,headheight=14pt]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{microtype,amsmath,amssymb,mathtools,booktabs,array,longtable}
\DeclareMathVersion{sourcecm}
\SetSymbolFont{operators}{sourcecm}{OT1}{cmr}{m}{n}
\SetSymbolFont{letters}{sourcecm}{OML}{cmm}{m}{it}
\SetSymbolFont{symbols}{sourcecm}{OMS}{cmsy}{m}{n}
\SetSymbolFont{largesymbols}{sourcecm}{OMX}{cmex}{m}{n}
\SetMathAlphabet{\mathbf}{sourcecm}{OT1}{cmr}{bx}{n}
\SetMathAlphabet{\mathsf}{sourcecm}{OT1}{cmss}{m}{n}
\SetMathAlphabet{\mathit}{sourcecm}{OT1}{cmr}{m}{it}
\SetMathAlphabet{\mathtt}{sourcecm}{OT1}{cmtt}{m}{n}
\usepackage{lmodern}
\usepackage{graphicx,xcolor,fancyhdr,listings,needspace,etoolbox,dsfont,rotating}
\usepackage[shortlabels]{enumitem}
\usepackage[font=small,labelfont=bf]{caption}
\usepackage{pgfplots,url,xurl}
%%EXTRA_PACKAGES%%
\usepackage[hidelinks,bookmarksnumbered]{hyperref}
\hypersetup{pdftitle={The long-range Ising CFT: research notes},pdfauthor={Zechuan Zheng}}
\title{The long-range Ising CFT: research notes}
\author{Zechuan Zheng}
\date{Combined public edition}
%%AUDIT%%
\makeatletter
% Article-compatible structure: retain each note's section and appendix numbers.
\renewcommand\thesection{\arabic{section}}
\renewcommand\theequation{\arabic{equation}}
\renewcommand\thefigure{\arabic{figure}}
\renewcommand\thetable{\arabic{table}}
\renewcommand\appendix{\par\setcounter{section}{0}\setcounter{subsection}{0}%
  \renewcommand\thesection{\Alph{section}}}
\renewenvironment{thebibliography}[1]
 {\section*{\refname}%
  \list{\@biblabel{\@arabic\c@enumiv}}%
       {\settowidth\labelwidth{\@biblabel{#1}}\leftmargin\labelwidth
        \advance\leftmargin\labelsep\@openbib@code
        \usecounter{enumiv}\let\p@enumiv\@empty\renewcommand\theenumiv{\@arabic\c@enumiv}}%
  \sloppy\clubpenalty4000\@clubpenalty\clubpenalty\widowpenalty4000\sfcode`\.=1000\relax}
 {\def\@noitemerr{\@latex@warning{Empty bibliography}}\endlist}
\providecommand\refname{References}
\setcounter{secnumdepth}{3}
\newcommand\UseSourceComputerModern{%
  \renewcommand\encodingdefault{OT1}\renewcommand\rmdefault{cmr}%
  \renewcommand\sfdefault{cmss}\renewcommand\ttdefault{cmtt}%
  \normalfont\mathversion{sourcecm}%
  \captionsetup{font=normalsize,labelfont=normalfont}%
  \emergencystretch=3em}
% amsmath's numberwithin changes formatting/reset lists globally; grouping alone
% does not undo those assignments. Save and restore them explicitly.
\newcommand\SaveStructuralState{%
  \let\SavedEquationFormat\theequation\let\SavedSectionReset\cl@section
  \let\SavedEquationAnchor\theHequation}
\newcommand\RestoreStructuralState{%
  \let\theequation\SavedEquationFormat\let\cl@section\SavedSectionReset
  \let\theHequation\SavedEquationAnchor}
\newcounter{sourcepart}
\newcommand\SourcePart[1]{\par\addvspace{4ex}\@afterindentfalse
  \refstepcounter{sourcepart}\addcontentsline{toc}{chapter}{\Roman{sourcepart}\quad #1}%
  {\parindent\z@\raggedright\interlinepenalty\@M\normalfont
   \Large\bfseries Part \Roman{sourcepart}\par\nobreak\huge\bfseries #1\par}%
  \nobreak\vskip3ex\@afterheading}
\let\OriginalEndPart\@endpart
\def\@endpart{\vskip2em{\large\SourceAuthor\par\SourceDate\par}\OriginalEndPart}
\newcommand\BeginSourcePart[4]{%
  \def\AuditPart{#1}%
  \makeatletter\input{size#2.clo}\makeatother%
  \newgeometry{layout=#3,margin=#4,headheight=14pt}%
  \def\PartPaper{#3}\def\LetterPaper{letterpaper}%
  \ifx\PartPaper\LetterPaper\pdfpagewidth=8.5in\pdfpageheight=11in
  \else\pdfpagewidth=210mm\pdfpageheight=297mm\fi
  \setcounter{section}{0}\setcounter{subsection}{0}\setcounter{subsubsection}{0}%
  \setcounter{equation}{0}\setcounter{figure}{0}\setcounter{table}{0}%
  \setcounter{footnote}{0}\setcounter{sourcepart}{0}%
  \def\theHsection{#1.\thesection}\def\theHsubsection{\theHsection.\arabic{subsection}}%
  \def\theHsubsubsection{\theHsubsection.\arabic{subsubsection}}%
  \def\theHequation{#1.\thesection.\arabic{equation}}%
  \def\theHfigure{#1.\arabic{figure}}\def\theHtable{#1.\arabic{table}}%
  \def\theHsourcepart{#1.\arabic{sourcepart}}%
  \def\theHfootnote{#1.\arabic{footnote}}%
  \setlength{\parskip}{0pt plus 1pt}%
  \pagestyle{plain}\allowdisplaybreaks[0]%
  \setlist{itemsep=\itemsep,topsep=\topsep}%
}
\makeatother
\begin{document}
\pagenumbering{roman}
\begin{titlepage}\centering\vspace*{.2\textheight}
{\Huge\bfseries The long-range Ising CFT:\\[.5em]research notes\par}
\vspace{3em}{\Large Zechuan Zheng\par}\vfill{\large Combined public edition\par}
\end{titlepage}
\setcounter{page}{2}
\setcounter{tocdepth}{1}\tableofcontents\clearpage
\input{preface.tex}
% The opening part (if any) follows the contents and the preface, in the roman front matter.
%%FRONT%%
\restoregeometry
\pagenumbering{arabic}
%%PARTS%%
\hypersetup{pdftitle={The long-range Ising CFT: research notes},pdfauthor={Zechuan Zheng}}
\end{document}
'''

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('public_root',nargs='?',default='~/Documents/LRI_public')
    ap.add_argument('--snapshot-only',action='store_true')
    ap.add_argument('--from-snapshot',action='store_true',help='regenerate from the tracked source snapshots')
    args=ap.parse_args()
    if not args.from_snapshot: snapshot(Path(args.public_root).expanduser().resolve())
    if not args.snapshot_only: generate()

if __name__=='__main__': main()
