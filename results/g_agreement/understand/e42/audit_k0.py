"""§151 clarification 2: prefixes and frozen labels only; no following text or scores."""
from io42 import *
from states import state
from collections import Counter
import argparse

def audit(out):
 inv=read(HERE/'INVENTORY.json');p=HERE/'cache/prepared/private_items.json'
 if sha(p)!=inv['private_items_sha256']:raise ValueError('private inventory changed')
 from transformers import PreTrainedTokenizerFast
 tp=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B/tokenizer.json')
 if sha(tp)!='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42':raise ValueError('tokenizer changed')
 tok=PreTrainedTokenizerFast(tokenizer_file=str(tp));ledger=[];counts={}
 for item in read(p):
  text=tok.decode(item['ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
  if text!=item['text']:raise ValueError('decoded prefix differs from frozen text')
  actual=state(item,text)
  status='undetermined' if actual is None else 'agree' if actual==item['value'] else 'disagree'
  key=item['bank']+':'+item['feature'];counts.setdefault(key,Counter())[status]+=1
  ledger.append({'key':item['key'],'bank':item['bank'],'feature':item['feature'],'id':item['id'],'expected':item['value'],'actual':actual,'status':status})
 out.mkdir(exist_ok=False)
 summary=[{'row':key,**{s:c[s] for s in ['agree','undetermined','disagree']},'n':sum(c.values()),'excluded':c['undetermined']+c['disagree'],'evaluable':(c['undetermined']+c['disagree'])/sum(c.values())<=.2} for key,c in sorted(counts.items())]
 dump(out/'COUNTS.json',{'rows':summary,'totals':dict(Counter(r['status'] for r in ledger)),'states_sha256':sha(HERE/'states.py'),'private_items_sha256':sha(p),'continuations_read':False,'scores_read':False})
 dump(out/'DISAGREEING_ITEMS.json',[r for r in ledger if r['status']=='disagree'])
 (out/'cache').mkdir()
 dump(out/'cache/ITEM_K0.json',ledger)
 seal(out,['COUNTS.json','DISAGREEING_ITEMS.json','cache/ITEM_K0.json'],'K0_SEAL.json')
 for r in summary:print(r['row'],r['agree'],r['undetermined'],r['disagree'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);audit(p.parse_args().out)
