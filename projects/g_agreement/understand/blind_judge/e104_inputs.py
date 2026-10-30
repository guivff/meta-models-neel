"""CPU exact-source normalizer for the existing precommitted E104 interface."""
from pathlib import Path
from .run import ROOT
from . import e104_judging as e
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
BASE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis402_verified/E104/U_test')
INPUTS=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement/r_ops/e104U_test_bind')
DOSE_SHA='5d921857d24a7a1a6c98e6fe95c753b60a3d8e46e25616757dcaa9f19e8f7bbb'
DOSE_COMMIT='490f23af0e336b17da65537c9e38ab3fde8ec89e'
SHARDS={
 'fact_recall':('1e91a33f801d1eff72641fee56fa718957c65f57a7667fea5b5145a8db77b04a','276968c827ffc1c4163f4351d871e85141d1c43fbbcb7467809b5656910d278c'),
 'language_plan':('c76cd41ca9acce20581162cef1b5c0ef4d6efa919959039a1938a9fe13aeaaad','499810189e60a8072338f04b215120cb0ae2b2028186c269ed7cf35b06e55688')}


def build():
    e.source_gate();cfg=read(ROOT/'results/g_agreement/understand/blind_judge/e101_bank/INPUTS.json')
    verify(cfg['targets'],cfg['targets_sha256']);targets={x['id']:x for x in read(Path(cfg['targets']).parent/'TARGETS.json')}
    out=e.CACHE/'normalized';require(not out.exists(),'normalizer already exists; verify/reuse rather than rebuild')
    records=[];sources=[]
    for row,(ih,oh) in SHARDS.items():
        ip=INPUTS/row/'INPUT_SEAL.json';op=BASE/row/'out/OUTPUT_SEAL.json';ins=verify(ip,ih);outs=verify(op,oh)
        require(outs['experiment']=='E104' and outs['status']=='COMPLETE' and outs['input_sha256']==ih,'complete bound production only')
        run=read(op.parent/'RUN.json');require(run['stage']=='test' and run['seed']==20261029 and run['dose_sha256']==DOSE_SHA and run['dose_commit']==DOSE_COMMIT and run['dose_score_field']=='pair_logits','registered test/scorer/committed dev dose')
        manifest=read(ip.parent/'MANIFEST.json');require(manifest['stage']=='test' and manifest['dose_sha256']==DOSE_SHA and manifest['dose_commit']==DOSE_COMMIT,'pretest dose input binding')
        xs=read(ip.parent/'items.json');require(len(xs)==168 and len({x['id'] for x in xs})==168,'84 paired full row')
        grid=read(op.parent/'JOB_GRID.json');require(sorted(read(op.parent/'COMPLETED.json'))==list(range(len(grid))),'all scheduled jobs complete')
        sources.extend([dict(seal=str(ip),sha256=ih),dict(seal=str(op),sha256=oh)]);si=len(sources)-1
        indexed={}
        for j,g in enumerate(grid):
            member=f'jobs/{j:06d}.json';require(member in outs['files'],'sealed job member')
            rs=read(op.parent/member);require([x['id'] for x in rs]==[xs[i]['id'] for i in g['indices']],'job/item order')
            for k,x in enumerate(rs):
                key=x['id'],g['kind'];require(key not in indexed,'unique native/logits source');indexed[key]=(member,k,x)
        require(len(indexed)==2*len(xs),'one native oracle plus behaviour per cell')
        for x in xs:
            require(x['arm']=='U' and x['row']==row and x['condition'] in ('steered','random'),'eligible U cells only')
            lm,li,lr=indexed[x['id'],'logits'];om,oi,orr=indexed[x['id'],'oracle'];t=targets[x['base_id']]
            require(t['split']=='test' and t['row']==row and lr['behaviour_scorer_sha256']==run['behaviour_scorer_sha256'],'CPU frozen targets/scorer')
            require(orr['norm_source_job']==int(lm.split('/')[-1].split('.')[0]),'native reads exact corresponding behaviour job')
            def ref(member,index,field):return dict(seal_index=si,member=member,keys=[index,field])
            records.append(dict(id=x['id'],item_id=x['base_id'],arm='U',row=row,reader='oracle',split='test',alpha=x['alpha'],condition=x['condition'],property=t['property'],values=t['values'],target=t['target'],contrast_target_sign=t['contrast_target_sign'],behaviour_scorer_sha256=run['behaviour_scorer_sha256'],candidate_count=len(x['candidate_ids']),measurements=dict(text=ref(om,oi,'text'),pair_scores=ref(lm,li,'pair_logits'),norm_ratio=ref(lm,li,'norm_ratio'),read_norm_ratio=ref(lm,li,'read_norm_ratio'))))
    require(len(records)==336,'eligible two-row U grid only')
    out.mkdir(parents=True);write(out/'RECORDS.json',records)
    write(out/'INPUT_SEAL.json',dict(experiment='E104',status='COMPLETE',labels_cpu_only=True,dose_sha256=DOSE_SHA,random_seed=20261029,reader='oracle',read_block=44,U_hook=dict(block=40,positions='eight_before_read',read_token_untouched=True),N_hook=dict(block=44,positions='read_token',renormalized=True,random_renormalized=True),source_seals=sources,files={'RECORDS.json':sha(out/'RECORDS.json')}))
    spec=dict(dose_path=str(ROOT/'results/g_agreement/understand/e104/doses/E104_DOSES.json'),dose_commit=DOSE_COMMIT,dose_sha256=DOSE_SHA,input_seal=str(out/'INPUT_SEAL.json'),input_sha256=sha(out/'INPUT_SEAL.json'),blind=str(e.CACHE/'blind'),private=str(e.CACHE/'PRIVATE.json'),judgments=str(e.CACHE/'judgments'),analysis=str(e.CACHE/'analysis_once'))
    write(e.CACHE/'SPEC.json',spec);return spec

if __name__=='__main__':build()
