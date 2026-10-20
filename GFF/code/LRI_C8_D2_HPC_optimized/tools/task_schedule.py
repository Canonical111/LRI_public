"""Scheduling only: graph locality and frozen variable-size checkpoint blocks.

Task UID, replicate, graph, point interval, normalization and cost are never
changed here. Legacy plans without checkpoint_blocks retain their original
fixed-size layout. Graph and task limits are hard bounds. A measured-time
target is enforced between existing native tasks; one indivisible task may
exceed it and is explicitly reported.
"""
from __future__ import annotations

import heapq
import itertools
import math

LAYOUT = 'c8-d2-explicit-blocks-1'


def has_explicit_blocks(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='checkpoint_blocks'").fetchone() is not None


def rows_for(db, shard):
    return db.execute('SELECT uid,rep,gi,lo,hi,total FROM tasks WHERE shard=? ORDER BY pos', (shard,))


def block_count(db, shard, max_tasks):
    if has_explicit_blocks(db):
        return db.execute('SELECT COUNT(*) FROM checkpoint_blocks WHERE shard=?', (shard,)).fetchone()[0]
    count = db.execute('SELECT COUNT(*) FROM tasks WHERE shard=?', (shard,)).fetchone()[0]
    return (count + max_tasks - 1) // max_tasks


def task_blocks(db, shard, max_tasks, with_cost=False):
    """Yield exact frozen blocks, accepting both legacy and explicit layouts."""
    if not 1 <= max_tasks <= 100000:
        raise ValueError('Invalid checkpoint task limit')
    columns = 'uid,rep,gi,lo,hi,total' + (',cost' if with_cost else '')
    if not has_explicit_blocks(db):
        cursor = db.execute(f'SELECT {columns} FROM tasks WHERE shard=? ORDER BY pos', (shard,))
        while block := list(itertools.islice(cursor, max_tasks)):
            yield block
        return
    # A streamed merge of the descriptor and task tables is O(max_tasks) in
    # Python memory, even when one shard has millions of checkpoint blocks.
    descriptors = db.execute('SELECT part,first_pos,task_count FROM checkpoint_blocks WHERE shard=? ORDER BY part', (shard,))
    cursor = db.execute(f'SELECT {columns},pos FROM tasks WHERE shard=? ORDER BY pos', (shard,))
    expected_pos = 0
    for expected_part, (part, first_pos, count) in enumerate(descriptors):
        if part != expected_part or first_pos != expected_pos or not 1 <= count <= max_tasks:
            raise ValueError('Invalid frozen checkpoint block layout')
        rows = list(itertools.islice(cursor, count))
        if len(rows) != count or any(row[-1] != first_pos + offset for offset, row in enumerate(rows)):
            raise ValueError('Task positions disagree with the frozen checkpoint layout')
        expected_pos += count
        yield [row[:-1] for row in rows]
    if next(cursor, None) is not None:
        raise ValueError('Explicit checkpoint blocks do not cover every shard task')


def assign_graph_bundles(db, requested_shards):
    """Whole-graph LPT assignment; only placement columns shard/pos change.

    Sort G graph costs, rather than R*G native-task costs. All assignment updates
    use bounded executemany batches. No graph's full task list is materialized.
    """
    if requested_shards < 1:
        raise ValueError('Positive shard count required')
    bundles = list(db.execute('SELECT gi,SUM(cost),COUNT(*) FROM tasks GROUP BY gi ORDER BY SUM(cost) DESC,gi'))
    nshards = min(requested_shards, len(bundles))
    if nshards < 1:
        raise ValueError('Cannot schedule an empty task group')
    heap = [(0.0, 0, shard) for shard in range(nshards)]
    heapq.heapify(heap)
    positions = [0] * nshards
    shard_costs = [0.0] * nshards
    assignment = {}
    for graph, cost, count in bundles:
        if not math.isfinite(cost) or cost < 0 or count < 1:
            raise ValueError('Invalid graph bundle cost/count')
        old_cost, old_count, shard = heapq.heappop(heap)
        assignment[graph] = [shard, positions[shard], count]
        positions[shard] += count
        shard_costs[shard] = old_cost + cost
        heapq.heappush(heap, (old_cost + cost, old_count + count, shard))
    writer = db.cursor()
    with db:
        batch = []
        for graph, uid in db.execute('SELECT gi,uid FROM tasks ORDER BY gi,rep,lo,uid'):
            state = assignment[graph]
            batch.append((state[0], state[1], uid))
            state[1] += 1
            state[2] -= 1
            if len(batch) >= 10000:
                writer.executemany('UPDATE tasks SET shard=?,pos=? WHERE uid=?', batch)
                batch.clear()
        if batch:
            writer.executemany('UPDATE tasks SET shard=?,pos=? WHERE uid=?', batch)
    if any(state[2] for state in assignment.values()):
        raise ValueError('A graph bundle changed while scheduling')
    return nshards, shard_costs


def freeze_blocks(db, shards, max_tasks, max_graphs=None, target_seconds=None):
    """Freeze exact block boundaries without modifying any scientific task.

    Complete graph bundles remain together when they fit. Oversize bundles are
    split only between existing tasks and reported. No new point chunks are
    introduced. Costs must be measured seconds when target_seconds is used.
    """
    if not 1 <= max_tasks <= 100000:
        raise ValueError('Checkpoint task limit must be in [1,100000]')
    if max_graphs is not None and max_graphs < 1:
        raise ValueError('Positive checkpoint graph limit required')
    if target_seconds is not None and (not math.isfinite(target_seconds) or target_seconds <= 0):
        raise ValueError('Positive finite checkpoint time target required')
    stats = {'layout': LAYOUT, 'blocks': 0, 'graph_loads': 0,
             'max_tasks_per_block': 0, 'max_graphs_per_block': 0,
             'max_estimated_cost_per_block': 0.0,
             'graph_bundles_split_for_task_limit': 0,
             'graph_bundles_split_for_time_target': 0,
             'indivisible_tasks_above_time_target': 0,
             'max_tasks': max_tasks, 'max_graphs': max_graphs,
             'target_measured_seconds': target_seconds}
    with db:
        db.execute('DROP TABLE IF EXISTS checkpoint_blocks')
        db.execute('CREATE TABLE checkpoint_blocks(shard INTEGER NOT NULL,part INTEGER NOT NULL,first_pos INTEGER NOT NULL,task_count INTEGER NOT NULL,estimated_cost REAL NOT NULL,graph_count INTEGER NOT NULL,PRIMARY KEY(shard,part))')
        for shard in range(shards):
            # O(G) metadata only; task rows remain streamed, including oversize
            # graph bundles with very many replicate/chunk tasks.
            bundles = {row[0]: (row[1], row[2]) for row in db.execute(
                'SELECT gi,COUNT(*),SUM(cost) FROM tasks WHERE shard=? GROUP BY gi', (shard,))}
            part = first_pos = count = 0
            graphs = set()
            costs = []
            running_cost = 0.0

            def exceeds_time(addition):
                if target_seconds is None:
                    return False
                estimate = running_cost + addition
                # O(1) in the normal case. Recompute a stable sum only when
                # rounding could change a boundary decision.
                if abs(estimate - target_seconds) <= target_seconds * 1e-10:
                    estimate = math.fsum(costs + [addition])
                return estimate > target_seconds

            def flush():
                nonlocal part, first_pos, count, graphs, costs, running_cost
                if not count:
                    return
                cost = math.fsum(costs)
                db.execute('INSERT INTO checkpoint_blocks VALUES(?,?,?,?,?,?)',
                           (shard, part, first_pos, count, cost, len(graphs)))
                stats['blocks'] += 1
                stats['graph_loads'] += len(graphs)
                stats['max_tasks_per_block'] = max(stats['max_tasks_per_block'], count)
                stats['max_graphs_per_block'] = max(stats['max_graphs_per_block'], len(graphs))
                stats['max_estimated_cost_per_block'] = max(stats['max_estimated_cost_per_block'], cost)
                first_pos += count
                part += 1
                count = 0
                graphs = set()
                costs = []
                running_cost = 0.0

            cursor = db.execute('SELECT gi,pos,cost FROM tasks WHERE shard=? ORDER BY pos', (shard,))
            visited = set()
            for graph, iterator in itertools.groupby(cursor, key=lambda row: row[0]):
                if graph in visited:
                    raise ValueError('Explicit graph-local blocks require contiguous graph bundles')
                visited.add(graph)
                bundle_count, bundle_cost = bundles[graph]
                split_tasks = bundle_count > max_tasks
                split_time = target_seconds is not None and bundle_cost > target_seconds
                stats['graph_bundles_split_for_task_limit'] += int(split_tasks)
                stats['graph_bundles_split_for_time_target'] += int(split_time)
                if split_tasks or split_time:
                    flush()
                elif count and (count + bundle_count > max_tasks or
                                 (max_graphs is not None and len(graphs) + 1 > max_graphs) or
                                 exceeds_time(bundle_cost)):
                    flush()
                for gid, pos, cost in iterator:
                    if not math.isfinite(cost) or cost < 0:
                        raise ValueError('Invalid native task cost')
                    if count and (count >= max_tasks or
                                  (gid not in graphs and max_graphs is not None and len(graphs) >= max_graphs) or
                                  exceeds_time(cost)):
                        flush()
                    if pos != first_pos + count:
                        raise ValueError('Noncontiguous graph task positions')
                    if target_seconds is not None and cost > target_seconds:
                        stats['indivisible_tasks_above_time_target'] += 1
                    count += 1
                    graphs.add(gid)
                    costs.append(cost)
                    running_cost += cost
            flush()
    return stats
