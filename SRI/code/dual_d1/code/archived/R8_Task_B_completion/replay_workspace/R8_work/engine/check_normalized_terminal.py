import install_fastq
install_fastq.install_domain()
import scaled_b as sb
install_fastq.install_endpoint()
import native_fused;native_fused.install()
import normalized_terminal as nt
import time,json
st=time.time();folder=sb.OUT/'n8_f1_b00'
items=sb.tb.br.rr.load(folder/'stage4.jsonl');v,count,negative=nt.last_two(items,8)
r=json.loads((folder/'result.json').read_text());assert str(v)==r['value'];assert list(map(str,negative))==r['dimensionless_negative_inverse_euler']
d={'status':'complete_normalized_terminal_exact_regression','block':'n8_f1_b00','boundary':str(v),'negative':list(map(str,negative)),'terms':count,'native_fused':native_fused.COUNTS,'seconds':time.time()-st};(sb.ROOT/'normalized_terminal_control.json').write_text(json.dumps(d,indent=2));print('PASS',d,flush=True)
