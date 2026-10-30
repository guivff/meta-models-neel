"""CPU-only E117/c source units, literal original E56/E57 blind descriptors.

No model/API/GPU call, scoring, target computation, statistical analysis or cap
allocation. The same verified descriptor source serves both registered phases.
"""
import argparse
from collections import Counter
from pathlib import Path
from .transport import ROOT,HERE
from .runner import CACHE
from .banks import opaque
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

ROWS={'nesting_depth','indent_level','page_range_digit','fact_recall'}
RUBRIC_SHA='03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613'


def descriptor_rows(labels,packets,keys):
    """Copy original property/A/B strings by sealed unit ID; no aliases or gold."""
    require(len(labels)==len({x['id'] for x in labels})==336 and Counter(x['row'] for x in labels)=={r:84 for r in ROWS} and all(x['split']=='test' for x in labels),'exact four original TEST rows')
    out={}
    for label in labels:
        bank='E56' if label['row']=='fact_recall' else 'E57';require(label['bank']==bank,'original family lineage')
        packet={x['id']:(i,x) for i,x in enumerate(packets[bank])};matches=[]
        for ki,key in enumerate(keys[bank]):
            if key['unit_id']!=label['source_id'] or key.get('eval'):continue
            require(key['opaque_id'] in packet,'original private key/source packet identity')
            pi,p=packet[key['opaque_id']];require(set(p)=={'id','property','values','readout'},'original frozen value record, no S6 replacement')
            matches.append((ki,pi,p))
        require(bool(matches),'original descriptor actually present, no reconstructed candidates')
        original=matches[0][2]
        require(all(x[2]['property']==original['property'] and x[2]['values']==original['values'] for x in matches),'original reader/repetition descriptors agree')
        out[label['id']]=dict(source_id=label['id'],original_source_id=label['source_id'],row=label['row'],source_bank=bank,property=original['property'],values=original['values'],original_key_indices=[x[0] for x in matches],original_packet_indices=[x[1] for x in matches])
    return out


def make_units(part,records,descriptors,pointers=None):
    require(part in ('main','c') and len(descriptors)==336 and Counter(x['row'] for x in descriptors.values())=={r:84 for r in ROWS},'complete original descriptor scope')
    n=3024 if part=='main' else 672;require(len(records)==len({r['id'] for _,r in records})==n,'whole registered native census')
    ptr={p['id']:p for p in pointers or []}
    if part=='c':require(len(ptr)==336 and {x['source_id'] for x in ptr.values()}==set(descriptors),'original E117c-to-E113 explicit source map')
    seen=set();units=[];joins=[]
    for ref,r in records:
        ident=r['item_id'] if part=='main' else ptr[r['item_id']]['source_id'];require(ident in descriptors,'original source item, never join by order')
        d=descriptors[ident];require(r['row']==d['row'] and r['source_layer']==44 and type(r['text']) is str,'original source row/read-site/text retained')
        if part=='main':
            require(r['alpha'] in (1,2,4) and r['arm'] in ('T','W','R'),'registered full T/W/R x1/2/4')
            key=ident,r['alpha'],r['arm']
        else:
            require(r['reader']=='oracle' and r['condition'] in ('targeted','sham') and ptr[r['item_id']]['row']==d['row'],'registered targeted/sham Oracle source')
            key=ident,r['condition']
        require(key not in seen,'one exact source cell');seen.add(key)
        uid=opaque('E117',part,r['id']);units.append(dict(id=uid,kind='original57',rubric=None,data=dict(id=uid,property=d['property'],values=d['values'],readout=r['text'])))
        j=dict(id=uid,part=part,native_id=r['id'],item_id=ident,row=d['row'],native_item_id=r['item_id'],source_ref=ref,descriptor_ref_id=ident,source_bank=d['source_bank'])
        if part=='main':j.update(alpha=r['alpha'],arm=r['arm'])
        else:j.update(arm=r['condition'])
        joins.append(j)
    expected={(i,a,arm) for i in descriptors for a in (1,2,4) for arm in ('T','W','R')} if part=='main' else {(i,arm) for i in descriptors for arm in ('targeted','sham')}
    require(seen==expected,'all original source cells, no degenerate/missing subset selection')
    return sorted(units,key=lambda x:x['id']),sorted(joins,key=lambda x:x['id'])


def origin():
    labels=ROOT.parent/'outputs/e113-inputs-v1/cpu_only/LABEL_SEAL.json';verify(labels,'46364015d7e4c81a19ed29bec18e75e0aec98f5aa2fb72b3a8feaeea35d848bf')
    selected=[x for x in read(labels.parent/'LABELS.json') if x['row'] in ROWS and x['split']=='test'];packets={};keys={};sources=[];proof=[]
    for bank in ('E56','E57'):
        spec=ROOT.parent/'wt-wmech/results/g_agreement/understand'/bank.lower()/'job/ANALYSIS_SPEC.json';s=read(spec);b=Path(s['blind_out'])/'BLIND_SEAL.json';bs=verify(b,{'E56':'31c97158e53052f223ba17dffdfdd4ac473e1852bc110c287152de6bc7d18843','E57':'e548fda34f5982554e53d56c699ccdf6b63d63f7cd9974971799d369088cdbd1'}[bank]);require(bs['experiment']==bank and bs['rubric_sha256']==RUBRIC_SHA,'actual original shared rubric')
        kp=Path(s['private_key']);require(sha(kp)==bs['private_key_sha256'],'original CPU private identity key bytes')
        packets[bank]=read(b.parent/'JUDGE_PACKET.json');keys[bank]=read(kp);sources.append(dict(seal=str(b),sha256=sha(b)));proof.append(dict(bank=bank,blind_seal=str(b),blind_sha256=sha(b),key_path=str(kp),key_sha256=sha(kp),analysis_spec_sha256=sha(spec)))
    descriptors=descriptor_rows(selected,packets,keys)
    d=CACHE/'E117/original_descriptor_origin';d.mkdir(parents=True,exist_ok=True)
    if(d/'ORIGIN_SEAL.json').exists():verify(d/'ORIGIN_SEAL.json',sha(d/'ORIGIN_SEAL.json'));require(read(d/'DESCRIPTORS.PRIVATE.json')==descriptors,'immutable original source descriptors');return d
    write(d/'DESCRIPTORS.PRIVATE.json',descriptors);write(d/'ORIGINAL_IDENTITY_SOURCE_RECEIPT.PRIVATE.json',proof)
    write(d/'ORIGIN_SEAL.json',dict(experiment='E117',status='COMPLETE_LITERAL_ORIGINAL_DESCRIPTORS',n=336,labels_cpu_only=True,source_seals=sources+[dict(seal=str(labels),sha256=sha(labels))],rubric_sha256=RUBRIC_SHA,files={n:sha(d/n) for n in ['DESCRIPTORS.PRIVATE.json','ORIGINAL_IDENTITY_SOURCE_RECEIPT.PRIVATE.json']}))
    return d


def prepare(part):
    for n,h in read(HERE/'E117_SOURCE_UNITS_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published source-only E117 descriptor/intake code')
    base=origin();verify(base/'ORIGIN_SEAL.json',sha(base/'ORIGIN_SEAL.json'));descriptors=read(base/'DESCRIPTORS.PRIVATE.json')
    if part=='main':
        native=ROOT.parent/'wt-i2/cache/g_agreement/i2/parallel_gpu230/e117-final15600/terminal_pull/outputs/OUTPUT_SEAL.json';digest='44aadc42dc76ad0c0de8bb3e75acbdd00b9f6f8a5843f3bcaf2243a781242bd8';inp=ROOT.parent/'outputs/e117-inputs-v1/INPUT_SEAL.json';ptr=None
    else:
        native=ROOT.parent/'wt-wmech/cache/g_agreement/understand/analysis402_verified/E117/part_c_measured_a2/out/OUTPUT_SEAL.json';digest='9dd48b680986c55c34cef77b798be3e76a6c381c65fb6e21628d78d048da2ea0';inp=ROOT.parent/'outputs/e117c-inputs-v1/inputs/INPUT_SEAL.json';p=ROOT.parent/'outputs/e117c-inputs-v1/cpu_only/ORIGINAL_POINTERS.PRIVATE.json';require(sha(p)=='611a4066ad1bdd4bffb460008d8fb291558130d459bef2425c4010a92a5da390','original E117c input pointer bytes');ptr=read(p)
    ns=verify(native,digest);verify(inp,ns['input_sha256']);require(ns['status']=='COMPLETE' and ns['experiment']==('E117' if part=='main' else 'E117c'),'complete actual original source; planning/NOFIT excluded')
    records=[]
    for m in ns['files']:
        if m.startswith('jobs/') and m.endswith('.json'):
            records.extend((dict(seal=str(native),sha256=digest,member=m,keys=[i,'text']),r) for i,r in enumerate(read(native.parent/m)))
    units,joins=make_units(part,records,descriptors,ptr)
    copies,audit=redact([u['data'] for u in units],'E117',addresses=True);by={x['id']:x for x in copies};affected={x['id'] for x in audit['affected']};evidence={u['id']:u['data']['readout'] for u in units if u['id'] in affected};units=[dict(u,data=by[u['id']]) for u in units]
    rubric=ROOT/'projects/g_agreement/understand/wmech2/RUBRIC.md';require(sha(rubric)==RUBRIC_SHA,'frozen original E56/E57 rubric');units=[dict(u,rubric=rubric.read_text()) for u in units]
    d=CACHE/'E117'/('native_units' if part=='main' else 'targeted_sham_units');d.mkdir(exist_ok=True)
    if(d/'UNIT_SEAL.json').exists():verify(d/'UNIT_SEAL.json',sha(d/'UNIT_SEAL.json'));require(read(d/'UNITS.json')==units,'immutable full source units');return d
    for n,v in [('UNITS.json',units),('SOURCE_POINTERS.PRIVATE.json',joins),('PATH_REDACTION_AUDIT.json',audit),('ORIGINAL_EVIDENCE.PRIVATE.json',evidence)]:write(d/n,v)
    write(d/'CUSTODY.json',dict(experiment='E117',part=part,issuer='W-internals-C',verified=True,source_only_no_paid_admission=True,complete_eligible_native_grid=True,labels_cpu_only=True,original_E56_E57_descriptors_copied=True,original_E56_E57_rubric_sha256=RUBRIC_SHA,no_scientific_scoring_or_target_computation=True,all_degenerate_native_texts_retained=True,source_seals=[dict(seal=str(x),sha256=sha(x)) for x in (base/'ORIGIN_SEAL.json',native,inp)]))
    write(d/'UNIT_SEAL.json',dict(experiment='E117',part=part,n=len(units),files={n:sha(d/n) for n in ['UNITS.json','SOURCE_POINTERS.PRIVATE.json','PATH_REDACTION_AUDIT.json','ORIGINAL_EVIDENCE.PRIVATE.json','CUSTODY.json']}))
    write(d/'PREPARE_SPEC.json',dict(bank='E117',unit_seal=str(d/'UNIT_SEAL.json'),unit_sha256=sha(d/'UNIT_SEAL.json'),phase_name='targeted_sham' if part=='c' else 'native'))
    return d


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--part',choices=['main','c'],required=True);print('E117 source-only unit seal '+sha(prepare(p.parse_args().part)/'UNIT_SEAL.json'))
