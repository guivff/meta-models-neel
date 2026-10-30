"""CPU-only full paired E106 inventory and label-free evaluation vector package."""
import argparse,importlib.util,json
from collections import Counter
from pathlib import Path
import numpy as np
from projects.g_agreement.e96.reconstructor_check import write,digest
from projects.g_agreement.e96.prepare_smoke_inputs import verify

ROWS={'e57':['nesting_depth','indent_level','page_range_digit'],
      'e49':['container_after_move','holder_after_handovers','branch_taken','var_type_at_use'],
      'e56':['linewrap_implicit','fact_recall','tense_implicit'],
      'e59':['format_plan','language_plan']}
CONTENT={'format_plan','language_plan','fact_recall','tense_implicit'}


def make_placebos(calibration):
    verify(calibration,'CALIBRATION_SEAL.json')
    c=json.loads((calibration/'CALIBRATION.json').read_text())
    generator=Path('results/g_agreement/understand/e76/common76.py')
    spec=importlib.util.spec_from_file_location('e106_e76_generator',generator);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    z=np.random.default_rng(20261031).standard_normal((200,5120)).astype(np.float32)
    banks=np.array(c['source_bank_indices_by_pool_index'][:200],dtype=int)
    if len(banks)!=200 or not np.all((0<=banks)&(banks<5)):raise ValueError('E76 source-bank references')
    arrays={l:m.norm_match(z,np.array(c['source_bank_median_norms'][str(l)])[banks]) for l in (42,44)}
    return arrays,{'generator':str(generator),'generator_sha256':digest(generator),'calibration_seal_sha256':digest(calibration/'CALIBRATION_SEAL.json'),
                   'gaussian_seed':20261031,'count':200,'dimension':5120,'norm_policy':'E76 norm_match; first200 frozen E76 source-bank assignments and corresponding sealed native bank medians',
                   'metric':'blind any-trained-value statement rate; no binary pseudo-labels'}


def build(cache,bank_root,e59_capture,calibration,train_selection,out,inventory_dir,receipt):
    if out.exists() or inventory_dir.exists():raise FileExistsError('new evaluation and inventory directories required')
    verify(train_selection,'INPUT_SEAL.json')
    trained=json.loads((train_selection/'DEV_PAIRS.json').read_text());train_keys={x['key'] for x in trained}
    sources=[];selected=[];vector_lookup={}
    for bank,rows in ROWS.items():
        folder=bank_root/bank/('cache/frozen_2026-10-26' if bank=='e49' else 'cache/bank_2026-10-27_v1')
        if digest(folder/'BANK_SEAL.json')!=digest(Path('results/g_agreement/understand')/bank/'BANK_SEAL.json'):raise ValueError('bank identity')
        seal=json.loads((folder/'BANK_SEAL.json').read_text());ip=folder/'items.PRIVATE.json'
        if digest(ip)!=seal['files']['items.PRIVATE.json']:raise ValueError('private items bytes')
        sources.append({'path':str(folder/'BANK_SEAL.json'),'sha256':digest(folder/'BANK_SEAL.json'),'items_sha256':digest(ip)})
        items=json.loads(ip.read_text())
        for row in rows:
            xs=[x for x in items if x['feature']==row and x['split']=='test']
            if len(xs)!=84 or Counter(x['label'] for x in xs)!=Counter({0:42,1:42}):raise ValueError('balanced84 test row')
            selected += [(bank,x) for x in xs]
        if bank=='e49':caps=[cache/'g_agreement/understand/e49/verified_section149/out/capture']
        elif bank=='e59':caps=[e59_capture]
        else:caps=[cache/f'g_agreement/understand/e56_e57/verified_pull_single_v1/shard_{i}/out/{bank}/capture' for i in range(3)]
        for c in caps:
            verify(c,'CAPTURE_SEAL.json');ids=json.loads((c/'items.order.json').read_text());a={l:np.load(c/f'acts{l}.npy',allow_pickle=False) for l in (42,44)}
            if any(v.shape!=(len(ids),5120) or not np.isfinite(v).all() for v in a.values()):raise ValueError('capture shape/finite')
            for i,key in enumerate(ids):
                if (bank,key) in vector_lookup:raise ValueError('duplicate native capture')
                vector_lookup[bank,key]={l:v[i] for l,v in a.items()}
            sources.append({'path':str(c/'CAPTURE_SEAL.json'),'sha256':digest(c/'CAPTURE_SEAL.json')})
    public=[];private=[]
    for bank,x in selected:
        row='line_length' if x['feature']=='linewrap_implicit' else x['feature'];key=bank+':'+x['id']
        if key in train_keys:raise ValueError('test/optimizer overlap')
        public.append({'key':key,'id':x['id'],'row':row,'source_row':x['feature'],'bank':bank,'split':'test','content':row in CONTENT})
        private.append('A' if x['label']==1 else 'B')
    if len(public)!=1008 or len({x['key'] for x in public})!=1008:raise ValueError('12unique84-item rows')
    placebos,placebo_meta=make_placebos(calibration)
    for i in range(200):public.append({'key':f'placebo:{i:03d}','id':f'placebo:{i:03d}','row':'placebo','source_row':'placebo','bank':'E76','split':'placebo','content':False})
    inventory=[];availability={r:{a:{} for a in ('P','T')} for r in ('oracle','nla')}
    for reader in ('oracle','nla'):
        for arm in ('P','T'):
            for i,x in enumerate(public):
                if arm=='P' and (x['content'] or x['row']=='placebo'):continue
                record={'id':reader+':'+arm+':'+x['key'],'item_id':x['key'],'reader':reader,'arm':arm,'row':x['row'],'split':x['split']}
                if x['split']=='test':record['target_by_cell']={'original':private[i],'intervention':private[i]}
                inventory.append(record)
            counts=Counter(x['row'] for x in inventory if x['reader']==reader and x['arm']==arm)
            availability[reader][arm]={row:{'count':n,'reason':''} for row,n in counts.items()}
    if len(inventory)!=3760:raise ValueError('all P/T/readers paired inventory')
    out.mkdir(parents=True);inventory_dir.mkdir(parents=True)
    write(out/'EVAL_ITEMS.json',public)
    for l in (42,44):np.save(out/f'acts{l}.npy',np.concatenate([np.stack([vector_lookup[b,x['id']][l] for b,x in selected]),placebos[l]]),allow_pickle=False)
    write(out/'INPUT_SEAL.json',{'status':'E106_PAIRED_TEST_PLACEBO_VECTORS_FROZEN','files':{p.name:digest(p) for p in sorted(out.iterdir())},'placebo_seed':20261031})
    # Only this CPU file contains truth. A committed inventory seal binds its bytes;
    # the file itself is ignored, kept off pods, and never placed in GPU archives.
    write(inventory_dir/'INVENTORY.json',inventory)
    write(inventory_dir/'INVENTORY_SEAL.json',{'experiment':'E106','placebo_seed':20261031,'files':{'INVENTORY.json':digest(inventory_dir/'INVENTORY.json')},
          'availability':availability,'legacy_nla_holder_original_max_tokens':128,'new_max_tokens':512,'row_alias':{'E56/line_length':'E56/linewrap_implicit'},
          'label_mapping_source':'E49 freeze_bank.py / E56 bank56.py / E57 bank57.py / E59 build59.py: label1=A, label0=B',
          'planned_closed_Oracle_T':'Retain full planned inventory; terminal NOT RUN disposition supplied by I-4, no readouts admitted'})
    write(receipt,{'status':'FULL_PAIRED_INVENTORY_AND_EVAL_VECTORS_FROZEN_NO_OUTPUT','paired_units':3760,'P_per_reader':672,'T_per_reader':1208,'ordinary_test_items':1008,'placebos':200,
                   'vectors_directory':str(out.resolve()),'input_seal_sha256':digest(out/'INPUT_SEAL.json'),'inventory_seal':str((inventory_dir/'INVENTORY_SEAL.json').resolve()),'inventory_seal_sha256':digest(inventory_dir/'INVENTORY_SEAL.json'),
                   'cpu_inventory_sha256':digest(inventory_dir/'INVENTORY.json'),'labels_cpu_only':True,'train_test_overlap':0,'training_input_seal_sha256':digest(train_selection/'INPUT_SEAL.json'),
                   'sources':sources,'placebo':placebo_meta,'first_output_utc':None})

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('cache','bank-root','e59-capture','calibration','train-selection','out','inventory-dir','receipt'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();build(**vars(a))
