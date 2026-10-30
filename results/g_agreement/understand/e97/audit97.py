"""Pre-capture v2 definition inventory and v1 preservation checks; no outcomes."""
import ast
import hashlib
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def source_inventory():
    entries=[]
    for base in ('projects/g_agreement','results/g_agreement/understand'):
        for p in sorted((REPO/base).rglob('*.py')):
            if any(x in p.parts for x in ('cache','tests','__pycache__','superseded','e97')) or p.name.startswith('test') or p.name=='w1_templates.py':continue
            try:tree=ast.parse(p.read_text())
            except (SyntaxError,UnicodeError):continue
            for n in tree.body:
                if not isinstance(n,(ast.Assign,ast.AnnAssign)):continue
                ts=n.targets if isinstance(n,ast.Assign) else [n.target]
                names=[x.id for x in ts if isinstance(x,ast.Name)]
                if not any(re.fullmatch(r'(?:ALL_)?FEATURES|MODES|DEFS|ROWS|SPEC|SPECS|STATES|COUNTERS|DESCRIPTIONS|NATURAL_PAIRS|LEXICONS|CLOSED_CLASSES|PROPERTIES|ROW_.*',x) for x in names):continue
                strings=[v.value for v in ast.walk(n.value) if isinstance(v,ast.Constant) and isinstance(v.value,str)]
                keys=[k.value for k in n.value.keys if isinstance(k,ast.Constant) and isinstance(k.value,str)] if isinstance(n.value,ast.Dict) else []
                if strings:entries.append(dict(source=str(p.relative_to(REPO)),source_sha256=sha(p),line=n.lineno,assignments=names,keys=keys,strings=strings))
    for p in sorted((REPO/'results/g_agreement/understand').rglob('*DEFINITIONS.json')):
        if any(x in p.parts for x in ('cache','superseded','e97')):continue
        data=json.loads(p.read_text())
        entries.append(dict(source=str(p.relative_to(REPO)),source_sha256=sha(p),definition_packet=data))
    return entries

def preservation():
    old=ROOT/'superseded/v1_before_capture'
    seal=json.loads((old/'BANK_SEAL.json').read_text())
    for n,h in seal['files'].items():assert sha(old/n)==h,n
    a=json.loads((old/'ROW_LIST.json').read_text())['rows'];b=json.loads((ROOT/'ROW_LIST.json').read_text())['rows']
    a={r['row']:r for r in a};b={r['row']:r for r in b}
    assert set(a)-set(b)=={'register_plan'} and set(b)-set(a)=={'calendar_system_plan'}
    assert all(a[r]==b[r] for r in set(a)&set(b))
    prior=ROOT/'cache/bank_2026-10-28';new=ROOT/'cache/bank_2026-10-28_v2'
    oa=[json.loads(l) for l in (prior/'PRIVATE_LABELS.jsonl').read_text().splitlines()]
    ob=[json.loads(l) for l in (new/'PRIVATE_LABELS.jsonl').read_text().splitlines()]
    keep={x['item_id'] for x in oa if x['row']!='register_plan'}
    assert len(keep)==6552
    for file in ('PRIVATE_LABELS.jsonl','PUBLIC_ITEMS.jsonl'):
        left={json.loads(l)['item_id']:l for l in (prior/file).read_text().splitlines()}
        right={json.loads(l)['item_id']:l for l in (new/file).read_text().splitlines()}
        assert all(left[k]==right[k] for k in keep),file
        assert len(set(left)-set(right))==168 and len(set(right)-set(left))==168
    return dict(original_seal_sha256=sha(old/'BANK_SEAL.json'),unchanged_rows=39,unchanged_items=6552,
                removed_row='register_plan',added_row='calendar_system_plan',removed_items=168,added_items=168,
                row_definitions_taxonomy_regex_and_all_other_items='byte-identical for the 39 retained rows',
                original_cache_preserved=str(prior),revised_cache=str(new))
if __name__=='__main__':
    inventory=source_inventory();p=ROOT/'cache/novelty_source_inventory_v2.json';dump(p,inventory)
    receipt=preservation();dump(ROOT/'REVISION_RECEIPT.json',receipt)
    print(json.dumps(dict(definition_sources=len({e['source'] for e in inventory}),definition_blocks=len(inventory),**receipt)))
