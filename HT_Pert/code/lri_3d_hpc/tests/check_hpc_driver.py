#!/usr/bin/env python3
"""Exercise restart, precision, writer and validation controls on tiny jobs.

Use --mpiexec with a site-compatible launcher to include real two-rank CLI
checks.  This test creates only its own temporary fixture directory.  It does
not submit scheduler jobs or modify an existing vertex store.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'code'))
sys.path.insert(0, str(ROOT/'vendor'))
import ht3d_coefficients as driver
from taylor_pipeline import prepare_vertex_inputs, build_particle_images, assemble_vertex_task
from vertex_store import sha256_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--native-cache', type=Path)
    parser.add_argument('--reference', type=Path, default=ROOT/'results'/'reference_coefficients_L14.json')
    parser.add_argument('--mpiexec', type=Path)
    parser.add_argument('--work', type=Path, default=ROOT/'work')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    cases = []

    def run(name, command, ok=True, contains=None, env=None):
        # A cold node compiles the native library on first use; allow for it.
        completed = subprocess.run([str(value) for value in command], text=True,
                                   capture_output=True, timeout=900,
                                   env=None if env is None else {**os.environ, **env})
        if (completed.returncode == 0) != ok:
            raise AssertionError((name, completed.returncode, completed.stdout, completed.stderr))
        if contains is not None and contains not in completed.stdout+completed.stderr:
            raise AssertionError((name, 'missing expected message', contains,
                                  completed.stdout, completed.stderr))
        cases.append({'name': name, 'passed': True, 'expected_success': ok,
                      'returncode': completed.returncode})
        return completed

    def expect_error(name, function):
        try:
            function()
        except (ValueError, ArithmeticError):
            cases.append({'name': name, 'passed': True, 'expected_success': False})
        else:
            raise AssertionError(name)

    with tempfile.TemporaryDirectory(prefix='ht3d-driver-check-', dir=args.work) as temporary:
        work = Path(temporary)
        script = ROOT/'code'/'ht3d_coefficients.py'
        common = [sys.executable, script, 'solve', '--store', args.store,
                  '--cutoff', '4', '--order', '8', '--scheme', 'consistent',
                  '--backend', 'native', '--threads', '1']
        if args.native_cache is not None:
            common += ['--native-cache', args.native_cache]
        output = work/'serial.json'
        solve = common+['--output', output]
        run('fresh_serial_coefficient_job', solve+['--compare-reference', args.reference])
        original = output.read_bytes()
        job = json.loads(original)
        assert job['complete'] and job['request']['mpi_enabled'] is False
        assert job['result']['arithmetic_significand_bits'] == np.finfo(np.longdouble).nmant+1
        assert job['execution']['input_checksums_verified'] is True
        assert np.longdouble(job['execution']['validation']['max_scaled_error']) < np.longdouble('5e-13')
        assert job['execution']['arithmetic']['runtime_probe'] is True
        assert job['execution']['ranks'][0]['native_precision_probe']['passed'] is True
        assert (np.longdouble(job['execution']['residual_gate']['value']) <=
                np.longdouble(job['execution']['residual_gate']['limit']))
        run('identical_completed_resume', solve+['--resume'], contains='already complete')
        assert output.read_bytes() == original
        run('duplicate_output_refused', solve, ok=False, contains='exists')
        run('changed_thread_request_refused', solve+['--threads', '2', '--resume'],
            ok=False, contains='different inputs')
        assert output.read_bytes() == original
        run('working_precision_mismatch_refused', common+['--output', work/'wrong_precision.json',
            '--dtype', 'float64'], ok=False, contains='arithmetic differs')
        run('insufficient_vertex_degree_refused', common+['--output', work/'wrong_order.json',
            '--order', '10'], ok=False, contains='Taylor degree is insufficient')
        claimed = work/'claimed.json'
        with driver.output_claim(claimed):
            run('concurrent_output_writer_refused', common+['--output', claimed],
                ok=False, contains='Another job is writing')
        assert not claimed.exists()
        locks = work/'locks'
        with driver.output_claim(claimed, locks):
            run('concurrent_writer_refused_via_lock_dir', common+['--output', claimed,
                '--lock-dir', locks], ok=False, contains='Another job is writing')
            run('concurrent_writer_refused_via_HT3D_LOCK_DIR', common+['--output', claimed],
                ok=False, contains='Another job is writing', env={'HT3D_LOCK_DIR': str(locks)})
        assert not claimed.exists()
        try:
            driver.publish_new_json(output, {'overwrite': True})
        except FileExistsError:
            cases.append({'name': 'publish_never_overwrites', 'passed': True,
                          'expected_success': False})
        else:
            raise AssertionError('publish_new_json replaced an existing result')
        assert output.read_bytes() == original
        assert not list(work.glob('serial.json.tmp-*'))
        run('residual_gate_refuses_publication', common+['--output', work/'residual.json',
            '--max-residual', '1e-40'], ok=False, contains='residual')
        assert not (work/'residual.json').exists()
        uncovered = work/'uncovered_reference.json'
        uncovered.write_text(json.dumps({'results': [row for row in
            json.loads(args.reference.read_text())['results'] if row['cutoff'] != 4]}))
        run('uncovered_reference_refused_before_solve', common+['--output', work/'uncovered.json',
            '--compare-reference', uncovered], ok=False, contains='exactly one matching')
        assert not (work/'uncovered.json').exists()
        run('srun_step_without_mpi_refused', common+['--output', work/'srun.json'], ok=False,
            contains='add --mpi', env={'SLURM_STEP_ID': '0', 'SLURM_STEP_NUM_TASKS': '2'})
        threaded = work/'threads2.json'
        two_threads = [('2' if i and common[i-1] == '--threads' else value)
                       for i, value in enumerate(common)]
        run('two_thread_native_openmp', two_threads+['--output', threaded,
            '--compare-reference', args.reference])
        threaded_job = json.loads(threaded.read_text())
        assert threaded_job['execution']['ranks'][0]['backend']['backend'] == 'native-openmp'
        assert threaded_job['execution']['ranks'][0]['native_precision_probe']['threads'] == 2
        assert threaded_job['result']['C'] == job['result']['C']

        reference = json.loads(args.reference.read_text())
        matching = [row for row in reference['results'] if row['cutoff'] == 4 and
                    row['scheme'] == 'consistent' and row['order'] == 8]
        assert len(matching) == 1
        bad = copy.deepcopy(matching[0])
        bad['C'][2] = str(np.longdouble(bad['C'][2])+1)
        bad_path = work/'wrong_reference.json'
        bad_path.write_text(json.dumps(bad))
        run('resume_performs_new_reference_comparison', solve+['--resume',
            '--compare-reference', bad_path], ok=False, contains='validation failed')
        assert output.read_bytes() == original
        for tolerance in ('nan', 'inf', '0', '-1'):
            expect_error('invalid_tolerance_'+tolerance,
                         lambda t=tolerance: driver.validate_coefficients(job['result'], args.reference, t))
        bad['C'][2] = 'nan'
        bad_path.write_text(json.dumps(bad))
        expect_error('nonfinite_reference_refused',
                     lambda: driver.validate_coefficients(job['result'], bad_path))
        run('resume_validates_good_reference', solve+['--resume', '--compare-reference', args.reference],
            contains='validation')

        prepared = work/'pipeline'
        prepare_vertex_inputs(prepared, 2, degree=1, dtype=np.longdouble)
        task_script = ROOT/'hpc'/'pipeline_task.py'
        image = [sys.executable, task_script, 'images', '--path', prepared, '--task-id', '1']
        run('new_particle_image_task', image, contains='complete')
        image_manifest = prepared/'images'/'p1'/'manifest.json'
        image_hash = sha256_file(image_manifest)
        run('verified_particle_image_restart', image, contains='verified complete')
        assert sha256_file(image_manifest) == image_hash
        corrupt = work/'pipeline_bad_images'
        shutil.copytree(prepared, corrupt)
        corrupt_manifest = corrupt/'images'/'p1'/'manifest.json'
        record = json.loads(corrupt_manifest.read_text())
        record['images'] = {}
        corrupt_manifest.write_text(json.dumps(record))
        run('incomplete_image_manifest_refused', [sys.executable, task_script, 'images',
            '--path', corrupt, '--task-id', '1'], ok=False)
        record = json.loads(image_manifest.read_text())
        record['inputs_sha256'] = 'wrong input identity'
        corrupt_manifest.write_text(json.dumps(record))
        run('stale_particle_image_identity_refused', [sys.executable, task_script, 'images',
            '--path', corrupt, '--task-id', '1'], ok=False, contains='incompatible inputs')
        corrupt_manifest.write_bytes(image_manifest.read_bytes())
        record = json.loads(image_manifest.read_text())
        array_name = next(iter(record['images'].values()))['data']['file']
        array_path = corrupt/'images'/'p1'/array_name
        damaged = bytearray(array_path.read_bytes())
        damaged[-1] ^= 1
        array_path.write_bytes(damaged)
        run('particle_image_checksum_damage_refused', [sys.executable, task_script, 'images',
            '--path', corrupt, '--task-id', '1'], ok=False, contains='checksum mismatch')
        build_particle_images(prepared, 0)
        build_particle_images(prepared, 2)
        assemble_vertex_task(prepared, 1, 0)
        run('verified_matrix_task_restart', [sys.executable, task_script, 'matrix',
            '--path', prepared, '--task-id', '0'], contains='verified complete')
        run('unused_image_array_slot_is_safe', [sys.executable, task_script, 'images',
            '--path', prepared, '--task-id', '99'], contains='unused array slot')
        run('invalid_matrix_array_slot_refused', [sys.executable, task_script, 'matrix',
            '--path', prepared, '--task-id', '99'], ok=False, contains='out of range')

        for script in sorted((ROOT/'hpc').glob('*.sbatch')) + [ROOT/'hpc'/'submit_pipeline.sh']:
            run('shell_syntax_'+script.name, ['bash', '-n', script])

        mpi_job = None
        if args.mpiexec is not None:
            launcher = [args.mpiexec, '-n', '2']
            mpi_output = work/'mpi.json'
            mpi_command = launcher+common+['--output', mpi_output, '--mpi',
                                           '--compare-reference', args.reference]
            run('two_rank_cli_single_output', mpi_command, contains='complete')
            mpi_job = json.loads(mpi_output.read_text())
            assert mpi_job['request']['mpi_enabled'] is True and mpi_job['request']['ranks'] == 2
            assert len(mpi_job['execution']['ranks']) == 2
            assert mpi_job['result']['optimization']['coefficients_synchronized'] is True
            assert mpi_job['result']['optimization']['fused_hamiltonian_application'] is True
            resumed = run('two_rank_cli_identical_resume', mpi_command+['--resume'],
                          contains='already complete')
            assert resumed.stdout.count('already complete') == 1
            run('one_rank_mpi_is_distinct_from_serial', [args.mpiexec, '-n', '1']+solve+
                ['--mpi', '--resume'], ok=False, contains='different inputs')
            run('multiple_processes_require_mpi_flag', launcher+common+
                ['--output', work/'unmarked_mpi.json'], ok=False, contains='add --mpi')
            assert not (work/'unmarked_mpi.json').exists()

        report = {'passed': True, 'cases': cases, 'store_manifest_sha256':
                  sha256_file(args.store/'manifest.json'),
                  'serial_validation': job['execution']['validation'],
                  'serial_precision_bits': job['result']['arithmetic_significand_bits'],
                  'mpi_validation': mpi_job['execution']['validation'] if mpi_job else None,
                  'mpi_execution': mpi_job['execution'] if mpi_job else None,
                  'scope': 'Tiny CLI, restart, integrity, precision and local real-MPI checks; no scheduler jobs submitted'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passed': True, 'cases': len(cases),
                      'mpi_exercised': args.mpiexec is not None}), flush=True)


if __name__ == '__main__':
    main()
