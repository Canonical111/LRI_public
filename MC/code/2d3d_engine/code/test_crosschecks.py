#!/usr/bin/env python3
"""Independent mt19937 build and sanitizer smoke checks. Requires g++."""
from pathlib import Path
import json,subprocess,tempfile
import numpy as np
from test_v2 import exact,jack,ROOT

def main():
    report={}
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);out=tmp/'mt'
        cmd=[str(ROOT/'bin/lri_mt'),'--dim','2','--length','4','--s','1.4','--beta','.18',
             '--out',str(out),'--measurements','300000','--warmup','10000','--seed','129411',
             '--sampler','hybrid','--record','extended']
        subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
        v,e=jack(np.fromfile(out/'samples.bin',dtype='<f8').reshape(-1,8),.18);truth=exact(2,4,1.4,.18);z=(v-truth)/e
        assert np.all(abs(z)<5);report['mt19937_exact']={'estimate':v.tolist(),'exact':truth.tolist(),'stderr':e.tolist(),'z':z.tolist()}
        binary=tmp/'sanitized'
        subprocess.run(['g++','-O1','-g','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(ROOT/'src/lri_mc.cpp'),'-o',str(binary)],check=True)
        cmd=[str(binary),'--dim','3','--length','64','--s','1.8','--beta','.100108','--out',str(tmp/'san'),
            '--measurements','50','--warmup','10','--seed','87451','--sampler','hybrid','--record','extended']
        proc=subprocess.run(cmd,text=True,capture_output=True)
        report['sanitizer_returncode']=proc.returncode;report['sanitizer_stderr']=proc.stderr
        assert proc.returncode==0 and not proc.stderr
    (ROOT.parent/'tests/crosscheck_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
