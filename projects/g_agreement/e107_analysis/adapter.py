"""E107 sealed normalized source joins; no generation, judging or prior analysis replay."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from .rules import analyze
from .sensitivity import affected_items,sensitivity
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
require,read,write,sha=core.require,core.read,core.write,core.sha
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e107/ANALYSIS_ONCE.json')

def committed():
    for name,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==digest,'changed dependency')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            blob=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            require(hashlib.sha256(blob).hexdigest()==sha(p),'uncommitted adapter')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def code(code,text,target,grouped=False):
    if code is None:return None
    # E82's original grouped validator requires evidence wholly in one position.
    # This is validation of the unchanged group code, never a position estimator.
    if isinstance(text,list):
        require(grouped and bool(text),'positions list only for original E82 native groups')
        require(all(isinstance(p,dict) and isinstance(p.get('readout'),str) and 'position' in p for p in text),'original position/readout records')
        require(len({p['position'] for p in text})==len(text),'unique original positions')
        if code.get('category')=='UNPARSEABLE':
            core.score(code,target,'')
        else:
            evidence=code.get('evidence');require(isinstance(evidence,str),'original evidence string')
            matching=[p['readout'] for p in text if core.normalize(evidence) in core.normalize(p['readout'])]
            require(bool(matching),'group evidence wholly in one original position; no concatenation')
            core.score(code,target,matching[0])
    else:
        core.score(code,target,text)
    return None if code['category']=='UNPARSEABLE' else code

def evaluate(meta,measurements):
    systems={}
    require(set(measurements)==set(meta['systems']),'exact planned system grid')
    for system,targets in measurements.items():
        require(system in ('oracle','nla','outside','qwen_self'),'registered comparison systems')
        needed={'S'} if meta['bank']=='E81' else {'belief','truth'} if meta['bank']=='E82' and meta['cohort']!='no_canonical_truth' else {'belief'} if meta['bank']=='E82' else {'truth'}
        require(set(targets)==needed,'original target judgments; no invented truth')
        letters=meta['target_letters_by_system'].get(system) if 'target_letters_by_system' in meta else meta.get('target_letters')
        require(isinstance(letters,dict) and set(letters)==needed,'exact per-system target mapping')
        values={};named=False;missing=False
        for target,data in targets.items():
            letter=letters[target];require(letter in ('A','B'),'CPU original target mapping')
            require(data['target_letter']==letter,'letter must match original sealed system/target map; no rewritten codes')
            c=code(data['code'],data['text'],letter,grouped=meta['bank']=='E82' and system!='outside')
            if c is None:missing=True;values[target]=None;continue
            named|=c['category']=='states_value'
            values[target]=core.score(c,letter,data['text']) if target=='S' else int(c['category']=='states_value' and letter in c['values'])
        # E82 naming cohort requires complete belief/truth judgments as in E82.
        if missing and meta['bank']=='E82':values={k:None for k in values}
        systems[system]=dict(values,named=None if missing else named)
    return dict(meta,systems=systems)

def inputs(s):
    ip=Path(s['inventory_seal']).resolve();commit=s['inventory_commit']
    require(len(commit)==40 and all(c in '0123456789abcdef' for c in commit),'full inventory commit')
    blob=subprocess.check_output(['git','show',commit+':'+str(ip.relative_to(ROOT))],cwd=ROOT)
    require(hashlib.sha256(blob).hexdigest()==s['inventory_sha256'],'committed inventory')
    inv=core.verify(ip,s['inventory_sha256']);require(inv['experiment']=='E107','inventory experiment')
    require('INVENTORY.json' in inv['files'] and len(inv['e81_rows'])==37 and len(set(inv['e81_rows']))==37,'all37 original E81 rows')
    metadata=read(ip.parent/'INVENTORY.json');by=core.unique(metadata)
    require(set(inv['surviving_e82_rows']) and inv['surviving_e86_rows'],'surviving original banks')
    for bank in ('E82','E86'):
        entry=s['prior_analyses'][bank];seal=core.verify(entry['seal'],entry['sha256'])
        require('ANALYSIS' in str(seal.get('status','')) or seal.get('status')=='COMPLETE_ONCE','prior registered analysis must be sealed')
    op=Path(s['output_seal']);seal=core.verify(op,s['output_sha256'])
    require(seal['experiment']=='E107' and seal['status']=='COMPLETE' and seal['inventory_sha256']==s['inventory_sha256'],'complete bound E107 bank')
    require(seal['route_verified'] is True and seal['redaction_audit_complete'] is True and seal['same_bank_rubrics'] is True,'existing route/rubric/privacy receipts')
    require(seal['outside_generation']==dict(model='google/gemini-3.1-flash-lite',provider='google-vertex/global',temperature=0,max_tokens=256,ZDR=True,data_collection='deny',fallbacks=False),'frozen outside describer')
    sources=seal['source_seals'];ss=[core.verify(x['seal'],x['sha256']) for x in sources]
    require('MEASUREMENTS.json' in seal['files'],'sealed measurement index')
    measurements=core.unique(read(op.parent/'MEASUREMENTS.json'));require(set(measurements)==set(by),'full original item inventory')
    out=[];identities=set();cache={}
    for ident,meta in by.items():
        require(meta['bank'] in ('E82','E86','E81'),'registered bank')
        k=(meta['bank'],meta['row'],meta['item_id']);require(k not in identities,'unique source item');identities.add(k)
        if meta['bank']=='E82':require(meta['row'] in inv['surviving_e82_rows'] and meta['cohort'] in ('belief_wrong','belief_right','no_canonical_truth'),'frozen belief classification')
        elif meta['bank']=='E86':require(meta['row'] in inv['surviving_e86_rows'],'original E86 row')
        else:require(meta['row'] in inv['e81_rows'],'original E81 row')
        require('outside' in meta['systems'],'outside for every source item')
        required={'outside','oracle','nla','qwen_self'} if meta['bank']=='E81' else {'outside','oracle','nla'}
        unavailable=meta.get('unavailable_systems',{})
        require(set(meta['systems'])|set(unavailable)==required and not set(meta['systems'])&set(unavailable) and all(isinstance(v,str) and v for v in unavailable.values()),'explicit frozen availability for every comparison')
        values={}
        for system,targets in measurements[ident]['systems'].items():
            values[system]={}
            for target,fields in targets.items():
                require(set(fields)=={'text','code','target_letter'},'exact source text/code fields')
                values[system][target]={}
                for field,ref in fields.items():
                    ix=ref['seal_index'];require(ref['member'] in ss[ix]['files'],'sealed original source')
                    cache_key=(ix,ref['member'])
                    if cache_key not in cache:cache[cache_key]=read(Path(sources[ix]['seal']).parent/ref['member'])
                    value=cache[cache_key]
                    for key in ref['keys']:value=value[key]
                    values[system][target][field]=value
        out.append(evaluate(meta,values))
    require({x['row'] for x in out if x['bank']=='E81'}==set(inv['e81_rows']),'all37 row inventories')
    require({x['row'] for x in out if x['bank']=='E82'}==set(inv['surviving_e82_rows']),'all surviving E82 rows')
    require({x['row'] for x in out if x['bank']=='E86'}==set(inv['surviving_e86_rows']),'all surviving E86 rows')
    def ref(r):
        ix=r['seal_index'];require(type(ix) is int and 0<=ix<len(ss) and r['member'] in ss[ix]['files'],'sealed audit pointer')
        value=read(Path(sources[ix]['seal']).parent/r['member'])
        for key in r['keys']:value=value[key]
        return value
    audit=ref(seal['redaction_audit']);mapping=ref(seal['redaction_plan_map'])
    plan_ref=seal['redaction_original_plan'];plan_ix=plan_ref['seal_index']
    require(sources[plan_ix]['sha256']==mapping['plan_seal_sha256'] and ss[plan_ix]['files'][plan_ref['member']]==mapping['plan_member_sha256'],'original frozen plan hashes')
    affected=affected_items(out,audit,mapping,ref(plan_ref))
    return out,inv,affected

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=read(a.spec);items,inv,affected=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['output_sha256']),commit)
    result=analyze(items,inv['e81_rows']);write(out/'RESULTS.json',result);write(out/'REDACTION_SENSITIVITY.json',sensitivity(items,inv['e81_rows'],affected));write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E107',status='COMPLETE_ONCE',code_commit=commit,output_sha256=s['output_sha256'],inventory_sha256=s['inventory_sha256'])
if __name__=='__main__':main()
