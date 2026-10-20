# Stand-in for `perf` in tests/test_profiling.py (installed as <tmp>/perf with a shebang): never a measurement.
# record -o FILE ... -- CMD   runs CMD, writes FILE and prints perf's summary line to stderr
# stat -x, -o FILE -e EVENTS -- CMD   runs CMD and writes canned CSV (perf stat -x, format) to FILE (or stderr)
# report ... --sort KEY ...   prints the canned report for KEY (symbol, dso,symbol or dso); --header-only a header
# annotate ...                prints a canned perf annotate --stdio listing of the worker
# --version                   prints a version line
# FAKE_PERF_REFUSE=1 makes stat and record fail as perf does under a restrictive perf_event_paranoid.
import os,subprocess,sys
ROWS=[(30.00,300000,'libgcc_s.so.1','.','__multf3'),(20.00,200000,'libgcc_s.so.1','.','__addtf3'),(10.00,100000,'c8d2_gmp','.','main._omp_fn.0'),
      (8.00,80000,'libquadmath.so.0.0.0','.','expq'),(6.00,60000,'libgmp.so.10.4.1','.','__gmpn_mul_basecase'),(5.00,50000,'libgmp.so.10.4.1','.','__gmpf_add'),
      (4.00,40000,'libc-2.28.so','.','__expl_finite'),
      (3.00,30000,'c8d2_gmp','.','std::pair<long double, long double> calculate_reference<long double>(Graph const&, long double const*, long double)'),
      (2.50,25000,'libgmp.so.10.4.1','.','__gmpf_get_str'),(2.00,20000,'libc-2.28.so','.','____strtold_l_internal'),(2.00,20000,'libc-2.28.so','.','_int_malloc'),
      (1.50,15000,'libc-2.28.so','.','free'),(1.50,15000,'libgomp.so.1.0.0','.','gomp_barrier_wait_end'),(1.00,10000,'libgcc_s.so.1','.','__subtf3'),
      (1.00,10000,'libgcc_s.so.1','.','__divtf3'),(1.00,10000,'[kernel.kallsyms]','k','native_write_msr'),(0.50,5000,'libgcc_s.so.1','.','__lttf2'),
      (0.50,5000,'libgmp.so.10.4.1','.','__gmpn_divrem_1'),(0.50,5000,'libc-2.28.so','.','__ieee754_logl')]
HEAD="""# To display the perf.data header info, please use --header/--header-only options.
#
#
# Total Lost Samples: 0
#
# Samples: 1M  of event 'cycles'
# Event count (approx.): 987654321000
#
"""
def report(key):
    out=[HEAD]
    if key=='symbol':
        out.append('# Overhead       Samples  Symbol\n# ........  ............  ......................................\n#\n')
        out+=[f'  {o:6.2f}%  {n:12d}  [{lv}] {s}\n'for o,n,d,lv,s in ROWS]
    elif key=='dso,symbol':
        out.append('# Overhead       Samples  Shared Object         Symbol\n# ........  ............  ....................  ......\n#\n')
        out+=[f'  {o:6.2f}%  {n:12d}  {d:<20s}  [{lv}] {s}\n'for o,n,d,lv,s in ROWS]
    else:
        agg={}
        for o,n,d,lv,s in ROWS:a=agg.setdefault(d,[0.,0]);a[0]+=o;a[1]+=n
        out.append('# Overhead       Samples  Shared Object\n# ........  ............  ....................\n#\n')
        out+=[f'  {o:6.2f}%  {n:12d}  {d}\n'for d,(o,n)in sorted(agg.items(),key=lambda kv:-kv[1][0])]
    out.append('\n\n#\n# (Cannot load tips.txt file, please install perf!)\n#\n')
    return ''.join(out)
ANNOTATE=""" Percent |	Source code & Disassembly of c8d2_gmp for cycles (100000 samples, percent: local period)
---------------------------------------------------------------------------------------------------
         :
         :
         :
         :	Disassembly of section .text:
         :
         :	0000000000403f60 <main._omp_fn.0>:
    0.00 :	  403f60:       push   %r15
   60.00 :	  403f62:       fldt   0x10(%rsp)
   40.00 :	  403f66:       faddp  %st,%st(1)
"""
STAT="""123456789,,cycles,1000000,100.00,,
98765432,,instructions,1000000,100.00,0.80,insn per cycle
1000,,branches,1000000,100.00,,
10,,branch-misses,1000000,100.00,1.00,of all branches
<not supported>,,L1-dcache-loads,0,100.00,,
<not counted>,,L1-dcache-load-misses,0,0.00,,
1234.56,msec,task-clock,1234560000,100.00,1.00,CPUs utilized
"""
def after_dashes(a):return a[a.index('--')+1:]if '--'in a else[]
def opt(a,name):return a[a.index(name)+1]if name in a else None
a=sys.argv[1:]
if a[:1]==['--version']:print('perf version 0.0.fake');sys.exit(0)
cmd=a[0]if a else''
if cmd in('stat','record')and os.environ.get('FAKE_PERF_REFUSE'):
    print('Error:\nNo permission to enable cycles event.\nConsider tweaking /proc/sys/kernel/perf_event_paranoid',file=sys.stderr);sys.exit(255)
if cmd=='record':
    rc=subprocess.run(after_dashes(a)).returncode;f=opt(a,'-o')or'perf.data';open(f,'w').write('FAKE PERF DATA\n')
    print(f'[ perf record: Woken up 3 times to write data ]\n[ perf record: Captured and wrote 0.123 MB {f} (1234 samples) ]',file=sys.stderr);sys.exit(rc)
if cmd=='stat':
    rc=subprocess.run(after_dashes(a)).returncode;f=opt(a,'-o')
    if f:open(f,'w').write(STAT)
    else:sys.stderr.write(STAT)
    sys.exit(rc)
if cmd=='report':
    if '--header-only'in a:print('# ========\n# captured on    : fake\n# ========');sys.exit(0)
    sys.stdout.write(report(opt(a,'--sort')or'symbol'));sys.exit(0)
if cmd=='annotate':sys.stdout.write(ANNOTATE);sys.exit(0)
print(f'fake perf: unsupported {a}',file=sys.stderr);sys.exit(1)
