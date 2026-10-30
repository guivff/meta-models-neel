"""Fill frozen E110 operator data after original selection; no GPU/API effects."""
from pathlib import Path
import argparse,hashlib,io,json,math,tarfile
from e110_reader_contract227 import read,sha,verify_preparation

def prepare(home,intake):
 home=Path(home);d=read(intake);runtime=read(home/'FROZEN_RUNTIME.json')
 assert not (home/'PREPARATION.json').exists() and not (home/'CREATE_ONCE_INTENT.json').exists()
 sel=Path(d['selection_seal']);inputs=sel.parent/'PUBLIC_READER_INPUTS.json';items=read(inputs)
 assert len(items)==len({x['id'] for x in items}) and all(set(x)=={'id','prompt','input_ids','read_position'} for x in items)
 assert all(x['read_position']==len(x['input_ids'])-1 for x in items)
 with tarfile.open(home/'source.tar.gz') as t:
  timings=json.load(t.extractfile('results/g_agreement/understand/late198/E110_RETAINED_NATIVE_TIMINGS.json'))
 rates={r:max(x['seconds'] for x in timings if x['phase']==r+'_native') for r in ['oracle','nla']}
 setup=sum(max(x['seconds']for x in timings if x['phase']==k)for k in ['nla_setup','nla_warmup_discarded'])
 minimum=453.621612+1.25*(math.ceil(len(items)/32)*sum(rates.values())+setup)+60
 with tarfile.open(home/'inputs.tar.gz','w:gz') as t:
  b=inputs.read_bytes();m=tarfile.TarInfo('PUBLIC_INPUTS.json');m.size=len(b);m.mtime=0;t.addfile(m,io.BytesIO(b))
 parts={'inputs.tar.gz':sha(home/'inputs.tar.gz')}
 frozen=read(home/'OPERATOR_FREEZE.json');d['prospective_source_bindings']=frozen['prospective_source_bindings']
 meta=dict(d,**runtime,experiment='E110_READERS',gpu_type='H200',cap_seconds=5400,prior_probe_gpu_seconds=0,gpu_forecast_upper_usd=9.94,selected_count=len(items),public_inputs_sha256=sha(inputs),input_archive_sha256=sha(home/'inputs.tar.gz'),input_parts_sha256=parts,minimum_native_staging_need_seconds=minimum,capture_fit_requires_actual_original_profile=True,selection_seal_sha256=sha(sel),inventory_seal_sha256=sha(d['inventory_seal']),fresh_extract_cpu_import_pass=True,adapter_pre_output_verified=True,C_channel_pre_output_verified=True,selection_guard_original=True,all_selected_items_retained=True,operator_files_sha256=read(home/'OPERATOR_FREEZE.json')['files'])
 verify_preparation(home,meta)
 with (home/'PREPARATION.json').open('x') as f:json.dump(meta,f,indent=2)
 return {'status':'PREPARED_NO_ALLOCATION','selected_count':len(items),'minimum_native_staging_need_seconds':minimum,'registered_cap_seconds':5400}

def main():
 p=argparse.ArgumentParser();p.add_argument('--home',required=True,type=Path);p.add_argument('--intake',required=True,type=Path);a=p.parse_args();print(json.dumps(prepare(a.home,a.intake)))
if __name__=='__main__':main()
