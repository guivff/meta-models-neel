import json,unittest
from .subset300 import first300
class SubsetTests(unittest.TestCase):
    def rows(self):return [dict(id=str(i),pair_id=str(i//2),member=i%2,ids=[17,i,24],read_index=2,candidate_ids=[])for i in range(1200)]
    def test_lossless_original_bytes_and_order(self):
        rows=self.rows();raw=json.dumps(rows,indent=2,sort_keys=True)+'\n';result=first300(raw)
        self.assertEqual(json.loads(result),rows[:600]);self.assertTrue(raw.startswith(result[:-3]))
    def test_missing_parent_rejected(self):
        with self.assertRaises(ValueError):first300(json.dumps(self.rows()[:-1]))
    def test_reordered_twins_rejected(self):
        rows=self.rows();rows[0],rows[1]=rows[1],rows[0]
        with self.assertRaises(ValueError):first300(json.dumps(rows))
    def test_duplicate_pairs_rejected(self):
        rows=self.rows();rows[2]['pair_id']=rows[3]['pair_id']='0'
        with self.assertRaises(ValueError):first300(json.dumps(rows))
if __name__=='__main__':unittest.main()
