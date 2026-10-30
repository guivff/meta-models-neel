import json,hashlib,datetime,collections
from pathlib import Path
import torch
from transformers import AutoTokenizer
from projects.g_agreement.core.scoring_lo import token_variants,lo_jlens
from projects.g_agreement.r_bench import section49 as S
from projects.g_agreement.core.readers import JLensReader
reg=S.REG;old=Path('cache/g_agreement/r/remainder/section49/4jtfvnqizafxfr/final')
tokdir=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9')
tok=AutoTokenizer.from_pretrained(str(tokdir),local_files_only=True)
bank={r['id']:r for r in S.read(reg/'plan.json')['records']};fail=[];replayed=[]
for name in ['jlens','rlens','jpp']:
 bad=[r for r in S.rows(old/'smoke'/f'{name}.jsonl') if r['status']=='MISSING'];fail+=bad
 for r in bad:
  reader=JLensReader();reader.name=name;reader.tokenizer=tok;reader.J={44:torch.zeros(1,1)};reader.w_u=torch.zeros(1,1)
  result=lo_jlens(reader,torch.zeros(1,1),[(r['native']['cand_A'],r['native']['cand_B'])],layer=44)[0]
  assert all(result[k]==r['native'][k] for k in result)
 replayed.append({'reader':name,'reproduced_missing_cells':len(bad)})
coverage=[]
for r in bank.values():
 d=bank[r['donor']];a,b=S.reader_candidates('jlens',r,d)
 coverage.append({'item':r['id'],'donor':r['donor'],'original_candidates':[r['bridge'],d['bridge']],'registered_lens_candidates':[a,b],'variants_A':token_variants(tok,a),'variants_B':token_variants(tok,b),'old_scorable':bool(token_variants(tok,r['bridge']) and token_variants(tok,d['bridge']))})
new_bad=[r for r in coverage if not r['variants_A'] or not r['variants_B']]
assert not new_bad,new_bad
S.save(reg/'SHARDS_MISSING_PAYLOADS.json',{'source_manifest_sha256':S.sha(old/'manifest.json'),'source_table_hashes':{n:S.sha(old/'smoke'/f'{n}.jsonl') for n in ['jlens','rlens','jpp']},'cells':fail})
S.save(reg/'SHARDS_CPU_DIAGNOSTIC.json',{'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cpu_only':True,'gpu_hours':0,'original_missing_cells':len(fail),'replay':replayed,'replay_note':'Native missing branch replay with pinned local tokenizer and placeholder1x1 matrices; no numerical lens score claimed. Payload equality checked against saved native output.','diagnosis':'Runner ignored frozen bridge_jlens forms used by SWAP reader_pair; native single-token scorer behaved correctly. Restore existing frozen forms for J/R/J++; no new aliases or exclusions. Explicit prospective candidate-string correction supersedes attempt4 prohibition.','tokenizer_files':{p.name:S.sha(p) for p in tokdir.glob('tokenizer*.json')},'old_unscorable_pairs':sum(not r['old_scorable'] for r in coverage),'new_unscorable_pairs':len(new_bad),'all196':coverage})
print(json.dumps({'old_missing_pairs':sum(not r['old_scorable'] for r in coverage),'new_missing_pairs':len(new_bad),'replayed':replayed,'shard_sizes':[s['n'] for s in S.read(reg/'shards.json')['shards']]}))
