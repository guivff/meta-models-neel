import hashlib,json
import pytest
from .sources import SealedJSON,join_cue_rows

def test_open_choice_uses_all_category_names_and_registered_aliases():
 from .sources import open_choice_rows
 cohort=[dict(id=str(i),choice='Alpha',ground_truth_ref={'original':'synthetic'},arm='immediate') for i in range(376)]
 cats={str(i):'synthetic' for i in range(376)}
 catalog={'synthetic':[dict(member='Alpha',registered_aliases=['first']),dict(member='Beta',registered_aliases=[])]}
 texts={(str(i),b):('first and Beta' if b==60 else 'FIRST' if b==52 else 'alphabet') for i in range(376) for b in (44,52,60)}
 refs={k:{'original':'synthetic'} for k in texts}
 rows=open_choice_rows(cohort,cats,catalog,texts,refs)
 assert rows[0]['readings']=={44:None,52:'Alpha',60:None}
 assert set(rows[0]['matcher_matches'][60])=={'Alpha','Beta'}
 del texts['0',60]
 with pytest.raises(ValueError):open_choice_rows(cohort,cats,catalog,texts,refs)

def test_classified_unhooked_join_preserves_orientation_and_text_priority():
 from .sources import classified_unhooked_truth
 cs=[dict(id=f'e{i}:unhooked',base_id=f'e{i}',condition='unhooked',text_value='new' if i==0 else 'neither',pair_value='old' if i<2 else 'tie') for i in range(84)]
 labs=[dict(base_id=f'l{i}',original_base_id=f'o{i}',old_value='before',new_value='after') for i in range(84)]
 inv=[dict(item_id=f'o{i}',old_value='B') for i in range(84)]
 mapping={f'e{i}':f'l{i}' for i in range(84)}
 result=classified_unhooked_truth(cs,labs,mapping,inv)
 assert result['o0']['truth']=='A' and result['o1']['truth']=='B'
 assert result['o2']['truth'] is None
 with pytest.raises(ValueError):classified_unhooked_truth(cs[:-1],labs,mapping,inv)
 cs[1]['base_id']='e0'
 with pytest.raises(ValueError):classified_unhooked_truth(cs,labs,mapping,inv)

def test_sealed_json_pointer_hash_and_json_only(tmp_path):
 def save(name,value):
  p=tmp_path/name;p.write_text(json.dumps(value));return str(p),hashlib.sha256(p.read_bytes()).hexdigest()
 p,h=save('rows.json',[{'code':{'values':['A','B']}}])
 sp,sh=save('seal.json',{'files':{'rows.json':h}})
 r=SealedJSON();sources=[dict(seal=sp,sha256=sh)]
 assert r.pointer(sources,dict(seal_index=0,member='rows.json',keys=[0,'code','values']))==['A','B']
 assert len(r.pins)==2
 with pytest.raises(ValueError):r.member(sp,sh,'../rows.json')
 with pytest.raises(ValueError):r.pointer(sources,dict(seal_index=True,member='rows.json',keys=[]))
 (tmp_path/'rows.json').write_text('[]')
 with pytest.raises(ValueError):r.member(sp,sh,'rows.json')
 with pytest.raises(ValueError):r.read(tmp_path/'array.npy','unused')

def test_cue_join_retains_untold_and_missing_without_negative_assertions():
 labels=[dict(public_id=str(i),split='test',addressed=i%2) for i in range(400)]
 cell=lambda flag:dict(mention=flag,source_ref={'original':'synthetic-only'})
 a={str(i):cell(False) for i in range(400)}
 late={(str(i),b):cell(True if b==52 else None) for i in range(400) for b in (52,60)}
 rows=join_cue_rows(labels,a,late)
 assert len(rows)==400 and sum(x['accuracy_eligible'] for x in rows)==200
 assert all(x['readings']=={44:None,52:'told',60:None} for x in rows)
 assert rows[0]['truth']=='not_told' and rows[1]['truth']=='told'
 del late['0',60]
 with pytest.raises(ValueError):join_cue_rows(labels,a,late)
