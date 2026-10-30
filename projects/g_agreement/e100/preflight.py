"""Validate the exact code and owner data archives on CPU before pod custody."""
import argparse,os,subprocess,sys,tarfile,time
from pathlib import Path
from .contract import ROOT,read,write,sha,require
OUT=ROOT/'results/g_agreement/understand/e100/runner'

def extract(path,digest,dest):
 require(sha(path)==digest,'exact archive digest')
 with tarfile.open(path) as t:
  for m in t.getmembers():require((m.isdir() or m.isfile()) and (dest/m.name).resolve().is_relative_to(dest.resolve()),'archive traversal/link forbidden')
  t.extractall(dest,filter='data')

def main():
 p=argparse.ArgumentParser();p.add_argument('--owner-request',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 req=read(a.owner_request);source=read(OUT/'SOURCE_ARCHIVE.json');code=a.out/'code';code.mkdir();extract(source['path'],source['sha256'],code)
 env=dict(os.environ);env['PYTHONPATH']=str(code)
 def run(args):
  r=subprocess.run([sys.executable,'-m','projects.g_agreement.e100.worker']+args,cwd=code,env=env,text=True,capture_output=True)
  require(r.returncode==0,'exact CPU preflight failed: '+r.stderr);return r.stdout.strip()
 print(run(['--cpu-import-preflight']));results=[]
 for shard in ('reported','missed'):
  dest=a.out/shard;dest.mkdir()
  for entry in req['archives']:
   if entry['kind'] in ('basis',shard):extract(entry['archive'],entry['archive_sha256'],dest)
  entry=next(x for x in req['archives'] if x['kind']==shard)
  args=['--inputs',str(dest/'inputs'),'--input-sha',entry['input_seal_sha256'],'--shard',shard,'--assignment','NOT_USED_CPU','--assets','NOT_USED_CPU','--out','NOT_USED_CPU','--source-seal',str(code/'results/g_agreement/understand/e100/runner/SOURCE_SEAL.json'),'--source-sha',source['source_seal_sha256'],'--validate-only']
  start=time.monotonic();print(shard,run(args));results.append(dict(shard=shard,input_seal_sha256=entry['input_seal_sha256'],seconds=time.monotonic()-start,status='PASS'))
 write(OUT/'EXACT_PREFLIGHT.json',dict(experiment='E100',status='EXACT_ARCHIVES_CPU_PASS',source_seal_sha256=source['source_seal_sha256'],source_archive_sha256=source['sha256'],owner_request_sha256=sha(a.owner_request),owner_public_input_seal_sha256=req['public_input_seal_sha256'],owner_publication='c7f7e53aab033d8cb2dce31e416c4527656b6687',shards=results,exact_import='PASS',GPU_calls=0,real_readouts_opened=False))
if __name__=='__main__':main()
