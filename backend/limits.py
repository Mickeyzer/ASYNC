"""Bound local request volume and provider work. One worker only."""
from collections import defaultdict, deque
from contextlib import contextmanager
import hashlib
import threading
import time

from fastapi import HTTPException


class Limits:
    def __init__(self):
        self.lock = threading.Lock()
        self.windows = {}
        self.provider = threading.BoundedSemaphore(2)

    def check(self, key, maximum, seconds=60):
        now = time.monotonic()
        with self.lock:
            self.windows = {k:v for k,v in self.windows.items() if v and v[-1]>now-60}
            if key not in self.windows and len(self.windows)>=10000:
                raise HTTPException(429,'Request capacity reached. Try again shortly.',headers={'Retry-After':'60'})
            window = self.windows.setdefault(key,deque())
            while window and window[0]<=now-seconds:
                window.popleft()
            if len(window)>=maximum:
                raise HTTPException(429,'Too many requests. Wait a minute and retry.',headers={'Retry-After':str(seconds)})
            window.append(now)

    @contextmanager
    def slot(self):
        if not self.provider.acquire(blocking=False):
            raise HTTPException(429,'Document/advisor service is busy. Retry shortly.',headers={'Retry-After':'5'})
        try:
            yield
        finally:
            self.provider.release()


LIMITS = Limits()
