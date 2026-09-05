"""轻量内存限流器（单进程）。

按「key + 动作」维护滑动时间窗，用于防止刷屏导致数据无限膨胀。
生产为单 uvicorn 进程部署，内存实现即可满足；未来多 worker 时需换 Redis。
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def check(key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    """允许则在窗口内记账并返回 (True, 0)；超限返回 (False, 需等待秒数)。"""
    now = time.monotonic()
    with _lock:
        q = _buckets[key]
        while q and q[0] <= now - window_seconds:
            q.popleft()
        if len(q) >= max_requests:
            retry_after = int(window_seconds - (now - q[0])) + 1
            return False, retry_after
        q.append(now)
        return True, 0
