"""Metadata-only preflight. Does not open readouts or invoke the once-only analysis."""
import importlib.util
from prepare import HERE
from contract56 import read,sha,verify,require
s=read(HERE/'ANALYSIS_SPEC.json');c=read(HERE/'ANALYSIS_COMMAND.json')
require(sha(HERE/'ANALYSIS_SPEC.json')==c['spec_sha256'],'spec pin')
verify(HERE,'SOURCE_SEAL.json',c['analysis_source_seal_sha256'])
verify(s['executed_source_root'],'SOURCE_SEAL.json',s['source_seal_sha256'])
require(sha(s['executed_source_archive'])==s['executed_source_archive_sha256'],'executed archive pin')
from pathlib import Path
root=Path(s['output']);r=read(s['receipt']);require(r['verified'] is True and sha(root/'OUTPUT_SEAL.json')==r['output_seal_sha256'],'verified output metadata')
o=read(root/'OUTPUT_SEAL.json');require(o['source_seal_sha256']==s['source_seal_sha256']==c['source_seal_sha256'],'executed source pin')
a=read(root/'ASSIGNMENT.json');require(a['source_seal_sha256']==s['source_seal_sha256'],'assignment source pin')
m=importlib.util.spec_from_file_location('historical_supplement',Path(s['executed_source_root'])/'worker.py');v=importlib.util.module_from_spec(m);m.loader.exec_module(v);v.custody(a,a['stage_started_epoch'])
require(read(root/'TIMING.json')['completed_epoch']<a['absolute_deadline_epoch'],'historical clock')
print('ANALYSIS_BINDING_PASS; readouts unopened; analysis not invoked')
