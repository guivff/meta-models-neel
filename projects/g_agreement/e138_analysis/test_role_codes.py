import pytest
from .role_codes import normalize
from .run import expand
def code(values,category="states_value"):
 return dict(id="j",values=values,category=category,evidence="unchanged")
@pytest.mark.parametrize("values,expected", [(["A"],["recipient-old"]),(["B"],["donor-old"]),(["OTHER"],["other"]),(["B","A"],["recipient-old","donor-old"]),(["A","OTHER"],["recipient-old","other"])])
def test_values(values,expected):
 c=code(values);assert normalize(c,"KEPT","j",dict(A="recipient-old",B="donor-old",OTHER="other"))==expected;assert c==code(values)
@pytest.mark.parametrize("category",["silent","exhibits","names_property_without_value"])
def test_none(category):
 assert normalize(code([],category),"KEPT","j",dict(A="recipient-old",B="other"))==[]
def test_missing():
 assert normalize(None,"UNPARSEABLE","j",dict(A="recipient-old",B="other")) is None
 assert normalize(code([],"UNPARSEABLE"),"UNPARSEABLE","j",dict(A="recipient-old",B="other")) is None
@pytest.mark.parametrize("c,status,j,m",[(None,"KEPT","j",dict(A="recipient-old",B="other")),(code(["A"]),"KEPT","wrong",dict(A="recipient-old",B="other")),(code(["A","B"]),"KEPT","j",dict(A="other",B="other")),(code(["A"]),"UNPARSEABLE","j",dict(A="recipient-old",B="other")),(code([]),"KEPT","j",dict(A="recipient-old",B="other"))])
def test_reject(c,status,j,m):
 with pytest.raises((ValueError,AssertionError)):normalize(c,status,j,m)
def test_literal_transport():
 vals=dict(code=code(["B"]),status="KEPT",judgment_id="j",value_roles=dict(A="other",B="recipient-old"))
 refs={k:{"ref":k}for k in vals}
 assert expand({"e104_role_code":refs},vals.__getitem__)==["recipient-old"]
 refs["status"]="KEPT"
 with pytest.raises((ValueError,AssertionError)):expand({"e104_role_code":refs},vals.__getitem__)
