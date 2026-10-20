"""Shared standard-library utilities; all stored paths are repository relative."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
# The first entry is the unnumbered opening part (author request 2026-10-19): the
# account of how the work was organized and checked, moved out of the paper. Its
# source is paper/supplement, not a folder note; it has no part page and no preface excerpt.
PARTS = [
    dict(tag='ai', folder='paper/supplement', note_dir='', main='ai_front', size=11, margin='2cm', paper='letterpaper', front=True),
    dict(tag='gff', folder='GFF', main='long_range_ising_condensed', size=11, margin='23mm', paper='a4paper'),
    dict(tag='sri', folder='SRI', main='sri_short_range', size=11, margin='23mm', paper='a4paper'),
    dict(tag='htp', folder='HT_Pert', main='lri_ht_perturbative', size=11, margin='2.5cm', paper='letterpaper'),
    dict(tag='ht', folder='HT', main='lri_ht_finite_coupling', size=11, margin='2.5cm', paper='letterpaper'),
    dict(tag='nrg', folder='NRG', main='lri_nrg_1d_note', size=10, margin='2.2cm', paper='a4paper'),
    dict(tag='mc', folder='MC', main='lri_mc_note', size=10, margin='2.2cm', paper='a4paper'),
    dict(tag='rs', folder='Resummation', main='lri_resummation', size=11, margin='23mm', paper='a4paper'),
]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def run(args, cwd=ROOT, **kw):
    return subprocess.run(args, cwd=cwd, check=True, text=True, **kw)

def uncomment(s):
    return re.sub(r'(?<!\\)%[^\n]*', '', s)

def group(s, start):
    """Read a balanced braced argument without treating escaped braces as syntax."""
    assert s[start] == '{'
    depth, i = 1, start + 1
    while i < len(s):
        if s[i] == '\\':
            i += 2
            continue
        if s[i] == '{': depth += 1
        if s[i] == '}': depth -= 1
        if depth == 0: return s[start + 1:i], i + 1
        i += 1
    raise ValueError('Unbalanced TeX argument')

def command_arg(s, name):
    m = re.search(r'\\' + re.escape(name) + r'\s*\{', s)
    if not m: return ''
    return group(s, m.end() - 1)[0]

def macro_names(directory):
    names = set()
    for f in sorted(Path(directory).rglob('*.tex')):
        s = uncomment(f.read_text())
        names.update(re.findall(r'\\(?:newcommand|renewcommand|providecommand|DeclareRobustCommand)\*?\s*\{?\\([A-Za-z@]+)', s))
        names.update(re.findall(r'\\(?:def|gdef|edef|xdef)\s*\\([A-Za-z@]+)', s))
        names.update(re.findall(r'\\(?:def|gdef|edef|xdef)\s*\\csname\s*([^#{}\n]+?)\s*\\endcsname', s))
    # These are structural/metadata definitions, not scientific number macros.
    return sorted(names - {'input@path', 'SRINoteSourceMDfive'})

def log_summary(path):
    s = Path(path).read_text(errors='replace')
    return dict(errors=len(re.findall(r'^!', s, re.M)),
                undefined_references=len(re.findall(r'LaTeX Warning: Reference .*? undefined', s)),
                undefined_citations=len(re.findall(r'LaTeX Warning: Citation .*? undefined', s)),
                multiply_defined_labels=len(re.findall(r'LaTeX Warning: Label .*? multiply defined', s)),
                duplicate_destinations=len(re.findall(r'destination with the same identifier', s)),
                overfull_boxes=len(re.findall(r'Overfull \\[hv]box', s)),
                overfull_details=re.findall(r'Overfull \\[hv]box[^\n]*(?:\n[^\n]*)?', s),
                pages=int(re.search(r'Output written on .*?\((\d+) pages?', s).group(1)))

AUDIT_TEX = r'''
\makeatletter
\newwrite\CombinedAuditStream
\immediate\openout\CombinedAuditStream=\jobname.audit
\newcommand{\AuditMacro}[2]{%
  \ifcsname#2\endcsname
    \expandafter\let\expandafter\AuditTemp\csname#2\endcsname
    \immediate\write\CombinedAuditStream{MACRO|#1|#2|\meaning\AuditTemp}%
  \else\immediate\write\CombinedAuditStream{MACRO|#1|#2|UNDEFINED}\fi}
\newcommand{\AuditEvent}[1]{\immediate\write\CombinedAuditStream{EVENT|\AuditPart|#1}}
\newcommand{\AuditPosition}[1]{%
  \pdfsavepos\write\CombinedAuditStream{POS|#1|\thepage|\the\pdflastxpos|\the\pdflastypos}}
\AtBeginEnvironment{figure}{\AuditEvent{figure}}
\AtBeginEnvironment{figure*}{\AuditEvent{figure*}}
\AtBeginEnvironment{sidewaysfigure}{\AuditEvent{sidewaysfigure}}
\AtBeginDocument{%
  \@ifundefined{Gin@setfile}{}{%
    \let\AuditOriginalGin\Gin@setfile
    \def\Gin@setfile#1#2#3{\AuditEvent{graphic|#3}\AuditOriginalGin{#1}{#2}{#3}}}%
  \@ifundefined{tikzpicture}{}{\AtBeginEnvironment{tikzpicture}{\AuditEvent{tikzpicture}}}%
}
\makeatother
'''

def dumps(names, phase):
    return '\n'.join(r'\AuditMacro{' + phase + '}{' + n + '}' for n in names) + '\n'
