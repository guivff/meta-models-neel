import types,unittest
from decimal import Decimal
from .e107b_generation243 import enforce_cap
from .resume_e340 import rate_loop

class ForecastTransportTest(unittest.TestCase):
    def fixture(self):
        n={'CAP':Decimal(5)};exec('class Ledger:\n def reserve(self,x):return x<=CAP\n def settle(self,x):return x<=CAP\n def summary(self):return {"cap_usd":str(CAP)}\ndef one(client):return CAP\n',n)
        return n,types.SimpleNamespace(CAP=Decimal(5)),types.SimpleNamespace(ledger=n['Ledger']())
    def test_cap2_enforced_in_actual_ledger_not_default5(self):
        n,a,c=self.fixture();enforce_cap(a,c,n['one']);self.assertFalse(c.ledger.reserve(Decimal('2.01')));self.assertEqual(c.ledger.summary()['cap_usd'],'2')
    def test_reload_cannot_raise_next_physical_cap(self):
        n,a,c=self.fixture();enforce_cap(a,c,n['one']);n['CAP']=Decimal(5);enforce_cap(a,c,n['one']);self.assertEqual(n['one'](c),Decimal(2))
    def test_rate_success_is_not_resent_after_refusal(self):
        sent=[];book=[];wait=[]
        r=rate_loop(lambda i:(sent.append(i)or dict(id=str(i))),lambda rid:dict(http_status=429 if rid=='0' else 200,response={}),book.append,wait.append)
        self.assertEqual(sent,[0,1]);self.assertEqual(book,['0']);self.assertEqual(wait,[30]);self.assertEqual(r['id'],'1')

if __name__=='__main__':unittest.main()
