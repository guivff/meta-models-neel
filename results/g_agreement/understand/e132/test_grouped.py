"""Synthetic only. No E107/E116 real data imported, read or classified."""
import unittest
import numpy as np
from grouped import joint_groups,make_folds,oof,auc,paired_endpoint_difference


def fixture():
    return [dict(item_group=f'i{i}',template_group=f't{i//4}',
                 text=('east ' if i%2 else 'west ')+f'uniqueitem{i}') for i in range(40)]


class Synthetic(unittest.TestCase):
    def test_transitive_joint_groups(self):
        data=[dict(item_group='a',template_group='x'),dict(item_group='a',template_group='y'),
              dict(item_group='b',template_group='y')]
        self.assertEqual(len(set(joint_groups(data))),1)

    def test_both_group_types_held_together(self):
        data=fixture();labels=np.arange(40)%2;f=make_folds(data,labels)
        np.testing.assert_array_equal(f,make_folds(data,labels))
        for field in ('item_group','template_group'):
            for g in {r[field] for r in data}:
                self.assertEqual(len({f[i] for i,r in enumerate(data) if r[field]==g}),1)

    def test_fewer_than_five_groups_fail(self):
        data=fixture()
        for r in data:r['template_group']='same'
        with self.assertRaises(ValueError):make_folds(data,np.arange(40)%2)

    def test_fold_vocabulary_no_leak(self):
        data=fixture();labels=np.arange(40)%2;f=make_folds(data,labels)
        p,v=oof(data,labels,f,'text',[0,1])
        self.assertEqual(auc(labels,p,[0,1],'binary'),1.)
        for i in range(40):self.assertNotIn(f'uniqueitem{i}',v[f[i]])

    def test_unseen_class_unavailable_not_zero(self):
        data=fixture();labels=np.arange(40);f=make_folds(data,np.arange(40)%2)
        p,_=oof(data,labels,f,'text',list(range(40)))
        self.assertIsNone(auc(labels,p,list(range(40)),'macro_ovr'))
        with self.assertRaises(ValueError):auc(labels,p,[0,1],'unspecified')

    def test_paired_difference_and_endpoint_mask(self):
        y=np.tile([0,1],20);r=np.c_[1-y,y];p=np.full((40,2),.5)
        # Each item-group contains both classes, so every resample remains defined.
        report=paired_endpoint_difference(y,r,p,[0,1],'binary',np.ones(40,bool),np.arange(40)//2,draws=20)
        self.assertEqual(report['difference'],.5)
        self.assertEqual(report['registered_B_rule'],'MET')
        report=paired_endpoint_difference(y,r,p,[0,1],'binary',y==1,np.arange(40)//2,draws=20)
        self.assertEqual(report['status'],'NOT_EVALUABLE')


if __name__=='__main__':unittest.main()
