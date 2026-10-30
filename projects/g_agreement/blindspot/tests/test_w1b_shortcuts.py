from collections import Counter
import numpy as np
from projects.g_agreement.blindspot.w1b_shortcuts import padding_text, grouped_predictions, flags


def test_padding_excludes_separator_carrier_and_terminal_label():
    assert padding_text('pad pad \n\nmemo x: 123') == 'pad pad '
    assert padding_text('memo pad: AMBER') == ''
    assert padding_text('padlock value') == ''


def test_held_out_cluster_vocabulary_does_not_leak_label():
    # Each cluster has unique class-specific tokens: an in-sample model could
    # memorize all labels, but a held-out vocabulary cannot see these tokens.
    bags, y, groups = [], [], []
    for cluster in range(4):
        for side in (0,1):
            bags.append(Counter({f'unique-{cluster}-{side}':1}))
            y.append(side)
            groups.append(str(cluster))
    predictions, folds = grouped_predictions(bags,y,groups)
    assert np.allclose(predictions,0)
    assert len(folds)==4 and all(f['auroc']==0.5 for f in folds)
    assert all(f['held_out_cluster'] not in f['train_clusters'] for f in folds)


def test_raw_repetition_counts_are_retained_and_threshold_is_inclusive():
    bags = [Counter({'pad':1+side}) for cluster in range(4) for side in (0,1)]
    y = [side for cluster in range(4) for side in (0,1)]
    groups = [str(cluster) for cluster in range(4) for side in (0,1)]
    _, folds = grouped_predictions(bags,y,groups)
    assert all(f['auroc']==1 for f in folds)
    assert flags(.8,.5)['padding_artefact_possible']
    assert flags(.5,.8)['status']=='possible shortcut'
    assert not flags(.5,.8)['padding_artefact_possible']
    assert flags(.799,.799)['status']=='not flagged'
