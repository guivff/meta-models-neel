"""One Mac-only selection on original full screen. No labels/axes on pod."""
from pathlib import Path
import json,os,sys,time,subprocess,tarfile,hashlib,shlex
H=Path(__file__).resolve().parent;R=H.parents[3];sys.path.insert(0,str(H));import stage_and_start as st
read=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 os.umask(0o077)
 with(H/'CPU_BRIDGE_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),pid=os.getpid(),source_sha256=sha(__file__)),f)
 # Load exact pinned tokenizer before screen is ready; no answer/output access.
 src=H/'rehearsal';sys.path[:0]=[str(src),str(src/'external/mats-nla-workspace/src')]
 from transformers import AutoTokenizer
 from projects.g_agreement.e140 import selection
 tokroot=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9');assert sha(tokroot/'tokenizer.json')=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42';tok=AutoTokenizer.from_pretrained(tokroot,local_files_only=True);assert hashlib.sha256(tok.chat_template.encode()).hexdigest()=='e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259'
 while True:
  s=read(H/'ALLOCATION.private.json');assert time.time()<s['hard_deadline_epoch']-60
  flags=json.loads(st.ssh(s,f"cd {s['remote_dir']}\n/weights/venv-kernels/bin/python - <<'REMOTE'\nimport json\nfrom pathlib import Path\nprint(json.dumps(dict(ready=Path('outputs/SCREEN_READY.json').exists(),terminal=Path('EXIT.json').exists())))\nREMOTE\n",30))
  if flags['terminal']:return
  if flags['ready']:break
  time.sleep(5)
 with(H/'SCREEN_PULL_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time()),f)
 host,port=s['address'].split(':');archive=H/'SCREEN_CPU_ONLY.tar';script=f"cd {s['remote_dir']}\n/weights/venv-kernels/bin/python - <<'REMOTE'\nimport tarfile,sys\nfrom pathlib import Path\nassert Path('outputs/SCREEN_READY.json').is_file()\nwith tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as t:\n for p in sorted(Path('outputs/screen').rglob('*')):\n  if p.is_file():t.add(p,arcname=str(p.relative_to('outputs')),recursive=False)\nREMOTE\n"
 args=['ssh','-i',str(st.KEY),'-p',port,'-o','BatchMode=yes','-o','ConnectTimeout=15','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','root@'+host,'bash -s']
 with archive.open('xb')as f:q=subprocess.run(args,input=script.encode(),stdout=f,stderr=subprocess.PIPE,timeout=45)
 assert q.returncode==0,'SCREEN_PULL_FAILED_NO_REPLAY';dest=H/'screen_cpu';dest.mkdir(exist_ok=False)
 with tarfile.open(archive)as t:
  for m in t.getmembers():assert m.isfile()and not Path(m.name).is_absolute()and'..'not in Path(m.name).parts
  t.extractall(dest)
 screen=dest/'screen';digest=sha(screen/'OUTPUT_SEAL.json');m=read(H/'PREPARATION.json')
 disposition=selection.select(screen,digest,Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e140-dev2-inputs-v1/inputs'),m['input_sha256'],H/'selection_cpu',tokenizer=tok)
 # Only public label-free main rows + immutable selection proof may leave the Mac.
 remote=s['remote_dir']
 if disposition['action']=='MAIN':
  pack=H/'MAIN_PUBLIC_INPUTS.tar.gz'
  with tarfile.open(pack,'w:gz')as t:
   for p in sorted((H/'selection_cpu/main').iterdir()):assert p.name in('items.json','MANIFEST.json','SCREEN_SELECTION_SEAL.json','INPUT_SEAL.json');t.add(p,arcname=p.name,recursive=False)
  q=subprocess.run(['scp','-i',str(st.KEY),'-P',port,'-o','BatchMode=yes','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null',str(pack),'root@'+host+':'+remote+'/main_inputs.tar.gz'],capture_output=True,timeout=40);assert q.returncode==0
  st.ssh(s,f"cd {remote}\n/weights/venv-kernels/bin/python - <<'REMOTE'\nfrom pathlib import Path\nimport hashlib,tarfile\np=Path('main_inputs.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=={sha(pack)!r}\nPath('main_inputs').mkdir()\nwith tarfile.open(p)as t:\n for m in t.getmembers():assert m.isfile() and len(Path(m.name).parts)==1\n t.extractall('main_inputs')\nREMOTE\n",30)
 # Strip CPU-only axes/locators; disposition contains hashes and counts only.
 safe={k:v for k,v in disposition.items()if k!='CPU_only_seal_sha256'}
 st.ssh(s,f"cd {remote}\n/weights/venv-kernels/bin/python - <<'REMOTE'\nfrom pathlib import Path\nimport json\np=Path('CPU_DISPOSITION.json');assert not p.exists();p.with_suffix('.new').write_text(json.dumps({safe!r}));p.with_suffix('.new').replace(p)\nREMOTE\n",30)
 (H/'CPU_BRIDGE_COMPLETE.json').write_text(json.dumps(dict(at=time.time(),screen_sha256=digest,disposition=disposition,private_axes_remain_CPU=True,no_analysis=True),indent=2)+'\n')
if __name__=='__main__':main()
