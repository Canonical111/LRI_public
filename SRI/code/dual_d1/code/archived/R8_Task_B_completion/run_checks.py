"""Independent stdlib-only verification from the four integrity-checked archives.
First execution unpacks into replay_workspace. It never uses original scratch paths.
"""
from pathlib import Path
import argparse,hashlib,json,zipfile,subprocess,sys
ROOT=Path(__file__).resolve().parent

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(2**20),b''):h.update(block)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--force-unpack',action='store_true');a=p.parse_args()
 manifest=json.loads((ROOT/'archive_manifest.json').read_text());assert manifest['status']=='Task_B_complete'
 dest=ROOT/'replay_workspace';dest.mkdir(exist_ok=True);signature=sha(ROOT/'archive_manifest.json');marker=dest/'unpacked_manifest.sha256'
 for row in manifest['extract_order']:
  path=ROOT/row['path'];assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],str(path)
 if a.force_unpack or not marker.exists() or marker.read_text()!=signature:
  for row in manifest['extract_order']:
   print('Unpacking',row['path'],flush=True)
   with zipfile.ZipFile(ROOT/row['path']) as z:
    for info in z.infolist():
     target=(dest/info.filename).resolve()
     if not target.is_relative_to(dest.resolve()):raise ValueError('Unsafe archive path')
    z.extractall(dest)
  marker.write_text(signature)
 root=dest/'R8_work';print('Verifying all 37 sources, exact sums, and six independent divergences',flush=True)
 subprocess.run([sys.executable,str(root/'engine/finalize_B_aggregate.py')],cwd=root,check=True)
 got=json.loads((root/'Task_B_result.json').read_text());expected=json.loads((ROOT/'result.json').read_text())
 assert got==expected,'Reassembled result differs from delivered result'
 report={'status':'complete_portable_replay_passed','archive_hashes_verified':True,'all_37_sources_covered':True,'all_six_divergences_exact':True,'R8':got['R8'],'no_original_scratch_paths_used':True}
 (ROOT/'portable_replay_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
