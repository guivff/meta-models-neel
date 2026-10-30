import pytest
from projects.g_agreement.e100_analysis import part_e as e
from projects.g_agreement.e100_analysis.rules import Bootstrap,ROWS

def cells(v=1):return {(r,s,'transplant'):{str(i):v for i in range(84)} for r in e.ROWS for s in ('oracle','nla')}

def test_two_rows_descriptive():
    z=e.analyze(cells());assert z['status']=='DESCRIPTIVE'
    assert all(z['rows'][r]['oracle']['estimate']==1 for r in e.ROWS)
    assert 'bookkeeping-specific' in z['rows'][e.ROWS[0]]['oracle']['pre_stated_reading']
    assert 'covers tracked state' in e.analyze(cells(0))['rows'][e.ROWS[0]]['oracle']['pre_stated_reading']

def test_reuse_original_bootstrap_algorithm():
    xs=cells();xs[(e.ROWS[0],'oracle','transplant')]['0']=None
    b=e.PartEBootstrap(xs)
    old={(ROWS[i],s,c):v for (r,s,c),v in xs.items() for i in [e.ROWS.index(r)]}
    a=Bootstrap(old)
    assert b.stat(e.ROWS[0],'transplant')==a.stat(ROWS[0],'transplant')

def test_missing_and_exact_grid():
    xs=cells(None);assert e.analyze(xs)['rows'][e.ROWS[0]]['oracle']['pre_stated_reading']=='NOT EVALUABLE'
    xs=cells();xs.pop(next(iter(xs)))
    with pytest.raises(ValueError):e.analyze(xs)
    xs=cells();xs[next(iter(xs))].pop('0')
    with pytest.raises(ValueError):e.analyze(xs)

def test_part_e_guard_is_separate(tmp_path):
    assert '/e100/part_e/' in str(e.GUARD)
    s=dict(analysis=str(tmp_path/'a'),guard=str(tmp_path/'g'),output_sha256='synthetic');e.core.claim(s,'synthetic')
    s['analysis']=str(tmp_path/'b')
    with pytest.raises(FileExistsError):e.core.claim(s,'synthetic')


def test_amendment_literal_and_false_custody():
    inv=dict(intervention='MISSING',pre_gpu_pairing_committed='MISSING')
    fields=dict(intervention=dict(value='h′ = h_donor at the read site'),pre_gpu_pairing_committed=dict(value=False))
    literal,caveat=e.amendment(inv,dict(amendment_fields=fields))
    assert literal=='h_prime=h_donor' and 'not committed before the first GPU run' in caveat
    with pytest.raises(ValueError):e.amendment(inv,{})

def test_per_row_gate_preserves_original_container_stat():
    xs=cells();base=e.analyze(xs)
    gates=dict(zip(e.ROWS,[.9075963718820862,.7142857142857143]))
    z=e.analyze(xs,gates,'synthetic custody caveat')
    assert z['rows'][e.ROWS[0]]==base['rows'][e.ROWS[0]]
    assert z['custody_caveat']=='synthetic custody caveat'
    excluded=z['rows'][e.ROWS[1]]
    assert excluded['status']=='EXCLUDED BY E87 GATE' and len(excluded['readouts']['oracle'])==84
    assert 'estimate' not in excluded
    gates[e.ROWS[1]]=.90
    assert e.analyze(xs,gates)['rows'][e.ROWS[1]]==base['rows'][e.ROWS[1]]


def test_split_gate_inventory_and_original_inputs(tmp_path,monkeypatch):
    import json,hashlib
    def write(name,x):
        p=tmp_path/name;p.write_text(json.dumps(x));return p
    def seal(name,files,**metadata):
        p=write(name,dict(files={f:e.core.sha(tmp_path/f) for f in files},**metadata));return p,e.core.sha(p)
    meta=[];measure=[];source={'gates':dict(zip(e.ROWS,[.9076,.7143])),'values':{}}
    def ref(*keys):return dict(seal_index=0,member='source.json',keys=list(keys))
    for row in e.ROWS:
        for i in range(84):
            ident=f'{row}-{i}';target=str(1-i%2)
            meta.append(dict(id=ident,row=row,split='test',donor_id=f'{row}-{i^1}',original_value=str(i%2),target_value=target))
            source['values'][ident]=dict(target=target,letter='A',text='value',code=dict(id=ident,category='states_value',values=['A'],evidence='value'))
            z=dict(target_value=ref('values',ident,'target'),target_letter=ref('values',ident,'letter'),text=ref('values',ident,'text'),code=ref('values',ident,'code'),judgment_id=ident)
            measure.append(dict(id=ident,systems=dict(oracle=z,nla=z)))
    write('INVENTORY.json',meta);write('source.json',source)
    sp,sh=seal('SOURCE_SEAL.json',['source.json'])
    ip,ih=seal('INV.json',['INVENTORY.json'],experiment='E100e',pairing_seed=20261029,intervention='MISSING',pre_gpu_pairing_committed='MISSING',reader_blocks=dict(oracle=44,nla=42))
    write('MEASUREMENTS.json',measure[:84]);write('HOLDER_DESCRIPTIVE.json',dict(row=e.ROWS[1],e87_gate=ref('gates',e.ROWS[1]),items=measure[84:]))
    op,oh=seal('OUT.json',['MEASUREMENTS.json','HOLDER_DESCRIPTIVE.json'],experiment='E100e',status='COMPLETE',inventory_sha256=ih,route_verified=True,privacy_verified=True,labels_cpu_only=True,one_greedy_readout_per_cell=True,donor_vector_binding_verified=True,rubric='E82',source_seals=[dict(seal=str(sp),sha256=sh)],e87_gates={e.ROWS[0]:ref('gates',e.ROWS[0])},excluded_by_gate={e.ROWS[1]:{}},amendment_fields=dict(intervention=dict(value='h′ = h_donor at the read site'),pre_gpu_pairing_committed=dict(value=False)))
    monkeypatch.setattr(e.subprocess,'check_output',lambda args,**kw:str(tmp_path)+'\n' if args[1]=='rev-parse' else ip.read_bytes())
    xs,gates,caveat=e.inputs(dict(inventory_seal=str(ip),inventory_commit='a'*40,inventory_sha256=ih,output_seal=str(op),output_sha256=oh))
    z=e.analyze(xs,gates,caveat)
    assert z['rows'][e.ROWS[0]]['oracle']['estimate']==1
    assert len(z['rows'][e.ROWS[1]]['readouts']['nla'])==84
