"""Persistent flock inode: an old filename is not an active process lock."""
from contextlib import contextmanager
import fcntl


@contextmanager
def dispatch_lock(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as handle:
        try:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Active dispatcher holds DISPATCH.lock; leave it intact and wait for that process.') from exc
        try:
            yield
        finally:
            fcntl.flock(handle,fcntl.LOCK_UN)
    # Never unlink: waiters must continue to reference the same inode.
