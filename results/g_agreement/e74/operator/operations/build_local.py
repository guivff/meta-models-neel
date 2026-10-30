"""Prepare and build the locked operations layer locally, without network in build."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

BASE = 'sha256:447fe0821f2ca4fb22daa5a06ade52edad3c710d22d2ef1e6852b69afeeb65e0'
ALIAS = 'codex/e74-science-447fe082:locked'


def main():
    p=argparse.ArgumentParser();p.add_argument('--debs',type=Path,required=True)
    p.add_argument('--context',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--tag',default='codex/e74-author-ops:20261027');a=p.parse_args()
    src=Path(__file__).resolve().parent
    lock=json.loads((src/'OS_LOCK.json').read_text())
    parent=json.loads(subprocess.check_output(['docker','image','inspect',BASE]))[0]
    assert parent['Id']==BASE and parent['Architecture']=='amd64' and parent['Os']=='linux'
    assert lock['base_runtime_image']==BASE
    for entry in lock['packages']:
        file=a.debs/entry['filename']
        assert file.stat().st_size==entry['bytes']
        assert hashlib.sha256(file.read_bytes()).hexdigest()==entry['sha256']
    a.context.mkdir(parents=True,exist_ok=False);(a.context/'debs').mkdir()
    for name in ['Dockerfile','OS_LOCK.json','SCIENTIFIC_FILES.json','start.py','sshd_config','verify_ops.py']:
        shutil.copyfile(src/name,a.context/name)
    for entry in lock['packages']:
        shutil.copyfile(a.debs/entry['filename'],a.context/'debs'/entry['filename'])
    subprocess.run(['docker','tag',BASE,ALIAS],check=True)
    subprocess.run(['docker','build','--platform','linux/amd64','--network','none','--pull=false',
                    '--tag',a.tag,'--metadata-file',str(a.metadata),str(a.context)],check=True)
    child=json.loads(subprocess.check_output(['docker','image','inspect',a.tag]))[0]
    assert child['RootFS']['Layers'][:len(parent['RootFS']['Layers'])]==parent['RootFS']['Layers']
    print(json.dumps({'status':'BUILT_CPU_ONLY','image_id':child['Id'],'bytes':child['Size'],
                      'exact_parent_layers_preserved':True,'registry_push':False}))


if __name__=='__main__':main()
