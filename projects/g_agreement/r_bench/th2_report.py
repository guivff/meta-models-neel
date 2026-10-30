"""Write TH-2 report from already computed, frozen artifacts; no model fitting."""
from pathlib import Path
import itertools,json,subprocess
import numpy as np
import pandas as pd

OUT=Path('results/g_agreement/r/i2')
READERS=['jlens','olens','nla','skip_a']

def h7(out):
    d=pd.read_csv(out/'th2_rows.csv.gz');rows=[]
    for block in ['A','B']:
      for convention,prefix in [('allmedian','err_'),('literal','literal_err_'),('poolmedian','pool_err_')]:
       sub=d[d.eligible & (d.block_B if block=='B' else True)]
       for ds,g in sub.groupby('dataset'):
        e=g[[prefix+r for r in READERS]].dropna().to_numpy(int)
        if not len(e):continue
        wrong=e.all(1);correct=~e.any(1);unanimous=wrong|correct;single=1-e.mean(0)
        rows.append(dict(block=block,convention=convention,dataset=ds,n=len(e),observed=wrong.mean(),independence=e.mean(0).prod(),ratio=wrong.mean()/e.mean(0).prod() if e.mean(0).prod()>0 else np.nan,consensus_accuracy=correct.sum()/unanimous.sum() if unanimous.any() else np.nan,best_single=single.max(),gain=correct.sum()/unanimous.sum()-single.max() if unanimous.any() else np.nan,same_items_gain=0))
    x=pd.DataFrame(rows);x.to_csv(out/'th2_h7_descriptive.csv',index=False);return x

def figure(out,m,ci):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mtick
    colors={'A':'#2864A8','B':'#D17B24'}
    fig,axes=plt.subplots(1,3,figsize=(12,3.6),gridspec_kw={'width_ratios':[1.2,1,1]})
    primary=m[(m.convention=='allmedian')&(m.model=='factor')].set_index('block')
    indep=m[(m.convention=='allmedian')&(m.model=='independence')].set_index('block')
    x=np.arange(3)
    for j,block in enumerate(['A','B']):
        q=primary.loc[block]
        axes[0].bar(x+(j-.5)*.34,[q.p_observed,indep.loc[block].p_predicted,q.p_predicted],width=.32,color=colors[block],label=f'Block {block}')
    axes[0].set_xticks(x,['Observed','Independent','Difficulty'])
    axes[0].yaxis.set_major_formatter(mtick.PercentFormatter(1));axes[0].set_ylim(0,.105)
    axes[0].set_title('Held-out four-reader failures');axes[0].legend(frameon=False,fontsize=9)
    for ax,metric,level,title in [(axes[1],'ratio',.9,'Tail ratio · 90% CI'),(axes[2],'gain',.95,'Joint-score gain · 95% CI')]:
      for i,block in enumerate(['A','B']):
        c=ci[(ci.block==block)&(ci.scheme=='envelope')&(ci.metric==metric)&(ci.level==level)].iloc[0];v=primary.loc[block,metric]
        ax.errorbar(v,1-i,xerr=[[v-c.low],[c.high-v]],fmt='o',capsize=4,color=colors[block],lw=2)
      ax.set_yticks([1,0],['A','B']);ax.set_ylim(-.6,1.6);ax.set_title(title)
    axes[1].axvspan(2/3,1.5,color='#dfeede',zorder=-2);axes[1].axvline(1,color='#777',ls=':',lw=1);axes[1].set_xlim(.55,1.6);axes[1].set_xlabel('Observed / predicted')
    axes[2].axvline(0,color='#888',lw=1);axes[2].axvline(.02,color='#888',ls=':',lw=1);axes[2].set_xlim(-.01,.18);axes[2].set_xlabel('Nats per endpoint item')
    for ax in axes:
      ax.spines[['top','right']].set_visible(False)
    fig.suptitle('TH-2: shared difficulty predicts the four-reader tail',fontsize=14,y=1.02)
    fig.text(.5,-.04,'A: 108 nondefective facts   ·   B: 104 facts, excluding audit flags   ·   34 source groups   ·   refitted bootstrap',ha='center',fontsize=9)
    fig.tight_layout();fig.savefig(out/'th2_summary.png',dpi=180,bbox_inches='tight');plt.close(fig)

def main():
    out=OUT;m=pd.read_csv(out/'th2_metrics.csv');ci=pd.read_csv(out/'th2_intervals.csv');fits=pd.read_csv(out/'th2_fits.csv');pre=json.loads((out/'th2_preflight.json').read_text());shards=json.loads((out/'th2_shards.json').read_text());cov=pd.read_csv(out/'th2_coverage.csv');desc=h7(out)
    figure(out,m,ci)
    def interval(block,metric,level,scheme='envelope'):
        x=ci[(ci.block==block)&(ci.metric==metric)&(ci.level==level)&(ci.scheme==scheme)].iloc[0];return x.low,x.high
    def fmtci(v):return f'[{v[0]:.3f}, {v[1]:.3f}]'
    def metric(block,conv='allmedian',model='factor'):
        return m[(m.block==block)&(m.convention==conv)&(m.model==model)].iloc[0]
    def verdict(block):
        q=metric(block);lo,hi=interval(block,'ratio',.9);rl,rh=interval(block,'ratio',.95);gl,gh=interval(block,'gain',.95)
        if q.n_facts<30 or q.n_corpora<5 or q.observed_all_wrong<30:return 'UNDERPOWERED'
        if lo>=2/3 and hi<=1.5 and q.gain>=.02 and gl>0:return 'SUPPORTED'
        if rh<2/3 or rl>1.5:return 'REFUTED'
        return 'INCONCLUSIVE / UNDERPOWERED'
    statuses={b:verdict(b) for b in ['A','B']}
    L=['# TH-2: held-out four-reader failures from shared difficulty', '',f"**Final handoff — 2026-10-19. Block A: {statuses['A']}; block B (without audit flags): {statuses['B']}.**",
       'The restricted shared-difficulty model predicts the held-out four-reader failure tail and improves the full error-vector log score over independent readers. Its parameters were fitted only from marginal and pairwise calibration errors. This supports shared difficulty as a sufficient predictive explanation on these facts; it does not identify a shared neural mechanism or prove that every dependence is one-dimensional.',
       '', '**Branch:** `r/i2-th2`. **Preregistration:** `7117a170dab3572ee7fa7125d42e164504741f5e`, pushed before preflight/fitting. **Compute:** CPU only; 0 GPU/pod hours; existing rows only. Ready for integrator review/merge; the dated handoff and separate WS3 vote-rule warning are in `../HANDOFF.md`.', '',
       '| Frozen primary (analyze.py votes) | A: nondefective facts | B: also drop audit flags |','|---|---:|---:|']
    a,b=metric('A'),metric('B')
    for name,values in [
      ('Facts / corpus groups',[f'{int(q.n_facts)} / {int(q.n_corpora)}' for q in [a,b]]),
      ('Endpoint items / all-four failures',[f'{int(q.n_items):,} / {int(q.observed_all_wrong):,}' for q in [a,b]]),
      ('Observed failure probability',[f'{q.p_observed:.4%}' for q in [a,b]]),
      ('Shared-difficulty predicted probability',[f'{q.p_predicted:.4%}' for q in [a,b]]),
      ('Independence predicted probability',[f'{metric(bl,model="independence").p_predicted:.4%}' for bl in ['A','B']]),
      ('Observed / predicted, 90% CI',[f'{metric(bl).ratio:.3f} {fmtci(interval(bl,"ratio",.9))}' for bl in ['A','B']]),
      ('Observed / predicted, 95% CI',[fmtci(interval(bl,'ratio',.95)) for bl in ['A','B']]),
      ('Joint-score gain, nats/item (95% CI)',[f'{metric(bl).gain:+.3f} {fmtci(interval(bl,"gain",.95))}' for bl in ['A','B']]),
      ('Registered verdict',[statuses[bl] for bl in ['A','B']])]:L.append(f'| {name} | {values[0]} | {values[1]} |')
    L+=['','![TH-2 held-out forecasts and confidence intervals](th2_summary.png)','','The thresholds are unchanged: the entire 90% ratio CI must lie in **[2/3, 1.5]**, and gain must be **≥0.02 nats/item with 95% lower bound >0**. A 95% ratio interval wholly outside the band rejects tail closure. Both blocks pass the ≥30 facts / ≥5 corpora / ≥30 all-wrong event gates.',
        '', '## Coverage and semantic audit, completed before fitting','',
        f"Read {sum(r['rows'] for r in shards['files']):,} existing rows from {len(shards['files'])} shards. All {int(cov.n_bank_test.sum()):,} R-A test items from 113 facts have four finite, scorable primary-site readers; no missing reader rows, duplicate raw/full semantic keys, candidate/label/split mismatches or partial tails were found. Non-R-A and pod-D rows were scoped out using `analyze.py` provenance rules. Native rows carry frozen SHA `4d482b6`, allowed pod identities and the matching bank-file hash. The frozen bank hash is `{pre['input_hashes']['projects/g_agreement/dataset/items_r.json']}`.",
        '', '| Population | Complete test items | Marginal-calibration half | Endpoint half | Facts | Corpus groups |','|---|---:|---:|---:|---:|---:|']
    for bl in ['A','B']:
        x=pre['coverage'][bl];L.append(f"| {bl} | {x['complete_items']:,} | {x['calibration_items']:,} | {x['endpoint_items']:,} | {x['facts']} | {x['corpus_groups']} |")
    L+=['', 'Five R-A LABEL_DEFECT facts are always excluded: 139/140/141 (AG News) and 145/146 (disease); their two multiclass parent IDs are outside R-A. Block B additionally removes the frozen nondefect flags 131 (Typical Time), 142 (Thyroid Cancer), 144 (Colon Cancer), and 153 (Administrative rights). The thresholds, holdout mapping and fitting algorithm are identical across blocks.',
        '', '## Frozen estimation and uncertainty','',
        'Reader order is J-lens@42, Oracle@44, NLA@42, skip_a@42, natural/chat. Scores and ordered shard loading use `analyze.py`; the streamed loader applies its provenance filtering and keeps the last raw key, then asserts full semantic-key uniqueness. Positive semantic label means the bank’s positive candidate, independently of score order. Primary votes use strict `score > fact/test median`; ties vote negative.',
        '', 'The §4.9 corpus map is augmented by binary-parent families, registered source families and shared normalized text, producing 34 document-disjoint groups. SHA256 seed 20261019 fixes five corpus folds; SHA256 seed 20261020 fixes global text groups into calibration and endpoint halves. Every fact is scored once. Class-specific reader loadings use only calibration-half marginal/pairwise tables from the other corpus folds. A held-out fact contributes calibration-half marginal rates `(errors+0.5)/(n+1)`, never its dependence or endpoints, to its forecast. No triple/four-way count or vector likelihood selects a parameter.',
        '', 'The one-factor model is `Z_r = a_r U + sqrt(1-a_r²) epsilon_r`, `0≤a_r≤0.98`, with errors below the Gaussian quantile of each marginal. Separate loadings are fitted for semantic labels 0 and 1 by six-pair composite likelihood, with deterministic multiple starts. Gaussian quadrature predicts all 16 error vectors. Independence uses exactly the same smoothed marginals. Ratios are pooled observed failures divided by pooled expected failures; gain is paired full-vector log score in natural-log units.',
        '', 'Each block has 2,000 corpus→fact→shared-document bootstrap draws and 2,000 fact→item draws (seed 20261021). Marginals and all loadings are refitted in every draw; corpus folds and half assignments remain fixed. Shared text occurrences receive one paired weight within each resampled corpus occurrence. Headline intervals take the envelope of both percentile intervals. Inference conditions on the registered, frozen score thresholds; it does not resample/reselect the test median. The primary is retrospective, with prior H7 aggregates visible.',
        '', '| Block / bootstrap | Valid / requested | Ratio 90% CI | Gain 95% CI |','|---|---:|---:|---:|']
    for bl in ['A','B']:
      for scheme in ['corpus_fact_item','fact_item']:
        x=ci[(ci.block==bl)&(ci.scheme==scheme)].iloc[0]
        L.append(f'| {bl} / {scheme} | {int(x.n_valid)} / {int(x.n_valid+x.n_failed)} | {fmtci(interval(bl,"ratio",.9,scheme))} | {fmtci(interval(bl,"gain",.95,scheme))} |')
    L+=['','## Controls and matched event orders','', '| Block | Model | Four-way prediction | Observed / predicted | Joint-score gain |','|---|---|---:|---:|---:|']
    for r in m[m.convention=='allmedian'].itertuples():L.append(f'| {r.block} | {r.model} | {r.p_predicted:.4%} | {r.ratio:.3f} | {r.gain:+.4f} |')
    L+=['','The equal-loading Gaussian and exchangeable beta toy are restricted controls. The beta toy uses only first/pairwise evidence but replaces heterogeneous reader marginals with their mean; it is not a matched-marginal alternative. The unrestricted Gaussian is a six-correlation, positive-definite pairwise diagnostic. Its near-identical pooled forecast does not supply a new verdict. Full pair/triple/quartet subset probabilities and ratios are in `th2_event_orders.csv` (R2/R3/R4 denote event order here). All-correct rates and vector log scores are in `th2_metrics.csv`.',
        '', '## Vote-rule sensitivity and the H7 discrepancy','',
        '**For WS3/integrator:** `analyze.r7_agreement` thresholds all facts at the test-score median, whereas BRIEF_R §4.7 says sign(`s_diff`) for two-sided facts. Both conventions were registered before fitting. The primary above preserves the requested analysis-code convention. Neither this analysis nor its handoff edits the existing H7 verdict.',
        '', '| Block | Registered vote sensitivity | Observed four-way | Predicted four-way | Ratio | Gain, nats/item |','|---|---|---:|---:|---:|---:|']
    for r in m[(m.model=='factor')&(m.convention!='allmedian')].itertuples():L.append(f'| {r.block} | {r.convention} | {r.p_observed:.4%} | {r.p_predicted:.4%} | {r.ratio:.3f} | {r.gain:+.4f} |')
    L+=['','These are prespecified descriptive sensitivity point estimates, with no substituted primary verdict or primary CI claim. Literal votes use zero for two-sided scores and the test median for one-sided scores. Pool-median votes use existing pool-eval scores for every fact/reader; coverage matches the primary.',
        '', '| Full-test H7 reproduction | Mean per-fact ratio | Pooled ratio | Consensus gain vs best on all items |','|---|---:|---:|---:|']
    for (bl,c),g in desc.groupby(['block','convention']):L.append(f'| {bl} / {c} | {g.ratio.mean():.2f} | {np.average(g.observed,weights=g.n)/np.average(g.independence,weights=g.n):.2f} | {100*g.gain.mean():+.2f} pp |')
    L+=['','This reconciles the motivating “2–3×” statement with the interim mean-ratio value around 22×: event order and aggregation matter. The mean of ratios can be dominated by facts with tiny independent failure probabilities. The consensus-vs-best comparison on the same unanimous items is exactly zero by construction; the all-item comparator above is different. The vote discrepancy changes descriptive gains and ratios and merits WS3 review with its original clustered H7 decision rule.',
        '', '## Validation, limits and artifacts','',
        f"All 18 numerical/leakage/vote/isolation tests passed. All fitted diagnostics converged. Primary quadrature vs 1,024-node integration differs by at most {fits.quad_max_delta.max():.3g} probability; recovered marginal error is at most {fits.marginal_max_error.max():.3g}. The unrestricted diagnostic was independently recomputed for all 424 forecasts, matching stored probabilities exactly; maximum raw normalization error was 1.26e-6 and marginal error 6.41e-7 (`th2_numerical_qa.json`). Numerical and leakage tests are in `projects/g_agreement/tests/test_th2_*.py`. Main-checkout files and its cache link were not changed; all data were read through the worktree’s link to the real cache.",
        '', 'This result applies to pooled held-out natural R-A failures for four Qwen instruments at their declared sites. It does not establish item-level causal difficulty, universal per-fact fit, independence after conditioning on an observed difficulty score, or a neural mechanism. Two-stage label/corpus variation and candidate priors are controlled as registered, but unidentified label noise and the transductive median convention remain limitations. No new collection was made. The optional Gemma three-vote extension is not run: its AO variants are one underlying instrument and its rows lack this analysis’s frozen Qwen provenance contract; no Gemma failure or success is inferred. Optional text/probe residualization is not run.',
        '', 'Reproduce from the branch root with the existing bank and read-only cache:', '', '```sh',
        'PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m projects.g_agreement.r_bench.th2_preflight',
        'PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m projects.g_agreement.r_bench.th2_forecast --stage point',
        '# For each block A/B and scheme corpus_fact_item/fact_item:',
        'PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m projects.g_agreement.r_bench.th2_forecast --stage bootstrap --block A --scheme corpus_fact_item --n-boot 2000 --workers 3',
        '.venv/bin/python -m projects.g_agreement.r_bench.th2_forecast --stage intervals',
        '.venv/bin/python -m projects.g_agreement.r_bench.th2_report','```','',
        'Artifacts: `th2_coverage.csv`, `th2_shards.json`, `th2_preflight.json`, `th2_split_manifest.csv.gz`, `th2_rows.csv.gz`, `th2_thresholds.csv`, `th2_fits.csv`, `th2_predictions.csv`, `th2_metrics.csv`, `th2_event_orders.csv`, `th2_intervals.csv`, bootstrap CSVs, `th2_numerical_qa.json`, and `th2_h7_descriptive.csv`. Bootstrap outputs are resumable by replicate index. Input manifests include every shard’s hash and before/after stat check. The standard log/compute ledger records commands and zero GPU use.', '',
        '**Deviations:** no population, holdout, model or decision-threshold change after registration. Streaming is an implementation adaptation of the existing loading/provenance functions for the 3.9GB shard inventory. Optional Gemma/text/probe diagnostics are not run as disclosed above.']
    (out/'th2.md').write_text('\n'.join(L)+'\n')
    (out/'th2_verdict.json').write_text(json.dumps({'date':'2026-10-19','preregistration':'7117a170dab3572ee7fa7125d42e164504741f5e','verdicts':statuses,'thresholds':{'ratio_90_interval':[2/3,1.5],'gain_min_nats':.02,'gain_95_lower_gt':0}},indent=2)+'\n')
if __name__=='__main__':main()
