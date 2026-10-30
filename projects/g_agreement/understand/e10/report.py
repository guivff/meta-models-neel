"""Reader join only after sealed blind extraction, matching and type assignment."""
from collections import Counter,defaultdict
import time
from . import io as I

def select(pairs,typed,random_ids):
 eligible={p['pair_id'] for p in pairs if p['examples_eligible']};freq=Counter(x['type'] for x in typed if x['type']);used=set(random_ids);chosen=[]
 for t,_ in sorted(freq.items(),key=lambda x:(-x[1],x[0]))[:3]:
  counts=Counter(x['pair_id'] for x in typed if x['type']==t)
  picked=0
  for pid,n in sorted(counts.items(),key=lambda x:(-x[1],I.rank('example',t,x[0]))):
   if pid not in eligible or pid in used:continue
   chosen.append({'pair_id':pid,'reason':'top type '+t,'type_claims':n});used.add(pid);picked+=1
   if picked==2:break
 chosen += [{'pair_id':pid,'reason':'frozen seeded random'} for pid in random_ids]
 return chosen

def block(s):
 # Code-fence delimiter cannot occur in the source; content itself is unchanged.
 fence='`'*(max([len(x) for x in __import__('re').findall(r'`+',s)]+[2])+1)
 return fence+'text\n'+s+'\n'+fence+'\n'

def report():
 for name in ['typed_blind','pair_coverage_blind','taxonomy','claims_blind','matches_blind','one_sided_blind']:
  p=I.CACHE/(name+'.json');seal=I.read(I.OUT/(name.upper()+'_SEAL.json'))
  if I.sha(p)!=seal['sha256']:raise RuntimeError('blind seal mismatch')
 pairs=I.rows(I.CACHE/'pool.private.jsonl');byid={p['pair_id']:p for p in pairs};typed=I.read(I.CACHE/'typed_blind.json');coverage=I.read(I.CACHE/'pair_coverage_blind.json');taxonomy=I.read(I.CACHE/'taxonomy.json');manifest=I.read(I.OUT/'POOL_MANIFEST.json')
 for x in typed:
  swap=int(I.rank('AB',x['pair_id'])[:8],16)%2
  x['reader']='oracle' if (x['side']=='A')!=(swap==1) else 'nla';x['dataset']=byid[x['pair_id']]['dataset']
 chosen=select(pairs,typed,manifest['random_example_pair_ids']);counts=Counter((x['type'],x['reader']) for x in typed if x['type']);freq=Counter(x['type'] for x in typed if x['type']);covered=Counter(byid[r['pair_id']]['dataset'] for r in coverage)
 costs=I.read(I.CACHE/'cost.json');extraction=I.read(I.CACHE/'claims_blind.json');ntokens={}
 for reader in ['oracle','nla']:
  lengths=[len(p[reader].split()) for p in pairs];ntokens[reader]={'mean_whitespace_words':sum(lengths)/len(lengths),'characters':sum(len(p[reader]) for p in pairs)}
 table=[]
 for t in taxonomy:
  tid=t['id'];rs=[x for x in typed if x['type']==tid]
  table.append({'id':tid,'name':t['name'],'definition':t['definition'],'oracle_claims':counts[tid,'oracle'],'nla_claims':counts[tid,'nla'],'pairs':len({r['pair_id'] for r in rs}),'W1_claims':sum(r['dataset']=='W1' for r in rs),'S61_claims':sum(r['dataset']=='S61' for r in rs)})
 summary={'section':97,'status':'DESCRIPTIVE','pool_pairs':len(pairs),'complete_pair_matches':len(coverage),'covered_by_source':dict(covered),'unique_valid_readout_extractions':len(extraction),'claims_in_complete_pairs':sum(x['claims_A']+x['claims_B'] for x in coverage),'matched_claim_pairs':sum(x['matched'] for x in coverage),'one_sided_claims':len(typed),'unclassified_one_sided_claims':sum(x['type'] is None for x in typed),'one_sided_by_reader':dict(Counter(x['reader'] for x in typed)),'types':table,'examples':chosen,'lengths':ntokens,'cost':costs,'gpu_h':0}
 I.save(I.OUT/'SUMMARY.json',summary)
 lines=['# §97 E10 — qualitative case studies','', '**Prediction and status: DESCRIPTIVE / EXPLORATORY.** The programme predicts that readers differ in content they describe versus enact. §97 registered no numerical prediction or decision rule. This analysis describes what each output alone says; it cannot establish whether an assertion is true, encoded uniquely in the activation, or a mechanism prediction holds.','',f"Pool: {len(pairs):,} frozen pairs (W1 1,680; §61 1,592). W6’s 480 empty NLA partners are inventoried and excluded by Guiv’s ruling. §61’s 1,592 artificial mismatches are excluded. Complete extraction/matching: {len(coverage):,}/{len(pairs):,} pairs ({dict(covered)}). Valid unique readout extractions: {len(extraction):,}/5,236.",'',f"Across complete pairs: {summary['claims_in_complete_pairs']:,} atomic assertions, {summary['matched_claim_pairs']:,} equivalent claim pairs and {len(typed):,} one-sided claims. Unclassified one-sided claims: {summary['unclassified_one_sided_claims']:,}. Missing extraction/matching is never scored as one-sided content. Counts below are annotations, not accuracy.",'','## Frozen type table','', '| Type | Definition | Oracle-only claims | NLA-only claims | Pairs containing type | W1 claims | §61 claims |','|---|---|---:|---:|---:|---:|---:|']
 for t in table:lines.append('| '+ ' | '.join(str(t[k]).replace('|','\\|').replace('\n',' ') for k in ['name','definition','oracle_claims','nla_claims','pairs','W1_claims','S61_claims'])+' |')
 lines+=['','Types are induced from a fixed seeded sample of at most 512 blinded one-sided claims and frozen before all-claim classification. Pairs can contain several types, so the pair column is not additive. Counts weight the frozen pool, including W1’s two generation samples and reused text; they are not independent observations.','', '## Verbatim illustrative pairs','', 'Selection: two distinct eligible pairs from each of the three most frequent types, ranked by number of one-sided claims of that type, plus the two pre-frozen seeded random pairs. Ties, deduplication and the accidentally pre-exposed W1 item exclusion follow PLAN.json. These are illustrations chosen for large differences, not representative accuracy estimates. Raw strings retain format markers and incomplete endings; no repair. A display newline immediately before each closing fence is not part of the saved source. Exact string hashes below bind the original UTF-8 contents.']
 examples=[]
 for j,c in enumerate(chosen,1):
  p=byid[c['pair_id']];pid=p['pair_id'];annotations=[x for x in typed if x['pair_id']==pid];examples.append({'selection':c,'source':p,'one_sided_claims':annotations})
  lines+=['',f"### Pair {j}: {c['reason']} — {p['dataset']}",'',f"Pair `{pid}`; Oracle/NLA blocks {p['sites']}; source item `{p['item_id']}`."]
  if not any(x['pair_id']==pid for x in coverage):lines+=['','Annotation MISSING; selected random pair retained without replacement.']
  for reader,label in [('oracle','Oracle lens'),('nla','NLA')]:
   if I.digest(p[reader])!=p[reader+'_sha256']:raise RuntimeError('verbatim source changed')
   lines+=['',f"**{label}** — SHA-256 `{p[reader+'_sha256']}`",'',block(p[reader])]
  lines+=['','One-sided atomic claims (type; reader; exact evidence):','']
  for x in annotations:
   label=x['type'] or 'UNCLASSIFIED';lines.append('- '+label+'; '+x['reader']+': '+x['claim'].replace('\n',' ')+' Evidence: '+I.canonical(x['evidence']))
 lines+=['','## Limits, provenance and cost','', 'W1 uses the exact nonempty raw generations: all 1,680 NLA parsed `text` fields failed the source parser because the explanation terminator was absent; none was repaired. Truncation can remove propositions and inflate apparent one-sidedness. Oracle narrative continuations and NLA meta-descriptions also differ in style and length: extraction explicitly includes propositions depicted in continuations, but remains model-mediated. Mean whitespace words per raw output: '+', '.join(f"{r} {ntokens[r]['mean_whitespace_words']:.1f}" for r in ['oracle','nla'])+'.', '', 'W1 compares the same captured item/token across native blocks 44/42, not the same activation vector. §61 retains its registered 44/42 or 44/44 sites and includes natural, shuffled and SA-R controls; pooling these is descriptive. No source prompts, reader identities, sites, correctness labels or old §61 judgments were sent to extraction, matching or clustering. Text style can still reveal reader identity. One W1 pair surfaced accidentally during metadata inspection before the rule freeze; all samples of that item were excluded from illustration selection and retained in the analysis pool.', '', f"API: Gemini 3.1 Flash Lite via Google Vertex global only; minimal reasoning, ZDR and deny collection enforced, temperature 0, strict JSON schema. No retry or format repair. Actual charge ${costs['actual_usd']}; unresolved reservation ${costs['unresolved_reserve_usd']}; committed total ${costs['committed_usd']} ≤ $20. GPU: 0 h. The append-only reserve-before-send ledger and raw API responses remain under untracked cache. See PLAN.json, PROMPTS.json, POOL_MANIFEST.json and stage seals for reproducibility."]
 I.save(I.OUT/'EXAMPLES.json',examples);(I.OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n');print({k:summary[k] for k in ['complete_pair_matches','one_sided_claims','unclassified_one_sided_claims','cost']})
if __name__=='__main__':report()
