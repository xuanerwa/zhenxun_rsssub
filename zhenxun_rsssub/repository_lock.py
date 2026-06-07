from __future__ import annotations

from contextlib import ExitStack, contextmanager
from threading import RLock

from .repository_utils import feed_key

_feed_write_locks: dict[str, RLock] = {}


def get_feed_write_lock(name: str) -> RLock:
    return _feed_write_locks.setdefault(feed_key(name), RLock())


@contextmanager
def locked_feeds(*names: str):
    keys = sorted({feed_key(name) for name in names if name})
    with ExitStack() as stack:
        for key in keys:
            stack.enter_context(get_feed_write_lock(key))
        yield
