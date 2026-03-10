import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import PyPDF2
import google.generativeai as genai
import os, re, smtplib, requests, time, json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from io import BytesIO
from fpdf import FPDF
from PIL import Image

# ==========================================
# 1. KONFIGURASI HALAMAN UTAMA
# ==========================================
st.set_page_config(page_title="Nexus Talent-Forge V9", page_icon="🌌", layout="wide", initial_sidebar_state="expanded")
CHART_THEME = "plotly_white"
st.markdown("""
    <style>
        /* Import Font Google Kelas Atas */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
        
        /* Sembunyikan Logo & Menu Streamlit Biar Kelihatan Aplikasi Mandiri (SaaS) */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Styling Judul Utama Gradient Mahal */
        .main-title { 
            background: linear-gradient(135deg, #0F172A 0%, #3B82F6 100%); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent; 
            font-weight: 800; 
            font-size: 3.5rem; 
            text-align: center; 
            margin-bottom: 5px; 
            letter-spacing: -1.5px;
        }
        
        /* Styling Container / Card ala Apple & Vercel */
        div[data-testid="stVerticalBlockBorderWrapper"] { 
            border-radius: 20px !important; 
            border: 1px solid rgba(226, 232, 240, 0.8) !important; 
            background: rgba(255, 255, 255, 0.7) !important; 
            backdrop-filter: blur(10px) !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01) !important; 
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important; 
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover { 
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important; 
            transform: translateY(-5px) !important; 
        }
        
        /* Tombol Premium 3D Effect */
        div.stButton > button:first-child {
            background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
            color: white;
            border-radius: 12px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 600;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.4);
            transition: all 0.3s ease;
        }
        div.stButton > button:first-child:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.5);
        }
        
        /* Styling Metrik (Angka Dashboard) */
        div[data-testid="stMetricValue"] {
            font-size: 2.5rem !important;
            font-weight: 800 !important;
            color: #0F172A !important;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. KONFIGURASI AI (RADAR PINTAR)
# ==========================================
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model_hidup = None
    
    # AI nyari sendiri model apa yang aktif di laptop sampeyan
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            if '1.5-flash' in m.name: # Prioritaskan versi 1.5 biar bisa Audio J.A.R.V.I.S
                model_hidup = m.name
                break
            elif not model_hidup: 
                model_hidup = m.name # Kalau nggak ada, pakai versi apa aja yang penting hidup wkwk
                
    ai_model = genai.GenerativeModel(model_hidup) if model_hidup else None
else:
    ai_model = None

# ==========================================
# 3. DATABASE SETUP (V9)
# ==========================================
Base = declarative_base()
engine = create_engine('sqlite:///nexus_talent.db', connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
session = Session()

class JobPosting(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    department = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default="Open")
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d"))
    candidates = relationship('Candidate', backref='job', cascade="all, delete-orphan")

class Candidate(Base):
    __tablename__ = 'candidates'
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    name = Column(String(100), nullable=False); email = Column(String(100), nullable=True); phone = Column(String(50), nullable=True)
    
    score_hr = Column(Float, default=0.0); score_tech = Column(Float, default=0.0); score_biz = Column(Float, default=0.0)
    match_score = Column(Float, default=0.0); trust_score = Column(Float, default=100.0)
    
    proctor_result = Column(Text, nullable=True); offered_salary = Column(String(100), nullable=True)
    red_flags = Column(Text, nullable=True); skill_matrix = Column(String(200), nullable=True) 
    ai_summary = Column(Text, nullable=True); missing_skills = Column(Text, nullable=True)
    onboarding_roadmap = Column(Text, nullable=True); cv_filename = Column(String(200), nullable=False)
    status = Column(String(50), default="Screening") 
    
    interview_questions = Column(Text, nullable=True); interview_chat_log = Column(Text, nullable=True)
    interview_final_score = Column(Float, nullable=True); voice_analysis_log = Column(Text, nullable=True)
    coding_question = Column(Text, nullable=True); coding_answer = Column(Text, nullable=True); coding_score = Column(Float, nullable=True)

Base.metadata.create_all(engine)

# ==========================================
# 4. FUNGSI DEWA (AI, VISION, PDF, MATCHING, EMAIL, TELEGRAM)
# ==========================================
def extract_text_from_pdf(pdf_file):
    try:
        reader = PyPDF2.PdfReader(pdf_file); text = ""
        for page in reader.pages: text += page.extract_text() + "\n" if page.extract_text() else ""
        return text[:15000] 
    except: return ""

def send_telegram_blast(message):
    if "TELEGRAM_BOT_TOKEN" in st.secrets and "TELEGRAM_CHAT_ID" in st.secrets:
        try:
            url = f"https://api.telegram.org/bot{st.secrets['TELEGRAM_BOT_TOKEN']}/sendMessage"
            requests.post(url, data={'chat_id': st.secrets['TELEGRAM_CHAT_ID'], 'text': message})
        except: pass

def analyze_cv_with_multi_agent(cv_text, job_desc):
    import json
    if not ai_model: return None
    prompt = f"""
    Evaluasi CV secara brutal.
    --- LOWONGAN ---
    {job_desc}
    --- CV PELAMAR ---
    {cv_text}
    
    KEMBALIKAN OUTPUT HANYA DALAM FORMAT JSON VALID SEPERTI INI (TANPA MARKDOWN/BACKTICKS):
    {{
        "score_hr": 80,
        "score_tech": 85,
        "score_biz": 70,
        "trust_score": 90,
        "name": "Nama Lengkap",
        "email": "email@domain.com",
        "phone": "0812345678",
        "summary": "Kesimpulan 3 kalimat.",
        "skills": "Python:80, SQL:90, AWS:70",
        "gap": "Kekurangan terbesar",
        "roadmap": "3 poin training",
        "red_flags": "Aman"
    }}
    """
    
    res = "Tidak ada balasan (API putus / Error sebelum merespon)." # 👈 PENYELAMAT NYA DI SINI
    
    try:
        res = ai_model.generate_content(prompt).text.strip()
        res = res.replace("```json", "").replace("```", "").strip()
        data = json.loads(res)
        
        s_hr = float(data.get("score_hr", 0))
        s_tech = float(data.get("score_tech", 0))
        s_biz = float(data.get("score_biz", 0))
        
        return {
            "score_hr": s_hr, "score_tech": s_tech, "score_biz": s_biz, 
            "score": round((s_hr + s_tech + s_biz) / 3, 1),
            "trust_score": float(data.get("trust_score", 100)),
            "name": data.get("name", "Unknown"),
            "email": data.get("email", "-"),
            "phone": data.get("phone", "-"),
            "summary": data.get("summary", "-"),
            "skills": data.get("skills", "General:50"),
            "gap": data.get("gap", "-"),
            "roadmap": data.get("roadmap", "-"),
            "red_flags": data.get("red_flags", "Aman")
        }
    except Exception as e: 
        st.error(f"🚨 DEBUG ERROR GEMINI: {e}\n\nBalasan AI: {res}")
        return None

def analyze_proctor_image(image_bytes):
    if not ai_model: return "AI Offline"
    try:
        img = Image.open(image_bytes)
        return ai_model.generate_content(["Kamu Pengawas Ujian HRD. 1. Sendirian? 2. Wajah jelas? 3. Fokus? Beri laporan 2 kalimat, awali [AMAN] atau [MENCURIGAKAN].", img]).text
    except Exception as e: return f"Gagal menganalisis foto: {e}"

def cross_match_candidate(cand_summary, current_job_id):
    other_jobs = session.query(JobPosting).filter(JobPosting.id != current_job_id, JobPosting.status == "Open").all()
    if not other_jobs: return None
    jobs_str = "\n".join([f"ID: {j.id} | Posisi: {j.title} | Desc: {j.description[:100]}" for j in other_jobs])
    prompt = f"Profil: {cand_summary}\n\nLowongan Lain:\n{jobs_str}\n\nApakah kandidat LEBIH COCOK di lowongan lain? Jika YA balas HANYA angka ID nya. Jika TIDAK balas NONE."
    try:
        res = ai_model.generate_content(prompt).text.strip()
        if res != "NONE" and res.isdigit(): return int(res)
    except: pass
    return None

def estimate_salary(job_title, skills):
    if not ai_model: return "Rp 8.000.000"
    try: return ai_model.generate_content(f"Estimasi gaji sebulan dalam Rupiah (Hanya angka, misal Rp 10.000.000) untuk posisi {job_title} dengan skill {skills}.").text.strip()
    except: return "Rp 8.000.000"

# FUNGSI PEMBERSIH UNICODE (ANTI ERROR PDF)
def clean_text(text):
    if not text: return "-"
    text = str(text)
    # Ubah karakter cantik Gemini jadi karakter mesin tik biasa
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '-', '\u2026': '...'
    }
    for k, v in replacements.items(): text = text.replace(k, v)
    # Paksa buang karakter aneh lainnya biar FPDF nggak ngambek
    return text.encode('latin-1', 'ignore').decode('latin-1') 

def create_offering_pdf(name, job_title, salary):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="NEXUS CORP - OFFERING LETTER", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", '', 12)
    body = f"Tanggal: {datetime.now().strftime('%d %B %Y')}\n\nKepada Yth,\nBapak/Ibu {name},\n\nSelamat! Kami dari Nexus Corp dengan bangga menawarkan posisi sebagai {job_title} kepada Anda.\n\nBerdasarkan evaluasi AI, kami menawarkan kompensasi awal sebesar:\n\nGAJI POKOK: {salary} / Bulan\n\nSilakan balas email ini untuk menyetujui penawaran kerja ini.\n\nHormat Kami,\n\nTim HRD Nexus Corp"
    pdf.multi_cell(0, 8, txt=clean_text(body))
    return pdf.output(dest='S').encode('latin-1')

def create_dossier_pdf(cand_data):
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(200, 10, txt=clean_text(f"AI CANDIDATE DOSSIER - {cand_data.name}"), ln=True, align='C')
    pdf.ln(5); pdf.set_font("Arial", 'B', 12); pdf.cell(200, 8, txt=clean_text(f"Posisi: {cand_data.job.title}"), ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 8, txt=clean_text(f"Email: {cand_data.email} | Phone: {cand_data.phone}"), ln=True); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 8, txt="1. AI Scoring Metrics", ln=True); pdf.set_font("Arial", '', 11)
    pdf.cell(200, 8, txt=f"Overall Match Score: {cand_data.match_score}%", ln=True)
    pdf.cell(200, 8, txt=f"HR Score: {cand_data.score_hr}% | Tech Score: {cand_data.score_tech}% | Biz Score: {cand_data.score_biz}%", ln=True)
    pdf.cell(200, 8, txt=f"Trust Score (Kejujuran CV): {cand_data.trust_score}%", ln=True); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 8, txt="2. Profiling Summary", ln=True); pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 6, txt=clean_text(f"Kesimpulan AI:\n{cand_data.ai_summary}")); pdf.ln(3)
    pdf.multi_cell(0, 6, txt=clean_text(f"Red Flags / Kebohongan:\n{cand_data.red_flags}")); pdf.ln(3)
    pdf.multi_cell(0, 6, txt=clean_text(f"Kelemahan (Skill Gap):\n{cand_data.missing_skills}")); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 8, txt="3. Interview & Test Results", ln=True); pdf.set_font("Arial", '', 11)
    pdf.cell(200, 8, txt=clean_text(f"Interview Score: {cand_data.interview_final_score}%" if cand_data.interview_final_score else "Interview Score: Belum Tes"), ln=True)
    pdf.cell(200, 8, txt=clean_text(f"Coding Score: {cand_data.coding_score}%" if cand_data.coding_score else "Coding Score: Belum Tes"), ln=True)
    return pdf.output(dest='S').encode('latin-1')

def generate_and_send_email(email_to, name, job_title, status, extra_info=None):
    if "SMTP_EMAIL" not in st.secrets: return False
    try:
        msg = MIMEMultipart(); msg['From'] = st.secrets["SMTP_EMAIL"]; msg['To'] = email_to
        if status == "Invited":
            msg['Subject'] = f"🚀 Undangan Interview Wajib - {job_title}"
            msg.attach(MIMEText(f"Halo {name},\n\nAnda diundang mengikuti Live AI Interview & Coding Test untuk {job_title}. Siapkan WEBCAM dan MIC Anda.\n\nHRD Nexus", 'plain'))
            send_telegram_blast(f"🔔 [NOTIFIKASI HRD]\nUndangan Wawancara terkirim ke {name} ({job_title}).")
        elif status == "Rejected":
            msg['Subject'] = f"Update Status Lamaran - {job_title}"
            msg.attach(MIMEText(ai_model.generate_content(f"Buat email penolakan ramah untuk {name} posisi {job_title}. Alasan: {extra_info}.").text, 'plain'))
            send_telegram_blast(f"🚫 [NOTIFIKASI HRD]\n{name} telah ditolak untuk posisi {job_title}.")
        elif status == "Cross_Matched":
            msg['Subject'] = f"♻️ Peluang Baru - {extra_info} di Nexus Corp"
            msg.attach(MIMEText(f"Halo {name},\n\nAnda belum lolos untuk {job_title}. TAPI, AI memindahkan profil Anda ke posisi {extra_info} karena lebih cocok!\n\nHRD Nexus", 'plain'))
            send_telegram_blast(f"♻️ [NOTIFIKASI HRD]\n{name} didaur ulang dari {job_title} ke {extra_info}.")
        elif status == "Offered":
            msg['Subject'] = f"🎉 OFFERING LETTER - {job_title} di Nexus Corp"
            msg.attach(MIMEText(f"Halo {name},\n\nSELAMAT! Anda diterima. Terlampir Surat Penawaran Kerja (Offering Letter) resmi Anda.\n\nHRD Nexus", 'plain'))
            part = MIMEApplication(extra_info, Name="Offering_Letter.pdf"); part['Content-Disposition'] = f'attachment; filename="Offering_Letter_Nexus.pdf"'; msg.attach(part)
            send_telegram_blast(f"🎉 [KABAR GEMBIRA]\nOffering Letter telah dikirim ke {name} ({job_title})!")
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(st.secrets["SMTP_EMAIL"], st.secrets["SMTP_PASSWORD"]); server.send_message(msg); server.quit()
        return True
    except: return False

def plot_radar_chart(skills_str):
    try:
        skills = []; scores = []
        for item in skills_str.split(','):
            if ':' in item:
                k, v = item.split(':'); skills.append(k.strip()[:15]); scores.append(int(re.search(r'\d+', v).group()))
        skills.append(skills[0]); scores.append(scores[0])
        fig = go.Figure(data=go.Scatterpolar(r=scores, theta=skills, fill='toself', line_color='#3B82F6', fillcolor='rgba(59, 130, 246, 0.3)'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        return fig
    except: return None

# ==========================================
# 5. GERBANG APLIKASI UTAMA
# ==========================================
app_mode = st.sidebar.radio("Pilih Portal:", ["👨‍💼 Portal Admin HRD", "🗣️ Portal Wawancara Kandidat"])
st.sidebar.markdown("---")

if app_mode == "👨‍💼 Portal Admin HRD":
    menu = st.sidebar.radio("Navigasi HRD", ["📊 Dashboard ATS", "📝 Kelola Lowongan", "🔍 Smart CV Screening"])

    if menu == "📝 Kelola Lowongan":
        st.markdown("<h1 class='main-title'>📝 Kelola Lowongan Pekerjaan</h1><br>", unsafe_allow_html=True)
        with st.form("job_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1: title = st.text_input("Posisi Pekerjaan")
            with col2: dept = st.selectbox("Departemen", ["IT", "Data", "Marketing", "Finance", "HR"])
            desc = st.text_area("Job Description & Requirements", height=150)
            if st.form_submit_button("💾 Buka Lowongan", type="primary"):
                if title and desc: 
                    session.add(JobPosting(title=title, department=dept, description=desc)); session.commit(); st.success("✅ Lowongan dibuka!"); st.rerun()
                else: st.error("Lengkapi form!")
        jobs = session.query(JobPosting).order_by(JobPosting.id.desc()).all()
        if jobs: st.dataframe(pd.DataFrame([{"ID": j.id, "Posisi": j.title, "Dept": j.department, "Dibuat": j.created_at} for j in jobs]), use_container_width=True)

    elif menu == "🔍 Smart CV Screening":
        st.markdown("<h1 class='main-title'>🤖 Board of Directors AI Screening</h1>", unsafe_allow_html=True)
        jobs = session.query(JobPosting).filter_by(status="Open").all()
        if not jobs: 
            st.warning("⚠️ Buka lowongan terlebih dahulu.")
        else:
            selected_job_name = st.selectbox("📌 Pilih Lowongan:", [f"{j.title} ({j.department})" for j in jobs])
            selected_job = next(j for j in jobs if f"{j.title} ({j.department})" == selected_job_name)
            
            uploaded_cvs = st.file_uploader("📥 Upload CV (PDF) - Bisa banyak sekaligus", type=['pdf'], accept_multiple_files=True)
            
            # FITUR ANTI-FREEZE & RADAR ERROR DENGAN JSON
            if st.button("🚀 Eksekusi Sidang AI", type="primary", use_container_width=True):
                if uploaded_cvs:
                    status_text = st.empty()
                    progress_bar = st.progress(0)
                    success_count = 0
                    
                    for i, cv_file in enumerate(uploaded_cvs):
                        status_text.info(f"⏳ Sedang menyidang CV {i+1} dari {len(uploaded_cvs)}:\n**{cv_file.name}**\n*(AI sedang mikir keras...)*")
                        time.sleep(0.1) 
                        
                        cv_text = extract_text_from_pdf(cv_file)
                        if len(cv_text) < 50:
                            st.error(f"❌ GAGAL: Teks di CV '{cv_file.name}' kosong atau berupa gambar!")
                            continue
                            
                        ai_result = analyze_cv_with_multi_agent(cv_text, selected_job.description)
                        if ai_result is None:
                            st.error(f"❌ GAGAL: AI bingung membaca format CV '{cv_file.name}'!")
                            continue
                            
                        session.add(Candidate(
                            job_id=selected_job.id, name=ai_result['name'], email=ai_result['email'], phone=ai_result['phone'], 
                            score_hr=ai_result['score_hr'], score_tech=ai_result['score_tech'], score_biz=ai_result['score_biz'],
                            match_score=ai_result['score'], trust_score=ai_result['trust_score'], red_flags=ai_result['red_flags'],
                            ai_summary=ai_result['summary'], skill_matrix=ai_result['skills'], missing_skills=ai_result['gap'], 
                            onboarding_roadmap=ai_result['roadmap'], cv_filename=cv_file.name
                        )); session.commit()
                        success_count += 1
                        
                        progress_bar.progress((i + 1) / len(uploaded_cvs))
                            
                    if success_count > 0:
                        status_text.success(f"✅ Selesai! Berhasil menyimpan {success_count} dari {len(uploaded_cvs)} CV.")
                        time.sleep(1.5) 
                        st.rerun()
                    else:
                        status_text.error("❌ Semua CV gagal diproses. Cek pesan error di atas!")

            candidates = session.query(Candidate).filter_by(job_id=selected_job.id).order_by(Candidate.match_score.desc()).all()
            if candidates:
                st.markdown("---")
                col_l1, col_l2 = st.columns([3, 1])
                with col_l1: st.markdown("### 🏆 Leaderboard Elite")
                with col_l2: blind_mode = st.toggle("🙈 Blind Recruitment")

                df_cands = pd.DataFrame([{
                    "Nama": f"Kandidat Anonim #{c.id}" if blind_mode else c.name, 
                    "Skor AI": f"{c.match_score}%", "🕵️ Trust": f"{c.trust_score}%", 
                    "Status": c.status, "Wawancara": f"{c.interview_final_score}%" if c.interview_final_score else "-",
                    "Koding": f"{c.coding_score}%" if c.coding_score else "-"
                } for c in candidates])
                st.dataframe(df_cands, use_container_width=True, hide_index=True)
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer: df_cands.to_excel(writer, index=False, sheet_name='Data_Pelamar')
                st.download_button(label="⬇️ Download Data ke Excel", data=output.getvalue(), file_name=f"Pelamar_{selected_job.title}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
                st.markdown("#### 🕵️‍♂️ Deep Profiling & Eksekusi")
                c_det = next(c for c in candidates if (f"Kandidat Anonim #{c.id}" if blind_mode else c.name) == st.selectbox("Pilih Pelamar:", [f"Kandidat Anonim #{c.id}" if blind_mode else c.name for c in candidates]))
                
                tab1, tab2, tab3 = st.tabs(["🕸️ Profil & Forensik", "📸 Hasil Wawancara & Koding", "🎯 Eksekusi AI"])
                
                with tab1:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Skor Keseluruhan", f"{c_det.match_score}%"); st.metric("🕵️ Kejujuran CV", f"{c_det.trust_score}%")
                        if c_det.trust_score < 80: st.error(f"🚩 RED FLAGS:\n{c_det.red_flags}")
                        st.warning(f"**Kekurangan (Gap):**\n{c_det.missing_skills}")
                        dossier_pdf = create_dossier_pdf(c_det)
                        st.download_button(label="⬇️ Download AI Dossier (PDF Print)", data=dossier_pdf, file_name=f"Dossier_{c_det.name}.pdf", mime="application/pdf")
                    with c2:
                        fig = plot_radar_chart(c_det.skill_matrix)
                        if fig: st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    if c_det.status in ["Interview Completed", "Hired"]:
                        col_sc1, col_sc2 = st.columns(2)
                        col_sc1.metric("📝 Skor Wawancara Teks", f"{c_det.interview_final_score}%"); col_sc2.metric("💻 Skor Logic / Coding", f"{c_det.coding_score}%")
                        st.info(f"**📸 Laporan Kamera Pengawas:**\n{c_det.proctor_result}")
                        with st.expander("🎙️ Log Analisis Suara (J.A.R.V.I.S)"): st.write(c_det.voice_analysis_log)
                        with st.expander("💻 Log Jawaban Koding/Logika"): st.write(f"**Soal:**\n{c_det.coding_question}\n\n**Jawaban:**\n{c_det.coding_answer}")
                        with st.expander("💬 Baca Log Chat Wawancara"): st.write(c_det.interview_chat_log)
                    else: st.warning("Kandidat belum menyelesaikan sesi wawancara & koding di Portal Kandidat.")
                    
                with tab3:
                    if not c_det.interview_questions:
                        if st.button("🧠 Persiapkan Soal Wawancara & Koding", use_container_width=True):
                            with st.spinner("AI Meracik Soal..."):
                                c_det.interview_questions = ai_model.generate_content(f"Buat 3 soal interview singkat: Posisi {selected_job.description}, Profil {c_det.ai_summary}").text
                                c_det.coding_question = ai_model.generate_content(f"Buat 1 soal tes logika/koding untuk posisi: {selected_job.title}. Tulis soalnya saja tanpa jawaban.").text
                                session.commit(); st.rerun()
                            
                    col_act1, col_act2, col_act3 = st.columns(3)
                    with col_act1:
                        if st.button("📧 Undang Wawancara", type="primary", use_container_width=True) and c_det.status == "Screening":
                            with st.spinner("Mengirim email & Telegram..."):
                                if generate_and_send_email(c_det.email, c_det.name, selected_job.title, "Invited"): 
                                    c_det.status = "Interview Invited"; session.commit(); st.success("Terkirim!"); st.rerun()
                    with col_act2:
                        if st.button("♻️ Smart Reject", use_container_width=True) and c_det.status != "Rejected":
                            with st.spinner("AI mencari lowongan pengganti..."):
                                new_job_id = cross_match_candidate(c_det.ai_summary, selected_job.id)
                                if new_job_id:
                                    new_job = session.query(JobPosting).get(new_job_id)
                                    if generate_and_send_email(c_det.email, c_det.name, selected_job.title, "Cross_Matched", new_job.title):
                                        c_det.status = f"Cross-Matched ke ID {new_job.id}"; session.add(Candidate(job_id=new_job.id, name=c_det.name, email=c_det.email, phone=c_det.phone, cv_filename=c_det.cv_filename, match_score=c_det.match_score)); session.commit(); st.success(f"Didaur ulang ke {new_job.title}"); st.rerun()
                                else:
                                    generate_and_send_email(c_det.email, c_det.name, selected_job.title, "Rejected", c_det.missing_skills); c_det.status = "Rejected"; session.commit(); st.success("Ditolak Permanen."); st.rerun()
                    with col_act3:
                        if st.button("🎉 TERIMA & Kirim Offering", type="primary", use_container_width=True):
                            with st.spinner("AI membuat PDF Offering & Ngirim Email..."):
                                salary = estimate_salary(selected_job.title, c_det.skill_matrix)
                                pdf_bytes = create_offering_pdf(c_det.name, selected_job.title, salary)
                                if generate_and_send_email(c_det.email, c_det.name, selected_job.title, "Offered", pdf_bytes):
                                    c_det.status = "Hired"; c_det.offered_salary = salary; session.commit(); st.balloons(); st.success("Offering Sent!"); st.rerun()

    elif menu == "📊 Dashboard ATS":
        st.markdown("<h1 class='main-title'>📊 HR Recruitment Analytics</h1><br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 Total Lowongan", session.query(JobPosting).count())
        c2.metric("👥 Total Pelamar", session.query(Candidate).count())
        c3.metric("🎉 Karyawan Diterima", session.query(Candidate).filter_by(status="Hired").count())
        st.markdown("---")
        cands = session.query(Candidate).all()
        if cands:
            df = pd.DataFrame([{"Nama": c.name, "Skor": c.match_score, "Posisi": c.job.title} for c in cands])
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                with st.container(border=True):
                    df['Kategori'] = df['Skor'].apply(lambda s: "Elite (>80%)" if s >= 80 else ("Average (60-79%)" if s >= 60 else "Below Avg (<60%)"))
                    fig_pie = px.pie(df, names='Kategori', title="🗂️ Distribusi Kualitas Pelamar (AI Score)", color_discrete_sequence=px.colors.qualitative.Set2)
                    fig_pie.update_layout(margin=dict(t=30, b=0, l=0, r=0), template=CHART_THEME, paper_bgcolor='rgba(0,0,0,0)'); st.plotly_chart(fig_pie, use_container_width=True)
            with col_chart2:
                with st.container(border=True):
                    avg_df = df.groupby('Posisi')['Skor'].mean().reset_index()
                    fig_bar = px.bar(avg_df, x='Posisi', y='Skor', title="📈 Rata-rata Kualitas CV per Posisi", text_auto='.1f', color='Posisi')
                    fig_bar.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0), template=CHART_THEME, paper_bgcolor='rgba(0,0,0,0)'); st.plotly_chart(fig_bar, use_container_width=True)
        else: st.info("Silakan lakukan screening CV terlebih dahulu.")

# ---------------------------------------------------------
# B. PORTAL KANDIDAT
# ---------------------------------------------------------
elif app_mode == "🗣️ Portal Wawancara Kandidat":
    st.markdown("<h1 class='main-title'>🤖 Portal Wawancara AI</h1>", unsafe_allow_html=True)
    
    if "cand_id" not in st.session_state:
        st.info("Silakan masukkan email yang Anda gunakan di CV untuk memulai tes.")
        email_input = st.text_input("Email Anda:")
        if st.button("Masuk Portal", type="primary"):
            cand = session.query(Candidate).filter_by(email=email_input, status="Interview Invited").first()
            if cand: 
                st.session_state.cand_id = cand.id
                st.session_state.chat_history = [{"role": "assistant", "content": f"Halo {cand.name}. Berikut adalah pertanyaan dari HRD:\n\n{cand.interview_questions}"}]
                st.rerun()
            else: st.error("Email tidak ditemukan atau Anda belum menerima undangan wawancara.")
    else:
        cand = session.query(Candidate).get(st.session_state.cand_id)
        st.success(f"👤 Login Berhasil: **{cand.name}** | Melamar untuk: **{cand.job.title}**")
        st.markdown("---")
        
        if not cand.proctor_result:
            st.warning("⚠️ **KEAMANAN AKTIF:** Sesi diawasi AI Proctor. Ambil foto wajah verifikasi.")
            cam_photo = st.camera_input("📸 Ambil Foto Verifikasi")
            if cam_photo:
                with st.spinner("AI memverifikasi wajah Anda..."):
                    result = analyze_proctor_image(cam_photo)
                    cand.proctor_result = result; session.commit()
                    if "AMAN" in result.upper(): st.success("Lolos!"); st.rerun()
                    else: st.error("⚠️ Pelanggaran keamanan."); st.rerun()
        else:
            if "AMAN" in cand.proctor_result.upper(): st.success("✅ Verifikasi Wajah Lolos.")
            else: st.error("⚠️ Peringatan: Anomali wajah terdeteksi.")
            
            st.markdown("### 🎙️ Sesi 1: Wawancara Lisan (J.A.R.V.I.S Mode)")
            st.write("Rekam suara Anda:")
            audio_val = st.audio_input("Tekan Mic untuk Merekam")
            if audio_val and not cand.voice_analysis_log:
                with st.spinner("J.A.R.V.I.S menganalisis suara..."):
                    audio_bytes = audio_val.read()
                    try:
                        audio_res = ai_model.generate_content(["Transkrip dan analisis nada suara ini. Format: TRANSKRIP: [teks] | ANALISIS: [analisis]", {"mime_type": "audio/wav", "data": audio_bytes}]).text
                        cand.voice_analysis_log = audio_res; session.commit(); st.success("Suara dianalisis!"); st.info(audio_res)
                    except: st.error("Gagal memproses audio.")
            elif cand.voice_analysis_log: st.success("✅ Rekaman Tersimpan.")
            
            st.markdown("### 💬 Sesi 2: Wawancara Teks")
            chat_container = st.container(height=250)
            with chat_container:
                for msg in st.session_state.chat_history: st.chat_message(msg["role"]).markdown(msg["content"])
            if prompt := st.chat_input("Ketik jawaban di sini..."):
                st.session_state.chat_history.append({"role": "user", "content": prompt}); st.chat_message("user").markdown(prompt)
                ai_reply = "Jawaban dicatat. Lanjutkan ke Tes Logika."
                st.session_state.chat_history.append({"role": "assistant", "content": ai_reply}); st.chat_message("assistant").markdown(ai_reply)
            
            st.markdown("### 👨‍💻 Sesi 3: Live Logic & Coding Test")
            st.warning(f"**Soal Tes Anda:**\n{cand.coding_question}")
            code_input = st.text_area("Tulis jawaban / kodingan Anda di sini:", height=150)
            
            st.markdown("---")
            if st.button("🏁 Selesai & Kumpulkan Semua Ujian", type="primary", use_container_width=True):
                if code_input:
                    with st.spinner("Menilai hasil..."):
                        cand.interview_chat_log = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.chat_history])
                        cand.interview_final_score = float(re.search(r'\d+', ai_model.generate_content(f"Nilai 0-100 wawancara ini: {cand.interview_chat_log}").text).group() or 50)
                        cand.coding_answer = code_input
                        cand.coding_score = float(re.search(r'\d+', ai_model.generate_content(f"Nilai 0-100 logika ini.\nSoal: {cand.coding_question}\nJawaban: {code_input}\nHanya angka.").text).group() or 0)
                        cand.status = "Interview Completed"; session.commit()
                        send_telegram_blast(f"🚨 [NOTIFIKASI HRD]\nKandidat {cand.name} MENYELESAIKAN ujian!")
                        del st.session_state.cand_id; st.success("Semua Sesi Selesai! Hasil dikirim ke HRD."); st.rerun()
                else: st.error("⚠️ Jawaban tes wajib diisi!")