import numpy as np

def gate_counts(correct, agree, fractions, thresholds):
    correct=np.asarray(correct,dtype=bool);agree=np.asarray(agree,dtype=bool);f=np.asarray(fractions,dtype=float);t=np.asarray(thresholds,dtype=float)
    if correct.shape!=agree.shape or f.shape!=correct.shape or not np.isfinite(f).all():raise ValueError('finite matched gate')
    mask=np.column_stack([agree,*[agree&(f>x) for x in t]])
    return np.stack([np.ones_like(mask),mask,mask&correct[:,None]],axis=-1).astype(np.int64)
