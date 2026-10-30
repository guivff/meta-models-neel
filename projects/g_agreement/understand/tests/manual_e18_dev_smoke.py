import json, time
from pathlib import Path
import numpy as np
import common, torch
from transformers import AutoTokenizer, LlamaConfig, LlamaForCausalLM
from peft import LoraConfig, get_peft_model
from mats.readers.olens import OracleLens
from projects.g_agreement.understand.cpu import ROOT, read, rows, dump, sha, verify
from projects.g_agreement.understand.e18_worker import generate, score_arm
from projects.g_agreement.understand.e18 import ARMS
start=time.monotonic(); torch.set_num_threads(2); torch.manual_seed(20261025)
inputs=ROOT/'cache/g_agreement/understand/e18';verify(inputs,'INPUT_SEAL.json')
items=rows(inputs/'dev.input.jsonl');ix=[0,8];items=[items[i] for i in ix]
assert all(r['split']=='dev' for r in items)
# Shape-only CPU smoke: deterministic first16 components of sealed dev vectors;
# random tiny weights, never a measurement of the real reader or throughput.
h=np.load(inputs/'dev_acts44.npy',allow_pickle=False)[ix,:16]
tokpath=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B')
tok=AutoTokenizer.from_pretrained(tokpath,local_files_only=True)
config=LlamaConfig(vocab_size=len(tok),hidden_size=16,intermediate_size=24,num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=2,max_position_embeddings=512,pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
model=get_peft_model(LlamaForCausalLM(config),LoraConfig(r=2,lora_alpha=2,target_modules=['q_proj'],task_type='CAUSAL_LM')).eval()
reader=OracleLens(model,tok,device='cpu')
raw=generate(reader,h,items);mapping={r['id']:r for r in raw};donors={items[0]['id']:items[1]['id'],items[1]['id']:items[0]['id']}
templates=read(inputs/'templates.json')
checks={}
for arm in ARMS:
    values=score_arm(reader,arm,items,h,templates,mapping,donors)
    assert len(values)==2 and np.isfinite([r['scores'] for r in values]).all()
    assert all(len(r['scores'])==2 for r in values)
    checks[arm]='PASS'
report={'status':'PASS','scope':'CPU operational smoke; real W1 dev vectors first16 components and native Qwen tokenizer; tiny randomly initialized one-layer Llama+LoRA; not pretrained reader science','split':'dev','ids':[r['id'] for r in items],'feature':items[0]['feature'],'test_forwards':0,'pretrained_model_forwards':0,'model_API_calls':0,'GPU_hours':0,'question_selection':False,'input_seal_sha256':sha(inputs/'INPUT_SEAL.json'),'native_tokenizer_sha256':sha(tokpath/'tokenizer.json'),'generation_max_new_tokens':16,'generated_lengths':[len(r['continuation_ids']) for r in raw],'arms':checks,'scores_and_texts_retained':False,'wall_seconds':time.monotonic()-start,'GPU_forecast_seconds':None}
dump(ROOT/'results/g_agreement/understand/e18/CPU_DEV_SMOKE.json',report)
print(json.dumps(report))
