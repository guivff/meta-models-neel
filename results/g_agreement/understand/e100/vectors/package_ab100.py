"""Label-free E100 a/b data archives; basis archives staged separately, no CPU keys."""
import argparse
import shutil
import tarfile
from pathlib import Path
from build100 import read,write,sha


def package(root,out):
    s=read(root/'VECTOR_SEAL.json')
    assert s['status']=='AB_SEALED_BEFORE_GPU_CD_WITHDRAWN'
    for n,h in s['files'].items():assert sha(root/n)==h
    public=root/'public';manifest=read(public/'MANIFEST.json');out.mkdir(parents=True,exist_ok=False)
    archives=[]
    for name in ['Q_J.npy','Q_R.npy']:
        arc=out/(name+'.tar.gz')
        with tarfile.open(arc,'w:gz') as t:t.add(public/name,arcname='inputs/'+name)
        archives.append(dict(kind='basis',archive=str(arc.resolve()),archive_sha256=sha(arc),bytes=arc.stat().st_size))
    for group in ['reported','missed']:
        inp=out/group/'inputs';inp.mkdir(parents=True);rows=[r for r in manifest['rows'] if r['group']==group]
        files={n:sha(public/n) for n in ['Q_J.npy','Q_R.npy']}
        for row in rows:
            for n in [row['h44'],row['h42'],row['pairings']]:
                target=inp/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(public/n,target);files[n]=sha(target)
        W=dict(manifest,rows=rows,oracle_readouts=len(rows)*84*5,nla_readouts=len(rows)*84*5,total_readouts=len(rows)*84*10,
            per_row_readouts={r['row']:840 for r in rows})
        write(inp/'MANIFEST.json',W);files['MANIFEST.json']=sha(inp/'MANIFEST.json')
        write(inp/'INPUT_SEAL.json',dict(experiment='E100',parts=['a','b'],labels_on_pod=False,files=files,
            parent_public_input_seal_sha256=sha(public/'INPUT_SEAL.json'),basis_archives_required=True))
        arc=out/(group+'.tar.gz')
        with tarfile.open(arc,'w:gz') as t:t.add(inp,arcname='inputs')
        archives.append(dict(kind=group,archive=str(arc.resolve()),archive_sha256=sha(arc),input_seal_sha256=sha(inp/'INPUT_SEAL.json'),
            bytes=arc.stat().st_size,rows=len(rows),items=len(rows)*84,readouts=W['total_readouts']))
    assert all(x['bytes']<=20*1024*1024 for x in archives),'each archive within20MiB'
    receipt=dict(status='SEALED_CPU_DATA_REQUIRES_RUNNER_AND_INTEGRATOR_ADMISSION',authority=['f425a5e2','fd07c12a','69f8c08e4'],
        vector_seal_sha256=sha(root/'VECTOR_SEAL.json'),public_input_seal_sha256=sha(public/'INPUT_SEAL.json'),archives=archives,
        stage='extract both basis archives and exactly one group archive into the same fresh root; verify inputs/INPUT_SEAL.json before use',
        labels_on_pod=False,GPU_calls=0,full_launch_allowed=False)
    write(out/'HANDOFF.json',receipt);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();package(a.root,a.out)
