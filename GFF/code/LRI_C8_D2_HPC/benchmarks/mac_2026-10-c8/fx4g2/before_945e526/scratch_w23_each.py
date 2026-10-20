# Scratch only (not in the package's tests): tests/unit_orchestration.py test_no_reread with every refusal recorded
# instead of raised, run on 945e526's tools to show each part (a)-(g) failing there (w23_each.json).
def test_w23_each(E):
    """W23 (host residual) and its class: nothing assemble and combine checked is read again. (a) assemble.evaluate of
    a NON-test campaign whose pinned design_meta.json changes right after production.design_bundle checked it (here: a
    trailing space, the same counts digests) is refused, naming the campaign's sha256 (before: the coverage guard
    parsed the second read). (b) combine.load_batch of a test-only batch likewise (combine.test_coverage). (c) The
    coverage guard parses each counts file with design.parse_counts: a verified file with '+8' or a repeated graph is
    refused (before: int() took them). (d) evaluate's inventory and (e) load_batch's group seeds come from bytes
    verified against the campaign's pins: a whitespace change after load_campaign is refused (before: re-read
    unverified). (f) The order-8 module is executed from the bytes whose sha256 was checked (a loader re-read is never
    used) and the result records that sha256; (g) two_loop() returns the sha256 of the bytes it parsed. The same class in
    production and lanes: (h) the serial merge reads a verified private copy of tasks.sqlite (a file changed after
    merge's digest check is refused); (i) a lane reads cost_model.json from bytes verified against the manifest pin."""
    p,A,CB=E.M.prod,E.M.asm,E.M.comb;n=0;_fails=[]
    B=synth_bundle(E,E.td/'w23_B')
    d=E.td/'w23';E.plan(d,'--design',B,'--test-graphs','all','--bootstrap-chunk',4,'--shards',1,seed=SEED+340);E.run_all(d);cli(p,'merge',d)
    m=manifest(d);pinned=d/'design_bundle/design_meta.json';meta0=pinned.read_bytes()
    real_load=A.load_campaign
    def nontest(directory,accept_tool_change=False):
        m_,*rest=real_load(directory,accept_tool_change);return (dict(m_,test_only=False),*rest)
    assert A.evaluate(d,0)['test_only']is True
    with mock.patch.object(A,'load_campaign',nontest):A.evaluate(d,0)  # the coverage guard passes on the untouched campaign
    real_db=p.design_bundle
    def swapped(directory,m_,override=None):
        b=real_db(directory,m_,override);(b/'design_meta.json').write_bytes(meta0+b' ');return b
    try:
        with mock.patch.object(A,'load_campaign',nontest),mock.patch.object(p,'design_bundle',swapped):
            try:A.evaluate(d,0);_fails.append('evaluate used a design_meta.json other than the one design_bundle checked')
            except ValueError as e:assert m['design']['meta_sha256']in str(e)and 'design_meta.json'in str(e),str(e);n+=1
        pinned.write_bytes(meta0)
        with mock.patch.object(p,'design_bundle',swapped):
            try:CB.load_batch(d,True);_fails.append('load_batch used a design_meta.json other than the one design_bundle checked')
            except ValueError as e:assert m['design']['meta_sha256']in str(e),str(e);n+=1
    finally:pinned.write_bytes(meta0)
    CB.load_batch(d,True)
    # (c) the counts parsed strictly (a bundle whose meta pins the edited counts file)
    inv=json.loads((E.fixture/'inventory.json').read_text())
    groups={(c,s,L):{int(r['id']):8 for r in inv[s][str(L)]}for c in 'ab'for s in ('free','power')for L in range(3,9)}
    C2=synth_bundle(E,E.td/'w23_C');assert A.coverage_guard(groups,inv,8,C2,1)['groups']==24
    name='counts/a_free_L3.txt';orig=(C2/name).read_bytes();g0=orig.split(b' ',1)[0]
    for what,data in (('+8',orig.replace(b' 8\n',b' +8\n',1)),('a repeated graph',orig+g0+b' 8\n')):
        (C2/name).write_bytes(data);mm=json.loads((C2/'design_meta.json').read_text());mm['counts_sha256'][name]=hashlib.sha256(data).hexdigest()
        (C2/'design_meta.json').write_text(json.dumps(mm))
        try:A.coverage_guard(groups,inv,8,C2,1);_fails.append(f'the coverage guard parsed {what}')
        except ValueError as e:assert 'a_free_L3.txt'in str(e),(what,str(e));n+=1
    # (d), (e): the inventory and the group configs re-read after load_campaign
    invf=E.fixture/'inventory.json';inv0=invf.read_bytes();cfgf=d/'groups/a_free_L3/config.json';cfg0=cfgf.read_bytes()
    def then(fn):
        def wrapped(directory,accept_tool_change=False):
            out=real_load(directory,accept_tool_change);fn();return out
        return wrapped
    def nontest_then(fn):
        def wrapped(directory,accept_tool_change=False):
            m_,*rest=real_load(directory,accept_tool_change);fn();return (dict(m_,test_only=False),*rest)
        return wrapped
    try:
        with mock.patch.object(A,'load_campaign',nontest_then(lambda:replace_bytes(invf,inv0+b' '))):
            try:A.evaluate(d,0);_fails.append('evaluate parsed a re-read inventory.json')
            except ValueError as e:assert 'Checksum mismatch'in str(e)and 'inventory.json'in str(e),str(e);n+=1
    finally:replace_bytes(invf,inv0)
    try:
        with mock.patch.object(A,'load_campaign',then(lambda:replace_bytes(cfgf,cfg0+b' '))):
            try:CB.load_batch(d,True);_fails.append('load_batch took a seed from a re-read config.json')
            except ValueError as e:assert 'Checksum mismatch'in str(e)and 'config.json'in str(e),str(e);n+=1
    finally:replace_bytes(cfgf,cfg0)
    # (f) the module is executed from the verified bytes; (g) two_loop's sha256 is of the bytes parsed
    import importlib.machinery
    real_get=importlib.machinery.SourceFileLoader.get_data
    def tampered(self,path):
        data=real_get(self,path)
        return data+b'\nW23_TAMPERED = True\n'if str(path).endswith('order8_assembly.py')else data
    saved=(A._OA,getattr(A,'_OA_SHA',None))
    try:
        A._OA=None
        with mock.patch.object(importlib.machinery.SourceFileLoader,'get_data',tampered):mod=A.vendored()
        _fails.append('(f) the order-8 module was executed from a re-read of its file')if hasattr(mod,'W23_TAMPERED')else None;n+=1
        pin=next(x['sha256']for x in json.loads((E.pkg/'tools/VENDORED.json').read_text())['files']if x['path']=='order8_assembly.py');_fails.append('(f) no verified module sha recorded')if getattr(A,'_OA_SHA',None)!=pin else None
    finally:A._OA,A._OA_SHA=saved
    tl=E.pkg/'inputs/two_loop.json';real_rb=Path.read_bytes;alt=json.dumps({'B2':[0.0]*len(json.loads(tl.read_text())['B2'])}).encode()
    with mock.patch.object(Path,'read_bytes',lambda self:alt if self.resolve()==tl.resolve()else real_rb(self)):b2,sha=A.two_loop()
    _fails.append('(g) two_loop recorded the sha256 of another read than the one it parsed')if not(sha==hashlib.sha256(alt).hexdigest()and not b2.any())else None;n+=1
    print('W23_EACH',json.dumps(_fails),flush=True)
    assert not _fails,_fails

