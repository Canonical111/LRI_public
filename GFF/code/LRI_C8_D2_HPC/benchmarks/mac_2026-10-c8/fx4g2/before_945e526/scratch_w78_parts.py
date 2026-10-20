def test_w78_parts(E):
    """Scratch only (before-run evidence): the separate pieces of W7 and W8, each recorded instead of stopping."""
    C=E.M.common;p=E.M.prod;res={}
    def part(name,fn):
        try:fn();res[name]='passed'
        except BaseException as e:res[name]=f'FAILED: {type(e).__name__}: {str(e)[:200]}'
    # W7 (b): the lane worker under LD_PRELOAD
    def w7b():
        dl=E.td/'p_w7_lanes';lanes_plan(E,dl,seed=SEED+402);tool(E.pkg,'lanes.py','queue',dl)
        cp=tool(E.pkg,'lanes.py','worker',dl,env={'SLURM_JOB_ID':'7301','C8_LANE_SECONDS':'36000','LD_PRELOAD':'/nonexistent/libw7.so'},check=False)
        assert cp.returncode==64,(cp.returncode,cp.stderr[-200:])
    part('W7 (b) lane worker refuses LD_PRELOAD',w7b)
    t=E.td/'p_w7_ldd';t.mkdir();(t/'ld-2.28.so').write_bytes(b'ld.so');(t/'libgmp.so.10').write_bytes(b'gmp');(t/'libc.so.6').write_bytes(b'libc')
    A_,B_=t/'libA.so',t/'libB.so';A_.write_bytes(b'A');B_.write_bytes(b'B');exe=t/'worker';exe.write_bytes(elf_bytes(interp_path=str(t/'ld-2.28.so')))
    def text(order):
        return (''.join(f'\t{x} (0x00007f2b1e000000)\n'for x in order)+f'\tlibgmp.so.10 => {t}/libgmp.so.10 (0x00007f2b1c000000)\n'
                f'\tlibc.so.6 => {t}/libc.so.6 (0x00007f2b1b000000)\n\t{t}/ld-2.28.so (0x00007f2b1d000000)\n').encode()
    def w7c():
        fab,fba=ldd_probe(C,text([A_,B_]),exe),ldd_probe(C,text([B_,A_]),exe)
        assert C.runtime_identity_key(fab)!=C.runtime_identity_key(fba),'reversed preload order: one identity'
    part('W7 (c) preload order in the runtime identity',w7c)
    def w7d():
        d2=E.td/'p_w7run';E.small(d2,'--checkpoint-tasks',4,'--shards',1,seed=SEED+401);m2=manifest(d2)
        stub=lambda order:(lambda target,counter=None,identity=None:ldd_probe(C,text(order),target,counter,identity))
        with mock.patch.object(p,'fingerprint',stub([A_,B_])):E.run(d2,m2['jobs'][0]['id'])
        with mock.patch.object(p,'fingerprint',stub([B_,A_])):r=E.run(d2,m2['jobs'][1]['id'],expect=1)
    part('W7 (d) a claim with the reversed order refused',w7d)
    # W8: merges of checkpoints of another libgmp; the non-test plan's build record
    X='4'*64;Y='9'*64
    fx=json.loads((E.fixture/'inventory.json').read_text());dexe=E.pkg/'bin/c8d2_gmp_dd+mp256';dexe.write_text(FAKE_SHEBANG+(ROOT/'tests/fake_worker.py').read_text());dexe.chmod(0o755)
    cmd_=cost_model_for(E,None);cmd_['numerics']='dd+mp256';cmf=E.td/'p_w8_cm.json';cmf.write_text(json.dumps(cmd_))
    B=route_b_bundle(E.td/'p_w8_B',fx,digest(E.fixture/'manifest.json'),digest(dexe),X)
    d=E.td/'p_w8';E.plan(d,'--design',B,'--test-graphs',2,'--cost-model',cmf,'--shards',1,'--numerics','dd+mp256','--approved-numerics-change','unit test (W8)',seed=SEED+410)
    m=manifest(d)
    lib=lambda path,sha:{'path':path,'resolved':path,'sha256':sha}
    def fp_with(sha):
        real=p.fingerprint
        def fake(target,counter=None,identity=None):
            x=real(target,counter,identity);x.update(glibc='glibc 2.35',ldd_error=None,interpreter={'path':'/lib64/ld.so','resolved':'/lib64/ld.so','sha256':'1'*64},
                                                    libraries={'libgmp.so.10':lib('/usr/lib/libgmp.so.10',sha),'libc.so.6':lib('/lib/libc.so.6','3'*64)});return x
        return fake
    with mock.patch.object(p,'elf_kind',lambda path:'dynamic'),mock.patch.object(p,'fingerprint',fp_with(Y)):E.run_all(d)  # old tools: claims of libgmp Y run
    g=m['jobs'][0]['group']
    for args in (('--jobs',1),('--jobs',2),('--serial',)):
        part(f'W8 merge {args} refuses checkpoints of another libgmp',lambda args=args:cli(p,'merge',d,'--group',g,*args,expect=1))
    N=nontest_package(E);nexe=N.pkg/'bin/c8d2_gmp_dd+mp256';nexe.write_text(FAKE_SHEBANG+(ROOT/'tests/fake_worker.py').read_text());nexe.chmod(0o755)
    ninv=json.loads((N.pkg/'inputs/inventory.json').read_text())
    NB=route_b_bundle(E.td/'p_w8_NB',ninv,digest(N.pkg/'inputs/manifest.json'),digest(nexe),X,test_only=False,reps=32,count=256)
    ncm=cost_model_for(E,None);ncm['numerics']='dd+mp256';ncmf=E.td/'p_w8_ncm.json';ncmf.write_text(json.dumps(ncm))
    fake_build_record(nexe,'gmp','dd+mp256',gmp_library={'soname':'libgmp.so.10','sha256':Y})
    def w8plan():
        cp=tool(N.pkg,'production.py','plan',E.td/'p_w8_nontest','--seed',SEED+411,'--design',NB,'--threads',2,'--checkpoint-tasks',8,'--shards',1,'--cost-model',ncmf,
                '--forbid-seeds-from',N.log,'--numerics','dd+mp256','--approved-numerics-change','unit test (W8)',env=N.env,check=False)
        assert cp.returncode!=0,'the non-test plan accepted a build record of another libgmp'
    part('W8 a non-test plan refuses a build record of another libgmp',w8plan)
    print('W78_PARTS',json.dumps(res),flush=True)
    assert all(v=='passed'for v in res.values()),res

