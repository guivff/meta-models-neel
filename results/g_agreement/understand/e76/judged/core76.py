"""E76 blind sampling and judged estimands; CPU only, no inference or transport."""
import sys,re,unicodedata
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from common76 import *
from regex76 import validate_grid
JHERE=HERE/'judged';JCACHE=CACHE/'judged_v1'
PRODUCTION_SEAL='4a199f6c48a3aed8175000804e1e69f2a270ca9edccf096a6e5a30f09c169c34'
REGEX_SEAL='a0b9808a250f905be103b5bafb90c27d34e8de69a09ed62ce00431734c5b3bd7'
RUBRIC_SHA='03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613'
CATEGORIES=('states_value','names_property_without_value','exhibits','silent')


def text_sha(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()


def validate_registry(reg):
    rows=reg['rows'];require(rows and len({(x['bank'],x['row']) for x in rows})==len(rows),'Unique nonempty frozen row set')
    count=0
    for row in rows:
        require(isinstance(row['property'],str) and row['property'] and row['families'],'Frozen property and values required')
        require(len({x['family'] for x in row['families']})==len(row['families']),'Unique family identity')
        for f in row['families']:
            values=f['values'];require(set(values)=={'A','B'} and values['A']!=values['B'] and f['weight']>0,'Binary A/B family and frozen weight')
            require(all(isinstance(v,str) and bool(v) or isinstance(v,list) and v and all(isinstance(x,str) and x for x in v) for v in values.values()),'Frozen strings or explicit synonym lists')
        count+=len(row['families'])
    n=min(50,5000//(4*count));require(n>0 and reg['n_per_row_reader_pool']==n and reg['expanded_records']==4*n*count,'Uniform per-cell sample and5000-record cap')
    return n


def build_export(records,reg):
    n=validate_registry(reg);grid=validate_grid(records);sample=np.random.default_rng(20261028)
    ids=np.random.default_rng(np.random.SeedSequence([20261028,1]));coins=np.random.default_rng(20261029).integers(0,2,N)
    packet=[];mapping=[];used=set()
    for row in sorted(reg['rows'],key=lambda x:(x['bank'],x['row'])):
        for reader in sorted(READERS):
            for pool in sorted(ARMS):
                selected=sorted(int(i) for i in sample.choice(N,n,replace=False))
                for i in selected:
                    original=grid[reader,pool][i];require(original['pool_index']==i,'Canonical pool index')
                    for family in row['families']:
                        opaque=ids.bytes(16).hex();require(opaque not in used,'Opaque ID collision');used.add(opaque)
                        packet.append({'id':opaque,'property':row['property'],'values':family['values'],'readout':original['text']})
                        mapping.append({'id':opaque,'bank':row['bank'],'row':row['row'],'reader':reader,'pool':pool,'pool_index':i,
                            'family':family['family'],'pseudo_truth':'A' if coins[i]==0 else 'B','source_native_id':original['id'],
                            'original_readout_sha256':text_sha(original['text'])})
    order=np.random.default_rng(np.random.SeedSequence([20261028,2])).permutation(len(packet));packet=[packet[int(i)] for i in order]
    validate_export(packet,mapping,reg)
    return packet,mapping


def validate_export(packet,mapping,reg):
    n=validate_registry(reg);require(len(packet)==len(mapping)==reg['expanded_records'],'Complete expanded packet')
    ids=[x['id'] for x in packet];require(len(set(ids))==len(ids),'Unique blind packet IDs')
    lookup={x['id']:x for x in packet};require(len({x['id'] for x in mapping})==len(mapping) and set(lookup)=={x['id'] for x in mapping},'Complete private grouping key')
    require(all(set(x)=={'id','property','values','readout'} and re.fullmatch('[a-f0-9]{32}',x['id']) and isinstance(x['readout'],str) for x in packet),'Exact blind positive fields')
    rows={(x['bank'],x['row']):x for x in reg['rows']};groups=defaultdict(dict)
    coins=np.random.default_rng(20261029).integers(0,2,N)
    for m in mapping:
        row=rows[m['bank'],m['row']];family=next(f for f in row['families'] if f['family']==m['family']);x=lookup[m['id']]
        require(x['property']==row['property'] and x['values']==family['values'] and text_sha(x['readout'])==m['original_readout_sha256'],'Verbatim property/value/readout linkage')
        require(m['reader'] in READERS and m['pool'] in ARMS and type(m['pool_index']) is int and 0<=m['pool_index']<N,'Original reader/pool/index')
        require(m['pseudo_truth']==('A' if coins[m['pool_index']]==0 else 'B'),'Frozen pseudo-truth coin')
        cell=m['bank'],m['row'],m['reader'],m['pool'];key=m['pool_index'],m['family'];require(key not in groups[cell],'Duplicate pair');groups[cell][key]=m
    require(len(groups)==4*len(rows),'Every row × reader × pool required')
    for cell,entries in groups.items():
        families={f['family'] for f in rows[cell[:2]]['families']};ix={i for i,f in entries}
        require(len(ix)==n and set(entries)=={(i,f) for i in ix for f in families},'Uniform sampled vectors and complete family expansion')


def render(record,rubric):
    val=lambda v:' / '.join(v) if isinstance(v,list) else v
    return {'id':record['id'],'readout':record['readout'],'rubric':rubric+'\n\nProperty: '+record['property']+'\nA: '+val(record['values']['A'])+'\nB: '+val(record['values']['B'])+'\n'}


def normalize(text):
    quotes=dict.fromkeys('‘’‚‛',"'")|dict.fromkeys('“”„‟«»','"')
    return re.sub(r'\s+',' ',''.join(quotes.get(c,'-' if unicodedata.category(c)=='Pd' else c) for c in text)).strip().casefold()


def join_terminal(terminal,copied):
    require(len(terminal)==len(copied) and len({x['id'] for x in terminal})==len(terminal)
        and {x['id'] for x in terminal}=={x['id'] for x in copied},'Exact terminal judgment grid; missing is not UNPARSEABLE')
    indexed={x['id']:x for x in copied};out={}
    for row in terminal:
        require(type(row.get('attempts')) is int and 0<=row['attempts']<=2,'Original singleton retry count')
        if row['status']=='UNPARSEABLE':
            require(row['code'] is None and row['attempts']==2,'Only exhausted validation retries are missing')
            out[row['id']]=None;continue
        require(row['status']=='KEPT' and isinstance(row['code'],dict),'Terminal KEPT or UNPARSEABLE only')
        code=row['code'];require(set(code)=={'id','category','values','evidence'} and code['id']==row['id'],'Exact code schema')
        require(code['category'] in CATEGORIES and isinstance(code['values'],list) and len(set(code['values']))==len(code['values'])
            and set(code['values'])<={'A','B'} and bool(code['values'])==(code['category']=='states_value'),'Category/value consistency')
        require(isinstance(code['evidence'],str),'String evidence')
        evidence=normalize(code['evidence']);require(evidence in normalize(indexed[row['id']]['readout'])
            and (bool(evidence) or code['category']=='silent'),'Kept evidence must match actual judge copy')
        out[row['id']]=code
    return out


def estimates(entries,codes,row,excluded=set(),draws=2000,seed=20261027):
    entries=[x for x in entries if x['id'] not in excluded]
    families=row['families'];vectors=sorted({x['pool_index'] for x in entries});pos={i:k for k,i in enumerate(vectors)}
    num_s=np.zeros((len(vectors),len(families)));num_n=num_s.copy();den=num_s.copy();category=Counter()
    fpos={f['family']:i for i,f in enumerate(families)}
    unparseable=0
    for x in entries:
        code=codes[x['id']]
        if code is None:unparseable+=1;continue
        category[code['category']]+=1;i=pos[x['pool_index']];f=fpos[x['family']];den[i,f]=1
        values=code['values'];num_n[i,f]=bool(values)
        num_s[i,f]=0 if len(values)!=1 else (1 if values==[x['pseudo_truth']] else -1)
    weights=np.array([f['weight'] for f in families],float);weights/=weights.sum()
    totals=den.sum(0)
    counts={'n_pairs':len(entries),'n_sampled_vectors':len(vectors),'kept':len(entries)-unparseable,'UNPARSEABLE':unparseable,
        'unparseable_over_5_percent':20*unparseable>len(entries),'category_counts':dict(category),
        'family_parseable_counts':{str(f['family']):int(totals[j]) for j,f in enumerate(families)}}
    if len(vectors)==0 or (totals==0).any():return {**counts,'status':'NOT EVALUABLE','reason':'No parseable records for one or more frozen families','S':None,'N_any_value':None}
    point_s=float((num_s.sum(0)/totals)@weights);point_n=float((num_n.sum(0)/totals)@weights)
    active=np.where(den.sum(1)>0)[0];rng=np.random.default_rng(seed);boot_s=[];boot_n=[];undefined=0
    for start in range(0,draws,100):
        ix=active[rng.integers(0,len(active),size=(min(100,draws-start),len(active)))];d=den[ix].sum(1);valid=(d>0).all(1)
        undefined+=int((~valid).sum());d=d[valid]
        boot_s.extend(((num_s[ix].sum(1)[valid]/d)@weights).tolist());boot_n.extend(((num_n[ix].sum(1)[valid]/d)@weights).tolist())
    stat=lambda value,boot:{'estimate':value,'ci95':np.quantile(boot,[.025,.975],method='linear').tolist() if boot else None}
    return {**counts,'status':'EVALUABLE','n_vectors_with_parseable_codes':len(active),
        'S':stat(point_s,boot_s),'N_any_value':stat(point_n,boot_n),'bootstrap_undefined_draws':undefined,'bootstrap_defined_draws':len(boot_s)}


def analyze(mapping,codes,reg,regex,redacted):
    require(set(codes)=={x['id'] for x in mapping} and redacted<=set(codes),'Complete once-only codes and audited redaction IDs')
    full={(x['bank'],x['row']):x for x in regex['rows']};groups=defaultdict(list)
    for x in mapping:groups[x['bank'],x['row'],x['reader'],x['pool']].append(x)
    output=[]
    for row in reg['rows']:
        key=row['bank'],row['row'];rr=full[key];item={'bank':key[0],'row':key[1],'judged_n_per_cell':reg['n_per_row_reader_pool'],
            'property':row['property'],'binary_families':len(row['families']),'regex_status':rr['regex_status'],'readers':{}}
        for reader in READERS:
            item['readers'][reader]={}
            for pool in ARMS:
                entries=groups[key+(reader,pool)];ids={x['id'] for x in entries}
                item['readers'][reader][pool]={'judged_full':estimates(entries,codes,row),
                    'judged_without_redacted':estimates(entries,codes,row,redacted),'redacted_pairs':len(ids&redacted),
                    'redacted_vectors':len({x['pool_index'] for x in entries if x['id'] in redacted}),
                    'sealed_full_regex':rr['readers'][reader][pool] if rr['regex_status']=='AVAILABLE' else None}
        output.append(item)
    return {'experiment':'E76','status':'JUDGED_FLOORS_COMPLETE_ONCE','rows':output,
        'excluded_rows':reg['excluded_rows'],'bootstrap':{'draws':2000,'seed':20261027,'unit':'sampled pool vector, all value families together','method':'95% percentile'},
        'S_definition':'correct-only minus wrong-only, using frozen independent seed20261029 pseudo-truth; both/neither zero',
        'N_definition':'Any explicitly asserted A/B value; both-values included',
        'missing_policy':'UNPARSEABLE counted/excluded per family; no missing family dropped or renormalized',
        'redaction_sensitivity':'Same sampled grid, affected opaque IDs excluded; no replacement/resampling',
        'regex_comparison':'Unchanged full500-vector-per-pool sealed regex floor; judged sample n is displayed',
        'total_pairs':len(mapping),'UNPARSEABLE':sum(x is None for x in codes.values()),'redacted_pairs':len(redacted),'judge_calls':0}
