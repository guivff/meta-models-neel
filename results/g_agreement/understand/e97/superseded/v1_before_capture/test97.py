import json
import re
import unittest
from collections import Counter
from pathlib import Path
from rows97 import specifications, render, check
class Tests(unittest.TestCase):
    def test_protocol(self):
        specs=specifications(); self.assertEqual(len(specs),40)
        self.assertEqual(set(Counter(s['family'] for s in specs).values()),{10})
        for s in specs:
            for t in range(12):
                for f in range(7):
                    for label in 'AB':
                        text=render(s['row'],t,f,label)
                        self.assertEqual(check(s['row'],text),label)
                        if s['family']=='decision_ladder':
                            self.assertTrue(text.startswith("If "+s['decision_condition']+", reply 'alpha'; otherwise reply 'beta'.\n"))
                            self.assertTrue(text.endswith('\nReply:'))
    def test_regex_values(self):
        for s in specifications():
            for label in 'AB':
                example=('lamp is '+s['values'][label]) if s['row']=='lamp_power' else ('JSON '+s['values'][label]) if s['row']=='json_key_phase' else s['values'][label]
                hits=[k for k,p in s['value_regex'].items() if re.search(p,example)]
                self.assertIn(label,hits)
                # Ambiguous overlaps remain unresolved, never silently assigned.
    def test_parser_counterexamples(self):
        for row,a,b in [('queue_front','red','blue'),('stack_top','red','blue'),('number_sign','+37','-37')]:
            text=render(row,0,0,'A')
            before,current=text.split('CURRENT example:\n')
            if row=='number_sign': current=current.replace(a,b)
            else: current=current.replace('red','TEMP').replace('blue','red').replace('TEMP','blue')
            self.assertEqual(check(row,before+'CURRENT example:\n'+current),'B')
    def test_primary_regex(self):
        from regex97 import classify
        self.assertEqual(classify('door_lock','The door is locked.'),'A')
        self.assertEqual(classify('door_lock','The door is unlocked.'),'B')
        for text in ['The door is not locked.', "If locked reply alpha.", 'locked or unlocked', 'alpha', 'beta', 'The note says locked.']:
            self.assertIsNone(classify('door_lock',text))
        self.assertIsNone(classify('divisibility_decision','not a multiple of three'))
    def test_artifacts(self):
        root=Path(__file__).parent
        if not (root/'MANIFEST.json').exists(): self.skipTest('Bank not built')
        m=json.loads((root/'MANIFEST.json').read_text())
        import hashlib
        for p,h in m['files'].items(): self.assertEqual(hashlib.sha256((root/p).read_bytes()).hexdigest(),h)
        public=[json.loads(l) for l in (root/'cache/bank_2026-10-28/PUBLIC_ITEMS.jsonl').read_text().splitlines()]
        self.assertEqual(len(public),6720)
        for r in public:
            self.assertEqual(set(r),{'item_id','split','text','input_ids','read_position'})
            self.assertEqual(r['read_position'],len(r['input_ids'])-1)
if __name__=='__main__': unittest.main()
