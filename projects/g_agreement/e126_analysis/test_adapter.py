from pathlib import Path
import pytest
from . import adapter as a,rules
from .test_rules import item


def fixture(tmp,monkeypatch):
    monkeypatch.setattr(a,'GUARD',tmp/'ANALYSIS_ONCE.json')
    inventory={};private=[];ms={};original=[]
    for row,n in rules.ROWS.items():
        inventory[row]=[];ms[row]=[]
        for i in range(n):
            unit=f'{row}:{i}';r=item(unit,row=row)
            metadata=dict(item_id=unit,steered_value='B',candidate_A_value='A',pair_count=1,candidate_ids_sha256='synthetic-frozen-token-hash')
            inventory[row].append(metadata);private.append(dict(item_id=unit,row=row,arm='U',condition='steered',flipped=True,target='B'))
            def cell(value,direction,block=None,patch=None):
                raw_id=f'{unit}:{direction}:{block}:{patch}';identity=dict(metadata,row=row,direction=direction,block=block,patch=patch,raw_id=raw_id,patch_binding_verified=True,unscaled_residual_replacement=True,position=9 if patch=='earlier_token' else 20,read_index=20,norm_matched=True,random_seed=20261030)
                index=len(original);original.append(dict(identity=identity,raw=dict(id=raw_id,pair_logprobs=[[-1000-value,-1000]])))
                return dict(identity=dict(seal_index=0,member='original.json',keys=[index,'identity']),raw=dict(seal_index=0,member='original.json',keys=[index,'raw']))
            patches={str(b):{d:{p:cell(r['patches'][b][d][p],d,b,p)for p in rules.PATCHES}for d in rules.DIRECTIONS}for b in rules.BLOCKS}
            ms[row].append(dict(item_id=unit,clean=cell(r['clean'],'clean'),steered=cell(r['steered'],'steered'),patches=patches))
    def bundle(name,files,**meta):
        folder=tmp/name;folder.mkdir()
        for k,v in files.items():a.core.write(folder/k,v)
        a.core.seal(folder,'SEAL.json',**meta);return folder/'SEAL.json'
    pp=tmp/'PRIVATE.json';a.core.write(pp,private);monkeypatch.setattr(a,'PRIVATE_SHA',a.core.sha(pp))
    ip=bundle('inventory',{'INVENTORY.json':inventory},experiment='E126',status='SOURCE_ONLY_COHORT_BOUND',labels_cpu_only=True,source_e104_private_sha256=a.PRIVATE_SHA)
    source=bundle('original',{'original.json':original},experiment='E126',status='COMPLETE')
    op=bundle('output',{'MEASUREMENTS.json':ms},experiment='E126',status='COMPLETE',inventory_sha256=a.core.sha(ip),blocks=list(rules.BLOCKS),labels_cpu_only=True,logits_only=True,new_reader_or_judge_calls=0,steer=dict(block=40,positions='eight_before_read',alpha_by_row={'fact_recall':8,'language_plan':2}),source_seals=[dict(seal=str(source),sha256=a.core.sha(source))])
    return dict(inventory_seal=str(ip),inventory_sha256=a.core.sha(ip),e104_private=str(pp),output_seal=str(op),output_sha256=a.core.sha(op),analysis=str(tmp/'analysis')),source


def test_full_synthetic_binding_orientation_and_grid(tmp_path,monkeypatch):
    spec,source=fixture(tmp_path,monkeypatch)
    rows=a.inputs(spec,a.cohort(spec));assert len(rows)==134
    assert rows[0]['clean']==-1 and rows[0]['steered']==1
    assert rules.item_ratios(rows[0])['ratios'][52]['restore']['read_token']==pytest.approx(.6)


def test_wrong_original_value_rejected_before_claim(tmp_path,monkeypatch):
    spec,_=fixture(tmp_path,monkeypatch);p=Path(spec['inventory_seal']);inv=a.core.read(p.parent/'INVENTORY.json');inv['fact_recall'][0]['steered_value']='A';a.core.write(p.parent/'INVENTORY.json',inv)
    meta=a.core.read(p);meta.pop('files');a.core.seal(p.parent,p.name,**meta);spec['inventory_sha256']=a.core.sha(p)
    with pytest.raises(ValueError,match='target orientation'):a.run(spec,'synthetic')
    assert not a.GUARD.exists()


def test_earlier_position_in_steered_span_rejected(tmp_path,monkeypatch):
    spec,source=fixture(tmp_path,monkeypatch);records=a.core.read(source.parent/'original.json')
    next(x for x in records if x['identity']['patch']=='earlier_token')['identity']['position']=15
    a.core.write(source.parent/'original.json',records);meta=a.core.read(source);meta.pop('files');a.core.seal(source.parent,source.name,**meta)
    p=Path(spec['output_seal']);meta=a.core.read(p);meta.pop('files');meta['source_seals'][0]['sha256']=a.core.sha(source);a.core.seal(p.parent,p.name,**meta);spec['output_sha256']=a.core.sha(p)
    with pytest.raises(ValueError,match='earlier token'):a.run(spec,'synthetic')
    assert not a.GUARD.exists()


def test_once_guard_and_private_raw_values(tmp_path,monkeypatch):
    spec,_=fixture(tmp_path,monkeypatch);original=rules.analyze
    monkeypatch.setattr(rules,'analyze',lambda xs:original(xs,draws=10))
    seal=a.run(spec,'synthetic');result=a.core.read(seal.parent/'RESULTS.json')
    assert result['rows']['fact_recall']['n_items']==84
    assert len(a.core.read(seal.parent/'PER_ITEM.PRIVATE.json'))==134
    with pytest.raises(ValueError,match='once guard'):a.run(spec,'synthetic')


def test_commit_gate_before_spec_IO(monkeypatch):
    import sys
    monkeypatch.setattr(sys,'argv',['adapter','--spec','not-opened'])
    def fail():raise ValueError('uncommitted')
    monkeypatch.setattr(a,'committed',fail);monkeypatch.setattr(a.core,'read',lambda p:pytest.fail('read before commit gate'))
    with pytest.raises(ValueError,match='uncommitted'):a.main()


@pytest.mark.parametrize('cell_name,allowed',[('clean',True),('steered',False),('patch',False)])
def test_e105_complete_source_allowed_for_clean_cell_only(tmp_path,monkeypatch,cell_name,allowed):
    spec,source=fixture(tmp_path,monkeypatch)
    p=Path(spec['output_seal']);meta=a.core.read(p);grid=a.core.read(p.parent/'MEASUREMENTS.json')
    # Same byte-exact source under its original E105 experiment; no relabelled raw values.
    alt=tmp_path/'e105';alt.mkdir();(alt/'original.json').write_bytes((source.parent/'original.json').read_bytes())
    a.core.seal(alt,'SEAL.json',experiment='E105',status='COMPLETE')
    meta['source_seals'].append(dict(seal=str(alt/'SEAL.json'),sha256=a.core.sha(alt/'SEAL.json')))
    for cells in grid.values():
        for item in cells:
            cell=item[cell_name] if cell_name!='patch' else item['patches']['44']['restore']['read_token']
            cell['raw']['seal_index']=1
    a.core.write(p.parent/'MEASUREMENTS.json',grid);meta.pop('files');a.core.seal(p.parent,p.name,**meta);spec['output_sha256']=a.core.sha(p)
    if allowed:
        rows=a.inputs(spec,a.cohort(spec));assert len(rows)==134 and rows[0]['clean']==-1
    else:
        with pytest.raises(ValueError,match='unrelated raw scores'):a.inputs(spec,a.cohort(spec))
    assert not a.GUARD.exists()
