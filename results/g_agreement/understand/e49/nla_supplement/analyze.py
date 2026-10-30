"""Once-only descriptive supplement with the unchanged E49 native scorer."""
import argparse,json,sys
from pathlib import Path
from prepare import HERE,ROOT,E56
from contract56 import read,dump,verify,sha,seal,require
sys.path.insert(0,str(HERE.parent/'job'))
from analysis49 import summarize_native
from native_nla512 import truncation_summary
from analysis_io import claim_once

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args();s=read(a.spec)
 require(sha(a.spec)==read(HERE/'ANALYSIS_COMMAND.json')['spec_sha256'],'spec identity');verify(HERE,'SOURCE_SEAL.json',read(HERE/'ANALYSIS_COMMAND.json')['analysis_source_seal_sha256']);verify(Path(s['executed_source_root']),'SOURCE_SEAL.json',s['source_seal_sha256']);require(sha(s['executed_source_archive'])==s['executed_source_archive_sha256'],'executed archive identity')
 for path,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/path)==digest,'unchanged scorer/dependency')
 b=read(HERE/'INPUT_BINDING.json');require(sha(b['private_items'])==b['private_items_sha256'],'original labels');original=Path(b['original_analysis']);verify(original,'ANALYSIS_SEAL.json');require(sha(original/'NATIVE_PRIMARY.json')==b['original_native_primary_sha256'],'original result unchanged')
 root=Path(s['output']);receipt=read(s['receipt']);require(receipt['verified'] is True and receipt['experiment']=='E49_NLA_SUPPLEMENT','verified pull');o=verify(root,'OUTPUT_SEAL.json',receipt['output_seal_sha256']);require(o['source_seal_sha256']==s['source_seal_sha256'] and o['input_seal_sha256']==b['input_seal_sha256'] and o['pod_id']==receipt['pod_id'],'custody identity')
 ass=read(root/'ASSIGNMENT.json');import importlib.util
 module_spec=importlib.util.spec_from_file_location('executed_supplement_worker',Path(s['executed_source_root'])/'worker.py');module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module);module.custody(ass,ass['stage_started_epoch']);require(read(root/'TIMING.json')['completed_epoch']<ass['absolute_deadline_epoch'],'stage cap')
 records=[json.loads(t) for t in (root/'nla_native.jsonl').read_text().splitlines()];items=read(Path(b['inputs'])/'items.json');require(len(records)==672 and {x['id'] for x in records}=={x['id'] for x in items},'same item grid');labels={x['id']:x['label'] for x in read(b['private_items'])}
 out=claim_once(s['analysis_out'],'E49_NLA_SUPPLEMENT',sha(a.spec));old=read(original/'NATIVE_PRIMARY.json');result={}
 for row in b['qualified_rows']:
  xs=[x for x in records if x['feature']==row];ids=[x['id'] for x in items if x['feature']==row]
  result[row]={'original_sealed':old['rows'][row],'supplement_NLA':summarize_native(row,xs,ids,labels)}
 dump(out/'SIDE_BY_SIDE.json',result);dump(out/'NLA_TRUNCATION.json',truncation_summary(records))
 (out/'RESULTS.md').write_text('# E49 NLA supplement — DESCRIPTIVE\n\nSame8gated rows and84items/row, sealed block42. NLA greedy512with closing-tag stop; unchanged E49 scorer. SIDE_BY_SIDE.json retains the sealed original beside the supplement. This replaces nothing and enters neither E49 nor E52 rules.\n')
 seal(out,'ANALYSIS_SEAL.json',{'experiment':'E49_NLA_SUPPLEMENT','status':'COMPLETE_ONCE','descriptive_only':True,'original_analysis_unchanged':True})
if __name__=='__main__':main()
