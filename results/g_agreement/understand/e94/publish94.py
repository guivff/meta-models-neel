"""Publication projection only: preserve exact once outputs in cache; never rescore."""
import shutil
from pathlib import Path
from sources94 import HERE,CACHE,read,sha,write
from score94 import require

def project(result):
    return {k:v for k,v in result.items() if k!='banks'} | {'banks':{bank:{k:v for k,v in block.items() if k!='strata'} for bank,block in result['banks'].items()}}
def main():
    out=HERE/'analysis_once_20261028';original=read(out/'ANALYSIS_SEAL.json')
    for n,digest in original['files'].items():require(sha(out/n)==digest,'once output drift')
    cached=CACHE/'analysis_once_20261028';require(not cached.exists(),'publication already made');shutil.copytree(out,cached)
    for p in out.iterdir():require(sha(p)==sha(cached/p.name),'byte preserving copy')
    result=read(cached/'RESULTS.json');summary=project(result)
    write(out/'SUMMARY.json',summary)
    # Full strata include exact donor identity keys, so custody and size both require cache.
    (out/'RESULTS.json').unlink();(out/'ANALYSIS_SEAL.json').unlink()
    write(out/'SEALED_ANALYSIS_REF.json',{'experiment':'E94','status':'COMPLETE_ONCE','original_directory':str(cached),'original_analysis_seal_sha256':sha(cached/'ANALYSIS_SEAL.json'),'original_seal':original,'publication':'Bank and wave summaries copied verbatim; no refit, rescoring or analysis rerun. Detailed strata remain in ignored cache with private identity binding.'})
    write(out/'PUBLICATION_SEAL.json',{'experiment':'E94','status':'COMPLETE_ONCE_PUBLICATION','original_analysis_seal_sha256':sha(cached/'ANALYSIS_SEAL.json'),'files':{n:sha(out/n) for n in ('ONCE.json','REPORT.md','SUMMARY.json','SEALED_ANALYSIS_REF.json')},'publication_code_sha256':sha(__file__)})
    print('E94 publication sealed; original outputs byte-preserved in cache; no analysis rerun.')
if __name__=='__main__':main()
