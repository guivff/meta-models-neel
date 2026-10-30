"""94a770cc(a,b): deterministic public wire rendering and lossless terminal adapter."""
import argparse
from pathlib import Path
from collections import Counter
from projects.g_agreement.readerbench.io import read, sha, verify, write
from projects.g_agreement.readerbench.scoring import require

# Frozen layout; fields are substituted verbatim, never reordered by correctness.
SUFFIX = '\n\nProperty: {property}\nA: {A}\nB: {B}\n'


def render_record(record, frozen_rubric):
    require(set(record) == {'id','property','values','readout'}, 'source packet schema')
    require(isinstance(record['property'],str) and isinstance(record['values'],dict) and
            set(record['values']) == {'A','B'} and
            all(isinstance(record['values'][k],str) or (isinstance(record['values'][k],list) and
                all(isinstance(v,str) for v in record['values'][k])) for k in ('A','B')), 'frozen property/value strings or lists')
    return dict(id=record['id'], readout=record['readout'], rubric=frozen_rubric +
                SUFFIX.format(property=record['property'],
                    A=' / '.join(record['values']['A']) if isinstance(record['values']['A'],list) else record['values']['A'],
                    B=' / '.join(record['values']['B']) if isinstance(record['values']['B'],list) else record['values']['B']))


def adapt_grid(terminal, packet, taxonomy="E56"):
    from .later_runner import classify
    ids=[x['id'] for x in packet];ts=[x['id'] for x in terminal]
    require(len(set(ids)) == len(ids) == len(ts) == len(set(ts)) and set(ids) == set(ts), 'exact terminal/packet grid')
    indexed={x['id']:x for x in terminal};result=[];audit=[]
    for item in packet:
        row=indexed[item['id']]
        require(type(row['attempts']) is int and 0 <= row['attempts'] <= 2, 'retry count')
        if row['status'] == 'UNPARSEABLE':
            require(row['code'] is None and row['attempts'] == 2, 'exhausted validation retries only')
            code=dict(id=item['id'], category='UNPARSEABLE', values=[], evidence='')
        else:
            require(row['status'] == 'KEPT' and row['code']['id'] == item['id'], 'kept identity')
            require(classify([item],dict(records=[row['code']]),taxonomy)[0]['status']=='KEPT', 'kept judgment validation')
            require(set(row['code']) == ({'id','eval_mention','evidence'} if taxonomy=='S6' else {'id','category','values','evidence'}), 'flat judgment fields')
            code=dict(row['code'])
        result.append(code)
        audit.append(dict(id=item['id'],status=row['status'],attempts=row['attempts']))
    return result,audit


def validate_flat(code, text):
    """Consumer helper: terminal sentinel is missing, never silent or wrong."""
    from .later_runner import classify
    require(set(code) == {'id','category','values','evidence'}, 'flat judgment schema')
    if code['category'] == 'UNPARSEABLE':
        require(code['values'] == [] and code['evidence'] == '', 'missing-code sentinel')
    else:
        require(classify([dict(id=code['id'],readout=text)],dict(records=[code]))[0]['status']=='KEPT', 'normalized evidence/category')


def score_values(codes, truths):
    """S inputs after the private row join. Missing entries are excluded, not zero."""
    require(len(codes)==len(truths), 'paired truth grid')
    scores=[]
    for c,truth in zip(codes,truths):
        require(truth in ('A','B'), 'binary truth')
        if c['category']=='UNPARSEABLE':continue
        require(c['category'] in ('states_value','names_property_without_value','exhibits','silent'), 'frozen categories')
        values=c['values']
        require(values in ([],['A'],['B'],['A','B'],['B','A']), 'value list')
        require(bool(values)==(c['category']=='states_value'), 'category/value consistency')
        scores.append(0 if len(values)!=1 else 1 if truth in values else -1)
    return scores


def summarize_row(codes, truths):
    """Call separately per joined row and pooled. Keep item IDs with retained scores for CIs."""
    scores=score_values(codes,truths);n=len(codes);u=n-len(scores)
    return dict(n_readouts=n,kept=len(scores),unparseable=u,flagged_over_5_percent=20*u>n,
                S=sum(scores)/len(scores) if scores else None,
                counts=dict(Counter(c['category'] for c in codes)))


def adapt_files(blind, blind_sha, terminal, terminal_sha, out, eval_terminal=None, eval_sha=None, converted=None, converted_sha=None):
    from .later_runner import HERE
    sources=read(HERE/'RUNNER_SOURCE_SEAL.json')
    for name,digest in sources['files'].items():require(sha(name)==digest,'adapter source changed')
    bs=verify(blind/'BLIND_SEAL.json',blind_sha)
    require(bs['experiment'] in ('E57','E56','E62','E59','E68'),'supported value adapter bank')
    require('JUDGE_PACKET.json' in bs['files'],'unsealed source packet')
    if (blind/'EVAL_PACKET.json').exists():require('EVAL_PACKET.json' in bs['files'],'unsealed eval inventory')
    ts=verify(terminal/'RESULT_SEAL.json',terminal_sha)
    require('JUDGMENTS.json' in ts['files'],'unsealed terminal grid')
    expected_packet_sha=blind_sha
    if converted is not None:
        require(bs['experiment']=='E68' and converted_sha,'converted packet only for E68')
        cs=verify(converted/'PACKET_SEAL.json',converted_sha)
        require(cs['experiment']=='E68' and cs['source_seal_sha256']==blind_sha and
                cs['source_packet_sha256']==bs['files']['JUDGE_PACKET.json'] and
                'PACKET.json' in cs['files'],'converted/original custody')
        require(read(converted/'PACKET.json')==read(blind/'JUDGE_PACKET.json'),'converted records unchanged')
        expected_packet_sha=converted_sha
    require(ts['bank']==bs['experiment'] and ts.get('channel','value')=='value' and
            ts['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS' and ts['packet_seal_sha256']==expected_packet_sha,
            'terminal/original blind custody')
    eval_packet=read(blind/'EVAL_PACKET.json') if (blind/'EVAL_PACKET.json').exists() else []
    require(bool(eval_packet)==bool(eval_terminal), 'complete value/eval channel grid required')
    packet=read(blind/'JUDGE_PACKET.json')
    redaction_files={'JUDGE_COPY.json','PATH_REDACTION_AUDIT.json'}
    has_redaction=bool(redaction_files & set(ts['files']))
    if has_redaction:
        from .privacy79 import redact
        require(redaction_files <= set(ts['files']),'complete sealed redaction custody')
        saved_audit=read(terminal/'PATH_REDACTION_AUDIT.json')
        expected,ra=redact(packet,bs['experiment'],addresses=saved_audit.get('address_authority')=='25c32f25')
        copied=read(terminal/'JUDGE_COPY.json')
        require(read(terminal/'PATH_REDACTION_AUDIT.json')==ra,'redaction audit differs from originals')
        require([(x['id'],x['readout']) for x in copied]==[(x['id'],x['readout']) for x in expected],
                'judge copy differs from authorized path-only redaction')
        packet=copied
    codes,audit=adapt_grid(read(terminal/'JUDGMENTS.json'),packet)
    if eval_packet:
        es=verify(eval_terminal/'RESULT_SEAL.json',eval_sha)
        require(bs['experiment']=='E62' and es['bank']=='E62' and es['channel']=='eval' and
                es['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS' and es['packet_seal_sha256']==blind_sha and
                'JUDGMENTS.json' in es['files'], 'eval terminal custody')
        ec,ea=adapt_grid(read(eval_terminal/'JUDGMENTS.json'),eval_packet,'S6')
        codes+=ec;audit+=ea
        require(len({x['id'] for x in codes})==len(codes), 'channel ID collision')
    out.mkdir(parents=True,exist_ok=False)
    write(out/'JUDGMENTS.json',codes);write(out/'ATTEMPTS.json',audit)
    if has_redaction:
        for name in redaction_files:(out/name).write_bytes((terminal/name).read_bytes())
    write(out/'JUDGMENT_SEAL.json',dict(blind_seal_sha256=blind_sha,terminal_seal_sha256=terminal_sha,
        adapter_source_seal_sha256=sha(HERE/'RUNNER_SOURCE_SEAL.json'),authority='94a770cc',eval_terminal_seal_sha256=eval_sha,
        converted_packet_seal_sha256=converted_sha,
        unparseable_policy='exclude from S denominator; retain and count per row and pooled',
        files={p.name:sha(p) for p in out.iterdir()}))


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    wire=sub.add_parser('wire');wire.add_argument('--spec',type=Path,required=True);wire.add_argument('--out',type=Path,required=True)
    adapter=sub.add_parser('adapt')
    for name in ('blind','terminal','out'):adapter.add_argument('--'+name,type=Path,required=True)
    for name in ('blind-sha','terminal-sha'):adapter.add_argument('--'+name,required=True)
    adapter.add_argument('--eval-terminal',type=Path);adapter.add_argument('--eval-sha')
    adapter.add_argument('--converted',type=Path);adapter.add_argument('--converted-sha')
    a=p.parse_args()
    if a.mode=='adapt':adapt_files(a.blind,a.blind_sha,a.terminal,a.terminal_sha,a.out,a.eval_terminal,a.eval_sha,a.converted,a.converted_sha)
    else:
        from .later_runner import admission,HERE
        for name,digest in read(HERE/'RUNNER_SOURCE_SEAL.json')['files'].items():require(sha(name)==digest,'wire source changed')
        spec=read(a.spec);items,_=admission(spec)
        require(spec['bank'] in ('E57','E56','E62','E59','E68'),'supported value wire export')
        a.out.mkdir(parents=True,exist_ok=False);write(a.out/'WIRE_PACKET.json',items)
        write(a.out/'WIRE_SEAL.json',dict(blind_seal_sha256=spec['packet_seal_sha256'],
            source_seal_sha256=sha(HERE/'RUNNER_SOURCE_SEAL.json'),files={'WIRE_PACKET.json':sha(a.out/'WIRE_PACKET.json')}))


if __name__=='__main__':main()
