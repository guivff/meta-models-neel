"""Once-only D4 stage analysis; original frozen lexicon and paired_ratios, independent of D3."""
from worker import *
sys.path.insert(0,str(HERE.parent/'e61/job'))
from analysis_acquired61 import summarize
from acquired_selection61 import select_d3_d4
from displays61 import display_html,select_three
from analysis_io import claim_once

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);a=p.parse_args();m=read(a.manifest);require(m['verified'] is True,'integrator verified pull')
 verify(HERE,'SOURCE_SEAL.json',m['source_seal_sha256'])
 for n,d in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==d,'analysis dependency')
 binding=read(HERE.parent/'e61/job/INPUT_BINDING.json');inp=Path(binding['inputs']);verify(inp,'INPUT_SEAL.json',binding['input_seal_sha256']);items=[x for x in read(inp/'items.json') if x['display']=='D4'];records=[];probs=[];seen=set();pilots=[]
 for sh in m['shards']:
  n=sh['shard'];require(n in range(3) and n not in seen,'three distinct E61 shards');seen.add(n);b=read(HERE/f'E61_{n}_BINDING.json');plan=read(Path(b['inputs'])/'PLAN.json');require(sha(Path(b['inputs'])/'PLAN.json')==b['plan_sha256'],'sealed shard plan')
  root=Path(sh['stage_path']);s=verify(root,'STAGE_SEAL.json',sh['stage_seal_sha256']);require(s['stage']=='D4' and s['status']=='COMPLETE' and s['plan_sha256']==b['plan_sha256'],'complete D4 stage')
  receipt=read(root/'RECEIPT.json');ass=receipt['assignment'];go=receipt['go'];end=validate_go(go,receipt['capture_ready'],ass)
  require(ass['cohort_id']==COHORT and ass['experiment']=='E61' and ass['shard']==n and ass['compute_cap_seconds']==6292 and receipt['completed_epoch']<=end and receipt['parity_status']=='PASS' and receipt['source_sha256']==m['source_seal_sha256'] and receipt['input_sha256']==b['input_seal_sha256'],'stage custody and parity')
  jobs=[j for j in plan['jobs'] if j['stage']=='D4'];require(set(read(root/'COMPLETED.json'))=={j['key'] for j in jobs} and not read(root/'NOT_RUN.json'),'complete D4 owned grid')
  for j in jobs:
   rows=read(root/'jobs'/f'{j["number"]:06d}.json');(probs if j['kind']=='base' else records).extend(rows)
  pilots.extend(x for x in plan['retained_pilots'] if x['stage']=='D4')
 require(seen=={0,1,2},'all D4 shards before once-only analysis')
 pulls={}
 for pull in m['retained_pilot_pulls']:
  root=Path(pull['root']);verify(root,pull['seal_file'],pull['seal_sha256']);pulls[pull['slot']]=read(root/pull['pilot_file'])
 for j in pilots:
  slot,n=map(int,j['original_key'].split(':'));xs=pulls[slot][str(n)];rows=[xs[i] for i in j['indices']];(probs if j['kind']=='base' else records).extend(rows)
 expected={x['id'] for x in items};require(len(probs)==len(expected) and {x['item_id'] for x in probs}==expected,'complete D4 probabilities with retained pilots')
 for reader in ('oracle','nla'):
  xs=[x for x in records if x['reader']==reader];require(len(xs)==len(expected) and {x['item_id'] for x in xs}==expected and all(x['display']=='D4' and x['repeat']==0 and x['relative_position']==0 for x in xs),'one D4 native per item/reader')
 out=claim_once(ROOT/'results/g_agreement/understand/e61/d4_stage_analysis','E61_D4',sha(a.manifest));result=summarize(items,records,probs,read(inp/'LEXICON.json'));selection={'D4_base_items':select_three(sorted({x['pair_id'] for x in items})),'seed':20261027,'authority':'6f9088bb; all three framings acquired'}
 dump(out/'RESULTS.json',{r:result[r]['D4'] for r in ('oracle','nla')});dump(out/'NLA_TRUNCATION.json',result['nla']['truncation']);dump(out/'ACQUIRED_SELECTION.json',selection);chosen=[dict(x,unit_id=x['id']) for x in records if x['pair_id'] in selection['D4_base_items']];dump(out/'SELECTED_VERBATIM.json',chosen);(out/'SELECTED_VERBATIM.html').write_text(display_html('E61 D4',chosen));(out/'RESULTS.md').write_text('\n'.join(r+': R-W '+result[r]['D4']['R_W'] for r in ('oracle','nla'))+'\n');seal(out,'ANALYSIS_SEAL.json',{'status':'COMPLETE','cohort_id':COHORT,'stage':'D4','manifest_sha256':sha(a.manifest)})
if __name__=='__main__':main()
