"""§94 c97d0893: descriptive parity; padding/mask/position audit remains a hard gate."""
from contextlib import contextmanager
import numpy as np
from .cpu import read,dump,sha,verify


class ParityNoFit(TimeoutError):pass


def parity_metrics(batched,reference,raw_batched,raw_reference):
    if not batched or not len(batched)==len(reference)==len(raw_batched)==len(raw_reference):raise ValueError('complete paired parity set required')
    rows=[];positions=[]
    for i,(a,b,ra,rb) in enumerate(zip(batched,reference,raw_batched,raw_reference)):
        equal=a==b
        first=None if equal else next((j for j,(x,y) in enumerate(zip(a,b)) if x!=y),min(len(a),len(b)))
        positions.append(128 if first is None else first)
        rows.append({'parity_index':i,'first32_tokens_identical':a[:32]==b[:32],
            'all_tokens_identical':equal,'raw_text_identical':ra==rb,'first_divergence_position0_based':first})
    n=len(rows);matches=sum(r['first32_tokens_identical'] for r in rows);median=float(np.median(positions))
    return {'status':'PASS_INPUT_AUDIT','accepted':True,'n':n,
        'first32_identical_count':matches,'first32_identical_rate':matches/n,
        'all_tokens_identical_rate':sum(r['all_tokens_identical'] for r in rows)/n,
        'raw_text_identical_rate':sum(r['raw_text_identical'] for r in rows)/n,
        'median_first_divergence_position0_based':median,'first_divergence_convention':'zero-based count of identical preceding tokens; median over ALL parity readouts; no divergence is right-censored at128; identical early-EOS completions count as identical',
        'thresholds':None,'parity_is_descriptive':True,'rows':rows}


def check_left_mask(mask):
    import torch
    if not isinstance(mask,torch.Tensor) or mask.ndim!=2 or not bool(((mask==0)|(mask==1)).all()):raise ParityNoFit('NO_FIT: invalid attention mask')
    if not bool((mask[:,-1]==1).all()) or bool((mask[:,1:]<mask[:,:-1]).any()):raise ParityNoFit('NO_FIT: prompt padding must be left padding')


def check_positions(position_ids,expected,active):
    import torch
    if position_ids is None:return False
    if position_ids.ndim<1 or position_ids.shape[-1]!=expected.shape[-1]:raise ParityNoFit('NO_FIT: position-id length mismatch')
    if position_ids.ndim==1:streams=position_ids.reshape(1,1,-1).expand(1,*expected.shape)
    elif position_ids.shape[-2] in [1,expected.shape[0]]:
        streams=position_ids.reshape(-1,position_ids.shape[-2],expected.shape[-1]).expand(-1,expected.shape[0],-1)
    else:raise ParityNoFit('NO_FIT: position-id batch mismatch')
    expected=expected.to(position_ids.device);active=active.to(position_ids.device)
    if not bool(((streams==expected.unsqueeze(0))|~active.unsqueeze(0)).all()):raise ParityNoFit('NO_FIT: consumed position ids differ from attention-mask positions')
    return True


class GenerationAudit:
    """Observe native inputs and consumed positions; never supply or modify model inputs."""
    def __init__(self,nla):
        self.nla=nla;self.calls=[];self.current=None;self.call=None;self.steps=0

    def begin(self,kwargs):
        import torch
        ids=kwargs.get('input_ids');mask=kwargs.get('attention_mask');check_left_mask(mask)
        if not isinstance(ids,torch.Tensor) or ids.ndim!=2 or ids.shape!=mask.shape:raise ParityNoFit('NO_FIT: prompt IDs/mask shape mismatch')
        expected=torch.as_tensor(self.nla.prompt_ids,device=ids.device).unsqueeze(0).expand(len(ids),-1)
        if ids.shape!=expected.shape or not torch.equal(ids,expected) or not bool((mask==1).all()):raise ParityNoFit('NO_FIT: fixed native prompt must be repeated without prompt padding')
        if ids[0,self.nla.marker].item()!=self.nla.prompt_ids[self.nla.marker]:raise ParityNoFit('NO_FIT: injection marker moved')
        self.call={'batch_size':len(ids),'prompt_tokens':ids.shape[1],'device':str(ids.device),'prompt_padding_tokens':0,
            'left_padding_compatible':True,'attention_mask_all_ones':True,'position_steps_verified':0,'position_shapes':[],'forward_mask_formats':[]}
        self.calls.append(self.call);self.current=None;self.offset=0

    def before_forward(self,_module,args,kwargs):
        import torch
        if self.current is not None and not self.current['checked']:raise ParityNoFit('NO_FIT: native position ids were not observed')
        ids=kwargs.get('input_ids',args[0] if args else None);mask=kwargs.get('attention_mask')
        if not isinstance(ids,torch.Tensor) or ids.ndim!=2:raise ParityNoFit('NO_FIT: native generation IDs unavailable for verification')
        kind='None (native all-visible causal optimization)' if mask is None else ('model-prepared dictionary' if isinstance(mask,dict) else f'tensor ndim={mask.ndim}')
        if kind not in self.call['forward_mask_formats']:self.call['forward_mask_formats'].append(kind)
        if isinstance(mask,torch.Tensor) and mask.ndim==2:
            expected=(mask.long().cumsum(-1)-1)[:,-ids.shape[1]:];active=mask[:,-ids.shape[1]:].bool()
        else:
            # HF may optimize the verified all-ones entry mask to None or a prepared causal
            # mask. Observe native positions against the logical unpadded sequence; no override.
            start=0 if kwargs.get('past_key_values') is None else self.offset
            expected=torch.arange(start,start+ids.shape[1],device=ids.device).unsqueeze(0).expand(len(ids),-1)
            active=torch.ones_like(expected,dtype=torch.bool)
        self.offset=int(expected[0,-1])+1
        self.current={'expected':expected,'active':active,'checked':False};self.steps+=1
        self.observe_position(kwargs.get('position_ids'))

    def observe_position(self,position):
        if self.current is None or position is None:return
        check_positions(position,self.current['expected'],self.current['active'])
        if not self.current['checked']:self.call['position_steps_verified']+=1
        self.current['checked']=True;shape=list(position.shape)
        if shape not in self.call['position_shapes']:self.call['position_shapes'].append(shape)

    def before_rotary(self,_module,args,kwargs):
        self.observe_position(kwargs.get('position_ids',args[1] if len(args)>1 else None))

    def finish(self):
        if self.current is None or not self.current['checked']:raise ParityNoFit('NO_FIT: consumed position ids not verified')

    @contextmanager
    def observing(self):
        model=self.nla.av.get_base_model() if hasattr(self.nla.av,'get_base_model') else self.nla.av
        handles=[model.register_forward_pre_hook(self.before_forward,with_kwargs=True)]
        handles += [m.register_forward_pre_hook(self.before_rotary,with_kwargs=True) for n,m in model.named_modules() if n.endswith('rotary_emb')]
        try:yield
        finally:
            for h in handles:h.remove()

    def report(self):return {'padding_side':getattr(self.nla.tok,'padding_side',None),'native_prompt':'same fixed-length prompt for every vector; zero prompt padding, equivalent to left padding of length0',
        'position_ids':'native model-computed positions observed at forward/rotary consumption; not overridden','forward_steps':self.steps,'calls':self.calls}


def report_text(report):
    if 'first32_identical_rate' not in report:return '**E7 operational setup parity:** NO_FIT. '+report.get('error','Padding/position verification failed.')+'\n'
    return ('**E7 operational setup parity (§94, c97d0893):** '+report['status']+'.\n\n'
        +f"First32-token agreement: {report['first32_identical_count']}/{report['n']} ({report['first32_identical_rate']:.2%}). "
        +f"Median first-divergence position: {report['median_first_divergence_position0_based']:.1f}. "
        +f"Full-token agreement: {report['all_tokens_identical_rate']:.2%}; full decoded-text agreement: {report['raw_text_identical_rate']:.2%}.\n\n"
        +'DESCRIPTIVE: §94 c97d0893 removes parity acceptance thresholds after seeing the earlier operational parity numbers and before any E7 science. Padding, attention-mask and consumed position-ID checks remain mandatory hard gates.\n\n'
        +'Positions are zero-based counts of matching preceding tokens. Identical completions, including matching early EOS, have no divergence and are censored at128 for the all-readout median. Only padding after the first EOS is ignored. Batch8 is a setup reference; every production readout uses the batch32 setting, including its final partial unit. No per-item selection or fallback.\n')


def save_report(path,report):
    dump(path,report);dump(path.with_name('GENERATION_PARITY_SEAL.json'),{'status':'E7_C97D0893_PARITY_SEALED_BEFORE_SCIENCE','files':{path.name:sha(path)}})
    path.with_name('PARITY_RESULTS.md').write_text(report_text(report))


def main():
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser(description='Append frozen operational parity rates after unchanged E7 analysis; no scientific metric computation')
    p.add_argument('--collection',type=Path,required=True);p.add_argument('--results',type=Path,required=True);a=p.parse_args()
    verify(a.collection);verify(a.collection,'GENERATION_PARITY_SEAL.json');report=read(a.collection/'GENERATION_PARITY.json')
    if report.get('status')!='PASS_INPUT_AUDIT':raise ValueError('No passing input-audit receipt')
    parent=a.results.parent;original=verify(parent);text=a.results.read_text();marker='**E7 operational setup parity (§94,'
    if marker in text:raise FileExistsError('parity section already present')
    a.results.write_text(text+'\n'+report_text(report));(parent/'GENERATION_PARITY.json').write_bytes((a.collection/'GENERATION_PARITY.json').read_bytes())
    receipt={'status':'OPERATIONAL_PARITY_REPORT_ONLY','prior_analysis_seal':original,'parity_receipt_sha256':sha(a.collection/'GENERATION_PARITY.json'),'scientific_analysis_rerun':False}
    dump(parent/'PARITY_REPORT_ADDITION.json',receipt)
    files={n:sha(parent/n) for n in original['files']};files.update({n:sha(parent/n) for n in ['GENERATION_PARITY.json','PARITY_REPORT_ADDITION.json']})
    dump(parent/'SCORE_SEAL.json',{'status':original['status'],'files':files})


if __name__=='__main__':main()
