"""
轻量级内存限流。

- 滑动窗口（默认 60 秒）按 IP + 路径桶计数
- 纯 ASGI 中间件：只读 scope，不包裹响应体，因此不会破坏
  `/api/chat/ask` 的 SSE 流（BaseHTTPMiddleware 会缓冲流，不能用）
- 单进程内存实现；多 worker / 多实例部署时应换成 Redis

限流只覆盖敏感路径：认证与问答。健康检查、静态资源不受影响。
"""

from __future__ import annotations

import threading
import time
from collections import deque

from starlette.responses import JSONResponse

from app.config import settings


class SlidingWindowLimiter:
    """线程安全的滑动窗口计数器。"""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(
        self,
        key: str,
        limit: int,
        window: float = 60.0,
        now: float | None = None,
    ) -> bool:
        """在 window 秒内允许 limit 次；limit <= 0 表示不限制。"""
        if limit <= 0:
            return True

        current = time.monotonic() if now is None else now
        cutoff = current - window

        with self._lock:
            queue = self._events.setdefault(key, deque())
            while queue and queue[0] <= cutoff:
                queue.popleft()

            if len(queue) >= limit:
                return False

            queue.append(current)

            # 防止 key 无限增长（大量不同 IP 时）
            if len(self._events) > 10000:
                empty = [k for k, v in self._events.items() if not v]
                for k in empty:
                    self._events.pop(k, None)
            return True

    def count(
        self,
        key: str,
        window: float = 60.0,
        now: float | None = None,
    ) -> int:
        current = time.monotonic() if now is None else now
        cutoff = current - window
        with self._lock:
            queue = self._events.get(key)
            if not queue:
                return 0
            while queue and queue[0] <= cutoff:
                queue.popleft()
            return len(queue)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


class RateLimitMiddleware:
    """纯 ASGI 限流中间件。"""

    def __init__(self, app):
        self.app = app
        self.limiter = SlidingWindowLimiter()

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not settings.RATE_LIMIT_ENABLED:
            await self.app(scope, receive, send)
            return

        rule = self._rule_for(scope.get("path", ""))
        if rule is None:
            await self.app(scope, receive, send)
            return

        bucket, limit = rule
        client = scope.get("client") or ("unknown", 0)
        key = f"{bucket}:{client[0]}"

        if not self.limiter.allow(key, limit):
            response = JSONResponse(
                {"detail": "请求过于频繁，请稍后再试"},
                status_code=429,
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    def _rule_for(path: str) -> tuple[str, int] | None:
        if path.startswith("/api/auth/"):
            return ("auth", settings.RATE_LIMIT_AUTH_PER_MINUTE)
        if path.startswith("/api/chat/ask"):
            return ("chat", settings.RATE_LIMIT_CHAT_PER_MINUTE)
        return None
