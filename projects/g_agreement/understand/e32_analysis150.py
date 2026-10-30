"""§149/§150 guarded unchanged E32 analysis, binding both capture and score pulls."""
import argparse,json,os
from pathlib import Path
from projects.g_agreement.blindspot import protocol as P
from . import e32_split150 as S,e32_analysis as A


def run(specpath,digest):
    if P.sha(specpath)!=digest:raise ValueError('analysis spec hash')
    spec=json.loads(specpath.read_text());lock=Path(spec['lock']);lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as f:json.dump({'authority':'§149 RUN-BY-INTEGRATOR; §150','spec_sha256':digest},f)
    try:
        for n,h in spec['pins'].items():
            if P.sha(n)!=h:raise ValueError('analysis pin: '+n)
        final=Path(spec['scoring_pull']);source=final/'out';capture=Path(spec['capture']);plan=Path(spec['plan']);bank=Path(spec['bank']);p=S.E.read(plan)
        if not final.is_symlink():raise ValueError('scoring delivery must link original verified pull')
        for line in (final/'PULL_SUMS').read_text().splitlines():
            h,n=line.split(None,1);file=(final/n.lstrip('*')).resolve()
            if not file.is_relative_to(final.resolve()) or P.sha(file)!=h:raise ValueError('scoring pull checksum')
        S.verify_capture(capture,bank,p)
        P.verify(source,'SCORE_SEAL.json');P.verify(source,'SCORE_PARITY_SEAL.json')
        if S.E.read(source/'SCORE_SEAL.json')['status']!='COMPLETE_GATES_RECORDED' or S.E.read(source/'SCORE_PARITY_SEAL.json')['status']!='PASS':raise ValueError('score/gate status')
        q=S.E.read(source/'STAGE_BINDING.json')
        if q['capture_seal_sha256']!=P.sha(capture/'CAPTURE_SEAL.json') or P.sha(source/'CAPTURE_SEAL.json')!=q['capture_seal_sha256'] or q['capture_assignment_sha256']!=p['capture_assignment_sha256'] or q['scoring_environment']!='/weights/venv-kernels' or q['score_parity_seal_sha256']!=P.sha(source/'SCORE_PARITY_SEAL.json'):raise ValueError('two-stage binding')
        binding=S.E.read(source/'BINDING.json');assignment=final/'ASSIGNMENT.json'
        if binding['assignment_sha256']!=P.sha(assignment) or S.E.read(assignment)['plan_sha256']!=P.sha(plan):raise ValueError('score assignment binding')
        if (source/'INCOMPLETE.json').exists() or Path(spec['out']).exists():raise ValueError('incomplete or existing output')
        os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1')
        A.analyse(bank,plan,source,Path(spec['out']));P.verify(Path(spec['out']),'ANALYSIS_SEAL.json')
        P.dump(lock.with_suffix('.receipt.json'),{'status':'COMPLETE','label':'§149 RUN-BY-INTEGRATOR','retry':False})
    except BaseException as exc:
        P.dump(lock.with_suffix('.receipt.json'),{'status':'STOP_OWNER_REQUIRED','error':str(exc),'retry':False});raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--spec-sha256',required=True);a=p.parse_args();run(a.spec,a.spec_sha256)
