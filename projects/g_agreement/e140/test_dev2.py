"""Prospective source-scope tests only; no real screen/outcome access."""
import pytest
from projects.g_agreement.e140 import runner as r,selection as s
from projects.g_agreement.e140.test_runner import items,FixtureTok
from projects.g_agreement.e100.contract import read,write,sha


def packet(tmp_path,monkeypatch):
 root=tmp_path/'public';root.mkdir();xs=items(300)
 write(root/'items.json',xs)
 write(root/'MANIFEST.json',dict(pairs=300,prompts=600,authority='section252 deviation2 b10b2694e',parent_input_sha256=r.PARENT_INPUT_SHA,parent_items_sha256=r.PARENT_ITEMS_SHA))
 write(root/'INPUT_SEAL.json',dict(experiment='E140',stage='screen',labels_on_pod=False,files={p.name:sha(p)for p in root.iterdir()}))
 h=sha(root/'INPUT_SEAL.json');monkeypatch.setattr(r,'PREFIX_INPUT_SHA',h)
 return root,h,xs


def answer_packet(tmp_path,xs,n):
 root=tmp_path/'answers';(root/'jobs').mkdir(parents=True)
 answers=[dict(id=x['id'],text=('Alpha'if x['member']==0 else'Beta')if int(x['pair_id'][1:])<n else'common')for x in xs]
 write(root/'jobs/000000.json',answers)
 def seal():
  write(root/'OUTPUT_SEAL.json',dict(experiment='E140',stage='screen',status='COMPLETE',files={'jobs/000000.json':sha(root/'jobs/000000.json')}))
  return sha(root/'OUTPUT_SEAL.json')
 return root,seal(),answers,seal


@pytest.mark.parametrize('n',[39,40,90])
def test_prefix_complete_census_threshold_and_order(tmp_path,monkeypatch,n):
 root,h,xs=packet(tmp_path,monkeypatch);a,ah,_,_=answer_packet(tmp_path,xs,n)
 assert len(r.load(root,h,'screen'))==600
 result=s.select(a,ah,root,h,tmp_path/'selection',tokenizer=FixtureTok())
 assert result['screen_candidates']==300 and result['qualifying_pairs']==n
 assert result['screen_scope_authority']==r.SCOPE_AUTHORITY and result['parent_input_sha256']==r.PARENT_INPUT_SHA
 assert result['kept_pairs']==min(n,84)
 if n<40:
  assert result['action']=='SCREEN_RESULTS_ONLY' and not(tmp_path/'selection/main').exists()
 else:
  main=r.load(tmp_path/'selection/main',result['input_sha256'],'main')
  assert main==xs[:2*min(n,84)]
  p=read(tmp_path/'selection/main/SCREEN_SELECTION_SEAL.json')
  assert p['screen_candidates']==300 and p['parent_items_sha256']==r.PARENT_ITEMS_SHA


@pytest.mark.parametrize('change',['missing','extra','duplicate'])
def test_prefix_missing_extra_duplicate_answers_rejected(tmp_path,monkeypatch,change):
 root,h,xs=packet(tmp_path,monkeypatch);a,_,answers,seal=answer_packet(tmp_path,xs,50)
 if change=='missing':answers.pop()
 elif change=='extra':answers.append(dict(id='foreign',text='Alpha'))
 else:answers.append(answers[0])
 write(a/'jobs/000000.json',answers)
 with pytest.raises(ValueError):s.select(a,seal(),root,h,tmp_path/'selection',tokenizer=FixtureTok())
 assert not(tmp_path/'selection').exists()


def test_unpinned_or_wrong_parent_prefix_refused(tmp_path,monkeypatch):
 root,h,xs=packet(tmp_path,monkeypatch)
 with pytest.raises(ValueError):r.screen_scope(root,'another-seal',xs)
 m=read(root/'MANIFEST.json');m['parent_input_sha256']='wrong';write(root/'MANIFEST.json',m)
 with pytest.raises(ValueError):r.screen_scope(root,h,xs)
 with pytest.raises(ValueError):r.validate_items(items(299),'screen')


def test_main_cannot_drop_parent_authority(tmp_path,monkeypatch):
 root,h,xs=packet(tmp_path,monkeypatch);a,ah,_,_=answer_packet(tmp_path,xs,40)
 result=s.select(a,ah,root,h,tmp_path/'selection',tokenizer=FixtureTok())
 main=tmp_path/'selection/main';p=read(main/'SCREEN_SELECTION_SEAL.json');p['screen_scope_authority']='unregistered'
 write(main/'SCREEN_SELECTION_SEAL.json',p)
 seal=read(main/'INPUT_SEAL.json');seal['files']['SCREEN_SELECTION_SEAL.json']=sha(main/'SCREEN_SELECTION_SEAL.json');write(main/'INPUT_SEAL.json',seal)
 with pytest.raises(ValueError):r.load(main,sha(main/'INPUT_SEAL.json'),'main')
