"""CPU-only sealed E67 selection. No model, judge, or E67 re-analysis runs."""
import argparse, collections, hashlib, json, random, tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SEED=20261028

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')
def require(ok,msg):
    if not ok:raise ValueError(msg)

def verify(path,expected,ledger):
    path=Path(path);require(sha(path)==expected,'Source seal mismatch: '+str(path));ledger[str(path)]=expected
    seal=read(path)
    for name,h in seal['files'].items():
        p=path.parent/name;require(sha(p)==h,'Source member mismatch: '+name);ledger[str(p)]=h
    return seal

def cohort(code):
    if code is None:return None
    vs={c['verdict'] for c in code['claims']}
    if 'CONTRADICTED' in vs:return 'hallucinated'
    if 'SUPPORTED' in vs:return 'faithful'
    return None

def allocate(capacities,limit=200):
    total=sum(capacities.values());n=min(limit,total)
    if not total:return {k:0 for k in capacities}
    result={k:n*v//total for k,v in capacities.items()}
    order=sorted(capacities,key=lambda k:(-(n*capacities[k]%total),k))
    for k in order[:n-sum(result.values())]:result[k]+=1
    return result

def select(units,limit=200):
    groups=collections.defaultdict(lambda:{'hallucinated':[],'faithful':[]})
    for u in units:
        if u['cohort']:groups[(u['wave'],u['bank'],u['reader'])][u['cohort']].append(u)
    capacities={k:min(map(len,g.values())) for k,g in groups.items()}
    quotas=allocate(capacities,limit);rng=random.Random(SEED);chosen=[];counts=[]
    for k in sorted(groups):
        g=groups[k];n=quotas[k]
        counts.append(dict(wave=k[0],bank=k[1],reader=k[2],eligible={c:len(v) for c,v in g.items()},selected_per_cohort=n))
        for c in ('hallucinated','faithful'):
            chosen.extend(rng.sample(sorted(g[c],key=lambda u:u['uid']),n))
    return sorted(chosen,key=lambda u:u['uid']),counts

def pair_controls(selected,eligible):
    rng=random.Random(SEED);out={}
    for u in sorted(selected,key=lambda x:x['uid']):
        pool=sorted({v['source_key'] for v in selected if (v['wave'],v['bank'])==(u['wave'],u['bank']) and v['source_key']!=u['source_key']})
        if not pool:pool=sorted({v['source_key'] for v in eligible if v['cohort'] and (v['wave'],v['bank'])==(u['wave'],u['bank']) and v['source_key']!=u['source_key']})
        require(pool,'No same-bank different-item control for '+u['uid']);out[u['uid']]=rng.choice(pool)
    return out

def load(ledger):
    units=[];sources={}
    for wave in (1,2):
        specpath=ROOT/f'results/g_agreement/r/e67_analysis/ANALYSIS_SPEC.wave{wave}.json';ledger[str(specpath)]=sha(specpath);spec=read(specpath)
        priv=Path(spec['private_seal']);verify(priv,spec['private_seal_sha256'],ledger)
        pairmap=read(priv.parent/'PAIRING_CONDITION_MAP.PRIVATE.json')
        binding=read(priv.parent/'SOURCE_BINDING.PRIVATE.json')
        packetroot=ROOT/f'results/g_agreement/understand/e67/judge_wave{wave}'
        verify(packetroot/'JUDGE_PACKET_SEAL.json',pairmap['packet_seal_sha256'],ledger)
        packets={};codes={}
        for n,g in spec['terminal_grids'].items():
            n=int(n);root=Path(g['dir']);verify(root/'RESULT_SEAL.json',g['result_seal_sha256'],ledger)
            rows=read(root/'JUDGMENTS.json');codes[n]={r['id']:r for r in rows};require(len(codes[n])==len(rows),'Duplicate code IDs')
            rows=[json.loads(x) for x in (packetroot/f'packet_{n:02d}.jsonl').read_text().splitlines()]
            packets[n]={r['id']:r for r in rows};require(set(packets[n])==set(codes[n]),'Complete packet judgment join')
        suffixes={'E49':'/e49/cache/frozen_2026-10-26/items.PRIVATE.json','E54':'/e54_items.json','D4':'/e61/inputs_v2_label_free/items.json'} if wave==1 else {'E56':'/e56/inputs_v3_self_admit/items.json','E57':'/e57/inputs_v4_single/items.json'}
        banks={}
        for bank,suffix in suffixes.items():
            candidates=[p for p in binding['files_sha256'] if p.endswith(suffix)];require(len(candidates)==1,'Unique original item source '+bank)
            p=candidates[0];h=binding['files_sha256'][p];require(sha(p)==h,'Original item file changed');ledger[p]=h
            banks[bank]={x['id']:x for x in read(p)}
        for p in pairmap['pairs']:
            matched=next(r for r in p['records'] if r['condition']=='matched');n=matched['packet'];opaque=matched['id'];packet=packets[n][opaque];j=codes[n][opaque]
            require(digest(packet['prompt_text'])==matched['prompt_sha256'] and digest(packet['readout'])==p['readout_sha256'],'Matched text custody')
            require(j['status'] in ('KEPT','UNPARSEABLE'),'Unexpected code status')
            code=j['code'];require((code is None)==(j['status']=='UNPARSEABLE'),'Unparseable sentinel')
            if code is not None:require(code['id']==opaque,'Code identity')
            item=banks[p['bank']][p['item_id']];require(item['split']=='test','Test source required')
            require(item['text']==packet['prompt_text'],'Original read prefix differs from packet')
            ids=item['ids'];require(ids,'Nonempty source IDs')
            if p['bank']=='D4':require(ids==item['read_ids'] and item['read_index']==len(ids)-1,'D4 copied sentence read boundary')
            source_key=f"wave{wave}|{p['bank']}|{p['item_id']}"
            src={'id':'s_'+digest(source_key)[:24],'prompt':item['text'],'input_ids':ids,'read_position':len(ids)-1}
            require(source_key not in sources or sources[source_key]==src,'Cross-reader source mismatch');sources[source_key]=src
            units.append(dict(uid=f"wave{wave}:{p['pair_id']}",wave=wave,bank=p['bank'],reader=p['reader'],row=p['row'],item_id=p['item_id'],arm=p.get('arm'),source_key=source_key,cohort=cohort(code),claims=[] if code is None else code['claims'],readout=packet['readout'],E67_matched_id=opaque,E67_packet=n,truncation_cohort=p['truncation_cohort']))
    require(len({u['uid'] for u in units})==len(units),'Wave-qualified identities unique')
    return units,sources

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    ledger={};verify(HERE/'PRE_DATA_SEAL.json',sha(HERE/'PRE_DATA_SEAL.json'),ledger)
    units,sources=load(ledger);selected,counts=select(units);controls=pair_controls(selected,units)
    keys=sorted({u['source_key'] for u in selected}|set(controls.values()))
    public=[sources[k] for k in keys]
    private=[];calls=[]
    for u in selected:
        u=dict(u);u['own_source_id']=sources[u['source_key']]['id'];u['control_source_key']=controls[u['uid']];u['control_source_id']=sources[u['control_source_key']]['id'];private.append(u)
        verdict='CONTRADICTED' if u['cohort']=='hallucinated' else 'SUPPORTED'
        for i,c in enumerate(u['claims']):
            if c['verdict']!=verdict:continue
            for arm,source in [('own',u['own_source_id']),('mismatched',u['control_source_id'])]:
                calls.append(dict(id='j_'+digest(f"{u['uid']}|{i}|{arm}")[:24],readout_uid=u['uid'],wave=u['wave'],bank=u['bank'],reader=u['reader'],item_id=u['item_id'],cohort=u['cohort'],claim_index=i,claim=c['claim'],verdict=c['verdict'],arm=arm,source_id=source))
    require(len({x['id'] for x in calls})==len(calls),'Unique calls')
    a.out.mkdir(parents=True,exist_ok=False)
    write(a.out/'SOURCE_PREFIXES.json',public);write(a.out/'SELECTION.PRIVATE.json',private);write(a.out/'CLAIM_CALLS.PRIVATE.json',calls)
    write(a.out/'SOURCE_CUSTODY.PRIVATE.json',{'files':ledger,'source_key_to_public_id':{k:sources[k]['id'] for k in keys}})
    with tarfile.open(a.out/'PUBLIC_SAMPLING.tar.gz','w:gz') as archive:archive.add(a.out/'SOURCE_PREFIXES.json',arcname='SOURCE_PREFIXES.json')
    summary={'experiment':'E103','seed':SEED,'selected_readouts':len(selected),'selected_by_cohort':dict(collections.Counter(u['cohort'] for u in selected)),'strata':counts,'public_source_items':len(public),'samples':8*len(public),'claim_calls':len(calls),'claims':len(calls)//2,'wave_namespaces_separate':True,'first_output_utc':'unknown','first_output_reason':'CPU input selection only; no model continuations or E103 judgments exist','files':{p.name:sha(p) for p in sorted(a.out.iterdir()) if p.is_file()},'private_cache':str(a.out.resolve()),'pod_allowlist':['SOURCE_PREFIXES.json']}
    write(a.out/'SELECTION_SEAL.json',summary);write(HERE/'SELECTION_SEAL.json',summary)
    print(json.dumps({k:summary[k] for k in ['selected_by_cohort','public_source_items','samples','claims','claim_calls','strata']},indent=2))
if __name__=='__main__':main()
