import streamlit as st
import os
from dotenv import load_dotenv
from pypdf import PdfReader # for reading PDFs

# Load env vars (API keys) BEFORE imports
load_dotenv()

# Import our custom simple modules
from modules import (
    transcript_processor,
    web_research,
    rag_engine,
    fact_checker,
    article_writer,
    narration,
    export_utils
)

# Basic Setup
st.set_page_config(page_title="AI Article Writer Pro", layout="wide")

st.title("✍️ AI Article Writer Pro")
st.markdown("Generate high-quality articles from transcripts or topics.")

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Panel 2: Research Settings
    st.subheader("Internet Research")
    enable_search = st.toggle("Enable Web Search", value=True)
    num_results = st.slider("Number of Sources", 1, 10, 3)
    
    st.divider()
    
    # Writing Settings
    tone = st.selectbox("Writing Tone", ["Professional", "Casual", "Enthusiastic", "Storytelling"])
    audience = st.text_input("Target Audience", "General Public")

# --- MAIN INTERFACE ---

# Panel 1: Input
st.subheader("1. Input Data")
topic = st.text_input("Enter Topic Name", "The Future of AI")
uploaded_file = st.file_uploader("Upload Transcript (txt, pdf)", type=["txt", "pdf"])
youtube_url = st.text_input("OR Paste YouTube Video URL")

if uploaded_file:
    # Check if PDF
    if uploaded_file.name.endswith('.pdf'):
        with st.spinner("Extracting text from PDF..."):
            try:
                reader = PdfReader(uploaded_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                transcript_text = text
                st.success("PDF Transcript loaded!")
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
                transcript_text = ""
    else:
        # Assume TXT
        transcript_text = uploaded_file.read().decode("utf-8")
        st.success("Transcript loaded from file!")
elif youtube_url:
    with st.spinner("Fetching YouTube transcript..."):
        transcript_text = transcript_processor.extract_transcript_from_youtube(youtube_url)
        if "Error" in transcript_text:
            st.error(transcript_text)
            transcript_text = ""
        else:
            st.success("Transcript loaded from YouTube!")
else:
    transcript_text = st.text_area("Or paste transcript here:")

# Session State for data persistence
if "article" not in st.session_state:
    st.session_state.article = ""
if "sources" not in st.session_state:
    st.session_state.sources = ""

# --- ACTION BUTTON ---
if st.button("🚀 Generate Article", type="primary"):
    if not os.environ.get("GROQ_API_KEY"):
        st.error("Please set GROQ_API_KEY in .env file")
        st.stop()
        
    status = st.status("Working...", expanded=True)
    
    try:
        # Step 1: Process Transcript
        status.write("🧠 Reading transcript...")
        summary = transcript_processor.summarize_transcript(transcript_text if transcript_text else topic)
        
        # Step 2: Web Research
        web_data = ""
        if enable_search:
            status.write("🌍 Searching the web...")
            web_data = web_research.get_web_facts(topic, num_results)
            
        # Step 3: Knowledge Fusion
        status.write("🔗 Connecting dots...")
        fused_data = rag_engine.fuse_knowledge(summary, web_data, topic)
        
        # Step 4: Write Draft
        status.write("✍️ Drafting content...")
        draft = article_writer.write_article(fused_data, tone, audience)
        
        # Step 5: Fact Check
        status.write("🔍 Verify facts...")
        final_article = fact_checker.verify_facts(draft)
        
        st.session_state.article = final_article
        st.session_state.sources = web_data
        status.update(label="Done!", state="complete", expanded=False)
        
    except Exception as e:
        status.update(label="Error", state="error")
        st.error(f"Something went wrong: {e}")

# --- OUTPUT DISPLAY ---
if st.session_state.article:
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Panel 3: Preview
        st.subheader("📄 Article Preview")
        st.markdown(st.session_state.article)
        
        if st.session_state.sources:
            with st.expander("📚 View Research Sources"):
                st.markdown(st.session_state.sources)
        
    with col2:
        # Panel 5: Export (Panel 4 SEO skipped)
        st.subheader("💾 Export Options")
        
        # Helper to get a good filename from topic or use default
        export_name = topic.strip() if topic else "article_draft"

        # PDF Download Button
        path_pdf = export_utils.export_to_pdf(st.session_state.article, filename=export_name)
        if path_pdf and os.path.exists(path_pdf):
            with open(path_pdf, "rb") as f:
                st.download_button("📄 Download PDF", data=f, file_name=os.path.basename(path_pdf), mime="application/pdf")
            
        # Docx Download Button
        path_docx = export_utils.export_to_docx(st.session_state.article, filename=export_name)
        if path_docx and os.path.exists(path_docx):
            with open(path_docx, "rb") as f:
                st.download_button("📝 Download Word Doc", data=f, file_name=os.path.basename(path_docx))
            
        # Panel 6: Narration
        st.divider()
        st.subheader("🎧 Audio Version")
        if st.button("Generate Audio"):
            with st.spinner("Talking..."):
                audio_path = narration.generate_audio(st.session_state.article, filename=export_name)
                if audio_path:
                    st.audio(audio_path)
