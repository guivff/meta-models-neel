"""CPU-only original-source identity join; never evaluates or copies pair scores."""
import hashlib,json


def input_key(x):
    fields=[x['row'],x['ids'],x['read_index'],x['candidate_ids']]
    return hashlib.sha256(json.dumps(fields,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def match_inputs(targets,clean):
    """Unique byte-equivalent unpatched native inputs; never an order/label join."""
    by={}
    for source in clean:
        if source['condition']!='0' or source['vector_index'] is not None or source['donor_id'] is not None:
            raise ValueError('true E105 unpatched0 input required')
        key=input_key(source)
        if key in by:raise ValueError('ambiguous original clean input')
        by[key]=source
    result=[];seen=set()
    for target in targets:
        if target['id']in seen:raise ValueError('duplicate target identity')
        seen.add(target['id']);source=by.get(input_key(target))
        if source is None:raise ValueError('no exact original prompt/read-site/ordered-candidate match')
        # Explicit checks retained alongside the digest; no hash-only identity assertion.
        if any(target[k]!=source[k]for k in ('row','ids','read_index','candidate_ids')):
            raise ValueError('input hash collision or unequal original bytes')
        result.append((target,source))
    return result
