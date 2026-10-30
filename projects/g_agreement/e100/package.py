"""Freeze exact runtime source and data-stage request; no provider/model actions."""
import argparse,ast,json,subprocess,tarfile
from pathlib import Path
from .contract import ROOT,read,write,sha,require,OLD_RUNNER
OUT=ROOT/'results/g_agreement/understand/e100/runner'

def function_tree(text,name):return ast.dump(next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);OUT.mkdir(parents=True,exist_ok=True)
 original=read(ROOT/'results/g_agreement/understand/e79/DEPENDENCIES.json');files={};drift=[]
 for n,h in original.items():
  actual=sha(ROOT/n)
  if actual!=h:
   require(n in ('projects/g_agreement/blindspot/protocol.py','projects/g_agreement/blindspot/run.py'),'unexpected original dependency drift');drift.append(dict(path=n,old_sha256=h,new_sha256=actual))
  files[n]=actual
 require(sha(ROOT/'results/g_agreement/understand/e79/worker.py')==OLD_RUNNER,'pinned original E79 runner')
 old=subprocess.check_output(['git','show','8e431cca:projects/g_agreement/blindspot/run.py'],cwd=ROOT,text=True);new=(ROOT/'projects/g_agreement/blindspot/run.py').read_text()
 require(all(function_tree(old,n)==function_tree(new,n) for n in ('_assets','_load_oracle')),'original asset verification and native load recipes')
 for p in (ROOT/'projects/g_agreement/e100').glob('*.py'):files[str(p.relative_to(ROOT))]=sha(p)
 files['results/g_agreement/understand/e79/worker.py']=OLD_RUNNER
 files['common/__init__.py']=sha(ROOT/'common/__init__.py')
 for n in list(files):
  for parent in (ROOT/n).parents:
   if parent==ROOT:break
   init=parent/'__init__.py'
   if init.exists():files[str(init.relative_to(ROOT))]=sha(init)
 write(OUT/'SOURCE_SEAL.json',dict(experiment='E100',authority=['f425a5e2','fd07c12a','69f8c08e4'],original_runner_commit='8e431cca',files=files))
 write(OUT/'RECIPE_AUDIT.json',dict(original_worker_sha256=OLD_RUNNER,unrelated_operational_file_drift=drift,native_asset_and_oracle_loader_AST_unchanged=True,readout_method='unchanged worker56.Backend.native_one',nla='unchanged native_nla512',GPU_calls=0))
 arc=a.out/'E100_SOURCE.tar.gz'
 with tarfile.open(arc,'w:gz') as t:
  for n in sorted(files):t.add(ROOT/n,arcname=n)
  t.add(OUT/'SOURCE_SEAL.json',arcname=str((OUT/'SOURCE_SEAL.json').relative_to(ROOT)))
 require(arc.stat().st_size<20*1024*1024,'source archive below20MiB')
 write(OUT/'SOURCE_ARCHIVE.json',dict(path=str(arc.resolve()),sha256=sha(arc),bytes=arc.stat().st_size,source_seal_sha256=sha(OUT/'SOURCE_SEAL.json'),root='extract into repository runtime root',parts=['a','b'],withdrawn=['c','d'],no_launch=True))
 print('E100 runtime sources packaged; no models or providers loaded.')
if __name__=='__main__':main()
