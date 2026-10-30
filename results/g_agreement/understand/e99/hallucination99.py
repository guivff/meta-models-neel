"""Exact pinned v5c-chat and verification formatting; k=1, CPU only."""
import json
from pathlib import Path
C=json.loads(Path(__file__).with_name('HALLUCINATION_PROMPTS.json').read_text())['constants']
def render(item,site,readout,*,wrong_spans=None):
    response=item['response'];at=max(0,min(int(site['char']),len(response)))
    marked=response[:at]+C['READ_MARK']+response[at:]
    sample=f'<readout idx="0">\n{readout}\n</readout>'
    values=dict(prompt=item['prompt'],mark=C['READ_MARK'],marked_response=marked,k=1,samples_block=sample)
    if wrong_spans is None:
        values['facts_block']='';stage='JUDGE'
    else:
        falses='\n'.join('  - '+json.dumps(x,ensure_ascii=False) for x in wrong_spans) or '  (none)'
        values['samples_block']=sample+'\nEstablished FALSE spans of readout 0:\n'+falses;stage='VERIFY'
    return dict(system=C[stage+'_SYSTEM'],user=C[stage+'_USER'].format(**values),schema=C[stage+'_SCHEMA'])
