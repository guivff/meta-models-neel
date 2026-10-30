"""§217: verify E82 seal, close allocation once, analyse once, publish and request R2.
No inference, GPU, result repair or source-bank re-analysis. Existing intents and
scientific seals are never replayed. Private target maps are never published.
"""
import json,hashlib,subprocess,time,os,fcntl,tarfile,re,shutil
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[3];H=R/'cache/g_agreement/i2/e82_judge_cpu_v1';JOB=H/'judging/E82_judgments'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def log(message):
 with (R/'results/g_agreement/i2/HANDOFF.md').open('a')as f:f.write('\n'+datetime.now(timezone.utc).isoformat()+' '+message+'\n')
def scan(b,name):
 assert not any(re.search(p,b)for p in [rb'hf_[A-Za-z0-9]{25,}',rb'sk-[A-Za-z0-9_-]{20,}',rb'Bearer\s+[A-Za-z0-9._-]{20,}']),name

def tar_sources(dest,files):
 with tarfile.open(dest,'w:gz',format=tarfile.PAX_FORMAT)as t:
  for p,name in files:
   assert p.is_file()and not p.is_symlink();data=p.read_bytes();scan(data,name);info=t.gettarinfo(str(p),arcname=name);info.pax_headers['mtime']=str(Decimal(p.stat().st_mtime_ns)/Decimal(10**9))
   with p.open('rb')as f:t.addfile(info,f)

def validate():
 import sys
 sys.path.insert(0,str(R/'results/g_agreement/i2'));import e82_dispatch as D
 pre,records,rubric,original,old,allowed,route,api,privacy,protocol,io=D.source_preflight();seal=read(JOB/'RESULT_SEAL.json');assert seal['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS' and seal['experiment']=='E82'
 for n,d in seal['files'].items():assert sha(JOB/n)==d
 totals={};kept={};unparseable={}
 for label,items,rr,name in [('E82',records,rubric,'JUDGMENTS.json'),('E82_original_25pct',original,old,'ORIGINAL_JUDGMENTS.json')]:
  rows=read(JOB/name);assert [x['id']for x in rows]==[x['id']for x in items];assert len({x['id']for x in rows})==len(rows)
  for item,row in zip(items,rows):
   assert row['status']in ('KEPT','UNPARSEABLE')and row['attempts']in (0,1,2)
   body=D.G.wire([item],rr,protocol,D.run.payload);rid=hashlib.sha256((label+':'+str(row['attempts'])+':'+io.canonical(body)).encode()).hexdigest();folder=H/'judging'/(label+'_attempt'+str(row['attempts']));request=read(folder/(rid+'.request.json'));response=read(folder/(rid+'.response.json'));assert request['wire']==body and response['http_status']==200
   raw=response['response'];assert raw['provider']=='Google' and raw['model']in [protocol.MODEL,protocol.MODEL+'-001']and raw.get('usage',{}).get('cost')is not None
   finish=raw['choices'][0]['finish_reason'];assert finish in ('stop','length')
   if row['status']=='KEPT':
    assert finish=='stop';codes=json.loads(raw['choices'][0]['message']['content'])['records'];assert [x for x in codes if x.get('id')==item['id']]==[row['code']];assert D.classify([item],dict(records=[row['code']]),allowed)[0]['status']=='KEPT'
   else:
    assert row['code']is None
    if finish=='length':assert row.get('terminal_reason')=='CHARGED_LENGTH'
    else:
     assert row['attempts']==2
     try:decoded=json.loads(raw['choices'][0]['message']['content'])
     except (ValueError,TypeError):decoded={}
     assert D.classify([item],decoded,allowed)[0]['status']=='INVALID'
  totals[label]=len(rows);kept[label]=sum(x['status']=='KEPT'for x in rows);unparseable[label]=sum(x['status']=='UNPARSEABLE'for x in rows)
 api.CAP=Decimal(18);ledger=api.Ledger(H/'judging/ledger.jsonl');book,settled=ledger.totals();assert len(book)==len(settled)and set(book)==settled;actual=sum(book.values(),Decimal(0));assert actual<=18
 responses=list((H/'judging').rglob('*.response.json'));assert len(responses)==len(book);assert len({p.stem.split('.')[0]for p in responses})==len(responses)
 raw_cost=sum((Decimal(str(read(p)['response']['usage']['cost']))for p in responses),Decimal(0));assert raw_cost==actual
 return dict(at_utc=datetime.now(timezone.utc).isoformat(),bank='E82',status='FULL_BLIND_GRID_VERIFIED',terminal_seal_sha256=sha(JOB/'RESULT_SEAL.json'),records=totals,kept=kept,unparseable=unparseable,physical_requests=len(book),actual_usd=str(actual),unresolved_usd='0',allocated_usd='18',allocation_released_usd=str(18-actual),raw_provider_route_cost_source_schema_verified=True,no_paid_request_resend=True,no_new_GPU_or_judge_calls=True)

def close(v):
 with (H/'JUDGE_FINANCIAL_CLOSE_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),terminal_seal_sha256=v['terminal_seal_sha256']),f)
 write(R/'results/g_agreement/i2/E82_JUDGING_FINANCIAL_CLOSEOUT.json',v)
 log('USE217.5 E82 fullblindgridverified/financialallocationCLOSEDonce actual'+v['actual_usd']+'/unresolved0/release'+v['allocation_released_usd']+'. No second judge-cost booking and no GPUledger entry. Charged truncations preserved missing.')

def publish_raw(v):
 dest=R/'results/g_agreement/sealed/E82_FULL_BLIND_JUDGMENTS';dest.mkdir(exist_ok=False)
 for n in ['JUDGMENTS.json','ORIGINAL_JUDGMENTS.json','COUNTS.json','RESULT_SEAL.json','CHARGED_TRUNCATIONS_SECTION217.json']:
  shutil.copy2(JOB/n,dest/n)
 shutil.copy2(H/'grouped_adapter_v1/GROUPED_PACKET.json',dest/'GROUPED_PACKET.json');shutil.copy2(H/'grouped_adapter_v1/ORIGINAL_IDS.json',dest/'ORIGINAL_IDS.json')
 files=[(p,str(p.relative_to(H/'judging')))for p in (H/'judging').rglob('*')if p.is_file()and p.name!='DISPATCH.lock'];tar_sources(dest/'RAW_RESPONSES.tar.gz',files)
 source=[(p,'runtime/'+str(p.relative_to(H/'runtime')))for p in (H/'runtime').rglob('*')if p.is_file()and '__pycache__'not in p.parts]
 source += [(R/'results/g_agreement/i2'/n,n)for n in ['e82_dispatch.py','e82_continue217.py','e82_grouped_judge.py','fresh_judging_snapshot.py']]
 source += [(H/'RUNTIME_SOURCE_MANIFEST.json','RUNTIME_SOURCE_MANIFEST.json')];tar_sources(dest/'EXECUTED_SOURCE.tar.gz',source)
 responses=sorted((H/'judging').rglob('*.response.json'),key=lambda p:p.stat().st_mtime_ns);first=responses[0]
 write(dest/'INTAKE.json',dict(**v,first_output_evidence=dict(relative_path=str(first.relative_to(H)),mtime_ns=first.stat().st_mtime_ns,sha256=sha(first)),source_preflight_sha256=sha(H/'grouped_adapter_v1/PREFLIGHT.json'),files={p.name:sha(p)for p in dest.iterdir()},private_correctness_labels_and_joins_absent=True))
 return dest

def render():
 os.environ.setdefault('MPLCONFIGDIR','/private/tmp/i2-e82-plot');import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 dest=R/'results/g_agreement/sealed/E82_ANALYSIS';d=read(dest/'SUMMARY.json');rows=list(d['rows'].items());fig,ax=plt.subplots(figsize=(9,4.8))
 for y,(name,x)in enumerate(rows):
  if x['delta']is None:ax.text(-.95,y,'no value stated: not evaluable');continue
  lo,hi=x['CI95'];ax.hlines(y,lo,hi,color='#396f98');ax.plot(x['delta'],y,'o',color='#396f98');ax.text(1.03,y,f"{x['naming_either_value']}/{x['planned_items']} name a value",va='center',fontsize=9)
 ax.set_yticks(range(len(rows)),[n for n,x in rows]);ax.axvline(0,color='black',lw=.7);ax.axvline(.2,color='#999999',ls='--');ax.set_xlim(-1.05,1.65);ax.set_xlabel('P(model belief) − P(truth), conditional on naming either value');ax.set_title('E82: do readers report the model’s wrong belief?');fig.text(.5,.015,'Item bootstrap; paired missing judgments excluded and bounded. Ten no-truth items are descriptive only.',ha='center',fontsize=8);fig.tight_layout(rect=[0,.04,1,1]);fig.savefig(dest/'E82_BELIEF_TRUTH.png',dpi=180);fig.savefig(dest/'E82_BELIEF_TRUTH.svg');plt.close(fig)
 p=dest/'E82_BELIEF_TRUTH.svg';p.write_text('\n'.join(x.rstrip()for x in p.read_text().splitlines())+'\n')
 verdicts='; '.join(f"{r}: {x['R_B2']} ({x['rows_met']}/2 rows)"for r,x in d['per_reader'].items())
 (dest/'SLIDE_NOTES.md').write_text('# E82 — belief versus truth (review pending)\n\n'+verdicts+'\n\nRegistered R-B2 requires conditional belief−truth ≥0.20 and item-bootstrap lower bound >0 on at least two source rows, per reader. Every source position was retained and grouped by item; positions are not independent n. Separate belief/truth calls remain separate; cross-judgment disagreements and terminal missingness are disclosed. Ten knowledge-cutoff items lack canonical truth and receive belief-mention reporting only. There is no invented belief-right comparison; R-B3 is not evaluable from this source swap. Source wrong-belief evidence is provenance, not a new belief measurement on this checkpoint.\n\nE107 outside-LLM comparison is separate and must wait for both E82 and E86 registered analyses. No reader-specific-versus-text claim is inferred from this result alone. Old-rubric matched sensitivity uses only the frozen selected IDs, with unpaired targets disclosed; it cannot replace the full primary grid.\n')
 write(dest/'REPORT_SEAL.json',dict(analysis_seal_sha256=sha(dest/'ANALYSIS_SEAL.json'),files={p.name:sha(p)for p in dest.iterdir()if p.name!='REPORT_SEAL.json'},review_pending=True))

def main():
 cfg=read(H/'ANALYSIS_WATCHER_CONFIG.json');assert sha(R/'projects/g_agreement/e82_analysis/analyze.py')==cfg['analysis_code_sha256']and sha(Path(__file__))==cfg['watcher_code_sha256']
 lock=(H/'ANALYSIS_WATCHER.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with (H/'ANALYSIS_WATCHER_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),config_sha256=sha(H/'ANALYSIS_WATCHER_CONFIG.json')),f)
 while not (JOB/'RESULT_SEAL.json').exists():
  if (JOB/'SECTION217_BLOCKED.json').exists():write(H/'WATCHER_ATTENTION_REQUIRED.json',read(JOB/'SECTION217_BLOCKED.json'));return
  assert time.time()<cfg['watch_until_epoch'],'WATCHER_DEADLINE_NO_REPLAY';time.sleep(15)
 v=validate();close(v);raw=publish_raw(v)
 assert not (H/'ANALYSIS_ONCE_INTENT.json').exists();subprocess.run([os.sys.executable,str(R/'projects/g_agreement/e82_analysis/analyze.py')],cwd=R,check=True);render()
 dest=R/'results/g_agreement/sealed/E82_ANALYSIS';d=read(dest/'SUMMARY.json')
 log('USE217.6 E82 watcher verified fullblindseal/closedallocation once, ran committed synthetic-tested registered analysis ONCE, rendered figures. R-B2 perreader '+json.dumps(d['per_reader'])+'. Private joins LOCAL; publication/reviewerHANDOFF follows.')
 subprocess.run([os.sys.executable,'/private/tmp/i2_publish_paths.py','I-2: E82 full blind judgments and once-only registered analysis sealed',str(raw.relative_to(R)),str(dest.relative_to(R)),'results/g_agreement/i2/E82_JUDGING_FINANCIAL_CLOSEOUT.json'],cwd=R,check=True)
 request=H/'R2_ANALYSIS_READY_REQUEST.md';request.write_text('## E82 registered analysis ready — §217\nRequest-ID: I2-E82-ANALYSIS-READY-20261029\nTo: R-2\nFrom: I-2\n\nPlease review `results/g_agreement/sealed/E82_ANALYSIS` and `E82_FULL_BLIND_JUDGMENTS` on arrival. Code `projects/g_agreement/e82_analysis` was committed with10synthetic tests before judgment seal. Verify all209 source items/allpositions, 199truth contrasts +10belief-only items, per-reader R-B2 conditional denominator/item bootstrap, separate target calls/any-value cross-judgment disagreement, missingness and matched25% subset, source aliases/provenance, charged length terminal missing under§217, exact provider/cost/raw/code bindings. Private target map is local at wt-i2/cache/g_agreement/i2/e82_judge_cpu_v1/grouped_adapter_v1/TARGET_MAP.PRIVATE.json, bound by seals; do not publish it or replay author analysis/judging. R-B3 lacks a source belief-right group; E107 remains separate pending E86 registered analysis. Append review to R-2.md and acknowledge here.\n')
 subprocess.run([os.sys.executable,'/private/tmp/i2_append_owner_handoff.py','results/g_agreement/reviews/R-2/HANDOFF.md',str(request),'I-2 → R-2: E82 analysis seal ready under §217'],cwd=R,check=True)
 write(H/'WATCHER_COMPLETE.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),analysis_seal_sha256=sha(dest/'ANALYSIS_SEAL.json'),raw_judgments_published=True,reviewer_HANDOFF_posted=True,per_reader=d['per_reader']))
if __name__=='__main__':main()
