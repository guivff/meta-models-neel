"""CPU-only, lossless AO literal-marker rendering and exhaustive audit."""
from __future__ import annotations
import hashlib
import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from projects.g_agreement.r_bench import rd_pretext as P

RUN_ID = 'rd-ao-render-'+uuid.uuid4().hex
TOKENIZER_REVISION = '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'


def carrier(reader, layer, question):
    from projects.r_gemma import gemma as GM
    tok = reader.target.tokenizer
    prefix = reader.prefix(layer)
    prefix_ids, _ = GM.chat_ids(tok, prefix)
    slots = [i for i, value in enumerate(prefix_ids) if value == reader.special_id]
    if len(slots) != 1:
        raise RuntimeError('AO structural prefix: expected exactly one special token')
    slot = slots[0]
    head, _ = GM.chat_ids(tok, prefix + question)
    if head[:slot+1] != prefix_ids[:slot+1]:
        raise RuntimeError('AO structural injection prefix changed')
    # The native marker is ordinary Qwen token 907, decoded as space + '?'.
    # Literal occurrences in the question must not be activation slots.
    extra = [i for i, value in enumerate(head) if value == reader.special_id and i != slot]
    if not extra:
        return reader.carrier(layer, question)  # byte-identical native path
    decode = lambda ids: tok.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
    if decode([reader.special_id]) != ' ?':
        raise RuntimeError('AO literal-marker repair requires exact space-question marker')
    replacement = GM.encode(tok, ' ') + GM.encode(tok, '?')
    if reader.special_id in replacement or decode(replacement) != ' ?':
        raise RuntimeError('AO literal-marker replacement is not safe/lossless')
    fixed = []
    for i, value in enumerate(head):
        fixed.extend(replacement if i in extra else [value])
    if decode(fixed) != decode(head):
        raise RuntimeError('AO literal-marker repair changed visible text')
    positions = [i for i, value in enumerate(fixed) if value == reader.special_id]
    if positions != [slot]:
        raise RuntimeError('AO repaired carrier: expected exactly one special token at structural slot')
    return fixed, slot


def tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained('Qwen/Qwen3.6-27B', revision=TOKENIZER_REVISION, local_files_only=True)


def audit(bank, windows, tok=None, *, run_kind='test'):
    from projects.r_panel import setup
    setup.activate('Q27')
    from projects.r_gemma.oracle import AOReader
    from projects.r_gemma import config as G, gemma as GM
    from projects.g_agreement.r_bench.rd_pretext_finalize import validate_windows
    from projects.g_agreement.r_bench.rd_pretext_readers import reader_view
    validate_windows(bank, windows)
    tok = tokenizer() if tok is None else tok
    reader = AOReader(); reader.target = SimpleNamespace(tokenizer=tok)
    marker = GM.encode(tok, G.AO_SPECIAL)
    if len(marker) != 1: raise RuntimeError('AO marker must encode to exactly one token')
    reader.special_id = marker[0]
    items = {item['id']:item for item in bank['items']}
    checked, missing, repaired = [], [], []
    for window in windows:
        key = {k:window[k] for k in ('id','prefilled','position')}
        if not window['available']:
            missing.append(key | {'reason':window['reason']}); continue
        item = items[window['id']]
        question = reader.fc_question(reader_view(item | window)['visible_text'], *P.AO_CHOICES)
        native, _ = GM.chat_ids(tok, reader.prefix(32) + question)
        try:
            fixed, slot = carrier(reader, 32, question)
        except (RuntimeError, ValueError) as error:
            raise RuntimeError('invalid AO render '+str(key)+': '+str(error)) from error
        if native != fixed:
            try: reader.carrier(32, question)
            except RuntimeError as error: old_error = str(error)
            else: raise RuntimeError('unexpected change to a valid native carrier: '+str(key))
            repaired.append(key | {'split':item['split'], 'old_error':old_error})
        elif native.count(reader.special_id) != 1:
            raise RuntimeError('unrepaired AO marker collision: '+str(key))
        checked.append(key | {'head_sha256':P.digest(fixed),'marker_index':slot})
    provenance = {'run_id':RUN_ID,'run_kind':run_kind,'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for row in checked + missing + repaired: row.update(provenance)
    return provenance | {'status':'PASS','tokenizer_revision':TOKENIZER_REVISION,'marker_id':reader.special_id,
            'bank_sha256':bank['bank_sha256'],'windows_checked':len(checked),'missing_windows':missing,
            'items_checked':len({r['id'] for r in checked}),'literal_repairs':repaired,
            'unchanged_carriers':len(checked)-len(repaired),'carrier_manifest_sha256':P.digest([{k:v for k,v in row.items() if k not in provenance} for row in checked]),
            'all_decoded_text_preserved':True,'excluded_items':[], 'checked':checked}


def main():
    import argparse, uuid
    from projects.g_agreement.r_bench.rd_pretext_items import load_bank
    p=argparse.ArgumentParser();p.add_argument('--bank',type=Path,required=True);p.add_argument('--windows',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=audit(load_bank(a.bank),[json.loads(line) for line in a.windows.read_text().splitlines() if line.strip()])
    result.update(run_id=RUN_ID,run_kind='test',code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),diagnostic_only=True,windows_file_sha256=hashlib.sha256(a.windows.read_bytes()).hexdigest())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f: json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:result[k] for k in ('status','items_checked','windows_checked','unchanged_carriers','carrier_manifest_sha256')}))

if __name__=='__main__': main()
