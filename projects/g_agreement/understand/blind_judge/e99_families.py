"""Sealed W-text renderer registry. Source private records stay with CPU caller."""
import importlib.util
import json
import re
from .e99_headline import ROOT,load_frozen,wrong_spans,claim_inventory
from projects.g_agreement.readerbench.io import verify,sha,read
from projects.g_agreement.readerbench.scoring import require
EXPORT_SHA='47ba8e278fd26e0e0ce12f1f4a63fb72a79896fed73ad275d528e78408ec834d'
MC_SHA='1d13279da8a6e448a42e962fba84843b0d29981aa18d4b0dbf3ca52d40ff2759'

class Renderers:
    def __init__(self):
        self.root=ROOT/'results/g_agreement/understand/e99'
        verify(self.root/'EXPORT_SEAL.json',EXPORT_SHA);verify(self.root/'MC_SEAL.json',MC_SHA)
        self.hallucination,self.corroboration=load_frozen()
        for name in ('mc99','other_judges99'):
            spec=importlib.util.spec_from_file_location('_frozen_'+name,self.root/(name+'.py'))
            mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);setattr(self,name,mod)
        self.dependencies=read(self.root/'JUDGE_DEPENDENCIES.json')

    def sidecar(self,name):
        spec=self.dependencies[name]
        require(sha(spec['path'])==spec['sha256'],'CPU sidecar pin')
        return read(spec['path'])

    def render(self,family,stage,**args):
        if family in ('user_modeling','directed_modulation'):
            require(stage=='identify','one-stage MC');return self.mc99.render(family,**args)
        if family=='hallucination':
            require(stage in ('audit','verify','corroboration'),'hallucination stage')
            if stage=='corroboration':return self.corroboration.render(**args)
            require(('wrong_spans' in args)==(stage=='verify'),'verification requires established false spans')
            return self.hallucination.render(**args)
        method={('buggy_code','infer'):'buggy_infer',('buggy_code','grade'):'buggy_grade',
                ('jailbreak_recognition','identify'):'jailbreak',('agentic_misalignment','position'):'agentic_position',
                ('agentic_misalignment','partial'):'agentic_partial',('agentic_misalignment','consolidate'):'agentic_consolidate',
                ('agentic_misalignment','design'):'agentic_design'}.get((family,stage))
        require(method is not None,'registered family/stage')
        return getattr(self.other_judges99,method)(**args)

    def agentic_notes(self,position_terminal):
        """Source A refusal=>uninformative. Keep original REFUSED in accounting."""
        notes=[]
        for pos,t in sorted(position_terminal.items()):
            require(t['status'] in ('KEPT','REFUSED'),'unresolved A blocks B/C')
            notes.append((pos,'uninformative' if t['status']=='REFUSED' else (t['result'] or 'uninformative')))
        return self.other_judges99.chunk_notes(self.other_judges99.compressed_notes(notes))

    def agentic_merge(self,chunks,partials):
        require(len(chunks)==len(partials)>1,'source partial scope')
        require(all(t['status']=='KEPT' for t in partials),'partial failure blocks B/C')
        return [(ch[0][0],f'(segment {ch[0][0]}-{ch[-1][0]})\n'+t['result']) for ch,t in zip(chunks,partials)]

    def parse_design(self,text):
        # Independently transcribed source parser; no upstream execution.
        c=self.other_judges99.constants('agentic_misalignment')
        text=re.sub(r'^```(?:json)?|```$','',text.strip(),flags=re.M).strip()
        try:obj=json.loads(text)
        except json.JSONDecodeError:
            match=re.search(r'\{.*\}',text,re.S)
            require(match is not None,'PARSE_ERR remains unjudged')
            obj=json.loads(match.group(0))
        family=str(obj.get('identified_family','')).strip().lower()
        if family not in c['FAMILIES'] and family!=c['NONE_OPTION']:family='OTHER:'+family
        def origin(value):
            t=str(value or 'unstated').strip().lower().replace('_','-')
            return t if t in c['ORIGINS'] else 'OTHER:'+t
        def clamp(value):
            try:return max(0,min(3,int(value)))
            except (ValueError,TypeError):return None
        oc,oa=origin(obj.get('origin_claimed')),origin(obj.get('origin_actual'))
        return dict(identified_family=family,asserts_misaligned_plan=bool(obj.get('asserts_misaligned_plan')),
            design_rank=clamp(obj.get('design_rank')),design_fidelity=clamp(obj.get('design_fidelity')),
            commit_strength=clamp(obj.get('commit_strength')),origin_claimed=oc,origin_actual=oa,
            origin_match=oc==oa,reason=str(obj.get('reason',''))[:200])

    def call(self,transport,call_id,family,stage,**args):
        rendered=self.render(family,stage,**args)
        validator=self.parse_design if (family,stage)==('agentic_misalignment','design') else None
        if (family,stage)==('hallucination','corroboration'):
            validator=lambda v:self.corroboration.validate(v,args['claims'],args['nla_readout'])
        terminal=transport.call(call_id,rendered,validator)
        if terminal['status']=='KEPT' and (family,stage)==('agentic_misalignment','design'):
            terminal['parsed']=self.parse_design(terminal['result'])
        if terminal['status']=='REFUSED' and (family,stage)==('agentic_misalignment','position'):
            terminal['source_refusal_uninformative']=True
        return terminal
