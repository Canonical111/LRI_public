import install_fastq
install_fastq.install_domain()
import scaled_b as sb
install_fastq.install_endpoint()
import native_fused
native_fused.install()
import sys,os,json,time
import grouped_stage as gs
gs.install(from_stage=3)
name=sys.argv[1]
st=time.time()
sb.tb.worker(name)
f=sb.OUT/name/'result.json';data=json.loads(f.read_text());data['exact_arithmetic']='GMP scalar backend, checked against Fraction and QQ';data['fresh_runtime_seconds']=time.time()-st
f.write_text(json.dumps(data,indent=2))
