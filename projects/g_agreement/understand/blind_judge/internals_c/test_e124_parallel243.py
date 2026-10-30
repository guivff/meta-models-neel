import unittest
from .e124_parallel243 import bound_events, union_raw
from .resume_e340 import rate_loop

class ParallelContinuationTest(unittest.TestCase):
    def test_all_physical_responses_retained_without_duplicate_cached_success(self):
        r=union_raw([dict(path='old',sha256='a'),dict(path='success',sha256='b')],
            [dict(path='429',sha256='c'),dict(path='success',sha256='b')])
        self.assertEqual(len(r),3)
        self.assertEqual({x['path']for x in r},{'old','success','429'})
    def test_changed_saved_response_hash_stops(self):
        with self.assertRaises(ValueError):union_raw([dict(path='old',sha256='a')],[dict(path='old',sha256='b')])
    def test_only_explicit_settled_e340_bounds_are_reported(self):
        e=dict(event='settle',authority='e34073059',usd='.01')
        self.assertEqual(bound_events([e,dict(event='reserve',authority='e34073059'),dict(event='settle',usd='0')]),[e])
    def test_five_refusal_retries_book_each_and_keep_terminal_missing_policy(self):
        sends=[];book=[];wait=[]
        result=rate_loop(lambda retry:(sends.append(retry)or dict(id=str(retry))),
            lambda rid:dict(http_status=429,response={}),book.append,wait.append)
        self.assertEqual(sends,list(range(6)));self.assertEqual(book,[str(i)for i in range(6)])
        self.assertEqual(wait,[30,60,120,240,480]);self.assertEqual(result['id'],'5')

if __name__=='__main__':unittest.main()
