"""44ff2b5f sign-based descriptive cross-tab; preserve prior seals/gallery."""
from pathlib import Path
import math
import shutil
from .run import I,OUT,CACHE,NOW


def run():
    previous=I.read(OUT/'FOLLOWUP_SEAL.json')
    for name,h in previous['files'].items():
        if I.sha(OUT/name)!=h:raise ValueError('previous follow-up changed')
    for path,h in I.read(OUT/'GALLERY_RECEIPT.json')['files'].items():
        if I.sha(Path(path))!=h:raise ValueError('original gallery/ranking changed')
    data=I.read(OUT/'FOLLOWUP.json');ranking=I.read(CACHE/'q_analysis/gallery/ALL60_RANKING.json')['candidates']
    asked={r['item']:r for r in ranking};items=[]
    for old in data['asked_free_per_item']:
        r=dict(old);s=asked[r['item']]['readers'][r['reader']]['signed']
        if not math.isfinite(s):raise ValueError('invalid signed asked score')
        positive=s>0;success=r['free_majority_correct']
        if success!=(r['free_correct_generations']>=3):raise ValueError('original majority changed')
        items.append({**r,'asked_signed_s':s,'asked_favours_truth':positive,'asked_zero':s==0,'sign_discordant':positive!=success})
    if len(items)!=120:raise ValueError('item-reader coverage')
    cross=[]
    for tier,reader in sorted({(r['tier'],r['reader']) for r in items}):
        rs=[r for r in items if (r['tier'],r['reader'])==(tier,reader)]
        counts={f'asked_{"positive" if a else "nonpositive"}__free_{"majority" if f else "no_majority"}':sum(r['asked_favours_truth']==a and r['free_majority_correct']==f for r in rs) for a in [False,True] for f in [False,True]}
        if len(rs)!=20 or sum(counts.values())!=20:raise ValueError('tier counts')
        cross.append({'tier':tier,'reader':reader,'n_items':20,'counts':counts,'asked_zero_count':sum(r['asked_zero'] for r in rs),
                      'asked_positive_no_free_majority_ids':[r['item'] for r in rs if r['asked_favours_truth'] and not r['free_majority_correct']],
                      'asked_nonpositive_free_majority_ids':[r['item'] for r in rs if not r['asked_favours_truth'] and r['free_majority_correct']]})
    archive=CACHE/'q_analysis/followup_before_sign';archive.mkdir(parents=True,exist_ok=True)
    for n in ['FOLLOWUP.md','FOLLOWUP.json','FOLLOWUP_SEAL.json']:
        if (archive/n).exists():
            if I.sha(archive/n)!=I.sha(OUT/n):raise ValueError('existing archive differs')
        else:shutil.copyfile(OUT/n,archive/n)
    data['sign_followup']={'at':NOW(),'registration':'44ff2b5f','status':'DESCRIPTIVE_AFTER_PREVIOUS_FOLLOWUP_WAS_SEEN',
        'rule':'Asked favours true value iff original truth-signed mean paired logodds s>0; s=0 grouped nonpositive and counted separately. Same original free majority>=3/4: Oracle enact/NLA mention; unclear or absent not correct. Percentile split retained separately and never treated as sign/asked correctness.',
        'source_ranking_sha256':I.sha(CACHE/'q_analysis/gallery/ALL60_RANKING.json'),'cross_tabs':cross,'per_item':items}
    data['rater2']['local_input_binding_accepted_by']='44ff2b5f'
    I.save(OUT/'FOLLOWUP.json',data)
    lines=['','## 4. Asked-score sign versus free-text majority (44ff2b5f)','','DESCRIPTIVE, registered after the previous follow-up was seen. Same signed mean paired log-odds s and unchanged≥3/4 free-majority rule. Asked favours the true value iff s>0. Nonpositive includes zero/ties; it is labelled does-not-favour-truth rather than necessarily wrong. A low within-row percentile alone is not an asked-score failure. Original percentile cross-tabs are retained separately.','','| Tier / reader | s≤0: no free majority | s≤0: free majority | s>0: no free majority | s>0: free majority | s=0 |','|---|---:|---:|---:|---:|---:|']
    for r in cross:
        c=r['counts'];lines.append(f"| {r['tier']} / {r['reader']} | {c['asked_nonpositive__free_no_majority']} | {c['asked_nonpositive__free_majority']} | {c['asked_positive__free_no_majority']} | {c['asked_positive__free_majority']} | {r['asked_zero_count']} |")
    for r in cross:
        lines+=['',f"### {r['tier']} / {r['reader']}: sign-discordant IDs",'', 's>0, no free majority: '+(', '.join('`'+v+'`' for v in r['asked_positive_no_free_majority_ids']) or 'none')+'.','', 's≤0, free majority: '+(', '.join('`'+v+'`' for v in r['asked_nonpositive_free_majority_ids']) or 'none')+'.']
    # Original gallery narrative did not label percentile-low items as failures.
    # Preserve its sealed bytes and add a clearly versioned signed-score view.
    original=CACHE/'q_analysis/gallery/GALLERY.md';text=original.read_text();narrative=[line for line in text.splitlines() if not line.startswith('    ')]
    failure_lines=[line for line in narrative if any(term in line.lower() for term in ['asked failure','asked-score failure','asked score failure'])]
    if failure_lines:raise ValueError('unexpected failure wording requires explicit review')
    selections=I.read(OUT/'GALLERY_SELECTION.json')['selected']
    header='\n**Signed-score annotation, 44ff2b5f:** Low percentile does not mean an asked-score failure. Only s≤0 fails to favour the true value; s=0 is a tie. Selection, source text and all72readouts remain exactly as in the original sealed gallery.\n'
    text=text.replace('\n\n','\n'+header+'\n',1)
    for r in selections:
        needle=next(line for line in text.splitlines() if line.startswith("Item `"+r['item']+"`;"))
        if text.count(needle)!=1:raise ValueError('ambiguous gallery annotation anchor')
        notes=[]
        for reader in ['oracle','nla']:
            s=r['readers'][reader]['signed'];notes.append(f"{reader} s={s:.8g} ({'favours truth' if s>0 else 'nonpositive; does not favour truth'})")
        text=text.replace(needle,needle+' Signed asked scores: '+'; '.join(notes)+'.',1)
    annotated=CACHE/'q_analysis/gallery/GALLERY_SIGN_ANNOTATED.md';annotated.write_text(text)
    lines+=['','Rater2 local input binding is accepted by44ff2b5f; κ stands unchanged. Q2d status is unchanged. Original gallery narrative contained no asked-failure claim. Original sealed gallery is preserved; `GALLERY_SIGN_ANNOTATED.md` adds the signed margins without changing the selection or verbatim readouts.']
    with (OUT/'FOLLOWUP.md').open('a') as f:f.write('\n'.join(lines)+'\n')
    I.save(OUT/'SIGN_FOLLOWUP_RECEIPT.json',{'registration':'44ff2b5f','item_reader_cells':120,'cross_tab_cells':6,
        'annotated_gallery':str(annotated),'annotated_gallery_sha256':I.sha(annotated),'original_gallery_sha256':I.sha(original),'original_failure_claims':failure_lines,
        'original_selection_sha256':I.sha(OUT/'GALLERY_SELECTION.json'),'prior_followup_archive':str(archive),
        'prior_followup_archive_seal_sha256':I.sha(archive/'FOLLOWUP_SEAL.json'),'api_calls':0,'gpu_hours':0})
    status=I.read(OUT/'FOLLOWUP_STATUS.json');status.update(sign_cross_tab='COMPLETE',rater2_input_binding_accepted='44ff2b5f');I.save(OUT/'FOLLOWUP_STATUS.json',status)
    for n in ['FOLLOWUP.json','FOLLOWUP.md','FOLLOWUP_STATUS.json','SIGN_FOLLOWUP_RECEIPT.json']:previous['files'][n]=I.sha(OUT/n)
    I.save(OUT/'FOLLOWUP_SEAL.json',previous)
    print('Sign cross-tabs and discordant IDs added; gallery annotated, original preserved')

if __name__=='__main__':run()
