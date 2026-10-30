"""Value-free diagnostics for the unchanged exact serialized-output parity gate."""
import hashlib
import json
from contract import require,write
EOS_IDS=set()


def check_outputs(batched,serial,path,ids,batch_size):
    require(len(batched)==len(serial)==len(ids)>0,'parity coverage')
    encode=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()
    rows=[]
    for ident,a,b in zip(ids,batched,serial):
        require(set(a)==set(b)=={'raw','token_ids'},'E81 output schema unchanged')
        at,bt=a['token_ids'],b['token_ids']
        divergence=next((i for i,(x,y) in enumerate(zip(at,bt)) if x!=y),None)
        if divergence is None and len(at)!=len(bt):divergence=min(len(at),len(bt))
        rows.append(dict(id=ident,equal=encode(a)==encode(b),
            batched_sha256=hashlib.sha256(encode(a)).hexdigest(),serial_sha256=hashlib.sha256(encode(b)).hexdigest(),
            raw_text_equal=a['raw']==b['raw'],token_ids_equal=at==bt,
            batched_token_length=len(at),serial_token_length=len(bt),
            batched_text_utf8_length=len(a['raw'].encode()),serial_text_utf8_length=len(b['raw'].encode()),
            first_token_divergence=divergence,divergence_index_base=0,
            batched_terminal_eos=bool(at and at[-1] in EOS_IDS) if EOS_IDS else None,
            serial_terminal_eos=bool(bt and bt[-1] in EOS_IDS) if EOS_IDS else None))
    passed=all(r['equal'] for r in rows)
    # Persist before raising; no generated text or token values are published.
    write(path,dict(status='PASS' if passed else 'FAIL',n=len(rows),production_batch_size=batch_size,
        exact_serialized_output=True,generated_values_included=False,records=rows))
    require(passed,'batched greedy differs from serial greedy; no production continuation')
