"""Blind E88 packet export only. Does not call a judge or calculate agreement."""
import hashlib,json,os
from pathlib import Path
from audit import HERE,ROOT,CACHE,read,sha,write
def values(v):
 if isinstance(v,dict):assert set(v)=={'A','B'};return v
 assert isinstance(v,list)and len(v)==2;return dict(zip(['A','B'],v))
def main():
 base=ROOT/'results/g_agreement/understand/blind_judge/e66_e68/E68_RUBRIC.md'
 amended=ROOT/'results/g_agreement/understand/blind_judge/later_banks/RUBRIC202_VALUE.txt'
 sample=read(CACHE/'ITEM5_SAMPLE_v2.PRIVATE.json');inventory=read(CACHE/'ITEM6_INVENTORY_v2.PRIVATE.json')
 out=CACHE/'judging_packets';out.mkdir(exist_ok=False,mode=0o700)
 packets={};keys={}
 for part,xs in [('5',sample['records']),('6',inventory)]:
  wire=[];join=[]
  for n,x in enumerate(xs):
   uid=x['id']if part=='5'else hashlib.sha256(('E88-6|'+x['bank']+'|'+x['reader']+'|'+x['opaque_id']).encode()).hexdigest()[:32]
   wire.append(dict(id=uid,readout=x.get('readout',x.get('text')),property=x['property'],values=values(x['values'])))
   join.append(dict(id=uid,source_opaque_id=x.get('opaque_id'),bank=x.get('bank'),reader=x.get('reader'),row=x.get('feature'),pair_id=x.get('pair_id'))if part=='6'else sample['key'][n])
  assert len(wire)==len({x['id']for x in wire})==(300 if part=='5'else 3024)
  assert all(set(x)=={'id','readout','property','values'}for x in wire)
  name='ITEM'+part+'_BLIND_PACKET.json';write(out/name,wire);write(out/('ITEM'+part+'_JOIN.PRIVATE.json'),join)
  rubric=base if part=='5'else amended
  packets[part]=dict(path=str(out/name),sha256=sha(out/name),n=len(wire),rubric_path=str(rubric),rubric_sha256=sha(rubric),status='READY_FOR_TRACK_Q_CUSTODY_NO_DISPATCH')
  keys[part]=dict(path=str(out/('ITEM'+part+'_JOIN.PRIVATE.json')),sha256=sha(out/('ITEM'+part+'_JOIN.PRIVATE.json')))
 for p in out.iterdir():os.chmod(p,0o600)
 request=dict(experiment='E88',packets=packets,private_joins=keys,source_script_sha256=sha(__file__),authority='Direct user: W-lens owns items1-5 and item6 analysis; item6 judging via Track Q',item5_route='Second judge only, route explicitly authorised by Guiv; Track Q status names pending sonnet-5 route from W-internals; cap USD2',item6_route='Track Q §172+§202, cap USD6 under §204 ledger',no_api_calls_by_wlens=True,no_truth_or_primary_judgments_in_wire=True,analysis_after_terminal_returns=True,item5_caveat='E49 primary baseline is frozen regex, not a primary judge model; identify that distinction in agreement reports')
 write(HERE/'JUDGING_REQUEST.json',request)
 print('Blind packet exports sealed: item5=300, item6=3024; no judging calls')
if __name__=='__main__':main()
