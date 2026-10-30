"""CPU-only data-to-bank freeze; no dataset code or model execution."""
from datetime import datetime,timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

from transformers import PreTrainedTokenizerFast
from babi133 import build_pairs,episodes,QUESTION,SEED

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'cache/source_v1'
SNAP=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')


def build():
    now=datetime.now(timezone.utc)
    if now>=datetime(2026,10,30,7,0,tzinfo=timezone.utc):
        raise ValueError('08CET hard cut reached; drop external arm, do not freeze late')
    identity=json.loads((SOURCE/'SOURCE_IDENTITY_BEFORE_DOWNLOAD.json').read_text())
    download=json.loads((SOURCE/'DOWNLOAD_RECEIPT.json').read_text())
    assert identity['gated'] is False and identity['terms_accepted'] is False and identity['license']=='CC-BY-3.0'
    assert sha(SOURCE/'babi_tasks_1-20_v1-2.tar.gz')==download['archive_sha256']
    for data in download['selected_files'].values():assert sha(SOURCE/data['local_name'])==data['sha256']
    qa2=SOURCE/'qa2_two-supporting-facts_test.txt';qa3=SOURCE/'qa3_three-supporting-facts_test.txt'
    public,pairs,census=build_pairs(qa2.read_text(),sha(qa2))
    if len(pairs)<42:raise ValueError('fewer than42 checker-valid pairs; external arm not built')
    eps3=episodes(qa3.read_text());assert not any(QUESTION.fullmatch(ep['question']['text']) for ep in eps3)
    tok=PreTrainedTokenizerFast(tokenizer_file=str(SNAP/'tokenizer.json'))
    assert sha(SNAP/'tokenizer.json')=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
    lookup={r['id']:r['prompt'] for r in public}
    places=sorted({place for p in pairs for place in p['source_existing_locations']})
    candidates={v:tok.encode(' '+v,add_special_tokens=False) for v in places}
    assert all(len(ids)==1 for ids in candidates.values())
    tokenization=[];boundaries=0
    for p in pairs:
        lengths=[]
        for m in p['members']:
            text=lookup[m['id']];ids=tok.encode(text,add_special_tokens=False)
            assert ids[-1]==539
            for location in places:
                assert tok.encode(text+' '+location,add_special_tokens=False)==ids+candidates[location]
                boundaries+=1
            rp=[candidates[v][0] for v in p['recipients']]
            cp=[candidates[v][0] for v in (m['current_holder'],m['previous_holder'])]
            m['ordered_recipient_candidate_ids']=rp;m['current_previous_candidate_ids']=cp
            m['continuation_strings']={k:' '+m[k] for k in ('current_holder','previous_holder','twin_recipient')}
            tokenization.append(dict(id=m['id'],input_ids=ids,read_index=len(ids)-1,
                                     ordered_recipient_candidate_ids=rp,current_previous_candidate_ids=cp))
            lengths.append(len(ids))
        assert lengths[0]==lengths[1]
    assert len(public)==2*len(pairs) and len({r['id'] for r in public})==len(public)
    assert all(set(r)=={'id','prompt'} and '\t' not in r['prompt'] for r in public)
    out=HERE/'cache/bank_2026-10-30_v1';out.mkdir(parents=True,exist_ok=False)
    dump(out/'items.json',public)
    dump(out/'PAIRS.PRIVATE.json',{'experiment':'E133_babi','seed':SEED,'pairs':pairs,'candidate_token_ids':candidates,
         'source_test_file_sha256':sha(qa2),'selection':'operator32-token behaviour only; first42qualifying pairs in this source order'})
    dump(out/'TOKENIZATION_CPU.PRIVATE.json',tokenization)
    data=(out/'items.json').read_bytes()
    with (out/'PUBLIC_INPUTS.tar.gz').open('xb') as target:
        with gzip.GzipFile(fileobj=target,mode='wb',mtime=0,filename='') as gz:
            with tarfile.open(fileobj=gz,mode='w') as tar:
                entry=tarfile.TarInfo('items.json');entry.size=len(data);entry.mode=0o644;entry.mtime=0;tar.addfile(entry,io.BytesIO(data))
    with tarfile.open(out/'PUBLIC_INPUTS.tar.gz') as t:
        assert t.getnames()==['items.json'];assert json.load(t.extractfile('items.json'))==public
    provenance=dict(identity,download=download,raw_source_path=str(SOURCE.resolve()),
         data_only=True,dataset_scripts_or_instructions_executed=False,train_files_read=False,
         qa2_test_file_sha256=sha(qa2),qa3_test_file_sha256=sha(qa3),
         attribution='Jason Weston et al. (2015), Towards AI-Complete Question Answering: A Set of Prerequisite Toy Tasks; CC BY3.0. bAbI release v1.2, English test files. Counterfactual adaptation is ours.')
    dump(HERE/'SOURCE_PROVENANCE.json',provenance)
    manifest={'experiment':'E133_babi','authority':'§242 +§241/242clarification1 QA2only','status':'FROZEN_BEFORE_SCREEN_READERS',
         'utc':now.isoformat(),'deadline_08CET_met':True,'seed':SEED,'source_census':census,
         'qa3':{'test_episodes':len(eps3),'test_questions':1000,'eligible_current_location_questions':0,'disposition':'INELIGIBLE_HISTORICAL_QUESTIONS_NOT_REWRITTEN'},
         'pairs':len(pairs),'prompts':len(public),'minimum_pairs_requirement':42,'selection':'first42both-correct pairs by operator behaviour screen, source order',
         'read_rule':'exact original QA2 narrative fact lines, final original question, newline + The OBJECT is now by; raw prefix, final by539',
         'no_source_answer_or_support_ids_on_pod':True,'public_schema':['id','prompt'],'archive_members':['items.json'],
         'twin_change':'one location span in asked object final actual movement, alternative already mentioned before that movement; same previous location; replay verifies every OTHER object final location unchanged',
         'source_order':'one final question per original episode, QA2testsource order; earlier query/answer lines excluded from narrative facts; no question rewrite',
         'question_whitespace':'only trailing separator whitespace before source tab removed; words/punctuation unchanged',
         'tokenizer_sha256':sha(SNAP/'tokenizer.json'),'base_revision':SNAP.name,'final_read_token_id':539,
         'candidate_values_single_token':len(candidates),'candidate_boundary_checks':boundaries,'equal_token_length_pairs':len(pairs),
         'maximum_tokens':max(len(x['input_ids']) for x in tokenization),'files':{p.name:sha(p) for p in sorted(out.iterdir())},
         'source_files':{n:sha(HERE/n) for n in ('babi133.py','build_babi133.py','test_babi133.py')},'model_GPU_API_calls':0,'never_pooled_with_main_R_NL1':True}
    dump(HERE/'BANK_MANIFEST.json',manifest)
    dump(HERE/'INPUT_SEAL.json',{'experiment':'E133_babi','stage':'screen','labels_on_pod':False,'files':{'items.json':sha(out/'items.json')},
         'public_archive_sha256':sha(out/'PUBLIC_INPUTS.tar.gz'),'public_schema':'id,prompt only','pairs':len(pairs)})
    dump(HERE/'BANK_SEAL.json',{'experiment':'E133_babi','status':'FROZEN_BEFORE_SCREEN_READERS','files':{n:sha(HERE/n) for n in ('SOURCE_PROVENANCE.json','BANK_MANIFEST.json','INPUT_SEAL.json','babi133.py','build_babi133.py','test_babi133.py')}})
    for p in SOURCE.iterdir():
        if p.is_file():p.chmod(0o444)
    print(json.dumps({'status':'FROZEN','pairs':len(pairs),'prompts':len(public),'archive_sha256':sha(out/'PUBLIC_INPUTS.tar.gz'),'input_seal':sha(HERE/'INPUT_SEAL.json'),'bank_seal':sha(HERE/'BANK_SEAL.json'),'maximum_tokens':manifest['maximum_tokens'],'census':census}))


if __name__=='__main__':build()
