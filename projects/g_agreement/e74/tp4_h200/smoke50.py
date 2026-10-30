"""E74 clarification-4 smoke: statistics only, fixed50fixtures, no retries."""
from __future__ import annotations
import argparse, hashlib, json, math, os
from pathlib import Path
import statistics, subprocess, sys, time
from . import smoke as core
from . import hardware, ops

FIXTURE_SHA = "c391012c118d0ee1fe23ee935275f5fb463550374b992d1a4dd1df8d3ec16842"
SEAL_SHA = "f8d9aa6e0f2c4f945e0bb78f82a5438c1a2eb4e73701c8bbdb578cbe71e2e1a6"
FROZEN_FIELDS = {"id","token_ids","read_position","expected_readout_sha256","expected_token_set_sha256s"}


def token_hashes(ids):
    return {hashlib.sha256(str(i).encode()).hexdigest() for i in ids}


def validate_fixture(obj):
    if set(obj) != {"schema_version","authority","seed","source_repo","source_revision","fixtures"}:
        raise ValueError("smoke50 envelope fields differ")
    expected = {"schema_version":2,"authority":"b90325cb","seed":20261027,
                "source_repo":core.DATA_REPO,"source_revision":core.DATA_REVISION}
    if any(type(obj[k]) is not type(v) or obj[k]!=v for k,v in expected.items()):
        raise ValueError("smoke50 source/rule binding differs")
    rows=obj["fixtures"]
    if not isinstance(rows,list) or len(rows)!=50 or len({r["id"] for r in rows})!=50:
        raise ValueError("exactly50 unique fixtures required")
    for r in rows:
        if set(r)!=FROZEN_FIELDS: raise ValueError("smoke50 fixture field differs")
        if not core.SHA_RE.fullmatch(r["id"]) or not core.SHA_RE.fullmatch(r["expected_readout_sha256"]):
            raise ValueError("invalid fixture digest")
        ids=r["token_ids"];p=r["read_position"]
        if not isinstance(ids,list) or not 3<=len(ids)<=1151 or any(type(i)is not int or not 0<=i<154856 for i in ids):
            raise ValueError("invalid complete stored token sequence")
        if type(p)is not int or not 2<=p<len(ids) or ids[p] in (154822,154824):
            raise ValueError("invalid read position")
        hs=r["expected_token_set_sha256s"]
        if not isinstance(hs,list) or hs!=sorted(set(hs)) or any(not core.SHA_RE.fullmatch(x) for x in hs):
            raise ValueError("reference token-set hash schema differs")
    return rows


def load_inputs(fixture,seal):
    if core.sha256(seal)!=SEAL_SHA: raise ValueError("frozen50 input seal differs")
    sealed=json.loads(seal.read_text())
    if sealed!={"status":"E74_SMOKE50_INPUTS_SEALED","files":{"fixtures.json":FIXTURE_SHA}}:
        raise ValueError("frozen50 input seal schema differs")
    return validate_fixture(core.load_bound_json(fixture,FIXTURE_SHA))


def verdict(exact_count,jaccards,violations):
    if type(exact_count)is not int or type(violations)is not int or not 0<=exact_count<=50 or not 0<=violations<=50:
        raise ValueError("invalid counts")
    if len(jaccards)!=50 or any(not math.isfinite(x) or not 0<=x<=1 for x in jaccards):
        raise ValueError("all50 finite agreement values required")
    median=statistics.median(jaccards)
    passed=(exact_count/50>=0.15 or median>=0.50) and violations/50<=0.10
    return {"status":"PASS_AGREEMENT" if passed else "STOP_SMOKE_CRITERION_FAILED",
            "n":50,"exact_match_count":exact_count,"exact_match_rate":exact_count/50,
            "median_token_set_jaccard":median,"grammar_violation_count":violations,
            "grammar_violation_rate":violations/50,"passed":passed,
            "capture_authorized":False,"reader_go":False}


def agreement(outputs,fixtures,tok):
    if len(outputs)!=50 or len(fixtures)!=50: raise ValueError("incomplete smoke; no partial denominator")
    exact=violations=0;jaccards=[]
    for text,r in zip(outputs,fixtures):
        if not isinstance(text,str): raise ValueError("output is not a string")
        text=text.strip()
        ids=tok.encode(text,add_special_tokens=False)
        generated=token_hashes(ids);reference=set(r["expected_token_set_sha256s"])
        union=generated|reference
        jaccards.append(len(generated&reference)/len(union) if union else 1.0)
        exact+=core.text_hash(text)==r["expected_readout_sha256"]
        # Original grammar forces one initial '*' token; count the same GLM
        # tokenizer's tokens after that prefix, including any standalone space.
        initial=text.startswith("*")
        if initial and ids and tok.decode([ids[0]])!="*":
            raise ValueError("tokenizer does not reproduce the initial grammar token")
        violations+=not text or not initial or not text[1:].strip() or len(ids)-int(initial)>16
    return verdict(int(exact),jaccards,int(violations))


def run50(fixtures,runtime,engine,adapter_dir,expected_workers=4,before_verdict=None):
    import torch
    core.check_runtime_interface(runtime)
    if type(expected_workers) is not int or expected_workers not in (4,8):
        raise ValueError('unsupported expected worker count')
    if engine.n_workers!=expected_workers or len(engine.prompt_ids)!=70 or engine.mpos!=63 or engine.prompt_ids[63]!=154518 or engine.prompt_ids.count(154518)!=1 or engine.merged is not None:
        raise ValueError("native runtime interface differs")
    t=time.monotonic()
    acts=engine.capture_h51([r["token_ids"] for r in fixtures],[[r["read_position"]] for r in fixtures])
    capture_s=time.monotonic()-t
    if len(acts)!=50 or any(tuple(a.shape)!=(1,6144) or not bool(torch.isfinite(a).all()) or float(a.norm())<=0 for a in acts):
        raise ValueError("incomplete/invalid50fixture capture")
    engine.set_lens(adapter_dir,keep_base="gpu")
    t=time.monotonic()
    generated=engine.verbalize(torch.cat(acts),n=1,temperature=0.0,cap=16,seed=0,alpha=54.1)
    read_s=time.monotonic()-t
    if len(generated)!=50 or any(not isinstance(x,list) or len(x)!=1 for x in generated):
        raise ValueError("exactly one greedy output per fixture required")
    if before_verdict is not None:before_verdict()
    result=agreement([x[0] for x in generated],fixtures,engine.tok)
    result.update({"capture_seconds":capture_s,"readout_seconds":read_s,
                   "raw_text_retained":False,"fixture_text_inspected":False,
                   "full_scope":True,"read_block":51,"generated_count":50})
    return result


def validate_clocks(req,now,admission=None):
    science_cap = 1200 if admission is None else hardware.limits(admission)['boot_smoke_seconds']
    keys=["allocation_start_epoch","weight_staging_started_epoch","weight_staging_finished_epoch",
          "archive_staging_started_epoch","archive_staging_finished_epoch","science_start_epoch","deadline_epoch"]
    if any(type(req.get(k))not in (float,int) or not math.isfinite(req[k]) for k in keys):
        raise ValueError("missing/nonfinite stage clocks")
    for prefix,cap in (("weight",3600),("archive",900)):
        start=req[prefix+"_staging_started_epoch"];end=req[prefix+"_staging_finished_epoch"]
        if not 0<start<=end<=req["science_start_epoch"] or end-start>cap:
            raise ValueError("separate staging cap exceeded")
    if not 0<req["allocation_start_epoch"]<=req["science_start_epoch"]<=now<req["deadline_epoch"]:
        raise ValueError("invalid actual allocation/science clocks")
    if req["science_start_epoch"]-req["allocation_start_epoch"]>4500 or not 0<req["deadline_epoch"]-req["science_start_epoch"]<=science_cap:
        raise ValueError("staging or boot-plus-smoke deadline exceeds cap")


def worker(request_path,out):
    req=json.loads(request_path.read_text())
    admission=ops.admission(req['admission'],req['admission_sha256'],'resident_smoke_capture')
    config=hardware.profile(admission)
    validate_clocks(req,time.time(),admission)
    if admission['allocation_start_epoch']!=req['allocation_start_epoch']:raise ValueError('allocation clock differs')
    if sys.flags.optimize: raise ValueError("author assertions must be enabled")
    os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
                      VLLM_LENS_CUDA_GRAPHS="1",VLLM_ALLOW_INSECURE_SERIALIZATION="1",VLLM_LENS_MERGE_ALLOW_TP="1")
    fixtures=load_inputs(Path(req["fixtures"]),Path(req["input_seal"]))
    manifest=core.load_bound_json(Path(req["weight_manifest"]),core.WEIGHT_MANIFEST_SHA256)
    staging=core.load_bound_json(Path(req["staging_receipt"]),req["staging_receipt_sha256"])
    if staging["completed_epoch"]>req["science_start_epoch"]: raise ValueError("verification incomplete before model load")
    core.check_staging_receipt(staging,manifest,Path(req["model_dir"]),Path(req["adapter_dir"]),req["allocation_start_epoch"],staging_limit_seconds=4500)
    core.verify_fork(Path(req["fork_archive"])); versions=core.check_dependencies(staging["runtime_versions"])
    runtime=core.import_author_runtime(Path(req["runtime"]))
    import torch
    start=time.monotonic()
    engine=hardware.construct(runtime,torch,req['model_dir'],config)
    boot=time.monotonic()-start
    if core.sha256(Path(req["model_dir"])/"hf_quant_config.json")!=manifest["author_quant_override"]["derived_hf_quant_config_sha256"]:
        raise ValueError("derived quantization config differs")
    result=run50(fixtures,runtime,engine,req["adapter_dir"],expected_workers=config['gpu_count'])
    result.update({"authority":"b90325cb","fixture_sha256":FIXTURE_SHA,"input_seal_sha256":SEAL_SHA,
                   "boot_seconds":boot,"runtime_versions":versions,"provider_release_verified":False,
                   "staging_receipt_sha256":req["staging_receipt_sha256"],"hardware":config})
    core.canonical_write(out/"STATISTICS.json",result)
    core.canonical_write(out/"SEAL.json",{"status":"SMOKE50_STATISTICS_SEALED","files":{"STATISTICS.json":core.sha256(out/"STATISTICS.json")}})
    return 0 if result["passed"] else 3


def supervise(req,out):
    admission=ops.admission(req['admission'],req['admission_sha256'],'resident_smoke_capture')
    validate_clocks(req,time.time(),admission);out.mkdir(mode=0o700,parents=True,exist_ok=False)
    core.canonical_write(out/"REQUEST.json",req)
    with (out/"worker.log").open("x") as log:
        proc=subprocess.Popen([sys.executable,"-m","projects.g_agreement.e74.smoke50","--worker-request",str((out/"REQUEST.json").resolve()),"--out",str(out.resolve())],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=proc.wait(timeout=max(.01,req["deadline_epoch"]-time.time()-1))
        except subprocess.TimeoutExpired:code=124
        finally:core.kill_group(proc.pid)
    if time.time()>=req["deadline_epoch"]:code=124
    status="COMPLETE" if code==0 else "STOP_TIMEOUT" if code==124 else "STOP_SMOKE_CRITERION_FAILED" if code==3 else "STOP_SETUP_ERROR"
    receipt={"status":status,"exit_code":code,"provider_release_verified":False,"capture_authorized":False,"reader_go":False,"raw_text_displayed":False}
    if (out/"SEAL.json").exists():receipt["statistics_seal_sha256"]=core.sha256(out/"SEAL.json")
    core.canonical_write(out/"RECEIPT.json",receipt);print(json.dumps(receipt));return code


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixtures",type=Path);p.add_argument("--input-seal",type=Path);p.add_argument("--preflight",action="store_true")
    p.add_argument("--request",type=Path);p.add_argument("--worker-request",type=Path);p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.preflight:
        rows=load_inputs(a.fixtures,a.input_seal)
        print(json.dumps({"status":"PASS_CPU_ONLY","n":len(rows),"fixture_sha256":FIXTURE_SHA,"gpu_calls":0}));return 0
    if a.worker_request:return worker(a.worker_request,a.out)
    if not a.request or not a.out:p.error("--request and --out required; I-2 admission is external")
    return supervise(json.loads(a.request.read_text()),a.out)
if __name__=="__main__":raise SystemExit(main())
