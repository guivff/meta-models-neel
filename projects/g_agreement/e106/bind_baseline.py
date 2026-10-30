"""Bind Arm P to sealed native texts on CPU; never regenerates native baselines."""
import argparse,json
from pathlib import Path
from projects.g_agreement.e96.reconstructor_check import digest,write
from projects.g_agreement.e96.prepare_smoke_inputs import verify


def bind(cache,inputs,out,receipt):
    if out.exists():raise FileExistsError(out)
    verify(inputs,'INPUT_SEAL.json');items=json.loads((inputs/'ITEMS.json').read_text())
    required={(x['bank'],x['id'],r) for x in items for r in ('oracle','nla')};records={};sources=[]
    def take(bank,reader,x,path,seal):
        key=(bank,x.get('unit_id',x['id']),reader)
        if key not in required:return
        if key in records:
            if (records[key]['raw'],records[key]['text'])!=(x['raw'],x['text']):raise ValueError('conflicting native baseline')
            return
        if reader=='nla' and (x.get('native_max_new_tokens')!=512 or x.get('native_stop')!='</explanation>'):raise ValueError('NLA baseline contract')
        records[key]={'bank':bank,'id':key[1],'reader':reader,'raw':x['raw'],'text':x['text'],'source_file':str(path),'source_file_sha256':digest(path),'source_seal_sha256':seal}
    for bank in ('e56','e57'):
        for shard in range(3):
            root=cache/f'g_agreement/understand/analysis402_verified/{bank.upper()}/shard_{shard}/out'
            if not (root/'OUTPUT_SEAL.json').exists():continue
            seal=verify(root,'OUTPUT_SEAL.json');sha=digest(root/'OUTPUT_SEAL.json');sources.append({'path':str(root/'OUTPUT_SEAL.json'),'sha256':sha})
            paths=sorted((root/bank.upper()/'jobs').glob('*.json'))+sorted((root/'jobs').glob('*.json'))
            for f in paths:
                if str(f.relative_to(root)) not in seal['files']:continue
                data=json.loads(f.read_text())
                for x in data:
                    if x.get('kind')=='text' and x.get('reader') in ('oracle','nla'):take(bank,x['reader'],x,f,sha)
    root=cache/'g_agreement/understand/e49/verified_section149/out/readers';verify(root,'READER_OUTPUT_SEAL.json');sha=digest(root/'READER_OUTPUT_SEAL.json');sources.append({'path':str(root/'READER_OUTPUT_SEAL.json'),'sha256':sha})
    for row in ('container_after_move','holder_after_handovers','branch_taken','var_type_at_use'):
        f=root/row/'oracle_native.jsonl'
        for x in map(json.loads,f.read_text().splitlines()):take('e49','oracle',x,f,sha)
    root=cache/'g_agreement/understand/e49/nla_supplement/verified_pull/out';verify(root,'OUTPUT_SEAL.json');sha=digest(root/'OUTPUT_SEAL.json');sources.append({'path':str(root/'OUTPUT_SEAL.json'),'sha256':sha})
    f=root/'nla_native.jsonl'
    for x in map(json.loads,f.read_text().splitlines()):take('e49','nla',x,f,sha)
    missing=sorted(required-set(records))
    legacy=[]
    original=cache/'g_agreement/understand/e49/verified_section149/out/readers'
    original_sha=digest(original/'READER_OUTPUT_SEAL.json')
    for bank,key,reader in missing:
        if bank!='e49' or reader!='nla':continue
        f=original/key.split(':')[0]/'nla_native.jsonl'
        matches=[x for x in map(json.loads,f.read_text().splitlines()) if x['id']==key]
        if len(matches)!=1:raise ValueError('unique legacy baseline required')
        x=matches[0]
        legacy.append({'bank':bank,'id':key,'reader':reader,'raw':x['raw'],'text':x['text'],
                       'source_file':str(f),'source_file_sha256':digest(f),'source_seal_sha256':original_sha,
                       'native_max_new_tokens':128,'legacy_contract':True})
    out.mkdir(parents=True);write(out/'NATIVE_BASELINE.CPU.json',[records[k] for k in sorted(records)])
    write(out/'LEGACY128_BASELINE.CPU.json',legacy)
    write(out/'BASELINE_SEAL.json',{'files':{p.name:digest(p) for p in sorted(out.iterdir())},'status':'COMPLETE' if not missing else 'CORRECTED_NATIVE_BASELINE_MISSING_LEGACY_BOUND_SEPARATELY'})
    write(receipt,{'experiment':'E106','arm':'P','status':'SEALED_NATIVE_BASELINE_BOUND' if not missing else 'CORRECTED_NATIVE_BASELINE_MISSING_LEGACY_BOUND_SEPARATELY','required':len(required),'bound':len(records),'missing_corrected512':missing,'legacy128_bound':len(legacy),'legacy_note':'NLA holder_after_handovers has original128-token sealed baseline only; corrected512 supplement absent. No regenerated/substituted baseline. I-4/sole adapter must preserve this cap mismatch in R-FX0.','sources':sources,'baseline_seal_sha256':digest(out/'BASELINE_SEAL.json'),'baseline_directory':str(out.resolve()),'input_seal_sha256':digest(inputs/'INPUT_SEAL.json'),'baseline_regenerated':False,'judge_outputs_used':False,'cpu_only':True,'first_output_utc':None})

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('cache','inputs','out','receipt'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();bind(**vars(a))
