import copy
import json
import unittest
from .e133_judge import naming_call, terminal_code


class NamingTest(unittest.TestCase):
    def setUp(self):
        self.unit = dict(id='a'*32, property='holder of the tracked object',
            values={'A':['Ada'],'B':['Bea'],'C':['Cy']}, readout='Ada or Bea holds it; elsewhere Zoe.')

    def code(self, category='states_value', values=None, evidence='Ada or Bea'):
        return dict(records=[dict(id=self.unit['id'],category=category,
            values=['A','B'] if values is None else values,evidence=evidence)])

    def test_blind_packet_and_multiple_values_retained(self):
        call, validate = naming_call(self.unit)
        self.assertEqual(json.loads(call['rendered']['user']), [self.unit])
        self.assertEqual(validate(self.code())['values'], ['A','B'])
        for metadata in ('current','previous','layer','pair_id','arm','reader'):
            u=dict(self.unit,**{metadata:'hidden'})
            with self.assertRaises(ValueError): naming_call(u)

    def test_other_named_value_and_original_evidence(self):
        _, validate = naming_call(self.unit)
        self.assertEqual(validate(self.code(values=['OTHER'],evidence='Zoe'))['values'], ['OTHER'])
        with self.assertRaises(ValueError): validate(self.code(values=['OTHER'],evidence='invented name'))

    def test_schema_ids_alphabet_and_duplicate_values(self):
        _, validate = naming_call(self.unit)
        for edit in [('id','b'*32),('values',['D']),('values',['A','A'])]:
            c=self.code();c['records'][0][edit[0]]=edit[1]
            with self.assertRaises(ValueError): validate(c)
        c=self.code();c['records'].append(copy.deepcopy(c['records'][0]))
        with self.assertRaises(ValueError): validate(c)

    def test_nonstating_and_silent_fields(self):
        _,validate=naming_call(self.unit)
        validate(self.code('names_property_without_value',[],'holds it'))
        validate(self.code('silent',[],''))
        for c in [self.code(values=[]),self.code('exhibits',['A']),self.code('silent',[],'Ada')]:
            with self.assertRaises(ValueError):validate(c)

    def test_empty_readout_and_missing_are_distinct(self):
        u=dict(self.unit,readout='');_,validate=naming_call(u)
        code=validate(self.code('silent',[],''))
        self.assertEqual(code['category'],'silent')
        self.assertIsNone(terminal_code(dict(status='UNPARSEABLE',result=None)))
        self.assertIsNone(terminal_code(dict(status='REFUSED',result=None)))
        self.assertEqual(terminal_code(dict(status='KEPT',result={'records':[code]})),code)


if __name__ == '__main__': unittest.main()
