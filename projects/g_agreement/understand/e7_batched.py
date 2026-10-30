"""E7-only operational batching retry. Original inputs, arithmetic and analysis are unchanged."""
import argparse
import os
import time
from pathlib import Path
import numpy as np
from . import worker as W
from .cpu import ROOT,read,rows,dump,sha,verify,seal
from .e7_solo import SoloResidents
from .packed import experiment_seal
from .e7_batched_runtime import Gate
from .e7_parity import GenerationAudit,ParityNoFit,parity_metrics,save_report

GEN_BATCH=32
DECODE_BATCH=8
SCORE_BATCH=8
ARMS=('swap','self','ol_only','nla_only','delta_only','random')
REGISTRATION='results/g_agreement/understand/e7/batched_retry'


def schedule(n,pairs):
    gen=[list(range(i,min(n,i+GEN_BATCH))) for i in range(0,n,GEN_BATCH)]
    dec=[list(range(i,min(2*n,i+DECODE_BATCH))) for i in range(0,2*n,DECODE_BATCH)]
    scores=[{'id':p['id'],'index':i,'arm':arm,'feature':p['feature']} for arm in ARMS for i,p in enumerate(pairs)]
    units=[list(range(i,min(len(scores),i+SCORE_BATCH))) for i in range(0,len(scores),SCORE_BATCH)]
    needed={pairs[scores[i]['index']][side] for u in units[:3] for i in u for side in ['recipient','donor','random']}
    pd=set(range(3))|{pos//DECODE_BATCH for i in needed for pos in [i,i+n]}
    pg=set(range(3))|{(pos-n)//GEN_BATCH for k in pd for pos in dec[k] if pos>=n}
    return {'generation_units':gen,'decoder_units':dec,'score_records':scores,'score_units':units,
        'pilot_generation_units':sorted(pg),'pilot_decoder_units':sorted(pd),'pilot_score_units':[0,1,2]}


def generate(nla,h,batch=GEN_BATCH):
    import torch
    from mats.readers.nla import Sampling
    return nla.verbalize_raw(torch.as_tensor(h),k=1,sampling=Sampling(temperature=0,max_new_tokens=128),batch=batch)


def generation_with_tokens(nla,h,batch,audit=None):
    """Observe the unchanged native generate call; ignore only padding after its first EOS."""
    original=nla.av.generate;tokens=[]
    eos=getattr(nla.av.generation_config,'eos_token_id',None)
    endings=set(eos if isinstance(eos,list) else ([] if eos is None else [eos]))
    def captured(*args,**kwargs):
        if audit is not None:audit.begin(kwargs)
        out=original(*args,**kwargs);seq=out.sequences if hasattr(out,'sequences') else out
        if audit is not None:audit.finish()
        for row in seq[:,kwargs['input_ids'].shape[1]:].detach().cpu().tolist():
            stop=next((i+1 for i,t in enumerate(row) if t in endings),len(row));tokens.append(row[:stop])
        return out
    nla.av.generate=captured
    try:
        if audit is None:raw=generate(nla,h,batch)
        else:
            with audit.observing():raw=generate(nla,h,batch)
    finally:nla.av.generate=original
    return raw,tokens


def verify_generation_parity(nla,h,report_path=None):
    # Native prompt tensors are identical-length and unpadded. Configure left padding for any
    # tokenizer use and observe actual masks/consumed positions; do not override native positions.
    nla.tok.padding_side='left';audits={str(batch):GenerationAudit(nla) for batch in [GEN_BATCH,8]}
    try:
        batched,btokens=generation_with_tokens(nla,h,GEN_BATCH,audit=audits[str(GEN_BATCH)])
        reference,rtokens=generation_with_tokens(nla,h,8,audit=audits['8'])
        if any(len(x)!=len(h) for x in [batched,btokens,reference,rtokens]):raise ParityNoFit('NO_FIT: incomplete frozen parity set')
        report=parity_metrics(btokens,rtokens,[v[0] for v in batched],[v[0] for v in reference])
    except ParityNoFit as exc:
        report={'status':'NO_FIT','accepted':False,'error':str(exc),'n':len(h)}
        report['padding_verification']={k:v.report() for k,v in audits.items()}
        if report_path is not None:save_report(report_path,report)
        raise
    report.update(batch32=GEN_BATCH,reference_batch=8,greedy=True,k=1,max_new_tokens=128,same_loaded_AV=True,PID=os.getpid(),
        padding_verification={k:v.report() for k,v in audits.items()},ruling='§94 c97d0893; parity descriptive; hard padding/mask/position audit; all production batch32')
    if report_path is not None:save_report(report_path,report)
    return report


def parse_readout(key,raw):
    # Exact original worker extraction. Raw strings are kept, including truncated output.
    return {'id':key,'text':raw.split('</explanation>')[0].removeprefix('<explanation>').strip(),'raw':raw}


def score(nla,records,arms,templates):
    import torch
    from mats.readers.nla import paired_logodds_templates
    output=[]
    for f in sorted({r['feature'] for r in records}):
        selected=[r for r in records if r['feature']==f]
        vec=np.stack([arms[r['arm']][r['index']] for r in selected])
        if not np.isfinite(vec).all():raise ValueError('score pilot has undecoded dependencies')
        values=paired_logodds_templates(nla,torch.tensor(vec),templates[f]['nla'],batch=2*SCORE_BATCH).mean(0).numpy()
        output.extend({**r,'score':float(v)} for r,v in zip(selected,values))
    return output


class Collection:
    def __init__(self,a,resident,g,s):
        self.a=a;self.resident=resident;self.g=g;self.s=s;self.inputs=a.inputs/'e7';self.root=a.out/'e7'
        self.ids=read(self.inputs/'ids.json');self.n=len(self.ids);self.h=np.load(self.inputs/'acts42.npy',allow_pickle=False)
        self.ol=rows(self.inputs/'ol.input.jsonl');self.pairs=rows(self.inputs/'pairs.input.jsonl');self.templates=read(self.inputs/'templates.json')
        if [r['id'] for r in self.ol]!=self.ids or self.h.shape!=(self.n,5120):raise ValueError('frozen item order/shape mismatch')
        self.readouts={};self.recon=np.full((2*self.n,5120),np.nan,dtype=np.float32);self.scores={};self.done={k:set() for k in ['readouts','prepare','decoder','scores']}
        for key in ['readouts','prepare','decoder','scores']:(self.root/(key+'-units')).mkdir()

    def setup(self):
        import torch
        probe=self.a.out/'decoder-preflight';probe.mkdir()
        decoder=self.resident.get('decoder');test=decoder.reconstruct(['The unfinished prefix (','The current position is outside parentheses.'],batch=2).numpy()
        if test.shape!=(2,5120) or not np.isfinite(test).all():raise ValueError('native42 decoder preflight failed')
        # Warm the existing batch8 decoder on the longest available OL strings.
        longest=sorted(self.ol,key=lambda r:len(r['text']),reverse=True)[:DECODE_BATCH]
        decoder.reconstruct([r['text'] for r in longest],batch=DECODE_BATCH);self.g.setup_guard()
        dump(probe/'report.json',{'status':'LOADED_NATIVE42','assets_sha256':sha(self.a.assets),'AV_loaded':False,'same_process':True,'PID':os.getpid(),'loads':self.resident.loads['decoder']})
        seal(probe,['report.json'],'EXPLORATORY_DECODER_LOAD_VERIFIED')
        nla=self.resident.get('nla');tail=self.n%GEN_BATCH
        warm=np.concatenate([self.h[:GEN_BATCH],self.h[-tail:]]) if tail else self.h[:GEN_BATCH]
        verify_generation_parity(nla,warm,self.a.out/'GENERATION_PARITY.json')
        records=[self.s['score_records'][i] for i in self.s['score_units'][0]]
        feature=records[0]['feature'];pairs=self.templates[feature]['nla']
        from mats.readers.nla import paired_logodds_templates
        paired_logodds_templates(nla,torch.as_tensor(self.h[:SCORE_BATCH]),pairs,batch=2*SCORE_BATCH)
        self.g.setup_guard()

    def generation(self,which):
        nla=self.resident.get('nla')
        for k in which:
            if k in self.done['readouts']:continue
            self.g.start();ix=self.s['generation_units'][k];t=time.monotonic();raw=generate(nla,self.h[ix])
            result=[parse_readout(self.ids[i],v[0]) for i,v in zip(ix,raw)]
            if len(result)!=len(ix):raise ValueError('missing greedy readout')
            self.readouts.update(zip(ix,result));W.jsonl(self.root/'readouts-units'/f'{k:05d}.jsonl',result)
            self.done['readouts'].add(k);self.g.record('readouts',time.monotonic()-t)

    def prepare(self,k):
        if k in self.done['prepare']:return
        self.g.guard();t=time.monotonic();records=[]
        for pos in self.s['decoder_units'][k]:
            prefix='ol' if pos<self.n else 'nla';i=pos%self.n;r=self.ol[i] if prefix=='ol' else self.readouts[i]
            records.append({'id':prefix+':'+self.ids[i],'text':r['text']})
        out=self.root/'prepare-units'/f'{k:05d}';out.mkdir();W.jsonl(out/'decode.input.jsonl',records)
        dump(out/'INPUT_SEAL.json',{'files':{'decode.input.jsonl':sha(out/'decode.input.jsonl')},'status':'E7_RETAINED_DECODER_UNIT_INPUT_FROZEN'})
        self.done['prepare'].add(k);self.g.record('prepare',time.monotonic()-t)

    def decoding(self,which,pilot=False):
        t=time.monotonic();decoder=self.resident.get('decoder')
        if pilot:self.g.movement('decoder',time.monotonic()-t)
        for k in which:
            if k in self.done['decoder']:continue
            self.prepare(k);self.g.guard();inp=self.root/'prepare-units'/f'{k:05d}';verify(inp,'INPUT_SEAL.json');records=rows(inp/'decode.input.jsonl')
            t=time.monotonic();x=decoder.reconstruct([r['text'] for r in records],batch=DECODE_BATCH).numpy()
            if x.shape!=(len(records),5120) or not np.isfinite(x).all():raise ValueError('invalid native decoder unit')
            ix=self.s['decoder_units'][k];self.recon[ix]=x;np.save(self.root/'decoder-units'/f'{k:05d}.npy',x,allow_pickle=False)
            self.done['decoder'].add(k);self.g.record('decoder',time.monotonic()-t)

    def scoring(self,which,pilot=False):
        t=time.monotonic();nla=self.resident.get('nla')
        if pilot:self.g.movement('scores',time.monotonic()-t)
        ol,nrec=np.split(self.recon,2);arms=W.e7_arms(ol,nrec,self.pairs)
        for k in which:
            if k in self.done['scores']:continue
            self.g.guard();records=[self.s['score_records'][i] for i in self.s['score_units'][k]];t=time.monotonic();result=score(nla,records,arms,self.templates)
            if len(result)!=len(records):raise ValueError('incomplete score unit')
            self.scores[k]=result;W.jsonl(self.root/'scores-units'/f'{k:05d}.jsonl',result)
            self.done['scores'].add(k);self.g.record('scores',time.monotonic()-t)

    def finalize_readouts(self):
        if len(self.readouts)!=self.n:raise ValueError('incomplete readout population')
        out=self.root/'readouts';out.mkdir();W.jsonl(out/'readouts.jsonl',[self.readouts[i] for i in range(self.n)])
        dump(out/'provenance.json',{'input_seal_sha256':sha(self.inputs/'INPUT_SEAL.json'),'assignment_sha256':sha(self.a.assignments/'e7.json'),'assets_sha256':sha(self.a.assets),'decoding':{'k':1,'temperature':0,'max_new_tokens':128,'layer':42},'generation_batch':GEN_BATCH})
        dump(out/'WARMED_FORECAST.json',self.g.forecast()['phases']['readouts']);seal(out,['readouts.jsonl','provenance.json','WARMED_FORECAST.json'],'EXPLORATORY_NLA_READOUTS_SEALED')
        from types import SimpleNamespace
        W.prepare_e7_decode(SimpleNamespace(inputs=self.inputs,readouts=out,out=self.root/'decode-inputs'))

    def finalize(self):
        if not np.isfinite(self.recon).all():raise ValueError('incomplete decoder population')
        out=self.root/'decoder';out.mkdir();np.save(out/'recon.npy',self.recon,allow_pickle=False)
        dump(out/'ids.json',[prefix+':'+key for prefix in ['ol','nla'] for key in self.ids])
        dump(out/'provenance.json',{'reader':'nla','layer':42,'input_seal_sha256':sha(self.root/'decode-inputs/INPUT_SEAL.json'),'records':'decode.input.jsonl','assignment_sha256':sha(self.a.assignments/'e7.json'),'assets_sha256':sha(self.a.assets),'source_sha256':sha(Path(__file__))})
        dump(out/'WARMED_FORECAST.json',self.g.forecast()['phases']['decoder']);seal(out,['recon.npy','ids.json','provenance.json','WARMED_FORECAST.json'],'EXPLORATORY_RECONSTRUCTIONS_SEALED_BEFORE_LABEL_JOIN')
        out=self.root/'scores';out.mkdir();scores=[r for k in range(len(self.s['score_units'])) for r in self.scores[k]]
        expected={(p['id'],arm) for p in self.pairs for arm in ARMS}
        if len(scores)!=len(expected) or {(r['id'],r['arm']) for r in scores}!=expected:raise ValueError('incomplete six-arm grid')
        W.jsonl(out/'scores.jsonl',scores);ol,nrec=np.split(self.recon,2);np.save(out/'delta.npy',nrec-ol,allow_pickle=False);dump(out/'ids.json',self.ids)
        dump(out/'provenance.json',{'input_seal_sha256':sha(self.inputs/'INPUT_SEAL.json'),'reconstruction_score_seal_sha256':sha(self.root/'decoder/SCORE_SEAL.json'),'assignment_sha256':sha(self.a.assignments/'e7.json'),'assets_sha256':sha(self.a.assets),'site':'NATIVE42','score_orientation':'W1valueAminusB;no flips'})
        dump(out/'WARMED_FORECAST.json',self.g.forecast()['phases']['scores']);seal(out,['scores.jsonl','delta.npy','ids.json','provenance.json','WARMED_FORECAST.json'],'EXPLORATORY_E7_SCORES_SEALED_BEFORE_LABEL_JOIN')


def execute(a,resident,g,s):
    root=a.out/'e7';root.mkdir();g.out=root;resident.current=None;W.RESIDENT=resident;status='COMPLETE';error=None
    try:
        c=Collection(a,resident,g,s);c.setup();resident.current='E7'
        c.generation(s['pilot_generation_units']);c.decoding(s['pilot_decoder_units'],pilot=True);c.scoring(s['pilot_score_units'],pilot=True)
        g.admit_remaining()  # all four retained timing paths, including pilot dependencies, before remaining production
        c.generation(range(len(s['generation_units'])));c.finalize_readouts()
        c.decoding(range(len(s['decoder_units'])));c.scoring(range(len(s['score_units'])));c.finalize();g.guard()
    except ParityNoFit as exc:status='NO_FIT';error=type(exc).__name__+': '+str(exc)
    except Exception as exc:status='INCOMPLETE';error=type(exc).__name__+': '+str(exc)
    finally:
        g.state_status=status;g.write_state()
        phases=[root/n for n in ['readouts','decoder','scores']]
        experiment_seal(root,'E7',g,status,phases,resident.events,error);W.RESIDENT=None
    dump(a.out/'solo.json',{'status':status,'error':error,'PID':os.getpid(),'order':['E7'],'E1_E2_executed':False,'same_process':True,
        'checkpoint_load_counts':resident.loads,'generation_batch':GEN_BATCH,'decoder_batch':DECODE_BATCH,'score_vector_batch':SCORE_BATCH,'scientific_analysis_unchanged':True})
    evidence=['solo.json','e7/SCORE_SEAL.json']
    evidence += [name for name in ['e7/FULL_WARMED_FORECAST.json','e7/FORECAST_SEAL.json','decoder-preflight/report.json','decoder-preflight/SCORE_SEAL.json','GENERATION_PARITY.json','GENERATION_PARITY_SEAL.json','PARITY_RESULTS.md'] if (a.out/name).is_file()]
    seal(a.out,evidence,'EXPLORATORY_E7_BATCHED_SOLO_RECEIPT');print('HANDOFF E7 BATCHED',status,root/'SCORE_SEAL.json',flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['inputs','assets','assignments','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.official=None;a.whitener=None;inp=a.inputs/'e7';verify(inp,'INPUT_SEAL.json')
    s=schedule(len(read(inp/'ids.json')),rows(inp/'pairs.input.jsonl'))
    if s!=read(ROOT/REGISTRATION/'SCHEDULE.json'):raise ValueError('operational schedule differs from registered fixed input plan')
    counts={'readouts':len(s['generation_units']),'prepare':len(s['decoder_units']),'decoder':len(s['decoder_units']),'scores':len(s['score_units'])}
    g=Gate(a.assignments/'e7.json',counts)
    if g.assignment.get('input_seal_sha256')!=sha(inp/'INPUT_SEAL.json') or g.assignment.get('assets_sha256')!=sha(a.assets):raise ValueError('assignment input/asset binding mismatch')
    if any(a.inputs.rglob('*.DO_NOT_STAGE.*')):raise ValueError('private labels must not be staged')
    a.out.mkdir(exist_ok=False,parents=True);resident=SoloResidents(a,{'E7':g});g.setup_callback=resident.setup_guard;execute(a,resident,g,s)


if __name__=='__main__':main()
