from .adapter import rate,gain,reading
from projects.g_agreement.e108_analysis.rules import loo_modes

def test_wilson_missing():
 r=rate([True,False,None]);assert r['estimate']==.5 and r['kept']==2 and r['missing']==1 and r['CI95'][0]>0

def test_empty():assert rate([None])['CI95'] is None

def test_paired():
 xs=[{'hits':{60:True,52:False}},{'hits':{60:False,52:None}}]
 r=gain(xs,52);assert r['estimate']==1 and r['paired']==1 and r['CI95']==[1.,1.]

def test_no_pairs():assert gain([{'hits':{60:None,44:True}}],44)['estimate'] is None

def test_threshold():
 assert reading({'estimate':.4,'CI95':[.25,.6]}).startswith('intermediate')
 assert reading({'estimate':.4,'CI95':[.251,.6]})=='tracks specific choices'
 assert reading({'estimate':.10,'CI95':[0,.2]})=='predicts the prior'

def test_original_loo_tie():
 xs=[{'id':'a','category':'sport','choice':'a'},{'id':'b','category':'sport','choice':'b'},{'id':'c','category':'sport','choice':'a'}]
 assert loo_modes(xs)=={'a':1,'b':0,'c':1}
