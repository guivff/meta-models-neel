"""§210 E102 paired evaluation of original and retrained frozen readers."""
import argparse
from .common import *
TRAINED=('nesting_depth','indent_level','page_range_digit')
HELD=('line_length','container_after_move','holder_after_handovers','branch_taken','var_type_at_use','bracket_depth')
CONTENT=('format_plan','language_plan','hedge_plan','fact_recall','language_continuation','tense_implicit')
SETS={'trained':TRAINED,'held_out':HELD,'content':CONTENT}

def prepare(records,inventory):
    require(set(inventory['readers'])<= {'oracle','nla'} and 'oracle' in inventory['readers'],'Oracle required; optional gated NLA')
    groups={}
    for x in records:
        reader,group=x['reader'],x['set'];require(reader in inventory['readers'] and x['split']=='test','reader/test-only evaluation')
        require(group in ('trained','held_out','content','placebo','workspace'),'registered evaluation set')
        if group in SETS:require(x['row'] in SETS[group],'registered row')
        key=(reader,group,x['row']);groups.setdefault(key,[]).append(x)
        if group=='workspace':
            require(x['family'] and x['frozen_scorer_sha256'],'frozen WorkspaceBench scorer')
            for arm in ('original','retrained'):
                require(type(x[arm+'_pass']) is bool,'binary frozen-family pass')
        elif group=='placebo':
            require(x['property']=='any_registered_bookkeeping_value','placebo covers all three trained properties')
            for arm in ('original','retrained'):
                code=x[arm+'_placebo_code'];text=x[arm+'_text']
                require(set(code)=={'statement','evidence'} and (type(code['statement']) is bool or code['statement'] is None),'placebo judgment schema')
                require(isinstance(code['evidence'],str) and core.normalize(code['evidence']) in core.normalize(text),'placebo evidence substring')
                require(bool(code['evidence'])==(code['statement'] is True),'placebo evidence presence')
                x[arm+'_statement']=None if code['statement'] is None else int(code['statement'])
        else:
            for arm in ('original','retrained'):
                code=x[arm+'_code'];text=x[arm+'_text']
                score=core.score(code,x['target'],text)
                x[arm+'_score']=score
                x[arm+'_statement']=None if score is None else int(code['category']=='states_value' and bool(code['values']))
    for reader in inventory['readers']:
        gate=inventory['feasibility'][reader]
        require(gate['status']=='PASS' and gate['base_frozen'] is True and gate['steps']>=10 and gate['greedy_reproductions']==3,'feasibility gate')
        require(gate['adapter']==('olens_s3d_rl600' if reader=='oracle' else gate['adapter']),'correct reader adapter, never reconstructor')
        for group,rows in SETS.items():
            for row in rows:
                n=inventory['counts'][reader][group][row]
                require(type(n) is int and 0<=n<=84,'frozen available count')
                if group!='held_out':require(n==84,'all84 trained/content')
                xs=groups.get((reader,group,row),[])
                require(len(xs)==n and len({x['item_id'] for x in xs})==n,'exact paired row inventory')
                if row=='bracket_depth':require(all(x['rung']=='L0' for x in xs),'E62 held-out L0 only')
        for group,n in [('placebo',500),('workspace',518)]:
            xs=[x for x in records if x['reader']==reader and x['set']==group]
            require(len(xs)==n and len({x['item_id'] for x in xs})==n,'full placebo/workspace inventory')
    return records

def paired(xs,field='score'):
    a={x['item_id']:x['original_'+field] for x in xs};b={x['item_id']:x['retrained_'+field] for x in xs}
    return dict(original=stat(a),retrained=stat(b),difference=stat(b,a))

def analyze(records,inventory):
    result=dict(experiment='E102',bootstrap=dict(draws=DRAWS,seed=SEED,unit='item',paired=True),readers={},not_run_readers=inventory.get('not_run_readers',{}))
    for reader in inventory['readers']:
        xs=[x for x in records if x['reader']==reader];rows={};sets={}
        for group,names in SETS.items():
            rows[group]={row:paired([x for x in xs if x['set']==group and x['row']==row]) for row in names}
            # Set estimand pools items, while retaining row in the identity.
            pooled=[dict(x,item_id=x['row']+':'+x['item_id']) for x in xs if x['set']==group]
            sets[group]=paired(pooled)
        placebo=paired([x for x in xs if x['set']=='placebo'],'statement')
        ws=[x for x in xs if x['set']=='workspace'];workspace=paired(ws,'pass')
        family={f:paired([x for x in ws if x['family']==f],'pass') for f in sorted({x['family'] for x in ws})}
        trained=rows['trained'];held=rows['held_out'];content=rows['content']
        v1=count([both(ge(t['retrained'],.50),low(t['retrained'],.30),le(t['original'],.10)) for t in trained.values()],2)
        placebo_ok=le(placebo['retrained'],.10)
        v1['trained_rows_status']=v1['status'];v1['placebo_condition']=placebo_ok
        v1['status']='NOT MET' if placebo_ok is False or v1['status']=='NOT MET' else 'NOT EVALUABLE' if placebo_ok is None or v1['status']=='NOT EVALUABLE' else 'MET'
        v2=count([both(ge(t['difference'],.20),low(t['difference'],0)) for t in held.values()],3)
        v3=count([ge(t['difference'],-.10) for t in content.values()]+[ge(workspace['difference'],-.05)],7)
        falsifier=count([le(t['retrained'],.10) for t in trained.values()],3)
        result['readers'][reader]=dict(rows=rows,sets=sets,placebo=placebo,workspace=workspace,workspace_families=family,rules={'R-V1':v1,'R-V2':v2,'R-V3':v3,'falsifier':falsifier})
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=read(a.spec)
    require(s['experiment']=='E102','experiment');records,bundle,inventory=normalized(s,'E102');prepare(records,inventory)
    loss,ls=load(s['training'],'TRAINING_LOSS.json')
    require(ls.get('experiment')=='E102' and ls.get('test_used') is False and ls.get('judge_outputs_used') is False,'dev-only training receipt')
    require(ls.get('recipe')==dict(rank=16,learning_rate=.0001,steps=300,batch=16,seed=20261029),'fixed training recipe')
    out=reserve('E102',s,commit);result=analyze(records,inventory);result['training_loss']=loss
    finish('E102',s,commit,result,out)
if __name__=='__main__':main()
