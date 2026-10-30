"""650138c5: frozen S5 L4p test construction cross-tab, no reader/probe reads."""
from pathlib import Path
import json,hashlib,math
HERE=Path(__file__).resolve().parent
EXPECTED='862e4e7981a4f70cd85d6453194df72cd0f47b3c762361f70e8046de8a196dfd'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 bank=HERE/'cache/bank_2026-10-27';assert sha(bank/'BANK_SEAL.json')==EXPECTED
 seal=json.loads((bank/'BANK_SEAL.json').read_text())
 for name in ['items.PRIVATE.json','DECISIONS.PRIVATE.json']:assert sha(bank/name)==seal['files'][name]
 items=json.loads((bank/'items.PRIVATE.json').read_text());decisions=json.loads((bank/'DECISIONS.PRIVATE.json').read_text())
 rows=[x for x in items if x['state']=='S5' and x['rung']=='L4p' and x['split']=='test'];assert len(rows)==84
 table={v:{a:0 for a in ['alpha','beta']} for v in ['singular','plural']}
 for x in rows:
  assert x['value'] in table and x['label']==int(x['value']=='singular')
  d=decisions[x['id']];assert d['original_readout_label']==x['value']
  assert d['expected_decision']==('alpha' if d['unrelated_property_count']>=6 else 'beta')
  table[x['value']][d['expected_decision']]+=1
 # phi is Pearson correlation of plural=1 versus alpha=1.
 a=table['plural']['alpha'];b=table['plural']['beta'];c=table['singular']['alpha'];d=table['singular']['beta']
 den=math.sqrt((a+b)*(c+d)*(a+c)*(b+d));assert den>0
 phi=(a*d-b*c)/den
 # Independent centered binary-vector calculation checks sign/orientation.
 xs=[int(x['value']=='plural') for x in rows];ys=[int(decisions[x['id']]['expected_decision']=='alpha') for x in rows]
 mx=sum(xs)/84;my=sum(ys)/84
 check=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
 assert abs(phi-check)<1e-12
 result={'authority':'650138c5, §178 ratification note','bank_seal_sha256':EXPECTED,'state':'S5','rung':'L4p','split':'test','n':84,'cross_tab':table,'phi_encoding':{'target':'plural=1, singular=0','placebo_answer':'alpha=1, beta=0'},'phi':phi,'absolute_phi':abs(phi),'exclusion_threshold':0.2,'exclusion_comparison':'>','exclude_S5_L4p_from_R_L5':abs(phi)>.2,'flag':'PARTLY_CONFOUNDED' if abs(phi)>.2 else 'CHECK_PASSED','source_files':{n:sha(bank/n) for n in ['items.PRIVATE.json','DECISIONS.PRIVATE.json']},'code_sha256':sha(Path(__file__)),'reader_or_probe_files_read':False,'bank_rebuilt':False}
 out=HERE/'S5_L4P_CONFOUND_CHECK_2026-10-27.json'
 with out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
