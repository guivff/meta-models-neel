"""CPU-only §79 corpus builder: pinned public bytes + read-only frozen P3 bank."""
from __future__ import annotations
import argparse,hashlib,json,re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SEED=20261023
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'results/g_agreement/blindspot/s79'
CACHE=ROOT/'cache/g_agreement/blindspot/s79'
P3=Path('/Users/guivff/Documents/Neel_Exploration/wt-p3/results/g_agreement/r/p3/preparation_v5_20261021/selection.json')
SOURCES=[
 ('prose','Salesforce/wikitext','b08601e04326c79dfdd32d625aee71d232d685c3',['wikitext-2-raw-v1/train-00000-of-00001.parquet']),
 ('python','google-research-datasets/mbpp','4bb6404fdc6cacfda99d4ac4205087b89d32030c',[f'full/{s}-00000-of-00001.parquet' for s in ['prompt','test','train','validation']]),
 ('latex','EleutherAI/hendrycks_math','21a5633873b6a120296cce3e2df9d5550074f4a3',[f'{s}/train-00000-of-00001.parquet' for s in ['algebra','counting_and_probability','geometry','intermediate_algebra','number_theory','prealgebra','precalculus']]),
 ('markdown','bentrevett/wikitablequestions','4e4db6979e08a2fd0f0f614befaf871cae9e7b1a',['data/train-00000-of-00001.parquet']),
]

def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(x.encode()).hexdigest()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rank(*x):return digest(canonical([SEED,*x]))
def save(path,x):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def rows(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def jsonl(path,rs):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x') as f:
  for r in rs:f.write(canonical(r)+'\n')

def fetch():
 import requests
 jobs=[(domain,repo,rev,f) for domain,repo,rev,files in SOURCES for f in files]
 def one(job):
  domain,repo,rev,f=job;p=CACHE/'sources'/repo/ rev/f
  url=f'https://huggingface.co/datasets/{repo}/resolve/{rev}/{f}'
  if not p.exists():
   r=requests.get(url,timeout=120);r.raise_for_status();p.parent.mkdir(parents=True,exist_ok=True)
   if not r.content.startswith(b'PAR1'):raise ValueError('not Parquet '+url)
   p.write_bytes(r.content)
  return {'domain':domain,'repo':repo,'revision':rev,'file':f,'url':url,'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size}
 with ThreadPoolExecutor(max_workers=6) as pool:files=list(pool.map(one,jobs))
 save(CACHE/'SOURCE_FILES.json',files);return files

def render_table(table):
 if not isinstance(table,dict):raise ValueError('table not object')
 header=table.get('header');rr=table.get('rows')
 if not isinstance(header,list) or not header or not isinstance(rr,list) or not rr or any(not isinstance(r,list) or len(r)!=len(header) for r in rr):raise ValueError('ragged/empty table')
 def cell(x):return str(x).replace('\\','\\\\').replace('|','\\|').replace('\r\n','\n').replace('\r','\n').replace('\n','<br>')
 title=table.get('page_title') or table.get('title') or ''
 lines=['| '+' | '.join(map(cell,header))+' |','| '+' | '.join(['---']*len(header))+' |']+['| '+' | '.join(map(cell,r))+' |' for r in rr]
 return ('# '+str(title)+'\n\n' if title else '')+'\n'.join(lines)

def build(files):
 import pyarrow.parquet as pq
 rejected=Counter();candidates=[];source_meta={}
 def add(domain,text,source_id,group_id,location):
  if not isinstance(text,str) or not text.strip():rejected['empty_'+domain]+=1;return
  text=text.strip();h=digest(text);candidates.append({'id':domain+'-'+digest(source_id)[:20],'domain':domain,'text':text,'text_sha256':h,'source_id':source_id,'group_id':group_id,'source':location})
 for entry in files:
  path=ROOT/entry['path']
  if sha(path)!=entry['sha256']:raise ValueError('source hash changed '+str(path))
  repo=entry['repo'];domain=entry['domain'];article=0
  for i,r in enumerate(pq.read_table(path).to_pylist()):
   loc={'repo':repo,'revision':entry['revision'],'file':entry['file'],'row':i,'file_sha256':entry['sha256']};sid=repo+':'+entry['file']+':'+str(i)
   if domain=='prose':
    text=r['text']
    if re.fullmatch(r'\s*=\s+[^=]+\s+=\s*',text):article=i
    if text.strip().startswith('=') or sum(not x.isspace() for x in text)<128:rejected['prose_heading_or_short']+=1;continue
    add(domain,text,sid,repo+':article:'+str(article),loc)
   elif domain=='python':add(domain,r['code'],sid,repo+':task:'+str(r['task_id']),loc)
   elif domain=='latex':
    text=r['solution']
    if len(text.strip())<96 or not re.search(r'\\[A-Za-z]+|\$',text):rejected['latex_short_or_no_marker']+=1;continue
    add(domain,text,sid,repo+':problem:'+digest(r['problem']),loc)
   else:
    try:text=render_table(r['table'])
    except ValueError:rejected['invalid_table']+=1;continue
    name=r['table'].get('name') or digest(text)
    add(domain,text,sid,repo+':table:'+str(name),loc)
 # Frozen bank is retained in full, independent of feature values or native outcomes.
 p3=json.loads(P3.read_text());frozen=[]
 for r in p3['items']:
  t=r['prompt_text'];frozen.append({'id':'prose-p3-'+r['item_id'],'domain':'prose','text':t,'text_sha256':digest(t),'source_id':'P3:'+r['item_id'],'group_id':'P3:'+r['item_id'],'source':{'bank':'p3-v5-real-20261021','file':str(P3),'file_sha256':sha(P3),'item_id':r['item_id']}})
 if len(frozen)!=100 or len({r['id'] for r in frozen})!=100:raise ValueError('P3 expected100 distinct original prompts')
 seen={digest(re.sub(r'\s+',' ',r['text']).strip()) for r in frozen};unique=[]
 for r in sorted(candidates,key=lambda r:r['source_id']):
  h=digest(re.sub(r'\s+',' ',r['text']).strip())
  if h in seen:rejected['normalized_duplicate_'+r['domain']]+=1;continue
  seen.add(h);unique.append(r)
 selected=list(frozen)
 for domain,n in [('prose',500),('python',600),('latex',600),('markdown',600)]:
  pool=sorted([r for r in unique if r['domain']==domain],key=lambda r:rank(domain,r['source_id'],r['text_sha256']))
  if len(pool)<n:raise ValueError(f'insufficient {domain}: {len(pool)} < {n}')
  selected.extend(pool[:n])
 selected=sorted(selected,key=lambda r:(r['domain'],r['id']))
 if Counter(r['domain'] for r in selected)!=Counter({d:600 for d in ['prose','python','latex','markdown']}):raise ValueError('corpus counts')
 if len({r['id'] for r in selected})!=2400:raise ValueError('document identity collision')
 dest=CACHE/'frozen';dest.mkdir(parents=True,exist_ok=False);jsonl(dest/'corpus.jsonl',selected)
 manifest={'section':79,'seed':SEED,'status':'CORPUS_FROZEN_BEFORE_CAPTURE','domain_counts':dict(Counter(r['domain'] for r in selected)),'source_files':files,'frozen_bank':{'path':str(P3),'sha256':sha(P3),'items':100},'rejections':dict(rejected),'selection':'smallest sha256 canonical [seed,domain,sourceID,textSHA] after fixed filters and normalized deduplication; all100 P3 preserved','corpus_path':str((dest/'corpus.jsonl').relative_to(ROOT)),'corpus_sha256':sha(dest/'corpus.jsonl'),'documents':[{k:v for k,v in r.items() if k!='text'} for r in selected],'limits':'prose paragraph rows; LaTeX mathematical solution fragments; tables rendered as Markdown; no claim of complete natural files'}
 save(OUT/'CORPUS_MANIFEST.json',manifest);print(canonical({'counts':manifest['domain_counts'],'rejections':manifest['rejections'],'manifest_sha256':sha(OUT/'CORPUS_MANIFEST.json')}));return manifest

def main():
 p=argparse.ArgumentParser();p.add_argument('--download-and-build',action='store_true');a=p.parse_args()
 if not a.download_and_build:p.error('explicit --download-and-build required (CPU only)')
 build(fetch())
if __name__=='__main__':main()
