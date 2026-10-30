"""Build exactly 3 new E80c ablation conditions at two sites; no reader calls."""
import time
from pathlib import Path
import numpy as np
from projects.g_agreement.readerbench.io import read,sha,write
from projects.g_agreement.readerbench.scoring import require

ROOT=Path(__file__).resolve().parents[4]
HERE=ROOT/'results/g_agreement/understand/e80c'
OUTPUT=ROOT/'cache/g_agreement/understand/e80c/inputs_v1'
CAPTURE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wlens/cache/g_agreement/understand/e80/capture_delivery')
J=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wsae/cache/g_agreement/understand/e58b/pod_inputs_v2/J384.npy')
CAPSHA='25d02e881f2c5ceb99959a6d6c8a0a640bf1daed4e1ba71491dd0f4b34e09a32'
JSHA='a8f4b64c010aa2f3a72aac70e087ce5204d463c2bb93d1ebf3b22b21a0bdb4fb'
SEED=20261028
RANK=384


def canonical(q):
    # Projector invariant under signs; fix signs to make the saved basis reproducible.
    q=np.array(q,dtype=np.float64,copy=True)
    for k in range(q.shape[1]):
        if q[np.argmax(abs(q[:,k])),k]<0:q[:,k]*=-1
    return q


def bases(h44,j,rank=RANK,seed=SEED):
    x=h44.astype(np.float64)-h44.astype(np.float64).mean(axis=0)
    require(np.isfinite(x).all() and x.ndim==2 and x.shape[0]>rank and x.shape[1]>=rank,
            'enough finite centred activations')
    gram=x@x.T
    vals,vecs=np.linalg.eigh(gram)
    order=np.argsort(-vals,kind='stable')[:rank]
    require(vals[order[-1]]>1e-9,'PCA rank full')
    p=canonical(np.linalg.qr(x.T@vecs[:,order]/np.sqrt(vals[order])[None,:],mode='reduced')[0])
    random=canonical(np.linalg.qr(np.random.default_rng(seed).standard_normal((x.shape[1],rank)),
                                     mode='reduced')[0])
    require(j.shape==(x.shape[1],rank) and
            np.max(np.abs(j.T@j-np.eye(rank)))<1e-4,'sealed J basis orthonormal')
    return {'J':j.astype(np.float64),'random':random,'PCA':p},np.sqrt(vals[order])


def transform(h,mu,q):
    x=h.astype(np.float64)
    delta=x-mu
    projected=(delta@q)@q.T
    return x-projected,projected


def run():
    start=time.monotonic()
    frozen=read(HERE/'INPUTS.json')
    require(frozen['status']=='FROZEN_BEFORE_ABLATION' and frozen['n_items']==518 and
            frozen['rank']==384 and frozen['seed']==SEED and
            frozen['reader_outcomes_opened'] is False and
            all(sha(path)==digest for path,digest in frozen['files'].items()),
            'frozen code, capture, basis and plan bytes')
    require(sha(CAPTURE/'CAPTURE_SEAL.json')==CAPSHA and sha(J)==JSHA,'pinned capture and J hash')
    seal=read(CAPTURE/'CAPTURE_SEAL.json')
    require(seal['experiment']=='E80' and seal['reader_outputs']==0 and set(seal['layers'])=={42,44} and
            all(sha(CAPTURE/name)==value for name,value in seal['files'].items()),
            'complete verified original E80 capture')
    binding=read('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wlens/results/g_agreement/understand/e80/jlens/CAPTURE_BINDING.json')
    require(binding['status']=='REAL_CAPTURE_VERIFIED_NO_SCORING' and
            binding['files'][str(CAPTURE/'CAPTURE_SEAL.json')]==CAPSHA,
            'integrator-verified delivery receipt')
    ids=read(CAPTURE/'items.order.json')
    require(len(ids)==518 and len(set(ids))==518,'518 frozen capture-order items')
    OUTPUT.mkdir(parents=True,exist_ok=False) # once-only claim before the first projection
    h={block:np.load(CAPTURE/f'acts{block}.npy',allow_pickle=False) for block in (44,42)}
    require(all(x.shape==(518,5120) and x.dtype==np.float32 and np.isfinite(x).all() for x in h.values()),
            'exact finite activation matrices')
    q,sv=bases(h[44],np.load(J,allow_pickle=False))
    mu={block:h[block].astype(np.float64).mean(axis=0) for block in h}
    outputs=[];metadata=[];stats={};fractions={}
    for block in (44,42):
        site='Oracle' if block==44 else 'NLA_exploratory_block44_basis'
        centred=h[block].astype(np.float64)-mu[block]
        denom=np.sum(centred*centred,axis=1)
        require(np.all(denom>1e-12),'nonzero centred norm')
        fractions[str(block)]=(np.sum((centred@q['J'])**2,axis=1)/denom).tolist()
        for condition in ('J','random','PCA'):
            ablated,proj=transform(h[block],mu[block],q[condition])
            require(np.isfinite(ablated).all(),'finite ablated vectors')
            ratio=np.linalg.norm(ablated,axis=1)/np.linalg.norm(h[block].astype(np.float64),axis=1)
            require(np.isfinite(ratio).all(),'finite norm ratios')
            stats[f'{site}:{condition}']=dict(n=518,mean=float(ratio.mean()),minimum=float(ratio.min()),
                maximum=float(ratio.max()),above_1_5=int(sum(ratio>1.5)),per_item=ratio.tolist())
            outputs.append(ablated.astype(np.float32))
            # Sequential vector index; keep only capture-order ID and public site/condition.
            offset=len(metadata)
            metadata.extend(dict(id=ident,block=block,reader_site=site,condition=condition,
                                 index=offset+i) for i,ident in enumerate(ids))
    vectors=np.concatenate(outputs,axis=0)
    require(vectors.shape==(3108,5120) and len(metadata)==3108 and
            [r['index'] for r in metadata]==list(range(3108)),'four-condition stage grid')
    pod=OUTPUT/'pod_inputs';pod.mkdir()
    np.save(pod/'INPUT_VECTORS.npy',vectors)
    write(pod/'ITEMS.json',metadata)
    for name,key in (('J384.npy','J'),('R384.npy','random'),('PCA384.npy','PCA')):
        np.save(pod/name,q[key].astype(np.float32))
    write(pod/'RESULT_SEAL.json',dict(experiment='E80c',status='SEALED_ABLATION_INPUTS',
        n_items=518,n_vectors=3108,source_capture_sha256=CAPSHA,j_basis_sha256=JSHA,
        conditions=['J','random','PCA'],none_existing_e80_readouts=True,
        exploratory_block42_uses_block44_basis=True,
        files={p.name:sha(p) for p in pod.iterdir() if p.name!='RESULT_SEAL.json'}))
    write(HERE/'NORM_RATIOS.json',dict(seed=SEED,j_fraction_by_block=fractions,per_cell=stats,
        pca_top_five_singular_values=sv[:5].tolist(),
        pca_block44_only=True,mean_norm_per_block={str(b):float(np.linalg.norm(mu[b])) for b in mu}))
    write(HERE/'BUILD_RECEIPT.json',dict(status='READY',source_capture_sha256=CAPSHA,
         pod_seal_sha256=sha(pod/'RESULT_SEAL.json'),vectors_sha256=sha(pod/'INPUT_VECTORS.npy'),
         n_items=518,n_vectors=3108,conditions=['none_existing','J','random','PCA'],
         seed=SEED,reader_calls=0,gpu_hours=0,wall_seconds=time.monotonic()-start))
    write(HERE/'RESULT_SEAL.json',dict(status='CPU_SEALED_READY',files={p.name:sha(p)
          for p in HERE.iterdir() if p.is_file() and p.name!='RESULT_SEAL.json'},
          pod_seal_sha256=sha(pod/'RESULT_SEAL.json')))


if __name__=='__main__':run()
