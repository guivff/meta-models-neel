"""§223.3 report projection of existing sealed E94 sufficient counts only.
No item reclassification, judge/model calls, bootstrap, or original once rerun.
Original sealed report and verdicts stay byte-for-byte unchanged.
"""
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
import json,hashlib,math
R=Path.cwd();PUB=R/'cache/g_agreement/i2/publication'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def fraction(k,n):
 if not n:return dict(k=k,n=n,rate=None,Wilson95=None)
 z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;s=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return dict(k=k,n=n,rate=p,Wilson95=[max(0,c-s),min(1,c+s)])
def project(source):
 rows=[]
 for bank,b in sorted(source['banks'].items()):
  if bank.startswith('E67'):
   grouped=defaultdict(lambda:dict(n=0,correct_agreement=0,wrong_agreement=0))
   for key,x in b['strata'].items():
    parts=key.split('|');assert len(parts)==6,'E67 privacy-key shape drift';row='|'.join(parts[:4]);m=x['metrics'];v=grouped[row];v['n']+=m['n'];v['correct_agreement']+=m['confusion']['correct']['correct'];v['wrong_agreement']+=m['confusion']['wrong']['wrong']
   for row,x in sorted(grouped.items()):
    n=x['correct_agreement']+x['wrong_agreement'];rows.append(dict(bank=bank,row=row,kind='SEPARATE_INCOMPATIBLE_CLAIM_DIAGNOSTIC',paired_n=x['n'],agreement_precision=fraction(x['correct_agreement'],n),coverage=fraction(n,x['n']),source='sum original sealed strata confusion counts; private prompt-item keys omitted'))
  else:
   for row,x in sorted(b['strata'].items()):
    m=x['metrics'];assert m['ensemble']['precision']==m['P_correct_given_agree_both_mention']
    rows.append(dict(bank=bank,row=row,kind='VALUE_GROUNDED',paired_n=m['n'],agreement_precision=m['ensemble']['precision'],coverage=m['ensemble']['coverage'],pairing=x['pairing'],source='exact original sealed per-stratum metrics'))
 return rows

def main():
 base=PUB/'results/g_agreement/understand/e94/analysis_once_20261028';ref=read(base/'SEALED_ANALYSIS_REF.json');original=Path(ref['original_directory']);assert sha(original/'ANALYSIS_SEAL.json')==ref['original_analysis_seal_sha256']
 seal=read(original/'ANALYSIS_SEAL.json')
 for n,h in seal['files'].items():assert sha(original/n)==h,'original sealed E94 drift'
 source=read(original/'RESULTS.json');rows=project(source)
 out=R/'results/g_agreement/understand/e94/within_row_precision_223';assert not out.exists();out.mkdir(parents=True)
 result=dict(experiment='E94',authority='§223 item3/directGuiv',kind='REPORT_ONLY_SEALED_AGGREGATE_PROJECTION',source_analysis_seal_sha256=ref['original_analysis_seal_sha256'],source_results_sha256=sha(original/'RESULTS.json'),pooled_value_grounded=source['pooled_value_grounded'],rows=rows,unavailable=source['unavailable'],no_new_model_or_judge_calls=True,no_bootstrap_or_item_rescoring=True,no_original_once_guard_consumed=True)
 (out/'WITHIN_ROW_PRECISION.json').write_text(json.dumps(result,indent=2)+'\n')
 def rate(v):return 'N/E'if v['rate']is None else f"{v['rate']:.4f}"
 def interval(v):return 'N/E'if v['Wilson95']is None else f"[{v['Wilson95'][0]:.4f}, {v['Wilson95'][1]:.4f}]"
 lines=['','## §223 item3: within-row agreement precision and coverage','','Report-only projection of the original sealed E94 aggregates. Agreement precision is correct / decisive same-value agreements; both-no-mention agreements are excluded. Coverage is decisive same-value agreements / common-parseable paired items, within the same row. Zero decisive agreements give N/E precision. Pooled metrics above are unchanged.','','Within-row reporting removes selection between rows from the pooled comparison; it does not control unmeasured difficulty within a row. Wilson95 intervals and denominators are shown. The original missing/unmatched rules remain unchanged.','','| Bank | Row | Paired n | Correct / decisive agreements | Precision | Wilson95 | Coverage |','|---|---|---:|---:|---:|---|---:|']
 for x in rows:
  if x['kind']!='VALUE_GROUNDED':continue
  p=x['agreement_precision'];lines.append(f"| {x['bank']} | {x['row'].replace('|',' / ')} | {x['paired_n']} | {p['k']}/{p['n']} | {rate(p)} | {interval(p)} | {rate(x['coverage'])} |")
 lines+=['','### Separate E67 claim diagnostics','','E67 uses an incompatible claim rubric and remains excluded from the value-grounded pool. Its diagnostic rows aggregate condition/arm strata while omitting private prompt-item IDs and hashes. These figures are not shared-value agreement precision.','','| Bank | Condition/arm diagnostic row | Paired n | Correct / decisive agreements | Diagnostic precision | Wilson95 | Coverage |','|---|---|---:|---:|---:|---|---:|']
 for x in rows:
  if x['kind']=='VALUE_GROUNDED':continue
  p=x['agreement_precision'];lines.append(f"| {x['bank']} | {x['row'].replace('|',' / ')} | {x['paired_n']} | {p['k']}/{p['n']} | {rate(p)} | {interval(p)} | {rate(x['coverage'])} |")
 lines+=['','The original E76 placebo-unavailability caveat at this source freeze remains separate; this projection does not claim completion of the full §214 item8 placebo extension. No sealed bank verdict or original analysis output was changed.']
 (out/'REPORT_WITHIN_ROW_223.md').write_text((base/'REPORT.md').read_text()+'\n'.join(lines)+'\n')
 (out/'PUBLICATION_SEAL.json').write_text(json.dumps(dict(experiment='E94',status='REPORT_ONLY_WITHIN_ROW_223',at_utc=datetime.now(timezone.utc).isoformat(),source_analysis_seal_sha256=ref['original_analysis_seal_sha256'],projection_code_sha256=sha(Path(__file__)),files={p.name:sha(p)for p in out.iterdir()if p.is_file()}),indent=2)+'\n')
 print(json.dumps(dict(value_grounded_rows=sum(x['kind']=='VALUE_GROUNDED'for x in rows),separate_claim_diagnostic_rows=sum(x['kind']!='VALUE_GROUNDED'for x in rows),rows_with_estimable_value_precision=sum(x['kind']=='VALUE_GROUNDED'and x['agreement_precision']['n']>0 for x in rows),pooled_precision_unchanged=source['pooled_value_grounded']['ensemble']['precision']['rate'],original_analysis_untouched=True)))
if __name__=='__main__':main()
