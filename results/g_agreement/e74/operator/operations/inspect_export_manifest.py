import sys,tarfile,json,hashlib
from pathlib import Path
small={};sizes={}
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|') as tar:
 for m in tar:
  sizes[m.name]=m.size
  if m.isfile() and m.size<100000:
   raw=tar.extractfile(m).read()
   if m.name.startswith('blobs/sha256/'):assert hashlib.sha256(raw).hexdigest()==m.name.rsplit('/',1)[1]
   try:small[m.name]=json.loads(raw)
   except (UnicodeError,ValueError):pass
image='sha256:4b8dd4f8a4a2d0c928a8e00333406f83208e463583cd9c76087cc72fd53d8b53'
manifests={k:v for k,v in small.items() if isinstance(v,dict) and v.get('schemaVersion')==2 and 'config' in v}
assert len(manifests)==1
for m in manifests.values():
 assert m['config']['digest']==image
 for l in m['layers']:assert sizes['blobs/sha256/'+l['digest'].split(':',1)[1]]==l['size']
result={'status':'PASS_LOCAL_EXPORT_MANIFEST_METADATA','image_config_digest':image,'oci_manifest_blobs':manifests,'oci_manifest_digests':['sha256:'+k.rsplit('/',1)[1] for k in manifests],'docker_manifest':small['manifest.json'],'oci_index':small.get('index.json'),'small_json_blob_hashes_verified':True,'layer_member_sizes_verified':True,'layer_bytes_independently_hashed':False,'registry_manifest_digest_verified':False,'registry_push':False,'note':'OCI metadata extracted from local Docker save stream; no full second image archive retained. Registry compression/manifest will need its own verification after authorized publication.'}
Path('results/g_agreement/e74/operator/operations/LOCAL_IMAGE_MANIFEST.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':result['status'],'oci_manifest_digests':result['oci_manifest_digests']}))
