"""CPU-only §84 dependency export from an already committed, sealed §79 ranking.

Does not alter the GPU package, choose candidates or build any §84 items.
"""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from . import corpus as C


def receipt(source_commit,selection_file,selection_bytes):
 from ..analysis import validate_selection_receipt
 if not re.fullmatch('[0-9a-f]{40}',source_commit):raise ValueError('source_commit must be the full selection commit')
 path=Path(selection_file)
 if path.is_absolute() or '..' in path.parts:raise ValueError('selection_file must be repository-relative')
 top=json.loads(selection_bytes)
 if top.get('section')!=79 or top.get('status')!='FROZEN_BEFORE_ANY_S84_ITEMS':raise ValueError('selection is not a frozen §79 ranking')
 features=[r['feature'] for r in top['candidates']]
 return validate_selection_receipt({'source_commit':source_commit,'selection_file':path.as_posix(),'selection_sha256':hashlib.sha256(selection_bytes).hexdigest(),'section79_features':features,'section81_features':[]})


def export(source_commit,selection_file,out):
 from .analyse import top_candidates
 if not re.fullmatch('[0-9a-f]{40}',source_commit):raise ValueError('source_commit must be the full selection commit')
 path=Path(selection_file)
 if path.is_absolute() or '..' in path.parts:raise ValueError('selection_file must be repository-relative')
 def committed(name):return subprocess.check_output(['git','show',source_commit+':'+str(name)],cwd=C.ROOT)
 data=committed(path);top=json.loads(data);seal=json.loads(committed(path.parent/'ANALYSIS_SEAL.json'));results_bytes=committed(path.parent/'RESULTS.json');results=json.loads(results_bytes)
 if seal.get('run_kind')!='real' or results.get('status')!='COMPLETE':raise ValueError('real complete sealed analysis required')
 for name,blob in [(path.name,data),('RESULTS.json',results_bytes)]:
  if seal.get('files',{}).get(name)!=hashlib.sha256(blob).hexdigest():raise ValueError('committed analysis seal mismatch '+name)
 if top.get('results_sha256')!=hashlib.sha256(results_bytes).hexdigest() or top.get('freeze_sha256')!=C.sha(C.OUT/'FREEZE.json'):raise ValueError('ranking results/freeze mismatch')
 if top.get('candidates')!=top_candidates(results['rows']):raise ValueError('committed ranking differs from registered selection/order')
 result=receipt(source_commit,path.as_posix(),data)
 if Path(out).exists():raise ValueError('refuse to overwrite selection receipt')
 C.save(out,result);return result


def main():
 p=argparse.ArgumentParser();p.add_argument('--source-commit',required=True);p.add_argument('--selection-file',required=True);p.add_argument('--out',required=True,type=Path);a=p.parse_args();export(a.source_commit,a.selection_file,a.out)
if __name__=='__main__':main()
