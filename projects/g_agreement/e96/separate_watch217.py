"""Exact-grid once-only E96 separate analysis watcher; never opens primary outputs."""
import json,datetime,tarfile,hashlib,shutil,subprocess,fcntl,re,gzip
from pathlib import Path
from decimal import Decimal
from .reconstructor_check import digest,write
from .prepare_smoke_inputs import verify
ROOT=Path(__file__).resolve().parents[3]

def ready(packet,judgments):
 verify(packet,'PACKET_SEAL.json');verify(judgments,'JUDGMENT_SEAL.json')
 ps=json.loads((packet/'PACKET_SEAL.json').read_text());js=json.loads((judgments/'JUDGMENT_SEAL.json').read_text())
 if ps['scope']['mode']!='separate_slot1_17920' or js['packet_seal_sha256']!=digest(packet/'PACKET_SEAL.json') or js['status']!='TERMINAL_BLIND_GRID_NO_LABEL_JOIN':raise ValueError('separate terminal seal binding')
 for name,ids in [('current',{r['id'] for r in json.loads((packet/'JUDGE_PACKET.json').read_text())}),('original',set(json.loads((packet/'OLD_RUBRIC_IDS.json').read_text())))]:
  rows=json.loads((judgments/(name+'_JUDGMENTS.json')).read_text())
  if len(rows)!=len(ids) or len({x['id'] for x in rows})!=len(rows) or {x['id'] for x in rows}!=ids:raise ValueError('exact separate terminal grid')
 return ps,js

def once(base):
 packet=base/'packet';judgments=base/'judgments';ps,js=ready(packet,judgments);out=base/'analysis_once'
 if out.exists():raise ValueError('separate analysis output already exists; never replay')
 with (base/'ANALYSIS_WATCH_CLAIM.json').open('x') as f:json.dump({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'packet_sha256':digest(packet/'PACKET_SEAL.json'),'judgments_sha256':digest(judgments/'JUDGMENT_SEAL.json'),'mode':'separate17920 only'},f)
 from .analyze import run
 run(packet,judgments,ROOT/'cache/g_agreement/e96/cpu_inputs',ROOT/'results/g_agreement/e96/LEGACY_AXES.json',out)
 verify(out,'ANALYSIS_SEAL.json');return out

def publish(base):
 """Only packaging/Git may be resumed after a failure; analysis is never repeated."""
 shared=ROOT.parent/'wt-i4-status';package=shared/'results/g_agreement/e96/slot1_second_final_scientific';analysis=base/'analysis_once';judgments=base/'judgments';az=json.loads((analysis/'ANALYSIS_SEAL.json').read_text());now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 verify(analysis,'ANALYSIS_SEAL.json');ready(base/'packet',judgments)
 with (base/'PUBLICATION.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if (base/'PUBLISHED.json').exists():return json.loads((base/'PUBLISHED.json').read_text())
  def git(*args,check=True):return subprocess.run(['git',*args],cwd=shared,text=True,capture_output=True,check=check)
  if git('status','--porcelain').stdout.strip():raise RuntimeError('shared publication checkout busy/dirty; retry packaging later, never replay analysis')
  git('pull','--rebase','origin','r/blindspot')
  if package.exists():raise RuntimeError('publication package already staged; reconcile Git without re-analysis')
  package.mkdir();shutil.copytree(analysis,package/'analysis')
  with tarfile.open(package/'COMPLETE_JUDGMENTS.tar.gz','w:gz') as ar:
   for p in sorted(judgments.iterdir()):
    if p.is_file():ar.add(p,arcname=p.name)
  codes={}
  ps=json.loads((base/'packet/PACKET_SEAL.json').read_text());codes.update(ps['code_files']);codes.update(az['code_files'])
  for n in ['separate_dispatch217.py','separate_watch217.py']:codes['projects/g_agreement/e96/'+n]=digest(ROOT/'projects/g_agreement/e96'/n)
  with tarfile.open(package/'EXACT_CODE.tar.gz','w:gz') as ar:
   for n,h in codes.items():
    if digest(ROOT/n)!=h:raise ValueError('executed analysis/dispatch source changed before publication')
    ar.add(ROOT/n,arcname=n)
  custody=base/'private_transport';custody.mkdir(exist_ok=True);custody.chmod(0o700)
  with tarfile.open(custody/'FULL_REQUEST_RESPONSE_LEDGER.tar.gz','w:gz') as ar:ar.add(base/'ledger',arcname='ledger')
  (custody/'FULL_REQUEST_RESPONSE_LEDGER.tar.gz').chmod(0o600)
  write(package/'PRIVATE_TRANSPORT_CUSTODY.json',{'path':str(custody/'FULL_REQUEST_RESPONSE_LEDGER.tar.gz'),'sha256':digest(custody/'FULL_REQUEST_RESPONSE_LEDGER.tar.gz'),'reason':'Unredacted account/provider payloads stay private; all generatedreadouts/rawjudgedrecords/terminalattempts/cost/route/source published, no scientific filtering'})
  for n in ['SEPARATE_SLOT1_REPORT_CONTRACT.json','SEPARATE_SLOT1_JUDGING_ALLOCATION.json','JUDGING_INDEX.json','PLACEBO_INDEX.json','LEGACY_AXES.json']:shutil.copy2(ROOT/'results/g_agreement/e96'/n,package/n)
  write(package/'PUBLICATION_SEAL.json',{'experiment':'E96_SLOT1_SECOND_FINAL_SEPARATE','status':'COMPLETE_ONCE_R4_PENDING','sealed_utc':now,'first_output_utc':az['first_output_utc'],'primary_unchanged':True,'no_pooling_or_primary_reexecution':True,'files':{str(p.relative_to(package)):digest(p) for p in package.rglob('*') if p.is_file()}})
  (package/'REVIEW_HANDOFF.md').write_text('Separate17920/18rows28cells ONLY. Completejudgments/rawjudgedrecords/itemarrays/exactcode/indices/seals enclosed. Same frozen scientificrules/thresholds/seeds. Retained35200reviewedprimary immutable/notpooled/re-executed. Independent R4bootstrap/rulelines required before claim.\n')
  cost=Decimal(str(json.loads((judgments/'COST.json').read_text())['actual_usd']));total=cost+Decimal('10.31937525')
  event={'event':'slot1_separate_judging_complete','experiment':'E96','as_of_utc':now,'judging_usd':str(cost),'api_usd':str(cost),'E96_cumulative_judging_usd':str(total),'gpu_hours':0,'gpu_usd':0,'basis':'separatephysicalledgeractual; no doublebooking of primary; unusedallocationreleased'}
  ledger=shared/'results/g_agreement/compute.jsonl'
  if any(json.loads(x).get('event')==event['event'] for x in ledger.read_text().splitlines()):raise RuntimeError('cost already booked; reconcile publication')
  with ledger.open('a') as f:f.write(json.dumps(event)+'\n')
  for p,line in [(shared/'results/g_agreement/log.md',f'E96 {now}: separate17920judgment/analysissealedONCE,actual{cost}USD, primaryunchanged; slot1_second_final_scientific/PUBLICATION_SEAL.json'),(shared/'results/g_agreement/status/I-4.md',f'E96 materialseal {now}: separate17920judged/analyzedONCE,R4pending; actualnew{cost}USD,cumulative{total},open0,newallocation0,unused{50-cost}released; noGPU. Primary35200reviewedimmutable. E106 remains scientificdefinitionhold until explicitruling.'),(shared/'results/g_agreement/reviews/R-4/HANDOFF.md',f'ARRIVAL I-4→R-4 {now}: slot1_second_final_scientific/PUBLICATION_SEAL.json COMPLETE separate17920/rawjudgedrecords/itemarrays/exactcode/BRIEFregistrationrefs/indices/attempts/cost. Please independentbootstrap/rulelines onarrival. No retainedprimarypooling/replay.')]:
   with p.open('a') as f:f.write('\n'+line+'\n')
  # Publication scan covers decompressed scientific members; lexical task- false positives are logged, never recoded.
  rx=re.compile(rb'(?:hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,})');exceptions=[]
  def check(name,data):
   matches=list(rx.finditer(data))
   if matches:
    if not all(data[max(0,x.start()-2):x.start()]==b'ta' for x in matches):raise RuntimeError('publication secret-pattern review required; no push')
    exceptions.append({'member':name,'sha256':hashlib.sha256(data).hexdigest(),'count':len(matches),'reason':'sk- substring inside generated word task-; scientific text unchanged'})
  for p in package.rglob('*'):
   if not p.is_file():continue
   if p.name.endswith('.tar.gz'):
    with tarfile.open(p) as ar:
     for m in ar.getmembers():
      if m.isfile():check(str(p.relative_to(package))+':'+m.name,ar.extractfile(m).read())
   elif p.suffix=='.gz':check(str(p.relative_to(package)),gzip.decompress(p.read_bytes()))
   else:check(str(p.relative_to(package)),p.read_bytes())
  write(package/'SECRET_SCAN.json',{'status':'PASS','lexical_exceptions':exceptions})
  write(package/'PUBLICATION_SEAL.json',{'experiment':'E96_SLOT1_SECOND_FINAL_SEPARATE','status':'COMPLETE_ONCE_R4_PENDING','sealed_utc':now,'first_output_utc':az['first_output_utc'],'primary_unchanged':True,'no_pooling_or_primary_reexecution':True,'files':{str(p.relative_to(package)):digest(p) for p in package.rglob('*') if p.is_file() and p.name!='PUBLICATION_SEAL.json'}})
  git('add',str(package.relative_to(shared)),'results/g_agreement/compute.jsonl','results/g_agreement/log.md','results/g_agreement/status/I-4.md','results/g_agreement/reviews/R-4/HANDOFF.md')
  git('commit','-m','E96 separate slot1 complete once analysis raw judgments source and R4 handoff')
  for _ in range(3):
   rebase=git('pull','--rebase','origin','r/blindspot',check=False)
   if rebase.returncode:
    conflicts=git('diff','--name-only','--diff-filter=U').stdout.splitlines()
    allowed={'results/g_agreement/compute.jsonl','results/g_agreement/log.md','results/g_agreement/status/I-4.md','results/g_agreement/reviews/R-4/HANDOFF.md'}
    if not conflicts or not set(conflicts)<=allowed:raise RuntimeError('non-append publication conflict; manual Git repair, no analysis replay')
    for name in conflicts:
     p=shared/name;p.write_text(''.join(x for x in p.read_text().splitlines(keepends=True) if not x.startswith(('<<<<<<<','=======','>>>>>>>'))));git('add',name)
    subprocess.run(['git','-c','core.editor=true','rebase','--continue'],cwd=shared,check=True,capture_output=True)
   pushed=git('push','origin','HEAD:r/blindspot',check=False)
   if pushed.returncode==0:
    receipt={'published_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'shared_commit':git('rev-parse','HEAD').stdout.strip(),'package':'results/g_agreement/e96/slot1_second_final_scientific','first_output_utc':az['first_output_utc']};write(base/'PUBLISHED.json',receipt);return receipt
  raise RuntimeError('publication races exhausted; resume Git only')
