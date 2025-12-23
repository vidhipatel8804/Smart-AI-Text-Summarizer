import streamlit as st
from PyPDF2 import PdfReader
import docx
import google.generativeai as genai
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import base64
import math

# Configure Gemini API Key
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")

# Text extraction
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    return "\n\n".join([p.extract_text().rstrip() for p in reader.pages if p.extract_text()]).strip()

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n\n".join([p.text.rstrip() for p in doc.paragraphs if p.text]).strip()

def extract_text_from_txt(file):
    raw = file.read()
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="ignore")
    return str(raw)

# Summary Instructions
summary_instructions = {
    "Short (1-2 sentences)": "Write a very concise summary in 1-2 sentences, capturing only the main idea.",
    "Medium": "Write a clear and coherent summary in a short paragraph, highlighting the key points.",
    "Detailed": "Write a detailed summary in multiple paragraphs, covering all important information with clear structure."
}

# Summarization
def summarize_text(text, length):
    # Base propmt for summarization
    prompt = f"""
    You are an expert text summarizer. {summary_instructions[length]}

    Original Text:
    {text}

    Provide the summary in clear, grammatically correct language. Maintain key details, context, and logical flow. Do not include unrelated information or filler.
    """
    response = model.generate_content(prompt)
    return getattr(response, "text", str(response))

# PDF Creation
def create_pdf_bytes(summary_text):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    left_margin = 40
    right_margin = 40
    usable_width = width - left_margin - right_margin
    y = height - 60
    pdf.setFont("Times-Roman", 12)
    words = summary_text.split()
    line = ""
    for word in words:
        test_line = line + " " + word if line else word
        if pdf.stringWidth(test_line, "Times-Roman", 12) <= usable_width:
            line = test_line
        else:
            pdf.drawString(left_margin, y, line)
            y -= 18
            line = word
            if y < 60:
                pdf.showPage()
                pdf.setFont("Times-Roman", 12)
                y = height - 60
    if line:
        pdf.drawString(left_margin, y, line)
    pdf.save()
    buffer.seek(0)
    return buffer.read()

# Streamlit App
st.set_page_config(page_title="Smart AI Text Summarizer", layout="wide", page_icon="📝")

st.markdown("""
<style>
.stApp {background: linear-gradient(180deg,#e0f7fa 0%,#ffffff 100%); font-family: 'Segoe UI', Roboto, Arial, sans-serif;}
.header {background: linear-gradient(90deg,#0ea5a9 0%, #2b6ffb 100%); color:white; border-radius:14px; padding:28px; text-align:center;}
.card {background:white; border-radius:12px; padding:18px; box-shadow:0 6px 20px rgba(16,24,40,0.04); margin-bottom:18px;}
.btn {background: linear-gradient(90deg,#06b6d4,#3b82f6); color:white; padding:8px 16px; border-radius:10px; border:none; cursor:pointer; font-weight:600; transition: all 0.2s ease;}
.btn:hover {opacity:0.85;}
.secondary {background:white; border:1px solid #e6eefb; color:#0f172a;}
.flex-center {display:flex; justify-content:center; gap:15px; margin-bottom:15px;}
.toast {position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); background: #323232; color: white; padding: 10px 20px; border-radius: 8px; opacity: 0; transition: opacity 0.3s ease;}
.toast.show {opacity: 1;}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header">
<h1 style="margin:0; font-size:28px;">Smart AI Text Summarizer</h1>
<p style="margin:6px 0 0 0; opacity:0.95;">Upload a document or paste text below to get a clean, concise summary while preserving formatting.</p>
</div>
""", unsafe_allow_html=True)

# Session State Initialization
if "input_mode" not in st.session_state:
    st.session_state.input_mode = None
if "summary_text" not in st.session_state:
    st.session_state.summary_text = ""
if "text_content" not in st.session_state:
    st.session_state.text_content = ""

# Input Mode Selection
st.markdown('<div class="flex-center">', unsafe_allow_html=True)
col1, col2 = st.columns([1,1])
with col1:
    if st.button("📄 Upload a File", key="btn_upload"):
        if st.session_state.input_mode != "upload":
            st.session_state.summary_text = ""
            st.session_state.text_content = ""
        st.session_state.input_mode = "upload"
with col2:
    if st.button("Enter Text Manually", key="btn_text"):
        if st.session_state.input_mode != "manual":
            st.session_state.summary_text = ""
            st.session_state.text_content = ""
        st.session_state.input_mode = "manual"
st.markdown('</div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Input Area
if st.session_state.input_mode == "upload":
    uploaded_file = st.file_uploader("Choose file", type=["pdf","docx","txt"], label_visibility="visible")
    if uploaded_file:
        ext = uploaded_file.name.split(".")[-1].lower()
        try:
            if ext == "pdf":
                st.session_state.text_content = extract_text_from_pdf(uploaded_file)
            elif ext == "docx":
                st.session_state.text_content = extract_text_from_docx(uploaded_file)
            elif ext == "txt":
                st.session_state.text_content = extract_text_from_txt(uploaded_file)
        except:
            st.error("Failed to read the file")

elif st.session_state.input_mode == "manual":
    st.session_state.text_content = st.text_area("Paste text here:", height=260)

# Summarization and Output
if st.session_state.text_content:
    text_content = st.session_state.text_content
    length = st.selectbox("Summary Length", ["Short (1-2 sentences)", "Medium", "Detailed"], index=1)
    
    if st.button("✨ Generate Summary"):
        summary_text = summarize_text(text_content, length)
        st.text_area("Summary:", value=summary_text, height=260, key="summary")

        # Copy button using base64
        summary_b64 = base64.b64encode(summary_text.encode("utf-8")).decode("utf-8")
        
        # Combine Copy and Download buttons in single row
        copy_download_html = f"""
        <div style="display:flex; justify-content:center; gap:12px; margin-top:10px;">
            <button onclick="
                const text=atob('{summary_b64}');
                navigator.clipboard.writeText(text)
                .then(()=>{{alert('Summary copied to clipboard!')}})
                .catch(err=>{{alert('Copy failed: '+err)}});
            " 
            style="padding:8px 16px; font-size:16px; border-radius:8px; background:#3b82f6; color:white; border:none; cursor:pointer;">
            📋 Copy Summary
            </button>
            <form method='GET'>
                <a download='summary.pdf' href='data:application/pdf;base64,{base64.b64encode(create_pdf_bytes(summary_text)).decode()}'>
                    <button type='button' style='padding:8px 16px; font-size:16px; border-radius:8px; background:#06b6d4; color:white; border:none; cursor:pointer;'>
                    ⬇️ Download PDF
                    </button>
                </a>
            </form>
        </div>
        """

        st.components.v1.html(copy_download_html, height=70)
