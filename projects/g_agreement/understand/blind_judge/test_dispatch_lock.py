import fcntl
import pytest
from .dispatch_lock import dispatch_lock


def test_leftover_inode_reusable_and_active_lock_not_removed(tmp_path):
    p=tmp_path/'DISPATCH.lock';p.touch();inode=p.stat().st_ino
    with p.open('a') as held:
        fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(RuntimeError,match='Active dispatcher'):
            with dispatch_lock(p):raise AssertionError('must not enter')
        assert p.stat().st_ino==inode
        fcntl.flock(held,fcntl.LOCK_UN)
    with dispatch_lock(p):assert p.stat().st_ino==inode
    with dispatch_lock(p):assert p.stat().st_ino==inode


def test_exception_releases_kernel_lock(tmp_path):
    p=tmp_path/'DISPATCH.lock'
    with pytest.raises(ValueError):
        with dispatch_lock(p):raise ValueError('synthetic')
    with dispatch_lock(p):pass
