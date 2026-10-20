#!/usr/bin/env python3
"""Read-only check of the SRI note (SRI/note/sri_short_range.tex and its PDF).

1. The PDF is current. At compile time pdfTeX writes the MD5 of the TeX source into the PDF information dictionary
   (key /SRINoteSourceMD5, see the preamble); it must equal the MD5 of the source as it is now. The note is a single
   self-contained source file, so this decides whether the PDF was built from it.
2. No private names. The note's text files (the TeX source, README.md, Makefile, .gitignore) must contain no personal
   machine name, user name, private working-folder name, private absolute path, e-mail address or agent-session id.
   Only the symmetry cluster and SDSC Expanse may be named. The forbidden words are kept as truncated sha256 digests of
   their lower-case spelling, so that this file names none of them; path and id patterns are generic. TeX control
   words (a word preceded by a backslash, such as the command for pi) are not words of the text.
3. Open items. Every \\TODO of the source and every use of the provenance placeholders is listed (INFO); --strict
   turns any of them into a failure.
4. In the published tree, every file listed in MANIFEST.json (written at export) has its recorded sha256.

Usage, from SRI/note: python3 tools/check_note.py [--strict]. Exit status 1 on any failure."""
import hashlib
import json
import re
import sys
import zlib
from pathlib import Path

NOTE = Path(__file__).resolve().parent.parent
TEX = NOTE / 'sri_short_range.tex'
PDF = NOTE / 'sri_short_range.pdf'
TEXT_FILES = ['sri_short_range.tex', 'README.md', 'Makefile', '.gitignore']

# sha256(word.lower())[:16] of forbidden words: personal machine and host names, user names, the authors' private
# folder names and the private source-folder names of the computations behind this note.
FORBIDDEN = {
    '01380046d1d8e216', '0d4c8229f397de69', '0deeb8fa1dbbee4c', '1530ed0592af2f5e',
    '183ffdfaa3f8fcc5', '23c03b75392e7002', '38ca2a4c72623166', '3c28f12d22fd65a0',
    '4579de7b3751896c', '541d478cb9eb946c', '567c9d5b3ae751a6', '6b351867c4cc1f93',
    '726266651692ed17', '834e2202b342eada', '85b42e1702877c85', '915de1a723fa8049',
    'c6dc0176119b992e', 'c96415006f908b67', 'd0d35aa4bd8b2c17', 'd47c40bea34483aa',
    'da61c097d77f9f19', 'e4f5c1fa4207fc12', 'ecca91e0d47427cf', 'fb850c59ec10c0bd',
    'fe1e41d6b8bf8d89',
}
PATTERNS = [
    (r'/Users/|/home/|/mnt/|/media/|/private/|/tmp/|/local1/|~/', 'absolute or home-relative path'),
    (r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', 'session id (UUID)'),
    (r'\bwf_[0-9a-f]{6,}', 'workflow id'),
    (r'originSessionId', 'session id'),
    (r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', 'e-mail address'),
]


def digest(word):
    return hashlib.sha256(word.lower().encode()).hexdigest()[:16]


def md5_in_pdf(data):
    """The /SRINoteSourceMD5 value of the PDF, searched in the plain bytes and in every Flate stream."""
    pat = re.compile(rb'/SRINoteSourceMD5\s*\(([0-9A-Fa-f]{32})\)')
    m = pat.search(data)
    if m:
        return m.group(1).decode().upper()
    for s in re.finditer(rb'stream\r?\n(.*?)\r?\nendstream', data, re.S):
        try:
            m = pat.search(zlib.decompress(s.group(1)))
        except zlib.error:
            continue
        if m:
            return m.group(1).decode().upper()
    return None


def braced(text, start):
    """Text of the brace group that opens at text[start] == '{' (nested braces allowed)."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    return text[start + 1:]


def main():
    strict = '--strict' in sys.argv
    bad, info = [], []

    # 1. PDF current
    src = TEX.read_bytes()
    want = hashlib.md5(src).hexdigest().upper()
    if not PDF.exists():
        bad.append('PDF missing: ' + PDF.name)
    else:
        got = md5_in_pdf(PDF.read_bytes())
        if got is None:
            bad.append('PDF carries no /SRINoteSourceMD5 (not built from this source?)')
        elif got != want:
            bad.append('PDF is not current: built from a source with MD5 %s, source now %s (run make)' % (got, want))
        else:
            print('PDF current: source MD5 %s' % want)

    # 2. private names
    nwords = 0
    for name in TEXT_FILES:
        p = NOTE / name
        if not p.exists():
            continue
        for ln, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            flat = line.replace('\\_', '_')
            for m in re.finditer(r'(\\?)([A-Za-z0-9_]+)', flat):
                if m.group(1):
                    continue                      # TeX control word
                nwords += 1
                w = m.group(2)
                if digest(w) in FORBIDDEN or any(digest(part) in FORBIDDEN for part in w.split('_') if part):
                    bad.append('%s:%d: forbidden private name %r' % (name, ln, w))
            for pat, what in PATTERNS:
                if re.search(pat, flat):
                    bad.append('%s:%d: %s' % (name, ln, what))
    print('private-name scan: %d words in %d files' % (nwords, sum((NOTE / n).exists() for n in TEXT_FILES)))

    # 3. open items
    tex = src.decode('utf-8')
    lines = tex.splitlines()
    skip = {i for i, l in enumerate(lines, 1) if l.lstrip().startswith('%') or l.startswith('\\newcommand{\\TODO}')}
    for m in re.finditer(r'\\TODO\{', tex):
        ln = tex.count('\n', 0, m.start()) + 1
        if ln not in skip:
            info.append('line %d: TODO: %s' % (ln, ' '.join(braced(tex, m.end() - 1).split())[:110]))
    for m in re.finditer(r'\\(ProvCompendium|ProvCone)\b', tex):
        ln = tex.count('\n', 0, m.start()) + 1
        if ln not in skip and not lines[ln - 1].startswith('\\newcommand'):
            info.append('line %d: provenance placeholder \\%s' % (ln, m.group(1)))
    for i in info:
        print('  INFO', i)
    print('open items: %d' % len(info))
    if strict and info:
        bad.append('%d open items (--strict)' % len(info))

    # 4. MANIFEST.json (published tree only)
    man = NOTE / 'MANIFEST.json'
    n = 0
    if man.exists():
        m = json.loads(man.read_text())
        files = m.get('files', m)
        items = files.items() if isinstance(files, dict) else [(e['path'], e['sha256']) for e in files]
        for rel, h in items:
            h = h['sha256'] if isinstance(h, dict) else h
            n += 1
            p = NOTE / rel
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != h:
                bad.append('MANIFEST sha256 mismatch: ' + rel)
        print('MANIFEST.json: %d entries checked' % n)
    else:
        print('MANIFEST.json absent (written at export)')

    for b in bad:
        print('FAIL:', b)
    print('check_note: ' + ('FAIL' if bad else 'PASS'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
