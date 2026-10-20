"""Run or verify one restartable vertex task from a scheduler array."""
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'code'), str(ROOT/'vendor')]
from taylor_pipeline import (_read_inputs, build_particle_images,
                             assemble_vertex_task, IMAGE_FORMAT, TASK_FORMAT)
from vertex_store import load_sparse, sha256_file


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('images', 'matrix'))
    p.add_argument('--path', type=Path, required=True)
    p.add_argument('--task-id', type=int, default=int(os.environ.get('SLURM_ARRAY_TASK_ID', '0')))
    args = p.parse_args()
    inputs = _read_inputs(args.path)
    identity = sha256_file(args.path/'manifest.json')
    if args.task_id < 0:
        raise ValueError('task-id must be nonnegative')
    if args.stage == 'images':
        particles = sorted(map(int, inputs['particles']))
        if args.task_id >= len(particles):
            print(json.dumps(dict(status='unused array slot', task=args.task_id)))
            return
        particle = particles[args.task_id]
        folder = args.path/'images'/f'p{particle}'
        expected = dict(format=IMAGE_FORMAT, particle=particle,
                        inputs_sha256=identity, degree=inputs['degree'],
                        precision=inputs['precision'])
        run = lambda: build_particle_images(args.path, particle)
    else:
        degree_count = inputs['degree']+1
        if args.task_id >= 4*degree_count:
            raise ValueError('Matrix task-id is out of range')
        k, r = args.task_id//degree_count+1, args.task_id % degree_count
        folder = args.path/'tasks'/f'k{k}-r{r}'
        expected = dict(format=TASK_FORMAT, k=k, r=r, inputs_sha256=identity,
                        precision=inputs['precision'])
        run = lambda: assemble_vertex_task(args.path, k, r)
    if folder.exists():
        record = json.loads((folder/'manifest.json').read_text())
        if any(record.get(key) != value for key, value in expected.items()):
            raise ValueError(f'Existing task has incompatible inputs: {folder}')
        if args.stage == 'images':
            keys = {f'{k}:{r}' for k in range(1, min(4, particle)+1)
                    for r in range(inputs['degree']+1)}
            if set(record.get('images', {})) != keys:
                raise ValueError(f'Existing particle task has incomplete image layers: {folder}')
        arrays = (record['images'].values() if args.stage == 'images' else [record['matrix']])
        for array in arrays:
            load_sparse(folder, array, verify=True)
        print(json.dumps(dict(status='verified complete', task=str(folder))))
    else:
        result = run()
        print(json.dumps(dict(status='complete', task=str(folder), metadata=result), default=str))


if __name__ == '__main__':
    main()
