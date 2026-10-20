# runs a Python tool as __main__ and records, at exit, the peak RSS of this process (RUSAGE_SELF: the claim's Python
# process only) and of its reaped children (RUSAGE_CHILDREN: the native worker), in KiB as Linux reports them
import atexit, json, resource, runpy, sys, time
out = sys.argv[1]; sys.argv = sys.argv[2:]; t0 = time.time()
atexit.register(lambda: open(out, 'w').write(json.dumps({'self_maxrss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                                         'children_maxrss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                                                         'wall_seconds': round(time.time() - t0, 2), 'argv': sys.argv}) + '\n'))
runpy.run_path(sys.argv[0], run_name='__main__')
