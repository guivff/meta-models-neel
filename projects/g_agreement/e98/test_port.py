from projects.g_agreement.e98.port import convert

class Tokenizer:
    def __call__(self, text, **kw):
        return {'input_ids': [ord(c) for c in text],
                'offset_mapping': [(i, i+1) for i in range(len(text))]}
    def decode(self, ids, **kw):
        return ''.join(map(chr, ids))


def row(ident, feature, text, label):
    return dict(id=ident, feature=feature, text=text, label=label, split='test')


def test_whole_row_drop_and_private_custody():
    records = [row('A:0', 'bad', '', 0), row('A:1', 'bad', 'abc', 1),
               row('B:0', 'good', 'abc', 0)]
    kept, failures, dropped = convert('E57', records, Tokenizer())
    assert dropped == ['bad'] and len(failures) == 1 and len(kept) == 1
    public, private = kept[0]
    assert set(public) == {'id', 'ids', 'read_index'}
    assert public['id'] != 'B:0' and public['read_index'] == 2
    assert private['text'] == 'abc' and private['label'] == 0 and private['split'] == 'test'
    assert private['source_id'] == 'B:0'
    other, _, _ = convert('E59', [records[-1]], Tokenizer())
    assert other[0][0]['id'] != public['id']
