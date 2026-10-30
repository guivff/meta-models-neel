"""Operational batching and byte-parity gate; no prompt or decoding changes."""
import hashlib
import json

def left_padded(sequences, pad, device):
    import torch
    if not sequences or any(not x for x in sequences):
        raise ValueError('nonempty token sequences required')
    width=max(map(len,sequences))
    ids=torch.full((len(sequences),width),pad,dtype=torch.long,device=device)
    mask=torch.zeros_like(ids)
    for row,seq in enumerate(sequences):
        ids[row,-len(seq):]=torch.tensor(seq,dtype=torch.long,device=device)
        mask[row,-len(seq):]=1
    return ids,mask

def generated_tokens(row, eos):
    """Remove only batch fill AFTER the first generated terminal token."""
    ids=row.tolist() if hasattr(row,'tolist') else list(row)
    stops=set(eos if isinstance(eos,(list,tuple,set)) else [eos])-{None}
    for i,token in enumerate(ids):
        if token in stops:
            return ids[:i+1]
    return ids

def byte_parity(call, eight, batch_size):
    """Eight synthetic items, serial vs full batch; outputs discarded after hashing."""
    if len(eight)!=8 or batch_size<32 or batch_size%8:
        raise ValueError('eight parity items and a full batch>=32 divisible by8')
    serial=[call([x])[0] for x in eight]
    batched=call(list(eight)*(batch_size//8))
    if len(batched)!=batch_size:
        raise ValueError('parity batch cardinality')
    encode=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    if any(encode(value)!=encode(serial[i%8]) for i,value in enumerate(batched)):
        raise ValueError('BATCH_PARITY_FAILED: serial and batched greedy bytes differ')
    return dict(status='PASS',items=8,batch_size=batch_size,byte_identical=True,
                fingerprints=[hashlib.sha256(encode(x)).hexdigest() for x in serial],
                synthetic_only=True,scientific_readouts_written=0)
