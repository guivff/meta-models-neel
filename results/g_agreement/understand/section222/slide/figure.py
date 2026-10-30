"""Compact §222 slide: source-verified rendering only; no pooling or statistics."""
import importlib.util,json,hashlib,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/wlens-section222-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('appendix',HERE.parent/'talk/figure.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
def main():
 d=a.load();plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none'})
 f=plt.figure(figsize=(16,9),facecolor='#f2f5f7');ink=a.INK;blue=a.BLUE;amber=a.AMBER
 f.text(.06,.95,'Readers report the state at their read site',fontsize=27,weight='bold',color=ink,va='top')
 f.text(.06,.895,'Oracle · representative row: fact_recall · descriptive synthesis',fontsize=13,color=a.GRAY)
 f.text(.37,.84,'MODEL BEHAVIOUR',fontsize=12,weight='bold',color=ink,ha='center')
 f.text(.22,.79,'Changes (flips)',fontsize=18,weight='bold',color=blue,ha='center')
 f.text(.54,.79,'Behaviour barely moves\n(no flips)',fontsize=16,weight='bold',color=blue,ha='center',va='center',linespacing=1.3)
 f.text(.017,.47,'STATE AT THE READ SITE',rotation=90,ha='center',va='center',fontsize=12,weight='bold',color=ink)
 f.text(.048,.585,'YES',rotation=90,ha='center',va='center',fontsize=15,weight='bold',color=blue)
 f.text(.048,.255,'NO / unresolved',rotation=90,ha='center',va='center',fontsize=11,weight='bold',color=amber)
 boxes=[(.075,.43,.29,.31),(.395,.43,.29,.31),(.075,.10,.29,.29)]
 panels=[a.card(f,boxes[0]),a.card(f,boxes[1]),a.card(f,boxes[2],amber)]
 for ax,title in zip(panels,['E101 · present, used','E100 / E105 · present','E104 U · upstream write']):a.t(ax,.045,.95,title,14,bold=True)
 entries=[(panels[0],d['e101']['rows']['fact_recall']['oracle']['difference'],'ΔS reader',blue),(panels[1],d['e100']['rows']['fact_recall']['oracle']['transplant'],'Donor S reader',blue),(panels[2],d['e104']['arms']['U']['fact_recall']['difference'],'ΔS reader',amber)]
 for ax,z,label,col in entries:
  a.t(ax,.06,.72,label,13,a.GRAY);a.t(ax,.06,.60,f"{z['estimate']:+.2f}",54,col,True)
  a.t(ax,.06,.28,f"95% CI [{z['CI95'][0]:+.2f}, {z['CI95'][1]:+.2f}]",12,a.GRAY)
 a.t(panels[0],.06,.13,'Behaviour flips: 79/84',13,blue)
 a.t(panels[1],.06,.13,'Flips: 0/84 · Δbehaviour +0.31',11.5,blue)
 a.t(panels[2],.06,.13,'Behaviour flips: 84/84',13,amber)
 side=a.card(f,[.72,.43,.26,.31],amber)
 a.t(side,.05,.95,'Bookkeeping · E100',14,bold=True)
 a.t(side,.05,.72,'Present; outside decodable subspace',11,amber)
 for y,row,label in [(.59,'nesting_depth','Nesting depth'),(.42,'indent_level','Indent level'),(.25,'page_range_digit','Page-range digit')]:
  a.t(side,.05,y,label,12,bold=True);a.t(side,.68,y,f"{d['e100']['rows'][row]['oracle']['transplant']['estimate']:+.2f}",18,amber,True)
 a.t(side,.05,.085,'Donor S · probe AUROC 1.00 each',10,a.GRAY)
 # Empty bottom-right cell is omitted. Reserve its canvas area for future E109.
 ax=f.add_axes([.395,.10,.59,.29]);ax.axis('off')
 ax.add_patch(FancyBboxPatch((.02,.04),.96,.92,boxstyle='round,pad=0,rounding_size=.025',fill=False,edgecolor='#cbd5dc',linestyle=(0,(4,5)),transform=ax.transAxes))
 a.t(ax,.07,.83,'E109 · reserved',16,a.GRAY,True)
 a.t(ax,.07,.57,'Read-site arrival vs decoder limit',13,a.GRAY)
 f.savefig(HERE/'SITE_LOCAL_SLIDE.png',dpi=225,facecolor=f.get_facecolor());f.savefig(HERE/'SITE_LOCAL_SLIDE.svg',facecolor=f.get_facecolor(),metadata={'Date':None});plt.close(f)
 files=['figure.py','NOTES.md','SITE_LOCAL_SLIDE.png','SITE_LOCAL_SLIDE.svg']
 (HERE/'FIGURE_SEAL.json').write_text(json.dumps(dict(status='FIGURE_ONLY',statistics_recomputed=False,representative_row='fact_recall; no pooling',source_bindings_path=str(a.HERE/'SOURCE_BINDINGS.json'),source_bindings_sha256=a.sha(a.HERE/'SOURCE_BINDINGS.json'),files={n:a.sha(HERE/n) for n in files}),indent=2)+'\n')
if __name__=='__main__':main()
