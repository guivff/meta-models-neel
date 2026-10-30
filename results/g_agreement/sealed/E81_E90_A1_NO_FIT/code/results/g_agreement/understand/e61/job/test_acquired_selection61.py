from acquired_selection61 import select_d2

def unit(k):return [dict(unit_id=k,reader=r,repeat=i,text='irrelevant') for r in ('oracle','nla') for i in range(1)]

def test_intersection_and_content_independence():
    a=[];b=[]
    for i in range(5):
        a+=unit(f'linewrap_implicit:{i}')+unit(f'linewrap_asked:{i}')
        if i:a_key=f'count_gradient_first_letter:{i}';b+=unit(a_key)
    s=select_d2(a,b)
    assert s['implicit_ids'][0]=='linewrap_implicit:1'
    assert 'linewrap_implicit:0' not in s['eligible_implicit_ids']
    assert all(k.split(':',1)[1]==v.split(':',1)[1] for k,v in zip(s['implicit_ids'],s['first_letter_ids']))
    for x in a+b:x['text']='changed outcome'
    assert select_d2(a,b)==s
