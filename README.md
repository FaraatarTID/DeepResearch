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

   Copy the example secrets file:

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
export BRAVE_MAX_QUERIES=5
export SEMANTIC_MAX_RETRIES=5
export SEMANTIC_QUERY_DELAY_S=0.4
export SEMANTIC_MAX_QUERIES=5
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
