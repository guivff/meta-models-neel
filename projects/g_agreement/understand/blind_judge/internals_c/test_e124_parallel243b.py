import types,unittest
from decimal import Decimal
from .e124_parallel243b import enforce_cap

class CapNamespaceTest(unittest.TestCase):
    def fixture(self):
        namespace={'CAP':Decimal(5)}
        exec('class Ledger:\n def reserve(self,cost):return cost<=CAP\n def settle(self,cost):return cost<=CAP\n def summary(self):return {"cap_usd":str(CAP)}\ndef one(client):return CAP\n',namespace)
        api=types.SimpleNamespace(CAP=Decimal(5));client=types.SimpleNamespace(ledger=namespace['Ledger']())
        return namespace,api,client
    def test_reloaded_default_is_corrected_in_actual_ledger_and_client_globals(self):
        n,a,c=self.fixture();enforce_cap(a,c,n['one'])
        self.assertEqual(c.ledger.summary()['cap_usd'],'3');self.assertFalse(c.ledger.reserve(Decimal('3.01')))
        self.assertEqual(n['one'](c),Decimal(3));self.assertEqual(a.CAP,Decimal(3))
    def test_route_reload_after_recovery_cannot_raise_next_physical_cap(self):
        n,a,c=self.fixture();enforce_cap(a,c,n['one']);n['CAP']=Decimal(5);a.CAP=Decimal(5)
        enforce_cap(a,c,n['one']);self.assertFalse(c.ledger.reserve(Decimal('3.00001')))
    def test_original_api_module_source_is_not_edited(self):
        n,a,c=self.fixture();before=c.ledger.reserve.__func__.__code__.co_code;enforce_cap(a,c,n['one'])
        self.assertEqual(before,c.ledger.reserve.__func__.__code__.co_code)

if __name__=='__main__':unittest.main()
