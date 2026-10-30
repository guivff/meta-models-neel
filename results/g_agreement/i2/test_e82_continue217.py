import unittest
from e82_continue217 import response_disposition
class Tests(unittest.TestCase):
 def response(self,finish):return dict(http_status=200,response=dict(provider='Google',model='google/gemini-3.1-flash-lite',usage=dict(cost=.1),choices=[dict(finish_reason=finish)]))
 def test_charged_length_terminal_not_retry(self):self.assertEqual(response_disposition(self.response('length')),'TERMINAL_UNPARSEABLE')
 def test_stop_validates(self):self.assertEqual(response_disposition(self.response('stop')),'VALIDATE')
 def test_402_pauses_bank(self):self.assertEqual(response_disposition(dict(http_status=402,response={})), 'PAUSE_402')
 def test_unknown_provider_error_stops(self):self.assertRaises(RuntimeError,response_disposition,dict(http_status=503,response={}))
 def test_unknown_finish_stops(self):self.assertRaises(RuntimeError,response_disposition,self.response('content_filter'))
 def test_wrong_provider_stops(self):
  x=self.response('stop');x['response']['provider']='Other';self.assertRaises(AssertionError,response_disposition,x)
if __name__=='__main__':unittest.main()
