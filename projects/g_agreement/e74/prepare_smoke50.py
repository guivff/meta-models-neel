"""Clarification-4 metadata-only, once-only smoke selection; never display text."""
from __future__ import annotations
import argparse, collections, hashlib, json, random
from pathlib import Path

SEED = 20261027
REV = "226c6dce62ed88d5981ca864d0c99d3f082ccee6"
E66_SELECTION_SHA = "c7ded7b80744db5e86b81b36ec5090a0b8cd655e189937d34a386af1d045f39e"
SOURCE_HASHES = {"transcripts.parquet":"c44efbb4860219b05b2d7e6be592f454a32c51aa66aa984531bf0f2acf61137b", "olens_wild_rollouts.parquet":"6e42c4ed8bab563394e585f15287e57d61ac95f78845cdc98730ba74e27e33a1"}
TOKENIZER_SHA = "19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d"
RULE = {"authority":"b90325cb §192 clarification 4", "seed":SEED, "n":50,
 "sampling":"random.Random(seed).sample over lexicographically sorted eligible distinct (source,tid); then choice from sorted stored positions for each selected rollout",
 "eligibility":"all source families; unique (source,tid); entire stored ids, nontruncated, n_tokens_full == len(ids), 3..1151 tokens; stored position>=2 and not sink154822/154824",
 "context_limit_reason":"preserve accepted author engine max_model_len1152 without shortening or rerendering stored IDs",
 "exclusion":"all542 E66 packet rollouts by (source,tid), not merely their selected positions",
 "no_outcome_selection":True, "no_replacement":True,
 "agreement":"exact stripped UTF8 sha256; token-set Jaccard of pinned GLM token IDs of entire stripped bullet (includes initial *), add_special_tokens=False; sets stored as per-token SHA256s",
 "grammar":"empty content, missing initial *, or >16 GLM content tokens after the initial *; no additional failure criterion",
 "pass":"(exact_match_rate>=0.15 or median_token_set_jaccard>=0.50) and grammar_violation_rate<=0.10",
 "disclosure":"eligible complete short-context subset, not a representative sample of arbitrarily long wild transcripts"}

def digest(data): return hashlib.sha256(data).hexdigest()
def sha(path): return digest(path.read_bytes())
def encoded(obj): return (json.dumps(obj,sort_keys=True,indent=2)+"\n").encode()
def write(path,obj):
 with path.open("xb") as f: f.write(encoded(obj))
def token_hashes(ids): return sorted({digest(str(i).encode()) for i in ids})

def choose(rows,excluded):
 counts=collections.Counter((r["source"],r["tid"]) for r in rows)
 eligible={}
 for r in rows:
  key=(r["source"],r["tid"]); ids=r["ids"]
  if key in excluded or counts[key]!=1 or r["truncated"] is not False: continue
  if not isinstance(ids,list) or not 3<=len(ids)<=1151 or r["n_tokens_full"]!=len(ids): continue
  if any(type(i) is not int or not 0<=i<154856 for i in ids): raise ValueError("invalid stored token ID")
  positions=sorted({p for p in r["positions"] if type(p) is int and 2<=p<len(ids) and ids[p] not in (154822,154824)})
  if positions: eligible[key]=(r,positions)
 if len(eligible)<50: raise ValueError("fewer than50 eligible rollouts; no fallback")
 rng=random.Random(SEED); keys=rng.sample(sorted(eligible),50)
 selected=[(eligible[k][0],rng.choice(eligible[k][1])) for k in keys]
 return selected,{"source_transcripts":len(rows),"eligible_rollouts":len(eligible),"eligible_families":dict(collections.Counter(r[0]["family"] for r in eligible.values())),"excluded_e66_rollouts":len(excluded),"selected_families":dict(collections.Counter(r["family"] for r,p in selected))}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--result",type=Path,required=True);ap.add_argument("--e66-selection",type=Path,required=True);a=ap.parse_args()
 r=a.result; out=r/"smoke50";out.mkdir(exist_ok=False)
 write(out/"RULE.json",RULE|{"script_sha256":sha(Path(__file__))}) # before reading metadata/outcomes
 if sha(a.e66_selection)!=E66_SELECTION_SHA: raise ValueError("E66 selection seal mismatch")
 metadata=json.loads(a.e66_selection.read_text())
 excluded={tuple(json.loads(v["rollout"])) for v in metadata}
 if len(excluded)!=542: raise ValueError("E66 membership count differs")
 evidence=r/"evidence"
 for name,expected in SOURCE_HASHES.items():
  if sha(evidence/name)!=expected: raise ValueError("pinned source mismatch")
 if sha(evidence/"tokenizer/tokenizer.json")!=TOKENIZER_SHA: raise ValueError("tokenizer mismatch")
 import pyarrow.parquet as pq
 import pyarrow.dataset as ds
 from tokenizers import Tokenizer
 columns=["source","tid","family","ids","positions","truncated","n_tokens_full"]
 rows=pq.read_table(evidence/"transcripts.parquet",columns=columns).to_pylist()
 selected,counts=choose(rows,excluded)
 priv=r/"private/smoke50";priv.mkdir(exist_ok=False)
 keys=[{"source":v["source"],"tid":v["tid"],"pos":p} for v,p in selected]
 write(priv/"SELECTION.json",keys) # freeze exact identities before requesting references
 tok=Tokenizer.from_file(str(evidence/"tokenizer/tokenizer.json"))
 dataset=ds.dataset(evidence/"olens_wild_rollouts.parquet",format="parquet")
 fixtures=[]
 for i,(row,pos) in enumerate(selected):
  assert (row["source"],row["tid"]) not in excluded
  query=(ds.field("source")==row["source"])&(ds.field("tid")==row["tid"])&(ds.field("pos")==pos)
  matches=dataset.to_table(filter=query,columns=["rl_greedy","lens_rl_ckpt"]).to_pylist()
  if len(matches)!=1 or not str(matches[0]["lens_rl_ckpt"]).endswith("rl1b_2/step_0100"): raise ValueError("reference join/provenance mismatch; no replacement")
  text=matches[0]["rl_greedy"]
  if not isinstance(text,str): raise ValueError("reference type invalid; no replacement")
  text=text.strip()
  fixtures.append({"id":digest(encoded(keys[i])),"token_ids":row["ids"],"read_position":pos,
   "expected_readout_sha256":digest(text.encode()),"expected_token_set_sha256s":token_hashes(tok.encode(text,add_special_tokens=False).ids)})
 stage=r/"staging/smoke50";stage.mkdir(exist_ok=False)
 write(stage/"fixtures.json",{"schema_version":2,"authority":"b90325cb","seed":SEED,"source_repo":"ceselder/glm-5.3-olens-wild-rollouts","source_revision":REV,"fixtures":fixtures})
 write(stage/"INPUT_SEAL.json",{"status":"E74_SMOKE50_INPUTS_SEALED","files":{"fixtures.json":sha(stage/"fixtures.json")}})
 receipt={"status":"PREPARED_STATISTICS_ONLY","authority":"b90325cb","rule_sha256":sha(out/"RULE.json"),"source_hashes":SOURCE_HASHES,"e66_selection_sha256":E66_SELECTION_SHA,"selection_sha256":sha(priv/"SELECTION.json"),"e66_rollout_overlap":0,"fixture_count":50,"fixture_sha256":sha(stage/"fixtures.json"),"input_seal_sha256":sha(stage/"INPUT_SEAL.json"),"total_prompt_tokens":sum(len(v["token_ids"]) for v in fixtures),"min_prompt_tokens":min(len(v["token_ids"]) for v in fixtures),"max_prompt_tokens":max(len(v["token_ids"]) for v in fixtures),"counts":counts,"reference_text_displayed":False,"fixture_text_decoded":False,"other_readout_columns_requested":False,"gpu_calls":0,"wild_content_redistributed":False}
 write(out/"FIXTURE_RECEIPT.json",receipt)
 print(json.dumps(receipt))
if __name__=="__main__": main()
