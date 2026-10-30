"""Single-process E16 dev-select/test-once and exact Q1 native free-readout collection."""
import argparse,os,time
from pathlib import Path
import numpy as np
from .cpu import read,rows,dump,sha,verify,seal
from .e16 import Q1_SHA,READERS,choose,base_head,validate_free
from .followup_packed import Residents as PreviousResidents,jsonl
from .e16_runtime import Gate,NoFit,PATHS


def base_scores(reader,records,pairs):
    """Both candidates share a forward; E12 right-pad/equal-head machinery, no slot/injection."""
    import torch
    tok=reader.tok;model=reader.model;heads=[base_head(tok,r['text']) for r in records]
    if len({len(x) for x in heads})!=1:raise ValueError('base context batches require equal head lengths')
    headlen=len(heads[0]);answers=[]
    with reader.base(),torch.inference_mode():
        for pair in pairs:
            cands=[tok.encode(c,add_special_tokens=False) for c in pair]
            if any(not c for c in cands):raise ValueError('empty candidate')
            length=headlen+max(map(len,cands));ids=torch.full((2*len(records),length),tok.pad_token_id or 0,device=reader.device,dtype=torch.long);mask=torch.zeros_like(ids)
            for i,head in enumerate(heads):
                for j,cand in enumerate(cands):
                    s=head+cand;ids[2*i+j,:len(s)]=torch.tensor(s,device=reader.device);mask[2*i+j,:len(s)]=1
            logits=model(input_ids=ids,attention_mask=mask,logits_to_keep=length-headlen+1,use_cache=False).logits
            lp=torch.log_softmax(logits[:,:-1].float(),dim=-1);v=lp.gather(-1,ids[:,headlen:].unsqueeze(-1)).squeeze(-1)
            answers.append([float(v[2*i,:len(cands[0])].sum()-v[2*i+1,:len(cands[1])].sum()) for i in range(len(records))])
    return np.asarray(answers,float).T


def asked(reader,name,unit,items,h,templates,selection=None,benchmark=False):
    import torch
    f=unit['feature'];pairs=templates[f][name]
    if selection is not None:pairs=[selection[f]['pair']]
    if benchmark:
        # Forecast single-pair test execution on DEVELOPMENT inputs only, before selection.
        pairs=[max(pairs,key=lambda p:max(len(reader.tok.encode(c,add_special_tokens=False)) for c in p))]
    ix=unit['indices'];rs=[items[i] for i in ix]
    if name=='base':values=base_scores(reader,rs,pairs)
    else:
        v=torch.as_tensor(h[ix],dtype=torch.float32)
        if name=='olens':values=reader.paired_logodds_templates(v,44,pairs).numpy().T
        else:
            from mats.readers.nla import paired_logodds_templates
            values=paired_logodds_templates(reader,v,pairs,batch=32).numpy().T
    if values.shape!=(len(ix),len(pairs)) or not np.isfinite(values).all():raise ValueError('incomplete/nonfinite asked scores')
    return [{'id':r['id'],'feature':f,'reader':name,'scores':v.tolist(),
        **({'phrasing_index':selection[f]['index']} if selection is not None else {})} for r,v in zip(rs,values)]


def free_readouts(reader,name,h,items,unit,sampled,unit_index):
    """Native prompts/injection; raw decoded completions, no stripping/extraction/repair."""
    import torch
    k=3 if sampled else 1;seed=20261024+(0 if name=='olens' else 10000)+(1000 if sampled else 0)+unit_index
    torch.manual_seed(seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
    ix=unit['indices'];v=torch.as_tensor(h[ix],dtype=torch.float32).repeat_interleave(k,dim=0);texts=[]
    prompt,slot=reader.carrier(44) if name=='olens' else (reader.prompt_ids,reader.marker)
    with torch.inference_mode():
        for s in range(0,len(v),32):
            vectors=v[s:s+32].to(reader.device);ids=torch.tensor([prompt]*len(vectors),device=reader.device)
            opts={'do_sample':sampled,'num_beams':1,'max_new_tokens':128,'pad_token_id':reader.tok.pad_token_id if name=='nla' else (reader.tok.pad_token_id or reader.tok.eos_token_id)}
            if sampled:opts.update(temperature=.7,top_p=.95,top_k=64)
            if name=='olens':
                out=reader.model.generate(inputs_embeds=reader._embed(ids,slot,vectors),attention_mask=torch.ones_like(ids),**opts)
            else:
                with reader._inject(vectors):out=reader.av.generate(input_ids=ids,attention_mask=torch.ones_like(ids),**opts)
                out=out[:,len(prompt):]
            texts+=reader.tok.batch_decode(out,skip_special_tokens=True,clean_up_tokenization_spaces=False)
    if len(texts)!=len(ix)*k:raise ValueError('incomplete free unit')
    return [{'id':items[i]['id'],'reader':name,'layer':READERS[name],'sample':j+1 if sampled else 0,'raw':texts[p*k+j]} for p,i in enumerate(ix) for j in range(k)]


class Residents(PreviousResidents):
    def __init__(self,a,g):
        self.a=a;self.gates={'E16':g};self.current='E16';self.objects={};self.loads={};self.events=[];self.active=None;self.completed_science=0.
        g.setup_guard()
        from projects.g_agreement.blindspot.run import _assets
        self.assets=_assets(a.assets,('model','olens','nla'));self.assets_sha=sha(a.assets);g.setup_guard()

    def setup_guard(self):self.gates['E16'].setup_guard()

    def load(self,name):
        if name=='nla':
            import common
            from mats.readers.nla import load_nla
            return load_nla(root=self.assets['nla'],load_ar=False)
        if name!='olens':raise ValueError('only Oracle/base backbone and NLA verbalizer may load')
        import common,torch
        from transformers import AutoModelForCausalLM,AutoTokenizer
        from mats.readers.olens import load_olens
        model=AutoModelForCausalLM.from_pretrained(self.assets['model'],dtype=torch.bfloat16,device_map='cuda',local_files_only=True).eval()
        tok=AutoTokenizer.from_pretrained(self.assets['model'],local_files_only=True)
        return load_olens(model=model,tok=tok,lora_dir=self.assets['olens'])


class Collection:
    def __init__(self,a,g,resident):
        self.a=a;self.g=g;self.resident=resident;self.items=rows(a.inputs/'items.input.jsonl');self.templates=read(a.inputs/'templates.json');self.units=read(a.inputs/'units.json')
        self.h={n:np.load(a.inputs/f'acts{l}.npy',allow_pickle=False) for n,l in [('olens',44),('nla',42)]}
        self.free_items=rows(a.inputs/'free.input.jsonl');self.fh={n:np.load(a.inputs/f'free_acts{l}.npy',allow_pickle=False) for n,l in [('olens',44),('nla',42)]}
        self.results={k:{} for k in PATHS};self.dev_labels={r['id']:r['y'] for r in rows(a.inputs/'dev.labels.input.jsonl')};self.choices={}
        if set(self.dev_labels)!=set(read(a.inputs/'dev_ids.json')) or set(self.dev_labels)&set(read(a.inputs/'test_ids.json')):raise ValueError('selection labels must be dev-only')
        for k in PATHS:(a.out/k).mkdir()

    def plan(self,key):
        name,phase=key.split('_')
        return self.units['free'] if phase in ['greedy','sampled'] else self.units[phase]['base' if name=='base' else 'native']

    def call(self,key,i,benchmark=False):
        name,phase=key.split('_');reader=self.resident.get('olens' if name=='base' else name)
        if phase in ['greedy','sampled']:return free_readouts(reader,name,self.fh[name],self.free_items,self.plan(key)[i],phase=='sampled',i)
        unit=self.units['dev']['base' if name=='base' else 'native'][i] if benchmark else self.plan(key)[i]
        if phase=='test' and not benchmark:
            verify(self.a.out/name,'SELECTION_SEAL.json')
            selected=self.choices[name]
        else:selected=None
        return asked(reader,name,unit,self.items,None if name=='base' else self.h[name],self.templates,selected,benchmark)

    def setup(self):
        for owner in ['olens','nla']:
            reader=self.resident.get(owner)
            if owner=='olens' and sha(Path(self.resident.assets['model'])/'tokenizer.json')!=read(self.a.inputs/'provenance.json')['base_tokenizer_sha256']:raise ValueError('base tokenizer mismatch')
            for key in PATHS:
                if key.split('_')[0] not in (['olens','base'] if owner=='olens' else ['nla']):continue
                self.g.setup_guard();t=time.monotonic();self.call(key,0,benchmark=key.endswith('_test'));self.g.warm(key,time.monotonic()-t)
        self.resident.get('olens');self.g.setup_guard()

    def unit(self,key,i,benchmark=False):
        if i in self.results[key]:raise ValueError('duplicate retained unit')
        if not self.g.admitted and len(self.g.samples[key])>=3:raise ValueError('bulk forbidden before full forecast')
        self.g.guard();t=time.monotonic();value=self.call(key,i,benchmark);dt=time.monotonic()-t
        if not benchmark:
            self.results[key][i]=value;dump(self.a.out/key/f'unit-{i:05d}.json',value)
        else:
            dump(self.a.out/key/f'timing-only-dev-{i:05d}.json',{'development_ids':[r['id'] for r in value],'discarded':True,'science_seconds':dt,'test_item_calls':0})
        self.g.record(key,dt,retained=not benchmark)

    def free_seal(self):
        result=[r for name in ['olens','nla'] for phase in ['greedy','sampled'] for i in range(len(self.units['free'])) for r in self.results[name+'_'+phase][i]]
        validate_free(result,read(self.a.inputs/'E16_ITEM_REQUEST.json'))
        free=self.a.out/'free';free.mkdir();jsonl(free/'raw.jsonl',result);(free/'E16_ITEM_REQUEST.json').write_bytes((self.a.inputs/'E16_ITEM_REQUEST.json').read_bytes())
        if sha(free/'E16_ITEM_REQUEST.json')!=Q1_SHA:raise ValueError('free receipt must bind exact Q1 request bytes')
        dump(free/'provenance.json',{'q1_request_sha256':Q1_SHA,'input_seal_sha256':sha(self.a.inputs/'INPUT_SEAL.json'),
            'assignment_sha256':self.g.assignment_sha256,'assets_sha256':self.g.assignment.get('assets_sha256'),'source_files':self.g.assignment['source_files'],
            'source_banks':read(self.a.inputs/'provenance.json')['free_source_banks'],'decoding':read(self.a.inputs/'provenance.json')['free_decoding'],
            'seed_formula':'20261024 + (nla?10000:0) + (sampled?1000:0) + canonical_unit_index','records':480,'items':60,'sealed_before_any_coding':True,'Q1_keys_accessed':False})
        dump(free/'FREE_SEAL.json',{'status':'Q1_ALL_480_RAW_READOUTS_SEALED_BEFORE_CODING','q1_request_sha256':Q1_SHA,
            'files':{n:sha(free/n) for n in ['raw.jsonl','provenance.json','E16_ITEM_REQUEST.json']}})

    def dev_select_and_test(self,name):
        for i in range(len(self.plan(name+'_dev'))):
            if i not in self.results[name+'_dev']:self.unit(name+'_dev',i)
        ids=read(self.a.inputs/'dev_ids.json');rs=[r for i in range(len(self.plan(name+'_dev'))) for r in self.results[name+'_dev'][i]]
        index={r['id']:r for r in rs};ordered=[index[k] for k in ids]
        out=self.a.out/name;out.mkdir();jsonl(out/'dev.scores.jsonl',ordered)
        self.choices[name]=choose(ordered,self.dev_labels,self.templates,name,ids)
        dump(out/'SELECTION.json',{'reader':name,'selection':self.choices[name],'selection_split':'dev','test_scoring_started':False,
            'dev_ids_sha256':sha(self.a.inputs/'dev_ids.json'),'dev_labels_sha256':sha(self.a.inputs/'dev.labels.input.jsonl'),
            'input_seal_sha256':sha(self.a.inputs/'INPUT_SEAL.json'),'dev_scores_sha256':sha(out/'dev.scores.jsonl'),'tie_break':'lowest frozen phrasing index'})
        dump(out/'SELECTION_SEAL.json',{'status':'E16_DEV_SELECTION_SEALED_BEFORE_TEST','files':{n:sha(out/n) for n in ['SELECTION.json','dev.scores.jsonl']}})
        for i in range(len(self.plan(name+'_test'))):self.unit(name+'_test',i)
        rs=[r for i in range(len(self.plan(name+'_test'))) for r in self.results[name+'_test'][i]];ids=read(self.a.inputs/'test_ids.json');mapping={r['id']:r for r in rs}
        if len(rs)!=len(ids) or set(mapping)!=set(ids) or any(len(r['scores'])!=1 for r in rs):raise ValueError('exact selected-once test grid required')
        jsonl(out/'test.scores.jsonl',[mapping[k] for k in ids]);dump(out/'provenance.json',{'input_seal_sha256':sha(self.a.inputs/'INPUT_SEAL.json'),
            'selection_seal_sha256':sha(out/'SELECTION_SEAL.json'),'test_phrasings_per_item':1,'test_labels_accessed':False,
            'base_adapter':'disabled for every base forward' if name=='base' else None,'base_activation':'none' if name=='base' else 'native'})
        seal(out,['dev.scores.jsonl','SELECTION.json','SELECTION_SEAL.json','test.scores.jsonl','provenance.json'],'E16_READER_COMPLETE_SELECTION_BEFORE_TEST')


def execute(a,g,resident=None):
    error=None;status='COMPLETE'
    try:
        if resident is None:resident=Residents(a,g)
        c=Collection(a,g,resident);c.setup();g.start()
        for owner,keys in [('olens',['olens_dev','olens_test','base_dev','base_test','olens_greedy','olens_sampled']),('nla',['nla_dev','nla_test','nla_greedy','nla_sampled'])]:
            t=time.monotonic();resident.get(owner)
            if owner=='nla':g.movement(time.monotonic()-t)
            for key in keys:
                for i in range(3):c.unit(key,i,benchmark=key.endswith('_test'))
        c.free_seal();g.admit()
        c.dev_select_and_test('nla');resident.get('olens');g.guard()
        c.dev_select_and_test('olens');c.dev_select_and_test('base');g.guard()
    except Exception as exc:status='NO_FIT' if isinstance(exc,NoFit) else 'INCOMPLETE';error=type(exc).__name__+': '+str(exc)
    g.status=status;g.write_state();dump(a.out/'run.json',{'experiment':'E16','status':status,'error':error,'PID':os.getpid(),'first_science_epoch':g.first_science_epoch,
        'elapsed_science_seconds':g.elapsed(),'science_clock_resets':0,'checkpoint_load_counts':{} if resident is None else resident.loads,'resident_events':[] if resident is None else resident.events,'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),
        'assignment_sha256':g.assignment_sha256,'assets_sha256':g.assignment.get('assets_sha256'),'source_commit':g.assignment.get('source_commit'),'source_files':g.assignment['source_files']})
    seal(a.out,[str(p.relative_to(a.out)) for p in a.out.rglob('*') if p.is_file()],'E16_'+status)
    print('HANDOFF E16',status,a.out/'SCORE_SEAL.json',flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['inputs','assets','assignment','out']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();verify(a.inputs,'INPUT_SEAL.json')
    if sha(a.inputs/'E16_ITEM_REQUEST.json')!=Q1_SHA:raise ValueError('Q1 request hash mismatch')
    if any(a.inputs.rglob('*.DO_NOT_STAGE.*')):raise ValueError('private labels/keys forbidden on worker')
    u=read(a.inputs/'units.json');counts={k:(len(u['free']) if k.endswith(('_greedy','_sampled')) else len(u[k.split('_')[1]]['base' if k.startswith('base') else 'native'])) for k in PATHS}
    g=Gate(a.assignment,counts)
    if g.assignment.get('assets_sha256')!=sha(a.assets) or g.assignment.get('input_seal_sha256')!=sha(a.inputs/'INPUT_SEAL.json'):raise ValueError('assets/input binding mismatch')
    a.out.mkdir(parents=True,exist_ok=False);g.out=a.out;g.write_state();execute(a,g)


if __name__=='__main__':main()
