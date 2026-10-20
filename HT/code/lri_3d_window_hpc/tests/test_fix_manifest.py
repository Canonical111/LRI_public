"""The site patch must verify changes, not skip stale hashes indiscriminately."""
import hashlib
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fix_manifest',ROOT/'scripts/rebuild_fix_manifest.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def fixture(tmp):
    (tmp/'provenance').mkdir()
    (tmp/'old.py').write_text('original unchanged')
    (tmp/'changed.py').write_text('reviewed change')
    (tmp/'new.py').write_text('new checked file')
    (tmp/'cluster/expanse').mkdir(parents=True)
    (tmp/'cluster/expanse/unseen.py').write_text('preserve this')
    old=f'{m.digest(tmp/"old.py")}  old.py\n'+f'{"0"*64}  changed.py\n'
    (tmp/m.OLD_MANIFEST).write_text(old)
    payload=''.join(f'{m.digest(tmp/n)}  {n}\n' for n in ['changed.py','new.py'])
    (tmp/m.PAYLOAD_MANIFEST).write_text(payload)
    return hashlib.sha256(old.encode()).hexdigest()


def test_rebuild_checks_all_files_preserves_site(tmp_path):
    pin=fixture(tmp_path)
    assert m.rebuild(tmp_path,expected_original_sha=pin)==5
    data=(tmp_path/'MANIFEST.sha256').read_bytes()
    assert (tmp_path/'cluster/expanse/unseen.py').read_text()=='preserve this'
    assert 'unseen.py' not in data.decode()
    m.rebuild(tmp_path,expected_original_sha=pin)
    assert (tmp_path/'MANIFEST.sha256').read_bytes()==data


def test_rebuild_rejects_unlisted_edit_before_writing(tmp_path):
    pin=fixture(tmp_path)
    (tmp_path/'old.py').write_text('not reviewed')
    with pytest.raises(ValueError,match='Hash mismatch'):
        m.rebuild(tmp_path,expected_original_sha=pin)
    assert not (tmp_path/'MANIFEST.sha256').exists()


def test_rebuild_rejects_modified_patched_file(tmp_path):
    pin=fixture(tmp_path)
    (tmp_path/'changed.py').write_text('extra change')
    with pytest.raises(ValueError,match='Hash mismatch'):
        m.rebuild(tmp_path,expected_original_sha=pin)


def test_rebuild_rejects_escape_symlink_duplicate(tmp_path):
    pin=fixture(tmp_path)
    for name in ['../escape.py','/absolute.py','x/../escape.py','x\\escape.py']:
        with pytest.raises(ValueError):m.parse_manifest(f'{"0"*64}  {name}\n'.encode())
    with pytest.raises(ValueError):m.parse_manifest(f'{"0"*64}  a\n{"0"*64}  a\n'.encode())
    (tmp_path/'new.py').unlink()
    (tmp_path/'new.py').symlink_to(tmp_path/'old.py')
    with pytest.raises(ValueError,match='Symlink'):
        m.rebuild(tmp_path,expected_original_sha=pin)
