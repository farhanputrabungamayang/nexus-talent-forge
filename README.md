# 🚀 Nexus Talent-Forge: Next-Gen AI Applicant Tracking System (ATS)

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)

**Nexus Talent-Forge** is an end-to-end, AI-powered Applicant Tracking System (ATS) and Smart Interview Portal. Built to revolutionize the recruitment process, it leverages the power of **Google Gemini 1.5 Flash** to perform deep CV forensics, real-time interactive interviews (Text, Voice, and Code), and automated HR decision-making.

🔗 **Live Demo:** https://nexus-talent-forge-projects.streamlit.app/

---

## ✨ Key Features (The "Megazord" Capabilities)

### 👨‍💼 For HR & Recruiters (Admin Portal)
* **🤖 Multi-Agent AI CV Forensics:** Automatically extracts skills, evaluates candidates across 3 dimensions (HR, Tech, Biz), and calculates a **Trust Score** by detecting red flags/inconsistencies in the CV.
* **♻️ Smart Cross-Matching:** Intelligently analyzes rejected candidates and recommends them to other open positions that better fit their skills.
* **🖨️ Dual-PDF Auto Generator:** Generates an AI Candidate Dossier for HR meetings and automatically crafts/sends PDF Offering Letters to hired candidates.
* **📊 Interactive Analytics Dashboard:** Real-time visual insights using `Plotly` to track applicant distribution and quality per department.
* **📧 Automated Notifications:** Seamlessly integrated with SMTP Email and Telegram Bots to notify candidates and HR in real-time.

### 🗣️ For Candidates (Interview Portal)
* **📸 Vision AI Proctoring:** Anti-cheat mechanism requiring webcam verification before starting the interview.
* **🎙️ J.A.R.V.I.S Voice Mode:** Candidates can answer behavioral questions using their microphone. The AI transcribes the audio and analyzes their tone and confidence level.
* **👨‍💻 Live Coding Arena:** Dynamically generates technical logic/coding questions and automatically grades the candidate's code execution.
* **💬 Dynamic Chat Interview:** Simulates a conversational interview with HR based on the candidate's specific CV profile.

---

## 💻 Tech Stack
* **Frontend/Backend:** Streamlit (Python) with custom CSS Glassmorphism UI.
* **Generative AI:** Google Gemini 1.5 Flash (Multimodal: Text, Vision, Audio).
* **Database:** SQLite with SQLAlchemy ORM.
* **Data Visualization:** Plotly Express & Plotly Graph Objects.
* **Document Processing:** PyPDF2 (Reading CVs), FPDF (Generating Letters/Dossiers).
* **Communication:** `smtplib` (Email), `requests` (Telegram API).

---

## 🛠️ Installation & Setup Guide

Want to run this project locally? Follow these steps:

**1. Clone the repository**
```bash
git clone [https://github.com/farhanputrabungamayang/nexus-talent-forge.git](https://github.com/farhanputrabungamayang/nexus-talent-forge.git)
cd nexus-talent-forge

**2. Create a virtual environment (Optional but recommended)**

```Bash
python -m venv env
source env/bin/activate  # On Windows use: env\Scripts\activate

**3. Install dependencies**

```Bash
pip install -r requirements.txt

**4. Set up Environment Variables**
Create a .streamlit folder in the root directory and add a secrets.toml file:

```Ini, TOML
# .streamlit/secrets.toml
GOOGLE_API_KEY = "your_google_gemini_api_key_here"

# For Automated Emails (Use App Password for Gmail)
SMTP_EMAIL = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password_here"

# For Telegram Notifications (Optional)
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token"
TELEGRAM_CHAT_ID = "your_telegram_chat_id"

**5. Run the Application!**

Bash
streamlit run app.py

👨‍💻 Author
Farhan Putra