import asyncio
import unittest
from types import SimpleNamespace

from deep_research.search import brave_search
from deep_research.config import BRAVE_QUERY_DELAY_S, BRAVE_MAX_DELAY_S

class FakeResp:
    def __init__(self, status, headers=None, json_data=None):
        self.status = status
        self.headers = headers or {}
        self._json = json_data or {}
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        return False
    async def json(self):
        return self._json
    async def read(self):
        return b""

class FakeSession:
    def __init__(self, responses):
        self._iter = iter(responses)
    def get(self, *args, **kwargs):
        try:
            resp = next(self._iter)
        except StopIteration:
            resp = FakeResp(200, {}, {"web": {"results": []}})
        return resp

class TestThrottle(unittest.TestCase):
    def test_retry_after_updates_delay(self):
        async def run():
            # First response is 429 with Retry-After header, then a 200
            responses = [FakeResp(429, {"Retry-After": "2"}), FakeResp(200, {}, {"web": {"results": []}})]
            session = FakeSession(responses)
            from asyncio import Semaphore, Lock
            sem = Semaphore(1)
            lock = Lock()
            throttle_state = {"last_request": 0.0, "delay_s": BRAVE_QUERY_DELAY_S}
            snippets = await brave_search("q", session, sem, lock, throttle_state)
            # After handling Retry-After=2, delay_s should be at least 2 (but limited by BRAVE_MAX_DELAY_S)
            self.assertGreaterEqual(throttle_state.get("delay_s", 0), 2.0)
        asyncio.run(run())

if __name__ == '__main__':
    unittest.main()
