"""Offline synthetic checks. Never reads real placebo text or judgments."""
import copy,importlib.util,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from core76 import *
import export76 as E
from redaction76 import redact


def registry(rows=2,multifamily=False):
    data=[]
    for i in range(rows):
        families=[{'family':f,'values':{'A':'cat','B':'dog'+str(f)},'weight':f+1} for f in range(2 if multifamily and i==0 else 1)]
        data.append({'bank':'SYNTHETIC','row':f'row{i:03d}','property':'Synthetic animal category','families':families})
    count=sum(len(x['families']) for x in data);n=min(50,5000//(4*count))
    return {'rows':data,'excluded_rows':[],'n_per_row_reader_pool':n,'binary_families':count,'expanded_records':4*n*count}


def records():
    return [{'id':f'{r}-{a}-{i}','reader':r,'arm':a,'pool_index':i,'repeat':0,'layer':44 if r=='oracle' else 42,
        'source_bank':i%5,'text':'cat dog0 dog1','native_max_new_tokens':512,'native_stop':'</explanation>'}
        for r in READERS for a in ARMS for i in range(N)]


def regex_fixture(reg):
    return {'rows':[{'bank':x['bank'],'row':x['row'],'regex_status':'AVAILABLE','readers':{
        r:{p:{'N_any_value':{'estimate':.8,'ci95':[.7,.9],'n_vectors':500},'S_regex':{'estimate':.1,'ci95':[0.,.2],'n_vectors':500}} for p in ARMS} for r in READERS}} for x in reg['rows']]}


class ExportTests(unittest.TestCase):
    def test_uniform_cap_counts_every_family_without_selective_row_cut(self):
        reg=registry(43,True);n=validate_registry(reg)
        self.assertEqual(n,min(50,5000//(4*44)))
        packet,mapping=build_export(records(),reg)
        self.assertEqual(len(packet),4*n*44);self.assertLessEqual(len(packet),5000)
        counts=defaultdict(set)
        for x in mapping:counts[x['bank'],x['row'],x['reader'],x['pool']].add(x['pool_index'])
        self.assertTrue(all(len(x)==n for x in counts.values()))

    def test_seed_determinism_content_independence_and_verbatim_fields(self):
        reg=registry(multifamily=True);a=records();packet,mapping=build_export(a,reg)
        self.assertEqual((packet,mapping),build_export(list(reversed(a)),reg))
        b=copy.deepcopy(a)
        for x in b:x['text']='' if x['pool_index']%2 else 'totally different'
        bp,bm=build_export(b,reg)
        self.assertEqual([x['id'] for x in packet],[x['id'] for x in bp])
        self.assertEqual([(x['id'],x['pool_index']) for x in mapping],[(x['id'],x['pool_index']) for x in bm])
        self.assertTrue(all(set(x)=={'id','property','values','readout'} for x in packet))
        first=sorted({x['pool_index'] for x in mapping if x['row']=='row000' and x['reader']=='nla' and x['pool']=='random'})
        self.assertEqual(first,sorted(np.random.default_rng(20261028).choice(500,reg['n_per_row_reader_pool'],replace=False).tolist()))
        native={x['id']:x for x in a};public={x['id']:x for x in packet}
        self.assertTrue(all(public[x['id']]['readout']==native[x['source_native_id']]['text'] for x in mapping))

    def test_private_fields_duplicate_ids_and_incomplete_expansion_stop(self):
        reg=registry();p,m=build_export(records(),reg)
        bad=copy.deepcopy(p);bad[0]['reader']='oracle'
        with self.assertRaises(ValueError):validate_export(bad,m,reg)
        with self.assertRaises(ValueError):validate_export(p[:-1],m,reg)
        bad=copy.deepcopy(m);bad[1]['id']=bad[0]['id']
        with self.assertRaises(ValueError):validate_export(p,bad,reg)
        bad=copy.deepcopy(m);bad[0]['pseudo_truth']='wrong'
        with self.assertRaises(ValueError):validate_export(p,bad,reg)

    def test_export_guard_is_once_only_and_private_map_stays_in_cache(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);here=root/'public';cache=root/'cache';here.mkdir();cache.mkdir();reg=registry(1)
            dump(here/'ROW_INVENTORY.json',reg);dump(here/'CODE_SEAL.json',{'files':{}})
            (here/'RUBRIC.txt').write_bytes((JHERE/'RUBRIC.txt').read_bytes())
            dump(cache/'SOURCE_BINDING.PRIVATE.json',{'files':{}})
            dump(here/'ROW_INVENTORY_SEAL.json',{'files':{},'source_binding_sha256':sha(cache/'SOURCE_BINDING.PRIVATE.json')})
            with patch.object(E,'JHERE',here),patch.object(E,'JCACHE',cache),patch.object(E,'ROOT',root),patch.object(E,'load_production',return_value=records()) as load,patch.object(E.subprocess,'run',return_value=type('R',(),{'returncode':0})()):
                E.main();first=sha(cache/'blind/JUDGE_PACKET.json')
                with self.assertRaises(FileExistsError):E.main()
                self.assertEqual(load.call_count,1)
            self.assertEqual(sha(cache/'blind/JUDGE_PACKET.json'),first)
            self.assertEqual(list(here.glob('*.PRIVATE.json')),[])
            self.assertEqual((cache/'GROUPING_MAP.PRIVATE.json').stat().st_mode&0o777,0o600)


class JudgmentTests(unittest.TestCase):
    def test_terminal_missing_is_not_silently_unparseable(self):
        copied=[{'id':'a','readout':'cat'}];code={'id':'a','category':'states_value','values':['A'],'evidence':'CAT'}
        kept={'id':'a','status':'KEPT','attempts':0,'code':code}
        self.assertEqual(join_terminal([kept],copied),{'a':code})
        missing={'id':'a','status':'UNPARSEABLE','attempts':2,'code':None}
        self.assertEqual(join_terminal([missing],copied),{'a':None})
        for bad in ([],[kept,kept],[{**missing,'attempts':1}],[{**kept,'status':'INVALID'}]):
            with self.assertRaises(ValueError):join_terminal(bad,copied)

    def test_kept_evidence_uses_actual_redacted_judge_copy(self):
        item={'id':'a','property':'kind','values':{'A':'cat','B':'dog'},'readout':'cat at /tmp/file.log and 192.0.2.1:80'}
        copy_,audit=redact([render(item,'rubric')],'E76',addresses=True)
        self.assertIn('[REDACTED_PATH]',copy_[0]['readout']);self.assertIn('[REDACTED_ADDRESS]',copy_[0]['readout'])
        self.assertEqual(audit['redacted_records'],1)
        c={'id':'a','category':'states_value','values':['A'],'evidence':'/tmp/file.log'}
        with self.assertRaises(ValueError):join_terminal([{'id':'a','status':'KEPT','attempts':0,'code':c}],copy_)
        c['evidence']='cat';self.assertEqual(join_terminal([{'id':'a','status':'KEPT','attempts':0,'code':c}],copy_)['a'],c)
        self.assertEqual(item['readout'],'cat at /tmp/file.log and 192.0.2.1:80')

    def test_categories_values_normalized_quotes_and_evidence(self):
        copied=[{'id':'a','readout':'“cat”—dog'}]
        code={'id':'a','category':'states_value','values':['B','A'],'evidence':'"CAT"-DOG'}
        self.assertEqual(join_terminal([{'id':'a','status':'KEPT','attempts':1,'code':code}],copied)['a'],code)
        for changes in ({'values':['A','A']},{'values':['C']},{'category':'silent'},{'evidence':''}):
            with self.assertRaises(ValueError):join_terminal([{'id':'a','status':'KEPT','attempts':0,'code':{**code,**changes}}],copied)

    def test_preserve_runner_valid_silent_evidence_without_reclassification(self):
        # The frozen readerbench validator allows a nonempty quote for silent.
        # Consumer must not reject a KEPT record or reinterpret its category.
        code={'id':'a','category':'silent','values':[],'evidence':'CAT'}
        result=join_terminal([{'id':'a','status':'KEPT','attempts':0,'code':code}],[{'id':'a','readout':'cat'}])
        self.assertEqual(result,{'a':code})

    def test_signed_N_both_neither_and_unparseable_denominator(self):
        row={'families':[{'family':0,'weight':1}]};entries=[{'id':str(i),'pool_index':i,'family':0,'pseudo_truth':'A'} for i in range(5)]
        codes={str(i):{'category':'states_value' if values else 'silent','values':values} for i,values in enumerate((['A'],['B'],['A','B'],[]))};codes['4']=None
        r=estimates(entries,codes,row,draws=100)
        self.assertEqual(r['kept'],4);self.assertEqual(r['UNPARSEABLE'],1)
        self.assertEqual(r['S']['estimate'],0);self.assertEqual(r['N_any_value']['estimate'],.75)
        sens=estimates(entries,codes,row,{'1'},draws=100)
        self.assertAlmostEqual(sens['S']['estimate'],1/3);self.assertAlmostEqual(sens['N_any_value']['estimate'],2/3)
        bad=estimates(entries,{x['id']:None for x in entries},row,draws=100)
        self.assertEqual(bad['status'],'NOT EVALUABLE');self.assertIsNone(bad['S']);self.assertIsNone(bad['N_any_value'])

    def test_frozen_family_weights_and_vector_cluster_bootstrap(self):
        row={'families':[{'family':0,'weight':1},{'family':1,'weight':3}]};entries=[];codes={}
        for i in range(4):
            for f in (0,1):
                ident=f'{i}-{f}';entries.append({'id':ident,'pool_index':i,'family':f,'pseudo_truth':'A'})
                codes[ident]={'category':'states_value','values':['A'] if f==0 else ['B']}
        r=estimates(entries,codes,row,draws=100)
        self.assertEqual(r['S'],{'estimate':-.5,'ci95':[-.5,-.5]});self.assertEqual(r['n_vectors_with_parseable_codes'],4)
        bad=estimates(entries,codes,row,{f'{i}-0' for i in range(4)},draws=100)
        self.assertEqual(bad['status'],'NOT EVALUABLE')

    def test_analysis_preserves_full_regex_and_redaction_sensitivity(self):
        reg=registry(1);p,m=build_export(records(),reg);codes={x['id']:{'category':'silent','values':[]} for x in m}
        regex=regex_fixture(reg);before=copy.deepcopy(regex);bad={m[0]['id']};codes[m[0]['id']]=None
        result=analyze(m,codes,reg,regex,bad)
        self.assertEqual(result['UNPARSEABLE'],1);self.assertEqual(result['redacted_pairs'],1);self.assertEqual(regex,before)
        for reader in READERS:
            for pool in ARMS:
                cell=result['rows'][0]['readers'][reader][pool]
                self.assertEqual(cell['sealed_full_regex'],regex['rows'][0]['readers'][reader][pool])
                self.assertEqual(cell['sealed_full_regex']['N_any_value']['n_vectors'],500)
        with self.assertRaises(ValueError):analyze(m,codes,reg,regex,{'unknown'})

    def test_full_once_analysis_writes_seal_and_refuses_second_score(self):
        spec=importlib.util.spec_from_file_location('judged_analysis76',JHERE/'analyze_once76.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        reg=registry(1);packet,m=build_export(records(),reg);terminal=[{'id':x['id'],'status':'KEPT','attempts':0,'code':{'id':x['id'],'category':'silent','values':[],'evidence':''}} for x in packet]
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);dump(p/'ROW_INVENTORY.json',reg);dump(p/'CODE_SEAL.json',{'files':{}})
            inputs=(reg,m,regex_fixture(reg),terminal,[render(x,'rubric') for x in packet],set(),'a'*64)
            with patch.object(module,'JHERE',p),patch.object(module,'load_sealed_inputs',return_value=inputs) as load:
                module.main()
                with self.assertRaises(ValueError):module.main()
                self.assertEqual(load.call_count,1)
            verify(p/'analysis_once_20261028',read(p/'analysis_once_20261028/ANALYSIS_SEAL.json'))

class CustodyTests(unittest.TestCase):
    def test_complete_sealed_terminal_and_exact_redaction_custody(self):
        spec=importlib.util.spec_from_file_location('custody_analysis76',JHERE/'analyze_once76.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);public=root/'public';cache=root/'cache';parent=root/'e76'
            public.mkdir();cache.mkdir();parent.mkdir();reg=registry(1)
            native=records()
            for x in native:x['text']='cat at /tmp/synthetic.log and 192.0.2.1:80'
            packet,mapping=build_export(native,reg);blind=cache/'blind';converted=cache/'converted';final=cache/'terminal/final'
            blind.mkdir();converted.mkdir();final.mkdir(parents=True)
            (public/'RUBRIC.txt').write_bytes((JHERE/'RUBRIC.txt').read_bytes())
            dump(public/'CODE_SEAL.json',{'files':{}});dump(public/'ANALYSIS_COMMAND_SEAL.json',{'files':{}})
            dump(public/'ROW_INVENTORY.json',reg);dump(public/'ROW_INVENTORY_SEAL.json',{'files':{'ROW_INVENTORY.json':sha(public/'ROW_INVENTORY.json')}})
            dump(blind/'JUDGE_PACKET.json',packet);(blind/'RUBRIC.txt').write_bytes((JHERE/'RUBRIC.txt').read_bytes())
            dump(blind/'BLIND_SEAL.json',{'experiment':'E76','files':{'JUDGE_PACKET.json':sha(blind/'JUDGE_PACKET.json'),'RUBRIC.txt':sha(blind/'RUBRIC.txt')}})
            dump(cache/'GROUPING_MAP.PRIVATE.json',{'CPU_only':True,'judge_or_pod_access_forbidden':True,'blind_seal_sha256':sha(blind/'BLIND_SEAL.json'),'pairs':mapping})
            manifest={'blind_directory':'cache/blind','blind_seal_sha256':sha(blind/'BLIND_SEAL.json'),'CPU_grouping_map_sha256':sha(cache/'GROUPING_MAP.PRIVATE.json'),'records':len(packet)}
            dump(public/'EXPORT_MANIFEST.json',manifest);dump(public/'ANALYSIS_SPEC.json',{'export_manifest_sha256':sha(public/'EXPORT_MANIFEST.json')})
            folder=parent/'regex_20261027';folder.mkdir();regex=regex_fixture(reg);regex['output_seal_sha256']=PRODUCTION_SEAL
            dump(folder/'FLOOR_TABLE.json',regex);dump(folder/'ANALYSIS_SEAL.json',{'files':{'FLOOR_TABLE.json':sha(folder/'FLOOR_TABLE.json')}})
            dump(converted/'PACKET.json',packet);(converted/'RUBRIC.txt').write_bytes((JHERE/'RUBRIC.txt').read_bytes())
            dump(converted/'PACKET_SEAL.json',{'experiment':'E76','source_seal_sha256':sha(blind/'BLIND_SEAL.json'),
                'source_packet_sha256':sha(blind/'JUDGE_PACKET.json'),'rubric_sha256':RUBRIC_SHA,
                'files':{n:sha(converted/n) for n in ('PACKET.json','RUBRIC.txt')}})
            copied,audit=redact([render(x,(JHERE/'RUBRIC.txt').read_text()) for x in packet],'E76',addresses=True)
            terminal=[{'id':x['id'],'status':'KEPT','attempts':0,'code':{'id':x['id'],'category':'silent','values':[],'evidence':''}} for x in packet]
            dump(final/'JUDGE_COPY.json',copied);dump(final/'PATH_REDACTION_AUDIT.json',audit);dump(final/'JUDGMENTS.json',terminal)
            dump(final/'START.json',{'packet_seal_sha256':sha(converted/'PACKET_SEAL.json')})
            def reseal():
                seal={'bank':'E76','channel':'placebo','status':'TERMINAL_BLIND_GRID_NO_ANALYSIS','packet_seal_sha256':sha(converted/'PACKET_SEAL.json'),
                    'files':{n:sha(final/n) for n in ('JUDGE_COPY.json','PATH_REDACTION_AUDIT.json','JUDGMENTS.json','START.json')}}
                (final/'RESULT_SEAL.json').write_text(json.dumps(seal))
                (final.parent/'VERIFIED_PULL.json').write_text(json.dumps({'issuer':'integrator','experiment':'E76_JUDGED','verified_complete':True,'privacy_and_budget_custody_verified':True,'n':len(packet),
                    'terminal_seal_sha256':sha(final/'RESULT_SEAL.json'),'converted_packet_seal_sha256':sha(converted/'PACKET_SEAL.json'),
                    'original_blind_seal_sha256':sha(blind/'BLIND_SEAL.json')}))
            reseal()
            with patch.object(m,'ROOT',root),patch.object(m,'JHERE',public),patch.object(m,'JCACHE',cache),patch.object(m,'HERE',parent),patch.object(m,'REGEX_SEAL',sha(folder/'ANALYSIS_SEAL.json')):
                loaded=m.load_sealed_inputs();self.assertEqual(len(loaded[3]),len(packet));self.assertEqual(len(loaded[5]),len(packet))
                self.assertFalse((public/'JUDGED_ANALYSIS.RUN_ONCE.json').exists())
                copied[0]['readout']+=' changed';(final/'JUDGE_COPY.json').write_text(json.dumps(copied));reseal()
                with self.assertRaisesRegex(ValueError,'judge-copy'):m.load_sealed_inputs()


if __name__=='__main__':unittest.main()
