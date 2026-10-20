"""Numerical equivalence and cache-integrity checks for optimized vertices."""
from pathlib import Path
import importlib.util
import json
import tempfile
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
sys.path.insert(0, str(ROOT / 'vendor'))
from taylor_vertices import build_taylor_vertices
from taylor_pipeline import (prepare_vertex_inputs, build_particle_images,
                             assemble_vertex_task, finalize_vertex_store)
from vertex_store import load_vertex_store, save_vertex_store


def compare(a, b):
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
    worst = 0.0
    for series, old in zip(a[2], b[2]):
        for A, B in zip(series, old):
            assert A.dtype == B.dtype
            error = float(np.max(np.abs((A-B).data), initial=0))
            scale = max(1.0, float(np.max(np.abs(B.data), initial=0)))
            worst = max(worst, error/scale)
    assert worst < 2e-17, worst
    return worst


def rejected(call, phrase=None):
    try:
        call()
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        if phrase:
            assert phrase in str(exc), str(exc)
        return str(exc)
    raise AssertionError('Invalid store was accepted')


def main():
    spec = importlib.util.spec_from_file_location('frozen_taylor', ROOT / 'reference/taylor_vertices.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    # Tiny reference checks need no JIT.  Avoid writing a Numba cache tied to a
    # dynamic import name, which an ordinary standalone import cannot resolve.
    old._pole_pattern = old._pole_pattern.py_func
    report = {'reference_comparisons': [], 'rejections': {}}
    with tempfile.TemporaryDirectory(prefix='ht3d-store-check-') as temp:
        temp = Path(temp)
        for cutoff in (0, 2, 4):
            ref = old.build_taylor_vertices(cutoff, degree=6, return_metadata=True)
            new = build_taylor_vertices(cutoff, degree=6, return_metadata=True)
            report['reference_comparisons'].append(dict(cutoff=cutoff, degree=6,
                                                        max_scaled_error=compare(new, ref)))
        streamed = build_taylor_vertices(4, degree=6, store_path=temp/'stream',
                                          return_metadata=True)
        report['stream_max_scaled_error'] = compare(streamed, new)
        minimal_layouts = build_taylor_vertices(4, degree=6, cache_layouts=False,
                                                return_metadata=True)
        report['layout_cache_max_scaled_error'] = compare(minimal_layouts, new)
        assert isinstance(streamed[2][3][2].data, np.memmap)
        assert not streamed[2][3][2].data.flags.writeable
        report['read_only_mmap'] = True
        report['unique_patterns'] = streamed[3]['unique_sparse_patterns']
        report['rejections']['cutoff'] = rejected(lambda: load_vertex_store(temp/'stream', cutoff=6), 'cutoff')
        report['rejections']['degree'] = rejected(lambda: load_vertex_store(temp/'stream', degree=5), 'degree')
        report['rejections']['overwrite'] = rejected(lambda: save_vertex_store(temp/'stream', *new[:3], new[3]))
        manifest_path = temp/'stream/manifest.json'
        original_manifest = manifest_path.read_text()
        manifest = json.loads(original_manifest)
        manifest['precision']['nmant'] -= 1
        manifest_path.write_text(json.dumps(manifest))
        report['rejections']['precision'] = rejected(lambda: load_vertex_store(temp/'stream'), 'floating-point')
        manifest = json.loads(original_manifest)
        manifest['source_hashes']['taylor_vertices.py'] = '0' * 64
        manifest_path.write_text(json.dumps(manifest))
        report['rejections']['source'] = rejected(lambda: load_vertex_store(temp/'stream'), 'source')
        manifest_path.write_text(original_manifest)
        data_path = temp/'stream/W4_2.data.npy'
        original_data = data_path.read_bytes()
        data_path.write_bytes(original_data[:-1] + bytes([original_data[-1] ^ 1]))
        report['rejections']['checksum'] = rejected(lambda: load_vertex_store(temp/'stream'), 'checksum')
        data_path.write_bytes(original_data)
        (temp/'partial').mkdir()
        report['rejections']['partial'] = rejected(lambda: load_vertex_store(temp/'partial'))

        inputs = prepare_vertex_inputs(temp/'prepared', cutoff=4, degree=3)
        report['rejections']['missing_task'] = rejected(lambda: finalize_vertex_store(temp/'prepared', temp/'incomplete'))
        assert not (temp/'incomplete').exists()
        for particle in inputs['particles']:
            build_particle_images(temp/'prepared', int(particle))
        for k in range(1, 5):
            for r in range(4):
                assemble_vertex_task(temp/'prepared', k, r)
        finalize_vertex_store(temp/'prepared', temp/'assembled')
        assembled = load_vertex_store(temp/'assembled')
        ref = old.build_taylor_vertices(4, degree=3, return_metadata=True)
        report['pipeline_max_scaled_error'] = compare(assembled, ref)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
