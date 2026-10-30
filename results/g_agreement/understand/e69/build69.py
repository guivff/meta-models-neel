"""E69 suffix-only bank; verify frozen inputs and probe-only selection before writing."""
import hashlib,json,tarfile
from pathlib import Path
from collections import Counter
from sklearn.metrics import roc_auc_score
from transformers import PreTrainedTokenizerFast
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'results/g_agreement/understand'
MECH=ROOT.parent/'wt-wmech'
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
CONDITIONS={
'asserted_vs_hypothetical':('the final event in the preceding passage is asserted as actual','the final event in the preceding passage is hypothetical'),
'branch_taken':('the final if condition in the preceding code evaluates to true','the final if condition in the preceding code evaluates to false'),
'container_after_move':('the tracked object in the preceding passage is now in the cup','the tracked object in the preceding passage is now in the bowl'),
'unit_system':('the active measurement instruction in the preceding passage calls for metric units','the active measurement instruction in the preceding passage calls for imperial units'),
'user_expertise':('the preceding user describes expert familiarity with the topic','the preceding user describes novice familiarity with the topic'),
'var_type_at_use':('x at the final use in the preceding code is an integer','x at the final use in the preceding code is a string'),
'subject_number':('the pending subject at the end of the preceding passage is singular','the pending subject at the end of the preceding passage is plural'),
'clause_pending':('a main clause is still owed at the end of the preceding passage','no main clause is still owed at the end of the preceding passage'),
'nesting_depth':('one bracket remains open at the end of the preceding passage','three brackets remain open at the end of the preceding passage'),
'indent_level':('the final code line in the preceding passage is indented four spaces','the final code line in the preceding passage is indented twelve spaces'),
'loop_direction':('the final loop in the preceding code is decrementing','the final loop in the preceding code is incrementing'),
'page_range_digit':('the current citation’s first page number begins with 1, 2, 3, or 4','the current citation’s first page number begins with 6, 7, 8, or 9'),
'section_header':('the final read word in the preceding passage belongs to a section header','the final read word in the preceding passage belongs to body prose')}
GROUP_B=list(CONDITIONS)[6:]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def verified(p,seal,key):
 assert sha(p)==read(seal)['files'][key],str(p)
 return read(p)
def suffix(condition):return f"\nIf {condition}, reply 'alpha'; otherwise reply 'beta'.\nReply:"
def main():
 out=HERE/'cache/bank_2026-10-27_v2';out.mkdir(parents=True,exist_ok=False)
 a=BASE/'e49/cache/frozen_2026-10-26';b=BASE/'e57/cache/bank_2026-10-27_v1'
 items49=verified(a/'items.PRIVATE.json',a/'BANK_SEAL.json','items.PRIVATE.json')
 items57=verified(b/'items.PRIVATE.json',BASE/'e57/BANK_SEAL.json','items.PRIVATE.json')
 analysis=MECH/'results/g_agreement/understand/e49/job/analysis'
 assert sha(analysis/'RESULTS.md')==read(analysis/'ANALYSIS_SEAL.json')['files']['RESULTS.md']
 missed=[line.split('|')[1].strip() for line in (analysis/'RESULTS.md').read_text().splitlines() if line.endswith('MISSED |')]
 assert set(missed)==set(list(CONDITIONS)[:6])
 scores={};sources=[]
 cpu=MECH/'cache/g_agreement/understand/e56_e57/verified_pull_single_v1/e57/cpu'
 for d in sorted(cpu.glob('shard_*')):
  seal=d/'CPU_SEAL.json';assert read(seal)['private_items_sha256']==sha(b/'items.PRIVATE.json')
  for i in verified(d/'PROBE.json',seal,'PROBE.json'):
   assert i['id'] not in scores;scores[i['id']]=i['score']
  sources.append({'path':str(seal),'sha256':sha(seal),'probe_sha256':sha(d/'PROBE.json')})
 gates={}
 for row in GROUP_B:
  its=[i for i in items57 if i['feature']==row and i['split']=='test'];assert len(its)==84
  gates[row]={'probe_auroc':float(roc_auc_score([i['label'] for i in its],[scores[i['id']] for i in its]))}
  gates[row]['included']=gates[row]['probe_auroc']>=.90
 chosen={'E49':missed,'E57':[r for r in GROUP_B if gates[r]['included']]}
 assert sha(TOKENIZER)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
 tok=PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))
 answer_ids=[tok.encode(s,add_special_tokens=False) for s in [' alpha',' beta']];assert all(len(x)==1 for x in answer_ids)
 records=[];private=[]
 for bank,items in [('E49',items49),('E57',items57)]:
  for i in items:
   row=i['feature']
   if i['split']!='test' or row not in chosen[bank]:continue
   assert tok.encode(i['text'],add_special_tokens=False)==i['ids']
   for arm,k in [('normal',0),('swapped',1)]:
    suf=suffix(CONDITIONS[row][k]);text=i['text']+suf;ids=tok.encode(text,add_special_tokens=False)
    assert ids[:len(i['ids'])]==i['ids']
    rid=f'{bank}/{i["id"]}/{arm}'
    records.append({'id':rid,'bank':bank,'feature':row,'source_item_id':i['id'],'arm':arm,'text':text,'ids':ids,'source_prefix_tokens':len(i['ids']),'source_text_sha256':hashlib.sha256(i['text'].encode()).hexdigest(),'read_index':len(ids)-1,'suffix':suf})
    private.append({'id':rid,'label':i['label'],'value':i['value'],'alpha_target':i['label'] if k==0 else 1-i['label']})
 counts=Counter((i['bank'],i['feature'],i['arm']) for i in records);assert set(counts.values())=={84}
 for key in counts:
  same=[i for i in records if (i['bank'],i['feature'],i['arm'])==key];assert len({i['suffix'] for i in same})==1
 write(out/'INPUTS.json',records);write(out/'LABELS.PRIVATE.json',private)
 selection={'authority':'§186, 8b2012d7','selected':chosen,'E57_group_B_gates':gates,'probe_sources':sources,'E49_analysis_seal':{'path':str(analysis/'ANALYSIS_SEAL.json'),'sha256':sha(analysis/'ANALYSIS_SEAL.json')},'source_banks':[{'bank':'E49','seal_sha256':sha(a/'BANK_SEAL.json'),'items_sha256':sha(a/'items.PRIVATE.json')},{'bank':'E57','seal_sha256':sha(BASE/'e57/BANK_SEAL.json'),'items_sha256':sha(b/'items.PRIVATE.json')}]}
 write(HERE/'SELECTION.json',selection);write(HERE/'SUFFIXES.json',{r:{'A':v[0],'B':v[1],'normal':suffix(v[0]),'swapped':suffix(v[1])} for r,v in CONDITIONS.items()})
 write(HERE/'VALIDATION.json',{'records':len(records),'rows':sum(map(len,chosen.values())),'per_row_per_arm':84,'unchanged_source_ids':True,'identical_suffix_across_values':True,'alpha_beta_token_ids':answer_ids,'test_only':True,'reader_outcomes_opened_for_E57':False})
 seal={'experiment':'E69','status':'FROZEN','authority_commit':'8b2012d7','files':{str(p.relative_to(HERE)):sha(p) for p in [out/'INPUTS.json',out/'LABELS.PRIVATE.json',HERE/'SELECTION.json',HERE/'SUFFIXES.json',HERE/'VALIDATION.json',Path(__file__)]},'tokenizer_sha256':sha(TOKENIZER)}
 write(HERE/'BANK_SEAL.json',seal)
 archive=HERE/'cache/E69_BANK_2026-10-27.tar.gz'
 with tarfile.open(archive,'w:gz') as tf:
  for p in [out/'INPUTS.json',out/'LABELS.PRIVATE.json',HERE/'BANK_SEAL.json',HERE/'SELECTION.json',HERE/'SUFFIXES.json']:tf.add(p,arcname=str(p.relative_to(HERE)))
 write(HERE/'LAUNCH_REQUEST.json',{'experiment':'E69','owner':'W-mechanism runner; integrator launches','status':'BANK_READY','bank_seal_sha256':sha(HERE/'BANK_SEAL.json'),'archive_path':str(archive),'archive_sha256':sha(archive),'inputs_path':str(out/'INPUTS.json'),'private_labels_CPU_only':str(out/'LABELS.PRIVATE.json'),'gpu_cap_seconds':1080,'model':'base Qwen3.6-27B','score':'P( alpha) - P( beta) at final token, full-vocabulary softmax','normal_target':'original A label (A=1)','swapped_target':'original B label (B=1); also report against original A to expose reversal','reader_runs':False,'rules':'§186 R-B1 and falsifier unchanged; normal arm determines rule, swap reported as control','answer_ids':answer_ids})
 print(json.dumps({'selected':chosen,'gates':gates,'records':len(records),'seal':sha(HERE/'BANK_SEAL.json')},indent=2))
if __name__=='__main__':main()
