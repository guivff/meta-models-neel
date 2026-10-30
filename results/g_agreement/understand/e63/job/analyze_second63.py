"""Once-only E63 regex analysis with authorized single-readout grid; coding owner W-internals."""
import argparse,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'e56/job'))
from contract56 import ROOT,read,sha,verify,dump,seal,require
from vendor_readerbench.io import load_bundle
from vendor_readerbench.e63 import validate_scope
from vendor_readerbench.score_reader import score

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args();s=read(a.spec);require(sha(a.spec)==read(HERE/'ANALYSIS_COMMAND.json')['spec_sha256'],'analysis spec pin');verify(HERE,'SOURCE_SEAL.json',s['source_seal_sha256'])
 for name,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==digest,'source dependency')
 receipt=read(s['receipt']);require(receipt['verified'] is True and receipt['experiment']=='E63','verified acquisition');root=Path(s['output']);verify(root,'OUTPUT_SEAL.json',receipt['output_seal_sha256'])
 bundle=Path(s['bundle']);br=read(s['bundle_receipt']);require(br['verified'] is True and br['e63_output_seal_sha256']==sha(root/'OUTPUT_SEAL.json'),'normalizer binds exact E63 output');data,_=load_bundle(bundle,br['input_seal_sha256']);validate_scope(data)
 raw={x['reader']+':'+x['vector_id']:x for r in ('oracle','nla') for x in map(__import__('json').loads,(root/(r+'.jsonl')).read_text().splitlines())}
 require(len(raw)==800 and len(data['placebo'])==800,'one readout for 400 vectors per reader')
 for x in data['placebo']:
  k=x['reader']+':'+x['item_id'];require(k in raw and x['text']==raw[k]['text'] and x['repeat']==0,'unaltered pool normalization')
 guard=ROOT/'cache/g_agreement/understand/e63/REGEX_ANALYSIS_ONCE.json';guard.parent.mkdir(parents=True,exist_ok=True);out=Path(s['analysis_out']);require(not out.exists(),'output already exists')
 with guard.open('x') as f:f.write(sha(a.spec)+'\n')
 try:
  result={r:score(data,r) for r in ('oracle','nla')};out.mkdir(parents=True);dump(out/'REGEX_RESULTS.json',result);dump(out/'R_P2_STATUS.json',{'status':'W_INTERNALS_CODING_INPUT_READY','authority':'existing separate sealed coding command; no judge calls authorized here'});seal(out,'ANALYSIS_SEAL.json',{'experiment':'E63','status':'COMPLETE_ONCE','input_seal_sha256':br['input_seal_sha256'],'source_seal_sha256':s['source_seal_sha256']})
 except BaseException as e:dump(guard.with_name('REGEX_FAILURE.json'),{'error':str(e)});raise
if __name__=='__main__':main()
