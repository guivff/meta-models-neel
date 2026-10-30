"""Freeze E76's binary REPORTED registry exclusively from sealed bank analyses/definitions."""
import sys,json
from pathlib import Path
from collections import Counter,defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from common76 import *
JHERE=HERE/'judged';JCACHE=CACHE/'judged_v1';MECH=ROOT.parent/'wt-wmech';TEXT=ROOT.parent/'wt-wtext';INTERNALS=ROOT.parent/'wt-blindspot-internals'
BANK_SET=('E36','E49','E54','E56','E57','E59','E62')


class Sources:
    def __init__(self):self.files={};self.seals={}
    def bind(self,path,expected=None):
        p=Path(path).resolve();h=sha(p);require(expected is None or h==expected,'Frozen source mismatch')
        require(str(p) not in self.files or self.files[str(p)]==h,'Source changed');self.files[str(p)]=h;return p
    def sealed(self,folder,name='ANALYSIS_SEAL.json'):
        p=self.bind(Path(folder)/name);s=read(p);require(bool(s['files']),'Nonempty source seal')
        for n,h in s['files'].items():self.bind(p.parent/n,h)
        self.seals[str(p)]=sha(p);return s
    def load(self,path,expected=None):return read(self.bind(path,expected))


def reported(rate):return rate.get('S') is not None and rate['S']>=.2 and rate['CI95'][0]>0


def value_key(values):return json.dumps(values,ensure_ascii=False,sort_keys=True)


def freeze():
    require(not (JHERE/'ROW_INVENTORY.json').exists(),'Preserve frozen judged-row registry')
    src=Sources();catalog=src.load(HERE/'REGEX_CATALOG.json');claims=defaultdict(list);families={};properties={};exclusions=[]
    def claim(bank,row,reader,yes,rule,path,pointer):
        claims[bank,row].append({'reader':reader,'reported':bool(yes),'rule':rule,'source':str(Path(path).resolve()),'pointer':pointer})
    def define(bank,row,prop,values,weight=1):
        key=bank,row;properties[key]=prop;families.setdefault(key,Counter())[value_key(values)]+=weight
    # E36: existing §169 no-native-output forced-choice fallback, never labelled native.
    folder=HERE.parent/'e36/analysis_overnight149';src.sealed(folder);p=folder/'METRICS.json';metrics=src.load(p)
    defs=src.load(HERE.parent/'e36/ROW_DEFINITIONS.json')['rows']
    for row,d in defs.items():
        define('E36',row,d['definition'],d['values'])
        for reader,channel in (('oracle','oracle_descriptive'),('nla','nla')):
            v=metrics['metrics'][row].get(channel);claim('E36',row,reader,v is not None and v>=.8,'section169 no-native forced-choice AUROC>=0.80 (secondary channel)',p,['metrics',row,channel])
    # E49: use the sealed final native classification; the512-token supplement is separate provenance.
    folder=MECH/'results/g_agreement/understand/e49/job/analysis';src.sealed(folder);p=folder/'NATIVE_PRIMARY.json';d=src.load(p)
    definition_path=ROOT.parent/'wt-wlens/cache/g_agreement/understand/e52/E49-input/INPUT_SEAL.json'
    defs=src.load(definition_path)['rows']
    for row in d['rows']:
        define('E49',row,row,defs[row]['values'])
        for r,x in d['rows'][row].items():claim('E49',row,r,x['forecast_truth']=='REPORTED','sealed native forecast_truth',p,['rows',row,r,'forecast_truth'])
    sup=MECH/'results/g_agreement/understand/e49/nla_supplement/analysis_once_2026-10-28';src.sealed(sup);sp=sup/'SIDE_BY_SIDE.json'
    for row,x in src.load(sp).items():
        v=x['supplement_NLA'];claim('E49',row,'nla',v['correct_mention_rate']>=.1 and v['correct_mention_rate']>v['wrong_only_rate'],'sealed descriptive NLA512 supplement, original correct-value criterion',sp,[row,'supplement_NLA'])
    # E54: original native correct-value convention already used by the frozen E71 inventory.
    folder=INTERNALS/'results/g_agreement/understand/e5354/analysis_c9076571_541b23b1';src.sealed(folder);p=folder/'E54_RESULTS.json';d=src.load(p)
    defs=src.load(HERE.parent/'e54/CHANNEL_DEFINITIONS.json')
    for x in d['rows']:
        row=x['row'];define('E54',row,row,defs[row]['values'])
        for r,v in x['readers'].items():
            c=v['blind_counts'];correct=c['states_value_correct']+c['states_value_both']
            claim('E54',row,'oracle' if r=='olens' else r,correct/v['n']>=.1 and correct>c['states_value_wrong'],'existing E54/E71 native correct-including-both>=10% and >wrong-only',p,['rows',row,'readers',r])
    # E56 native text rows only; interventions do not create original-bank row identities.
    folder=MECH/'results/g_agreement/understand/e56/analysis402_once_2026-10-27';src.sealed(folder);p=folder/'NATIVE_RATES.json';rates=src.load(p)
    defs=src.load(HERE.parent/'e56/ROW_DEFINITIONS.json')['rows']
    for row,x in defs.items():define('E56',row,row,x['values'])
    for key,v in rates.items():
        reader,row,arm=key.split('|')
        if arm=='text':claim('E56',row,reader,reported(v),'section172 S>=0.20 and bootstrap lower>0',p,[key])
    # E57: original binary judge families and original native test sampling population.
    folder=MECH/'results/g_agreement/understand/e57/analysis402_once_2026-10-27';src.sealed(folder);p=folder/'RESULTS.json';d=src.load(p)
    spec=src.load(MECH/'results/g_agreement/understand/analysis402/E57_SPEC.json');inp=Path(spec['inputs']);s=src.load(inp/'INPUT_SEAL.json',spec['input_seal_sha256'])
    plan=src.load(inp/'RUN_PLAN.json',s['files']['RUN_PLAN.json'])
    for row,ids in plan['native_ids'].items():
        if row in ('capacity_list','category_switch'):
            exclusions.append({'bank':'E57','row':row,'reason':'EXCLUDED_REGISTERED_COUNT_MEASURE','reported_in_sealed_rates':any(reported(v) for k,v in d['rates'].items() if k.split('|')[1]==row)});continue
        for ident in ids:define('E57',row,plan['rows'][row]['canonical_row'],plan['judge_values'][ident])
    for key,v in d['rates'].items():
        reader,row=key.split('|');claim('E57',row,reader,reported(v),'section172 S>=0.20 and bootstrap lower>0',p,['rates',key])
    # E59/E62: exact original per-row A/B values, as used by their frozen judge exports.
    for bank,dirname in (('E59','analysis5968_once_2026-10-27'),('E62','analysis402_once_2026-10-27')):
        folder=MECH/f'results/g_agreement/understand/{bank.lower()}/{dirname}';src.sealed(folder);p=folder/'RESULTS.json';d=src.load(p)
        spec=src.load(MECH/f'results/g_agreement/understand/{bank.lower()}/job/ANALYSIS_SPEC.json')
        items=src.load(spec['private_items'],spec['private_items_sha256']);by=defaultdict(lambda:defaultdict(set))
        for x in items:
            if x['split']!='test':continue
            row=x['feature']
            if bank=='E62' and x['state']=='S6':continue
            by[row][x['label']].add(value_key(x['value']))
        for row,values in by.items():
            require(set(values)=={0,1} and all(len(v)==1 for v in values.values()),'One frozen value per class required')
            define(bank,row,row,[json.loads(next(iter(values[1]))),json.loads(next(iter(values[0])))])
        for key,v in d['rates'].items():
            reader,row=key.split('|');claim(bank,row,reader,reported(v),'section172 S>=0.20 and bootstrap lower>0',p,['rates',key])
    rows=[];defined={}
    for key,fs in sorted(families.items()):
        bank,row=key;terms=[]
        for i,(v,w) in enumerate(sorted(fs.items())):
            values=json.loads(v)
            if len(values)!=2 or values[0]==values[1] or any(not isinstance(x,(str,list)) or not x for x in values):continue
            terms.append({'family':i,'values':{'A':values[0],'B':values[1]},'weight':w})
        evidence=claims[key]
        if not terms:exclusions.append({'bank':bank,'row':row,'reason':'EXCLUDED_NON_BINARY_OR_IDENTICAL_VALUES'});continue
        if not any(x['reported'] for x in evidence):exclusions.append({'bank':bank,'row':row,'reason':'NO_REPORTED_READER_IN_SEALED_ANALYSIS'});continue
        rows.append({'bank':bank,'row':row,'property':properties[key],'families':terms,'reporting_claims':evidence})
        defined[key]=True
    listed={(x['bank'],x['row']) for x in exclusions}|set(defined)
    for x in catalog['rows']:
        key=x['bank'],x['row']
        if key in listed:continue
        exclusions.append({'bank':key[0],'row':key[1],'reason':'OUTSIDE_CLARIFICATION2_BANK_SET' if key[0] not in BANK_SET else 'EXCLUDED_EVALUATION_OR_NO_BINARY_SOURCE_PROPERTY'})
    total_families=sum(len(x['families']) for x in rows);n=min(50,5000//(4*total_families));require(n>0 and rows,'Positive uniform judged sample required')
    registry={'experiment':'E76','authority_commit':'f3fcb7153242faf61b385cbfea875aa174617584','status':'FROZEN_BEFORE_PLACEBO_TEXT_OR_JUDGMENT',
        'rows':rows,'excluded_rows':sorted(exclusions,key=lambda x:(x['bank'],x['row'])),'n_per_row_reader_pool':n,'binary_families':total_families,
        'expanded_records':4*n*total_families,'sample_seed':20261028,'full_regex_catalog_sha256':sha(HERE/'REGEX_CATALOG.json')}
    dump(JHERE/'ROW_INVENTORY.json',registry)
    JCACHE.mkdir(parents=True,exist_ok=False,mode=0o700);private=JCACHE/'SOURCE_BINDING.PRIVATE.json'
    private.write_text(json.dumps({'files':src.files,'analysis_seals':src.seals},indent=2,sort_keys=True)+'\n');private.chmod(0o600)
    dump(JHERE/'ROW_INVENTORY_SEAL.json',{'experiment':'E76','files':{'ROW_INVENTORY.json':sha(JHERE/'ROW_INVENTORY.json')},'source_binding_sha256':sha(private),
        'analysis_seals':src.seals,'placebo_readouts_opened':False,'judgments_opened':False})
    print(json.dumps({'rows':len(rows),'families':total_families,'n_per_cell':n,'records':registry['expanded_records']}))


if __name__=='__main__':freeze()
