import hashlib,json,gzip,tarfile,time
from pathlib import Path
p=Path('results/g_agreement/e74/evidence/runtime_deployment/e74-author-runtime.docker.tar.gz')
t=time.monotonic();h=hashlib.sha256()
with p.open('rb') as f:
 for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
small={};names=[];sizes={}
with gzip.open(p,'rb') as g:
 with tarfile.open(fileobj=g,mode='r|') as tar:
  for m in tar:
   names.append(m.name);sizes[m.name]=m.size
   if m.isfile() and m.size<2*1024*1024:
    raw=tar.extractfile(m).read()
    if m.name.startswith('blobs/sha256/'):
     assert hashlib.sha256(raw).hexdigest()==m.name.rsplit('/',1)[1],m.name
    try:small[m.name]=json.loads(raw)
    except (UnicodeError,ValueError):pass
 while g.read(8*1024*1024):pass
image_id='447fe0821f2ca4fb22daa5a06ade52edad3c710d22d2ef1e6852b69afeeb65e0'
config=small['blobs/sha256/'+image_id];assert config['architecture']=='amd64' and config['os']=='linux'
manifest=small['manifest.json'];assert len(manifest)==1 and manifest[0]['Config']=='blobs/sha256/'+image_id
index=small.get('index.json');image_manifests={k:v for k,v in small.items() if isinstance(v,dict) and v.get('schemaVersion')==2 and 'config' in v}
assert image_manifests
for m in image_manifests.values():
 assert m['config']['digest']=='sha256:'+image_id
 for layer in m['layers']:
  path='blobs/sha256/'+layer['digest'].split(':',1)[1]
  assert sizes[path]==layer['size']
out=dict(status='PASS_LOCAL_DOCKER_ARCHIVE',archive_path=str(p),archive_bytes=p.stat().st_size,archive_sha256=h.hexdigest(),gzip_crc_verified=True,config_digest_verified=True,small_blob_digests_verified=True,large_layer_digests_recomputed=False,layer_member_sizes_verified=True,docker_manifest=manifest,oci_index=index,oci_image_manifests=image_manifests,member_count=len(names),wall_seconds=time.monotonic()-t,registry_push=False,registry_pull_digest_verified=False,initial_layout_check='First verifier assumed legacy config filename; archive uses blobs/sha256 paths. Corrected verifier reads actual layout without changing archive/image.')
Path('results/g_agreement/e74/operator/deployment/IMAGE_ARCHIVE.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ('status','archive_bytes','archive_sha256','wall_seconds','member_count')},indent=2))
