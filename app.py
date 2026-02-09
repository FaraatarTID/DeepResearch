import streamlit as st
import asyncio
import os
from pathlib import Path

from deep_research.pipeline import run_research
from deep_research.utils import build_doc, logger
from deep_research.config import GEMINI_KEY, BRAVE_API_KEY
from deep_research.search import cleanup_fetch_cache
import logging

# Setup logging to Streamlit
class StreamlitHandler(logging.Handler):
    def __init__(self, container, max_messages: int = 200):
        super().__init__()
        self.container = container
        self.max_messages = max_messages
        self._count = 0
        self._truncated = False

    def emit(self, record):
        if self._truncated:
            return
        self._count += 1
        if self._count > self.max_messages:
            self.container.code("Log output truncated to keep the UI responsive.", language=None)
            self._truncated = True
            return
        msg = self.format(record)
        self.container.code(msg, language=None)

# Run cache cleanup on startup to enforce TTL/size caps
cleanup_fetch_cache()

# Page Config

# Page Config
st.set_page_config(
    page_title="Deep Research Tool",
    page_icon="🔬",
    layout="wide"
)

# Title
st.title("🔬 Deep Research Tool")
st.markdown("---")

# Sidebar for Settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Keys (Optional override)
    st.markdown("### API Keys")
    
    # Gemini
    if GEMINI_KEY:
        st.success("✅ Gemini API Key loaded")
        new_gemini = st.text_input("Override Gemini API Key", type="password", placeholder="Enter new key to override")
    else:
        st.warning("⚠️ Gemini API Key missing")
        new_gemini = st.text_input("Gemini API Key", type="password")

    # Brave
    if BRAVE_API_KEY:
        st.success("✅ Brave API Key loaded")
        new_brave = st.text_input("Override Brave API Key", type="password", placeholder="Enter new key to override")
    else:
        st.warning("⚠️ Brave API Key missing")
        new_brave = st.text_input("Brave API Key", type="password")
    
    if new_gemini:
        os.environ["GEMINI_KEY"] = new_gemini
        # Reset cached client via public helper instead of mutating module internals
        try:
            from deep_research import utils as dr_utils
            dr_utils.reset_client()
        except Exception as e:
            logger.exception("Failed to reset Gemini client: %s", e)
        
    if new_brave:
        try:
            from deep_research import config as dr_config
            dr_config.BRAVE_API_KEY = new_brave
        except Exception as e:
            logger.exception("Failed to set Brave API key: %s", e)

    st.markdown("---")
    st.markdown("### About")
    st.info(
        "This tool uses AI to perform deep research on any topic.\n\n"
        "1. Generates keywords\n"
        "2. Searches Web & Academic sources\n"
        "3. Filters & Deduplicates\n"
        "4. Synthesizes a Report"
    )

# Main Input
col1, col2 = st.columns([3, 1])
with col1:
    subject = st.text_input("Research Subject", placeholder="e.g., The Future of Quantum Computing")

with col2:
    st.write("") # Spacer
    st.write("")
    start_btn = st.button("🚀 Start Research", type="primary", use_container_width=True)

# Advanced Options
with st.expander("Advanced Options"):
    c1, c2 = st.columns(2)
    with c1:
        general_rounds = st.number_input("General Search Rounds", min_value=0, max_value=10, value=3)
    with c2:
        academic_rounds = st.number_input("Academic Search Rounds", min_value=0, max_value=10, value=2)

# Main Logic
# Main Logic
if "report" not in st.session_state:
    st.session_state.report = None
if "biblio_text" not in st.session_state:
    st.session_state.biblio_text = None

if start_btn and subject:
    st.session_state.report = None
    st.session_state.biblio_text = None
    status_container = st.status("Starting research...", expanded=True)

    # Add log expander
    log_expander = st.expander("View Logs", expanded=False)

    # Setup logging
    st_handler = StreamlitHandler(log_expander)
    root_logger = logging.getLogger()
    root_logger.addHandler(st_handler)
    root_logger.setLevel(logging.INFO)

    async def run_with_status():
        try:
            def status_update(message: str) -> None:
                status_container.write(message)

            result = await run_research(
                subject=subject,
                general_rounds=general_rounds,
                academic_rounds=academic_rounds,
                status_callback=status_update,
            )

            if result.error:
                status_container.error(result.error)
                return None, None

            status_container.update(label="Research Complete!", state="complete", expanded=False)
            return result.report, result.biblio_text

        except Exception as e:
            logger.exception("Error during run_with_status: %s", e)
            import traceback
            err_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            status_container.error(err_msg)
            st.error(err_msg) # Also show outside status container
            return None, None

    # Run the coroutine on a dedicated event loop to avoid using asyncio.run in library code
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        try:
            report, biblio_text = loop.run_until_complete(run_with_status())
            st.session_state.report = report
            st.session_state.biblio_text = biblio_text
        except Exception as e:
            logger.exception("Critical Error running event loop: %s", e)
            st.error(f"Critical Error in Event Loop: {e}")
            st.session_state.report = None
            st.session_state.biblio_text = None
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        try:
            asyncio.set_event_loop(None)
        except Exception:
            pass
        try:
            loop.close()
        except Exception:
            pass
        # Cleanup logger
        if 'st_handler' in locals():
            root_logger.removeHandler(st_handler)

# Display Results if available in session state
if st.session_state.report:
    st.success("Research completed successfully!")
    
    # Display Report
    st.markdown("## 📄 Research Report")
    st.markdown(st.session_state.report)
    
    # Download Buttons
    c1, c2, c3 = st.columns(3)
    
    # DOCX
    doc = build_doc(st.session_state.report)
    # Save to a temporary buffer for download
    from io import BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    with c1:
        st.download_button(
            label="📥 Download DOCX",
            data=buffer,
            file_name=f"research_report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    # Markdown
    with c2:
        st.download_button(
            label="📥 Download Markdown",
            data=st.session_state.report,
            file_name=f"research_report.md",
            mime="text/markdown"
        )

    # Bibliometrics
    if st.session_state.biblio_text:
        with c3:
            st.download_button(
                label="📥 Download Bibliometrics",
                data=st.session_state.biblio_text,
                file_name=f"bibliometrics.txt",
                mime="text/plain"
            )
