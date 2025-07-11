import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import smtplib
from email.message import EmailMessage

# PAGE CONFIG
st.set_page_config(page_title="ERNEST DUNG EMR SYSTEM", layout="centered")
st.title("🩺 ERNEST DUNG ELECTRONIC MEDICAL RECORD SYSTEM")
st.subheader("🔐 Secure Login Page")

# Google Sheet Setup
SHEET_NAME = "Unauthorized_Login_Attempts"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# Email Setup
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"
EMAIL_RECEIVER = "receiver_email@gmail.com"

def send_email_alert(username, attempt_time):
    msg = EmailMessage()
    msg["Subject"] = "🚨 FRAUD ALERT: Unauthorized Access Attempt"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content(f"""
    Unauthorized login attempt detected on ERNEST DUNG EMR SYSTEM.
    
    Username: {username}
    Time: {attempt_time}
    """)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

def log_to_google_sheet(username, attempt_time):
    sheet.append_row([username, attempt_time, "Unauthorized Login Attempt"])

# Hardcoded login credentials
USERNAME = "admin"
PASSWORD = "admin123"

# Track login attempts
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "fraud_alert" not in st.session_state:
    st.session_state.fraud_alert = False

# Login Form
with st.form("login_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")

    if submitted:
        if username == USERNAME and password == PASSWORD:
            st.success("✅ Login successful. Welcome to the EMR System!")
            st.session_state.attempts = 0  # Reset attempts
        else:
            st.session_state.attempts += 1
            st.error(f"❌ Invalid credentials. Attempt {st.session_state.attempts}/3")

            if st.session_state.attempts >= 3:
                st.session_state.fraud_alert = True
                attempt_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_to_google_sheet(username, attempt_time)
                send_email_alert(username, attempt_time)

# Fraud Alert Message
if st.session_state.fraud_alert:
    st.markdown("<h3 style='color:red;'>🚨 FRAUD ALERT DETECTED! Unauthorized login attempts exceeded limit.</h3>", unsafe_allow_html=True)
