"""Copy exact E112 family terminal codes into the original status/result envelope.

No scorer, pass computation, aggregation, scientific analysis or once guard.
The original adapter alone calls original E80 score80.passed on these records.
"""
import argparse
from .runner import CACHE
from .transport import ROOT, HERE
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def envelope(rows, expected, cpu=False):
    require(len(rows) == expected and len({x['id'] for x in rows}) == expected, 'whole unique exact source census')
    out=[]
    for x in rows:
        require(x['status'] in (('CPU_REGEX',) if cpu else ('KEPT','UNPARSEABLE','REFUSED')), 'original known terminal status')
        require((x['code'] is not None) == (x['status'] in ('KEPT','CPU_REGEX')), 'exact original code/null retained')
        out.append(dict(id=x['id'], status=x['status'], result=x['code']))
    return out


def bind():
    receipt=HERE/'E112_BINDING_SOURCE_SEAL.json'
    for name,digest in read(receipt)['files'].items():require(sha(ROOT/name)==digest,'published E112 envelope source')
    home=CACHE/'E112';phase=home/'pca1_family_judging/outputs/JUDGMENT_SEAL.json';unit=home/'pca1_family_units/UNIT_SEAL.json'
    p=verify(phase,sha(phase));verify(unit,sha(unit))
    require(p['experiment']=='E112' and p['status']=='COMPLETE' and p['route_verified'] is True,'full E112 approved-route phase')
    paid=read(phase.parent/'JUDGMENTS.json');cpu=read(unit.parent/'CPU_REGEX_CODES.PRIVATE.json')
    codes=envelope(paid,840)+envelope(cpu,196,True)
    require(len({x['id']for x in codes})==1036,'all1036 distinct full family readouts')
    joins=read(unit.parent/'SOURCE_POINTERS.PRIVATE.json');by={x['id']:x for x in joins}
    require(len(by)==len(joins)==1036 and set(by)=={x['id']for x in codes} and
            len({(x['original_item_id'],x['reader'])for x in joins})==1036,'original item/reader crosswalk bijection')
    refs=[]
    for member,source,rows in [('JUDGMENTS.json',phase,paid),('CPU_REGEX_CODES.PRIVATE.json',unit,cpu)]:
        for i,x in enumerate(rows):
            refs.append(dict(by[x['id']],original_code=dict(seal=str(source),sha256=sha(source),member=member,keys=[i,'code']),
                             status=x['status'],envelope_index=len(refs)))
    dest=home/'family_code_binding';dest.mkdir(exist_ok=True);dest.chmod(0o700)
    final=dest/'JUDGMENT_SEAL.json'
    if final.exists():
        verify(final,sha(final));require(read(dest/'FAMILY_JUDGMENTS.PRIVATE.json')==codes,'immutable original envelope');return final
    write(dest/'FAMILY_JUDGMENTS.PRIVATE.json',codes);write(dest/'SOURCE_POINTERS.PRIVATE.json',refs)
    write(dest/'JUDGMENT_SEAL.json',dict(experiment='E112',status='COMPLETE_CPU_BINDING',n=1036,
        source_seals=[dict(seal=str(phase),sha256=sha(phase)),dict(seal=str(unit),sha256=sha(unit))],
        source_manifest_sha256=sha(receipt),no_scoring_or_analysis=True,original_code_values_unchanged=True,
        files={n:sha(dest/n)for n in ('FAMILY_JUDGMENTS.PRIVATE.json','SOURCE_POINTERS.PRIVATE.json')}))
    return final


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();print('E112 exact envelope binding '+sha(bind()))
