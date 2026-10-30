"""Talk §222: render sealed aggregate fields, with no statistical computation."""
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/wlens-section222-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
INK='#173140';BLUE='#0b7285';AMBER='#ab6020';GRAY='#536774'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def load():
    pins=json.loads((HERE/'SOURCE_BINDINGS.json').read_text());data={}
    for name,p in pins['sources'].items():
        a,b=ROOT/p['result_path'],ROOT/p['seal_path']
        assert sha(a)==p['result_sha256'] and sha(b)==p['seal_sha256'],name
        seal=json.loads(b.read_text());assert seal['status'] in ['COMPLETE','COMPLETE_ONCE']
        assert seal['files'][a.name]==sha(a)
        data[name]=json.loads(a.read_text())
    return data


def fmt(x):return f"{x['estimate']:+.2f} [{x['CI95'][0]:+.2f}, {x['CI95'][1]:+.2f}]"

def card(fig,box,color=BLUE):
    ax=fig.add_axes(box);ax.axis('off')
    ax.add_patch(FancyBboxPatch((0,0),1,1,boxstyle='round,pad=0,rounding_size=0.025',facecolor='white',edgecolor='#ced9de',transform=ax.transAxes))
    ax.plot([.045,.955],[.795,.795],color=color,lw=2,transform=ax.transAxes)
    return ax

def t(ax,x,y,s,size=12,color=INK,bold=False):
    ax.text(x,y,s,va='top',fontsize=size,color=color,weight='bold' if bold else 'normal',transform=ax.transAxes)

def main():
    d=load();plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none'})
    fig=plt.figure(figsize=(20,11.25),facecolor='#f2f5f7')
    fig.text(.065,.965,'State at the read site × use by the model',fontsize=28,weight='bold',color=INK,va='top')
    fig.text(.065,.919,'Oracle reader  •  §222 descriptive synthesis  •  sealed estimates with existing 95% bootstrap CIs',fontsize=14,color=GRAY,va='top')
    fig.text(.385,.873,'MODEL USES IT (BEHAVIOUR CHANGES)',fontsize=12,weight='bold',color=INK,ha='center')
    fig.text(.23,.84,'YES',fontsize=20,weight='bold',color=BLUE,ha='center')
    fig.text(.55,.84,'Behaviour barely moves (no flips)',fontsize=15,weight='bold',color=BLUE,ha='center')
    fig.text(.018,.52,'STATE PRESENT AT THE READER’S READ SITE',rotation=90,ha='center',va='center',fontsize=12,weight='bold',color=INK)
    fig.text(.047,.635,'YES',rotation=90,fontsize=16,weight='bold',color=BLUE,va='center')
    fig.text(.047,.30,'NO²',rotation=90,fontsize=16,weight='bold',color=AMBER,va='center')
    a=card(fig,[.072,.485,.305,.325]);b=card(fig,[.392,.485,.305,.325])
    c=card(fig,[.072,.145,.305,.315],AMBER);empty=card(fig,[.392,.145,.305,.315],GRAY)
    fifth=card(fig,[.722,.39,.26,.42],AMBER);inset=card(fig,[.722,.145,.26,.215],GRAY)
    for ax,title,sub in [(a,'E101 · present, used','DESCRIPTIVE · confirmatory rules NOT EVALUABLE'),(c,'E104 arm U · not at site², used','DESCRIPTIVE · R-U1 NOT MET')]:
        t(ax,.045,.95,title,16,bold=True);t(ax,.045,.855,sub,9.7,GRAY)
        t(ax,.045,.755,'Row / paired ΔS [95% CI]',11,GRAY,True)
    for y,row,label in [(.65,'fact_recall','Fact recall'),(.39,'language_plan','Language plan')]:
        z=d['e101']['rows'][row]['oracle']
        t(a,.045,y,label,12,bold=True);t(a,.37,y,fmt(z['difference'])+'*',12)
        t(a,.045,y-.11,f"Behaviour flips  {z['flipped_n']}/84",11,BLUE)
        w=d['e104']['arms']['U'][row]
        t(c,.045,y,label,12,bold=True);t(c,.37,y,fmt(w['difference'])+('*' if w['missing']['steered']['cohort_over5percent'] else ''),12)
        t(c,.045,y-.11,f"Behaviour flips  {w['flipped_n']}/84",11,AMBER)
    t(a,.045,.13,'ΔS = steered − random; flipped-item cohort.',10,GRAY)
    t(c,.045,.13,'ΔS = steered − random; flipped-item cohort.',10,GRAY)
    t(c,.045,.065,'² Written upstream; read-site arrival remains unresolved.',9.3,AMBER)
    t(b,.045,.95,'E100 transplant + E105 behaviour',15,bold=True)
    t(b,.045,.855,'R-PC MET: 5/5 · E105 R-BT1 NOT MET',10,GRAY)
    t(b,.045,.755,'Same content rows',10,GRAY,True)
    t(b,.355,.755,'E100 donor S [CI]',10,GRAY,True)
    t(b,.045,.69,'Fact recall',11,bold=True);t(b,.045,.50,'Format plan',11,bold=True);t(b,.045,.31,'Language plan',11,bold=True)
    for y,row in [(.69,'fact_recall'),(.50,'format_plan'),(.31,'language_plan')]:
        r=d['e100']['rows'][row]['oracle']['transplant'];q=d['e105']['rows'][row]
        assert q['flip_T']['estimate']==0
        t(b,.355,y,fmt(r)+('*' if r['over_5_percent'] else ''),11)
        t(b,.045,y-.075,'E105 Δbehaviour '+fmt(q['delta'])+'; flips 0/84',10,BLUE)
    t(b,.045,.12,'E100 paired ΔS: not sealed; donor S shown, not relabelled.',9.2,AMBER)
    t(b,.045,.055,'Other R-PC rows (S): language continuation .61; tense .65.',9.2,GRAY)
    t(empty,.045,.95,'No sealed example',16,bold=True)
    t(empty,.045,.855,'Not present × not used',11,GRAY)
    t(empty,.06,.64,'ΔS and behaviour-flip rate',16,GRAY)
    t(empty,.06,.48,'UNAVAILABLE',22,GRAY,True)
    t(empty,.06,.24,'No zero or counterfactual value imputed.',11,GRAY)
    t(fifth,.045,.96,'Present, outside the',17,AMBER,True)
    t(fifth,.045,.895,'decodable subspace',17,AMBER,True)
    t(fifth,.045,.735,'E100 · full transplant · descriptive',12,bold=True)
    t(fifth,.045,.665,'Row',11,GRAY,True);t(fifth,.48,.665,'Donor S',11,GRAY,True);t(fifth,.77,.665,'Probe AUC',10,GRAY,True)
    for y,row,label in [(.59,'nesting_depth','Nesting depth'),(.43,'indent_level','Indent level'),(.27,'page_range_digit','Page-range digit')]:
        z=d['e100']['rows'][row]['oracle']['transplant']
        t(fifth,.045,y,label,11,bold=True);t(fifth,.48,y,f"{z['estimate']:+.2f}",13,AMBER,True);t(fifth,.80,y,f"{d['probe'][row]:.2f}",12)
        t(fifth,.045,y-.065,'95% CI '+f"[{z['CI95'][0]:+.2f}, {z['CI95'][1]:+.2f}]",10,GRAY)
    t(fifth,.045,.105,'Probe AUCs: original sealed E57 test probes.',9.5,GRAY)
    t(fifth,.045,.05,'“Outside subspace” is the §222 account, not a new test.',9.1,GRAY)
    t(inset,.045,.95,'E109 · reserved inset',16,GRAY,True)
    t(inset,.06,.65,'Arrival at the read site vs decoder limit',12,GRAY)
    t(inset,.06,.43,'No E109 data shown',15,GRAY)
    fig.text(.072,.101,'¹ No strict flips ≠ no continuous change: E105 paired Δbehaviour = donor-oriented T − shuffled-S log-probability contrast.',fontsize=11,color=GRAY)
    fig.text(.072,.077,'S = signed judged report (correct − wrong). E101/E104 use the steered target; E100 uses the donor target. Cell headings follow the §222 account.',fontsize=10.7,color=GRAY)
    fig.text(.072,.053,'* >5% terminal missing judgments in that displayed statistic/cohort. Existing bootstrap intervals copied verbatim; no pooling or recomputation.',fontsize=10.7,color=GRAY)
    fig.text(.072,.029,'Exact source commits, field paths and hashes are recorded beside the figure. E101 / E104 causal contrasts are descriptive; no new confirmatory verdict.',fontsize=10.7,color=GRAY)
    fig.savefig(HERE/'SITE_LOCAL_TALK.png',dpi=180,facecolor=fig.get_facecolor())
    fig.savefig(HERE/'SITE_LOCAL_TALK.svg',facecolor=fig.get_facecolor(),metadata={'Date':None})
    plt.close(fig)
    (HERE/'FIGURE_SEAL.json').write_text(json.dumps({'status':'FIGURE_ONLY','statistics_recomputed':False,'files':{p.name:sha(p) for p in [HERE/'figure.py',HERE/'SOURCE_BINDINGS.json',HERE/'SITE_LOCAL_TALK.png',HERE/'SITE_LOCAL_TALK.svg']}},indent=2)+'\n')

if __name__=='__main__':main()
