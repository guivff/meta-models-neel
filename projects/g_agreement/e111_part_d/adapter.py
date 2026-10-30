import argparse,hashlib,subprocess
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.wmech2 import core as c
from projects.g_agreement.e111_analysis import adapter as original
from .analysis import features,analyze
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e111/part_d/ANALYSIS_ONCE.json'

def source_features(measurement, metadata, ref, weights):
    h=np.asarray(ref(measurement['natural']),float)
    hp=original.vector(h,metadata['vector_mode'],{k:ref(v) for k,v in measurement['vector_parameters'].items()})
    return features(h,hp,weights,ref(measurement['target_class']))


def split_report(rows):
    c.require(all(x['condition'] in ('steered','random') for x in rows),'sealed condition must be explicit')
    result={}
    for condition in ('steered','random'):
        selected=[x for x in rows if x['condition']==condition]
        result[condition]=analyze(selected) if selected else dict(status='NOT AVAILABLE',reason='no source-bound vectors for condition')
    return dict(experiment='E111',part='d',status='POST HOC EXPLORATORY',control='natural unmodified block44 baseline identical to original x1',primary=result['steered'],random_direction_reference=result['random'])


def inputs(s):
    # Revalidate original sealed source bindings; never call original analyze/main/guard.
    original_rows,census,_=original.inputs(s)
    old={x['id']:x for x in original_rows}
    ip=Path(s['inventory_seal']);op=Path(s['binding_seal'])
    inv=c.read(ip);b=c.read(op);meta=c.unique(c.read(ip.parent/'INVENTORY.json'));ms=c.unique(c.read(op.parent/'MEASUREMENTS.json'));probes=c.read(ip.parent/'PROBES.json');cache={}
    def ref(x):
        source=b['source_seals'][x['seal_index']];key=(x['seal_index'],x['member'])
        seal=c.read(source['seal']);c.require(x['member'] in seal['files'],'original sealed member')
        if key not in cache:
            p=Path(source['seal']).parent/x['member'];cache[key]=np.load(p,allow_pickle=False) if p.suffix in ('.npy','.npz') else c.read(p)
        v=cache[key]
        for k in x['keys']:v=v[k]
        return v
    weights={r:original.effective_weights(ref(p['coefficients']),p['preprocessing'],ref(p['feature_scale']) if p['preprocessing']=='standardized' else None) for r,p in probes.items()}
    rows=[];missing=[]
    for ident,x in meta.items():
        if x['experiment'] not in ('E101','E104_U') or x['vector_mode']=='natural':continue
        if ident not in ms:
            missing.append(dict(id=ident,reason='original natural/intervened vector unavailable'));continue
        c.require(x['condition'] in ('steered','random'),'original sealed condition')
        f=source_features(ms[ident],x,ref,weights[x['row']])
        c.require(np.isclose(f['probe_logit_shift'],old[ident]['x1'],atol=1e-6),'natural control agrees with original E111 x1 orientation')
        rows.append(dict(id=ident,experiment=x['experiment'],row=x['row'],condition=x['condition'],cluster_id=x['cluster_id'],y=old[ident]['y'],reconstructed=x['vector_mode']=='E101_reconstructed',**f))
    return rows,missing

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--analysis',required=True);a=p.parse_args()
    for f,h in c.read(HERE/'SOURCE_RECEIPT.json')['files'].items():
        c.require(c.sha(ROOT/f)==h and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+f],cwd=ROOT)).hexdigest()==h,'committed post-hoc source')
    s=c.read(a.spec);rows,missing=inputs(s);commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    out=c.claim(dict(analysis=a.analysis,guard=str(GUARD),output_sha256=s['binding_sha256']),commit)
    z=split_report(rows);z['missing_vectors']=len(missing)
    c.write(out/'RESULTS.json',z);c.write(out/'ITEM_FEATURES.PRIVATE.json',dict(rows=rows,missing=missing));c.write(out/'BINDING.json',s)
    c.seal(out,'ANALYSIS_SEAL.json',experiment='E111',part='d',status='COMPLETE_ONCE_EXPLORATORY',code_commit=commit)
if __name__=='__main__':main()
