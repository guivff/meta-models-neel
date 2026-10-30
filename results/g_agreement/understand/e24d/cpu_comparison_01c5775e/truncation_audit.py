"""CPU source/metadata audit; never loads model weights or calls a model."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
rows=lambda p:[json.loads(x) for x in Path(p).read_text().splitlines()]

def main():
    previous=OUT/'previous_before_truncation_audit'
    if previous.exists():raise FileExistsError('preserve once-only audit snapshot')
    previous.mkdir()
    for n in ('RESULTS.md','COMPARISON.json','compare.py','SEAL.json'):shutil.copyfile(OUT/n,previous/n)
    for n,h in read(previous/'SEAL.json')['files'].items():assert sha(previous/n)==h
    run=ROOT/'cache/g_agreement/understand/e24d/hydxzymqlfryhy/final/out/E24D_NEW_RUN'
    assets=read(run.parents[1]/'assets.json');directory=Path('cache/g_assets/Qwen__Qwen3.6-27B')
    conf={}
    for n in ('config.json','tokenizer_config.json'):
        expected=next(x['sha256'] for x in assets['files'] if x['path']==assets['model']+'/'+n)
        assert sha(directory/n)==expected
        conf[n]={'sha256':expected}
    conf['config.json']['text_max_position_embeddings']=read(directory/'config.json')['text_config']['max_position_embeddings']
    conf['tokenizer_config.json']['model_max_length']=read(directory/'tokenizer_config.json')['model_max_length']
    old24=subprocess.check_output(['git','show','e5d28d98:projects/g_agreement/understand/e24_worker.py'],cwd=ROOT)
    old32=subprocess.check_output(['git','show','1b13c172:projects/g_agreement/understand/e32.py'],cwd=ROOT)
    plan=read(ROOT/'results/g_agreement/understand/e24d/RUN_PLAN.json')
    assert hashlib.sha256(old24).hexdigest()==plan['original_e24_capture_sha256']
    helper=ROOT/'external/mats-nla-workspace/src/mats/capture.py'
    assert sha(helper)==plan['source_files']['external/mats-nla-workspace/src/mats/capture.py']
    capture_text=helper.read_text();assert 'n = max(len(s) for s in seqs)' in capture_text and 'ids[i, : len(s)] = torch.as_tensor(list(s)' in capture_text
    b=rows(run/'b/records.jsonl');equal=[x for x in b if x['token_count']==392];longer=[x for x in b if x['token_count']>392]
    all24=rows(ROOT/'cache/g_agreement/understand/e24-stage-v1/items.input.jsonl');all32=rows(ROOT/'cache/g_agreement/understand/e32-stage-v1/items.jsonl')
    import transformers
    backend=Path(transformers.__file__).parent/'models/qwen3_5/modeling_qwen3_5.py'
    backend_text=backend.read_text()
    assert 'self.embed_tokens(input_ids)' in backend_text and 'self.lm_head(hidden_states[:, slice_indices, :])' in backend_text
    versions={n:read(run/n)['packages']['transformers'] for n in ('ENV_w1.json','ENV_kernels.json')}
    info={'question':'Could E24/E32 capture truncate at392 tokens?','finding':'NO_TRUNCATION_FOUND_IN_CAPTURE_CALLS_OR_PINNED_HELPER',
          'old_e24_capture_file_sha256':hashlib.sha256(old24).hexdigest(),'old_e32_capture_file_sha256':hashlib.sha256(old32).hexdigest(),
          'capture_helper_sha256':sha(helper),'call_evidence':'Both old Engine.capture methods pass [x[ids] for x in items] directly, no tokenizer, slicing, max_length or truncation argument.',
          'helper_evidence':'_pad uses max(len(s)) and copies every token; _resolve(-1,len(s)) returns len(s)-1; full padded input and attention mask passed to model.',
          'capture_tokenizer_defaults':'Not applicable: capture uses frozen ids directly. No tokenizer call or implicit tokenizer max_length.',
          'model_config_verified_against_pulled_asset_manifest':conf,
          'backend':{'local_transformers_version':transformers.__version__,'pulled_environment_versions':versions,'source_sha256':sha(backend),
                     'evidence':'Forward embeds full input_ids, builds position_ids over inputs_embeds.shape[1], iterates decoder layers. logits_to_keep restricts final lm_head positions only; capture raises before lm_head.',
                     'limitation':'Local same-version backend source inspected; pulled remote source bytes were not archived and are not independently hash-matched.'},
          'sample_length392':{'n':len(equal),'pass':sum(x['cosine']>=.999 for x in equal),'fail':sum(x['cosine']<.999 for x in equal),'items':equal},
          'sample_longer_than392':{'n':len(longer),'max_length':max(x['token_count'] for x in longer),'all_b_pass':all(x['cosine']>=.999 for x in longer)},
          'e24_bank':{'n':len(all24),'max_length':max(len(x['ids']) for x in all24),'over392':sum(len(x['ids'])>392 for x in all24)},
          'e32_bank':{'n':len(all32),'max_length':max(len(x['ids']) for x in all32),'over392':sum(len(x['ids'])>392 for x in all32)},
          'mechanism_limit':'Absence of an identified truncation path does not prove the true numerical cause; no GPU or real-model inference was performed.',
          'prior_seal_sha256':sha(previous/'SEAL.json')}
    (OUT/'TRUNCATION_AUDIT.json').write_text(json.dumps(info,indent=2)+'\n')
    comparison=read(OUT/'COMPARISON.json');comparison['truncation_audit']=info;(OUT/'COMPARISON.json').write_text(json.dumps(comparison,indent=2)+'\n')
    with (OUT/'RESULTS.md').open('a') as f:
        f.write('''\n## Follow-up: is 392 a truncation boundary?\n\n**No truncation was found in the exact old capture calls or the pinned capture helper.** E24 at e5d28d98 and E32 at 1b13c172 pass the stored `ids` arrays directly to `mats.capture.capture`; neither capture path tokenizes the text, slices tokens, sets `max_length`, or requests truncation. Thus tokenizer default truncation cannot enter these calls.\n\nThe pinned helper allocates each batch to `max(len(s))`, copies every sequence in full, masks right padding, and resolves read position −1 to `len(s)−1`. `logits_to_keep=1` limits final LM-head outputs, not the input or decoder sequence; capture stops before that head. The locally available transformers 5.18.0 backend explicitly embeds the full input and constructs positions over its full length. Both pulled environments record 5.18.0; remote backend source bytes were not archived, so the local source is version-matched rather than independently byte-matched.\n\nBoth local model metadata files match the pulled asset-manifest hashes. `text_config.max_position_embeddings` and tokenizer `model_max_length` are 262144, not 392. The E24 bank contains 4,704 items, maximum 502 tokens, with 122 longer than 392. The diagnostic sample has five items longer than 392 (maximum 489), all passing arm (b). Of four sampled items exactly 392 tokens, one passes and three fail. Therefore 392 is neither an observed universal failure boundary nor an implemented capture cap.\n\nThis rules out an explicit truncation in the inspected call/helper and makes a 392-token context explanation unsupported. It does not identify the numerical mechanism behind the seven failures. The previous report, JSON, generator and seal are preserved byte-for-byte under `previous_before_truncation_audit/`. This remains CPU-only and does not gate the authorised relaunch.\n''')
    names=['compare.py','truncation_audit.py','COMPARISON.json','TRUNCATION_AUDIT.json','RESULTS.md','previous_before_truncation_audit/SEAL.json']
    (OUT/'SEAL.json').write_text(json.dumps({'status':'CPU_DESCRIPTIVE_WITH_TRUNCATION_AUDIT_NO_INFERENCE','files':{n:sha(OUT/n) for n in names}},indent=2)+'\n')
    print(json.dumps({k:info[k] for k in ('finding','e24_bank','e32_bank','sample_longer_than392')},indent=2))
if __name__=='__main__':main()
