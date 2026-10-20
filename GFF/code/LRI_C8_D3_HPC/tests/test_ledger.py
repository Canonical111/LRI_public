#!/usr/bin/env python3
"""tools/ledger.py alone (plan F-table row `test_ledger.py`; D.11, D.12; R12, R13, R20, H-e..H-g). Mac only.

The frame (byte-exact re-framing, checksum, size limit, every kind; a token already in the ledger or intents/ drawn
again); the intent file (O_CREAT|O_EXCL, file and directory fsync, the recorded st_ino and byte range) and the
resolution order; the record check's three classes; torn final records (evidence, then truncation; nothing truncated
when the evidence write fails; a crash between the two steps); interior corruption; `rebuild` (keeps every valid record,
restores every intent, matches each segment of each invalid line by byte range or token, blocks otherwise and whenever
the ledger is missing, proceeds only with --user-decision from G after the block; atomic under SIGKILL; unattributable
jobs); `register`; the session lock (75 with the holder line, free at once after SIGKILL, never deleted, the fsync
check); the mount check; the fail-closed settings; `lockprobe`'s ordered handshake.

  python3 -B tests/test_ledger.py
"""
from __future__ import annotations
import errno,hashlib,json,os,shutil,signal,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import ledger,budget
from common import Refuse
from fake_slurm.core import Fake,inprocess_runner
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)

class Killed(BaseException):pass
class TH(ledger.Hooks):
    """In-process test hooks: faults by write point, kills by step, a fake clock."""
    def __init__(self):self.faults={};self.kill=set();self.log=[];self.off=0.0;self.switches=set()
    def point(self,name,**info):
        self.log.append(('point',name,info))
        if name in self.kill:self.kill.discard(name);raise Killed(name)
    def event(self,name,**info):self.log.append(('event',name,info))
    def write_fault(self,point,nbytes):return self.faults.pop(point,None)
    def switch(self,name):return name in self.switches
    def offset(self):return self.off
    def advance(self,s):self.off+=s
    def setting(self,name,default):return {'lock_poll':0.005}.get(name,default)

def fresh(td:Path,name:str)->tuple[Path,dict,TH]:
    root=td/name;root.mkdir();h=TH();ledger.HOOKS=h
    return root,{'C8_SITE':'fake','C8_ROOT':str(root),'C8_LOCK_WAIT':'1','PATH':os.environ['PATH']},h

def refuses(code,fn,*a,**k)->str:
    try:fn(*a,**k)
    except Refuse as r:
        assert r.code==code,(r.code,str(r));return str(r)
    raise AssertionError(f'expected refusal {code}')

def P(kind,t,**f):return ledger.payload(kind,[t],token=t,**f)
def intent(t,**f):
    base=dict(name=f'c8d3-val-{"a"*12}-{t}',comment=f'c8d3:{"a"*12}:{"0"*12}:{t}',role='val',c='a'*12,p='0'*12,dir='/x',partition='shared',nodes=1,cpus=2,
              mem_mib=4096.0,time_s=3600,array=None,task_count=1,billing=2.0,reservation_su=2.0,slots={'shared':1},line='dev',pid=1,mono=0.0,command='t')
    base.update(f);return P('intent',t,**base)

def tool(script,*args,env,check=None):
    cp=subprocess.run([sys.executable,'-B',str(ROOT/'tools'/script),*map(str,args)],capture_output=True,text=True,env=env)
    if check is not None:assert cp.returncode==check,(script,args,cp.returncode,cp.stderr[-1500:],cp.stdout[-500:])
    return cp

# ----------------------------------------------------------------------------------------------------------------
def test_frame(td):
    root,env,h=fresh(td,'frame')
    kinds=[intent('a1'*6),P('submit','a1'*6,job_id='123'),P('adopted','b2'*6,job_id='124',dir=None),P('register','c3'*6,job_id='9',dir='/r'),
           P('annotation','a1'*6,about='dir',job_id='124',dir='/r'),P('resolution','a1'*6,rule='terminal',charge_su=1.25),
           P('not_submitted','d4'*6,launched=False,ambiguous=False,reason='x')]
    assert {k['kind']for k in kinds}==set(ledger.KINDS)
    for p in kinds:
        line=ledger.frame(p)
        assert line.endswith(b'\n')and line.startswith(b'{"rec":')and ledger.unframe(line)==p
        c=ledger.canonical(p).encode();assert line==b'{"rec":'+c+b',"sha256":"'+hashlib.sha256(c).hexdigest().encode()+b'"}\n'
        # any single flipped byte, a reordered frame, extra whitespace or a missing newline invalidates it
        for i in (8,len(line)//2,len(line)-5):
            bad=bytearray(line);bad[i]^=0x01;assert ledger.unframe(bytes(bad))is None
        obj=json.loads(line);assert ledger.unframe((json.dumps({'sha256':obj['sha256'],'rec':obj['rec']},separators=(',',':'))+'\n').encode())is None
        assert ledger.unframe(line.replace(b'{"rec":',b'{"rec": ',1))is None and ledger.unframe(line[:-1])is None
    big=P('annotation','a1'*6,blob='x'*70000);refuses(64,ledger.frame,big)
    exact=P('annotation','a1'*6,blob='');n=len(ledger.frame(exact));fit=dict(exact,blob='x'*(ledger.MAX_RECORD-n))
    assert len(ledger.frame(fit))==ledger.MAX_RECORD and ledger.unframe(ledger.frame(fit))==fit
    refuses(64,ledger.frame,dict(exact,blob='x'*(ledger.MAX_RECORD-n+1)))
    assert ledger.unframe(ledger.frame(fit)[:-1]+b' \n')is None
    assert ledger.unframe(b'{"rec":{"x":NaN},"sha256":"00"}\n')is None
    for bad in ({'schema':'other','kind':'intent','tokens':[]},{'schema':ledger.SCHEMA,'kind':'nope','tokens':[]},{'schema':ledger.SCHEMA,'kind':'intent','tokens':['XYZ']}):
        try:ledger.frame(bad)
        except ValueError:pass
        else:raise AssertionError(bad)
    # a token already in the ledger, in intents/ or in intents/resolved/ is drawn again
    s=ledger.Settings(env)
    with ledger.SessionLock(s,'t')as lock:
        led=ledger.Ledger(s,lock,create=True);led.read(writer=True);led.append(intent('111111111111'))
        ledger.ensure_dir(s.intents);ledger.ensure_dir(s.resolved);(s.intents/'222222222222.json').write_bytes(b'x');(s.resolved/'333333333333.json').write_bytes(b'x')
        seq=iter(['111111111111','222222222222','333333333333','444444444444']);real=ledger.secrets.token_hex
        ledger.secrets.token_hex=lambda n:next(seq)
        try:t=led.new_token()
        finally:ledger.secrets.token_hex=real
        assert t=='444444444444'and sum(1 for e in h.log if e[1]=='token_redrawn')==3
    ok('frame_every_kind_checksum_size_limit_token_redraw')

def test_intent_file_and_resolution(td):
    root,env,h=fresh(td,'ifile');s=ledger.Settings(env);calls=[]
    real=os.fsync
    def spy(fd):
        st=os.fstat(fd);calls.append(('dir'if os.path.isdir(f'/dev/fd/{fd}')or __import__('stat').S_ISDIR(st.st_mode)else'file',st.st_ino));return real(fd)
    os.fsync=spy
    try:
        with ledger.SessionLock(s,'t')as lock:
            led=ledger.Ledger(s,lock,create=True);led.read(writer=True)
            led.append(intent('aaaaaaaaaaa1'));p=intent('aaaaaaaaaaa2')
            ino,off,n=led.append(p);calls.clear()
            led.write_intent_file(p,ino,off,n)
            f=s.intents/'aaaaaaaaaaa2.json';fp=ledger.unframe(f.read_bytes())
            assert fp['ledger_st_ino']==os.stat(s.ledger_path).st_ino and s.ledger_path.read_bytes()[fp['ledger_offset']:fp['ledger_offset']+fp['ledger_length']]==ledger.frame(p)
            assert ('file',os.stat(f).st_ino)in calls and ('dir',os.stat(s.intents).st_ino)in calls and oct(f.stat().st_mode&0o777)=='0o600'
            try:led.write_intent_file(p,ino,off,n)
            except FileExistsError:pass
            else:raise AssertionError('O_EXCL not enforced')
            its=ledger.intent_state(led);assert its['aaaaaaaaaaa2'].unresolved and its['aaaaaaaaaaa2'].file_loc=='pending'
            assert its['aaaaaaaaaaa1'].unresolved and its['aaaaaaaaaaa1'].file_loc is None   # ledger copy only: counted, reported
            # resolution order: the resolving record first; a crash before the rename leaves T unresolved (union rule)
            led.append(P('resolution','aaaaaaaaaaa2',rule='terminal',charge_su=0.5))
            its=ledger.intent_state(led);assert its['aaaaaaaaaaa2'].unresolved and its['aaaaaaaaaaa2'].resolved_in_ledger
            calls.clear();assert led.rename_resolved('aaaaaaaaaaa2')and not led.rename_resolved('aaaaaaaaaaa2')   # completed once, never repeated
            assert ('dir',os.stat(s.intents).st_ino)in calls and ('dir',os.stat(s.resolved).st_ino)in calls
            its=ledger.intent_state(led);it=its['aaaaaaaaaaa2'];assert not it.unresolved and it.floor_su()==0.5
            # an intent present only as its file (ledger copy missing) is unresolved; resolved in one copy only too
            q=intent('aaaaaaaaaaa3');led.write_intent_file(q,0,0,0)
            its=ledger.intent_state(led);assert its['aaaaaaaaaaa3'].unresolved and its['aaaaaaaaaaa3'].ledger is None
            os.rename(s.intents/'aaaaaaaaaaa3.json',s.resolved/'aaaaaaaaaaa3.json')
            its=ledger.intent_state(led);assert its['aaaaaaaaaaa3'].unresolved,'resolved/ without a resolving record is unresolved'
            # an unreadable intent file with a valid ledger copy is counted and reported; without one it refuses
            (s.intents/'aaaaaaaaaaa1.json').write_bytes(b'garbage');its=ledger.intent_state(led)
            assert its['aaaaaaaaaaa1'].unresolved and its['aaaaaaaaaaa1'].file_error
            (s.intents/'aaaaaaaaaaa9.json').write_bytes(b'garbage');refuses(69,ledger.intent_state,led)
    finally:os.fsync=real
    ok('intent_file_excl_fsync_inode_range_resolution_order_union')

def states(s):
    led=ledger.Ledger(s);led.read(writer=False);return ledger.intent_state(led)

def write_ledger(s,payloads)->bytes:
    data=b''.join(ledger.frame(p)for p in payloads);s.ledger_path.write_bytes(data);return data

def test_record_check(td):
    root,env,h=fresh(td,'check');s=ledger.Settings(env)
    recs=[intent(f'{i:012x}')for i in range(3)];data=write_ledger(s,recs)
    assert ledger.Scan(data).status=='clean'
    torn=data+ledger.frame(P('submit','0'*11+'1',job_id='5'))[:40];assert ledger.Scan(torn).status=='torn'
    lines=ledger.split_lines(data);mid=bytearray(data);mid[lines[1][0]+20]^=1;sc=ledger.Scan(bytes(mid))
    assert sc.status=='corrupt'and sc.bad==(2,lines[1][0])
    final=bytearray(data);final[lines[2][0]+20]^=1;assert ledger.Scan(bytes(final)).status=='corrupt'
    for kind in ledger.KINDS:   # a torn final record of each kind is truncated after its bytes are kept as evidence
        p=intent('f'*12)if kind=='intent'else P(kind,'f'*12,x=1)
        line=ledger.frame(p);tail=line[:len(line)//2];s.ledger_path.write_bytes(data+tail)
        with ledger.SessionLock(s,'t')as lock:
            led=ledger.Ledger(s,lock);led.read(writer=True)
            assert s.ledger_path.read_bytes()==data
            ev=sorted(s.evidence.glob('tail.*'));assert ev and ev[-1].read_bytes()==tail
            led.append(P('annotation','f'*12,about='after'));assert ledger.Scan(s.ledger_path.read_bytes()).status=='clean'
        data=s.ledger_path.read_bytes()
    # nothing truncated when the evidence write fails (74)
    s.ledger_path.write_bytes(data+b'{"rec":{"partial');before=s.ledger_path.read_bytes()
    with ledger.SessionLock(s,'t')as lock:
        h.faults['evidence']={'errno':errno.EDQUOT};msg=refuses(74,ledger.Ledger(s,lock).read,writer=True)
        assert s.ledger_path.read_bytes()==before and 'nothing truncated'in msg
    # a crash between the evidence write and the truncation: the next holder handles the same tail again
    with ledger.SessionLock(s,'t')as lock:
        h.kill.add('tail_evidence_written')
        try:ledger.Ledger(s,lock).read(writer=True)
        except Killed:pass
    assert s.ledger_path.read_bytes()==before
    with ledger.SessionLock(s,'t')as lock:ledger.Ledger(s,lock).read(writer=True)
    assert s.ledger_path.read_bytes()==data
    # a complete final line with a bad checksum, and interior corruption: 69 naming the file, the line and the offset
    for bad in (bytes(final),bytes(mid),data+b'not a frame\n'+ledger.frame(intent('e'*12))):
        s.ledger_path.write_bytes(bad)
        with ledger.SessionLock(s,'t')as lock:
            msg=refuses(69,ledger.Ledger(s,lock).read,writer=True)
            assert str(s.ledger_path)in msg and 'line'in msg and 'byte offset'in msg and s.ledger_path.read_bytes()==bad
        refuses(69,ledger.Ledger(s).read,writer=False)
    # readers skip an incomplete final line without truncating it
    s.ledger_path.write_bytes(data+b'{"rec":');led=ledger.Ledger(s);led.read(writer=False);assert led.torn_skipped and s.ledger_path.read_bytes()==data+b'{"rec":'
    ok('record_check_clean_torn_corrupt_evidence_first_crash_between')

def test_append_failures(td):
    root,env,h=fresh(td,'append');s=ledger.Settings(env)
    with ledger.SessionLock(s,'t')as lock:
        led=ledger.Ledger(s,lock,create=True);led.read(writer=True);led.append(intent('1'*12));before=s.ledger_path.read_bytes()
        for spec in ({'errno':errno.EDQUOT},{'errno':errno.ENOSPC},{'errno':errno.EIO},{'short':1},{'short':'half'},{'short':'n-1'},{'fsync_errno':errno.EIO}):
            s.ledger_path.write_bytes(before);h.faults['ledger:submit']=spec;rec=P('submit','1'*12,job_id='7');n=len(ledger.frame(rec))
            led=ledger.Ledger(s,lock);led.read(writer=True)
            msg=refuses(74,led.append,rec)
            after=s.ledger_path.read_bytes();assert after[:len(before)]==before,'a byte present before the failed append changed'
            if 'errno'in spec:assert after==before and('EDQUOT'in msg or spec['errno']!=errno.EDQUOT)
            if 'short'in spec:assert len(after)-len(before)=={1:1,'half':n//2,'n-1':n-1}[spec['short']]and 'short write'in msg
            if 'fsync_errno'in spec:assert len(after)-len(before)==n   # complete but not fsynced: it stays (it can only over-count)
            # no further append follows a failed or short one (D.11 step 5): the same writer refuses (74) and writes nothing
            msg=refuses(74,led.append,P('annotation','1'*12,about='after a failure'));assert s.ledger_path.read_bytes()==after and 'nothing more'in msg
            led2=ledger.Ledger(s,lock);led2.read(writer=True);assert s.ledger_path.read_bytes()==(before if 'short'in spec else after)
        # the lock descriptor's fsync check ends the call before an append (69), nothing written; the lock stays lost
        s.ledger_path.write_bytes(before);h.faults['lock_fsync']={'errno':errno.EIO};led=ledger.Ledger(s,lock);led.read(writer=True)
        refuses(69,led.append,P('submit','1'*12,job_id='7'));assert s.ledger_path.read_bytes()==before and lock.lost
        refuses(69,ledger.Ledger(s,lock).append,P('submit','1'*12,job_id='7'));assert s.ledger_path.read_bytes()==before
    # EDQUOT at create (Lustre's file quota): the ledger's first append, an evidence file and an intent file: 74, no traceback
    root,env,h=fresh(td,'append_create');s=ledger.Settings(env)
    with ledger.SessionLock(s,'t')as lock:
        h.faults['ledger:create']={'errno':errno.EDQUOT};led=ledger.Ledger(s,lock,create=True);led.read(writer=True)
        msg=refuses(74,led.append,intent('2'*12));assert 'EDQUOT'in msg and not s.ledger_path.exists()
        led=ledger.Ledger(s,lock,create=True);led.read(writer=True);p=intent('2'*12);ino,off,n=led.append(p)
        h.faults['intent_file:create']={'errno':errno.EDQUOT};msg=refuses(74,led.write_intent_file,p,ino,off,n)
        assert 'EDQUOT'in msg and not (s.intents/f'{"2"*12}.json').exists()
        base=s.ledger_path.read_bytes();s.ledger_path.write_bytes(base+b'{"rec":{"torn')
        h.faults['evidence:create']={'errno':errno.EDQUOT};msg=refuses(74,ledger.Ledger(s,lock).read,writer=True)
        assert 'nothing truncated'in msg and s.ledger_path.read_bytes()==base+b'{"rec":{"torn'and not list(s.evidence.glob('tail.*'))
        h.faults['truncate:create']={'errno':errno.EIO};refuses(74,ledger.Ledger(s,lock).read,writer=True)
        assert s.ledger_path.read_bytes()==base+b'{"rec":{"torn'
    # a writer never creates a missing ledger unless allowed (admission's first use, or rebuild): 69, nothing created
    root,env,h=fresh(td,'append_nocreate');s=ledger.Settings(env)
    with ledger.SessionLock(s,'t')as lock:
        led=ledger.Ledger(s,lock);led.read(writer=True);refuses(69,led.append,intent('3'*12));assert not s.ledger_path.exists()
        def fu(seen):
            l=ledger.Ledger(s,lock);l.read(writer=True);l.first_use(seen,'admission');return l
        ledger.ensure_dir(s.intents);(s.intents/f'{"4"*12}.json').write_bytes(b'x')
        msg=refuses(69,fu,False);assert 'missing'in msg;os.unlink(s.intents/f'{"4"*12}.json')
        refuses(69,fu,True)            # a c8d3- job in the scheduler alone blocks too
        fu(False).append(intent('3'*12));assert s.ledger_path.exists()   # the first use on a new root creates it
    ok('append_edquot_enospc_eio_short_fsync_no_append_after_failure_create_faults_and_lock_fsync_check')

def test_register(td):
    root,env,h=fresh(td,'reg');d=root/'runs'/'smoke1';d.mkdir(parents=True);(d/'manifest.json').write_text('{"plan":1}\n')
    t='abcdefabcdef';c=ledger.dir_sha12(d)
    e={**env,'SLURM_JOB_ID':'777','SLURM_JOB_NAME':f'c8d3-plan-{c}-{t}','SLURM_RESTART_COUNT':'0'}
    # a missing ledger is a repair block: `register` (inside a running c8d3- job) and `resolve` refuse (69) and never
    # create it, with or without intent files (HD17's condition always holds for register: its own job is a c8d3- job)
    log=root/'PLAN-REVIEW-LOG.md';log.write_text('- **User decision: close the stuck intent.**\n')
    for files in ((),('9'*12,)):
        for f in files:ledger.ensure_dir(ledger.Settings(env).intents);(ledger.Settings(env).intents/f'{f}.json').write_bytes(b'x')
        cp=tool('ledger.py','register',d,'--role','plan',env=e);assert cp.returncode==69 and 'missing'in cp.stderr and not (root/'ledger.jsonl').exists(),cp.stderr
        cp=tool('ledger.py','resolve','9'*12,'--user-decision','PLAN-REVIEW-LOG.md:1','--decision-log',log,env=e)
        assert cp.returncode==69 and 'missing'in cp.stderr and not (root/'ledger.jsonl').exists(),cp.stderr
    os.unlink(ledger.Settings(env).intents/f'{"9"*12}.json');(root/'ledger.jsonl').write_bytes(b'')   # the ledger as admission's first use leaves it
    for _ in range(2):tool('ledger.py','register',d,'--role','plan',env=e,check=0)
    recs=[r for r in ledger.Ledger(ledger.Settings(env)).read(writer=False)if r['kind']=='register']
    assert len(recs)==1 and recs[0]['token']==t and recs[0]['p']==hashlib.sha256(b'{"plan":1}\n').hexdigest()[:12]and recs[0]['c']==c
    tool('ledger.py','register',d,'--role','plan',env={**e,'SLURM_RESTART_COUNT':'1'},check=0)
    assert sum(1 for r in ledger.Ledger(ledger.Settings(env)).read(writer=False)if r['kind']=='register')==2
    assert tool('ledger.py','register',d,'--role','plan',env={k:v for k,v in e.items()if k!='SLURM_JOB_ID'}).returncode==64
    assert tool('ledger.py','register',d,'--role','plan',env={**e,'SLURM_JOB_NAME':'manual'}).returncode==64
    ok('register_idempotent_per_restart_register_and_resolve_never_create_a_missing_ledger')

HOLD=r'''
import sys,time,os;sys.path.insert(0,sys.argv[1]);import ledger
s=ledger.Settings(dict(os.environ));l=ledger.SessionLock(s,'holder test');l.acquire();open(sys.argv[2],'w').write('held');time.sleep(60)
'''
def test_lock(td):
    root,env,h=fresh(td,'lock');s=ledger.Settings(env);marker=td/'held'
    p=subprocess.Popen([sys.executable,'-B','-c',HOLD,str(ROOT/'tools'),str(marker)],env=env)
    for _ in range(400):
        if marker.exists():break
        time.sleep(0.02)
    ino=os.stat(s.lock_path).st_ino;t0=time.time()
    msg=refuses(75,ledger.SessionLock(ledger.Settings({**env,'C8_LOCK_WAIT':'0.3'}),'second').acquire)
    assert time.time()-t0>=0.3 and f'"pid": {p.pid}'in msg and 'holder test'in msg,msg
    cp=tool('ledger.py','check',env={**env,'C8_LOCK_WAIT':'0.2'});assert cp.returncode==0   # readers take no lock
    p.send_signal(signal.SIGKILL);p.wait();t0=time.time()
    with ledger.SessionLock(ledger.Settings(env),'third')as l:assert time.time()-t0<0.5
    assert s.lock_path.exists()and os.stat(s.lock_path).st_ino==ino and oct(s.lock_path.stat().st_mode&0o777)=='0o600'
    assert oct(s.lock_path.parent.stat().st_mode&0o777)=='0o700'
    # the lock is not passed to children (non-inheritable descriptor)
    with ledger.SessionLock(ledger.Settings(env),'parent')as l:
        child=subprocess.run(['sh','-c','ls /dev/fd'],capture_output=True,text=True).stdout.split()
        assert not os.get_inheritable(l.fd)
        held=subprocess.run([sys.executable,'-B','-c','import fcntl,os,sys\ntry:fcntl.flock(int(sys.argv[1]),fcntl.LOCK_EX|fcntl.LOCK_NB);print("inherited")\nexcept OSError:print("not inherited")',
                             str(l.fd)],capture_output=True,text=True,close_fds=False).stdout.strip()
        assert held=='not inherited',held   # the child has no such descriptor (EBADF), so it cannot hold or release the lock
    ok('session_lock_75_holder_line_sigkill_release_never_deleted_noninheritable')

def mountinfo(td,lines)->str:
    p=td/f'mi_{len(list(td.glob("mi_*")))}';p.write_text(''.join(l+'\n'for l in lines));return str(p)

def test_mount_and_settings(td):
    root,env,h=fresh(td,'mount');(root/'locks').mkdir(mode=0o700);lockf=root/'locks'/'c8d3.lock';lockf.touch()
    st=os.stat(lockf);dev=f'{os.major(st.st_dev)}:{os.minor(st.st_dev)}';real=os.path.realpath(root)
    other=f'{os.major(st.st_dev)+1}:{os.minor(st.st_dev)+7}'
    def mi(fstype,opts,devid=dev,mp=real):return f'262 30 {devid} / {mp} rw,nosuid,nodev shared:1 - {fstype} 10.22.101.123@o2ib:/expanse/scratch {opts}'
    saved=(ledger.MOUNTINFO,ledger.IS_LINUX,ledger.EXPANSE_ROOT)
    try:
        cases={'accept':mi('lustre','rw,checksum,flock,lruresize'),'localflock':mi('lustre','rw,localflock'),'noflock':mi('lustre','rw,noflock'),
               'noflockopt':mi('lustre','rw,checksum'),'nonlustre':mi('ext4','rw,flock'),'nodev':mi('lustre','rw,flock',devid=other)}
        for name,line in cases.items():
            ledger.MOUNTINFO=mountinfo(td,['22 1 0:21 / / rw - apfs /dev/disk1 rw',line])
            s=ledger.Settings({**env,'C8_SITE':'expanse'})
            if name=='accept':
                with ledger.SessionLock(s,'t'):pass
                assert ledger.mount_check(lockf)['fstype']=='lustre'
            else:
                msg=refuses(69,ledger.SessionLock(s,'t').acquire);assert real in msg or 'device'in msg
        ledger.MOUNTINFO=mountinfo(td,['22 1 0:21 / / rw - apfs /dev/disk1 rw']);refuses(69,ledger.SessionLock(ledger.Settings({**env,'C8_SITE':'expanse'}),'t').acquire)
        ledger.MOUNTINFO=str(td/'missing_mountinfo');refuses(69,ledger.mount_check,lockf)   # unreadable at the mount check
        ledger.IS_LINUX=False;ledger.Settings(env)                                           # unreadable off Linux: not Expanse
        ledger.IS_LINUX=True;refuses(64,ledger.Settings,env)                                  # unreadable on Linux refuses (64)
        ledger.IS_LINUX=False
        # Expanse detected from mountinfo (/expanse/lustre) or SLURM_CLUSTER_NAME, independently of C8_SITE
        exp=mi('lustre','rw,flock',mp='/expanse/lustre/scratch')
        ledger.MOUNTINFO=mountinfo(td,[exp,cases['accept']])
        for site in (None,'fake','symmetry'):
            e={k:v for k,v in env.items()if k!='C8_SITE'}
            if site:e['C8_SITE']=site
            refuses(64,ledger.Settings,e)
        refuses(64,ledger.Settings,{**env,'C8_SITE':'expanse'})        # C8_ROOT must resolve to EXPANSE_ROOT there
        ledger.EXPANSE_ROOT=real
        with ledger.SessionLock(ledger.Settings({**env,'C8_SITE':'expanse'}),'t'):pass   # the mount check runs and passes
        ledger.MOUNTINFO=mountinfo(td,[exp,cases['localflock']]);refuses(69,ledger.SessionLock(ledger.Settings({**env,'C8_SITE':'expanse'}),'t').acquire)
        ledger.MOUNTINFO=str(td/'missing_mountinfo')
        for site in (None,'fake'):
            e={k:v for k,v in env.items()if k!='C8_SITE'}
            if site:e['C8_SITE']=site
            refuses(64,ledger.Settings,{**e,'SLURM_CLUSTER_NAME':'expanse'})
        ledger.Settings({**env,'C8_SITE':'symmetry'})   # off symmetry (the Mac), C8_SITE=symmetry is accepted with any root (Amendment A1)
        refuses(64,ledger.Settings,{**env,'C8_LOCK':str(root/'other.lock')})
        refuses(64,ledger.Settings,{**env,'C8_LEDGER':str(root/'ledger2.jsonl')})
        ledger.Settings({**env,'C8_LOCK':str(root/'locks'/'c8d3.lock'),'C8_LEDGER':str(root/'ledger.jsonl')})
        refuses(64,ledger.Settings,{k:v for k,v in env.items()if k!='C8_ROOT'})
        refuses(64,ledger.Settings,{**env,'C8_SITE':'expanse','C8_TEST_HOOKS':'/x'})
        refuses(64,ledger.Settings,{**env,'C8_LOCK_WAIT':'-1'})
    finally:ledger.MOUNTINFO,ledger.IS_LINUX,ledger.EXPANSE_ROOT=saved
    ok('mount_check_lustre_flock_only_and_fail_closed_settings_site_detection')


# ----------------------------------------------------------------------------------------------------------------
# symmetry (Amendment A1, addendum L): the session lock on the NFS home, site detection and the lockprobe's mount step
NFS_HOME='172.16.4.228:/HPCunixhome'
NFS_OPTS=('rw,vers=3,rsize=32768,wsize=32768,namlen=255,hard,proto=tcp,timeo=600,retrans=2,sec=sys,mountaddr=172.16.4.228,'
          'mountvers=3,mountport=1234,mountproto=udp,local_lock=none,addr=172.16.4.228')   # symmetry's /home on mn003 (2026-10-05)
APFS='22 1 0:21 / / rw - apfs /dev/disk1 rw'
def nfs_line(mp,devid,fstype='nfs',opts=NFS_OPTS):return f'593 34 {devid} / {mp} rw,relatime shared:211 - {fstype} {NFS_HOME} {opts}'
def beegfs_line(mp,devid):return f'1235 34 {devid} / {mp} rw,nosuid,relatime shared:526 - beegfs beegfs_nodev rw,cfgFile=/etc/beegfs/beegfs-client.conf'

def test_mount_symmetry(td):
    """C8_SITE=symmetry (addendum L): the lock's mount must be NFS with local_lock=none and without nolock; symmetry's
    BeeGFS (tuneUseGlobalFileLocks = 0: flock() on the local node only) and every other case refuse (69). On a symmetry
    host (a BeeGFS mount at /mnt/beegfs, whatever C8_SITE says) the lock is SYMMETRY_LOCK_DIR/c8d3.lock, C8_LOCK may name
    only that, a lock directory on BeeGFS refuses, and a second acquisition in one process is refused (69) while the first
    holds the lock (a per-process POSIX lock on NFS); after a release, or a refused acquisition, a new one succeeds."""
    root,env,h=fresh(td,'msym');(root/'locks').mkdir(mode=0o700);lockf=root/'locks'/'c8d3.lock';lockf.touch()
    st=os.stat(lockf);dev=f'{os.major(st.st_dev)}:{os.minor(st.st_dev)}';real=os.path.realpath(root)
    saved=(ledger.MOUNTINFO,ledger.IS_LINUX,ledger.SYMMETRY_ROOT,ledger.SYMMETRY_LOCK_DIR)
    senv={**env,'C8_SITE':'symmetry'}
    try:
        # off symmetry (the Mac), C8_SITE=symmetry: the lock stays under C8_ROOT and the NFS rule applies
        ledger.MOUNTINFO=mountinfo(td,[APFS,nfs_line(real,dev)])
        s=ledger.Settings(senv);assert s.lock_path==Path(real)/'locks'/'c8d3.lock',s.lock_path
        with ledger.SessionLock(s,'t'):pass
        assert ledger.mount_check(lockf,'symmetry')['fstype']=='nfs'
        ledger.MOUNTINFO=mountinfo(td,[APFS,nfs_line(real,dev,fstype='nfs4',opts='rw,vers=4.2,hard,proto=tcp,local_lock=none,addr=172.16.4.228')])
        assert ledger.mount_check(lockf,'symmetry')['fstype']=='nfs4'
        refused={'beegfs_2026_10_05':beegfs_line(real,dev),'local_lock_flock':nfs_line(real,dev,opts=NFS_OPTS.replace('local_lock=none','local_lock=flock')),
                 'local_lock_all':nfs_line(real,dev,opts=NFS_OPTS.replace('local_lock=none','local_lock=all')),
                 'local_lock_absent':nfs_line(real,dev,opts=NFS_OPTS.replace(',local_lock=none','')),'nolock':nfs_line(real,dev,opts=NFS_OPTS+',nolock'),
                 'lustre':f'262 30 {dev} / {real} rw shared:1 - lustre 10.22.101.123@o2ib:/expanse/scratch rw,flock',
                 'ext4':f'262 30 {dev} / {real} rw shared:1 - ext4 /dev/sda1 rw','nodev':nfs_line(real,f'{os.major(st.st_dev)+1}:7')}
        for name,line in refused.items():
            ledger.MOUNTINFO=mountinfo(td,[APFS,line])
            msg=refuses(69,ledger.SessionLock(ledger.Settings(senv),'t').acquire)
            if name=='beegfs_2026_10_05':assert 'tuneUseGlobalFileLocks = 0'in msg and 'this node only'in msg and 'local_lock=none'in msg,msg
        ledger.MOUNTINFO=mountinfo(td,[APFS,nfs_line(real,dev)])
        refuses(64,ledger.mount_check,lockf,'fake')                                                      # no rule for another site
        with ledger.SessionLock(ledger.Settings(env),'t'):pass                                           # fake and unset sites skip the check
        refuses(69,ledger.SessionLock(ledger.Settings({**env,'C8_SITE':'expanse'}),'t').acquire)         # expanse's rule refuses NFS
        # a symmetry host: BeeGFS at /mnt/beegfs; C8_ROOT on BeeGFS, the lock on the NFS home (SYMMETRY_LOCK_DIR)
        home=td/'nfs_home_locks';home.mkdir(mode=0o700);hreal=os.path.realpath(home)
        sym=beegfs_line('/mnt/beegfs','0:66')
        ledger.MOUNTINFO=mountinfo(td,[sym,beegfs_line(real,dev),nfs_line(hreal,dev)])
        for site in (None,'fake','expanse'):
            e={k:v for k,v in env.items()if k!='C8_SITE'}
            if site:e['C8_SITE']=site
            msg=refuses(64,ledger.Settings,e);assert 'this host is symmetry'in msg,msg
        msg=refuses(64,ledger.Settings,senv);assert ledger.SYMMETRY_ROOT in msg   # C8_ROOT must resolve to SYMMETRY_ROOT there
        ledger.SYMMETRY_ROOT=real;ledger.SYMMETRY_LOCK_DIR=str(home)
        s=ledger.Settings(senv);assert s.lock_path==Path(hreal)/'c8d3.lock'and s.ledger_path==Path(real)/'ledger.jsonl',(s.lock_path,s.ledger_path)
        with ledger.SessionLock(s,'first'):
            msg=refuses(69,ledger.SessionLock(ledger.Settings(senv),'second').acquire);assert 'already held by this process'in msg,msg
        with ledger.SessionLock(ledger.Settings(senv),'third'):pass                                      # released: acquired again
        assert (home/'c8d3.lock').is_file()
        refuses(64,ledger.Settings,{**senv,'C8_LOCK':str(Path(real)/'locks'/'c8d3.lock')})              # the BeeGFS path is not the lock there
        ledger.Settings({**senv,'C8_LOCK':str(home/'c8d3.lock')})
        ledger.SYMMETRY_LOCK_DIR=str(root/'locks')                                                       # a lock directory on BeeGFS: refused
        refuses(69,ledger.SessionLock(ledger.Settings(senv),'t').acquire)
        ledger.SYMMETRY_LOCK_DIR=str(home)
        with ledger.SessionLock(ledger.Settings(senv),'after a refusal'):pass                            # a refused acquisition held nothing
        ledger.MOUNTINFO=mountinfo(td,[nfs_line('/mnt/beegfs','0:66'),nfs_line(real,dev)]);ledger.Settings(env)   # a non-BeeGFS /mnt/beegfs is not symmetry
        exp=f'262 30 0:67 / /expanse/lustre/scratch rw shared:1 - lustre 10.22.101.123@o2ib:/expanse/scratch rw,flock'
        ledger.MOUNTINFO=mountinfo(td,[sym,exp,nfs_line(real,dev)])
        for site in ('symmetry','expanse'):refuses(64,ledger.Settings,{**env,'C8_SITE':site})            # both sites at once: nothing done
        ledger.MOUNTINFO=mountinfo(td,[sym,nfs_line(hreal,dev)])
        refuses(64,ledger.Settings,{**senv,'SLURM_CLUSTER_NAME':'expanse'})
    finally:ledger.MOUNTINFO,ledger.IS_LINUX,ledger.SYMMETRY_ROOT,ledger.SYMMETRY_LOCK_DIR=saved
    ok('mount_check_symmetry_lock_on_nfs_home_beegfs_refused_one_holder_per_process_detection_fail_closed')

# ----------------------------------------------------------------------------------------------------------------
def rb_env(td,name):
    root,env,h=fresh(td,name);fake=Fake(path=None);fake.now=lambda:time.time()+h.off;budget.RUNNER=inprocess_runner(fake)
    log=root/'decisions'/'PLAN-REVIEW-LOG.md';log.parent.mkdir();log.write_text('# log\n\n- **User decision (2026-10-04): close the blocked repair with a 5 SU hold.**\n')
    return root,env,h,fake,log

class A:
    def __init__(self,**k):self.__dict__.update(dict(reason=None,user_decision=None,hold_su=None,hold_line=None,decision_log=None));self.__dict__.update(k)

def setup_intents(s,lock,tokens):
    led=ledger.Ledger(s,lock,create=True);led.read(writer=True);pos={}
    for t in tokens:
        p=intent(t);ino,off,n=led.append(p);led.write_intent_file(p,ino,off,n);pos[t]=(off,n)
    return led,pos

def test_rebuild(td):
    root,env,h,fake,log=rb_env(td,'rb1');s=ledger.Settings(env)
    run=root/'runs'/'camp1';run.mkdir(parents=True);c=ledger.dir_sha12(run)
    with ledger.SessionLock(s,'t')as lock:
        led,pos=setup_intents(s,lock,['a'*12,'b'*12])
        led.append(P('submit','a'*12,job_id='9001'));led.append(P('register','b'*12,job_id='9002',dir=str(run),c=c,p='1'*12))
        led.append(P('resolution','b'*12,rule='terminal',charge_su=0.0));led.rename_resolved('b'*12)
    old=s.ledger_path.read_bytes();lines=ledger.split_lines(old)
    # damage: the submit record (token readable elsewhere in it), and A's intent line inside its token (matched by byte range)
    bad=bytearray(old);so=lines[2][0];bad[so+40]^=1
    io=lines[0][0];k=old.index(b'"token":"'+b'a'*12,io)+10;bad[k]=ord('x')
    s.ledger_path.write_bytes(bytes(bad))
    fake.add_job(f'c8d3-lane-{c}-{"c"*12}',state='RUNNING',partition='compute',comment=f'c8d3:{c}:{"1"*12}:{"c"*12}',hold_start=True)
    fake.add_job(f'c8d3-val-{c}-{"a"*12}',state='RUNNING',partition='shared',comment=f'c8d3:{c}:{"1"*12}:{"a"*12}',jid='9001')   # A's job (its submit record is damaged)
    refuses(69,ledger.Ledger(s).read,writer=False)
    with ledger.SessionLock(s,'t')as lock:refuses(69,ledger.Ledger(s,lock).read,writer=True)
    refuses(64,ledger.cmd_rebuild,A(),env)                                     # --reason is mandatory
    ledger.cmd_rebuild(A(reason='byte flips in a test'),env)
    new=s.ledger_path.read_bytes();sc=ledger.Scan(new);assert sc.status=='clean'
    kept=[l for i,(o,l) in enumerate(lines)if i not in(0,2)];nl=ledger.split_lines(new)
    assert [l for _,l in nl[:len(kept)]]==kept,'every valid record of the old file, in order, byte-identical'
    recs=[r for _,_,r in sc.records];added=recs[len(kept):]
    assert any(r['kind']=='intent'and r['token']=='a'*12 and r['by']=='rebuild'for r in added),'A restored from its file'
    ad=[r for r in added if r['kind']=='adopted'];assert {r['job_id']for r in ad}>={'9001'},ad
    a9=[r for r in ad if r['job_id']=='9001'][0];assert a9['token']=='a'*12 and a9['by']=='rebuild'and a9['dir']==str(run),a9   # the lost submit record's job, re-adopted
    assert any(r['kind']=='adopted'and r['token']=='c'*12 and r['dir']==str(run)for r in added),'unrecorded scheduler job adopted, dir from plan files'
    ev=list(s.evidence.glob('invalid.*'));assert len(ev)==2 and {e.read_bytes()for e in ev}=={bytes(bad[lines[0][0]:lines[0][0]+len(lines[0][1])]),bytes(bad[so:so+len(lines[2][1])])}
    assert list(s.evidence.glob('ledger.*.jsonl'))[0].read_bytes()==bytes(bad)
    summ=json.loads(sorted(s.evidence.glob('rebuild.*.json'))[-1].read_text());assert {m['by']for m in summ['segments_matched']}=={'byte_range','token'}
    its=states(s);its_a=its['a'*12];assert its_a.unresolved and not its['b'*12].unresolved
    ok('rebuild_keeps_valid_in_order_restores_matches_by_range_and_token_adopts')

def test_rebuild_blocks(td):
    # (1) a segment with no readable token and no recorded range blocks; nothing is written but evidence
    root,env,h,fake,log=rb_env(td,'rb2');s=ledger.Settings(env)
    with ledger.SessionLock(s,'t')as lock:led,pos=setup_intents(s,lock,['d'*12,'e'*12])
    data=s.ledger_path.read_bytes();L=ledger.split_lines(data)
    damaged=bytearray(data);o,n=pos['e'*12]
    seg=bytes(damaged[o:o+n]).replace(b'e'*12,b'#'*12);damaged[o:o+n]=seg      # E's tokens unreadable
    os.unlink(s.intents/f'{"e"*12}.json')                                       # and its file deleted: both copies lost
    s.ledger_path.write_bytes(bytes(damaged));files_before=sorted(p.name for p in root.rglob('*')if 'ledger_evidence'not in str(p))
    for reason in ('please','force it'):
        msg=refuses(69,ledger.cmd_rebuild,A(reason=reason),env);assert 'unmatched segment'in msg
    assert s.ledger_path.read_bytes()==bytes(damaged)and sorted(p.name for p in root.rglob('*')if 'ledger_evidence'not in str(p))==files_before
    # (2) the lost-newline merge: a valid record (newline lost) + E's record without readable token: only frame splitting finds it
    merged=data[:L[0][0]+len(L[0][1])-1]+seg
    s.ledger_path.write_bytes(merged);msg=refuses(69,ledger.cmd_rebuild,A(reason='merge'),env);assert 'unmatched segment'in msg
    segs=ledger.segments(0,merged);assert len(segs)==2 and ledger.readable_tokens(segs[0][1])=={'d'*12}and not ledger.readable_tokens(segs[1][1])
    # the user's decision: refused before G after the block, then accepted, recording REF and holding S SU for good
    d=A(reason='merge',user_decision='PLAN-REVIEW-LOG.md:3',hold_su=5.0,hold_line='dev',decision_log=str(log))
    refuses(64,ledger.cmd_rebuild,d,env)
    refuses(64,ledger.cmd_rebuild,A(reason='x',user_decision='PLAN-REVIEW-LOG.md:3',decision_log=str(log)),env)             # without --hold-su
    refuses(64,ledger.cmd_rebuild,A(reason='x',user_decision='PLAN-REVIEW-LOG.md:1',hold_su=1,hold_line='dev',decision_log=str(log)),env)  # not a decision line
    refuses(64,ledger.cmd_rebuild,A(reason='x',user_decision='other.md:3',hold_su=1,hold_line='dev',decision_log=str(log)),env)
    h.advance(ledger.INTENT_GRACE+1)
    ledger.cmd_rebuild(d,env);recs=ledger.Ledger(s).read(writer=False)
    hold=[r for r in recs if r['kind']=='intent'and r.get('hold')];assert len(hold)==1 and hold[0]['reservation_su']==5.0 and hold[0]['decision']['sha256']
    its=states(s);ht=hold[0]['token'];assert its[ht].hold and its[ht].unresolved and its[ht].floor_su()==5.0 and (s.intents/f'{ht}.json').exists()
    assert ledger.Scan(s.ledger_path.read_bytes()).status=='clean'
    ok('rebuild_blocks_unmatched_and_merged_segments_user_decision_after_G_hold')

def test_rebuild_missing(td):
    root,env,h,fake,log=rb_env(td,'rb3');s=ledger.Settings(env)
    with ledger.SessionLock(s,'t')as lock:
        led,pos=setup_intents(s,lock,['1'*12,'2'*12,'3'*12])
        led.append(P('resolution','3'*12,rule='terminal',charge_su=1.0));led.rename_resolved('3'*12)
    os.unlink(s.ledger_path)
    for _ in range(2):refuses(69,ledger.cmd_rebuild,A(reason='lost'),env)       # every visible T has a file: still blocked
    assert not s.ledger_path.exists()
    d=A(reason='lost',user_decision='PLAN-REVIEW-LOG.md:3',hold_su=0.0,hold_line='dev',decision_log=str(log))
    refuses(64,ledger.cmd_rebuild,d,env);h.advance(ledger.INTENT_GRACE+1);ledger.cmd_rebuild(d,env)
    its=states(s)
    assert all(its[t].unresolved for t in ('1'*12,'2'*12,'3'*12)),'every intent restored; resolved/ ones come back unresolved'
    # missing ledger + an unreadable intent file, and + a scheduler job whose token has no file
    root,env,h,fake,log=rb_env(td,'rb4');s=ledger.Settings(env)
    with ledger.SessionLock(s,'t')as lock:setup_intents(s,lock,['4'*12])
    os.unlink(s.ledger_path);(s.intents/f'{"4"*12}.json').write_bytes(b'unreadable')
    fake.add_job(f'c8d3-raw-{"a"*12}-{"5"*12}',comment=f'c8d3:{"a"*12}:{"0"*12}:{"5"*12}')
    msg=refuses(69,ledger.cmd_rebuild,A(reason='lost'),env);assert 'cannot be read'in msg and '5'*12 in msg
    h.advance(ledger.INTENT_GRACE+1)
    ledger.cmd_rebuild(A(reason='lost',user_decision='PLAN-REVIEW-LOG.md:3',hold_su=2.0,hold_line='pilot',decision_log=str(log)),env)
    assert not (s.intents/f'{"4"*12}.json').exists()and list(s.evidence.glob('unreadable_intent.*'))
    recs=ledger.Ledger(s).read(writer=False);assert any(r['kind']=='adopted'and r['token']=='5'*12 for r in recs)
    states(s)
    ok('rebuild_missing_ledger_always_blocks_then_user_decision_restores')

def test_rebuild_unattributable_and_sigkill(td):
    root,env,h,fake,log=rb_env(td,'rb5');s=ledger.Settings(env)
    with ledger.SessionLock(s,'t')as lock:setup_intents(s,lock,['6'*12])
    fake.add_job('c8d3-not a name',comment=None);fake.add_job(f'c8d3-raw-{"a"*12}-{"7"*12}',comment=f'c8d3:{"b"*12}:{"0"*12}:{"7"*12}')
    ledger.cmd_rebuild(A(reason='host check: manual test job'),env)
    recs=ledger.Ledger(s).read(writer=False);un=[r for r in recs if r['kind']=='adopted'and r.get('attribution',1)is None]
    assert len(un)==2 and all(r['reason']=='host check: manual test job'for r in un)
    # SIGKILL before and after the rename (subprocess with file hooks)
    hooks=root/'hooks.json';before=s.ledger_path.read_bytes()
    st=root/'fake.json';fk=Fake(path=str(st));e={**env,'C8_TEST_HOOKS':str(hooks),'FAKE_SLURM_STATE':str(st),'PATH':f'{install_bin(td)}:{os.environ["PATH"]}'}
    hooks.write_text(json.dumps({'kill_at':{'rebuild_before_rename':1}}))
    cp=tool('ledger.py','rebuild','--reason','kill test',env=e);assert cp.returncode==-9,cp.stderr
    assert s.ledger_path.read_bytes()==before and list(root.glob('ledger.jsonl.tmp.*'))
    hooks.write_text(json.dumps({'kill_at':{'rebuild_after_rename':1}}))
    cp=tool('ledger.py','rebuild','--reason','kill test',env=e);assert cp.returncode==-9 and not list(root.glob('ledger.jsonl.tmp.*'))
    after=s.ledger_path.read_bytes();assert ledger.Scan(after).status=='clean'and after.startswith(before)
    hooks.write_text('{}');tool('ledger.py','rebuild','--reason','again',env=e,check=0)
    ok('rebuild_unattributable_recorded_with_reason_atomic_under_sigkill')

def report_or_block(env):
    """budget.py's view: ('blocked', msg) on its 69 refusal, else ('ok', report)."""
    try:return 'ok',budget.report(env)
    except Refuse as r:
        assert r.code==69,(r.code,str(r));return 'blocked',str(r)

def test_rebuild_resolved_intent_both_copies_lost(td):
    """A RESOLVED intent loses both copies (its line damaged, its resolved/ file unreadable): rebuild blocks; the user's
    decision covers the token, so its surviving resolution record no longer blocks admission or budget.py for good."""
    root,env,h,fake,log=rb_env(td,'rbo1');s=ledger.Settings(env);t='a'*12
    with ledger.SessionLock(s,'t')as lock:
        led,pos=setup_intents(s,lock,[t,'b'*12]);led.append(P('resolution',t,rule='terminal',charge_su=0.5));led.rename_resolved(t)
    data=bytearray(s.ledger_path.read_bytes());o,n=pos[t];data[o+30]^=1;s.ledger_path.write_bytes(bytes(data))
    (s.resolved/f'{t}.json').write_bytes(b'garbage')
    msg=refuses(69,ledger.cmd_rebuild,A(reason='x'),env);assert 'unmatched segment'in msg and 'cannot be read'in msg
    assert report_or_block(env)[0]=='blocked'
    d=A(reason='x',user_decision='PLAN-REVIEW-LOG.md:3',hold_su=8.0,hold_line='dev',decision_log=str(log))
    h.advance(ledger.INTENT_GRACE+1);ledger.cmd_rebuild(d,env)
    st,r=report_or_block(env);assert st=='ok'and list(r['holds'].values())==[8.0],r
    hold=[x for x in ledger.Ledger(s).read(writer=False)if x['kind']=='intent'and x.get('hold')][0];assert t in hold['covers']
    assert not (s.resolved/f'{t}.json').exists()and list(s.evidence.glob(f'unreadable_intent.*.{t}.json'))
    assert any(x['kind']=='resolution'and x['token']==t for x in ledger.Ledger(s).read(writer=False))   # the record is kept; the hold covers it
    states(s);ledger.cmd_rebuild(A(reason='again'),env);refuses(64,ledger.cmd_rebuild,d,env)       # no block left: the decision is not needed
    # the same with nothing damaged but both copies cleanly gone: only resolving records remain for the token
    root,env,h,fake,log=rb_env(td,'rbo2');s=ledger.Settings(env)
    with ledger.SessionLock(s,'t')as lock:
        led,pos=setup_intents(s,lock,[t]);led.append(P('not_submitted',t,launched=False,ambiguous=False,reason='x'));led.rename_resolved(t)
    keep=[l for _,l in ledger.split_lines(s.ledger_path.read_bytes())if b'"kind":"intent"'not in l];s.ledger_path.write_bytes(b''.join(keep))
    os.unlink(s.resolved/f'{t}.json')
    refuses(69,states,s);msg=refuses(69,ledger.cmd_rebuild,A(reason='x'),env);assert 'resolving or not_submitted records but no intent copy'in msg
    h.advance(ledger.INTENT_GRACE+1);ledger.cmd_rebuild(A(reason='x',user_decision='PLAN-REVIEW-LOG.md:3',hold_su=0.0,hold_line='dev',decision_log=str(log)),env)
    assert t not in states(s)and report_or_block(env)[0]=='ok'
    ok('rebuild_resolved_intent_both_copies_lost_blocks_then_decision_covers_it')

CRASH_KILLS=('rebuild_evidence_written','rebuild_before_rename','rebuild_after_rename','rebuild_move','rebuild_files_done')
CRASH_FAULTS=({'rebuild_tmp':{'errno':errno.EDQUOT}},{'rebuild_tmp:create':{'errno':errno.EDQUOT}},{'rebuild_tmp':{'short':'half'}},
              {'rebuild_rename':{'errno':errno.EIO}},{'rebuild_dir':{'errno':errno.EIO}},{'rebuild_move':{'errno':errno.EIO}},
              {'evidence:create':{'errno':errno.EDQUOT}})
def test_rebuild_decision_crash_every_step(td):
    """`rebuild --user-decision` killed at every step, or failing a write (EDQUOT at create, a short write, EIO on a
    rename or a directory fsync): budget.py (and so admission) is either still blocked, or sees the decision's hold.
    Never a lifted block without the hold; a re-run then completes."""
    cases=[('kill',k)for k in CRASH_KILLS]+[('fault',f)for f in CRASH_FAULTS]
    for missing in (False,True):
        for i,(how,what) in enumerate(cases):
            root,env,h,fake,log=rb_env(td,f'rbc{int(missing)}_{i}');s=ledger.Settings(env);x='f'*12
            with ledger.SessionLock(s,'t')as lock:setup_intents(s,lock,['a'*12])
            (s.intents/f'{x}.json').write_bytes(b'{"rec":{"kind":"intent","tok')    # unreadable, no ledger copy
            if missing:os.unlink(s.ledger_path)
            refuses(69,ledger.cmd_rebuild,A(reason='block'),env);assert report_or_block(env)[0]=='blocked'
            h.advance(ledger.INTENT_GRACE+1)
            d=A(reason='decided',user_decision='PLAN-REVIEW-LOG.md:3',hold_su=3000.0,hold_line='dev',decision_log=str(log))
            if how=='kill':h.kill.add(what)
            else:h.faults.update(what)
            try:ledger.cmd_rebuild(d,env);rc=0
            except Killed:rc=-9
            except Refuse as r:rc=r.code
            h.kill.clear();h.faults.clear()
            st,r=report_or_block(env)
            assert st=='blocked'or list(r['holds'].values())==[3000.0],(missing,how,what,rc,st,r)   # never admitted without the hold
            if how=='kill'and what in('rebuild_evidence_written','rebuild_before_rename'):assert st=='blocked',(missing,what)
            if st=='blocked':ledger.cmd_rebuild(d,env)
            else:ledger.cmd_rebuild(A(reason='complete'),env)
            st,r=report_or_block(env);assert st=='ok'and list(r['holds'].values())==[3000.0],(missing,how,what,r)
            assert not (s.intents/f'{x}.json').exists()and (s.intents/f'{"a"*12}.json').exists()and ledger.Scan(s.ledger_path.read_bytes()).status=='clean'
            assert len([y for y in ledger.Ledger(s).read(writer=False)if y['kind']=='intent'and y.get('hold')])==1
    ok('rebuild_user_decision_killed_or_failing_at_every_step_never_lifts_the_block_without_the_hold',cases=2*len(cases))

def test_block_clock(td):
    """G for --user-decision runs from the first record of the CURRENT blocking conditions, never from an older block of
    a condition that has cleared."""
    root,env,h,fake,log=rb_env(td,'clk');s=ledger.Settings(env);t='a'*12
    with ledger.SessionLock(s,'t')as lock:setup_intents(s,lock,[t])
    f=s.intents/f'{t}.json';good=f.read_bytes();s.ledger_path.write_bytes(b'');f.write_bytes(b'garbage')
    refuses(69,ledger.cmd_rebuild,A(reason='first block'),env)                       # block 1: unreadable file, no ledger copy
    f.write_bytes(good);h.advance(86400)                                             # the condition clears without a rebuild
    s.ledger_path.write_bytes(s.ledger_path.read_bytes()+b'garbage without token\n'+ledger.frame(P('annotation','c'*12,about='x')))
    refuses(69,ledger.cmd_rebuild,A(reason='new block'),env)                         # block 2: an unmatched segment
    d=A(reason='new block',user_decision='PLAN-REVIEW-LOG.md:3',hold_su=10.0,hold_line='dev',decision_log=str(log))
    msg=refuses(64,ledger.cmd_rebuild,d,env);assert 'no earlier than G'in msg            # not accepted at once on block 1's clock
    h.advance(ledger.INTENT_GRACE-10);refuses(64,ledger.cmd_rebuild,d,env)
    # a further condition appears: the clock starts again for it
    f.write_bytes(b'garbage again');s.ledger_path.write_bytes(b'garbage without token\n'+ledger.frame(P('annotation','c'*12,about='x')))
    h.advance(20);msg=refuses(64,ledger.cmd_rebuild,d,env);assert 'recorded now'in msg
    h.advance(ledger.INTENT_GRACE+1);ledger.cmd_rebuild(d,env);assert report_or_block(env)[0]=='ok'
    ok('block_clock_g_from_the_current_conditions_not_a_stale_block')

def test_decision_ref_bytes(td):
    log=td/'dref'/'PLAN-REVIEW-LOG.md';log.parent.mkdir()
    raw3='- **User decision (2026-10-04): hold 5 SU. é**'.encode()
    log.write_bytes(b'# log\n- a note \x0c with a form feed and \xe2\x80\xa8 a line separator\n'+raw3+b'\n')
    d=ledger.decision_ref('PLAN-REVIEW-LOG.md:3',log)   # numbered by b'\n' only (str.splitlines would make this line 5)
    assert d['line']==3 and d['sha256']==hashlib.sha256(raw3).hexdigest()and d['text']==raw3.decode()
    for ref in ('PLAN-REVIEW-LOG.md:2','PLAN-REVIEW-LOG.md:4','PLAN-REVIEW-LOG.md:0'):refuses(64,ledger.decision_ref,ref,log)
    log.write_bytes(b'\xff\xfe decision with bad bytes\n');d=ledger.decision_ref('PLAN-REVIEW-LOG.md:1',log)
    assert d['sha256']==hashlib.sha256(b'\xff\xfe decision with bad bytes').hexdigest()
    ok('decision_ref_lines_by_newline_bytes_sha256_of_the_raw_line')

PROBE_WRAP=r"""
import errno,fcntl,os,sys;sys.path.insert(0,sys.argv[1]);import ledger
mode=sys.argv[2]
if mode.startswith('mountinfo='):ledger.MOUNTINFO=mode.split('=',1)[1]
elif mode=='noflock':
    def bad(fd,op):raise OSError(errno.EOPNOTSUPP,os.strerror(errno.EOPNOTSUPP))
    fcntl.flock=bad
elif mode=='early':   # a lock that grants too early: the first try of (i)'s blocking wait succeeds while the login side holds
    real=fcntl.flock;n=[0]
    def early(fd,op):
        if op==fcntl.LOCK_EX|fcntl.LOCK_NB:
            n[0]+=1
            if n[0]==4:return None
        return real(fd,op)
    fcntl.flock=early
sys.exit(ledger.main(sys.argv[3:]))
"""
def probe_pair(root,env,m,out,job_mode='plain',job_env=None,timeout=60,interval='0.05'):
    base=['lockprobe','--probe',str(root/'locks'/'probe.lock'),'--markers',str(m),'--interval',interval,'--wait','20']
    job=subprocess.Popen([sys.executable,'-B','-c',PROBE_WRAP,str(ROOT/'tools'),job_mode,*base,'--side','job','--out',str(out)+'_job.json'],
                         env={**env,**(job_env or{})},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    login=subprocess.run([sys.executable,'-B',str(ROOT/'tools/ledger.py'),*base,'--side','login','--out',str(out)+'_login.json'],env=env,capture_output=True,text=True,timeout=timeout)
    jo,je=job.communicate(timeout=timeout)
    return (job.returncode,json.loads(Path(str(out)+'_job.json').read_text()),je),(login.returncode,json.loads(Path(str(out)+'_login.json').read_text()),login.stderr)

def test_lockprobe_failures(td):
    """A lock or mount failure on one side is recorded by BOTH sides as that failure (the host STOPS), never as an
    expired handshake; a repeat with the same --markers runs in its own directory and passes."""
    root,env,h=fresh(td,'probef');m=td/'markers_f';(root/'locks').mkdir(mode=0o700);(root/'locks'/'probe.lock').touch()
    st=os.stat(root/'locks'/'probe.lock');dev=f'{os.major(st.st_dev)}:{os.minor(st.st_dev)}';real=os.path.realpath(root)
    mi=td/'mi_probe';mi.write_text(f'262 30 {dev} / {real} rw,nosuid shared:1 - lustre 10.22.101.123@o2ib:/expanse/scratch rw,checksum,localflock\n')
    (jr,jres,je),(lr,lres,le)=probe_pair(root,env,m,td/'pf_mount',job_mode=f'mountinfo={mi}',job_env={'C8_SITE':'expanse'})
    assert jr==69 and lr==69,(je,le)
    assert jres['steps']['iii_mount']['pass']is False and jres['steps']['iii_mount']['mount_check_ok']is False and 'localflock'in jres['steps']['iii_mount']['error']
    assert 'STOPS'in jres['verdict']and 'expired'not in json.dumps(jres)
    assert lres['peer_failed']['step']=='iii_mount'and 'STOPS'in lres['verdict']and 'expired'not in json.dumps(lres),lres
    (jr,jres,je),(lr,lres,le)=probe_pair(root,env,m,td/'pf_flock',job_mode='noflock')
    assert jr==69 and lr==69 and jres['steps']['i_login_holds']['errno']==errno.EOPNOTSUPP and lres['peer_failed']['step']=='i_login_holds',(jres,lres)
    assert 'STOPS'in lres['verdict']and 'expired'not in lres['verdict']
    for k in range(2):   # repeats with the same --markers directory: each run has its own subdirectory and passes
        (jr,jres,je),(lr,lres,le)=probe_pair(root,env,m,td/f'pf_ok{k}')
        assert jr==0 and lr==0 and jres['pass']and lres['pass']and jres['run_dir']==lres['run_dir'],(je,le)
    assert len([d for d in m.iterdir()if d.is_dir()])==4
    ok('lockprobe_lock_and_mount_failures_reach_the_peer_and_repeats_use_fresh_marker_dirs')

def test_lockprobe_symmetry(td):
    """J-LOCK-0-sym's mount step (iii) under C8_SITE=symmetry (addendum L): a probe file on symmetry's BeeGFS
    (tuneUseGlobalFileLocks = 0) fails the job side's mount check, both sides exit 69 and say the host STOPS (on one
    machine flock() is still exclusive, so (i) and (ii) pass here; across nodes they would not); on the NFS home
    (local_lock=none) the probe passes and records the mount line."""
    root,env,h=fresh(td,'probesym');m=td/'markers_sym';(root/'locks').mkdir(mode=0o700);(root/'locks'/'probe.lock').touch()
    st=os.stat(root/'locks'/'probe.lock');dev=f'{os.major(st.st_dev)}:{os.minor(st.st_dev)}';real=os.path.realpath(root)
    off=td/'mi_probe_beegfs';off.write_text(beegfs_line(real,dev)+'\n');on=td/'mi_probe_nfs';on.write_text(nfs_line(real,dev)+'\n')
    (jr,jres,je),(lr,lres,le)=probe_pair(root,env,m,td/'ps_off',job_mode=f'mountinfo={off}',job_env={'C8_SITE':'symmetry'})
    assert jr==69 and lr==69,(je,le)
    assert jres['steps']['i_login_holds']['pass']and jres['steps']['iii_mount']['pass']is False and 'tuneUseGlobalFileLocks = 0'in jres['steps']['iii_mount']['error'],jres
    assert lres['peer_failed']['step']=='iii_mount'and 'STOPS'in lres['verdict']and 'expired'not in json.dumps(lres),lres
    (jr,jres,je),(lr,lres,le)=probe_pair(root,env,m,td/'ps_on',job_mode=f'mountinfo={on}',job_env={'C8_SITE':'symmetry'})
    assert jr==0 and lr==0,(je,le)
    assert jres['site']['site']=='symmetry'and jres['site']['mount_check_ok']and 'local_lock=none'in jres['site']['mount_check']and 'beegfs_version'in jres['site'],jres['site']
    ok('lockprobe_symmetry_mount_step_refuses_beegfs_and_passes_on_the_nfs_home')

def test_lockprobe_early_grant(td):
    """J-LOCK-0 (i)/(ii) "returns only after the recorded release" is checked causally: the holder keeps the lock for
    --interval after the waiter's NB-failed marker and writes its release marker before it unlocks, so an acquisition
    that returns before the release finds no marker. A flock that grants early fails the step, although the timestamps
    alone (1 s of skew) would have passed it."""
    root,env,h=fresh(td,'probe_early');m=td/'markers_e';(root/'locks').mkdir(mode=0o700)
    (jr,jres,je),(lr,lres,le)=probe_pair(root,env,m,td/'pe',job_mode='early',interval='0.3')
    st=jres['steps']['i_login_holds']
    assert jr==69 and st['pass']is False and st['release_marker_at_acquisition']is False and st['nb']==[False]*3,(jr,jres)
    assert st['acquired']>=st['released']-1.0,'control: the timestamp comparison alone would have accepted the early grant'
    assert 'STOPS'in jres['verdict']and 'expired'not in jres['verdict']
    (jr,jres,je),(lr,lres,le)=probe_pair(root,env,m,td/'pe_ok',interval='0.3')   # a correct lock passes, both sides
    assert jr==0 and lr==0 and jres['steps']['i_login_holds']['release_marker_at_acquisition']is True and lres['steps']['ii_job_holds']['release_marker_at_acquisition']is True,(je,le)
    assert lres['steps']['ii_job_holds']['acquired']-lres['steps']['ii_job_holds']['released']>-1.0
    ok('lockprobe_release_checked_causally_an_early_grant_fails')

def test_lock_acquisition_check_failure_releases(td):
    """A failed fsync check at acquisition (69) closes the descriptor: the next SessionLock in the same process takes the
    lock at once instead of waiting C8_LOCK_WAIT and exiting 75."""
    root,env,h=fresh(td,'lockcheck');s=ledger.Settings(env)
    h.faults['lock_fsync:acquisition']={'errno':errno.EIO}
    try:
        with ledger.SessionLock(s,'first'):raise AssertionError('entered after a failed acquisition check')
    except Refuse as r:assert r.code==69 and 'fsync check'in str(r),r
    t0=time.time()
    with ledger.SessionLock(ledger.Settings({**env,'C8_LOCK_WAIT':'2'}),'second')as l:assert time.time()-t0<1.0 and l.fd is not None
    ev=[(e[1],e[2].get('command'))for e in h.log if e[0]=='event'and e[1]in('lock_acquired','lock_released')]
    assert ev[:2]==[('lock_acquired','first'),('lock_released','first')],ev
    ok('lock_acquisition_check_failure_releases_the_lock_in_process')

def test_rebuild_unreadable_file_and_os_errors(td):
    """An intent file the OS cannot read (EACCES) is re-written by rebuild from its valid ledger copy, with the error kept
    as evidence; a stale temporary that cannot be removed is 74; a stray OSError in a tool's main is 69 or 74 with the
    path, never a traceback."""
    import contextlib,io
    root,env,h,fake,log=rb_env(td,'rb_eacces');s=ledger.Settings(env);T='d'*12
    with ledger.SessionLock(s,'t')as lock:setup_intents(s,lock,[T])
    f=s.intents/f'{T}.json';good=f.read_bytes();f.chmod(0)
    if os.access(f,os.R_OK):f.chmod(0o600);ok('rebuild_unreadable_file_skipped_as_root');return
    def main(fn,argv,e=env):
        err=io.StringIO()
        with contextlib.redirect_stderr(err),contextlib.redirect_stdout(io.StringIO()):rc=fn(argv,e)
        return rc,err.getvalue()
    rc,err=main(ledger.main,['rebuild','--reason','an unreadable intent file (EACCES)']);assert rc==0,err
    assert os.access(f,os.R_OK)and ledger.unframe(f.read_bytes())['token']==T and states(s)[T].unresolved
    evf=list(s.evidence.glob(f'intentfile.*.{T}'));assert len(evf)==1 and b'unreadable intent file'in evf[0].read_bytes(),evf
    stale=root/'ledger.jsonl.tmp.999';stale.mkdir();(stale/'x').write_text('x')   # cannot be unlinked (a directory)
    rc,err=main(ledger.main,['rebuild','--reason','stale temporary']);assert rc==74 and str(stale)in err and 'Traceback'not in err,(rc,err)
    shutil.rmtree(stale)
    s.intents.chmod(0)   # an unreadable intents/ directory: readers and writers end in 69 with the path
    try:
        for fn,argv in ((ledger.main,['check']),(budget.main,[]),(ledger.main,['rebuild','--reason','x'])):
            rc,err=main(fn,argv);assert rc==69 and str(s.intents)in err and 'Traceback'not in err,(argv,rc,err)
    finally:s.intents.chmod(0o700)
    ok('rebuild_rewrites_an_unreadable_intent_file_os_errors_map_to_69_74')

def install_bin(td):
    from fake_slurm.core import install
    return install(td/'fakebin')

def test_lockprobe(td):
    root,env,h=fresh(td,'probe');m=td/'markers';out=td/'probe'
    base=[sys.executable,'-B',str(ROOT/'tools/ledger.py'),'lockprobe','--probe',str(root/'locks'/'probe.lock'),'--markers',str(m),'--interval','0.05','--wait','30']
    job=subprocess.Popen(base+['--side','job','--out',str(out)+'_job.json'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    for _ in range(400):   # the job side's ready marker, in its run directory MARKERS/<run id>/ (J-LOCK-0's order)
        if any(m.glob('*/ready')):break
        time.sleep(0.02)
    rds=[r.parent for r in m.glob('*/ready')];assert len(rds)==1 and not (rds[0]/'login_start').exists(),rds
    login=subprocess.run(base+['--side','login','--out',str(out)+'_login.json'],env=env,capture_output=True,text=True,timeout=60)
    jo,je=job.communicate(timeout=60)
    assert login.returncode==0 and job.returncode==0,(login.stderr,je)
    rj=json.loads(Path(str(out)+'_job.json').read_text());rl=json.loads(Path(str(out)+'_login.json').read_text())
    assert rj['pass']and rl['pass']and set(rl['steps'])=={'i_login_holds','ii_job_holds','iii_mount','iv_sigkill'}
    assert rj['run_dir']==rl['run_dir']==str(rds[0])
    # the handshake's order, from the markers' own times (one host, one clock): each side acts only after the other's step
    order=['ready','login_start','login_holds','job_nb_failed','login_released','job_i_done','login_i_ack','job_holds','login_nb_failed','job_released',
           'login_ii_done','child_holds','login_nb_failed_iv','child_killed','login_iv_done']
    ts=[json.loads((rds[0]/n).read_text())['t']for n in order];assert ts==sorted(ts),list(zip(order,ts))
    assert rl['steps']['iv_sigkill']['acquired']-rl['steps']['iv_sigkill']['killed']<5 and rl['steps']['ii_job_holds']['nb']==[False]*3
    assert tool('ledger.py','lockprobe','--probe',root/'locks'/'c8d3.lock','--side','job','--markers',m,env=env).returncode==64
    ok('lockprobe_ordered_handshake_two_processes_sigkilled_holder')

def test_lockprobe_login_waits_for_running(td):
    """HD15 and J-LOCK-0: with --job ID the login side starts only once `squeue` shows the job RUNNING and its ready
    marker exists. While the job is PENDING no `login_start` is written, although the marker is there; the squeue runs
    in the scheduler environment, so an exported SQUEUE_STATES cannot hide the RUNNING job. A job that never runs is a
    queue wait (69, not a lock result) and the login side writes nothing."""
    root,env,h=fresh(td,'probe_run');m=td/'markers_run';(root/'locks').mkdir(mode=0o700)
    fake=Fake(str(td/'fake_probe.json'));nm='c8d3-drill_lockprobe-'+'a'*12+'-'+'b'*12
    jid=fake.add_job(nm,state='PENDING',partition='debug',jid='7001')[0];idle=fake.add_job(nm.replace('b'*12,'c'*12),state='PENDING',partition='debug',jid='7002')[0]
    hk=td/'hooks_probe.json';hk.write_text(json.dumps({'settings':{'squeue_poll':0.1}}))
    lenv={**env,'PATH':f'{install_bin(td)}:{os.environ["PATH"]}',**fake.env(),'C8_TEST_HOOKS':str(hk),'SQUEUE_STATES':'PENDING'}
    base=[sys.executable,'-B',str(ROOT/'tools/ledger.py'),'lockprobe','--probe',str(root/'locks'/'probe.lock'),'--markers',str(m),'--interval','0.05']
    cp=subprocess.run(base+['--wait','1','--side','login','--job',idle],env=lenv,capture_output=True,text=True,timeout=60)   # never RUNNING
    assert cp.returncode==69 and 'not RUNNING'in cp.stderr and 'not a lock result'in cp.stderr and not (m/idle).exists(),(cp.returncode,cp.stderr)
    login=subprocess.Popen(base+['--wait','30','--side','login','--job',jid,'--out',str(td/'pr_login.json')],env=lenv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    job=subprocess.Popen(base+['--wait','30','--side','job','--out',str(td/'pr_job.json')],env={**env,'SLURM_JOB_ID':jid},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    rd=m/jid
    for _ in range(400):
        if (rd/'ready').exists():break
        time.sleep(0.02)
    assert (rd/'ready').exists(),'the job side wrote no ready marker'
    time.sleep(1.0)   # about ten squeue polls with the job PENDING and the ready marker present
    polls=[x for x in fake.state()['history']if x['cmd']=='squeue'and jid in x['argv']]
    assert not (rd/'login_start').exists()and login.poll()is None and job.poll()is None and len(polls)>=3,len(polls)
    t_run=time.time();fake.set(jid,state='RUNNING',start=fake.now(),hold_start=False)
    lo,le=login.communicate(timeout=60);jo,je=job.communicate(timeout=60)
    assert login.returncode==0 and job.returncode==0,(le,je)
    rl=json.loads((td/'pr_login.json').read_text());rj=json.loads((td/'pr_job.json').read_text())
    assert rl['pass']and rj['pass']and rl['run_dir']==rj['run_dir']==str(rd)
    assert json.loads((rd/'login_start').read_text())['t']>=t_run   # started only after the job was RUNNING
    ok('lockprobe_login_side_waits_for_running_and_the_ready_marker_squeue_env_filtered')

def test_finite_numbers(td):
    """nan, inf, 1e999 (float() reads it as inf) and out-of-range values of --hold-su, lockprobe's --interval and
    --wait, C8_LOCK_WAIT and C8_PILOT_SU_CAP refuse (64) before anything is written, locked or slept on, never with a
    traceback. The rebuild case is the reviewer's: a recorded block past G, then `--hold-su nan`."""
    import contextlib,io
    root,env,h,fake,log=rb_env(td,'finite');s=ledger.Settings(env);t='e'*12
    with ledger.SessionLock(s,'t')as lock:setup_intents(s,lock,[t])
    s.ledger_path.write_bytes(b'');(s.intents/f'{t}.json').write_bytes(b'garbage')   # an unreadable intent file without a ledger copy: a block
    refuses(69,ledger.cmd_rebuild,A(reason='block'),env);h.advance(ledger.INTENT_GRACE+1)
    def files():return {str(p):p.read_bytes()for p in root.rglob('*')if p.is_file()}
    def main(argv,e=env):
        err=io.StringIO()
        with contextlib.redirect_stderr(err),contextlib.redirect_stdout(io.StringIO()):rc=ledger.main(argv,e)
        return rc,err.getvalue()
    dec=['rebuild','--reason','decided','--user-decision','PLAN-REVIEW-LOG.md:3','--hold-line','dev','--decision-log',str(log)]
    before=files()
    for v in ('nan','NaN','inf','-inf','1e999','-1','abc'):
        rc,err=main(dec+['--hold-su',v]);assert rc==64 and 'hold-su'in err,(v,rc,err)
    refuses(64,ledger.cmd_rebuild,A(reason='decided',user_decision='PLAN-REVIEW-LOG.md:3',hold_su=float('nan'),hold_line='dev',decision_log=str(log)),env)
    assert files()==before   # nothing written: no ledger, no block record, no evidence
    rc,err=main(dec+['--hold-su','5']);assert rc==0,err
    holds=[r for r in ledger.Ledger(s).read(writer=False)if r['kind']=='intent'and r.get('hold')];assert len(holds)==1 and holds[0]['reservation_su']==5.0
    # lockprobe: every bad --interval/--wait refuses before the probe file or a marker directory exists
    m=td/'markers_finite';probe=root/'locks'/'probe_finite.lock'
    pb=['lockprobe','--probe',str(probe),'--side','job','--markers',str(m)]
    for extra in (['--interval','nan'],['--interval','inf'],['--interval','1e999'],['--interval','-1'],['--interval','61'],
                  ['--wait','nan'],['--wait','1e999'],['--wait','0'],['--wait','-5'],['--wait','601'],['--interval','1','--wait','3.5']):
        rc,err=main(pb+extra);assert rc==64 and ('--interval'in err or '--wait'in err),(extra,rc,err)
    assert not m.exists()and not probe.exists()
    cp=tool('ledger.py',*pb,'--interval','nan',env=env);assert cp.returncode==64 and 'Traceback'not in cp.stderr,cp.stderr
    # the settings of the same class: C8_LOCK_WAIT and C8_PILOT_SU_CAP
    for v in ('inf','nan','1e999','-1'):refuses(64,ledger.Settings,{**env,'C8_LOCK_WAIT':v})
    for v in ('inf','nan','1e999','0','-5','x'):refuses(64,budget.line_cap,'pilot',{'C8_PILOT_SU_CAP':v})
    assert budget.line_cap('pilot',{'C8_PILOT_SU_CAP':'300'})==(300.0,None)and ledger.Settings({**env,'C8_LOCK_WAIT':'2.5'}).lock_wait==2.5
    ok('finite_numbers_hold_su_interval_wait_lock_wait_pilot_cap_refuse_64_nothing_written')

def run():
    with tempfile.TemporaryDirectory(prefix='c8d3_ledger_')as td:
        td=Path(td)
        for t in (test_frame,test_intent_file_and_resolution,test_record_check,test_append_failures,test_register,test_lock,test_mount_and_settings,
                  test_rebuild,test_rebuild_blocks,test_rebuild_missing,test_rebuild_unattributable_and_sigkill,test_rebuild_resolved_intent_both_copies_lost,
                  test_rebuild_decision_crash_every_step,test_block_clock,test_decision_ref_bytes,test_lockprobe,test_lockprobe_failures,
                  test_lockprobe_early_grant,test_lock_acquisition_check_failure_releases,test_rebuild_unreadable_file_and_os_errors,
                  test_lockprobe_login_waits_for_running,test_finite_numbers,test_mount_symmetry,test_lockprobe_symmetry):
            t(td)
    return {'status':'passed','tests':RESULTS}
if __name__=='__main__':print(json.dumps(run(),indent=1,default=str))
