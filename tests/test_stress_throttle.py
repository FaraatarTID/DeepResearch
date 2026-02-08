import asyncio
import unittest
import time
from deep_research.search import brave_search
from deep_research.config import CONCURRENCY

class FakeResp:
    def __init__(self, status=200, headers=None, json_data=None, read_delay=0.1):
        self.status = status
        self.headers = headers or {}
        self._json = json_data or {"web": {"results": []}}
        self._read_delay = read_delay
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        return False
    async def json(self):
        return self._json
    async def read(self):
        # simulate some IO delay
        await asyncio.sleep(self._read_delay)
        return b"<html></html>"

class FakeSession:
    def __init__(self, responses):
        self._iter = iter(responses)
    def get(self, *args, **kwargs):
        try:
            resp = next(self._iter)
        except StopIteration:
            resp = FakeResp()
        return resp

class TestStressThrottle(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_fetch_bounded(self):
        # Build results where brave returns many urls
        fake_results = [{"title": f"t{i}", "url": f"http://example.com/{i}", "description": "d"} for i in range(20)]
        # Prepare a response that returns those results and a read delay
        resp = FakeResp(status=200, json_data={"web": {"results": fake_results}}, read_delay=0.05)
        session = FakeSession([resp])

        # We'll measure max concurrent reads by wrapping fetch_text side effect
        max_concurrent = 0
        current = 0
        lock = asyncio.Lock()

        orig_read = FakeResp.read

        async def tracked_read(self):
            nonlocal max_concurrent, current
            async with lock:
                current += 1
                max_concurrent = max(max_concurrent, current)
            try:
                await asyncio.sleep(self._read_delay)
                return b"<html></html>"
            finally:
                async with lock:
                    current -= 1

        FakeResp.read = tracked_read

        # run brave_search which uses CONCURRENCY for fetch_semaphore
        brave_semaphore = asyncio.Semaphore(1)
        throttle_lock = asyncio.Lock()
        throttle_state = {"last_request": 0.0, "delay_s": 0.0}

        snippets = await brave_search("q", session, brave_semaphore, throttle_lock, throttle_state)

        # restore
        FakeResp.read = orig_read

        # Assert we never exceeded CONCURRENCY concurrent fetches
        self.assertLessEqual(max_concurrent, CONCURRENCY)

if __name__ == '__main__':
    unittest.main()
