"""Restartable Taylor-vertex construction with independent cluster tasks.

Stages are deliberately separate: one graph/projector preparation, independent
particle-image jobs, independent (vertex power, Taylor order) contractions, and
an inexpensive store assembly.  No MPI package is required for these tasks;
Slurm arrays or an MPI task distributor can call the same Python functions.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import time

import numpy as np
from scipy.sparse import csr_matrix, csc_matrix, coo_matrix

from taylor_vertices import amplitude_taylor, canonical, _pole_pattern, _sum_products
from vertex_store import (VertexStoreWriter, atomic_json, load_array, load_sparse,
                          precision_fingerprint, save_array, save_sparse,
                          sha256_file, source_fingerprints)


INPUT_FORMAT = 'ht3d-taylor-inputs-v1'
IMAGE_FORMAT = 'ht3d-taylor-images-v1'
TASK_FORMAT = 'ht3d-taylor-matrix-task-v1'


def _stage_directory(target):
    target = Path(target).resolve()
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target, Path(tempfile.mkdtemp(prefix=target.name + '.partial-',
                                        dir=target.parent))


def _publish(stage, target, manifest):
    atomic_json(stage / 'manifest.json', manifest)
    if target.exists():
        raise FileExistsError(target)
    os.rename(stage, target)


def _read_inputs(path):
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text())
    if manifest.get('format') != INPUT_FORMAT:
        raise ValueError('Not a prepared Taylor-vertex input directory')
    dtype = np.dtype(manifest['precision']['dtype'])
    if precision_fingerprint(dtype) != manifest['precision']:
        raise ValueError('Prepared inputs have an incompatible floating-point ABI')
    if manifest['source_hashes'] != source_fingerprints():
        raise ValueError('Prepared inputs have stale source hashes')
    return manifest


def prepare_vertex_inputs(path, cutoff, degree=6, dtype=np.longdouble, *,
                          max_states=2_000_000, max_bytes=2 * 1024**3):
    """Build and persist the unchanged Fock graph's projected input arrays.

    This stage retains the exact supplied species-block SO(3) SVD policy.  It is
    still a single-process graph/projector setup and may set the maximum feasible
    cutoff.  Its resident graph is released before subsequent distributed tasks.
    """
    from ht3d.basis import SphereBathBasis
    if int(cutoff) != cutoff or cutoff < 0 or int(degree) != degree or degree < 0:
        raise ValueError('Require nonnegative integer cutoff and degree')
    cutoff, degree = int(cutoff), int(degree)
    target, stage = _stage_directory(path)
    started = time.perf_counter()
    try:
        basis = SphereBathBasis.build(cutoff, max_states=max_states, max_bytes=max_bytes)
        basis_seconds = time.perf_counter() - started
        begin = time.perf_counter()
        S, N, P, keep, diagnostics = basis.highest_weight(0, 0)
        projector_seconds = time.perf_counter() - begin
        begin = time.perf_counter()
        selected = np.flatnonzero(basis.M == 0)
        lookup = np.full(len(basis.N), -1, np.int64)
        lookup[selected] = np.arange(len(selected))
        labels = np.asarray(basis.labels, dtype=np.int64).reshape(-1, 3)
        coefficients = np.empty((degree + 1, len(labels)), dtype=dtype)
        cache = {}
        for mode, (n, ell, m) in enumerate(labels):
            key = (int(n), int(ell))
            if key not in cache:
                cache[key] = amplitude_taylor(n, ell, degree, dtype)
            coefficients[:, mode] = cache[key] * np.sqrt(np.dtype(dtype).type(2 * ell + 1))
        ptr, ix, modes, sqocc = _pole_pattern(selected, lookup, basis.ptr, basis.parents,
                                              basis.modes, basis.sqocc, labels[:, 2])
        occupations = np.rint(sqocc * sqocc).astype(np.int64)
        precise_sqocc = np.sqrt(occupations.astype(dtype))
        shape = (len(selected), len(selected))
        annihilator = []
        for r in range(degree + 1):
            A = canonical(csr_matrix((precise_sqocc * coefficients[r, modes], ix, ptr),
                                      shape=shape).T)
            annihilator.append(save_sparse(stage, A, f'annihilator-{r}', 'csr'))
        smallS = S[selected].astype(dtype).tocsc()
        particles = {}
        for p in sorted(np.unique(P)):
            rows = np.flatnonzero(P == p)
            block = smallS[:, rows]
            particles[str(int(p))] = dict(
                rows=save_array(stage / f'particle-{p}-rows.npy', rows),
                block=save_sparse(stage, block, f'particle-{p}-block', 'csc'))
        metadata = dict(cutoff=cutoff, degree=degree,
                        field_dimension='(3-epsilon)/4',
                        series_convention='ordinary Taylor coefficients, derivative/factorial',
                        dtype=np.dtype(dtype).name, projector_source_dtype='float64',
                        full_bath_states=len(basis.N), magnetic_zero_states=len(selected),
                        scalar_bath_states=len(N), bath_graph_array_bytes=basis.nbytes,
                        basis_seconds=basis_seconds, projector_seconds=projector_seconds,
                        input_array_seconds=time.perf_counter()-begin,
                        projector_diagnostics=diagnostics)
        manifest = dict(format=INPUT_FORMAT, cutoff=cutoff, degree=degree,
                        precision=precision_fingerprint(dtype), source_hashes=source_fingerprints(),
                        N=save_array(stage / 'N.npy', N), P=save_array(stage / 'P.npy', P),
                        annihilator=annihilator, particles=particles, metadata=metadata,
                        seconds=time.perf_counter()-started)
        _publish(stage, target, manifest)
        return manifest
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def build_particle_images(path, particle, output_path=None, *, verify=True):
    """One independent particle-number task; writes complete Taylor images.

    Only adjacent annihilation layers are held in memory, rather than all four
    layers for every particle sector.  Existing output is refused; complete
    tasks can be identified by their manifest and retained after a restart.
    """
    path = Path(path)
    inputs = _read_inputs(path)
    particle = int(particle)
    if str(particle) not in inputs['particles']:
        raise ValueError('Particle sector absent from prepared basis')
    target, stage = _stage_directory(output_path or path / 'images' / f'p{particle}')
    started = time.perf_counter()
    counts = {'zero_sparse_products_skipped': 0, 'sparse_products_executed': 0}
    try:
        dtype = np.dtype(inputs['precision']['dtype'])
        degree = inputs['degree']
        A = [load_sparse(path, r, verify=verify) for r in inputs['annihilator']]
        block = load_sparse(path, inputs['particles'][str(particle)]['block'], verify=verify)
        zero = csc_matrix(block.shape, dtype=dtype)
        # Keep the forward recurrence in CSR; save CSC layouts for the later
        # transposed left factors.  This avoids a conversion for every Taylor
        # product while retaining only adjacent annihilation layers in RAM.
        previous = [block.tocsr()] + [zero] * degree
        records = {}
        for k in range(1, min(4, particle) + 1):
            current = []
            for r in range(degree + 1):
                value = canonical(_sum_products(A, previous, r, counts=counts))
                current.append(value)
                records[f'{k}:{r}'] = save_sparse(stage, value, f'image-{k}-{r}', 'csc')
            previous = current
        manifest = dict(format=IMAGE_FORMAT, particle=particle,
                        inputs_sha256=sha256_file(path / 'manifest.json'),
                        degree=degree, precision=inputs['precision'], images=records,
                        shape=list(block.shape), seconds=time.perf_counter()-started,
                        **counts)
        _publish(stage, target, manifest)
        return manifest
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _load_images(path, inputs, particle, degree, verify, input_hash, cache_layouts):
    folder = path / 'images' / f'p{particle}'
    manifest = json.loads((folder / 'manifest.json').read_text())
    if (manifest.get('format') != IMAGE_FORMAT or
            manifest.get('inputs_sha256') != input_hash or
            manifest.get('particle') != particle or
            manifest.get('degree') != inputs['degree'] or
            manifest.get('precision') != inputs['precision']):
        raise ValueError(f'Invalid or stale particle-image task: {folder}')
    block = load_sparse(path, inputs['particles'][str(particle)]['block'], verify=verify)
    zero = csc_matrix(block.shape, dtype=np.dtype(inputs['precision']['dtype']))
    images = [[block] + [zero] * degree]
    for k in range(1, 5):
        images.append([load_sparse(folder, manifest['images'][f'{k}:{r}'], verify=verify)
                       for r in range(degree + 1)] if k <= particle
                      else [zero] * (degree + 1))
    right = [[W.tocsr() if W.nnz else W for W in layer] for layer in images[:3]] \
        if cache_layouts else images
    return images, right


def assemble_vertex_task(path, k, r, output_path=None, *, verify=True, cache_layouts=True):
    """One independent (k,r) task, preserving contraction and averaging order.

    ``k`` is the normal-ordered bath-field power 1..4; ``r`` is the ordinary
    epsilon Taylor degree.  Particle images must already be complete.  Only
    this one output matrix's coordinates are accumulated in memory.
    Disable ``cache_layouts`` to minimize the extra low-layer CSR footprint.
    """
    path = Path(path)
    inputs = _read_inputs(path)
    k, r = int(k), int(r)
    if not (1 <= k <= 4 and 0 <= r <= inputs['degree']):
        raise ValueError('Invalid vertex power or Taylor degree')
    target, stage = _stage_directory(output_path or path / 'tasks' / f'k{k}-r{r}')
    started = time.perf_counter()
    counts = {'zero_sparse_products_skipped': 0, 'sparse_products_executed': 0}
    try:
        dtype = np.dtype(inputs['precision']['dtype'])
        N = load_array(path, inputs['N'], verify=verify)
        rows = {int(p): load_array(path, item['rows'], verify=verify)
                for p, item in inputs['particles'].items()}
        image_cache = {}
        input_hash = sha256_file(path / 'manifest.json')
        def images(p):
            if p not in image_cache:
                image_cache[p] = _load_images(path, inputs, p, r, verify, input_hash,
                                               cache_layouts)
            return image_cache[p]
        rr, cc, dd = [], [], []
        ar = ar_right = al = al_right = None
        for pb in sorted(rows):
            for old in list(image_cache):
                if old < pb:
                    del image_cache[old]
            ar, ar_right = images(pb)
            for diff in range(k + 1):
                pa = pb + diff
                if pa not in rows or (diff + k) % 2:
                    continue
                al, al_right = images(pa)
                j = (diff + k) // 2
                value = canonical(_sum_products(al[j], ar_right[k-j], r,
                                                 transpose_left=True, counts=counts)
                                    * math.comb(k, j)).tocoo()
                if not value.nnz:
                    continue
                row, col = rows[pa][value.row], rows[pb][value.col]
                rr.append(row); cc.append(col); dd.append(value.data)
                if pa != pb:
                    rr.append(col); cc.append(row); dd.append(value.data)
        image_cache.clear()
        del ar, ar_right, al, al_right
        if rr:
            W = canonical(coo_matrix((np.concatenate(dd), (np.concatenate(rr), np.concatenate(cc))),
                                       shape=(len(N), len(N))))
            W = canonical((W + W.T) * dtype.type(.5))
        else:
            W = csr_matrix((len(N), len(N)), dtype=dtype)
        manifest = dict(format=TASK_FORMAT, k=k, r=r, inputs_sha256=input_hash,
                        precision=inputs['precision'], matrix=save_sparse(stage, W),
                        nnz=int(W.nnz), array_bytes=W.data.nbytes + W.indices.nbytes + W.indptr.nbytes,
                        seconds=time.perf_counter()-started, cache_layouts=bool(cache_layouts),
                        **counts)
        _publish(stage, target, manifest)
        return manifest
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def finalize_vertex_store(path, output_path, *, verify=True):
    """Validate and combine completed independent matrix tasks into one store."""
    path = Path(path)
    inputs = _read_inputs(path)
    input_hash = sha256_file(path / 'manifest.json')
    N = load_array(path, inputs['N'], verify=verify)
    P = load_array(path, inputs['P'], verify=verify)
    dtype = np.dtype(inputs['precision']['dtype'])
    metadata = dict(inputs['metadata'])
    metadata['construction'] = 'independent particle-image and (k,r) matrix tasks'
    metadata['vertex_nnz'] = [[] for k in range(4)]
    metadata['vertex_array_bytes'] = 0
    metadata['matrix_task_seconds_sum'] = 0.0
    with VertexStoreWriter(output_path, N, P, inputs['cutoff'], inputs['degree'], dtype) as out:
        for k in range(1, 5):
            for r in range(inputs['degree'] + 1):
                folder = path / 'tasks' / f'k{k}-r{r}'
                task = json.loads((folder / 'manifest.json').read_text())
                if (task.get('format') != TASK_FORMAT or task.get('inputs_sha256') != input_hash or
                        task.get('k') != k or task.get('r') != r or
                        task.get('precision') != inputs['precision']):
                    raise ValueError(f'Invalid or stale matrix task: {folder}')
                W = load_sparse(folder, task['matrix'], verify=verify)
                out.add(k, r, W)
                metadata['vertex_nnz'][k-1].append(int(W.nnz))
                metadata['vertex_array_bytes'] += int(task['array_bytes'])
                metadata['matrix_task_seconds_sum'] += task['seconds']
        out.finish(metadata)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--path', required=True)
    p.add_argument('--cutoff', type=int, required=True)
    p.add_argument('--degree', type=int, default=6)
    p.add_argument('--dtype', choices=['longdouble', 'float64'], default='longdouble')
    p.add_argument('--max-states', type=int, default=2_000_000)
    p.add_argument('--max-bytes', type=int, default=2 * 1024**3)
    p = sub.add_parser('images')
    p.add_argument('--path', required=True)
    p.add_argument('--particle', type=int, required=True)
    p.add_argument('--trust-staged-arrays', action='store_true')
    p = sub.add_parser('matrix')
    p.add_argument('--path', required=True)
    p.add_argument('--k', type=int, required=True)
    p.add_argument('--r', type=int, required=True)
    p.add_argument('--trust-staged-arrays', action='store_true')
    p.add_argument('--no-layout-cache', action='store_true')
    p = sub.add_parser('finalize')
    p.add_argument('--path', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--trust-staged-arrays', action='store_true')
    p = sub.add_parser('tasks')
    p.add_argument('--path', required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare_vertex_inputs(args.path, args.cutoff, args.degree,
                                       np.longdouble if args.dtype == 'longdouble' else np.float64,
                                       max_states=args.max_states, max_bytes=args.max_bytes)
    elif args.command == 'images':
        result = build_particle_images(args.path, args.particle,
                                        verify=not args.trust_staged_arrays)
    elif args.command == 'matrix':
        result = assemble_vertex_task(args.path, args.k, args.r,
                                       verify=not args.trust_staged_arrays,
                                       cache_layouts=not args.no_layout_cache)
    elif args.command == 'finalize':
        result = finalize_vertex_store(args.path, args.output,
                                        verify=not args.trust_staged_arrays)
    else:
        inputs = _read_inputs(args.path)
        result = dict(particles=sorted(int(p) for p in inputs['particles']),
                      matrices=[dict(task=(k-1)*(inputs['degree']+1)+r, k=k, r=r)
                                for k in range(1, 5) for r in range(inputs['degree']+1)])
    print(json.dumps(result, indent=2, default=lambda a: a.item()))


if __name__ == '__main__':
    main()
