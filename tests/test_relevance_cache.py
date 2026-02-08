import asyncio
import unittest
from unittest.mock import patch
from deep_research.search import check_relevance

class TestRelevanceCache(unittest.TestCase):
    @patch('deep_research.search.gemini_complete')
    def test_relevance_cache_hits(self, mock_gemini):
        async def run_test():
            mock_gemini.return_value = "YES"
            # First call should invoke gemini
            r1 = await check_relevance("topic", "title", "abstract")
            self.assertTrue(r1)
            # Second call with same inputs should be served from cache
            r2 = await check_relevance("topic", "title", "abstract")
            self.assertTrue(r2)
            # gemini_complete should have been called only once due to caching
            self.assertEqual(mock_gemini.call_count, 1)
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
