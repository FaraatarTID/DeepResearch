import asyncio
import unittest
from unittest.mock import patch

from deep_research.pipeline import run_research

class TestCancellation(unittest.TestCase):
    def test_immediate_cancel(self):
        async def run():
            result = await run_research(
                subject="test",
                general_rounds=1,
                academic_rounds=0,
                status_callback=None,
                cancel_check=lambda: True,
            )
            self.assertIsNotNone(result.error)
            self.assertEqual(result.error, "Cancelled")
        asyncio.run(run())

    @patch('deep_research.search.search_all')
    def test_cancel_before_search(self, mock_search):
        async def fake_search(*args, **kwargs):
            await asyncio.sleep(0.1)
            return []
        mock_search.side_effect = fake_search

        async def run():
            # cancel_check flips to True immediately
            result = await run_research(
                subject="test",
                general_rounds=1,
                academic_rounds=0,
                status_callback=None,
                cancel_check=lambda: True,
            )
            self.assertEqual(result.error, "Cancelled")
        asyncio.run(run())

if __name__ == '__main__':
    unittest.main()
