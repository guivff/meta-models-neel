"""Pure CPU sealed-source join for E132 C1; never runs prior analyses or models."""
import hashlib
import json
import re
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Store:
    def __init__(self):
        self.seals = {}
        self.members = {}
        self.values = {}

    def seal(self, path, expected):
        path = Path(path).resolve()
        if path not in self.seals:
            if sha(path) != expected:
                raise ValueError('source seal hash mismatch')
            self.seals[path] = (expected, json.loads(path.read_text()))
        elif self.seals[path][0] != expected:
            raise ValueError('inconsistent seal reference')
        return path, self.seals[path][1]

    def member(self, seal_path, seal_sha, member):
        sp, seal = self.seal(seal_path, seal_sha)
        p = (sp.parent / member).resolve()
        if sp.parent not in p.parents or member not in seal['files']:
            raise ValueError('unsealed member or path traversal')
        if p not in self.values:
            expected = seal['files'][member]
            if sha(p) != expected:
                raise ValueError('source member hash mismatch')
            self.members[str(p)] = expected
            self.values[p] = json.loads(p.read_text())
        return self.values[p]

    def ref(self, seal_path, seal_sha, member, keys):
        value = self.member(seal_path, seal_sha, member)
        for k in keys:
            value = value[k]
        return value


def template(prompt_id):
    m = re.fullmatch(r'c[0-9]{2}t([0-5])s[0-6]', prompt_id)
    if not m:
        raise ValueError('original E108 template identity unavailable')
    return 't' + m[1]


def bind(spec):
    st = Store()
    c = spec['cohort']
    cohort = st.member(c['seal'], c['sha256'], 'COHORT.PRIVATE.json')
    cohort = [x for x in cohort if x['arm'] == 'immediate']
    if len(cohort) != 329 or len({r['id'] for r in cohort}) != 329:
        raise ValueError('exact original329 immediate choices required')
    by = {r['id']: r for r in cohort}
    n = spec['nonmodal']
    note = st.member(n['seal'], n['sha256'], 'COHORT.PRIVATE.json')
    nonmodal = set(note['item_ids'])
    if len(nonmodal) != 110 or not nonmodal <= set(by):
        raise ValueError('exact existing110 nonmodal matched IDs required')
    i = spec['inventory']
    inventory = st.member(i['seal'], i['sha256'], 'INVENTORY.json')
    metadata = {r['id']: r for r in inventory if r['kind'] == 'native' and r['arm'] == 'immediate'}
    ip = Path(spec['public_inputs']['path'])
    if sha(ip) != spec['public_inputs']['sha256']:
        raise ValueError('original E108 prompt hash mismatch')
    public = {r['id']: r for r in json.loads(ip.read_text())}
    st.members[str(ip.resolve())] = spec['public_inputs']['sha256']
    rows = []
    for ident, item in sorted(by.items()):
        meta = metadata[ident]
        if not isinstance(item['choice'], str) or not item['choice'].strip():
            raise ValueError('missing original canonical choice')
        rows.append(dict(id=ident, item_group=ident, template_group=template(meta['prompt_id']),
                         category=meta['category'], pick=item['choice'], nonmodal=ident in nonmodal,
                         prompt=public[ident]['prompt'], readouts={}))
    rows_by = {r['id']: r for r in rows}
    late = spec['late_text_pointers']
    pointers = st.member(late['seal'], late['sha256'], 'SOURCE_POINTERS.PRIVATE.json')
    for p in pointers:
        ident = p['item_id']
        if ident not in by:
            continue
        b = p['block']
        if b not in (52, 60):
            raise ValueError('unexpected late block')
        ref = p['native_text_ref']
        if ref['sha256'] != spec['late_native']['sha256']:
            raise ValueError('late native output differs from original')
        text = st.ref(ref['seal'], ref['sha256'], ref['member'], ref['keys'])
        record = st.ref(ref['seal'], ref['sha256'], ref['member'], ref['keys'][:-1])
        if record['item_id'] != ident or record['id'] != p['native_id'] or record['source_layer'] != b or record['reader'] != 'oracle' or record['condition'] is not None:
            raise ValueError('late native identity/block mismatch')
        if str(b) in rows_by[ident]['readouts'] or not isinstance(text, str):
            raise ValueError('duplicate/missing original readout')
        rows_by[ident]['readouts'][str(b)] = text
    for r in rows:
        if set(r['readouts']) != {'52', '60'}:
            raise ValueError('both late native readouts required for329')
    # Original E108 block44 is inside the sealed source graph bound by E116.
    e = spec['e108_native']
    _, seal = st.seal(e['seal'], e['sha256'])
    count44 = 0
    for name in sorted(seal['files']):
        if not re.fullmatch(r'jobs/oracle_[0-9]{4}\.json', name):
            continue
        batch = st.member(e['seal'], e['sha256'], name)
        for record in batch:
            ident = record['id']
            if ident not in rows_by:
                continue
            if record['kind'] != 'native' or record['layer'] != 44 or record['reader'] != 'oracle' or record['repeat'] != 0 or not isinstance(record['text'], str):
                raise ValueError('E108 block44 identity mismatch')
            if '44' in rows_by[ident]['readouts']:
                raise ValueError('duplicate44')
            rows_by[ident]['readouts']['44'] = record['text']
            count44 += 1
    if count44 not in (0, 329):
        raise ValueError('partial source-linked44 bank: no silent row drop')
    return rows, {'source_seals': {str(p): h for p,(h,_) in st.seals.items()},
                  'consumed_members': st.members, 'n':329, 'nonmodal':110,
                  'block44': 'AVAILABLE_SAME_ORIGINAL_SOURCE_GRAPH' if count44 else 'NOT_AVAILABLE'}
