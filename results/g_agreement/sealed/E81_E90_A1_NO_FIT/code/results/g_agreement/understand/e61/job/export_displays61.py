"""Once-only D2/D6 export from verified E56/E57 pulls; no example substitution."""
import argparse,sys,json
from pathlib import Path
import numpy as np
from runtime61 import HERE,require,verify_dependencies
from contract56 import read,dump,verify,sha,seal,ROOT
from analysis_io import collect,claim_once
from displays61 import verbatim_records,injection_display,display_html


def probe_scores(spec,inj):
    import torch
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.probes import fit_logreg
    pins=read(HERE/'D6_PROBE_BINDING.json')
    for name,d in pins['files'].items():require(sha(d['path'])==d['sha256'],'D6 source '+name)
    source=Path(pins['capture']);order=read(source/'items.order.json');ix={k:i for i,k in enumerate(order)}
    labels=[json.loads(s) for s in Path(pins['labels']).read_text().splitlines()];dev=sorted([x for x in labels if x['feature']=='prose_sentiment' and x['split']=='dev'],key=lambda x:x['id'])
    require(len(dev)==84,'E36 dev only');y=torch.tensor([int(x['value']=='positive') for x in dev]);require(int(y.sum())==42,'positive orientation')
    h=np.load(source/'acts44.npy',mmap_mode='r');torch.set_num_threads(1);torch.manual_seed(20261027)
    model=fit_logreg(torch.from_numpy(np.array(h[[ix[x['id']] for x in dev]],dtype=np.float32)),y)
    vectors=np.load(inj/'INPUT_VECTORS.npz')['activations'];items=[x for x in read(inj/'ITEMS.json')['items'] if x['row']=='prose_sentiment']
    scores=model.decision(torch.from_numpy(vectors[[x['index'] for x in items]].copy())).tolist()
    return {x['id']:float(v) for x,v in zip(items,scores)}


def main():
    verify_dependencies()
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args();s=read(a.spec)
    require(sha(a.spec)==read(HERE/'DISPLAY_COMMAND.json')['spec_sha256'],'display spec pin');verify(HERE,'SOURCE_SEAL.json',s['source_seal_sha256'])
    s56=read(s['e56_spec']);s57=read(s['e57_spec']);d56=collect(s56,'E56');d57=collect(s57,'E57')
    out=claim_once(s['output'],'E61_D2_D6',sha(a.spec));selection=read(HERE/'SELECTION.json');cards=[];missing=[]
    for arm,key,records in [('implicit','implicit_ids',d56['native']),('report','report_ids',d56['native']),('first_letter','first_letter_ids',d57['native'])]:
        for k in selection['D2'][key]:
            try:cards+=verbatim_records(records,[k])
            except ValueError as error:missing.append({'arm':arm,'item_id':k,'reason':str(error)})
    dump(out/'D2_VERBATIM.json',cards);dump(out/'D2_MISSING.json',missing)
    (out/'D2.html').write_text(display_html('D2 three framings',cards)+'<p>Missing registered acquisitions: '+str(len(missing))+'. See D2_MISSING.json; no substitute examples.</p>')
    inj=Path(s56['inputs'])/'injection';d6=injection_display(d56['native'],read(inj/'ITEMS.json')['items'],probe_scores(s,inj));dump(out/'D6.json',d6)
    (out/'D6.html').write_text(display_html('D6 both sentiment directions, all arms',d6['readouts'])+'<pre>'+json.dumps(d6['probe_scores'],indent=2)+'</pre>')
    seal(out,'DISPLAY_SEAL.json',{'experiment':'E61_D2_D6','status':'D2_PARTIAL_D6_COMPLETE' if missing else 'COMPLETE','source_seal_sha256':s['source_seal_sha256']})
if __name__=='__main__':main()
