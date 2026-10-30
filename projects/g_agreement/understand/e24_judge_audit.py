"""Join independently frozen blinded judge codes; never tune the C4 regex."""
import argparse
from pathlib import Path
from projects.g_agreement.blindspot import protocol as P
from .e24_worker import read, seal


def audit(analysis,codes,out):
    P.verify(analysis,'ANALYSIS_SEAL.json');P.verify(codes,'JUDGE_SEAL.json')
    binding=read(codes/'JUDGE_SEAL.json')
    prompt=P.ROOT/'results/g_agreement/understand/e24/JUDGE_PROMPT.txt'
    if binding.get('packet_sha256')!=P.sha(analysis/'JUDGE_PACKET.jsonl') or binding.get('prompt_sha256')!=P.sha(prompt):
        raise ValueError('judge codes must be frozen and bound to exact packet and prompt before joining')
    rows=P.rows(codes/'codes.jsonl');byid={r['id']:r for r in rows}
    key=P.rows(analysis/'JUDGE_KEY.DO_NOT_SEND.jsonl')
    if len(byid)!=len(rows) or set(byid)!={x['id'] for x in key}:raise ValueError('exact complete blinded code population required')
    if any(r['statement'] not in ('A','B','both','neither') or not isinstance(r.get('evidence'),str) for r in rows):raise ValueError('invalid judge code')
    out.mkdir(parents=True,exist_ok=False);report={}
    for x in key:
        layer=str(x['layer']);report.setdefault(layer,{'n':0,'agreements':0,'disagreements':[]})
        rr=report[layer];rr['n']+=1;agree=byid[x['id']]['statement']==x['regex'];rr['agreements']+=agree
        if not agree:rr['disagreements'].append({**x,'judge':byid[x['id']]})
    if any(r['n']!=20 for r in report.values()):raise ValueError('twenty checks per layer required')
    P.dump(out/'AUDIT.json',{'layers':report,'status':'ALL_DISAGREEMENTS_RETAINED_NO_REGEX_REVISION',
        'judge_seal_sha256':P.sha(codes/'JUDGE_SEAL.json'),'analysis_seal_sha256':P.sha(analysis/'ANALYSIS_SEAL.json')})
    seal(out,['AUDIT.json'],'AUDIT_SEAL.json','C4_BLINDED_AUDIT_COMPLETE')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('analysis','codes','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();audit(a.analysis,a.codes,a.out)
