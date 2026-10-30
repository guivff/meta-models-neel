"""§221.1 only: versioned corrections; original validators remain immutable."""
import string
import unicodedata
from .e87 import validate_code as strict_e87
from projects.g_agreement.readerbench.scoring import require


def e87_code(item,code):
    corrected=dict(code)
    if corrected.get('category')=='silent':
        # Ignore only this field. Identity, empty evidence/values and every other
        # original validation requirement still run through the strict validator.
        corrected['first_position']=None
    strict_e87(item,corrected)
    return corrected


def e87_classify(items,response):
    codes=response.get('records',[]) if isinstance(response,dict) else []
    if type(codes) is not list:codes=[]
    result=[]
    for item in items:
        found=[c for c in codes if isinstance(c,dict) and c.get('id')==item['id']]
        try:
            require(len(found)==1,'one result per ID')
            result.append(dict(id=item['id'],status='KEPT',code=e87_code(item,found[0])))
        except (ValueError,TypeError,KeyError):result.append(dict(id=item['id'],status='INVALID',code=None))
    return result


def punctuation(char):
    return char in string.punctuation or unicodedata.category(char).startswith('P')


def e103_parse(text):
    require(isinstance(text,str),'text yes/no response')
    start,end=0,len(text)
    while start<end and (text[start].isspace() or punctuation(text[start])):start+=1
    while end>start and (text[end-1].isspace() or punctuation(text[end-1])):end-=1
    value=text[start:end].casefold()
    require(value in ('yes','no'),'expected yes/no after surrounding whitespace/punctuation only')
    return value
