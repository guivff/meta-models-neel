"""CPU-only E106 Arm P input and disjoint NLA gate selection; no judgments."""
import argparse,json,importlib.util
from pathlib import Path
import numpy as np
from projects.g_agreement.e96.reconstructor_check import digest,write
from projects.g_agreement.e96.prepare_smoke_inputs import verify

ROWS={'e57':['nesting_depth','indent_level','page_range_digit'],
      'e56':['linewrap_implicit'],
      'e49':['container_after_move','holder_after_handovers','branch_taken','var_type_at_use']}


def prepare(cache,bank_root,out,receipt):
    if out.exists():raise FileExistsError(out)
    templates=Path('results/g_agreement/understand/e102');verify(templates,'COMPLETE_TEMPLATES_SEAL.json')
    sources=[];lookup={};capture_meta={};items_by_bank={}
    def check(root,name):
        seal=verify(root,name);sources.append({'path':str(root/name),'sha256':digest(root/name),'files_verified':len(seal['files'])});return seal
    for bank,rows in ROWS.items():
        if bank=='e49':
            b=cache/'g_agreement/understand/e49/job_inputs_v1';check(b,'INPUT_SEAL.json')
            items=json.loads((b/'items.json').read_text())
            caps=[cache/'g_agreement/understand/e49/verified_section149/out/capture']
        else:
            b=bank_root/bank/'cache/bank_2026-10-27_v1'
            if digest(b/'BANK_SEAL.json')!=digest(Path('results/g_agreement/understand')/bank/'BANK_SEAL.json'):raise ValueError('bank identity')
            seal=json.loads((b/'BANK_SEAL.json').read_text())
            if digest(b/'items.PRIVATE.json')!=seal['files']['items.PRIVATE.json']:raise ValueError('bank items')
            sources.append({'path':str(b/'BANK_SEAL.json'),'sha256':digest(b/'BANK_SEAL.json'),'items_sha256':seal['files']['items.PRIVATE.json']})
            items=json.loads((b/'items.PRIVATE.json').read_text())
            caps=[cache/f'g_agreement/understand/e56_e57/verified_pull_single_v1/shard_{i}/out/{bank}/capture' for i in range(3)]
        items_by_bank[bank]=items
        for c in caps:
            check(c,'CAPTURE_SEAL.json');ids=json.loads((c/'items.order.json').read_text())
            arrays={l:np.load(c/f'acts{l}.npy',allow_pickle=False) for l in (42,44)}
            for i,key in enumerate(ids):
                if (bank,key) in lookup:raise ValueError('duplicate capture')
                lookup[bank,key]={l:a[i] for l,a in arrays.items()}
            capture_meta[str(c)]={'seal':digest(c/'CAPTURE_SEAL.json'),'shape':list(arrays[42].shape)}
    chosen=[]
    for bank,rows in ROWS.items():
        for row in rows:
            xs=[x for x in items_by_bank[bank] if x['feature']==row and x['split']=='test']
            if len(xs)!=84:raise ValueError('84test per row required: '+row)
            chosen += [(bank,x) for x in xs]
    public=[{'key':b+':'+x['id'],'id':x['id'],'bank':b,'row':'line_length' if x['feature']=='linewrap_implicit' else x['feature'],'source_row':x['feature'],'split':'test'} for b,x in chosen]
    # Three literal templates from dev values, fixed before any arm-P output.
    ts=json.loads((templates/'TEMPLATES.json').read_text())['rows']
    spec=importlib.util.spec_from_file_location('e106_page',templates/'page_range102.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    page=next(x for x in items_by_bank['e57'] if x['feature']=='page_range_digit' and x['split']=='dev')
    examples=[ts['nesting_depth']['three'][0],ts['indent_level']['four'][0],m.render_dev(page)[0]]
    prefix='Examples of structural descriptions:\n'+'\n'.join(examples)+'\n\n'
    out.mkdir(parents=True)
    write(out/'ITEMS.json',public)
    write(out/'PROMPT.json',{'prefix':prefix,'examples':examples,'templates_seal_sha256':digest(templates/'COMPLETE_TEMPLATES_SEAL.json'),'page_example_dev_id':page['id'],'selection':'first frozen template: depth three, indent four, first frozen page-range dev item actual digit'})
    for l in (42,44):np.save(out/f'acts{l}.npy',np.stack([lookup[b,x['id']][l] for b,x in chosen]),allow_pickle=False)
    # Original NLA supplement's first batch; compare first3, preserving its batch context.
    supplement=cache/'g_agreement/understand/e49/nla_supplement/verified_pull/out'
    check(supplement,'OUTPUT_SEAL.json');job=sorted((supplement/'jobs').glob('*.json'))[0]
    records=json.loads(job.read_text())
    if len(records)!=8 or any(r['native_max_new_tokens']!=512 or r['native_stop']!='</explanation>' for r in records):raise ValueError('original parity batch')
    write(out/'NLA_PARITY.json',{'compare_indices':[0,1,2],'records':records,'source_job_sha256':digest(job),'batch':8})
    np.save(out/'nla_parity42.npy',np.stack([lookup['e49',x['id']][42] for x in records]),allow_pickle=False)
    dev=[x for x in items_by_bank['e57'] if x['feature']=='nesting_depth' and x['split']=='dev'][:16]
    if len(dev)!=16:raise ValueError('16dev gate items')
    np.save(out/'gate_dev42.npy',np.stack([lookup['e57',x['id']][42] for x in dev]),allow_pickle=False)
    write(out/'GATE_DEV_IDS.json',[x['id'] for x in dev])
    write(out/'GATE_TARGETS.json',[{'id':x['id'],'split':'dev','text':'<explanation>\n'+ts['nesting_depth'][x['value']][0]+'\n</explanation>'} for x in dev])
    write(out/'INPUT_SEAL.json',{'status':'E106_P_AND_NLA_GATE_INPUTS_FROZEN','files':{p.name:digest(p) for p in sorted(out.iterdir())}})
    write(receipt,{'status':'CPU_INPUTS_READY_NO_MODEL_OUTPUT','source_seals':sources,'capture_metadata':capture_meta,'input_seal_sha256':digest(out/'INPUT_SEAL.json'),'input_directory':str(out.resolve()),'arm_p_items':672,'rows':8,'readers':['oracle','nla'],'arm_p_outputs_required':1344,'row_alias':{'E56/line_length':'E56/linewrap_implicit'},'parity_context_items':8,'parity_compared_items':3,'dev_gate_items':16,'labels_staged':False,'first_output_utc':None})

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('cache','bank-root','out','receipt'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prepare(a.cache,a.bank_root,a.out,a.receipt)
