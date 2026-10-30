"""Freeze regexes and literal registered value words before any E76 readout exists."""
import ast,copy,re
from collections import defaultdict,Counter
from common76 import *

WTEXT=ROOT.parent/'wt-wtext'
MECH=ROOT.parent/'wt-wmech'


def assignment_literal(path,name):
    tree=ast.parse(Path(path).read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):return ast.literal_eval(node.value)
    raise ValueError('Frozen literal assignment missing')


def freeze():
    inv=read(HERE.parent/'e65/SOURCE_INVENTORY_V2_2026-10-27.json');rows={};pins={}
    def source(path):
        path=Path(path);pins[str(path)]=sha(path);return str(path)
    def missing(bank,row,reason,sources=()):rows[bank,row]={'bank':bank,'row':row,'status':'UNAVAILABLE','reason':reason,'families':[],'sources':list(sources)}
    def words(bank,row,values,path,weight=1):
        groups=[v if isinstance(v,list) else [v] for v in values]
        if not groups or any(not g or any(not isinstance(v,(str,int)) or str(v) in ('A','B','unlabelled') or '_' in str(v) for v in g) for g in groups):
            missing(bank,row,'No frozen human-readable value-word regex; canonical IDs are not substituted as words',[path]);return
        patterns=[r'(?<!\w)(?:'+'|'.join(re.escape(str(x)) for x in group)+r')(?!\w)' for group in groups]
        rows[bank,row]={'bank':bank,'row':row,'status':'AVAILABLE','sources':[path],
            'families':[{'patterns':patterns,'ignore_case':True,'policy':'whole_word_or_frozen_regex','weight':weight,
                         'derivation':'Literal frozen value words, whole-word case-insensitive; no added aliases or stemming'}]}
    for bank in ('W1','E36','W12','E49','E56','E57','E59'):
        for row in inv['sources'][bank]['rows']:missing(bank,row,'No frozen value regex located')
    for bank in ('W1','W12'):
        path=Path(inv['sources'][bank]['path']).parent/'templates.json';p=source(path);data=read(path)
        for row,d in data.items():words(bank,row,d['values'],p)
    path=HERE.parent/'e36/ROW_DEFINITIONS.json';p=source(path)
    for row,d in read(path)['rows'].items():words('E36',row,d['values'],p)
    # Preserve the exact prospective sentence-local negation detector for these rows.
    path=ROOT/'projects/g_agreement/understand/e24_statements.py';p=source(path);patterns=assignment_literal(path,'PATTERNS');neg=assignment_literal(path,'NEGATION')
    for bank in ('W1','E36'):
        for row,pair in patterns.items():
            if (bank,row) in rows:rows[bank,row]={'bank':bank,'row':row,'status':'AVAILABLE','sources':[p],
                'families':[{'patterns':list(pair),'ignore_case':True,'policy':'sentence_negation','negation':neg,'weight':1,'derivation':'Exact frozen E24 statement regex and sentence-local negation policy'}]}
    path=MECH/'results/g_agreement/understand/e49/job/statements49.py';p=source(path)
    for row,pair in assignment_literal(path,'PATTERNS').items():rows['E49',row]={'bank':'E49','row':row,'status':'AVAILABLE','sources':[p],
        'families':[{'patterns':list(pair),'ignore_case':True,'policy':'sentence_negation','negation':neg,'weight':1,'derivation':'Exact frozen E49 extension of E24'}]}
    path=HERE.parent/'e54/CHANNEL_DEFINITIONS.json';p=source(path)
    for row,d in read(path).items():rows['E54',row]={'bank':'E54','row':row,'status':'AVAILABLE','sources':[p],
        'families':[{'patterns':[d['mention_patterns'][v] for v in d['values']],'ignore_case':True,'policy':'whole_word_or_frozen_regex','weight':1,'derivation':'Exact frozen E54 mention patterns'}]}
    path=HERE.parent/'e56/ROW_DEFINITIONS.json';p=source(path)
    for row,d in read(path)['rows'].items():words('E56',row,d['values'],p)
    path=WTEXT/'results/g_agreement/understand/e57/cache/bank_2026-10-27_v1/DEFINITIONS.json';p=source(path);defs=read(path)
    for row,d in defs.items():words('E57',row,d.get('spec',d)['values'],p)
    path=WTEXT/'results/g_agreement/understand/e57/cache/bank_2026-10-27_v1/items.PRIVATE.json';pitems=source(path);items={x['id']:x for x in read(path) if x['split']=='test'}
    path=WTEXT/'results/g_agreement/understand/e57/cache/bank_2026-10-27_v1/ANNOTATIONS.PRIVATE.json';p=source(path);ann=read(path)
    for row in ('antonym_crosslingual','multi_token_entity','page_range_digit','two_hop_answer'):
        families=Counter()
        for key,x in items.items():
            if x['feature']!=row:continue
            a=ann[key];values=a.get('value_words',a.get('answer_pair'));require(values is not None,'Frozen item value-word family missing')
            groups=tuple(tuple(v) if isinstance(v,list) else (v,) for v in values);families[groups]+=1
        result=[]
        for groups,n in sorted(families.items()):
            words('E57',row,[list(v) for v in groups],p,n);result.extend(rows['E57',row]['families'])
        rows['E57',row]['families']=result;rows['E57',row]['sources']=[p,pitems]
    for row in ('capacity_list','category_switch'):missing('E57',row,'Registered count measure has no fixed A/B value regex; no invented lexical surrogate')
    path=MECH/'cache/g_agreement/understand/e61/inputs_v2_label_free/LEXICON.json';p=source(path);lex=read(path)
    for row in ('focus_think','focus_ignore','focus_mention','focus_none'):words('E57',row,[lex['birds'],lex['citrus']],p)
    for row in ('think','ignore','none'):words('E61_D4',row,[lex['birds'],lex['citrus']],p)
    words('E61_D3','plan',[lex['decline'],lex['answer']],p)
    path=WTEXT/'results/g_agreement/understand/e59/cache/bank_2026-10-27_v1/VALIDATION.json';p=source(path)
    for row,d in read(path).items():words('E59',row,d['registered_reader_value_words'],p)
    path=WTEXT/'results/g_agreement/understand/e62/cache/bank_2026-10-27_v1/items.PRIVATE.json';pitems=source(path);rungs=read(path)
    for x in rungs:
        key='E62',x['feature']
        if key in rows:continue
        if x['state']=='S6':missing(*key,'Evaluation-awareness cue is not a binary value regex',[pitems]);continue
        original=rows[x['source_bank'],x['source_feature']];copyrow=copy.deepcopy(original);copyrow.update(bank='E62',row=x['feature'])
        copyrow['sources'].append(pitems);rows[key]=copyrow
    for row in rows.values():
        for family in row['families']:
            for pattern in family['patterns']:re.compile(pattern,re.I if family['ignore_case'] else 0)
    dump(HERE/'REGEX_CATALOG.json',{'experiment':'E76','status':'FROZEN_BEFORE_E76_READOUTS','rows':[rows[k] for k in sorted(rows)],
        'source_sha256':pins,'lexical_policy':'Reuse existing frozen regex and policies; otherwise literal frozen human-readable value words only. Canonical IDs without readable word sets and non-value count/eval rows are explicitly unavailable.',
        'future_banks':'Separate prospective catalog version before their E76 floor is scored; current catalog never retuned to pool output'})
    print(__import__('json').dumps({'rows':len(rows),'available':sum(r['status']=='AVAILABLE' for r in rows.values()),'unavailable':sum(r['status']!='AVAILABLE' for r in rows.values())}))


if __name__=='__main__':freeze()
