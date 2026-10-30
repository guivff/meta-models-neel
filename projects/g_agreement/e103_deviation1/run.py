"""Separate once custody for validator-corrected E103; strict artifacts immutable."""
import argparse,hashlib,subprocess
from pathlib import Path
from projects.g_agreement.analysis_late import e103
from projects.g_agreement.analysis_late import common as c
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
AUTH='f60fd54fe3400d58d1c07257ad565e8567b23488'
LABEL='validator-corrected (E103 deviation 1)'
STRICT='ab66636893e245bc17d039db70ced486f1b6120485db78c60722a980c485c64f'
BASE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e103')
GUARD=BASE/'deviation1/ANALYSIS_ONCE.json'

def committed():
    c.committed()
    for name,h in c.read(HERE/'DEPENDENCIES.json').items():c.require(c.sha(ROOT/name)==h,'unchanged scientific source')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            b=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            c.require(hashlib.sha256(b).hexdigest()==c.sha(p),'uncommitted execution binding')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def validate(s):
    c.require(s['experiment']=='E103' and s['label']==LABEL and s['deviation']=='E103 deviation 1' and s['authority_commit']==AUTH,'exact authorized deviation')
    g=s['strict_guard'];p=Path(g['path']);c.require(p.resolve()==(BASE/'ANALYSIS_ONCE.json').resolve(),'original strict guard')
    c.require(c.sha(p)==g['sha256'],'strict guard unchanged')
    seal=s['strict_analysis_seal'];c.require(seal['sha256']==STRICT,'original strict seal');c.verify(seal['path'],STRICT)
    c.require(Path(s['analysis']).name=='validator_corrected_deviation1_once','distinct fixed output namespace')
    bundle=c.verify(s['data']['seal'],s['data']['sha256'])
    c.require(bundle['label']==LABEL and bundle['authority_commit']==AUTH,'corrected normalized source')
    for source in bundle['source_seals']:
        b=c.verify(source['seal'],source['sha256'])
        c.require(b['status']=='COMPLETE_VALIDATOR_CORRECTED_ONCE' and b['label']==LABEL and b['new_calls']==0,'sole corrected validator, no new call')
    return {str(p):g['sha256'],seal['path']:STRICT}

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();commit=committed();s=c.read(args.spec);before=validate(s)
    rows,bundle,inventory=c.normalized(s,'E103');e103.prepare(rows,inventory)
    out=c.core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['data']['sha256']),commit)
    result=e103.analyze(rows);result['label']=LABEL;result['strict_analysis_seal_sha256']=STRICT
    result['descriptive_extensions']={'D4':'not part of this E67 confirmatory adapter','E99':'not part of this E67 confirmatory adapter'}
    c.require(all(c.sha(p)==h for p,h in before.items()),'strict artifacts changed')
    c.write(out/'RESULTS.json',result);c.write(out/'BINDING.json',s)
    c.core.seal(out,'ANALYSIS_SEAL.json',experiment='E103',status='COMPLETE_ONCE',label=LABEL,authority_commit=AUTH,code_commit=commit,strict_analysis_seal_sha256=STRICT,strict_artifacts_unchanged=before,bootstrap_draws=c.DRAWS,seed=c.SEED)
if __name__=='__main__':main()
