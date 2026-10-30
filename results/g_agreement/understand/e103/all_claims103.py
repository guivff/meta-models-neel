"""Complete §210's 'for each claim' queue from the sealed selection, without resampling."""
from pathlib import Path
from select103 import HERE,read,write,sha,digest,require

def calls_for(selected):
    calls=[]
    for u in selected:
        for i,c in enumerate(u['claims']):
            for arm,source in [('own',u['own_source_id']),('mismatched',u['control_source_id'])]:
                calls.append(dict(id='j_'+digest(f"{u['uid']}|{i}|{arm}")[:24],readout_uid=u['uid'],wave=u['wave'],bank=u['bank'],reader=u['reader'],item_id=u['item_id'],cohort=u['cohort'],claim_index=i,claim=c['claim'],verdict=c['verdict'],arm=arm,source_id=source))
    require(len({c['id'] for c in calls})==len(calls),'Unique claim/arm identities')
    return calls

def main():
    seal=read(HERE/'SELECTION_SEAL.json');cache=Path(seal['private_cache'])
    path=cache/'SELECTION.PRIVATE.json';require(sha(path)==seal['files'][path.name],'Frozen selection changed')
    out=cache/'ALL_CLAIM_CALLS.PRIVATE.json';require(not out.exists(),'Already frozen; no overwrite')
    calls=calls_for(read(path));write(out,calls)
    write(HERE/'ALL_CLAIMS_SEAL.json',{'selection_seal_sha256':sha(HERE/'SELECTION_SEAL.json'),'private_path':str(out),'sha256':sha(out),'claims':len(calls)//2,'calls':len(calls),'first_output_utc':'unknown','reason':'CPU-only queue; no generation or judging','scope':'All original E67 claims in selected readouts, including mixed supported and unverifiable claims; no re-extraction. R-H2 uses contradicted claims; supported and unverifiable reported separately.'})
    print('All claims:',len(calls)//2,'calls:',len(calls))
if __name__=='__main__':main()
