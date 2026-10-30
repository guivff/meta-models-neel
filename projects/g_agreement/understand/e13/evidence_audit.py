"""Seeded verbatim audit and evidence-string proxies; no code revisions."""
import argparse
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from . import io as I, protocol as P

RULES = I.OUT/'EVIDENCE_AUDIT_RULES.json'
# Explicit token references, or a bare quoted/unquoted single lexeme, are echo-compatible.
TOKEN_REFERENCE = r'\btokens?\b|\b(?:final|last|current|target|input|source|original)\s+(?:words?|characters?|numbers?)\b'
BARE_LEXEME = r'(?:[+-]?(?:\d[\d,]*(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[^\W\d_]\w*|[^\w\s])'
STRIP_CHARS = ' \t\r\n\x22\x27`“”‘’'


def classify(evidence, property_pattern):
    property_named = bool(re.search(property_pattern, evidence, re.I))
    token_reference = bool(re.search(TOKEN_REFERENCE, evidence, re.I))
    bare_lexeme = bool(re.fullmatch(BARE_LEXEME, evidence.strip(STRIP_CHARS))) and not property_named
    token_like = token_reference or bare_lexeme
    bucket = 'both' if property_named and token_like else 'property_name_only' if property_named else 'token_like_only' if token_like else 'neither'
    return dict(bucket=bucket, property_named=property_named, token_like=token_like,
                explicit_token_reference=token_reference, bare_lexeme=bare_lexeme)


def freeze():
    obj=dict(at=datetime.now(timezone.utc).isoformat(),status='DESCRIPTIVE_RULE_FIXED_BEFORE_EVIDENCE_CLASSIFICATION',seed=I.SEED,
             selection='For each eligible group, sort opaque IDs by rank(seed, e13-evidence-audit-v1, group, id); first5; no replacement or curation.',
             groups={'a':'section84 NLA codes with mentions=true','b':'section84 Oracle codes with enacts=true','c':'W1 NLA table_column codes with mentions=true'},
             evidence_input='Coder evidence string only; no truth or label-key fields used to select/classify. Row property regex is assigned by exact blind question, before key join.',
             property_patterns=I.read(I.OUT/'KEYWORDS_S84.json')['patterns'],w1_property_patterns={f:v['keyword'] for f,v in P.QUESTIONS.items()},
             token_reference=TOKEN_REFERENCE,bare_lexeme=BARE_LEXEME,strip_chars=STRIP_CHARS,
             classification='property-name flag: unchanged frozen row regex on evidence. Echo-compatible flag: explicit token/word/character reference OR whole evidence is one lexeme (numeric, word, punctuation), excluding a bare property-name match. Four exclusive buckets retain overlap: token_like_only, property_name_only, both, neither.',
             interpretation='Keyword proxies only. Property-name presence does not prove an assertion or correct value. Token-like is compatible with quoting/echoing, not proof of equality to the original source token. No attempt to infer actual source-token equality. Both/neither are not forced into a binary category.',
             count_scope='Each section84 row and native reader: all15records, and separately originally coded mentions and enacts. No recoding of the sealed Claude annotations. W1 table row also summarized for context.',
             code_sha256=I.sha(Path(__file__)))
    I.save(RULES,obj)
    (I.OUT/'EVIDENCE_AUDIT_SCOPE.md').write_text('# E13(b): descriptive evidence audit\n\nDated '+obj['at']+', before this evidence classification or example selection. Guiv requests five seeded verbatim examples each of section84 NLA mentions, section84 Oracle enactments, and W1 NLA table-column mentions. Seed20261024; opaque-ID hash ranking fixes selection with no outcome/evidence curation.\n\nExact rules in EVIDENCE_AUDIT_RULES.json. Evidence-only matching is done before loading the private keys. The frozen row property names supply the property flag; token-reference and bare-lexeme patterns supply an echo-compatible flag. Four mutually exclusive buckets preserve both and neither rather than assert a false binary. These are surface proxies, not new mention/enact labels. No truth, correctness or true-token content is consulted for classification. Then join keys only to report row/reader and true A/B for the chosen examples. Publish full unchanged readout and coder evidence for all15 examples; this is an unblinded audit artifact and must not be sent to a fresh blind coder. Old codes, metrics and seals remain unchanged. No API/GPU work.\n')
    print('Evidence rules and selection fixed')


def run():
    plan=I.read(RULES)
    if I.sha(Path(__file__)) != plan['code_sha256']:
        raise ValueError('evidence code changed')
    rel=str(RULES.relative_to(I.ROOT))
    if subprocess.check_output(['git','show','HEAD:'+rel],cwd=I.ROOT) != RULES.read_bytes():
        raise ValueError('rules not committed')
    verify=I.read(I.OUT/'CLAUDE_PREJOIN_VERIFICATION.json');receipt=I.read(I.OUT/'CLAUDE_SAMPLES_RECEIPT.json')
    if I.sha(I.CACHE/'claude_codes/CLAUDE_CODES_SEAL.json')!=verify['codes_seal_sha256']:
        raise ValueError('coder seal changed')
    questions=I.read(I.OUT/'QUESTIONS_S84.json')
    question_feature={v['question']:f for f,v in questions.items()}
    question_feature.update({v['question']:f for f,v in P.QUESTIONS.items()})
    classified=[]
    for scope in ['w1','s84']:
        inp=Path(receipt[scope]['sample']);cp=I.CACHE/'claude_codes'/f'{scope}.CLAUDE_CODES.jsonl'
        if I.sha(inp)!=verify['samples'][scope]['input_sha256'] or I.sha(cp)!=verify['samples'][scope]['codes_sha256']:
            raise ValueError('blind input/code changed')
        sample={r['id']:r for r in I.rows(inp)}
        patterns=plan['property_patterns'] if scope=='s84' else plan['w1_property_patterns']
        for code in I.rows(cp):
            source=sample[code['id']];feature=question_feature[source['question']]
            if code['evidence'] and code['evidence'] not in source['readout']:
                raise ValueError('nonverbatim evidence')
            classified.append(dict(scope=scope,feature=feature,**code,readout=source['readout'],question=source['question'],
                                   evidence_class=classify(code['evidence'],patterns[feature])))
    # Seal these truth-blind classifications before loading any keys.
    ledger=I.CACHE/'evidence_audit'/'classifications.before_key.jsonl'
    ledger.parent.mkdir(parents=True,exist_ok=True)
    I.jsonl(ledger,[{k:v for k,v in r.items() if k not in ['readout','question']} for r in classified])
    I.save(I.OUT/'EVIDENCE_CLASSIFICATION_SEAL.json',dict(at=datetime.now(timezone.utc).isoformat(),status='EVIDENCE_FLAGS_SEALED_BEFORE_TRUTH_JOIN',
              file_cache_only=str(ledger),sha256=I.sha(ledger),rules_sha256=I.sha(RULES),records=600))
    for scope in ['w1','s84']:
        kp=Path(receipt[scope]['key_cache_only'])
        if I.sha(kp)!=receipt[scope]['key_sha256']:raise ValueError('key changed')
        keys={r['id']:r for r in I.rows(kp)}
        for r in [x for x in classified if x['scope']==scope]:
            k=keys[r['id']]
            if k['feature']!=r['feature']:raise ValueError('blind-question/key row disagreement')
            r.update(reader=k['reader'],layer=k['layer'],true_value=k['label'])
            values=P.QUESTIONS[r['feature']]['values'] if scope=='w1' else questions[r['feature']]['values']
            r['true_AB']='A' if k['label']==values[0] else 'B'
    selected=[]
    for group in ['a','b','c']:
        eligible=[r for r in classified if (group=='a' and r['scope']=='s84' and r['reader']=='nla' and r['mentions'])
                  or (group=='b' and r['scope']=='s84' and r['reader']=='oracle' and r['enacts'])
                  or (group=='c' and r['scope']=='w1' and r['feature']=='table_column' and r['reader']=='nla' and r['mentions'])]
        selected += [dict(group=group,**r) for r in sorted(eligible,key=lambda r:I.rank('e13-evidence-audit-v1',group,r['id']))[:5]]
    if len(selected)!=15:raise ValueError('insufficient examples')
    counts=[]
    buckets=['token_like_only','property_name_only','both','neither']
    for scope in ['s84','w1']:
        features=list(plan['property_patterns']) if scope=='s84' else ['table_column']
        for feature in features:
            for reader in ['oracle','nla']:
                rs=[r for r in classified if (r['scope'],r['feature'],r['reader'])==(scope,feature,reader)]
                for category in ['all','mentions','enacts']:
                    use=rs if category=='all' else [r for r in rs if r[category]]
                    c=Counter(r['evidence_class']['bucket'] for r in use)
                    counts.append(dict(scope=scope,feature=feature,reader=reader,layer=44 if reader=='oracle' else 42,category=category,n=len(use),**{b:c[b] for b in buckets}))
    I.save(I.OUT/'EVIDENCE_TYPE_COUNTS.json',dict(status='DESCRIPTIVE_EVIDENCE_STRING_PROXIES',counts=counts,rules_sha256=I.sha(RULES)))
    I.save(I.OUT/'SEEDED_VERBATIM_EXAMPLES.json',dict(status='UNBLINDED_AUDIT_DO_NOT_SEND_TO_BLIND_CODER',seed=I.SEED,examples=selected))
    lines=['# E13(b): descriptive evidence-type split','','Surface proxies, unchanged coder labels. Classifications use only coder evidence and the row question, sealed before truth join. “Property name” does not establish an assertion; “token-like” does not establish equality to the actual source token. Four buckets retain overlap/uncertainty. Counts are on the150-state/reader section84 Claude sample, not the full sealed bank.','','| Scope / row | Reader/site | Original code subset | n | Token-like only | Property-name only | Both | Neither |','|---|---|---|---:|---:|---:|---:|---:|']
    for r in counts:
        if r['category']=='all':continue
        lines.append(f"| {r['scope']} / {r['feature']} | {r['reader']} L{r['layer']} | {r['category']} | {r['n']} | {r['token_like_only']} | {r['property_name_only']} | {r['both']} | {r['neither']} |")
    lines+=['','All-record counts (including code-negative records) are preserved in EVIDENCE_TYPE_COUNTS.json. No re-estimation of truth accuracy or change to prior result seals. Examples: SEEDED_VERBATIM_EXAMPLES.md/.json; all15 full readouts, evidence and true values, selected by the frozen seed/hash rule. No API/GPU.']
    (I.OUT/'EVIDENCE_TYPE_COUNTS.md').write_text('\n'.join(lines)+'\n')
    lines=['# E13(b): 15 seeded verbatim examples','','UNBLINDED AUDIT — do not send to a blind coder. Seed20261024; five per group, hash-selected without content curation. Full readouts and coder evidence below are unchanged; JSON preserves exact strings/whitespace. These examples include true values only after the evidence classifications were sealed.']
    for group in ['a','b','c']:
        title={'a':'§84 NLA mentions','b':'§84 Oracle enactments','c':'W1 NLA table-column mentions'}[group]
        lines+=['',f'## ({group}) {title}']
        for j,r in enumerate([x for x in selected if x['group']==group],1):
            lines+=['',f"### {group}{j}: {r['feature']} — {r['reader']} L{r['layer']}",'',f"True value: **{r['true_AB']} = {r['true_value']}**. Coder: mentions={r['mentions']}, value={r['value']}; enacts={r['enacts']}, enact_value={r['enact_value']}. Evidence proxy: **{r['evidence_class']['bucket']}**.",'','Coder evidence (verbatim):','',r['evidence'],'','Full readout (verbatim; indented block):','']
            lines += ['    '+line for line in r['readout'].split('\n')]
    (I.OUT/'SEEDED_VERBATIM_EXAMPLES.md').write_text('\n'.join(lines)+'\n')
    names=['EVIDENCE_TYPE_COUNTS.json','EVIDENCE_TYPE_COUNTS.md','SEEDED_VERBATIM_EXAMPLES.json','SEEDED_VERBATIM_EXAMPLES.md','EVIDENCE_CLASSIFICATION_SEAL.json','EVIDENCE_AUDIT_RULES.json','EVIDENCE_AUDIT_SCOPE.md']
    I.save(I.OUT/'EVIDENCE_AUDIT_SEAL.json',dict(files={n:I.sha(I.OUT/n) for n in names}))
    print('15 examples and evidence split written;600 classifications sealed before truth join')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);a=p.parse_args();{'freeze':freeze,'run':run}[a.action]()
