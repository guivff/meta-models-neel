"""Read-only E66 helper: public readouts and judge codes, no private map exposed.

Run with python -B. GLM only; this is not a Qwen or paired-reader bank.
"""
import json
from pathlib import Path
from evidence_e67 import WORK, read, digest, verified_read

def load_e66():
    base=WORK/'wt-wtext/results/g_agreement/understand/e66'
    analysis=read(base/'analysis183_once_2026-10-27/ANALYSIS_SEAL.json')
    assert analysis['status']=='SEALED'
    result=verified_read(base/'analysis183_once_2026-10-27/RESULTS.json',analysis['results_sha256'])
    spec=read(base/'ANALYSIS_SPEC.json')
    js=verified_read(spec['judgment_seal'],result['judgment_seal_sha256'])
    assert digest(spec['judgments'])==analysis['judgments_sha256']==js['judgments_sha256']
    judgments={x['id']:x for x in map(json.loads,Path(spec['judgments']).read_text().splitlines())}
    packet=Path(spec['private_map']).parent/'BLIND_PACKET.jsonl'
    assert digest(packet)==spec['packet_sha256']==js['packet_sha256']
    records=list(map(json.loads,packet.read_text().splitlines()))
    # Return the already-public blind packet and blind judgment only.
    return [dict(packet=x,judgment=judgments[x['id']]) for x in records]
