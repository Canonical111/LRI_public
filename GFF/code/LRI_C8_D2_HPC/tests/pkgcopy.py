"""An isolated copy of the package for the orchestration tests (tests/unit_orchestration.py) and the vendor-rule spy of
tests/check_vendored.py: tools/, tests/, slurm/, src/, vendor/, inputs/ and gen/ copied, the input packs and the archived
records the seed registry reads hard-linked (never modified in place), the pinned C7(2) calibration and kernel copies,
and the fake native worker (tests/fake_worker.py) as bin/c8d2_decimal and bin/c8d2_gmp. With real_exe=True the built
bin/c8d2_gmp and its build record replace the fake gmp worker (the Linux A-ORC-13 path). The package's multi-GB L8 packs
(inputs/packs/*_L8.pack, built by `make inputs-l8`, not in git) are never copied: the tests plan on the fixture
tests/fixtures/inputs_mini, and the zero-task test needs a package without them."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAKE_SHEBANG = f'#!{sys.executable} -S\n'  # -S: the fake worker never imports site (so no spy or sitecustomize reaches it)
L8_PACKS = ('free_L8.pack', 'power_L8.pack')
REFERENCE_FILES = ('reference/power_mass/verification/production_manifest.json', 'reference/LRI_C7_d2_progress/code/prepare.py',
                   'reference/SHA256SUMS', 'reference/SHA256SUMS_c8', 'reference/c7d2_hpc_a55958f/tools/calibration.json',
                   'reference/c7d2_hpc_a55958f/src/kernel.hpp', 'reference/c7d2_hpc_a55958f/src/c7d2_integrate.cpp',
                   'reference/LRI_C7_d2_progress/inputs/L2/G0.txt')


def link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def make_package(td: Path, real_exe: bool = False, name: str = 'pkg') -> Path:
    pkg = td / name
    for sub in ('tools', 'tests', 'slurm', 'src', 'vendor', 'inputs', 'gen'):
        for f in (ROOT / sub).rglob('*'):
            if not f.is_file() or f.name == '.DS_Store' or '__pycache__' in f.parts:
                continue
            if f.parent == ROOT / 'inputs/packs' and f.name in L8_PACKS:
                continue
            dst = pkg / f.relative_to(ROOT)
            if f.suffix == '.pack':
                link_or_copy(f, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
    for sub in ('reference/LRI_C7_d2_progress/records', 'reference/power_mass/records'):
        for f in (ROOT / sub).rglob('*'):
            if f.is_file() and f.name != '.DS_Store':
                link_or_copy(f, pkg / f.relative_to(ROOT))
    for rel in REFERENCE_FILES:
        (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, pkg / rel)
    shutil.copy2(ROOT / 'Makefile', pkg / 'Makefile')
    (pkg / 'bin').mkdir()
    for b in ('c8d2_decimal', 'c8d2_gmp'):
        fake = pkg / 'bin' / b
        fake.write_text(FAKE_SHEBANG + (ROOT / 'tests/fake_worker.py').read_text())
        fake.chmod(0o755)
    if real_exe:
        for f in ('c8d2_gmp', 'c8d2_gmp.build.json'):
            if (ROOT / 'bin' / f).exists():
                (pkg / 'bin' / f).unlink(missing_ok=True)
                shutil.copy2(ROOT / 'bin' / f, pkg / 'bin' / f)
    return pkg
