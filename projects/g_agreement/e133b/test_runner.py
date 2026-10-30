from pathlib import Path
import copy,json
import pytest
from projects.g_agreement.e133 import runner as v3
from projects.g_agreement.e133b import runner as r,selection as sel
from projects.g_agreement.e100.contract import sha

ROOT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e133b-inputs-v1/inputs')
DIGEST='0d2bd3968b0f4eb6981d960d3054ebc87d2e2ae52e150395d82a894ec56e2ec1'
def items(n):return [dict(id=f'{i}:{j}',pair_id=str(i),family='babi',member=j,ids=list(range(12)),read_index=11,candidate_ids=[[[3],[4]]])for i in range(n)for j in (0,1)]

def test_exact_original_v3_callable_aliases():
    for name in ['generation_batch','capture_batch','patch_batch','batches']:
        assert getattr(r,name)is getattr(v3,name)
    assert r.CAPTURE==(36,44,48,52,56,60)and r.READ==(44,52,60)and r.PATCH==(44,48,52,56,60)

@pytest.mark.parametrize('n,expected,kept',[(0,'SCREEN_RESULTS_ONLY',0),(19,'SCREEN_RESULTS_ONLY',19),(20,'MAIN',20),(41,'MAIN',41),(42,'MAIN',42),(494,'MAIN',42)])
def test_registered_count_boundary(n,expected,kept):
    d=r.main_disposition(n);assert d['action']==expected and d['kept_pairs']==kept

@pytest.mark.parametrize('n',[1,19,43])
def test_main_refused_before_runtime(n,tmp_path):
    with pytest.raises(ValueError):r.main_job(None,items(n),tmp_path/'never',lambda*a:True,gpu_type='synthetic')
    assert not(tmp_path/'never').exists()

def test_non_babi_and_role_bearing_contrast_refused():
    xs=items(20);xs[0]['family']='one_hop';xs[1]['family']='one_hop'
    with pytest.raises(ValueError):r.validate_babi(xs,'main')
    xs=items(20);xs[0]['candidate_ids'].append([[5],[6]])
    with pytest.raises(ValueError):r.validate_babi(xs,'main')

def test_fresh_complete_screen_no_model_on_forecast_failure(tmp_path):
    out=tmp_path/'screen';assert r.screen(None,None,items(494),out,lambda*a:False,gpu_type='synthetic')=='NO_FIT'
    with pytest.raises(SystemExit):sel.answers(out)
    with pytest.raises(FileExistsError):r.screen(None,None,items(494),out,lambda*a:True,gpu_type='synthetic')

def test_actual_byteidentical_original494_bank_public_schema_only():
    xs=r.load(ROOT,DIGEST,'screen');original=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e133-screen-adapted-v3/babi/inputs')
    assert len(xs)==988 and xs==json.loads((original/'items.json').read_text())
    assert sha(ROOT.parent/'inputs.tar.gz')=='02cb8f0a38abb71cbca04ffc3d617e2b65f25665467a7e9efc93dbd59ab7111e'
    assert all(set(x)=={'id','pair_id','family','member','ids','read_index','candidate_ids'}for x in xs)
    assert all(len(x['candidate_ids'])==1 and x['candidate_ids'][0][0][0]<x['candidate_ids'][0][1][0]for x in xs)

def test_original_parser_both_members_missing_dual_and_source_order_first42():
    labels=[dict(member_ids=[f'{i}:0',f'{i}:1'],original_current='kitchen',twin_current='garden',previous='office')for i in range(50)]
    ans={f'{i}:{j}':('  kitchen'if j==0 else ' garden')for i in range(50)for j in (0,1)}
    ans['0:0']=None;ans['1:1']='office';ans['2:0']='kitchen and garden'
    kept,n=sel.choose(labels,ans)
    assert n==47 and len(kept)==42 and kept[0]==['3:0','3:1']and kept[-1]==['44:0','44:1']
    assert sel.main_disposition(n)['action']=='MAIN'

def test_count_guard_invalid():
    for n in [-1,495,False,2.1]:
        with pytest.raises(ValueError):r.main_disposition(n)

@pytest.mark.parametrize('n',[19,20,44])
def test_new_screen_to_cpu_frozen_main_or_screen_only(tmp_path,monkeypatch,n):
    def write(p,x):p.write_text(json.dumps(x)+'\n')
    pub=tmp_path/'public';cpu=tmp_path/'cpu';screen=tmp_path/'screen'
    for p in [pub,cpu,screen]:p.mkdir()
    (screen/'jobs').mkdir()
    xs=items(494);write(pub/'items.json',xs);write(pub/'MANIFEST.json',dict(arm='babi'))
    write(pub/'INPUT_SEAL.json',dict(experiment='E133',stage='screen',labels_on_pod=False,files={f:sha(pub/f)for f in ['items.json','MANIFEST.json']}))
    labels=[dict(member_ids=[f'{i}:0',f'{i}:1'],original_current='kitchen',twin_current='garden',previous='office')for i in range(494)]
    write(cpu/'LABELS.PRIVATE.json',labels)
    write(cpu/'LABEL_SEAL.json',dict(public_input_sha256='a7bd943885497f10d62410c196dbed0f668fe770966c7fde7f8c6c58c0840c34',files={'LABELS.PRIVATE.json':sha(cpu/'LABELS.PRIVATE.json')}))
    ans=[dict(id=x['id'],text=('kitchen'if x['member']==0 else 'garden')if int(x['pair_id'])<n else 'office')for x in xs]
    write(screen/'jobs/0.json',ans)
    write(screen/'OUTPUT_SEAL.json',dict(experiment='E133',arm='babi',stage='screen',status='COMPLETE',files={'jobs/0.json':sha(screen/'jobs/0.json')}))
    monkeypatch.setattr(sel,'PUBLIC_SHA',sha(pub/'INPUT_SEAL.json'));monkeypatch.setattr(sel,'CPU_SHA',sha(cpu/'LABEL_SEAL.json'))
    out=tmp_path/'selection';result=sel.select(screen,sha(screen/'OUTPUT_SEAL.json'),pub,cpu,out)
    assert result['qualifying_pairs']==n and result['kept_pairs']==min(42,n)
    if n<20:assert result['action']=='SCREEN_RESULTS_ONLY'and not(out/'main_babi').exists()
    else:
        kept=r.load(out/'main_babi',result['input_sha256'],'main')
        assert [x['id']for x in kept]==[x['id']for x in xs[:2*min(42,n)]]
        assert not any({'label','current','previous','answer'}&set(x)for x in kept)
    with pytest.raises(FileExistsError):sel.select(screen,sha(screen/'OUTPUT_SEAL.json'),pub,cpu,out)

def test_original_selection_helpers_unchanged_ast():
    import ast
    original=Path(sel.__file__).resolve().parents[3]/'projects/g_agreement/e133_trackq/select133.py'
    a=ast.parse(original.read_text());b=ast.parse(Path(sel.__file__).read_text())
    for name in ['req','answers','correct','write_main']:
        aa=next(n for n in a.body if isinstance(n,ast.FunctionDef)and n.name==name)
        bb=next(n for n in b.body if isinstance(n,ast.FunctionDef)and n.name==name)
        assert ast.dump(aa)==ast.dump(bb)
