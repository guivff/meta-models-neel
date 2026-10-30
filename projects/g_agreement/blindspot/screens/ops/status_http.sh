#!/usr/bin/env bash
set -euo pipefail
set -a
source "${RUNPOD_SECRETS:-$HOME/.config/mats/secrets.env}"
set +a
python3 - "$1" <<'PY'
import json,os,re,sys,urllib.request,time
pod=sys.argv[1]
assert re.fullmatch('[a-z0-9]+',pod)
query='query { pod(input:{podId:"'+pod+'"}) { id desiredStatus } }'
request=urllib.request.Request('https://api.runpod.io/graphql',data=json.dumps({'query':query}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['RUNPOD_API_KEY'],'User-Agent':'curl/8.7.1','Accept':'application/json'})
with urllib.request.urlopen(request,timeout=45) as response:code=response.status;body=json.load(response)
entry=body.get('data',{}).get('pod',{})
assert code==200 and entry.get('id')==pod and entry.get('desiredStatus') in ('RUNNING','EXITED')
print(json.dumps({'http_status':code,'pod_id':entry['id'],'status':entry['desiredStatus'],'at':time.time()}))
PY
