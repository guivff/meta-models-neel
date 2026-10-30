"""Metadata-only binding for the already frozen integrator-only words command."""
from pathlib import Path
import json,hashlib
NATIVE='25b38da7c35387315a54d0c42f85ecba83fd10347a20cf40a5bb418bf9713f58'
UNIT='8df559faf25a338b0c30ff9e53e3e9a03df3c5c03fdd316d0c8272004373c501'
ROOT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-c/cache/g_agreement/understand/internals_c/E136/native_units250')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def entries_for(joins,key):
 if len(joins)!=400 or len({r['item_id']for r in joins})!=400 or len(key)!=320:raise ValueError('original400 native units/320 TEST labels')
 entries=[]
 for r in joins:
  item=r['item_id'];ref=r['source_ref']
  if r['layer']!=44 or r['native_id']!=item+':oracle:44' or ref['sha256']!=NATIVE:raise ValueError('exact original Oracle44 native record identity')
  if not ref['member'].startswith('jobs/')or not ref['member'].endswith('.json')or len(ref['keys'])!=2 or type(ref['keys'][0])is not int or ref['keys'][0]<0 or ref['keys'][1]!='text':raise ValueError('literal original text pointer')
  if item not in key:continue
  meta=key[item]
  if r['split']!='test'or any(r[k]!=meta[k]for k in ('cue','pair_id','split')):raise ValueError('original TEST cue/pair/split binding')
  seal=Path(ref['seal'])
  if seal.name!='OUTPUT_SEAL.json':raise ValueError('original native seal, never judge seal')
  entries.append(dict(item_id=item,block=44,root=str(seal.parent),seal_name=seal.name,seal_sha256=NATIVE,member=ref['member'],record_path=[ref['keys'][0]],identity=dict(id=r['native_id'],item_id=item,reader='oracle',source_layer=44),text_field='text'))
 if len(entries)!=320 or {r['item_id']for r in entries}!=set(key):raise ValueError('full unique320 TEST readouts, no substitution')
 return sorted(entries,key=lambda r:r['item_id'])
def main(out):
 out=Path(out)
 if out.exists():raise FileExistsError('fresh metadata binding only')
 from projects.g_agreement.e136_words.run_once import labels
 code_root=Path(__file__).resolve().parents[3];code=code_root/'projects/g_agreement/e136_words/CODE_SEAL.json'
 for name,h in json.loads(code.read_text())['files'].items():
  if sha(code_root/name)!=h:raise ValueError('frozen prospective words source changed')
 binding,key=labels() # Original CPU labels only, no native output/guard/fit.
 p=ROOT/'UNIT_SEAL.json'
 if sha(p)!=UNIT:raise ValueError('original C unit custody')
 s=json.loads(p.read_text());m=ROOT/'SOURCE_POINTERS.PRIVATE.json'
 if sha(m)!=s['files'][m.name]:raise ValueError('sealed original source-pointer member')
 joins=json.loads(m.read_text());entries=entries_for(joins,key)
 guard=Path(binding['CPU_only_root']).parent/'E136_WORDS_ONCE.json'
 if guard.exists():raise FileExistsError('existing once attempt; do not compete/retry')
 out.mkdir();(out/'SPEC.PRIVATE.json').write_text(json.dumps(dict(experiment='E136_WORDS',entries=entries,source='ORIGINAL_NATIVE_ONLY_NO_JUDGMENT_CODES',native_sha256=NATIVE,unit_seal_sha256=UNIT),indent=2,sort_keys=True)+'\n')
 p=out/'SPEC.PRIVATE.json';(out/'SPEC_SEAL.json').write_text(json.dumps(dict(experiment='E136_WORDS_SOURCE',status='COMPLETE_METADATA_BINDING',entries=320,actual_native_readout_texts_opened=False,fit=False,guard_consumed=False,files={p.name:sha(p)}),indent=2,sort_keys=True)+'\n')
 print('metadata SPEC prepared',sha(p),'320 TEST pointers; no native text/fit/guard/judgments')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
