#!/usr/bin/env python3
"""Write a site copy of LRI_C6_1D_HPC for a production rerun on another Slurm cluster.

Usage (from GFF/code/LRI_C6_1D_HPC):  python public/slurm/adapt.py SITE_ENV DEST
  SITE_ENV  filled copy of public/slurm/site.env.example
  DEST      new directory, normally <C6_HOME>/code/<revision>; then: ln -sfn <revision> <C6_HOME>/code/current

The shipped cluster/ scripts are the ones that ran on symmetry (Perimeter Institute, Slurm 21.08) and are not
modified. DEST receives Makefile, README.md, src/, tools/, tests/, reference/ and cluster/ unchanged except for
the site lines of cluster/ listed in SUBST below (paths, modules, partitions, memory, account), plus
public/slurm/analyze_stage.sh as cluster/analyze_stage.sh. Every pattern must match the expected number of times,
otherwise nothing is written. Optional drops: gate V3_all_N6_vs_recon_compensated without RECON_FILE, and the
cross-architecture job with its four V11 gates without PART_XARCH. A list of all changes goes to DEST/SITE_CHANGES.txt.
"""
import re, shutil, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]


def read_env(p):
    env = {}
    for ln in Path(p).read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith('#'):
            k, _, v = ln.partition('=')
            env[k.strip()] = v.strip()
    for k in ('C6_HOME', 'PART_MAIN', 'PART_DEBUG', 'PART_SHARED'):
        if not env.get(k) or '<' in env[k]:
            sys.exit(f'{p}: set {k}')
    return env


def subst(e):
    home, main, fb = e['C6_HOME'], e['PART_MAIN'], e.get('PART_FALLBACK') or e['PART_MAIN']
    mods, mem, acct = e.get('MODULES', ''), e.get('MEM') or '180G', e.get('ACCOUNT', '')
    acct = '' if '<' in acct else acct
    mods = '' if '<' in mods else mods
    S = {  # file: [(regex, replacement, expected count)]
        'env.sh': [
            (r'^source /etc/profile\.d/modules\.sh$', '[[ -f /etc/profile.d/modules.sh ]] && source /etc/profile.d/modules.sh', 1),
            (r'^module load .*$', f'module load {mods}' if mods else '# module load: none (public/slurm/adapt.py)', 1),
            (r'^export PATH=\S*slurm\S*:\$PATH$', '# site Slurm PATH line removed (public/slurm/adapt.py)', 1),
            (r'^export C6_HOME=.*$', f'export C6_HOME={home}' + (f'\nexport SBATCH_ACCOUNT={acct}' if acct else ''), 1),
            (r'sinfo -h -p amdq ', f'sinfo -h -p {main} ', 1),
            (r'then echo amdq; else echo amdq,defq; fi', f'then echo {main}; else echo {main if fb == main else main + "," + fb}; fi', 1),
        ],
        'prepare.slurm': [(r'^#SBATCH -p debugq ', f'#SBATCH -p {e["PART_DEBUG"]} ', 1)],
        'batch.slurm': [(r'^#SBATCH -p defq ', f'#SBATCH -p {main} ', 1)],
        'validate.slurm': [(r'^#SBATCH -p defq ', f'#SBATCH -p {main} ', 1)],
        'submit_level.sh': [(r' -p sharedq ', f' -p {e["PART_SHARED"]} ', 1)],
        'validate_all.sh': [
            (r' -p amddebugq,debugq ', f' -p {e["PART_DEBUG"]} ', 1),
            (r' -J c6val_\$part -p amdq ', f' -J c6val_$part -p {main} ', 1),
            (r' -J c6valsum -p sharedq ', f' -J c6valsum -p {e["PART_SHARED"]} ', 1),
        ],
    }
    for f in ('prepare.slurm', 'batch.slurm', 'validate.slurm', 'task.slurm'):
        S.setdefault(f, []).append((r'^(#SBATCH .*-o )\S*/logs/', r'\g<1>' + home + '/logs/', 1))
    for f in ('prepare.slurm', 'batch.slurm', 'validate.slurm', 'task.slurm'):
        S[f].append((r'--mem=180G', f'--mem={mem}', 1))
    if e.get('RECON_FILE'):
        S['validate.slurm'].append((r'^REC=.*$', f'REC={e["RECON_FILE"]}', 1))
    else:
        S['validate.slurm'].append((r'^REC=.*$', 'REC=/dev/null  # recon record not available: gate V3_all_N6_vs_recon_compensated dropped', 1))
        S['validate.slurm'].append((r'^(  python tools/validate.py \$V vector V3_all_N6_vs_recon_compensated .*)$',
                                    r'  : # gate dropped (no recon record; public/slurm/adapt.py): \g<1>', 1))
        S['validate_all.sh'].append((r',V3_all_N6_vs_recon_compensated', '', 1))
    if e.get('PART_XARCH'):
        S['validate_all.sh'].append((r' -J c6val_xarch -p defq ', f' -J c6val_xarch -p {e["PART_XARCH"]} ', 1))
    else:
        S['validate_all.sh'] += [
            (r'^(x=\$\(sbatch --parsable -J c6val_xarch .*)$', r'# cross-architecture job dropped (no PART_XARCH; public/slurm/adapt.py): \g<1>', 1),
            (r'^ids\+=\("\$x"\)$', '# ids+=("$x")  (dropped with the cross-architecture job)', 1),
            (r'^REQ\+=,V11_xarch_light_dbl_N8,V11_xarch_hard_ld_N6,V11_xarch_L5_J16_ld,V11_xarch_cpus_differ$',
             '# V11 gates dropped (no PART_XARCH): V11_xarch_light_dbl_N8,V11_xarch_hard_ld_N6,V11_xarch_L5_J16_ld,V11_xarch_cpus_differ', 1)]
    return S


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    e = read_env(sys.argv[1]); dest = Path(sys.argv[2])
    if dest.exists():
        sys.exit(f'{dest} exists; use a fresh directory (a rerun needs a fresh campaign)')
    new, log = {}, []
    for f, rules in subst(e).items():
        src = PKG / 'cluster' / f; text = src.read_text()
        for rx, rep, want in rules:
            text, n = re.subn(rx, rep, text, flags=re.M)
            if n != want:
                sys.exit(f'cluster/{f}: pattern {rx!r} matched {n} times, expected {want}; nothing written')
            log.append(f'cluster/{f}: {rx}  ->  {rep}')
        new[f] = text
    leftover = [f'{f}: {m}' for f, t in new.items() for m in re.findall(r'.*(?:/mnt/beegfs|<USER>|amdq|defq|sharedq|debugq).*', t)
                if not m.lstrip().startswith('#')]
    dest.mkdir(parents=True)
    for p in ('Makefile', 'README.md', 'src', 'tools', 'tests', 'reference', 'cluster'):
        (shutil.copytree if (PKG / p).is_dir() else shutil.copy2)(PKG / p, dest / p)
    for f, t in new.items():
        (dest / 'cluster' / f).write_text(t)
    shutil.copy2(Path(__file__).with_name('analyze_stage.sh'), dest / 'cluster/analyze_stage.sh')
    (dest / 'GIT_SHA').write_text(e.get('GIT_SHA', 'public') + '\n')
    (dest / 'SITE_CHANGES.txt').write_text('\n'.join(log) + '\n' + ''.join(f'remaining site word (check): {x}\n' for x in leftover))
    print(f'wrote {dest} ({len(log)} substitutions; see SITE_CHANGES.txt)')
    for x in leftover:
        print('check:', x)


if __name__ == '__main__':
    main()
