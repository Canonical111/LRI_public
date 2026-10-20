#!/usr/bin/env python3
"""Scan the repository for private material before a release.

Reports every text file whose contents or path contain a flagged pattern.
Exemptions: .maintainer/public_allowlist.txt exempts whole files (contents and
name); .maintainer/public_allowlist_names.txt exempts only the file name, so the
contents are still scanned. Exit code 1 if anything is found.
PDF files are scanned too: their raw bytes plus every Flate stream, decompressed.
Other binary files are skipped; files above 50 MB are reported by size only.
"""
import subprocess, fnmatch, os, re, sys, zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERNS = {
    # personal homes only; bare cluster file-system roots (/expanse/lustre, /mnt/beegfs) are public site facts, and a
    # user directory below them is caught by "cluster user name"
    "absolute home path": r"/Users/[A-Za-z]|/home/[a-z]|/media/[a-z]",
    "cluster user name": r"(?<![A-Za-z0-9])zzheng\d*(?![A-Za-z])",
    # a user directory below a data-disk placeholder (the /media rule leaves it): <DATA>/<name>/...
    # a data disk of a personal desktop (scrubbed to <DATA>)
    "data-disk path": r"/media/[A-Za-z0-9_]+/",
    "user name after a placeholder": r"<(?:DATA|SCRATCH|PROJECTS)>/zheng(?![A-Za-z0-9])",
    "workstation user or host": r"(?<![A-Za-z0-9])zephyr(?:-MS-7E25)?(?![A-Za-z0-9])",
    # the authors' other machines (the paper names only symmetry and Expanse); "canonical" and "pi" only in host contexts
    "machine name": r"(?i:(?<![A-Za-z0-9])(?:apao|thanos|canonical111(?!/LRI_public)|zephyr-MS-7E25)(?![A-Za-z0-9]))"
                    r'|"host"\s*:\s*"(?:canonical|pi)"'
                    r"|(?<=\bon )(?:canonical|pi|apao|thanos)\b(?! (?:form|basis|ensemble|class|order|ordering|choice))(?!\s*[\^*/+(]|,\s*\w+\(|,\s*(?:log|sqrt|zeta|e)\b)"
                    r"|\b(?:ssh|host) (?:canonical|pi)\b|\bcanonical(?=,\s*python)"
                    r"|\b(?:canonical|pi) (?:node|host|machine|workstation|server|GPU)s?\b"
                    # runtime and reviewer notes: "(node: pi, 1 core)", "one core (pi)", "(pi, Ubuntu GCC ...)", "pi's 1 TB disk"
                    r"|\bnode:\s*(?:canonical|pi)\b|(?<![A-Za-z0-9_.'\\])\(pi\)(?!\s*[\^*/+\-])"
                    r"|(?<![A-Za-z0-9_.'\\])\((?:canonical|pi),\s*(?=Ubuntu|GCC|RTX|Slurm|[0-9]+\s*cores?\b)"
                    r"|(?<![A-Za-z0-9_.'\\])(?:canonical|pi)'s(?=\s+(?:[0-9.]+\s*[TGM]B|disks?|SSD|NVMe|GPU|node|queue|Slurm)\b)",
    "allocation account": r"yun124(?![0-9])",  # also after a flag letter, e.g. -Ayun124
    # bounded parts (RFC limits 64/63): unbounded `+` is quadratic on long alphanumeric runs such as hex dumps
    "e-mail address": r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63}){0,8}\.(?:com|org|net|edu|gov|io|ai|ca|fr|de|ch|uk|jp|cn|us)\b",
    # cn112 is allowed: the excluded node in the shipped NRG site configuration
    "compute node name": r"(?<![A-Za-z0-9])(?:exp-\d+-\d+|cn(?!112(?![0-9]))\d{3}|mn003)(?![0-9])",
    "rclone remote": r"\bgd[1-4]:|\brclone\b",
    "internal project path": r"Agent_LRI|LRI_Wrap|paper_draft",
    "session id or tool name": r"agent-deck|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    "token-like string": r"(?<![A-Za-z0-9])(ghp_|gho_|sk-|xox[abp]-)[A-Za-z0-9]{10,}",
}
RX = {k: re.compile(v) for k, v in PATTERNS.items()}
# narrow exceptions (author decisions 2026-10-15): the author's published contact address, and resolver URLs
# whose UUID is a document identifier (e.g. resolver.tudelft.nl/uuid:...), not a session id
AUTHOR_MAIL = "zechuan.zheng.phy@gmail.com"
def _mail_ok(hit, before):  # the whole address, or its tail after PDF kerning split it: (zec)29(h)28(uan.zheng.ph)29(y@gmail.com)
    return hit == AUTHOR_MAIL or (AUTHOR_MAIL.endswith(hit) and "uan.zheng.ph" in before)
def _uuid_ok(hit, before):
    return re.search(r"(?:resolver\.tudelft\.nl/uuid:|repository\.tudelft\.nl/record/uuid:)$", before) is not None
EXCEPT = {"e-mail address": _mail_ok, "session id or tool name": _uuid_ok}
# file names only: a personal machine's name as a whole path component or name part (pi_cmp/, *_canonical.json, ...)
NAME_RX = {"machine name (in file name)": re.compile(r"(?:^|[/_.-])(?:pi|canonical|apao|thanos|zephyr)(?=[/_.-]|$)", re.I)}
# raw review transcripts are never published (author decision 2026-10-13); summaries go in REVIEWS.md
FORBIDDEN_NAMES = ["*REVIEW-LOG*", "*review_log*", "*transcript*.jsonl", "*.jsonl.transcript"]

def pdf_text(path):
    """Raw bytes and decompressed Flate streams of a PDF, as latin-1 text."""
    b = open(path, "rb").read()
    parts = [b]
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", b, re.S):
        try:
            parts.append(zlib.decompress(m.group(1)))
        except zlib.error:
            pass
    return "\n".join(x.decode("latin-1") for x in parts)

def allowlist(name="public_allowlist.txt"):
    p = os.path.join(REPO, ".maintainer", name)
    if not os.path.exists(p):
        return []
    return [l.split("\t")[0].strip() for l in open(p) if l.strip() and not l.startswith("#")]

def matcher(patterns):
    """Fast membership test: exact paths in a set, globs precompiled (fnmatch's cache holds only 256 patterns)."""
    exact = {x for x in patterns if not any(c in x for c in "*?[")}
    globs = [re.compile(fnmatch.translate(x)) for x in patterns if x not in exact]
    return lambda rel: rel in exact or any(g.match(rel) for g in globs)

def main():
    allowed = matcher(allowlist())                                  # whole file exempt
    name_ok = matcher(allowlist("public_allowlist_names.txt"))      # only the file name exempt
    hits, big = {}, []
    try:  # only files git would publish: tracked, or untracked and not ignored
        out = subprocess.run(["git", "-C", REPO, "ls-files", "-co", "--exclude-standard", "-z"], capture_output=True, check=True).stdout
        publish = set(out.decode().split("\0")) - {""}
    except (OSError, subprocess.CalledProcessError):
        publish = None
    for d, dirs, files in os.walk(REPO):
        dirs[:] = [x for x in dirs if x not in (".git", ".maintainer")]
        for f in files:
            p = os.path.join(d, f); rel = os.path.relpath(p, REPO)
            if publish is not None and rel not in publish:
                continue
            if allowed(rel) or rel == "tools/check_public.py":
                continue
            if any(fnmatch.fnmatch(f, g) for g in FORBIDDEN_NAMES):
                hits.setdefault("raw review log (never published)", []).append((rel, 1))
            for k, rx in RX.items():  # private strings in the path itself
                if rx.search(rel) and not name_ok(rel):
                    hits.setdefault(f"{k} (in file name)", []).append((rel, 1))
            for k, rx in NAME_RX.items():
                if rx.search(rel) and not name_ok(rel):
                    hits.setdefault(k, []).append((rel, 1))
            sz = os.path.getsize(p)
            if sz > 50e6:
                big.append((rel, sz)); continue
            try:
                txt = pdf_text(p) if f.lower().endswith(".pdf") else open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            for k, rx in RX.items():
                n = 0
                for m in rx.finditer(txt):
                    ok = EXCEPT.get(k)
                    if ok and ok(m.group(0), txt[max(0, m.start() - 60):m.start()]):
                        continue
                    n += 1
                if n:
                    hits.setdefault(k, []).append((rel, n))
    for k, lst in hits.items():
        print(f"== {k}: {len(lst)} files")
        for rel, n in sorted(lst)[:20]:
            print(f"   {n:6d}  {rel}")
        if len(lst) > 20:
            print(f"   ... {len(lst)-20} more")
    for rel, sz in big:
        print(f"== large file: {rel} ({sz/1e6:.0f} MB)")
    sys.exit(1 if hits or big else 0)

if __name__ == "__main__":
    main()
