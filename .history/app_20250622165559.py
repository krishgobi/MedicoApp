from flask import Flask, render_template, redirect, url_for, request, session, jsonify, flash,json
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.start()
from twilio.rest import Client
from flask import Response
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz
import requests
import random
from flask_migrate import Migrate

# Initialize Flask App
app = Flask(__name__)

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "medicoapplication05@gmail.com"  # Replace with your Gmail
SMTP_PASSWORD = "gdminhcuetlmxkpu"  # Replace with app-specific password
SENDER_EMAIL = "medicoapplication05@gmail.com"  # Replace with your Gmail

def send_email_reminder(to_email, subject, message):
    try:
        print(f"Preparing to send email to {to_email} via {SMTP_SERVER}:{SMTP_PORT}")
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))

        print("Connecting to SMTP server...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        print("Starting TLS...")
        server.starttls()
        print("Logging in...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        print("Sending email...")
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        import traceback
        print(f"Failed to send email: {e}")
        traceback.print_exc()
        return False

# Security & Configurations
app.secret_key = "Sqlpassword@123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newdata.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database & Bcrypt
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)

# ------------------------- MODELS -------------------------

# User Authentication Model
class UserAuthentication(db.Model):
    __tablename__ = 'user_authentication'  # Explicitly name the table

    id = db.Column(db.Integer, primary_key=True)  # Define primary key
    name = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Hashed Passwords

# History Model (modified remainder to DateTime)
class History(db.Model):
    __tablename__ = "history"

    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(20), nullable=False)
    subname = db.Column(db.String(30), nullable=False)
    postingname = db.Column(db.String(10), nullable=False)
    patientname = db.Column(db.String(10), nullable=False)
    disease = db.Column(db.String(100), nullable=False)
    remarks = db.Column(db.String(300), nullable=False)
    duration = db.Column(db.String(100), nullable=True)  # Optional
    remainder = db.Column(db.DateTime, nullable=False)  # Changed to DateTime for both date and time

# Subject Model
class SubjectName(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    namesub = db.Column(db.String(30), nullable=False)
    staffname = db.Column(db.String(30), nullable=False)
    examdate = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(20), nullable=False)

# Subject History Model
class SubjectHistory(db.Model):
    __tablename__ = 'subject_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Auto-increment id
    namesub = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    posting_name = db.Column(db.String(100), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    disease_detail = db.Column(db.Text, nullable=False)
    remarks = db.Column(db.Text)  # Optional
    duration_date = db.Column(db.Date, nullable=False)
    remainder_date = db.Column(db.Date, nullable=False)
    remainder_time = db.Column(db.Time, nullable=False)
    extra_fields = db.Column(db.JSON, nullable=True)  # Extra Fields (JSON)

# --- File Metadata Model for Permanent Storage ---
class FileMeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(100), nullable=True)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    deleted = db.Column(db.Boolean, default=False)

# --- Conversation Model for Chatbot ---
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=True)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    subject_history_id = db.Column(db.Integer, db.ForeignKey('subject_history.id'), nullable=True)

# --- Remainder Model ---
class Remainder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    link = db.Column(db.String(255), nullable=True)

# ------------------------- DATABASE INITIALIZATION -------------------------
with app.app_context():
    db.create_all()  # Create all tables again

    # Predefined Users
    PREDEFINED_USERS = {
        "anusha@gmail.com": "password123",
        "admin@example.com": "adminpass"
    }

    for email, password in PREDEFINED_USERS.items():
        user = UserAuthentication.query.filter_by(email=email).first()
        if not user:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = UserAuthentication(name=email.split('@')[0], email=email, password=hashed_password)
            db.session.add(new_user)
    db.session.commit()

# --- Twilio WhatsApp Config ---
ACCOUNT_SID = "AC8ab66d2f801547805cc1d20add4449e3"
AUTH_TOKEN = "d66c5ad3b0e5f149e529925ee4ace8c6"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"
client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_whatsapp_reminder(message, phone_number):
    try:
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=f"whatsapp:{7200077663}"  # Replace with the actual phone number (without +)
        )
        return msg.sid
    except Exception as e:
        print(f"Failed to send WhatsApp message: {e}")
        return None

# ------------------------- ROUTES -------------------------



@app.route("/index")
def index():
    return redirect(url_for('authenticate'))

@app.route("/", methods=["GET", "POST"])
def entry():
    if session.get('is_authenticated'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        if not name or not email:
            flash('Please enter both name and email.', 'danger')
            return render_template('register.html')
        code = str(random.randint(1000, 9999))
        session['pending_email'] = email
        session['pending_name'] = name
        session['pending_code'] = code
        send_email_reminder(email, 'Your Login Code', f'Your verification code is: {code}')
        flash('A 4-digit code has been sent to your email. Please enter it below.')
        return redirect(url_for('verify_code'))
    return render_template('register.html')

@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        input_code = request.form.get('code')
        if 'pending_code' in session and input_code == session['pending_code']:
            session['user_email'] = session['pending_email']
            session['user_name'] = session['pending_name']
            session['is_authenticated'] = True
            session.pop('pending_code', None)
            session.pop('pending_email', None)
            session.pop('pending_name', None)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid code. Please try again.')
    return render_template('verify_code.html')

@app.route('/login_code', methods=['GET', 'POST'])
def login_code():
    if request.method == 'POST':
        input_code = request.form['code']
        if 'last_code' in session and input_code == session['last_code']:
            session['is_authenticated'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid code. Please try again.')
    # If not POST or failed, show code entry
    return render_template('verify_code.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_code'))

@app.before_request
def require_login():
    allowed_routes = ['entry', 'verify_code', 'login_code', 'static']
    if request.endpoint not in allowed_routes:
        if not session.get('is_authenticated'):
            # If user has already registered, only ask for code
            if session.get('user_email') and session.get('user_name'):
                # Generate and send new code
                code = str(random.randint(1000, 9999))
                session['last_code'] = code
                send_email_reminder(session['user_email'], 'Your Login Code', f'Your login code is: {code}')
                flash('Please enter the code sent to your email.')
                return redirect(url_for('login_code'))
            else:
                return redirect(url_for('entry'))

if __name__ == '__main__':
    app.run(debug=True)
