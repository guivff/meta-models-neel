"""Once-only CPU dev probes for E85/E91/E92; produces a public release receipt, not GO."""
import argparse
import os
from pathlib import Path
from contract import *
from cpu_gates import probes

def build_groups(exp,private,order):
    key=lambda x:x.get('public_id',x['id'])
    rows={key(x):x for x in private}
    require(set(order)==set(rows),'capture exactly matches private owner map')
    conditions=[('genre','genre'),('addressed','addressed')] if exp=='E85' else (
        [(kind,'label') for kind in ('statements','instructions','plans')] if exp=='E91' else [('source','label')])
    groups=[]
    for name,target in conditions:
        chosen=[rows[i] for i in order if exp!='E91' or rows[i]['type']==name]
        dev=[x for x in chosen if x['split']=='dev'];test=[x for x in chosen if x['split']=='test']
        cluster={'E85':'matched_set','E91':'pair_id','E92':'content_id'}[exp]
        for layer in (42,44):
            groups.append(dict(name=name,layer=layer,dev_ids=[key(x) for x in dev],test_ids=[key(x) for x in test],
                dev_labels=[x[target] for x in dev],test_labels=[x[target] for x in test],
                dev_cluster_ids=[x[cluster] for x in dev],test_cluster_ids=[x[cluster] for x in test]))
    return groups,[i for i in order if rows[i]['split']=='test']

def run(config_path,capture,capture_sha,out):
    cfg=read(config_path);exp=cfg['experiment']
    require(exp in ('E85','E91','E92'),'registered CPU bank adapter')
    require(sha(cfg['private_path'])==cfg['private_sha256'],'private owner freeze')
    s=verify(capture,'STAGE_SEAL.json',capture_sha)
    require(s['experiment']==exp and not s.get('synthetic',False) and s['input_seal_sha256']==cfg['input_seal_sha256'], 'authentic matching capture')
    order=read(capture/'items.order.json');private=read(cfg['private_path'])
    groups,reader_ids=build_groups(exp,private,order)
    out.mkdir(parents=True,exist_ok=False);os.chmod(out,0o700)
    write(out/'ONCE.json',dict(experiment=exp,capture_seal_sha256=capture_sha,config_sha256=sha(config_path),reader_outputs_opened=False))
    write(out/'SPEC.PRIVATE.json',dict(capture_seal_sha256=capture_sha,groups=groups))
    report=probes(capture,capture_sha,out/'SPEC.PRIVATE.json',out/'probes')
    if exp=='E85':
        # Descriptive word-only factor diagnostics; never a selection gate.
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.linear_model import LogisticRegression
        from cpu_gates import auc
        rows={x['public_id']:x for x in private};dev=[rows[i] for i in order if rows[i]['split']=='dev'];test=[rows[i] for i in order if rows[i]['split']=='test']
        vectorizer=CountVectorizer();xd=vectorizer.fit_transform([x['text'] for x in dev]);xt=vectorizer.transform([x['text'] for x in test]);bow={}
        for target in ('genre','addressed'):
            model=LogisticRegression(C=1.,max_iter=1000,random_state=20261028).fit(xd,[x[target] for x in dev])
            bow[target]=dict(test_auroc=auc([x[target] for x in test],model.decision_function(xt)),descriptive=True,gate=False)
        write(out/'BOW_DESCRIPTIVE.json',bow)
    probe_sha=sha(out/'probes/PROBE_SEAL.json')
    write(out/'PUBLIC_PROBE_RECEIPT.json',dict(experiment=exp,capture_seal_sha256=capture_sha,
        input_seal_sha256=cfg['input_seal_sha256'],probe_seal_sha256=probe_sha,released_ids=reader_ids,
        reader_outputs_opened=False,integrator_GO_still_required=True,
        acquisition_scope='all frozen test items; probe gates applied to scientific verdicts, no test outcome selection'))
    seal(out,'CPU_RECEIPT_SEAL.json',experiment=exp,capture_seal_sha256=capture_sha,reader_outputs_opened=False)
    return report

def main():
    p=argparse.ArgumentParser()
    for k in ('config','capture','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--capture-sha',required=True);a=p.parse_args();run(a.config,a.capture,a.capture_sha,a.out)

if __name__=='__main__':main()
