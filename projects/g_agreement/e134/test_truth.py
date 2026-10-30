from datetime import datetime,timezone
import pytest
from .truth import *

def test_greedy_precedes_pair_and_no_value_falls_back():
 assert e131_value('  red','red','blue',-2,'old','A','B')['truth']=='A'
 assert e131_value('no stated candidate','red','blue',-2,'old','A','B')['truth']=='B'
 assert e131_value('red and blue','red','blue',2,'old','A','B')['truth']=='A'
 assert e131_value('neither','red','blue',0,'old','A','B')['truth'] is None

def test_language_label_and_fact_fallback_clock():
 early=datetime(2026,10,30,10,59,59,tzinfo=timezone.utc)
 assert unhooked_value('language_plan','A',as_of=early)['truth_basis']==LABEL_BASED
 with pytest.raises(ValueError,match='await sealed E131'):unhooked_value('fact_recall','A',as_of=early)
 assert unhooked_value('fact_recall','A',as_of=FACT_FALLBACK_UTC)['truth_basis']==LABEL_BASED
 actual=e131_value('blue','red','blue',2,'old','A','B')
 assert unhooked_value('fact_recall','A',e131=actual,e131_sealed_at=early,as_of=early)['truth']=='B'
 with pytest.raises(ValueError):unhooked_value('fact_recall','A',as_of=datetime(2026,10,30,11))


def test_label_based_rows_shown_separately_in_each_score():
 from .policy import score
 rows=[dict(id='1',truth='A',readings={44:'A'},truth_basis=BEHAVIOUR),dict(id='2',truth='B',readings={44:'A'},truth_basis=LABEL_BASED)]
 result=score(rows,'P44',draws=10)
 assert set(result['truth_basis_scores'])=={BEHAVIOUR,LABEL_BASED}
 assert result['truth_basis_scores'][BEHAVIOUR]['metrics']['accuracy']['estimate']==1
 assert result['truth_basis_scores'][LABEL_BASED]['metrics']['accuracy']['estimate']==0
 assert result['truth_basis_scope'].startswith('MIXED')


def test_late_seal_cannot_replace_noon_fallback():
 actual=e131_value('blue','red','blue',2,'old','A','B')
 late=datetime(2026,10,30,11,1,tzinfo=timezone.utc)
 with pytest.raises(ValueError,match='late E131'):unhooked_value('fact_recall','A',e131=actual,e131_sealed_at=late,as_of=late)
