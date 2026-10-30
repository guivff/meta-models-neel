"""Anonymous, metadata-only refresh restricted to the author's exact release collection."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

COLLECTION='ceselder/glm53-olens-6adaf9d544d3645a7fb96eb9'
LENS='ceselder/glm-5.3-olens-lens'
EXPECTED={'stein_all_L51.pt','stein_all_L60.pt','head.pt'}
ROOT=Path('results/g_agreement/e74')


def fetch(url, method='GET'):
    assert url.startswith('https://huggingface.co/')
    if method=='GET':assert url.startswith('https://huggingface.co/api/')
    req=urllib.request.Request(url,method=method,headers={'User-Agent':'E74-anonymous-J-metadata-refresh','Cache-Control':'no-cache'})
    stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(req,timeout=30) as response:
            raw=response.read() if method=='GET' else b''
            record={'url':url,'method':method,'checked_at_utc':stamp,'status':response.status,'headers':{k:response.headers.get(k) for k in ('Date','ETag','Content-Length','Content-Type','Age','X-Repo-Commit')},'body_sha256':hashlib.sha256(raw).hexdigest() if raw else None}
            return record,json.loads(raw) if raw else None,response.headers.get('Link','')
    except urllib.error.HTTPError as exc:
        return {'url':url,'method':method,'checked_at_utc':stamp,'status':exc.code},None,''


def repository(item):
    kind=item['type'];name=item['id']
    assert kind in ('model','dataset') and re.fullmatch(r'ceselder/[A-Za-z0-9._-]+',name)
    request,data,_=fetch(f'https://huggingface.co/api/{kind}s/{name}')
    result={'repo_type':kind,'repo_id':name,'head_request':request}
    if data is None:return dict(result,status='HTTP_METADATA_UNAVAILABLE')
    revision=data['sha'];assert re.fullmatch('[0-9a-f]{40}',revision)
    prefix=f'https://huggingface.co/api/{kind}s/{name}/tree/{revision}'
    url=prefix+'?recursive=true&limit=1000';files=[];pages=[]
    while url:
        request,entries,links=fetch(url);pages.append(request)
        if entries is None:return dict(result,status='TREE_METADATA_UNAVAILABLE',revision=revision,pages=pages)
        files.extend(x['path'] for x in entries if x.get('type')=='file')
        nxt=re.search(r'<([^>]+)>;\s*rel="next"',links)
        url=nxt[1] if nxt else None
        if url:assert url.startswith(prefix+'?')
    matches=[p for p in files if Path(p).name in EXPECTED or (re.search(r'jlens|j-lens|j_lens|stein',p,re.I) and p.endswith(('.pt','.pth','.bin','.safetensors')))]
    heads=[]
    for path in matches:
        dataset='datasets/' if kind=='dataset' else ''
        heads.append(fetch(f'https://huggingface.co/{dataset}{name}/resolve/{revision}/{path}',method='HEAD')[0])
    return dict(result,status='METADATA_COMPLETE',revision=revision,private=data.get('private'),gated=data.get('gated'),files=sorted(files),pages=pages,j_checkpoint_candidates=matches,candidate_anonymous_heads=heads)


def main():
    start=time.monotonic();old=json.loads((ROOT/'ANONYMOUS_AUDIT.json').read_text())
    req,data,_=fetch('https://huggingface.co/api/collections/'+COLLECTION)
    assert data is not None,'Collection metadata unavailable'
    items=[{'id':x['id'],'type':x['type']} for x in data['items']]
    assert any(x['id']==LENS for x in items)
    selected=[x for x in items if x['type'] in ('model','dataset') and x['id'].startswith('ceselder/')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:repos=list(pool.map(repository,selected))
    baseline={x['repo_id']:x for x in old['repos']}
    for r in repos:
        b=baseline.get(r['repo_id'])
        r['prior_revision']=b['revision'] if b else None
        r['revision_unchanged_from_asset_audit']=r.get('revision')==b['revision'] if b else None
        r['new_file_paths_since_asset_audit']=sorted(set(r.get('files',[]))-set(b['files'])) if b else None
    candidates=[{'repo_id':r['repo_id'],'revision':r.get('revision'),'files':r.get('j_checkpoint_candidates',[])} for r in repos if r.get('j_checkpoint_candidates') or re.search('jlens|j-lens|j_lens',r['repo_id'],re.I)]
    complete=all(r['status']=='METADATA_COMPLETE' for r in repos)
    result={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authentication':'none; fresh stdlib requests without auth header, cookie jar, HF SDK or credential-store access','scope':'Exact author release collection and the ceselder model/dataset repositories linked by it; no author-wide or global search','collection':{'slug':COLLECTION,'request':req,'items':items,'items_unchanged_from_asset_audit':items==old['collection']['items']},'repositories':repos,'candidates':candidates,'verdict':'CANDIDATE_FOUND_STOP_AND_REPORT' if candidates else ('NOT_FOUND_IN_SEARCHED_RELEASE_METADATA' if complete else 'INCOMPLETE_METADATA_CHECK'),'expected_weight_filenames':sorted(EXPECTED),'weight_payload_bytes':0,'dataset_payload_bytes':0,'readme_or_rollout_text_read':False,'gpu_used':False,'science_changed':False,'global_absence_claimed':False,'wall_seconds':time.monotonic()-start}
    dest=ROOT/'j_refresh'/('REFRESH_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
    dest.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'out':str(dest),'verdict':result['verdict'],'candidates':candidates,'repos':[{'repo_id':r['repo_id'],'revision':r.get('revision'),'status':r['status'],'files':len(r.get('files',[]))} for r in repos]},indent=2))


if __name__=='__main__':main()
