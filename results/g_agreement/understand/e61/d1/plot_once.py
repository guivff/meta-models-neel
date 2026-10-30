"""§177 D1: all gated rows, signed native S, frozen categories, sealed E60 curves."""
from pathlib import Path
import json
import math
import os
import subprocess
import sys
import time
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e52'))
from build_basis import read,dump,sha
from run_labels import verify
BANKS=('W1','E36','W12','E49','E56','E57','E59')
READERS=('oracle','nla')
COLOURS={'bookkeeping':'#0072B2','delimiter':'#D55E00','syntactic':'#009E73','format':'#CC79A7','content':'#E69F00'}
MARKERS=dict(zip(BANKS,('o','s','D','^','v','P','X')))

def sealed(ref):
    p=Path(ref['path']).resolve();s=Path(ref['seal_path']).resolve()
    if sha(p)!=ref['sha256'] or sha(s)!=ref['seal_sha256']:raise ValueError('source hash differs')
    if (s.parent/ref['member']).resolve()!=p or read(s)['files'][ref['member']]!=ref['sha256']:raise ValueError('source file not bound to seal')
    return read(p)

def categories(ref):
    repo=Path(ref['repository']).resolve();p=repo/ref['repository_path']
    def committed(path,h):
        rel=str(path.relative_to(repo))
        if sha(path)!=h or subprocess.check_output(['git','show',ref['commit']+':'+rel],cwd=repo)!=path.read_bytes():raise ValueError('W-text category source must match committed bytes')
    committed(p,ref['sha256']);manifest=read(p)
    if manifest.get('outcome_files_opened') is not False:raise ValueError('description-only category provenance required')
    mapping={};aliases={}
    for name,h in manifest['assignment_files'].items():
        f=(p.parent/name).resolve()
        if not f.is_relative_to(p.parent.resolve()):raise ValueError('category path escapes manifest')
        committed(f,h)
        for r in read(f)['rows']:
            k=(r['bank'],r['row'])
            if r['category'] not in COLOURS or (k in mapping and mapping[k]!=r['category']):raise ValueError('invalid/conflicting category')
            mapping[k]=r['category']
    for name,h in manifest.get('condition_aliases',{}).items():
        f=(p.parent/name).resolve()
        if not f.is_relative_to(p.parent.resolve()):raise ValueError('alias path escapes manifest')
        committed(f,h);d=read(f)
        for row,canonical in d['aliases'].items():
            k=(d['bank'],row)
            if k in aliases and aliases[k]!=canonical:raise ValueError('conflicting alias')
            aliases[k]=canonical
    return mapping,aliases

def prepare_rows(table,mapping,aliases):
    if table.get('status')!='SEALED_E60_ROW_TABLE' or set(table['banks'])!=set(BANKS):raise ValueError('complete seven-bank E60 row universe required')
    seen=set();points=[];excluded=[]
    for r in table['rows']:
        key=(r['bank'],r['row'],r['reader'])
        if key in seen or r['bank'] not in BANKS or r['reader'] not in READERS:raise ValueError('duplicate or unknown bank/row/reader')
        seen.add(key)
        if type(r['gated']) is not bool:raise ValueError('sealed registered gate required')
        if not r['gated']:excluded.append({'bank':r['bank'],'row':r['row'],'reader':r['reader'],'reason':r['gate_reason']});continue
        x=r['J_fraction'];counts=r['native_counts'];n=counts['N'];a=counts['correct_only'];b=counts['wrong_only']
        if type(x) not in (int,float) or not math.isfinite(x) or x<0:raise ValueError('every gated row needs a finite nonnegative J-fraction')
        if any(type(v)!=int or v<0 for v in (n,a,b)) or n==0 or a+b>n:raise ValueError('signed native S requires valid counts of all readouts')
        s=(a-b)/n
        if 'S' in r and not math.isclose(r['S'],s,rel_tol=0,abs_tol=1e-12):raise ValueError('native S disagrees with registered counts')
        k=(r['bank'],r['row']);canonical=aliases.get(k,r['row']);category=mapping.get(k,mapping.get((r['bank'],canonical)))
        if category not in COLOURS:raise ValueError('missing W-text category; do not omit row or invent colour')
        points.append({'bank':r['bank'],'row':r['row'],'reader':r['reader'],'J_fraction':float(x),'S':s,'category':category,'N':n,'correct_only':a,'wrong_only':b})
    return points,excluded

def render(points,curves,out):
    os.environ.setdefault('MPLCONFIGDIR',str(out/'mpl-cache'))
    os.environ.setdefault('XDG_CACHE_HOME',str(out/'xdg-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    if set(curves)!=set(READERS):raise ValueError('both E60 reader curve statuses required')
    fig,axes=plt.subplots(1,2,figsize=(12.5,6.7),sharex=True,sharey=True)
    xmax=max([p['J_fraction'] for p in points]+[.01]);drawn=0
    for ax,reader in zip(axes,READERS):
        part=[p for p in points if p['reader']==reader]
        for bank in BANKS:
            for category,colour in COLOURS.items():
                rows=[p for p in part if p['bank']==bank and p['category']==category]
                if rows:
                    ax.scatter([p['J_fraction'] for p in rows],[p['S'] for p in rows],c=colour,marker=MARKERS[bank],s=42,alpha=.8,linewidths=.35,edgecolors='#222222',zorder=3);drawn+=len(rows)
        curve=curves[reader]
        if curve['status']=='ESTIMATED':
            x=np.asarray(curve['J_fraction'],dtype=float);prob=np.asarray(curve['P_report'],dtype=float)
            if x.ndim!=1 or len(x)<2 or x.shape!=prob.shape or not np.isfinite(x).all() or not np.isfinite(prob).all() or np.any(x<0) or np.any(np.diff(x)<=0) or np.any((prob<0)|(prob>1)):raise ValueError('invalid sealed E60 prediction grid')
            ax.plot(x,prob,color='#252525',linewidth=1.8,label='E60 P(report)',zorder=2);xmax=max(xmax,float(x.max()))
        elif curve['status']=='NOT EVALUABLE':ax.text(.02,.96,'E60 curve not estimable: '+curve['reason'],transform=ax.transAxes,ha='left',va='top',fontsize=8,wrap=True)
        else:raise ValueError('unknown sealed E60 fit status')
        if not part:ax.text(.5,.5,'No rows passed the registered gates',transform=ax.transAxes,ha='center',fontsize=10)
        ax.set_title(('Oracle lens' if reader=='oracle' else 'NLA')+f' — {len(part)} gated rows',fontsize=13)
        ax.axhline(0,color='#999999',linewidth=.7,zorder=0);ax.grid(alpha=.15);ax.set_xlabel('J-fraction (sparse pursuit, k = 16)');ax.set_ylim(-1.04,1.04)
    for ax in axes:ax.set_xlim(-.015*xmax,1.035*xmax)
    axes[0].set_ylabel('Native statement rate S = (correct-only − wrong-only) / N')
    colour_handles=[Line2D([],[],marker='o',linestyle='',color=c,label=k,markersize=7) for k,c in COLOURS.items()]
    bank_handles=[Line2D([],[],marker=MARKERS[b],linestyle='',color='#555555',label=b,markersize=7) for b in BANKS]
    fig.legend(handles=colour_handles,loc='lower center',bbox_to_anchor=(.5,.155),ncol=5,frameon=False,title='W-text category')
    fig.legend(handles=bank_handles+[Line2D([],[],color='#252525',label='E60 P(report)',linewidth=1.8)],loc='lower center',bbox_to_anchor=(.5,.075),ncol=8,frameon=False,title='Bank / sealed curve')
    fig.text(.5,.035,'Points show signed native S; E60 curves predict binary native reporting. All gated rows shown; no refit or display-dependent selection.',ha='center',fontsize=8)
    fig.suptitle('D1 · J-fraction and native reporting',fontsize=15,y=.98)
    fig.subplots_adjust(left=.09,right=.985,top=.9,bottom=.32,wspace=.12)
    fig.savefig(out/'D1.png',dpi=180);fig.savefig(out/'D1.svg');plt.close(fig)
    if drawn!=len(points):raise ValueError('not every gated point rendered')
    return {'points_rendered':drawn,'figure_files':['D1.png','D1.svg'],'selection':'all gated rows; outcome-independent','E60_refitted':False}

def run():
    request=read(HERE/'REQUEST_2026-10-27.json');receipt=ROOT/request['verified_inputs']
    if not receipt.exists():print('D1 WAITING_FOR_SEALED_E60_AND_COMPLETE_CATEGORIES');return 2
    verify(ROOT,read(HERE/'CODE_SEAL_2026-10-27.json')['files']);r=read(receipt)
    if r['issuer']!='integrator' or r['status']!='VERIFIED_D1_AFTER_E60':raise ValueError('post-E60 verified delivery required')
    completion=sealed(r['E60_completion'])
    if completion['status']!='COMPLETE_ONCE_ONLY_ANALYSIS' or completion['E52_R3_scored'] is not True:raise ValueError('E60 and E52 R3 must be complete first')
    for key in ('row_table','curve_table'):
        if r[key]['seal_sha256']!=r['E60_completion']['seal_sha256'] or Path(r[key]['seal_path']).resolve()!=Path(r['E60_completion']['seal_path']).resolve():raise ValueError('row table and curves must belong to the final E60 seal')
    mapping,aliases=categories(r['category_manifest'])
    table=sealed(r['row_table']);curves=sealed(r['curve_table'])
    if curves['fit_scope']!='all_gated_rows' or curves['model']!='logistic' or curves['target']!='native_reported_169_clarification2':raise ValueError('the sealed all-row E60 logistic curve is required; no refitting')
    points,excluded=prepare_rows(table,mapping,aliases)
    cache=ROOT/'cache/g_agreement/understand/e61/d1';cache.mkdir(parents=True,exist_ok=True)
    with (cache/'ONCE.json').open('x') as f:json.dump({'status':'CLAIMED_NEVER_RESET','created_epoch':time.time(),'verified_inputs_sha256':sha(receipt)},f)
    artifacts=cache/'artifacts';artifacts.mkdir(exist_ok=False);rendered=render(points,curves['readers'],artifacts)
    dump(artifacts/'POINTS.json',{'points':points,'excluded_by_registered_gates':excluded})
    out=HERE/'results';out.mkdir(exist_ok=False)
    dump(out/'D1_SEAL.json',{'files':{p.name:sha(p) for p in artifacts.iterdir() if p.is_file()},'artifact_directory':str(artifacts),'verified_inputs_sha256':sha(receipt),'code_seal_sha256':sha(HERE/'CODE_SEAL_2026-10-27.json'),'render':rendered,'show_unconditionally':True,'E60_refitted':False})
    (out/'DISPLAY.md').write_text('# D1: all gated rows\n\n![D1]('+str(artifacts/'D1.png')+')\n\nEvery gated row is included. Points use signed S; the overlaid E60 curves predict binary native reporting. Category colours and bank markers are fixed. No display-dependent exclusions or refit.\n')
    print('D1 COMPLETE; show regardless of appearance');return 0

if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('No plot/filter overrides; use the committed job')
    raise SystemExit(run())
