"""CPU-only gate helpers. No private key or truth is accepted by the pod worker."""
import argparse
import os
import sys
from pathlib import Path
import numpy as np
from contract import *

def behaviour_decisions(experiment, predictions, groups):
    """Classify frozen candidate groups; E82 matching remains an owner-sealed manifest."""
    decisions=[]
    for g in groups:
        ids=g['paraphrase_score_ids']
        require(len(ids)==3 and len(set(ids))==3,'three distinct frozen paraphrases')
        answers=[predictions[i]['token_id'] for i in ids]
        truth=g['truth_token_id']
        stable=len(set(answers))==1
        if experiment=='E86':
            baseline=all(a==truth for a in answers)
            arms={arm: baseline and (predictions[k]['token_id']==truth if arm=='honest'
                                    else predictions[k]['token_id']!=truth)
                  for arm,k in g['arm_score_ids'].items()}
            require(set(arms)=={'honest','lie','role'},'three arm scores')
            decisions.append(dict(id=g['id'],baseline_pass=baseline,arms=arms,
                arm_answers={arm:predictions[k]['token_id'] for arm,k in g['arm_score_ids'].items()}))
        elif experiment=='E82':
            decisions.append(dict(id=g['id'],stable=stable,belief_token_id=answers[0] if stable else None,
                                  belief_wrong=stable and answers[0]!=truth,belief_right=stable and answers[0]==truth))
        else:raise ValueError('no behaviour filtering for this experiment')
    return decisions

def auc(labels, scores):
    y=np.asarray(labels);s=np.asarray(scores)
    a=s[y==1];b=s[y==0]
    require(len(a) and len(b) and np.isfinite(s).all(),'binary evaluable probe')
    return float(((a[:,None]>b[None,:])+.5*(a[:,None]==b[None,:])).mean())

def fit_three_way(xdev,ydev,xtest):
    """Fixed multinomial analogue; normalization and optimization use dev only."""
    import torch
    xd=torch.as_tensor(xdev,dtype=torch.float32);xt=torch.as_tensor(xtest,dtype=torch.float32)
    y=torch.as_tensor(ydev,dtype=torch.long)
    require(set(y.tolist())=={0,1,2},'all three dev source classes')
    mu=xd.mean(0);sd=xd.std(0).clamp_min(1e-4);z=(xd-mu)/sd
    w=torch.zeros((xd.shape[1],3),requires_grad=True);b=torch.zeros(3,requires_grad=True)
    opt=torch.optim.LBFGS([w,b],lr=1,max_iter=200,history_size=20,line_search_fn='strong_wolfe')
    def closure():
        opt.zero_grad();loss=torch.nn.functional.cross_entropy(z@w+b,y)+.001*(w*w).sum();loss.backward();return loss
    opt.step(closure)
    with torch.no_grad():ds=z@w+b;ts=((xt-mu)/sd)@w+b
    return dict(w=w.detach().numpy(),b=b.detach().numpy(),mu=mu.numpy(),sd=sd.numpy(),
                dev_scores=ds.numpy(),test_scores=ts.numpy())

def probes(capture, capture_sha, private_spec, out):
    """Fixed dev-only logistic recipe; no cross-validation or reader outcome access."""
    import torch
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.probes import fit_logreg
    verify(capture,'STAGE_SEAL.json',capture_sha)
    spec=read(private_spec)
    require(spec['capture_seal_sha256']==capture_sha,'CPU probe spec binds capture')
    order=read(capture/'items.order.json');index={key:i for i,key in enumerate(order)}
    out.mkdir(parents=True,exist_ok=False);os.chmod(out,0o700)
    reports=[]
    for n,g in enumerate(spec['groups']):
        require(set(g['dev_ids']).isdisjoint(g['test_ids']),'disjoint dev/test items')
        require(set(g['dev_cluster_ids']).isdisjoint(g['test_cluster_ids']),'disjoint dev/test clusters')
        require(g['layer'] in (42,44),'registered reader sites')
        h=np.load(capture/f"acts{g['layer']}.npy",allow_pickle=False)
        ydev=np.array(g['dev_labels']);ytest=np.array(g['test_labels'])
        require(len(ydev)==len(g['dev_ids'])==len(g['dev_cluster_ids']) and
                len(ytest)==len(g['test_ids'])==len(g['test_cluster_ids']),'private label grid')
        record=dict(name=g['name'],layer=g['layer'],status='NOT EVALUABLE')
        if set(ydev)=={0,1,2} and set(ytest)<=set(ydev):
            fit=fit_three_way(h[[index[x] for x in g['dev_ids']]],ydev,h[[index[x] for x in g['test_ids']]])
            dp=fit['dev_scores'].argmax(1);tp=fit['test_scores'].argmax(1)
            matrix=np.zeros((3,3),dtype=int)
            for truth,prediction in zip(ytest,tp):matrix[truth,prediction]+=1
            record.update(status='COMPLETE',dev_accuracy=float(np.mean(dp==ydev)),test_accuracy=float(np.mean(tp==ytest)),
                          confusion_matrix=matrix.tolist(),class_order=['user','tool','assistant'],descriptive=True)
            np.savez(out/f'probe_{n:03d}.npz',**fit)
        elif set(ydev)=={0,1} and set(ytest)=={0,1}:
            xd=torch.tensor(h[[index[x] for x in g['dev_ids']]].astype(np.float32))
            xt=torch.tensor(h[[index[x] for x in g['test_ids']]].astype(np.float32))
            model=fit_logreg(xd,torch.tensor(ydev),lam=1e-3,iters=200)
            ds=model.decision(xd).numpy();ts=model.decision(xt).numpy()
            record.update(status='COMPLETE',dev_auroc=auc(ydev,ds),test_auroc=auc(ytest,ts))
            record['probe_pass']=record['dev_auroc']>=.90 and record['test_auroc']>=.90
            np.savez(out/f'probe_{n:03d}.npz',w=model.w.numpy(),b=model.b,mu=model.mu.numpy(),sd=model.sd.numpy(),
                     dev_scores=ds,test_scores=ts)
        reports.append(record)
    write(out/'PROBES.json',reports)
    seal(out,'PROBE_SEAL.json',capture_seal_sha256=capture_sha,private_spec_sha256=sha(private_spec),
         recipe='existing mats.probes.fit_logreg lam=.001 iters=200; dev-only normalization and fit',reader_outputs_opened=False)
    return reports

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    p1=sub.add_parser('probes')
    for k in ('capture','private-spec','out'):p1.add_argument('--'+k,type=Path,required=True)
    p1.add_argument('--capture-sha',required=True)
    p2=sub.add_parser('classify')
    for k in ('behaviour','private-key','out'):p2.add_argument('--'+k,type=Path,required=True)
    p2.add_argument('--behaviour-sha',required=True)
    a=p.parse_args()
    if a.command=='probes':probes(a.capture,a.capture_sha,a.private_spec,a.out)
    else:
        s=verify(a.behaviour,'STAGE_SEAL.json',a.behaviour_sha);key=read(a.private_key)
        require(key['experiment']==s['experiment'] and key['input_seal_sha256']==s['input_seal_sha256'],'private gate key binding')
        rows=[x for f in sorted(a.behaviour.glob('[0-9]*.json')) for x in read(f)]
        require(len({x['id'] for x in rows})==len(rows),'unique scored items')
        decisions=behaviour_decisions(s['experiment'],{x['id']:x for x in rows},key['groups'])
        a.out.mkdir(parents=True,exist_ok=False);os.chmod(a.out,0o700)
        write(a.out/'DECISIONS.PRIVATE.json',decisions)
        seal(a.out,'CPU_GATE_SEAL.json',behaviour_seal_sha256=a.behaviour_sha,private_key_sha256=sha(a.private_key),
             status='CLASSIFIED_OWNER_SELECTION_REQUIRED',reader_outputs_opened=False)

if __name__=='__main__':main()
