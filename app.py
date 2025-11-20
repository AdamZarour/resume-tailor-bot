import streamlit as st
import pdfplumber
import plotly.graph_objects as go
from fpdf import FPDF
import json
import re
from groq import Groq

# -------------------------------
# 1. PAGE CONFIGURATION
# -------------------------------
st.set_page_config(
    page_title="Resume Tailor Bot",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------
# 2. SECURE API CONNECTION
# -------------------------------
# This ensures the key is never exposed in the code.
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("⚠️ API Key not found! If running locally, add a .streamlit/secrets.toml file. If online, add to 'Secrets' in settings.")
    st.stop()

# -------------------------------
# 3. CSS STYLING
# -------------------------------
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1 {
        background: -webkit-linear-gradient(45deg, #FF4B4B, #FF9068);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    } 
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        border: 1px solid #333;
        transition: all 0.3s;
    }
    .stButton>button:hover { border-color: #FF4B4B; color: #FF4B4B; }
    .stSuccess { border-left: 5px solid #FF4B4B; }
    .keyword-chip {
        display: inline-block;
        padding: 4px 10px;
        margin: 3px;
        border-radius: 999px;
        background-color: #1f2933;
        color: #f5f5f5;
        border: 1px solid #FF4B4B33;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 4. HELPER FUNCTIONS
# -------------------------------
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def ask_llama(prompt):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"

# -------------------------------
# 5. ANALYTICS FUNCTIONS
# -------------------------------
STOPWORDS = {
    "the","a","an","and","or","to","of","in","on","for","with","at","by","is",
    "are","was","were","be","this","that","as","it","from","will","you","your",
    "our","we","they","them","their","i","me","my"
}

def tokenize(text):
    words = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
    return [w for w in words if w not in STOPWORDS]

def analyze_match(resume_text, job_text):
    jd_tokens = set(tokenize(job_text))
    res_tokens = set(tokenize(resume_text))

    if not jd_tokens:
        return 0, [], [], {}

    overlap = jd_tokens.intersection(res_tokens)
    missing = jd_tokens.difference(res_tokens)
    
    # Simple Score
    match_score = int(round(len(overlap) / len(jd_tokens) * 100))
    
    # Frequency
    freq_job = {}
    for w in tokenize(job_text):
        freq_job[w] = freq_job.get(w, 0) + 1

    top_job_keywords = sorted(freq_job.items(), key=lambda x: x[1], reverse=True)[:10]
    return match_score, sorted(list(overlap)), sorted(list(missing)), dict(top_job_keywords)

def build_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=11)
    # Encoding hack for simple PDFs
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_text)
    return bytes(pdf.output(dest='S').encode('latin-1'))

# -------------------------------
# 6. SIDEBAR
# -------------------------------
with st.sidebar:
    st.title("Adam's Resume Bot")
    st.write("Upload your resume and see how well it matches the job description.")
    st.divider()
    st.success("🟢 **System Ready**")
    st.markdown("---")
    st.markdown("**Created by Adam Zarour**")
    st.markdown("[Connect on LinkedIn](https://www.linkedin.com/in/adam-zarour)")

# -------------------------------
# 7. MAIN INTERFACE
# -------------------------------
st.title("🚀 Resume Tailor Bot")
st.markdown("### Optimize your application in seconds.")

col1, col2 = st.columns(2)
resume_text = ""

with col1:
    with st.container(border=True):
        st.subheader("📄 Your Resume")
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded_file:
            with st.spinner("Extracting text..."):
                resume_text = extract_text_from_pdf(uploaded_file)
                st.success("PDF Loaded Successfully!")
        else:
            resume_text = st.text_area("Or paste text:", height=200)

with col2:
    with st.container(border=True):
        st.subheader("💼 Job Description")
        job_input = st.text_area("Paste Job Description:", height=320)

st.divider()
b1, b2, b3 = st.columns(3)

with b1:
    analyze_btn = st.button("📊 Analyze Match Score")
with b2:
    optimize_btn = st.button("✨ Rewrite Bullet Points")
with b3:
    full_resume_btn = st.button("📝 Generate Full Tailored Resume")

# Initialize session state
if "analysis" not in st.session_state: st.session_state["analysis"] = None
if "improved_bullets" not in st.session_state: st.session_state["improved_bullets"] = None
if "tailored_resume" not in st.session_state: st.session_state["tailored_resume"] = None

# -------------------------------
# 8. LOGIC
# -------------------------------
if analyze_btn and resume_text and job_input:
    match_score, overlap, missing, top_job_keywords = analyze_match(resume_text, job_input)
    st.session_state["analysis"] = {
        "match_score": match_score, "overlap": overlap, 
        "missing": missing, "top_job_keywords": top_job_keywords
    }
    
    st.subheader("📊 Match Analysis")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=match_score, title={'text': "ATS Match Score"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#FF4B4B"},
               'steps': [{'range': [0, 50], 'color': "#333"}, {'range': [50, 100], 'color': "#333"}]}
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("#### 🔑 Top Job Keywords")
    st.markdown("".join([f"<span class='keyword-chip'>{k}</span>" for k in top_job_keywords.keys()]), unsafe_allow_html=True)
    
    st.markdown("#### ⚠️ Missing Keywords")
    if missing:
        st.markdown("".join([f"<span class='keyword-chip'>{k}</span>" for k in missing[:15]]), unsafe_allow_html=True)
    else:
        st.write("Good match!")

if optimize_btn and resume_text:
    with st.spinner("AI is rewriting..."):
        prompt = f"Rewrite these resume bullets to be impactful using action verbs:\n{resume_text[:2000]}"
        result = ask_llama(prompt)
        st.session_state["improved_bullets"] = result
        st.subheader("🔧 Improved Bullet Points")
        st.write(result)

if full_resume_btn and resume_text and job_input:
    with st.spinner("Generating tailored resume..."):
        prompt = f"Rewrite this resume to match the job description perfectly:\nRESUME: {resume_text[:3000]}\nJOB: {job_input[:2000]}"
        result = ask_llama(prompt)
        st.session_state["tailored_resume"] = result
        st.subheader("📝 Full Tailored Resume")
        st.write(result)
        
        pdf_bytes = build_pdf(result)
        st.download_button("📄 Download PDF", data=pdf_bytes, file_name="tailored_resume.pdf", mime="application/pdf")