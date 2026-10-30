from pathlib import Path
import pytest
from . import adapter as a,producer_q232 as q
from .test_adapter import Fixture
from projects.g_agreement.e105.scoring import batches


def fixture(tmp,monkeypatch):
    f=Fixture(tmp,monkeypatch);items=[];joins=[];donors={x['id']:x for x in a.rules.same_condition_pairs(f.cells)}
    candidates=[x['candidate_ids'][0] for x in f.defs]
    for c in f.cells:
        carrier=c['id']
        for cond in ['0']+(['T','S'] if c['split']=='test' and c['addressed']==0 else []):
            donor=None if cond=='0' else donors[carrier][cond+'_donor_id']
            ident=q.oid(carrier,cond,donor)
            x=dict(id=ident,inventory_id=q.oid('inv',carrier),base_id=carrier,row='e122',condition=cond,block=44,ids=[10,20],read_index=1,candidate_ids=candidates,vector_index=None if cond=='0' else len(items),donor_id=None if donor is None else q.oid('donor',donor))
            items.append(x)
            j=dict(id=ident,part='a' if cond=='0' else 'b',matched_set=c['quartet_id'],genre=c['genre'],split=c['split'])
            j.update(dict(public_id=carrier,addressed=c['addressed']) if cond=='0' else dict(recipient_public_id=carrier,donor_public_id=donor,condition=cond))
            joins.append(j)
    ip=f.bundle('q_input',{'items.json':items,'vectors.npy':[]},experiment='E122',labels_on_pod=False,block=44,contrasts_seal_sha256=a.CONTRAST_SHA,candidate_order='[positive, negative]',contrast_order=f.order,parts={'a_unpatched':600,'b_T':200,'b_S':200})
    monkeypatch.setattr(q,'INPUT_SHA',a.sha(ip))
    sources=dict(contrasts_seal=a.CONTRAST_SHA,e85_labels=a.E85_PRIVATE_SHA,e85_capture_stage_seal=q.CAPTURE_SHA,donor_seed=20261030)
    jp=f.bundle('q_join',{'JOIN.PRIVATE.json':dict(sources=sources,records=joins)},experiment='E122',input_seal_sha256=q.INPUT_SHA,sources=sources)
    monkeypatch.setattr(q,'JOIN_SHA',a.sha(jp))
    jobs={f'jobs/{k:04d}_e122.json':dict(records=[],indices=ix) for k,ix in enumerate(batches(items))}
    # No numerical raw arrays are needed or allowed in the source-only index test.
    folder=tmp/'q_output';(folder/'jobs').mkdir(parents=True)
    for name,value in jobs.items():a.write(folder/name,value)
    a.core.seal(folder,'SEAL.json',experiment='E122',status='COMPLETE',input_seals={'e122':q.INPUT_SHA},evaluations=1000)
    output=folder/'SEAL.json'
    monkeypatch.setattr(q,'OUTPUT_SHA',a.sha(output))
    entry=dict(seal=str(output),sha256=a.sha(output),producer_input_seal=str(ip),producer_join_seal=str(jp))
    return f,entry,items


def test_exact_trackq_context_and_metadata_only_index(tmp_path,monkeypatch):
    f,entry,items=fixture(tmp_path,monkeypatch)
    output=a.core.read(entry['seal']);ctx=q.context(entry,output,f.fp,f.cells,f.defs)
    assert len(ctx['mapping'])==1000
    old=a.read
    def no_job_read(path):
        assert 'jobs' not in Path(path).parts
        return old(path)
    monkeypatch.setattr(a,'read',no_job_read)
    spec=dict(f.base,raw_output_seal=entry['seal'],producer_input_seal=entry['producer_input_seal'],producer_join_seal=entry['producer_join_seal'])
    plan=q.prepare(spec);index=a.read(Path(a.read(plan)['raw_index_seal']).parent/'RAW_INDEX.json')
    assert len(index['native'])==600 and len(index['transplant'])==200
    assert all(set(v)=={'T','S'} for v in index['transplant'].values())


def test_wrong_original_donor_rejected_without_guard(tmp_path,monkeypatch):
    f,entry,_=fixture(tmp_path,monkeypatch);jp=Path(entry['producer_join_seal']);d=a.read(jp.parent/'JOIN.PRIVATE.json')
    next(x for x in d['records'] if x.get('condition')=='S')['donor_public_id']='wrong-donor'
    a.write(jp.parent/'JOIN.PRIVATE.json',d);meta=a.read(jp);meta.pop('files');a.core.seal(jp.parent,jp.name,**meta);monkeypatch.setattr(q,'JOIN_SHA',a.sha(jp))
    with pytest.raises(ValueError,match='donor'):q.context(entry,a.read(entry['seal']),f.fp,f.cells,f.defs)
    assert not (a.CANONICAL/'dev_selection_ONCE.json').exists()


def test_trackq_full_synthetic_phases_no_raw_rewrite(tmp_path,monkeypatch):
    from . import watch
    f,entry,items=fixture(tmp_path,monkeypatch);by={c['id']:c for c in f.cells}
    out=Path(entry['seal']).parent
    for number,indices in enumerate(batches(items)):
        records=[]
        for i in indices:
            x=items[i];c=by[x['base_id']]
            shift=2*c['addressed'] if x['condition']=='0' else 3 if x['condition']=='T' else 2
            records.append(dict({k:x[k] for k in ('id','inventory_id','base_id','row','condition','block','vector_index')},pair_logprobs=[[-1000,-1000],[-1000+shift,-1000],[-1000,-1000],[-1000,-1000]]))
        a.write(out/f'jobs/{number:04d}_e122.json',dict(records=records,indices=indices))
    meta=a.read(entry['seal']);meta.pop('files');a.core.seal(out,'SEAL.json',**meta);monkeypatch.setattr(q,'OUTPUT_SHA',a.sha(entry['seal']))
    spec=dict(f.base,raw_output_seal=entry['seal'],producer_input_seal=entry['producer_input_seal'],producer_join_seal=entry['producer_join_seal'])
    plan=a.read(q.prepare(spec));before=a.sha(entry['seal'])
    result=watch.run(plan,'synthetic-commit')
    assert result['status']=='COMPLETE_ALL_PHASES'
    assert a.read(a.CANONICAL/'dev_selection'/'SELECTION.json')['selected_contrast_id']=='self'
    assert a.read(a.CANONICAL/'native_test'/'RESULTS.json')['R_BEV1']=='MET'
    assert a.read(a.CANONICAL/'transplant'/'RESULTS.json')['fraction_recovered']['estimate']==.5
    assert a.sha(entry['seal'])==before
