from group_before_fibration import *
r=ROOT;i=int(sys.argv[1]);source=r/'weighted_s2'/f'bucket{i:03}.jsonl';folder=r/'moving_s3';folder.mkdir(exist_ok=True);dest=folder/f'b{i:03}.jsonl'
if not dest.exists():
 g,n=moving_stage([source],3,4);dump_moving(dest,g)
 rp={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'input_rows':n,'output_rows':len(g),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
 dest.with_suffix('.report.json').write_text(json.dumps(rp,indent=2))
print('DONE_MOVING',i,flush=True)
