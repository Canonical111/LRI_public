#!/usr/bin/env python3
"""Tiny input-attachment regression fixtures; no graph packs or native jobs.

Run: python3 -B tests/attach_inputs.py
All fixtures are temporary. The test process selects umask022 while loading
the publishing helper, then restores the caller's mask before returning.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ATTACH = None
MODES = ('symlink', 'hardlink', 'copy')


class AttachTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='c8-attach-checks-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def fixture(self, label):
        source, destination = self.root / label / 'source', self.root / label / 'destination'
        (source / 'packs').mkdir(parents=True)
        destination.mkdir(parents=True)
        checksums = {}
        for sector in ('free', 'power'):
            for loop in range(3, 9):
                name = f'packs/{sector}_L{loop}.pack'
                data = f'synthetic input identity {sector} {loop}\n'.encode()
                (source / name).write_bytes(data)
                checksums[name] = hashlib.sha256(data).hexdigest()
        for directory in (source, destination):
            (directory / 'gamma.txt').write_bytes(b'synthetic nonpack control\n')
        checksums['gamma.txt'] = hashlib.sha256((source / 'gamma.txt').read_bytes()).hexdigest()
        manifest = {'schema': 'c8-d2-hpc-inputs-1', 'order': 8, 'sha256': checksums}
        data = json.dumps(manifest, indent=2).encode() + b'\n'
        for directory in (source, destination):
            (directory / 'manifest.json').write_bytes(data)
        return source, destination, [name for name in checksums if name.startswith('packs/')]

    def assert_no_packs(self, destination):
        self.assertFalse((destination / 'packs').exists(), 'preflight must precede publication')

    def test_modes_and_matching_existing_destinations(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                source, destination, names = self.fixture(mode)
                result = ATTACH.attach(source, destination, mode)
                self.assertEqual(result['created'], names)
                self.assertEqual(result['retained'], [])
                self.assertEqual(result['verified_packs'], 12)
                identities = {}
                for name in names:
                    src, dst = source / name, destination / name
                    self.assertEqual(dst.read_bytes(), src.read_bytes())
                    identities[name] = (dst.lstat().st_ino, dst.lstat().st_mtime_ns)
                    if mode == 'symlink':
                        self.assertTrue(dst.is_symlink())
                        self.assertFalse(Path(os.readlink(dst)).is_absolute())
                        self.assertEqual(dst.resolve(), src.resolve())
                    else:
                        self.assertFalse(dst.is_symlink())
                        self.assertEqual(os.path.samefile(src, dst), mode == 'hardlink')
                    if mode == 'copy':
                        self.assertEqual(stat.S_IMODE(dst.stat().st_mode), 0o644)
                # Existing matching inputs are retained even if the requested
                # attachment mode changes; publication must never replace them.
                retained = ATTACH.attach(source, destination, MODES[(MODES.index(mode) + 1) % 3])
                self.assertEqual(retained['created'], [])
                self.assertEqual(retained['retained'], names)
                for name in names:
                    dst = destination / name
                    self.assertEqual((dst.lstat().st_ino, dst.lstat().st_mtime_ns), identities[name])

    def test_corrupt_last_source_pack_refuses_before_publication(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                source, destination, names = self.fixture(mode)
                (source / names[-1]).write_bytes(b'corrupt last pack')
                with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                    ATTACH.attach(source, destination, mode)
                self.assert_no_packs(destination)

    def test_source_manifest_mismatch_refuses_before_publication(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                source, destination, _ = self.fixture(mode)
                # Even a semantically equivalent manifest with different bytes
                # fails the promised complete-manifest identity check.
                with (source / 'manifest.json').open('ab') as stream:
                    stream.write(b' ')
                with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                    ATTACH.attach(source, destination, mode)
                self.assert_no_packs(destination)

    def test_destination_manifest_replacement_is_not_parsed_unchecked(self):
        source, destination, _ = self.fixture('manifest-race')
        original_digest = ATTACH.digest

        def replace_after_hash(path):
            value = original_digest(path)
            if Path(path) == destination / 'manifest.json':
                with Path(path).open('ab') as stream:
                    stream.write(b' ')
            return value

        with mock.patch.object(ATTACH, 'digest', side_effect=replace_after_hash):
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                ATTACH.attach(source, destination)
        self.assert_no_packs(destination)

    def test_corrupt_existing_destination_is_retained_and_refused(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                source, destination, names = self.fixture(mode)
                target = destination / names[-1]
                target.parent.mkdir()
                target.write_bytes(b'preexisting different data')
                before = target.read_bytes()
                with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                    ATTACH.attach(source, destination, mode)
                self.assertEqual(target.read_bytes(), before)
                self.assertEqual(list(target.parent.iterdir()), [target])

    def test_concurrent_publication_never_clobbers(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                source, destination, names = self.fixture(mode)
                target = destination / names[0]
                function = 'symlink' if mode == 'symlink' else 'link'
                original = getattr(os, function)

                def race(src, dst, *args, **kwargs):
                    if Path(dst) == target:
                        target.write_bytes(b'concurrent owner data')
                    return original(src, dst, *args, **kwargs)

                with mock.patch.object(os, function, side_effect=race):
                    with self.assertRaises(FileExistsError):
                        ATTACH.attach(source, destination, mode)
                self.assertFalse(target.is_symlink())
                self.assertEqual(target.read_bytes(), b'concurrent owner data')
                self.assertEqual(list(target.parent.iterdir()), [target], 'temporary copy must be removed')

    def test_copy_bytes_are_rechecked_before_publication(self):
        source, destination, _ = self.fixture('copy-corruption')

        def corrupt_copy(inp, out, length):
            out.write(b'corrupted during copying')

        with mock.patch.object(ATTACH.shutil, 'copyfileobj', side_effect=corrupt_copy):
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                ATTACH.attach(source, destination, 'copy')
        self.assertEqual(list((destination / 'packs').iterdir()), [])


def main():
    global ATTACH
    previous_umask = os.umask(0o022)
    try:
        sys.path.insert(0, str(ROOT / 'tools'))
        spec = importlib.util.spec_from_file_location('c8_attach_inputs_under_test', ROOT / 'tools/attach_inputs.py')
        ATTACH = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ATTACH)
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(AttachTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        print(json.dumps({'schema': 'c8-attach-inputs-checks-1', 'status': 'passed' if result.wasSuccessful() else 'failed',
                          'test_methods': result.testsRun, 'modes': list(MODES), 'copy_umask': '022'}))
        return 0 if result.wasSuccessful() else 1
    finally:
        os.umask(previous_umask)


if __name__ == '__main__':
    raise SystemExit(main())
