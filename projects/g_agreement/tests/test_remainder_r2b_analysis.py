import pytest
from projects.g_agreement.r_bench import remainder_r2b_analysis as A


def test_paired_specificity_bootstrap_and_undefined_decoy():
    items=[dict(dataset=f'd{i//4}',label=i%2,population='main',corpus=f'c{i//8}',correct=dict(sham=1.,mean_ablation=0.,random_ablation=1.)) for i in range(16)]
    result=A.summarize(items,draws=50)
    assert result[0]['estimate']==-1 and result[0]['ci95']==[-1,-1]
    assert result[1]['estimate']==0 and result[2]['estimate']==-1
    with pytest.raises(ValueError,match='Undefined'):A.summarize([r for r in items if r['label']==0],draws=10)


def test_unexpected_arm_decoy():
    with pytest.raises(ValueError,match='decoy'):
        A.paired_items([dict(cell=dict(dataset='d',item_id='i',arm='decoy'))])
