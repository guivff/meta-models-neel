"""Publish sealed blinded response/code bytes; private joins/request bodies stay CPU."""
import argparse
import hashlib
import re
import shutil
import tarfile
from pathlib import Path
from decimal import Decimal
from .transport import ROOT,SHARED
from .runner import CACHE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def publish(bank,phase,label):
    require(re.fullmatch(r'E\d+[a-z]?',bank) and re.fullmatch(r'[a-zA-Z0-9_]+',phase) and
        re.fullmatch(r'[a-zA-Z0-9_]+',label),'fixed artifact path components')
    src=CACHE/bank/phase/'outputs';parent=src/('GENERATION_SEAL.json' if phase=='generation' else 'JUDGMENT_SEAL.json');seal=verify(parent,sha(parent))
    require(seal['status']=='COMPLETE' and seal['experiment']==bank and seal['route_verified'] is True,'complete route-verified phase')
    dest=CACHE/bank/(phase+'_public');dest.mkdir(exist_ok=True)
    allowed={'RESPONSES.json','JUDGMENTS.json','ATTEMPTS.json','ROUTE_AUDIT.json','COUNTS.json','OPERATIONS_EXECUTION.json','SECTION226_OPERATIONS_EXECUTION.json','PATH_REDACTION_AUDIT.json'}
    for name in allowed & set(seal['files']):shutil.copyfile(src/name,dest/name)
    shutil.copyfile(parent,dest/'ORIGINAL_PHASE_SEAL.json')
    bindings=read(src/'RAW_RESPONSE_BINDINGS.json');raw=dest/'raw_responses';raw.mkdir(exist_ok=True)
    wire_hashes=[]
    for ref in bindings:
        path=Path(ref['path']);require(sha(path)==ref['sha256'],'exact original physical response')
        shutil.copyfile(path,raw/path.name)
        req=path.with_name(path.name.replace('.response.json','.request.json'))
        require(req.exists(),'original wire retained CPU')
        wire_hashes.append(dict(request_id=path.name.removesuffix('.response.json'),request_sha256=sha(req),response_sha256=sha(path)))
    write(dest/'REQUEST_RESPONSE_HASHES.json',wire_hashes)
    write(dest/'PUBLIC_PHASE_SEAL.json',dict(experiment=bank,phase=phase,status='COMPLETE',original_phase_seal_sha256=sha(parent),
        route_verified=True,private_joins_published=False,request_bodies_published=False,
        files={str(p.relative_to(dest)):sha(p)for p in dest.rglob('*')if p.is_file()and p.name!='PUBLIC_PHASE_SEAL.json'}))
    verify(dest/'PUBLIC_PHASE_SEAL.json',sha(dest/'PUBLIC_PHASE_SEAL.json'))
    out=ROOT/'results/g_agreement/sealed_raw/trackQ'/label;out.mkdir(parents=True,exist_ok=True);archive=out/('GENERATION.tar.gz' if phase=='generation' else 'JUDGMENTS.tar.gz')
    with tarfile.open(archive,'w:gz')as tar:
        for p in sorted(dest.rglob('*')):
            if p.is_file():
                info=tar.gettarinfo(str(p),arcname=str(p.relative_to(dest)));info.uid=info.gid=0;info.uname=info.gname=''
                with p.open('rb')as f:tar.addfile(info,f)
    with tarfile.open(archive,'r:gz')as tar:
        for member in tar.getmembers():
            require(member.isfile() and (dest/member.name).is_file(),'exact known archive members')
            require(hashlib.sha256(tar.extractfile(member).read()).hexdigest()==sha(dest/member.name),'reopened member hash')
    cost=read(src/'COUNTS.json')['cost']
    receipt=dict(bank=bank,phase=phase,status='COMPLETE',original_phase_seal_sha256=sha(parent),original_phase_seal=str(parent),
        public_phase_seal_sha256=sha(dest/'PUBLIC_PHASE_SEAL.json'),archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
        cost=cost,remaining_lifetime_cap_usd=str(Decimal(cost['cap_usd'])-Decimal(cost['committed_usd'])),cap_released=False,
        first_output_utc=seal['first_output_utc'],private_joins_published=False,request_bodies_published=False,all_archive_members_verified=True,analysis_run=False)
    write(out/'RECEIPT.json',receipt)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bank',required=True);p.add_argument('--phase',required=True);p.add_argument('--label',required=True);a=p.parse_args()
    r=publish(a.bank,a.phase,a.label);print('Published phase archive '+r['archive_sha256'])
