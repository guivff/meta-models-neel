"""E85 sealed normalized source joins; no generation, judging or prior analysis replay."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from .rules import analyze
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
require,read,write,sha=core.require,core.read,core.write,core.sha
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e85/ANALYSIS_ONCE.json')

def committed():
    for name,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==digest,'changed dependency')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            blob=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            require(hashlib.sha256(blob).hexdigest()==sha(p),'uncommitted adapter')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

import importlib.util
JUDGE=ROOT/'results/g_agreement/understand/e85/judge205.py'
js=importlib.util.spec_from_file_location('e85_frozen_judge',JUDGE);judge=importlib.util.module_from_spec(js);js.loader.exec_module(judge)

def codes(record,text):
    if record is None:return dict(a=None,b=None,c=None)
    judge.validate(record)
    for flag,evidence in [('a_model_self_evaluated','a_evidence'),('b_evaluation_genre_vocabulary','b_evidence'),('c_absent_genre_named','c_evidence')]:
        require(bool(record[evidence])==record[flag] and record[evidence] in text,'verbatim affirmative evidence; absent flag has no evidence')
    return dict(a=record['a_model_self_evaluated'],b=record['b_evaluation_genre_vocabulary'],c=record['c_absent_genre_named'])

def original_code(record,text):
    if record is None:return None
    require(set(record)=={'id','eval_mention','evidence'} and type(record['eval_mention']) is bool,'original S6 schema')
    require(type(record['evidence']) is str and record['evidence'] in text and bool(record['evidence'])==record['eval_mention'],'original evidence')
    return record['eval_mention']

def original_ids(ids):
    # Byte-equivalent selection to frozen blind_judge/rubric202.py, avoiding
    # importing the API runner into this CPU-only adapter.
    require(len(ids)==len(set(ids)) and bool(ids),'unique seeded sample scope')
    return set(sorted(ids,key=lambda x:hashlib.sha256(f'20261028:E85:{x}'.encode()).digest())[:(len(ids)+3)//4])

def inventory(private):
    by=core.unique(private,'public_id');require(len(private)==600,'original600 item inventory')
    groups={}
    for x in private:
        require(x['split'] in ('test','dev') and x['genre'] in (0,1) and x['addressed'] in (0,1),'frozen factors/split')
        groups.setdefault(x['matched_set'],[]).append(x)
    require(len(groups)==150,'150 matched quartets')
    for group in groups.values():
        require(len(group)==4 and {(x['genre'],x['addressed']) for x in group}=={(0,0),(0,1),(1,0),(1,1)} and len({x['split'] for x in group})==1,'complete split-disjoint matched quartet')
    require(sum(x['split']=='test' for x in private)==400,'100test50dev quartets')
    return by

def inputs(s):
    cfg=read(ROOT/'results/g_agreement/understand/e85/CPU_CONFIG.json')
    require(sha(s['private'])==cfg['private_sha256'],'original CPU-private label freeze')
    by=inventory(read(s['private']));test={k:v for k,v in by.items() if v['split']=='test'}
    op=Path(s['output_seal']);seal=core.verify(op,s['output_sha256'])
    require(seal['experiment']=='E85' and seal['status']=='COMPLETE','complete E85 bank')
    require(seal['input_seal_sha256']==cfg['input_seal_sha256'] and seal['private_sha256']==cfg['private_sha256'],'original bank custody')
    require(seal['route_verified'] is True and seal['redaction_audit_complete'] is True,'existing route/privacy receipts')
    require(seal['judge205_sha256']==sha(JUDGE) and seal['original_rubric_comparison_verified'] is True,'frozen judge205 and seeded25percent original comparison')
    require(set(('MEASUREMENTS.json','DIAGNOSTICS.json'))<=set(seal['files']),'sealed measurements and diagnostic pointers')
    sources=seal['source_seals'];ss=[core.verify(x['seal'],x['sha256']) for x in sources];cache={}
    def resolve(ref):
        ix=ref['seal_index'];require(type(ix) is int and 0<=ix<len(ss),'source index')
        require(ref['member'] in ss[ix]['files'],'original sealed member')
        key=(ix,ref['member'])
        if key not in cache:cache[key]=read(Path(sources[ix]['seal']).parent/ref['member'])
        value=cache[key]
        for k in ref['keys']:value=value[k]
        return value
    ms=read(op.parent/'MEASUREMENTS.json');core.unique(ms)
    require(len(ms)==800 and {(x['item_id'],x['reader']) for x in ms}=={(i,r) for i in test for r in ('oracle','nla')},'exact800 native readout grid')
    wanted=set(seal['original_subsample_ids']);require(wanted==original_ids([x['id'] for x in ms]),'seeded25percent comparison inventory')
    rows=[]
    for m in ms:
        meta=test[m['item_id']];f=m['fields'];required={'text','code','original_code'} if m['id'] in wanted else {'text','code'}
        require(set(f)==required,'exact judged source fields')
        text=resolve(f['text']);c=codes(resolve(f['code']),text)
        orig=original_code(resolve(f['original_code']),text) if m['id'] in wanted else None
        rows.append(dict(id=m['id'],matched_set=meta['matched_set'],genre=meta['genre'],addressed=meta['addressed'],reader=m['reader'],original=orig,original_selected=m['id'] in wanted,**c))
    ds=read(op.parent/'DIAGNOSTICS.json');require(set(ds)=={'probes','bow','behaviour'},'all frozen descriptive checks')
    diagnostics={k:resolve(v) for k,v in ds.items()};probes=diagnostics['probes']
    require(len(probes)==4 and {(x['name'],x['layer']) for x in probes}=={(n,l) for n in ('genre','addressed') for l in (42,44)},'both probes at both read sites')
    for p in probes:
        require(p['status'] in ('COMPLETE','NOT EVALUABLE'),'probe disposition')
        if p['status']=='COMPLETE':require(type(p['test_auroc']) in (int,float) and 0<=p['test_auroc']<=1,'testAUROC gate')
    # Only numeric aggregate diagnostics may enter the published report.
    bow=diagnostics['bow']
    require(set(bow)=={'genre','addressed'} and all(type(bow[k]['test_auroc']) in (int,float) and 0<=bow[k]['test_auroc']<=1 for k in bow),'BOW aggregate schema')
    diagnostics['bow']={k:dict(test_auroc=bow[k]['test_auroc'],descriptive=True,gate=False) for k in bow}
    b=diagnostics['behaviour']
    if b is not None:
        require(set(b)=={'pairs','different','missing','comparison'} and b['comparison']=='exact_answer_text' and all(type(b[k]) is int for k in ('pairs','different','missing')) and b['pairs']==200 and 0<=b['different']<=b['pairs']-b['missing']<=200,'downstream aggregate schema')
    return rows,diagnostics

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=read(a.spec);rows,d=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['output_sha256']),commit)
    result=analyze(rows,**d);write(out/'RESULTS.json',result);write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E85',status='COMPLETE_ONCE',code_commit=commit,output_sha256=s['output_sha256'])
if __name__=='__main__':main()
