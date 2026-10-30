"""DESCRIPTIVE arithmetic only from sealed §79 results; no fits/scores/resampling."""
from __future__ import annotations
import argparse,hashlib,json,math,statistics,subprocess
from pathlib import Path
from . import corpus as C,features as F

STRUCTURES={
 'bracket depth':('paren_depth','square_depth','brace_depth','bracket_depth'),
 'table column':('table_column',),
 'line index':('line_index',),
 'quote state':('inside_string','inside_single_quote','inside_double_quote','inside_triple_quote'),
}

def mean(rows,key):
 values=[r[key]['auroc'] if key in ('probe','native_true') else r[key] for r in rows]
 return statistics.mean(values) if values else None

def describe(analysis,out):
 analysis,out=Path(analysis),Path(out)
 raw=(analysis/'RESULTS.json').read_bytes();top_bytes=(analysis/'TOP10.json').read_bytes();results=json.loads(raw);top=json.loads(top_bytes);seal=json.loads((analysis/'ANALYSIS_SEAL.json').read_text());receipt=json.loads((analysis/'S84_SELECTION_RECEIPT.json').read_text())
 for name,blob in [('RESULTS.json',raw),('TOP10.json',top_bytes)]:
  if hashlib.sha256(blob).hexdigest()!=seal['files'][name]:raise ValueError('sealed result mismatch '+name)
 if hashlib.sha256(top_bytes).hexdigest()!=receipt['selection_sha256']:raise ValueError('selection receipt mismatch')
 committed=subprocess.check_output(['git','show',receipt['source_commit']+':'+receipt['selection_file']],cwd=C.ROOT)
 if committed!=top_bytes:raise ValueError('committed selection bytes changed')
 rows=results['rows'];by={(r['feature'],r['reader']):r for r in rows};features=sorted({r['feature'] for r in rows})
 if len(by)!=len(rows) or len(rows)!=2*len(features):raise ValueError('reader-feature coverage')
 for r in rows:
  if r['probe'] is None:raise ValueError('missing probe; denominator must be stated '+r['feature'])
  if r['class_label']!=F.BY_ID[r['feature']].kind:raise ValueError('class differs from frozen registry')
  if r['evaluable']!=(r['probe']['auroc']>=.85 and r['native_mismatched']['auroc']<=.60):raise ValueError('registered gate flag mismatch')
 selected=[r['feature'] for r in top['candidates']]
 if selected!=receipt['section79_features'] or receipt['section81_features']!=[]:raise ValueError('ordered selection differs')
 classes=[]
 for cls in F.CLASSES:
  rr={reader:[r for r in rows if r['class_label']==cls and r['reader']==reader] for reader in ('olens','nla')}
  record={'class':cls,'features':len(rr['olens']),'by_reader':{}}
  for reader,group in rr.items():
   passing=[r for r in group if r['evaluable']]
   record['by_reader'][reader]={'site':group[0]['site'],'passing_features':len(passing),'all_retained':{'mean_probe_auroc':mean(group,'probe'),'mean_reader_auroc':mean(group,'native_true'),'mean_gap':mean(group,'gap')},'registered_gate_passing':{'mean_probe_auroc':mean(passing,'probe'),'mean_reader_auroc':mean(passing,'native_true'),'mean_gap':mean(passing,'gap')}}
  classes.append(record)
 top_rows=[{'feature':f,'class':F.BY_ID[f].kind,**{name:by[f,name] for name in ('olens','nla')}} for f in selected]
 structures=[]
 for label,families in STRUCTURES.items():
  ids=[f for f in features if F.BY_ID[f].family in families];registered=[f.id for f in F.FEATURES if f.family in families]
  rec={'group':label,'frozen_families':list(families),'retained_features':ids,'pre_capture_dropped_features':sorted(set(registered)-set(ids)),'by_reader':{},'rows':[{'feature':f,**{name:by[f,name] for name in ('olens','nla')}} for f in ids]}
  for reader in ('olens','nla'):
   group=[by[f,reader] for f in ids];passing=[r for r in group if r['evaluable']]
   rec['by_reader'][reader]={'n':len(group),'passing_features':len(passing),'all_retained_mean_gap':mean(group,'gap'),'registered_gate_passing_mean_gap':mean(passing,'gap')}
  structures.append(rec)
 # Reproduce original primary point estimates arithmetically; no new inference.
 o_cs=[r for r in rows if r['reader']=='olens' and r['evaluable'] and r['class_label'] in ('count-like','state-like')];o_sem=[r for r in rows if r['reader']=='olens' and r['evaluable'] and r['class_label']=='semantic']
 h1=mean(o_cs,'gap')-mean(o_sem,'gap')
 pairs=[by[f,'olens']['gap']-by[f,'nla']['gap'] for f in features if F.BY_ID[f].kind in ('count-like','state-like') and by[f,'olens']['evaluable'] and by[f,'nla']['evaluable']]
 h2=statistics.mean(pairs)
 if not math.isclose(h1,results['claims'][0]['point'],abs_tol=1e-12) or not math.isclose(h2,results['claims'][1]['point'],abs_tol=1e-12):raise ValueError('registered primary cohort reconstruction mismatch')
 data={'label':'DESCRIPTIVE','section':79,'source_results_sha256':C.sha(analysis/'RESULTS.json'),'source_analysis_seal_sha256':C.sha(analysis/'ANALYSIS_SEAL.json'),'source_selection_sha256':C.sha(analysis/'TOP10.json'),'selection_source_commit':receipt['source_commit'],'means':'equal weight per feature; all retained and registered gate-passing cohorts reported separately; native probe44 for Oracle44, probe42 for NLA42','uncertainty':'per-feature intervals copied from sealed results only; no new CI/resampling or inferential rule','classes':classes,'top10':top_rows,'w1_like_structures':structures,'unchanged_primary_claims':results['claims']}
 out.mkdir(parents=True,exist_ok=False);C.save(out/'TABLES.json',data)
 def num(x):return '—' if x is None else f'{x:.4f}'
 def auc(x):return f"{x['auroc']:.4f} [{x['lo']:.4f}, {x['hi']:.4f}]"
 def gap(r):return num(r['gap'])+f" [{r['gap_ci95'][0]:.4f}, {r['gap_ci95'][1]:.4f}]"
 lines=['# §79 — DESCRIPTIVE summaries of sealed natural-text results','','No new scores, probe fits, selection, sign changes, bootstrap or decision rules. Original H1 and H2 remain NOT MET. Means below weight each feature equally; thresholds of the same family remain separate frozen features. Natural text means the frozen mixed prose/Python/LaTeX/Markdown corpus, not prose alone.','','## 1. Class counts and means','','Passing means the original native-site probe AUROC ≥0.85 and mismatched AUROC ≤0.60, exactly the sealed `evaluable` flag. All 95 retained features have probe estimates at both sites. Oracle and NLA use different native-site probes.','','All retained features (including those failing gates; no new CI for descriptive class means):','','| Class | Features | Oracle pass | NLA pass | Probe44 mean | Oracle44 mean | Probe42 mean | NLA42 mean |','|---|---:|---:|---:|---:|---:|---:|---:|']
 for c in classes:
  o,n=c['by_reader']['olens'],c['by_reader']['nla'];lines.append(f"| {c['class']} | {c['features']} | {o['passing_features']} | {n['passing_features']} | {num(o['all_retained']['mean_probe_auroc'])} | {num(o['all_retained']['mean_reader_auroc'])} | {num(n['all_retained']['mean_probe_auroc'])} | {num(n['all_retained']['mean_reader_auroc'])} |")
 lines+=['','Original reader-specific gate-passing cohorts (denominators can differ between readers):','','| Class | Oracle n | Probe44 mean | Oracle44 mean | Gap44 mean | NLA n | Probe42 mean | NLA42 mean | Gap42 mean |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for c in classes:
  o,n=c['by_reader']['olens'],c['by_reader']['nla'];a,b=o['registered_gate_passing'],n['registered_gate_passing'];lines.append(f"| {c['class']} | {o['passing_features']} | {num(a['mean_probe_auroc'])} | {num(a['mean_reader_auroc'])} | {num(a['mean_gap'])} | {n['passing_features']} | {num(b['mean_probe_auroc'])} | {num(b['mean_reader_auroc'])} | {num(b['mean_gap'])} |")
 lines+=['','## 2. Exact committed top 10, original order','','AUROC [95% CI] copied from sealed results. Selection uses Oracle eligibility; NLA rows are reported regardless of their eligibility.','','| Feature | Probe44 | Oracle44 | Probe42 | NLA42 | NLA passes |','|---|---|---|---|---|---|']
 for t in top_rows:
  o,n=t['olens'],t['nla'];lines.append(f"| {t['feature']} | {auc(o['probe'])} | {auc(o['native_true'])} | {auc(n['probe'])} | {auc(n['native_true'])} | {'yes' if n['evaluable'] else 'no'} |")
 lines+=['','## 3. W1-like structures on natural text','','Named families are enumerated explicitly below; every retained feature in them is included. This is descriptive grouping by frozen definition, not a new endpoint or a natural-versus-W1 statistical comparison. Gap = native-site probe AUROC − reader AUROC.','','| Group | Retained | Oracle pass | NLA pass | All-feature gap44 | All-feature gap42 | Passing-only gap44 | Passing-only gap42 |','|---|---:|---:|---:|---:|---:|---:|---:|']
 for s in structures:
  o,n=s['by_reader']['olens'],s['by_reader']['nla'];lines.append(f"| {s['group']} | {len(s['retained_features'])} | {o['passing_features']} | {n['passing_features']} | {num(o['all_retained_mean_gap'])} | {num(n['all_retained_mean_gap'])} | {num(o['registered_gate_passing_mean_gap'])} | {num(n['registered_gate_passing_mean_gap'])} |")
 lines+=['','Bracket-depth features show large positive probe-minus-reader gaps; NLA’s mean gap is smaller here. Line-index rows have no gate-passing feature at either site, so their smaller raw gaps do not supply eligible evidence. Quote-state means across all retained features differ substantially from the one passing feature. These are descriptive observations only.']
 for s in structures:
  lines+=['',f"### {s['group']}",'','Families: '+', '.join(s['frozen_families'])+'. Pre-capture drops: '+(', '.join(s['pre_capture_dropped_features']) or 'none')+'.','','| Feature | Probe44 | Oracle44 | Gap44 [95%] | O gate | Probe42 | NLA42 | Gap42 [95%] | N gate |','|---|---:|---:|---|---|---:|---:|---|---|']
  for t in s['rows']:
   o,n=t['olens'],t['nla'];lines.append(f"| {t['feature']} | {num(o['probe']['auroc'])} | {num(o['native_true']['auroc'])} | {gap(o)} | {'pass' if o['evaluable'] else o['status']} | {num(n['probe']['auroc'])} | {num(n['native_true']['auroc'])} | {gap(n)} | {'pass' if n['evaluable'] else n['status']} |")
 lines+=['','No sign is flipped. Matched opposite-value mismatched rows are a permutation of the same native requests, not an independent validation set. No new inferential verdict is assigned.']
 (out/'TABLES.md').write_text('\n'.join(lines)+'\n')
 C.save(out/'VERIFICATION.json',{'label':'DESCRIPTIVE','source_seals_and_committed_selection_verified':True,'reader_feature_rows':len(rows),'retained_features':len(features),'all_probes_present':True,'class_labels_equal_frozen_registry':True,'passing_flags_equal_original_gates':True,'top10_order_unchanged':True,'original_h1_point_reproduced':h1,'original_h2_point_reproduced':h2,'no_fit_score_bootstrap_or_api':True,'tables_json_sha256':C.sha(out/'TABLES.json'),'tables_md_sha256':C.sha(out/'TABLES.md')})
 return data


def main():
 p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();describe(a.analysis,a.out)
if __name__=='__main__':main()
