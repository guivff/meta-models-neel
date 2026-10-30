"""CPU-only E110 reader admission contract; never selects, allocates or reads codes."""
from pathlib import Path
import hashlib,json,re,subprocess
CAP=5400
UPPER=9.94
BANK='b24e72f77d8ab29b8e3ab0fcf3f64ade4b25580cbca72c4b895c46e88756ef20'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify_shape(meta):
 assert meta['experiment']=='E110_READERS' and meta['gpu_type']=='H200'
 assert meta['cap_seconds']==CAP and meta['prior_probe_gpu_seconds']==0 and meta['gpu_forecast_upper_usd']==UPPER
 assert type(meta['selected_count']) is int and 60<=meta['selected_count']<=3000
 assert meta['fresh_extract_cpu_import_pass'] is True and meta['adapter_pre_output_verified'] is True and meta['C_channel_pre_output_verified'] is True
 assert meta['minimum_native_staging_need_seconds']<=CAP
 assert re.fullmatch('[0-9a-f]{40}',meta['inventory_commit'])
 assert meta['selection_guard_original'] is True and meta['all_selected_items_retained'] is True
 return True

def verify_seal(path,expected):
 path=Path(path);assert sha(path)==expected
 seal=read(path)
 for n,h in seal['files'].items():
  p=path.parent/n;assert p.resolve().is_relative_to(path.parent.resolve()) and sha(p)==h
 return seal

def verify_preparation(home,meta):
 home=Path(home);verify_shape(meta)
 frozen=read(home/'FROZEN_RUNTIME.json')
 for k in ['source_archive_sha256','source_sha256','timings_sha256']:assert meta[k]==frozen[k]
 assert sha(home/'source.tar.gz')==meta['source_archive_sha256']
 frozen_source=read(home.parents[3]/'results/g_agreement/i2/E110_READER_OPERATOR_SOURCE227.json')
 assert sha(home/'OPERATOR_FREEZE.json')==frozen_source['operator_source_sha256'],'COMMITTED_OPERATOR_FREEZE_CHANGED'
 selection=verify_seal(meta['selection_seal'],meta['selection_seal_sha256'])
 guard=read(home.parents[4]/'wt-wtext/results/g_agreement/understand/e110/cache/FILTER_SELECTION_DEV2_ONCE.json')
 assert Path(guard['out']).resolve()==Path(meta['selection_seal']).parent.resolve() and guard['receipt_sha256']==selection['filter_receipt_sha256'] and guard['input_seal_sha256']==BANK,'ORIGINAL_ONCE_SELECTOR_BINDING'
 assert selection['experiment']=='E110' and selection['phase']=='deviation2_obscure' and selection['status']=='COMPLETE_ONCE' and selection['input_seal_sha256']==BANK
 counts=read(Path(meta['selection_seal']).parent/'COUNTS.json')
 assert counts['status']=='READY' and counts['selected_wrong']>=60 and counts['selected_wrong']+counts['matched_right']==meta['selected_count']
 assert counts['companion_E82_excluded_from_primary'] is True
 inventory=verify_seal(meta['inventory_seal'],meta['inventory_seal_sha256'])
 assert inventory['experiment']=='E110' and inventory['survivor_counts']['belief_wrong']==counts['selected_wrong'] and inventory['survivor_counts']['belief_right']==counts['matched_right']
 repo=Path(meta['inventory_repo']);rel=Path(meta['inventory_seal']).resolve().relative_to(repo.resolve()).as_posix()
 committed=subprocess.check_output(['git','show',meta['inventory_commit']+':'+rel],cwd=repo)
 assert hashlib.sha256(committed).hexdigest()==meta['inventory_seal_sha256'],'PRE_OUTPUT_COMMITTED_INVENTORY_REQUIRED'
 for name,h in meta['operator_files_sha256'].items():assert sha(home/name)==h,'FROZEN_OPERATOR_CHANGED'
 for name,h in meta['input_parts_sha256'].items():assert sha(home/name)==h
 assert meta['prospective_source_bindings']==read(home/'OPERATOR_FREEZE.json')['prospective_source_bindings']
 assert {x['role'] for x in meta['prospective_source_bindings']}=={'worker','W-mech2_adapter','C_channel'}
 for name,h in read(home/'OPERATOR_FREEZE.json')['external_files'].items():assert sha(name)==h,'FROZEN_ADMISSION_HELPER_CHANGED'
 for binding in meta['prospective_source_bindings']:
  assert sha(binding['path'])==binding['sha256'],'PROSPECTIVE_ADAPTER_OR_C_SOURCE_CHANGED'
 return True
