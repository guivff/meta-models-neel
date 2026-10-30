"""Frozen E103 claim/continuation call. Verdict labels are never inputs."""
import json
QUESTION = "Here is a claim and 8 continuations of the same text. Does any continuation assert or imply the claim's content? Answer yes or no."
def render(claim, continuations):
    if not isinstance(claim,str) or not claim.strip():raise ValueError('nonempty claim required')
    if len(continuations)!=8 or not all(isinstance(x,str) for x in continuations):raise ValueError('exactly eight text continuations required')
    return QUESTION + '\n\n' + json.dumps({'claim':claim,'continuations':continuations},ensure_ascii=False)
def parse(response):
    value=response.strip().casefold()
    if value not in ('yes','no'):raise ValueError('unparseable: expected yes or no')
    return value=='yes'
