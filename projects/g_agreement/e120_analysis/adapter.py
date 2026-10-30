"""§230 E120(a): original E85 matched-item bootstrap at blocks 52 and 60."""
import argparse
import hashlib
import subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core as c
from projects.g_agreement.e85_analysis.adapter import inventory, codes, JUDGE
from projects.g_agreement.e85_analysis.rules import summarize, DRAWS, SEED
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
BLOCKS=(52,60)
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e120/part_a/ANALYSIS_ONCE.json'


def verdict(effects):
    positive=any(v['estimate'] is not None and round(v['estimate'],12)>=.20 and v['CI95'] is not None and v['CI95'][0]>0 for v in effects.values())
    complete=all(v['estimate'] is not None and v['CI95'] is not None for v in effects.values())
    low=all(v['estimate'] is not None and round(v['estimate'],12)<=.05 for v in effects.values())
    return dict(R_EV1='MET' if positive else 'NOT MET' if complete else 'NOT EVALUABLE',
                not_timing_at_these_layers='MET' if low else 'NOT EVALUABLE' if any(v['estimate'] is None for v in effects.values()) else 'NOT MET',
                descriptive=True)


def analyze(rows):
    c.unique(rows)
    c.require(len(rows)==800 and {x['block'] for x in rows}==set(BLOCKS),'exact800 readouts at52/60')
    by={b:[x for x in rows if x['block']==b] for b in BLOCKS}
    for xs in by.values():
        c.require(len(xs)==400 and len({x['item_id'] for x in xs})==400,'400 unique test items per block')
        c.require(all(x['genre'] in (0,1) and x['addressed'] in (0,1) and (x['a'] is None or type(x['a']) is bool) for x in xs),'frozen factors and boolean-or-missing eval mention')
    meta=lambda xs:{x['item_id']:(x['matched_set'],x['genre'],x['addressed']) for x in xs}
    c.require(meta(by[52])==meta(by[60]),'same original items and factors at both blocks')
    blocks={b:summarize(xs,'a') for b,xs in by.items()}
    c.require(all(x['matched_sets']==100 and all(z['total']==100 for z in x['cells'].values()) for x in blocks.values()),'original100 test quartets')
    return dict(experiment='E120',part='a',authority='§230',blocks=blocks,
                rules=verdict({b:x['effects']['addressed'] for b,x in blocks.items()}),
                bootstrap=dict(draws=DRAWS,seed=SEED,unit='original matched item quartet',paired_cells=True,source='unchanged E85 summarize'),
                scope='Explicit system-prompt evaluation cue; descriptive timing reading, not organic evaluation awareness')


def judgment(m,ref):
    f=m['fields'];cp=f['code'];jp=f['judgment_id']
    c.require(cp['seal_index']==jp['seal_index'] and cp['member']==jp['member']
              and cp['keys'] and cp['keys'][-1]=='code'
              and jp['keys']==cp['keys'][:-1]+['id'],'judgment ID and code are siblings in original row')
    c.require(ref(jp)==m['judgment_id'],'original judgment identity')
    return codes(ref(cp),ref(f['text']))


def validate_config(p,cfg,ids,test_ids):
    c.require(p['experiment']=='E120' and p['part']=='a' and p['oracle_read_layers']==[52,60] and p['source_capture_layers']==[52,60] and p['items']==400 and p['readouts']==800 and p['split']=='test','original timing scope')
    c.require(p['cpu_only_labels']['sha256']==cfg['private_sha256'] and p['cpu_only_labels']['stage_to_pod'] is False and p['labels_on_pod'] is False,'original private custody')
    c.require(p['source_public']['sha256']==cfg['input_seal_sha256'],'original E85 public source')
    c.require(p['reader']['temperature']==0 and p['reader']['k']==1 and p['reader']['max_new_tokens']==128 and p['native_alpha']==16000 and p['native_transform']=='unit' and p['capture']['patches'] is False,'original native reader')
    c.require(len(ids)==400 and len(set(ids))==400 and set(ids)==set(test_ids),'exact original400 TEST identities')


def validate_plan(s,cfg,test_ids):
    if s.get('plan_mode')=='original_config_and_inputs':
        import json
        commit='39b1116039e0f12bed4c6755c8154449381a71b0'
        c.require(s['plan_commit']==commit and s['plan_sha256']=='34d8cb266f3d0c26dab7b49906489931defba5299d2ea463121f7cdcea43fad9','original committed timing pin')
        raw=subprocess.check_output(['git','show',commit+':projects/g_agreement/e120/timing.json'],cwd=ROOT)
        c.require(hashlib.sha256(raw).hexdigest()==s['plan_sha256'],'original timing bytes')
        p=json.loads(raw);ip=Path(s['original_input_seal']);seal=c.verify(ip,p['public_input']['input_sha256'])
        c.require('items.json' in seal['files'],'original timing input inventory')
        items=c.read(ip.parent/'items.json')
        validate_config(p,cfg,[x['id'] for x in items],test_ids)
        return
    plan=Path(s['plan']).resolve()
    c.require(c.sha(plan)==s['plan_sha256'] and hashlib.sha256(subprocess.check_output(['git','show',s['plan_commit']+':'+str(plan.relative_to(ROOT))],cwd=ROOT)).hexdigest()==s['plan_sha256'],'committed pre-output source plan')
    p=c.read(plan)
    c.require(p['experiment']=='E120' and p['part']=='a' and p['blocks']==[52,60] and p['items']==400 and p['greedy'] is True,'registered timing plan')
    c.require(p['private_sha256']==cfg['private_sha256'] and p['input_seal_sha256']==cfg['input_seal_sha256'],'original E85 plan custody')


def inputs(s):
    cfg=c.read(ROOT/'results/g_agreement/understand/e85/CPU_CONFIG.json')
    c.require(c.sha(s['private'])==cfg['private_sha256'],'original frozen E85 private600')
    test={k:v for k,v in inventory(c.read(s['private'])).items() if v['split']=='test'}
    validate_plan(s,cfg,test)
    op=Path(s['binding_seal']);seal=c.verify(op,s['binding_sha256'])
    c.require(seal['experiment']=='E120' and seal['part']=='a' and seal['status']=='COMPLETE','complete terminal timing bank')
    for key,value in [('private_sha256',cfg['private_sha256']),('input_seal_sha256',cfg['input_seal_sha256']),('plan_sha256',s['plan_sha256']),('judge205_sha256',c.sha(JUDGE))]:
        c.require(seal[key]==value,'frozen '+key)
    for key in ('route_verified','redaction_audit_complete','labels_cpu_only','same_E85_prompts_and_read_token_verified','native_Oracle_greedy_verified','source_plan_precedes_output_verified'):
        c.require(seal[key] is True,key)
    c.require('MEASUREMENTS.json' in seal['files'],'sealed full measurements')
    sources=seal['source_seals'];ss=[c.verify(x['seal'],x['sha256']) for x in sources];cache={}
    def ref(r):
        i=r['seal_index'];c.require(type(i) is int and 0<=i<len(ss) and r['member'] in ss[i]['files'],'original member pointer')
        key=(i,r['member'])
        if key not in cache:cache[key]=c.read(Path(sources[i]['seal']).parent/r['member'])
        v=cache[key]
        for k in r['keys']:v=v[k]
        return v
    ms=c.read(op.parent/'MEASUREMENTS.json');c.unique(ms)
    c.require(len(ms)==800 and {(x['item_id'],x['block']) for x in ms}=={(i,b) for i in test for b in BLOCKS},'all and only original400×2')
    out=[]
    for m in ms:
        meta=test[m['item_id']];f=m['fields']
        c.require(set(f)=={'item_id','block','text','code','judgment_id'},'exact original source fields')
        c.require(ref(f['item_id'])==m['item_id'] and ref(f['block'])==m['block'],'original source identity/block')
        scored=judgment(m,ref)
        out.append(dict(id=m['id'],item_id=m['item_id'],block=m['block'],matched_set=meta['matched_set'],genre=meta['genre'],addressed=meta['addressed'],a=scored['a']))
    return out


def committed():
    for f,h in c.read(HERE/'SOURCE_RECEIPT.json')['files'].items():
        c.require(c.sha(ROOT/f)==h and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+f],cwd=ROOT)).hexdigest()==h,'committed source receipt')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args()
    commit=committed();s=c.read(a.spec);rows=inputs(s)
    out=c.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['binding_sha256']),commit)
    c.write(out/'RESULTS.json',analyze(rows));c.write(out/'BINDING.json',s)
    c.seal(out,'ANALYSIS_SEAL.json',experiment='E120',part='a',status='COMPLETE_ONCE',code_commit=commit)
if __name__=='__main__':main()
