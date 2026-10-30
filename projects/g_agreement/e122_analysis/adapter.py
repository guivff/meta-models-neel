"""E122 sealed CPU inputs and three independently guarded analysis phases."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from projects.g_agreement.understand.wmech2 import core
from . import rules

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CANONICAL = Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/e122')
E85_BANK_SHA = '1c966b10b67de74dafeadf51daf9f2a7496bf6578ff66566dde76d060c436478'
E85_PRIVATE_SHA = '5ed311882f9b06f208776d1636567267570ed33bbf83b39d5da9732559975a44'
CONTRAST_SHA = '23c9b0f8c75c869d36868ed3b44480ac53ef2346cc0438f5ee2eb84d5623f414'
require, read, write, sha = core.require, core.read, core.write, core.sha


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',',':'), allow_nan=False).encode()).hexdigest()


def measurement_id(carrier, condition):
    return hashlib.sha256(f'E122:{carrier}:{condition}'.encode()).hexdigest()


def committed():
    for name, expected in read(HERE / 'DEPENDENCIES.json').items():
        require(sha(ROOT / name) == expected, 'pinned dependency ' + name)
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            blob = subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))], cwd=ROOT)
            require(hashlib.sha256(blob).hexdigest() == sha(p), 'uncommitted adapter ' + p.name)
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def committed_file(path, commit, expected):
    path = Path(path).resolve()
    require(len(commit)==40 and all(c in '0123456789abcdef' for c in commit), 'full frozen source commit')
    repo = Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=path.parent,text=True).strip())
    blob = subprocess.check_output(['git','show',commit+':'+str(path.relative_to(repo))],cwd=repo)
    require(hashlib.sha256(blob).hexdigest()==expected==sha(path), 'frozen committed source bytes')


def original_cells(bank_path, private_path):
    bank = core.verify(bank_path,E85_BANK_SHA)
    require(bank['experiment']=='E85' and 'MANIFEST.json' in bank['files'], 'original E85 bank')
    manifest = read(Path(bank_path).parent/'MANIFEST.json')
    require(manifest['files']['LABELS.PRIVATE.json']==E85_PRIVATE_SHA==sha(private_path), 'original CPU quartet labels')
    rows = read(private_path)
    cells = [dict(id=x['public_id'],source_id=x['id'],quartet_id=x['matched_set'],genre=x['genre'],addressed=x['addressed'],split=x['split']) for x in rows]
    rules.validate_cells(cells)
    # Original genre templates differ, while each addressed/unaddressed twin
    # shares its original body. Preserve those source items verbatim.
    for x in rows:
        twin = next(y for y in rows if y['matched_set']==x['matched_set'] and y['genre']==x['genre'] and y['addressed']!=x['addressed'])
        require(twin['body']==x['body'], 'matched addressed twin body')
    return cells


def contrasts(document):
    require(document['schema']=='E122_CONTINUATION_CONTRASTS_V1' and document['E85_bank_seal_sha256']==E85_BANK_SHA,
            'original W-text E122 contract')
    require(document['dev_quartets']==50 and document['test_quartets']==100, 'original 50 dev / 100 test quartets')
    xs = document['contrasts']
    require(len(xs)==4 and len({x['id'] for x in xs})==4, 'four ordered frozen contrast pairs')
    normalized=[]
    for x in xs:
        require(isinstance(x['id'],str) and x['id'], 'original contrast identity')
        ids = [[x['positive']['token_ids'],x['negative']['token_ids']]]
        require(len(ids)==1 and len(ids[0])==2 and all(isinstance(y,list) and y and all(type(t)is int and t>=0 for t in y) for y in ids[0]), 'one original tokenized A/B pair')
        normalized.append(dict(id=x['id'],candidate_ids=ids,candidate_ids_sha256=digest(ids)))
    return normalized


def freeze(spec, commit):
    """Input-only preparation; no acquisition scores may enter this phase."""
    cp = Path(spec['contrast_seal'])
    require(spec['contrast_sha256']==CONTRAST_SHA, 'exact original W-text freeze')
    committed_file(cp,spec['contrast_commit'],spec['contrast_sha256'])
    source = core.verify(cp,spec['contrast_sha256'])
    require(source['experiment']=='E122' and source['status']=='FROZEN_BEFORE_E122_CAPTURE' and 'CONTRASTS.json' in source['files'], 'W-text pre-capture contrast freeze')
    document = read(cp.parent/'CONTRASTS.json')
    contrasts(document)
    cells = original_cells(spec['e85_bank_seal'],spec['e85_private'])
    out = CANONICAL/'frozen_inputs'
    ignored=subprocess.run(['git','check-ignore','-q',str(out)],cwd=CANONICAL.parents[3])
    require(ignored.returncode==0, 'private CPU inventory must be git-ignored')
    out.mkdir(parents=True,exist_ok=False)
    write(out/'INVENTORY.json',cells)
    write(out/'S_PAIRINGS.json',rules.same_condition_pairs(cells))
    # Byte-for-byte source copy, no template, token, direction or order edits.
    (out/'CONTRASTS.json').write_bytes((cp.parent/'CONTRASTS.json').read_bytes())
    write(out/'PROVENANCE.json',dict(contrast_source_seal=str(cp),contrast_source_sha256=spec['contrast_sha256'],
          contrast_commit=spec['contrast_commit'],e85_bank_seal=spec['e85_bank_seal'],e85_bank_sha256=E85_BANK_SHA,
          original_cpu_private_path=spec['e85_private'],original_cpu_private_sha256=E85_PRIVATE_SHA))
    core.seal(out,'INPUT_SEAL.json',experiment='E122',status='SOURCE_ONLY_CUSTODY_BOUND',code_commit=commit,
              block=44,dev_quartets=50,test_quartets=100,same_value_seed=20261030,contrast_source_sha256=spec['contrast_sha256'],labels_cpu_only=True,
              source_e85_bank_sha256=E85_BANK_SHA,source_e85_private_sha256=E85_PRIVATE_SHA,
              S_recipe='Guiv clarification: addressed same-value S; frozen runner cyclic permutation seed20261030, sequential genres0/1')
    return out/'INPUT_SEAL.json'


def frozen_inputs(spec):
    p = Path(spec['frozen_seal'])
    s = core.verify(p,spec['frozen_sha256'])
    require(s['experiment']=='E122' and s['status']=='SOURCE_ONLY_CUSTODY_BOUND' and s['block']==44 and s['same_value_seed']==20261030
            and s['source_e85_bank_sha256']==E85_BANK_SHA and s['source_e85_private_sha256']==E85_PRIVATE_SHA, 'original frozen E122 inputs')
    source = read(p.parent/'PROVENANCE.json')
    require(source['contrast_source_sha256']==CONTRAST_SHA, 'original W-text contrast freeze')
    cells = original_cells(source['e85_bank_seal'],source['original_cpu_private_path'])
    require(cells==read(p.parent/'INVENTORY.json'), 'unchanged original source order/identities/factors/splits')
    require(read(p.parent/'S_PAIRINGS.json')==rules.same_condition_pairs(cells), 'original seeded same-condition donors')
    cseal = core.verify(source['contrast_source_seal'],source['contrast_source_sha256'])
    require(cseal['files']['CONTRASTS.json']==sha(p.parent/'CONTRASTS.json'), 'exact W-text contrast bytes')
    return p, cells, contrasts(read(p.parent/'CONTRASTS.json'))


def phase_seal(phase):
    p = CANONICAL/phase/'ANALYSIS_SEAL.json'
    s = core.verify(p,sha(p))
    require(s['experiment']=='E122' and s['phase']==phase and s['status']=='COMPLETE_ONCE', 'previous phase complete once')
    return p,s


def prior_selection(spec):
    p,s = phase_seal('dev_selection')
    require(s['frozen_sha256']==spec['frozen_sha256'], 'same dev-selection inventory')
    return p,read(p.parent/'SELECTION.json')


def pair_score(pairs):
    # Same full frozen pair difference as E105 normalize, with fixed A-minus-B
    # rather than E100's donor-label orientation. No length normalization.
    require(isinstance(pairs,list) and len(pairs)==2 and all(type(x) in (float,int) and math.isfinite(x) and x<=0 for x in pairs), 'finite nonpositive raw full-continuation pair')
    return float(pairs[0]-pairs[1])


def measurements(spec, phase, frozen, cells, contrast_defs, selection_path=None, gate_path=None):
    p = Path(spec['output_seal'])
    s = core.verify(p,spec['output_sha256'])
    require(s['experiment']=='E122' and s['status']=='COMPLETE' and s['phase']==phase and s['frozen_sha256']==spec['frozen_sha256'], 'complete same-inventory phase acquisition')
    require(s['score_mode']=='full_continuation_logprob_sum' and s['block']==44 and 'MEASUREMENTS.json' in s['files'], 'raw frozen continuation scores at original block')
    if selection_path is not None:
        require(s['selection_seal_sha256']==sha(selection_path), 'dev-selected contrast bound before native test analysis')
    if gate_path is not None:
        require(s['gate_seal_sha256']==sha(gate_path) and s['supplied_vector_mode'] is True and s['vectors_unscaled'] is True, 'R-BEV1 before T/S scoring')
    sources = s['source_seals']
    seals = [core.verify(x['seal'],x['sha256']) for x in sources]
    require(bool(seals) and all(x['status']=='COMPLETE' for x in seals), 'only complete raw acquisitions, no failed pilots')
    frozen_meta=read(frozen)
    contexts=[]
    for entry,source in zip(sources,seals):
        if entry.get('format')=='trackq_e122_232':
            from .producer_q232 import context
            contexts.append(context(entry,source,frozen,cells,contrast_defs))
        elif entry.get('format')=='i2_e122_logits232_v1':
            from .producer232 import context
            require(phase!='transplant', 'native producer cannot certify transplants')
            contexts.append(context(entry,source,frozen,cells,contrast_defs))
        else:
            require('format' not in entry, 'unknown producer envelope')
            require(source['experiment']=='E122' and source['contrast_source_sha256']==frozen_meta['contrast_source_sha256']
                    and source['source_e85_bank_sha256']==E85_BANK_SHA, 'raw run bound original frozen contrast/E85 source')
            contexts.append(None)
    split = 'dev' if phase=='dev' else 'test'
    selected = [x for x in cells if x['split']==split and (phase!='transplant' or x['addressed']==0)]
    index = core.unique(read(p.parent/'MEASUREMENTS.json'))
    require(set(index)=={x['id'] for x in selected}, 'full exact phase grid, never drop cells')
    frozen_order = [x['id'] for x in contrast_defs]
    if phase!='dev':
        _,choice = prior_selection(spec)
        selected_id = choice['selected_contrast_id']
        require(selected_id in frozen_order, 'chosen original contrast')
        require(s['selected_contrast_id']==selected_id, 'no post-test contrast substitution')
    donors = {x['id']:x for x in read(frozen.parent/'S_PAIRINGS.json')}
    member_cache={}

    def raw(ref, carrier, condition):
        ix = ref['seal_index']
        require(type(ix)is int and 0<=ix<len(seals) and ref['member'] in seals[ix]['files'], 'sealed original raw source member')
        cache_key=(ix,ref['member'])
        if cache_key not in member_cache:
            member_cache[cache_key]=read(Path(sources[ix]['seal']).parent/ref['member'])
        obj=member_cache[cache_key]
        require(isinstance(ref['keys'],list) and all(type(k) in (int,str) for k in ref['keys']), 'JSON source pointer')
        for k in ref['keys']:
            obj=obj[k]
        expected = carrier if condition=='0' else measurement_id(carrier,condition)
        if contexts[ix] is not None and contexts[ix].get('mode')=='TrackQ':
            original=contexts[ix]['mapping'][carrier,condition]
            require(all(obj[k]==original[k] for k in ('id','inventory_id','base_id','row','condition','block','vector_index')), 'original TrackQ raw/input identity')
            order=contexts[ix]['order']
        elif contexts[ix] is not None:
            require(condition=='0' and obj['id']==carrier and obj['source_block']==44 and obj['split']==contexts[ix]['splits'][carrier], 'original I2 native identity/site/split')
            order=contexts[ix]['order']
        else:
            require(obj['id']==expected and obj['condition']==condition and obj['block']==44, 'original measured carrier/condition/site identity')
            order=obj['contrast_ids']
        if condition!='0' and contexts[ix] is None:
            require(obj['base_id']==carrier and obj['donor_id']==donors[carrier][condition+'_donor_id'], 'original twin/same-condition donor identity')
        pairs = obj['pair_logprobs']
        require(order==frozen_order or phase!='dev' and order==[selected_id], 'original all-four or frozen selected pair inventory')
        require(isinstance(pairs,list) and len(pairs)==len(order), 'exact frozen pair inventory')
        by_id={x['id']:x for x in contrast_defs}
        if contexts[ix] is None:
            require(obj['contrast_ids']==order and obj['candidate_ids_sha256']==digest([by_id[c]['candidate_ids'][0] for c in order]), 'raw original candidate order/token identities')
        # Parts may share one launch (§232 cap note). For non-dev phases,
        # compute only the selected contrast, never all-four test statistics.
        if phase=='dev':return dict(zip(order,[pair_score(x) for x in pairs]))
        return pair_score(pairs[order.index(selected_id)])

    rows = []
    for cell in selected:
        m=index[cell['id']]
        if phase=='transplant':
            require(set(m['conditions'])=={'T','S'}, 'both complete T/S conditions')
            scores={c:raw(m['conditions'][c],cell['id'],c) for c in ('T','S')}
        else:
            value=raw(m['ref'],cell['id'],'0')
            scores=value if phase=='dev' else {selected_id:value}
        rows.append(dict(cell,scores=scores))
    return rows


def claim(phase, spec, commit):
    return core.claim(dict(analysis=str(CANONICAL/phase),guard=str(CANONICAL/(phase+'_ONCE.json')),
                           output_sha256=spec['output_sha256']),commit)


def execute(spec, action, commit):
    expected_phase={'select-dev':'dev_selection','native-test':'native_test','transplant':'transplant'}[action]
    require(not (CANONICAL/expected_phase).exists() and not (CANONICAL/(expected_phase+'_ONCE.json')).exists(), 'analysis output exists or guard consumed; no replay')
    frozen,cells,defs = frozen_inputs(spec)
    if action=='select-dev':
        rows=measurements(spec,'dev',frozen,cells,defs)
        out=claim('dev_selection',spec,commit)
        result=rules.select_dev(rows,[x['id'] for x in defs])
        write(out/'SELECTION.json',result)
        phase='dev_selection'
    elif action=='native-test':
        selection,choice=prior_selection(spec)  # no test source read before selection
        rows=measurements(spec,'native_test',frozen,cells,defs,selection_path=selection)
        out=claim('native_test',spec,commit)
        result=rules.native_test(rows,choice['selected_contrast_id'])
        write(out/'RESULTS.json',result)
        phase='native_test'
    else:
        selection,choice=prior_selection(spec)
        gate,gmeta=phase_seal('native_test')
        require(gmeta['frozen_sha256']==spec['frozen_sha256'], 'same native test inventory')
        result_gate=read(gate.parent/'RESULTS.json')
        require(result_gate['R_BEV1']=='MET' and result_gate['selected_contrast_id']==choice['selected_contrast_id'], 'R-BEV1 gate before reading transplant source')
        rows=measurements(spec,'transplant',frozen,cells,defs,selection_path=selection,gate_path=gate)
        out=claim('transplant',spec,commit)
        result=rules.transplant(rows,result_gate)
        write(out/'RESULTS.json',result)
        phase='transplant'
    write(out/'BINDING.json',spec)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E122',phase=phase,status='COMPLETE_ONCE',code_commit=commit,
              frozen_sha256=spec['frozen_sha256'],output_sha256=spec['output_sha256'],judging=False)
    return out/'ANALYSIS_SEAL.json'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['freeze','select-dev','native-test','transplant'])
    parser.add_argument('--spec',required=True)
    args=parser.parse_args()
    commit=committed()
    spec=read(args.spec)
    seal=freeze(spec,commit) if args.action=='freeze' else execute(spec,args.action,commit)
    print(str(seal),sha(seal))


if __name__=='__main__':
    main()
