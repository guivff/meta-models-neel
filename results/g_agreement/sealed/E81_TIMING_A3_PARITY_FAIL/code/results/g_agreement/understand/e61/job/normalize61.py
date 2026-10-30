"""Normalize frozen W-text records without tokenizing, mutating, or building a bank."""
from runtime61 import require,position_jobs

def normalize(d3,d4):
    require(len(d3)==24 and len({x['pair_id'] for x in d3})==12,'D3 twelve paired prompts')
    require(len(d4)==252 and len({x['base_item_id'] for x in d4})==84,'D4 eighty-four matched three-arm items')
    out=[]
    for x in d3:
        start=x['instruction_end_token_index'];end=len(x['ids'])-1
        require(x['read_token_indices']==list(range(start,end+1)) and x['read_span_inclusive'] is True,'every frozen D3 position')
        out.append(dict(x,display='D3',arm=x['value'],instruction_end_index=start,pre_answer_index=end))
    for x in d4:
        require(x['answer_token_boundary_stable'] is True,'completion answer boundary')
        # Capture the dedicated prefix: encoding the full prompt may merge its boundary token.
        out.append(dict(x,display='D4',pair_id=x['base_item_id'],ids=x['read_ids'],text=x['read_prefix'],read_index=x['read_token_index'],completion_text=x['completion_prompt'],answer_text=x['answer']))
    for pair in {x['pair_id'] for x in out if x['display']=='D3'}:
        require({x['arm'] for x in out if x['display']=='D3' and x['pair_id']==pair}=={'decline','answer'},'D3 arm grid')
    for pair in {x['pair_id'] for x in out if x['display']=='D4'}:
        require({x['arm'] for x in out if x['display']=='D4' and x['pair_id']==pair}=={'think','ignore','none'},'D4 arm grid')
    position_jobs(out)
    return out
