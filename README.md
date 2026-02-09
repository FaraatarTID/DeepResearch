# 🔬 Deep Research Tool

An AI-powered research assistant that performs comprehensive research on any topic using web search and academic sources.

## Features

- 🤖 **AI-Powered Keyword Generation**: Uses Google's Gemini AI to generate relevant search keywords
- 🔍 **Multi-Source Search**: Searches both web (via Brave Search) and academic sources (Semantic Scholar)
- 📊 **Smart Filtering**: Filters and deduplicates results using AI-based relevance checking
- 📈 **Bibliometrics**: Generates citation analysis and source statistics
- 📝 **Report Synthesis**: Creates comprehensive research reports in Markdown and DOCX formats
- 🎨 **User-Friendly Interface**: Clean Streamlit interface with real-time progress tracking

## Quick Start

### Local Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/deep-research-tool.git
   cd deep-research-tool
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API keys**

   Preferred: copy the example environment file and set your keys locally:

   ```bash
   cp .env.example .env
   ```

   Then edit `.env` with your keys.

   Streamlit Cloud: copy the example secrets file:

   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

   Edit `.streamlit/secrets.toml` and add your API keys:

   ```toml
   GEMINI_KEY = "your-gemini-api-key"
   BRAVE_API_KEY = "your-brave-api-key"
   UNPAYWALL_EMAIL = "your-email@example.com"
   ```

4. **Run the app**
   ```bash
   streamlit run app.py
   ```

> Security note: never commit real API keys. Rotate any keys that were ever committed.

### Getting API Keys

- **Gemini API Key**: Get it from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Brave Search API Key**: Sign up at [Brave Search API](https://brave.com/search/api/)
- **Unpaywall Email**: Just use your email address (free, no signup needed)

## Deployment to Streamlit Cloud

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on deploying to Streamlit Cloud.

**Quick Deploy:**

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Add your API keys in the Secrets section
5. Deploy!

## Usage

1. Enter your research topic in the text field
2. (Optional) Adjust advanced settings:
   - **General Search Rounds**: Number of web search iterations (0-10)
   - **Academic Search Rounds**: Number of academic search iterations (0-10)
3. Click **"🚀 Start Research"**
4. Wait for the AI to:
   - Generate keywords
   - Search sources
   - Filter and deduplicate
   - Generate bibliometrics
   - Synthesize a report
5. Download your report in DOCX or Markdown format

### Rate-limit tuning (optional)

You can adjust retry behavior and pacing via environment variables if you hit API rate limits:

```bash
export BRAVE_MAX_RETRIES=3
export BRAVE_CONCURRENCY=2
export BRAVE_QUERY_DELAY_S=0.2
export BRAVE_MAX_DELAY_S=4.0
export GEMINI_MODEL=gemini-flash-latest
export GEMINI_MAX_DELAY_S=60.0
export SEMANTIC_MAX_RETRIES=5
export SEMANTIC_QUERY_DELAY_S=0.4
export SEMANTIC_MAX_DELAY_S=8.0
export SEMANTIC_SCHOLAR_API_KEY=your_api_key_here
```

### Disk cache (optional)

The fetcher stores a lightweight on-disk cache of fetched URLs to improve resilience.

```bash
export CACHE_ENABLE=true
export CACHE_TTL_S=86400
export CACHE_MAX_BYTES=200000000
```

#### Cache maintenance

Purge cache:

```bash
python -m deep_research.main --purge-cache
```

Cleanup cache (TTL/size enforcement):

```bash
python -m deep_research.main --cleanup-cache
```

## Project Structure

```
deep-research/
├── app.py                  # Main Streamlit application
├── deep_research/          # Core research modules
│   ├── core.py            # Keyword generation and synthesis
│   ├── search.py          # Search functionality
│   ├── utils.py           # Utility functions
│   ├── config.py          # Configuration
│   └── ...
├── tests/                  # Unit tests
├── requirements.txt        # Python dependencies
├── DEPLOYMENT.md          # Deployment guide
└── README.md              # This file
```

## Technologies Used

- **Streamlit**: Web interface
- **Google Gemini AI**: Keyword generation and content synthesis
- **Brave Search API**: Web search
- **Semantic Scholar API**: Academic paper search
- **aiohttp**: Async HTTP requests
- **scikit-learn**: Text similarity and deduplication
- **python-docx**: DOCX report generation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

---

Made with ❤️ using Streamlit and Google Gemini AI

## Reliability & Pre-Mortem Checks

This project includes a few features to reduce silent failures and make production
issues diagnosable:

- **Structured external errors**: `deep_research.utils.ExternalServiceError` is
   raised by `gemini_complete` and `fetch_text` on persistent failures. The
   pipeline opts into surfacing fatal errors from searches. This avoids silent
   empty-string fallbacks that hide root causes.
- **Cooperative cancellation**: `run_research` accepts a `cancel_check` callable
   (e.g., `lambda: stop_event.is_set()`) which is checked early and propagated
   to searches and synthesis so UI stop requests abort long-running runs.
- **Atomic file writes**: DOCX and text outputs are written atomically to avoid
   partial files on crashes or interruptions.
- **Pre-mortem static checks**: `scripts/pre_mortem_checks.py` scans for
   patterns like `except: pass` and other anti-patterns. It's run in CI and as a
   pre-commit hook.

CI will run `pre-commit` and `flake8` and fail on issues. To run checks locally:

```bash
python -m pip install -r requirements-dev.txt
pre-commit install
pre-commit run --all-files
python scripts/pre_mortem_checks.py
```

## Security & Secrets

- Never commit real API keys. Use `.env` locally or Streamlit Secrets in production.
- Rotate keys immediately if they were ever committed.
- Untrusted web content is treated as data only and sanitized before synthesis, but you should still treat outputs as untrusted and review for accuracy.

## Content Security Pipeline

Untrusted content is filtered and normalized before it reaches the LLM. The pipeline:
1) strips common instruction-like lines, 2) normalizes whitespace and URLs, and
3) extracts higher-signal sentences (years, citations, numeric facts) within a strict size budget.
