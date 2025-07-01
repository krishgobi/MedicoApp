from flask import Flask, render_template, redirect, url_for, request, session, jsonify, flash, json, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.start()
from flask import Response
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pytz
import requests
import random
import os
import shutil
import traceback
import zipfile
from flask_migrate import Migrate
from werkzeug.utils import secure_filename

# Initialize Flask App
app = Flask(__name__)

# In-memory storage for subjects (no database needed) with file persistence
subjects_storage = []
SUBJECTS_FILE = "subjects_data.json"

# Simple Subject Model Class
class Subject:
    def __init__(self, id, namesub, staffname, note):
        self.id = id
        self.namesub = namesub
        self.staffname = staffname
        self.note = note
    
    def to_dict(self):
        return {
            "id": self.id,
            "namesub": self.namesub,
            "staffname": self.staffname,
            "note": self.note
        }
    
    @staticmethod
    def get_all():
        return subjects_storage
    
    @staticmethod
    def get_by_name(namesub):
        for subject in subjects_storage:
            if subject.namesub == namesub:
                return subject
        return None
    
    @staticmethod
    def add_subject(namesub, staffname, note):
        # Generate a new ID
        new_id = len(subjects_storage) + 1
        new_subject = Subject(new_id, namesub, staffname, note)
        subjects_storage.append(new_subject)
        Subject.save_to_file()  # Save after adding
        return new_subject
    
    @staticmethod
    def delete_by_name(namesub):
        global subjects_storage
        subjects_storage = [s for s in subjects_storage if s.namesub != namesub]
        Subject.save_to_file()  # Save after deleting
    
    @staticmethod
    def save_to_file():
        """Save subjects to JSON file"""
        try:
            data = [subject.to_dict() for subject in subjects_storage]
            with open(SUBJECTS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"DEBUG: Saved {len(data)} subjects to {SUBJECTS_FILE}")
        except Exception as e:
            print(f"DEBUG: Error saving subjects to file: {str(e)}")
    
    @staticmethod
    def load_from_file():
        """Load subjects from JSON file"""
        global subjects_storage
        try:
            if os.path.exists(SUBJECTS_FILE):
                with open(SUBJECTS_FILE, 'r') as f:
                    data = json.load(f)
                subjects_storage = []
                for item in data:
                    subject = Subject(item['id'], item['namesub'], item['staffname'], item['note'])
                    subjects_storage.append(subject)
                print(f"DEBUG: Loaded {len(subjects_storage)} subjects from {SUBJECTS_FILE}")
            else:
                print(f"DEBUG: No subjects file found, starting with empty list")
                subjects_storage = []
        except Exception as e:
            print(f"DEBUG: Error loading subjects from file: {str(e)}")
            subjects_storage = []

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "medicoapplication05@gmail.com"  # Replace with your Gmail
SMTP_PASSWORD = "gdminhcuetlmxkpu"  # Replace with app-specific password
SENDER_EMAIL = "medicoapplication05@gmail.com"  # Replace with your Gmail

def send_email_reminder(to_email, subject, message, attachment_path=None):
    try:
        print(f"Preparing to send email to {to_email} via {SMTP_SERVER}:{SMTP_PORT}")
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))

        # Attach file if provided
        if attachment_path:
            filename = os.path.basename(attachment_path)
            with open(attachment_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

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

# Enhanced email function with multiple attachments
def send_email_with_attachments(to_email, subject, message, attachment_paths=None):
    try:
        print(f"Preparing to send email to {to_email} via {SMTP_SERVER}:{SMTP_PORT}")
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))

        # Attach multiple files if provided
        if attachment_paths:
            for attachment_path in attachment_paths:
                if attachment_path and os.path.exists(attachment_path):
                    filename = os.path.basename(attachment_path)
                    with open(attachment_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)
                    print(f"DEBUG: Attached file: {filename}")

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

# Generate PDF for history entry
def generate_history_pdf(history_id):
    try:
        history_entry = SubjectHistory.query.filter_by(id=history_id).first()
        if not history_entry:
            print(f"DEBUG: History entry not found for ID: {history_id}")
            return None

        # Create a temporary PDF file
        pdf_filename = f"history_{history_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_filename)

        # Create PDF content
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, f"Medical History Report - {history_entry.namesub}")

        # Content
        c.setFont("Helvetica", 12)
        y_position = height - 140
        line_height = 20

        content = [
            f"Subject Name: {history_entry.namesub}",
            f"Date: {history_entry.date.strftime('%Y-%m-%d')}",
            f"Posting Name: {history_entry.posting_name}",
            f"Patient Name: {history_entry.patient_name}",
            f"Disease Details: {history_entry.disease_detail}",
            f"Remarks: {history_entry.remarks or 'N/A'}",
            f"Duration Date: {history_entry.duration_date.strftime('%Y-%m-%d') if history_entry.duration_date else 'N/A'}",
            f"Reminder Date: {history_entry.remainder_date.strftime('%Y-%m-%d')}",
            f"Reminder Time: {history_entry.remainder_time.strftime('%H:%M')}",
        ]

        for line in content:
            c.drawString(100, y_position, line)
            y_position -= line_height

        # Extra fields if any
        if history_entry.extra_fields:
            y_position -= line_height
            c.drawString(100, y_position, "Additional Information:")
            y_position -= line_height
            c.drawString(120, y_position, str(history_entry.extra_fields))

        # Footer
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(100, 50, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(100, 35, "Medical History Management System")

        c.save()
        print(f"DEBUG: Generated PDF: {pdf_path}")
        return pdf_path

    except Exception as e:
        print(f"DEBUG: Error generating PDF: {str(e)}")
        return None

# Security & Configurations
app.secret_key = "Sqlpassword@123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newdata.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload Configuration
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    namesub = db.Column(db.String(100), nullable=False)
    staffname = db.Column(db.String(100), nullable=False)
    note = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "namesub": self.namesub,
            "staffname": self.staffname,
            "note": self.note
        }

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

    def to_dict(self):
        return {
            "id": self.id,
            "namesub": self.namesub,
            "date": self.date.strftime('%Y-%m-%d'),
            "posting_name": self.posting_name,
            "patient_name": self.patient_name,
            "disease_detail": self.disease_detail,
            "remarks": self.remarks,
            "duration_date": self.duration_date.strftime('%Y-%m-%d'),
            "remainder_date": self.remainder_date.strftime('%Y-%m-%d'),
            "remainder_time": self.remainder_time.strftime('%H:%M'),
            "extra_fields": self.extra_fields
        }

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

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "date": self.date.strftime('%Y-%m-%d'),
            "time": self.time.strftime('%H:%M'),
            "link": self.link
        }

# --- Exam Model ---
class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)

# ------------------------- DATABASE INITIALIZATION -------------------------
with app.app_context():
    db.create_all()  # Create all tables again

    # Load subjects from file on startup
    Subject.load_from_file()

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

# ------------------------- ROUTES -------------------------




@app.route("/", methods=["GET", "POST"])
def entry():
    user_name = session.get('user_name', 'User')
    remainders = [r.to_dict() for r in Remainder.query.order_by(Remainder.date.asc()).all()]
    subjects = Subject.get_all()
    num_subjects = len(subjects)
    upcoming_exams = Exam.query.filter(Exam.date >= datetime.now().date()).order_by(Exam.date.asc()).all()
    return render_template('dashboard.html', num_subjects=num_subjects, user_name=user_name, remainders=remainders, upcoming_exams=upcoming_exams)

@app.route("/dashboard")
def dashboard():
    user_name = session.get('user_name', 'User')
    remainders = [r.to_dict() for r in Remainder.query.order_by(Remainder.date.asc()).all()]
    subjects = Subject.get_all()
    num_subjects = len(subjects)
    upcoming_exams = Exam.query.filter(Exam.date >= datetime.now().date()).order_by(Exam.date.asc()).all()
    return render_template('dashboard.html', num_subjects=num_subjects, user_name=user_name, remainders=remainders, upcoming_exams=upcoming_exams)

@app.route('/add_history', methods=['POST'])
def add_subjecthistory():
    if request.method == 'POST':
        # Retrieve form data
        subname = request.form['namesub']
        postingname = request.form['posting_name']
        patientname = request.form['patient_name']
        disease = request.form['disease_detail']
        remarks = request.form['remarks']
        user_email = request.form.get('user_email', session.get('email', ''))  # Get user email from form or session
        
        # Retrieve remainder date and time
        remainder_date = request.form['remainder_date']
        remainder_time = request.form['remainder_time']
        remainder_datetime = datetime.strptime(f"{remainder_date} {remainder_time}", '%Y-%m-%d %H:%M')
        
        # Handle file upload if any
        uploaded_file = request.files.get('file_upload') or request.files.get('attachment')
        attachment_path = None
        if uploaded_file and uploaded_file.filename:
            filename = uploaded_file.filename
            attachment_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            uploaded_file.save(attachment_path)
            print(f"DEBUG: File uploaded and saved to: {attachment_path}")
        
        # Create and save history entry
        new_history = SubjectHistory(
            namesub=subname,
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            posting_name=postingname,
            patient_name=patientname,
            disease_detail=disease,
            remarks=remarks,
            duration_date=datetime.strptime(request.form.get('duration_date'), '%Y-%m-%d').date() if request.form.get('duration_date') else None,
            remainder_date=remainder_datetime.date(),
            remainder_time=remainder_datetime.time(),
            extra_fields=json.loads(request.form.get('extra_fields')) if request.form.get('extra_fields') else None
        )
        db.session.add(new_history)
        db.session.commit()

        print(f"DEBUG: Added history - Subject: {subname}, Patient: {patientname}, Disease: {disease}")
        print(f"DEBUG: History ID: {new_history.id}, User Email: {user_email}")

        flash("History added successfully!", "success")

        # Store user email in session for future use
        if user_email:
            session['email'] = user_email

        # Schedule email notifications with PDF generation
        user_tz = pytz.timezone('Asia/Kolkata')
        send_time = user_tz.localize(remainder_datetime)
        now = datetime.now(user_tz)

        if user_email:
            email_subject = f"Medical History Reminder: {subname}"
            email_message = f"""
Medical History Reminder

Subject: {subname}
Posting Name: {postingname}
Patient Name: {patientname}
Disease Details: {disease}
Remarks: {remarks}
Date: {new_history.date.strftime('%Y-%m-%d')}
Duration Date: {new_history.duration_date.strftime('%Y-%m-%d') if new_history.duration_date else 'N/A'}
Reminder Date & Time: {remainder_datetime.strftime('%Y-%m-%d %H:%M')}

This is an automated reminder from your Medical History Management System.
            """

            # Generate PDF for this history entry
            def send_reminder_with_pdf():
                try:
                    # Generate PDF
                    pdf_path = generate_history_pdf(new_history.id)
                    
                    # Send email with both the uploaded attachment and generated PDF
                    attachments = []
                    if pdf_path:
                        attachments.append(pdf_path)
                    if attachment_path and os.path.exists(attachment_path):
                        attachments.append(attachment_path)
                    
                    send_email_with_attachments(user_email, email_subject, email_message, attachments)
                    
                    # Clean up generated PDF
                    if pdf_path and os.path.exists(pdf_path):
                        os.remove(pdf_path)
                        
                except Exception as e:
                    print(f"ERROR: Failed to send reminder email: {str(e)}")

            if send_time > now:
                scheduler.add_job(
                    send_reminder_with_pdf,
                    'date',
                    run_date=send_time,
                    id=f"email_history_{new_history.id}",
                    replace_existing=True
                )
                print(f"DEBUG: Scheduled email reminder for {send_time}")
            else:
                # Send immediately if time has already passed
                send_reminder_with_pdf()
                print(f"DEBUG: Sent immediate email reminder")

        return redirect(url_for('view_subject_details', subject_name=subname))

@app.route('/add_subject', methods=['POST'])
def add_subject():
    if request.method == 'POST':
        subname = request.form['subname']
        staffname = request.form['staffname']
        note = request.form.get('note', '')  # Get note, default to empty string if not provided
        
        try:
            # Add subject using the Subject model
            new_subject = Subject.add_subject(subname, staffname, note)
            print(f"DEBUG: Added subject - {new_subject.namesub}, {new_subject.staffname}, {new_subject.note}")
            print(f"DEBUG: Total subjects now: {len(Subject.get_all())}")
            flash('Subject added successfully!', 'success')
        except Exception as e:
            print(f"DEBUG: Error adding subject: {str(e)}")
            flash(f'Error adding subject: {str(e)}', 'danger')
        
        # Redirect to view_subject page to show the updated list
        return redirect(url_for('view_subject'))

@app.route("/view_history")
def view_history():
    histories = History.query.all()  # Fetch all records
    return render_template('view_history.html', histories=histories)

@app.route("/view_subject")
def view_subject():
    subjects = Subject.get_all()
    print(f"DEBUG: view_subject route - Found {len(subjects)} subjects")
    for subject in subjects:
        print(f"DEBUG: Subject - ID: {subject.id}, Name: {subject.namesub}, Staff: {subject.staffname}, Note: {subject.note}")
    return render_template('view_subject.html', subjects=subjects)

@app.route('/delete_subject/<namesub>', methods=['GET', 'POST'])
def del_subject(namesub):
    try:
        Subject.delete_by_name(namesub)
        flash('Subject deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting subject: {str(e)}', 'danger')
    return redirect(url_for('view_subject'))

@app.route('/del_history/<int:id>', methods=['POST'])
def del_history(id):
    history_entry = History.query.get(id)
    if history_entry:
        db.session.delete(history_entry)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/subject_history_page')
def subject_history_page():
    subjects = Subject.get_all()
    return render_template('subject_history.html', subjects=subjects)

@app.route('/remainder_dashboard_page')
def remainder_dashboard():
    return render_template('remainder.html')
@app.route('/importants')
def importants():
    return render_template('important.html')
@app.route('/view_subject_details/<subject_name>')
def view_subject_details(subject_name):
    # Check if subject exists in our Subject model
    subject = Subject.get_by_name(subject_name)
    if not subject:
        return render_template('no_records_found.html', subject_name=subject_name)
    
    # Fetch all history entries for the given subject name
    subject_history_entries = SubjectHistory.query.filter_by(namesub=subject_name).all()
    
    print(f"DEBUG: view_subject_details - Subject: {subject_name}")
    print(f"DEBUG: Found {len(subject_history_entries)} history entries for {subject_name}")
    for entry in subject_history_entries:
        print(f"DEBUG: History entry - ID: {entry.id}, Patient: {entry.patient_name}, Disease: {entry.disease_detail}")

    # Always render the template, even if no history exists (so users can add history)
    return render_template('subject_history_details.html', subject_name=subject_name, subjects=subject_history_entries)
from datetime import date
@app.route('/check_reminders')
def check_reminders():
    today = date.today()
    reminders = SubjectHistory.query.filter_by(remainder_date=today).all()
    
    if reminders:
        for reminder in reminders:
            # Flash reminder details or some custom message
            flash(f"Reminder for {reminder.namesub}: {reminder.disease_detail}", "info")
    return redirect(url_for('dashboard'))  # Assuming you're redirecting to the dashboard


@app.route('/view_items')
def view_items():
    return render_template('view_items.html')
# ------------------------- PDF DOWNLOAD -------------------------

from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

@app.route('/download_single_history_pdf/<int:history_id>')
def download_single_history_pdf(history_id):
    history_entry = SubjectHistory.query.filter_by(id=history_id).first()

    if not history_entry:
        return "History not found", 404

    # Create a BytesIO buffer to hold the PDF data
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 750, f"History for Subject: {history_entry.namesub}")
    y_position = 730  # Initial position for the first entry

    pdf.drawString(100, y_position, f"Subject Name: {history_entry.namesub}")
    y_position -= 20
    pdf.drawString(100, y_position, f"Posting Name: {history_entry.posting_name}")
    y_position -= 20
    pdf.drawString(100, y_position, f"Patient Name: {history_entry.patient_name}")
    y_position -= 20
    pdf.drawString(100, y_position, f"Disease Details: {history_entry.disease_detail}")
    y_position -= 20
    pdf.drawString(100, y_position, f"Remarks: {history_entry.remarks}")
    y_position -= 20
    pdf.drawString(100, y_position, f"Date: {history_entry.date}")
    y_position -= 20
    pdf.drawString(100, y_position, f"Duration: {history_entry.duration_date}")
    y_position -= 20

    if history_entry.extra_fields:
        pdf.drawString(100, y_position, f"Extra Fields: {history_entry.extra_fields}")
        y_position -= 20

    pdf.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{history_entry.namesub}_history_{history_entry.id}.pdf", mimetype='application/pdf')
from flask import Flask, request, jsonify, send_from_directory

import os
# Directory to store uploaded files
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/upload", methods=["POST"])
def upload_files():
    if "files" not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    files = request.files.getlist("files")  # Get multiple files
    uploaded_files = []

    for file in files:
        if file.filename == "":
            continue
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], file.filename))
        uploaded_files.append(file.filename)

    return jsonify({"success": f"Uploaded {len(uploaded_files)} file(s) successfully!"})

@app.route("/files", methods=["GET"])
def list_files():
    files = os.listdir(app.config["UPLOAD_FOLDER"])
    return jsonify(files)

# Route to rename a file
@app.route("/rename/<old_name>", methods=["PUT"])
def rename_file(old_name):
    data = request.get_json()
    new_name = data.get("new_name")

    if not new_name:
        return jsonify({"error": "New file name is required"})

    old_path = os.path.join(app.config["UPLOAD_FOLDER"], old_name)
    new_path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)

    if not os.path.exists(old_path):
        return jsonify({"error": "File not found"})

    if os.path.exists(new_path):
        return jsonify({"error": "File with the new name already exists"})

    os.rename(old_path, new_path)
    return jsonify({"success": "File renamed successfully"})

# Route to delete a file
@app.route("/delete/<filename>", methods=["DELETE"])
def delete_file(filename):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"})

    os.remove(file_path)
    return jsonify({"success": "File deleted successfully"})

# Route to open/download a file
@app.route("/uploads/<filename>", methods=["GET"])
def get_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# Directory to store uploaded files
STORAGE_FOLDER = "user_uploads"
os.makedirs(STORAGE_FOLDER, exist_ok=True)
app.config["STORAGE_FOLDER"] = STORAGE_FOLDER

@app.route("/upload_files", methods=["POST"])
def handle_file_upload():
    if "user_files" not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    files = request.files.getlist("user_files")  # Get multiple files
    uploaded_list = []

    for file in files:
        if file.filename == "":
            continue
        file.save(os.path.join(app.config["STORAGE_FOLDER"], file.filename))
        uploaded_list.append(file.filename)

    return jsonify({"success": f"Uploaded {len(uploaded_list)} file(s) successfully!"})

@app.route("/list_uploaded_files", methods=["GET"])
def fetch_uploaded_files():
    file_list = os.listdir(app.config["STORAGE_FOLDER"])
    return jsonify(file_list)

@app.route("/rename_uploaded_file/<existing_name>", methods=["PUT"])
def modify_file_name(existing_name):
    data = request.get_json()
    new_file_name = data.get("new_name")

    if not new_file_name:
        return jsonify({"error": "New file name is required"})

    old_path = os.path.join(app.config["STORAGE_FOLDER"], existing_name)
    new_path = os.path.join(app.config["STORAGE_FOLDER"], new_file_name)

    if not os.path.exists(old_path):
        return jsonify({"error": "File not found"})

    if os.path.exists(new_path):
        return jsonify({"error": "File with the new name already exists"})

    os.rename(old_path, new_path)
    return jsonify({"success": "File renamed successfully"})

@app.route("/remove_uploaded_file/<file_name>", methods=["DELETE"])
def erase_uploaded_file(file_name):
    file_path = os.path.join(app.config["STORAGE_FOLDER"], file_name)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"})

    os.remove(file_path)
    return jsonify({"success": "File deleted successfully"})

@app.route("/fetch_file/<file_name>", methods=["GET"])
def retrieve_uploaded_file(file_name):
    return send_from_directory(app.config["STORAGE_FOLDER"], file_name)
from flask import Flask, render_template, request, jsonify, send_from_directory
import os

UPLOAD_FOLDER = "uplo"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

cards = []



@app.route("/get_cards")
def get_cards():
    return jsonify(cards)

@app.route("/add_card", methods=["POST"])
def add_card():
    card_id = len(cards) + 1
    new_card = {"id": card_id, "name": f"Card {card_id}", "files": []}
    cards.append(new_card)
    return jsonify({"success": True, "card": new_card})

@app.route("/delete_card/<int:card_id>", methods=["DELETE"])
def delete_card(card_id):
    global cards
    cards = [card for card in cards if card["id"] != card_id]
    return jsonify({"success": True})

@app.route("/rename_card", methods=["POST"])
def rename_card():
    data = request.json
    card_id = int(data["id"])
    new_name = data["name"]
    
    for card in cards:
        if card["id"] == card_id:
            card["name"] = new_name
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Card not found"})

# --- API: List all files (active and deleted) ---
@app.route("/api/files", methods=["GET"])
def api_list_files():
    files = FileMeta.query.all()
    return jsonify([
        {
            "filename": f.filename,
            "subject": f.subject,
            "upload_time": f.upload_time.strftime('%Y-%m-%d %H:%M:%S'),
            "deleted": f.deleted
        } for f in files
    ])

# --- API: Upload file ---
@app.route("/api/upload", methods=["POST"])
def api_upload_file():
    file = request.files.get("file")
    subject = request.form.get("subject")
    if not file or file.filename == "":
        return jsonify({"error": "No file provided"}), 400
    filename = file.filename
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)
    meta = FileMeta(filename=filename, subject=subject)
    db.session.add(meta)
    db.session.commit()
    return jsonify({"success": True, "filename": filename})

# --- API: Delete (move to recycle bin) ---
@app.route("/api/delete/<filename>", methods=["POST"])
def api_delete_file(filename):
    meta = FileMeta.query.filter_by(filename=filename, deleted=False).first()
    if not meta:
        return jsonify({"error": "File not found"}), 404
    meta.deleted = True
    db.session.commit()
    return jsonify({"success": True})

# --- API: Restore from recycle bin ---
@app.route("/api/restore/<filename>", methods=["POST"])
def api_restore_file(filename):
    meta = FileMeta.query.filter_by(filename=filename, deleted=True).first()
    if not meta:
        return jsonify({"error": "File not found in recycle bin"}), 404
    meta.deleted = False
    db.session.commit()
    return jsonify({"success": True})

@app.route("/uplo/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/documents')
def documents():
    return render_template('documents.html')

@app.route('/recycle_bin')
def recycle_bin():
    return render_template('recycle_bin.html')

# --- Gemini Chatbot API ---
GEMINI_API_KEY = "AIzaSyDSC0_iegx7FkpflShnjpJ8COLRqhh6wuE"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"


@app.route('/chatbot-gemini', methods=['POST'])
def chatbot_gemini():
    data = request.json
    user_message = data.get('message', '')
    
    # Try to answer from database first
    try:
        # Convert message to lowercase for better matching
        msg = user_message.lower()
        
        # Check for specific medical history queries
        if 'disease' in msg or 'condition' in msg:
            histories = SubjectHistory.query.filter(
                SubjectHistory.disease_detail.ilike(f'%{msg}%')
            ).all()
            if histories:
                response = "Found these related medical histories:<br>"
                for h in histories:
                    response += f"• Patient: {h.patient_name} - {h.disease_detail}<br>"
                return jsonify({"reply": response})

        # Check for subject-related queries
        if 'subject' in msg:
            subjects = Subject.get_all()
            if subjects:
                response = "Here are the subjects:<br>"
                for s in subjects:
                    response += f"• {s.namesub} (Staff: {s.staffname})<br>"
                return jsonify({"reply": response})

        # Check for staff-related queries
        if 'staff' in msg or 'teacher' in msg:
            subjects = Subject.get_all()
            staff_list = list(set(s.staffname for s in subjects))
            if staff_list:
                response = "Here are all staff members:<br>"
                response += "<br>".join([f"• {staff}" for staff in staff_list])
                return jsonify({"reply": response})

        # Check for reminders
        if 'reminder' in msg or 'upcoming' in msg:
            upcoming = SubjectHistory.query.filter(
                SubjectHistory.remainder_date >= datetime.now().date()
            ).order_by(SubjectHistory.remainder_date).limit(5).all()
            if upcoming:
                response = "Upcoming reminders:<br>"
                for u in upcoming:
                    response += f"• {u.namesub} on {u.remainder_date.strftime('%Y-%m-%d')} at {u.remainder_time.strftime('%H:%M')}<br>"
                return jsonify({"reply": response})

        # Check for patient history
        if 'patient' in msg:
            patients = SubjectHistory.query.with_entities(
                SubjectHistory.patient_name, 
                SubjectHistory.disease_detail
            ).distinct().limit(5).all()
            if patients:
                response = "Recent patient records:<br>"
                for p in patients:
                    response += f"• {p[0]} - {p[1]}<br>"
                return jsonify({"reply": response})

    except Exception as e:
        print(f"Database query error: {str(e)}")

    # If no database match, use Gemini API
    try:
        # Add medical context to the prompt
        prompt = f"""User: {user_message}\nContext: This is a medical history management system. Topics include:\n- Patient medical histories and conditions\n- Subject and staff management\n- Medical reminders and appointments\n- Document management for medical records\n\nAssistant:"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        resp = requests.post(GEMINI_API_URL, json=payload)
        resp.raise_for_status()
        gemini_reply = resp.json()['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"reply": gemini_reply})
    except Exception as e:
        return jsonify({"reply": "Sorry, I couldn't reach Gemini API. (" + str(e) + ")"}), 500

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    # Use the models to answer questions
    answer = answer_from_db(user_message)
    # Save conversation
    conversation = Conversation(message=user_message, response=answer)
    db.session.add(conversation)
    db.session.commit()
    return jsonify({'response': answer})

# --- Chatbot logic using your data ---
def answer_from_db(user_message):
    user_message = user_message.lower()
    # Remainders
    if 'remainder' in user_message or 'reminder' in user_message:
        from datetime import date, datetime
        today = date.today()
        current_time = datetime.now().time()
        
        # Get only active/future reminders
        future_remainders = Remainder.query.filter(Remainder.date > today).order_by(Remainder.date.asc()).all()
        today_remainders = Remainder.query.filter(
            Remainder.date == today,
            Remainder.time >= current_time
        ).order_by(Remainder.time.asc()).all()
        
        active_remainders = today_remainders + future_remainders
        
        if not active_remainders:
            return '<b>Active Remainders:</b><br><i>No active remainders found.</i>'
        lines = []
        for r in active_remainders:
            status = ' (Today)' if r.date == today else ''
            line = f'<li><a href="/view_remainders#rem-{r.id}" target="_blank">{r.content} - {r.date.strftime("%Y-%m-%d")}{status}</a></li>'
            lines.append(line)
        return '<b>Active Remainders:</b><ul>' + ''.join(lines) + '</ul>'
    # Subjects button or subjects list
    if 'subject' in user_message or 'subjects' in user_message or 'subjects list' in user_message or 'subjects button' in user_message:
        subjects = Subject.get_all()
        if not subjects:
            return '<b>Subjects:</b><br><i>No subjects found yet.</i>'
        lines = [f'<li><a href="/view_subject?subject={s.namesub}" target="_blank">{s.namesub}</a> (Staff: {s.staffname}, Note: {s.note})</li>' for s in subjects]
        return '<b>Subjects:</b><ul>' + ''.join(lines) + '</ul>'
    # Patient
    if 'patient' in user_message:
        patients = SubjectHistory.query.order_by(SubjectHistory.date.desc()).all()
        if patients:
            reply = 'Recent patients:<ul>' + ''.join(f'<li>{p.patient_name} - {p.disease_detail} (on {p.date.strftime("%Y-%m-%d")})</li>' for p in patients) + '</ul>'
        else:
            reply = 'No patient records found.'
        return reply
    # Disease
    if 'disease' in user_message:
        diseases = SubjectHistory.query.with_entities(SubjectHistory.disease_detail).distinct().all()
        if not diseases:
            return '<b>Diseases:</b><br><i>No diseases found yet.</i>'
        lines = [f'<li><a href="/view_history?disease={d[0]}" target="_blank">{d[0]}</a></li>' for d in diseases]
        return '<b>Diseases:</b><ul>' + ''.join(lines) + '</ul>'
    # History (list all history records)
    if 'history' in user_message:
        histories = SubjectHistory.query.order_by(SubjectHistory.date.desc()).all()
        if not histories:
            return '<b>History:</b><br><i>No history records found yet.</i>'
        lines = [
            f'<li><a href="/view_history?patient={h.patient_name}" target="_blank">{h.date.strftime("%Y-%m-%d")}: {h.namesub} - {h.patient_name} ({h.disease_detail})</a></li>'
            for h in histories
        ]
        return '<b>History:</b><ul>' + ''.join(lines) + '</ul>'
    # File
    if 'file' in user_message or 'document' in user_message:
        files = FileMeta.query.with_entities(FileMeta.filename).filter_by(deleted=False).all()
        if not files:
            return '<b>Files:</b><br><i>No files found yet.</i>'
        lines = [f'<li><a href="/uploads/{f[0]}" target="_blank">{f[0]}</a></li>' for f in files]
        return '<b>Files:</b><ul>' + ''.join(lines) + '</ul>'
    # Default
    return "Sorry, I couldn't understand. Try asking about <b>subjects</b>, <b>patients</b>, <b>reminders</b>, <b>diseases</b>, <b>history</b>, or <b>files</b>."
# --- Export actual database data as CSV ---
@app.route('/export_actual_data_csv')
def export_actual_data_csv():
    def generate():
        # UserAuthentication
        yield '# UserAuthentication Table\n'
        yield 'user_id,name,email,password\n'
        for u in UserAuthentication.query.all():
            yield f'{u.id},{u.name},{u.email},{u.password}\n'
        yield '\n# Subject Table\n'
        yield 'subject_id,namesub,staffname,note\n'
        for s in Subject.get_all():
            yield f'{s.id},{s.namesub},{s.staffname},{s.note}\n'
        yield '\n# SubjectHistory Table\n'
        yield 'history_id,namesub,date,posting_name,patient_name,disease_detail,remarks,duration_date,remainder_date,remainder_time,extra_fields\n'
        for h in SubjectHistory.query.all():
            extra = str(h.extra_fields).replace('\n',' ').replace(',',';') if h.extra_fields else ''
            yield f'{h.id},{h.namesub},{h.date},{h.posting_name},{h.patient_name},{h.disease_detail},{h.remarks},{h.duration_date},{h.remainder_date},{h.remainder_time},{extra}\n'
        yield '\n# FileMeta Table\n'
        yield 'file_id,filename,subject,upload_time,deleted\n'
        for f in FileMeta.query.all():
            yield f'{f.id},{f.filename},{f.subject},{f.upload_time},{f.deleted}\n'
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=actual_medico_data.csv"})

import os
import zipfile
from flask import send_file

@app.route('/download_all_pdfs')
def download_all_pdfs():
    # Folders to search for PDFs
    pdf_dirs = ['uploads', 'uplo', 'uploads/', 'uplo/']
    pdf_files = []
    for d in pdf_dirs:
        if os.path.exists(d):
            for fname in os.listdir(d):
                if fname.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(d, fname))
    # Create a zip in memory
    zip_path = 'all_medico_pdfs.zip'
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for f in pdf_files:
            zipf.write(f, os.path.relpath(f))
    return send_file(zip_path, as_attachment=True)

@app.route('/add_remainder', methods=['POST'])
def add_remainder():
    if request.method == 'POST':
        content = request.form['content']
        date_str = request.form['date']
        time_str = request.form['time']
        link = request.form.get('link', None)
        user_email = request.form.get('email') or session.get('user_email')
        reminder_offset = int(request.form.get('reminder_offset', 20))  # Default 20 mins
        file = request.files.get('file')
        attachment_path = None
        if file and file.filename:
            attachment_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(attachment_path)
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format for remainder.', 'danger')
            return redirect(url_for('dashboard'))
        remainder = Remainder(content=content, date=date, time=time, link=link)
        db.session.add(remainder)
        db.session.commit()
        flash('Remainder added successfully!', 'success')

        # Schedule both WhatsApp and Email reminders with user-selected offset
        user_tz = pytz.timezone('Asia/Kolkata')
        send_time = user_tz.localize(datetime.combine(date, time)) - timedelta(minutes=reminder_offset)
        now = datetime.now(user_tz)
        phone_number = "917200077663"  # Set your recipient phone number here
        email_subject = f"Reminder: {content}"
        email_message = f"""
        Reminder Details:
        Content: {content}
        Date: {date_str}
        Time: {time_str}
        """
        if link:
            email_message += f"\nRelated Link: {link}"
        if user_email:
            if send_time > now:
                # Schedule email reminder
                scheduler.add_job(
                    send_email_reminder,
                    'date',
                    run_date=send_time,
                    args=[user_email, email_subject, email_message, attachment_path],
                    id=f"email_reminder_{remainder.id}",
                    replace_existing=True
                )
            else:
                send_email_reminder(user_email, email_subject, email_message, attachment_path)
        else:
            flash('No email provided for reminder.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/view_remainders')
def view_remainders():
    from datetime import date, datetime
    remainders = Remainder.query.order_by(Remainder.date.asc()).all()
    now = datetime.now()
    current_date = now.date()
    current_time = now.time()
    return render_template('remainders.html', remainders=remainders, current_date=current_date, current_time=current_time)

@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        input_code = request.form['code']
        if 'pending_code' in session and input_code == session['pending_code']:
            # Successful verification
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

@app.route('/add_exam', methods=['POST'])
def add_exam():
    if request.method == 'POST':
        try:
            # Get form data
            subject = request.form['subject']
            exam_type = request.form['exam_type']
            date_str = request.form['date']
            time_str = request.form['time']
            remainder_date_str = request.form['remainder_date']
            remainder_time_str = request.form['remainder_time']
            user_email = request.form.get('user_email', session.get('email', ''))  # Get user email from form or session
            
            # Parse exam date and time
            exam_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            exam_time = datetime.strptime(time_str, "%H:%M").time()
            
            # Parse remainder date and time
            remainder_date = datetime.strptime(remainder_date_str, "%Y-%m-%d").date()
            remainder_time = datetime.strptime(remainder_time_str, "%H:%M").time()
            remainder_datetime = datetime.combine(remainder_date, remainder_time)
            
            # Handle file upload
            attachment_path = None
            if 'file' in request.files:
                file = request.files['file']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{filename}"
                    attachment_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(attachment_path)
                    print(f"DEBUG: File saved to {attachment_path}")
            
            # Create new exam (only with fields that exist in database)
            new_exam = Exam(
                subject=subject, 
                exam_type=exam_type, 
                date=exam_date, 
                time=exam_time
            )
            db.session.add(new_exam)
            db.session.commit()
            
            flash(f'Exam added successfully! Reminder set for {remainder_date.strftime("%Y-%m-%d")} at {remainder_time.strftime("%H:%M")}', 'success')
            print(f"DEBUG: Added exam - Subject: {subject}, Type: {exam_type}, Date: {exam_date}")
            print(f"DEBUG: Remainder scheduled for: {remainder_date} at {remainder_time}")
            
            # Store user email in session for future use
            if user_email:
                session['email'] = user_email
            
            # Schedule email reminder if user email is available
            if user_email:
                user_tz = pytz.timezone('Asia/Kolkata')
                send_time = user_tz.localize(remainder_datetime)
                now = datetime.now(user_tz)
                
                email_subject = f"Exam Reminder: {subject} ({exam_type})"
                email_message = f"""
Exam Reminder

Subject: {subject}
Exam Type: {exam_type}
Exam Date: {exam_date.strftime('%Y-%m-%d')}
Exam Time: {exam_time.strftime('%H:%M')}
Reminder Date & Time: {remainder_datetime.strftime('%Y-%m-%d %H:%M')}

This is an automated reminder from your Medical Management System.
Good luck with your exam!
                """
                
                def send_exam_reminder():
                    try:
                        attachments = []
                        if attachment_path and os.path.exists(attachment_path):
                            attachments.append(attachment_path)
                        
                        send_email_with_attachments(user_email, email_subject, email_message, attachments)
                        print(f"DEBUG: Sent exam reminder email for {subject}")
                    except Exception as e:
                        print(f"ERROR: Failed to send exam reminder email: {str(e)}")
                
                if send_time > now:
                    scheduler.add_job(
                        send_exam_reminder,
                        'date',
                        run_date=send_time,
                        id=f"email_exam_{new_exam.id}",
                        replace_existing=True
                    )
                    print(f"DEBUG: Scheduled exam email reminder for {send_time}")
                else:
                    # Send immediately if time has already passed
                    send_exam_reminder()
                    print(f"DEBUG: Sent immediate exam email reminder")
            else:
                print("DEBUG: No user email available for exam reminder")
                
        except ValueError as e:
            flash(f'Invalid date/time format: {str(e)}', 'danger')
            print(f"DEBUG: Date/time parsing error: {str(e)}")
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding exam: {str(e)}', 'danger')
            print(f"DEBUG: Error adding exam: {str(e)}")
            
        return redirect(url_for('dashboard'))

@app.route('/rename_profile', methods=['POST'])
def rename_profile():
    data = request.get_json()
    new_name = data.get('newProfileName', '').strip()
    if not new_name:
        return jsonify({'success': False, 'message': 'No new name provided.'}), 400
    # Remove login check, just update session and return success
    session['user_name'] = new_name
    return jsonify({'success': True, 'message': 'Profile name updated.'})

@app.route('/chatbot_ask', methods=['POST'])
def chatbot_ask():
    data = request.get_json()
    question = data.get('question', '').lower()
    reply = "I'm sorry, I couldn't process that."

    # Example: Show all subjects
    if 'subject' in question or 'all subjects' in question:
        subjects = Subject.get_all()
        if subjects:
            # Each subject links to its detail page
            reply = 'Here are your current subjects:<ul>' + ''.join(
                f'<li><a href="/view_subject_details/{s.namesub}" target="_blank">{s.namesub}</a> (Staff: {s.staffname})</li>' for s in subjects
            ) + '</ul>'
        else:
            reply = 'No subjects found.'
    # Example: Show all reminders (only show upcoming/active, not expired)
    elif 'reminder' in question:
        from datetime import date, datetime
        today = date.today()
        current_time = datetime.now().time()
        
        # Get reminders that are today (and not yet passed) or in the future
        future_reminders = Remainder.query.filter(Remainder.date > today).order_by(Remainder.date.asc(), Remainder.time.asc()).all()
        today_reminders = Remainder.query.filter(
            Remainder.date == today,
            Remainder.time >= current_time
        ).order_by(Remainder.time.asc()).all()
        
        all_active_reminders = today_reminders + future_reminders
        
        if all_active_reminders:
            reply = '<b>Active & Upcoming Reminders:</b><ul>'
            for r in all_active_reminders:
                # Link to remainders page, anchor to reminder id if possible
                status = " (Today)" if r.date == today else ""
                reply += f'<li><a href="/view_remainders#rem-{r.id}" target="_blank">{r.content} on {r.date.strftime('%Y-%m-%d')} at {r.time.strftime('%H:%M')}{status}</a></li>'
            reply += '</ul>'
        else:
            reply = 'No active or upcoming reminders found.'
    # Example: Show all patients from SubjectHistory table, each links to subject history detail page
    elif 'patient' in question:
        patients = SubjectHistory.query.order_by(SubjectHistory.date.desc()).all()
        if patients:
            reply = 'Recent patients:<ul>' + ''.join(f'<li><a href="/view_subject_details/{p.namesub}" target="_blank">{p.patient_name} - {p.disease_detail} (on {p.date.strftime('%Y-%m-%d')})</a></li>' for p in patients) + '</ul>'
        else:
            reply = 'No patient records found.'
    # Example: If user asks about a specific subject or patient, provide direct link
    elif 'details for' in question or 'show details for' in question:
        # Try to extract subject or patient name
        import re
        m = re.search(r'details for ([\w\s]+)', question)
        if m:
            name = m.group(1).strip()
            # Try subject first
            subject = Subject.get_by_name(name)
            if subject:
                reply = f'View details for <a href="/view_subject_details/{subject.namesub}" target="_blank">{subject.namesub}</a>.'
            else:
                # Try patient
                patient = SubjectHistory.query.filter(SubjectHistory.patient_name.ilike(f'%{name}%')).first()
                if patient:
                    reply = f'View patient record for <a href="/view_subject_details/{patient.namesub}" target="_blank">{patient.patient_name}</a>.'
                else:
                    reply = 'No matching subject or patient found.'
        else:
            reply = 'Please specify a subject or patient name.'
    # Example: Show today's date
    elif 'date' in question or 'today' in question:
        reply = f"Today's date is <strong>{datetime.now().strftime('%B %d, %Y')}</strong>."
    # Default fallback
    else:
        reply = "Sorry, I couldn't understand. Try asking about <b>subjects</b>, <b>patients</b>, or <b>reminders</b>."
    return jsonify({'reply': reply})

@app.route('/delete_exam/<int:exam_id>', methods=['POST'])
def delete_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    try:
        db.session.delete(exam)
        db.session.commit()
        flash('Exam deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting exam: {str(e)}', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/reminder_detail/<int:reminder_id>')
def reminder_detail(reminder_id):
    r = Remainder.query.get_or_404(reminder_id)
    return render_template('reminder_detail.html', r=r)

@app.route('/delete_reminder/<int:reminder_id>', methods=['POST'])
def delete_reminder(reminder_id):
    reminder = Remainder.query.get_or_404(reminder_id)
    try:
        db.session.delete(reminder)
        db.session.commit()
        flash('Reminder deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting reminder: {str(e)}', 'danger')
    return redirect(url_for('view_remainders'))

# --- API: List deleted files for recycle bin (JSON for frontend) ---
@app.route('/recycle-bin', methods=['GET'])
def api_recycle_bin():
    files = FileMeta.query.filter_by(deleted=True).all()
    filenames = [f.filename for f in files]
    return jsonify(filenames)

@app.route('/move_to_old/<namesub>', methods=['POST'])
def move_to_old(namesub):
    # Since we're using in-memory storage, we can just delete the subject
    # or mark it differently. For now, let's just delete it.
    Subject.delete_by_name(namesub)
    # Move all related histories to old as well
    histories = SubjectHistory.query.filter_by(namesub=namesub).all()
    for h in histories:
        h.namesub = f"OLD::{h.namesub}"
    db.session.commit()
    flash('Subject moved to Old Subjects!', 'success')
    return redirect(url_for('view_subject'))

@app.route('/old_subjects')
def old_subjects():
    # Since we're using in-memory storage, we won't have old subjects stored
    # We can only show histories for old subjects
    old_histories = SubjectHistory.query.filter(SubjectHistory.namesub.like('OLD::%')).all()
    return render_template('old_subjects.html', old_subjects=[], old_histories=old_histories)

@app.route("/authenticate", methods=["GET", "POST"])
def authenticate():
    if request.method == "POST":
        # Simple authentication for testing
        session['user_name'] = 'Test User'
        session['email'] = 'test@example.com'
        session['is_authenticated'] = True
        return redirect(url_for('dashboard'))
    
    # Simple login form for testing
    return '''
    <form method="post">
        <input type="submit" value="Login for Testing">
    </form>
    '''

@app.route("/add_sample_data")
def add_sample_data():
    """Add sample subjects for testing"""
    try:
        # Add sample subjects using the correct constructor
        Subject.add_subject("Cardiology", "Dr. Smith", "Study of heart and cardiovascular system")
        Subject.add_subject("Neurology", "Dr. Johnson", "Study of nervous system disorders")
        Subject.add_subject("Orthopedics", "Dr. Brown", "Study of bones, joints, and muscles")
        Subject.add_subject("Pediatrics", "Dr. Davis", "Medical care of infants and children")
        Subject.add_subject("Dermatology", "Dr. Wilson", "Study of skin conditions")
        
        print("DEBUG: Sample subjects added successfully")
        print(f"DEBUG: Total subjects now: {len(Subject.get_all())}")
        flash('Sample subjects have been added! You now have 5 subjects.', 'success')
        
    except Exception as e:
        print(f"DEBUG: Error adding sample data: {str(e)}")
        flash(f'Error adding sample data: {str(e)}', 'danger')
    
    return redirect(url_for('view_subject'))

@app.route('/delete_subject_history/<int:history_id>', methods=['POST'])
def delete_subject_history(history_id):
    """Delete a specific subject history entry"""
    try:
        # Find the history entry
        history_entry = SubjectHistory.query.get(history_id)
        
        if not history_entry:
            flash('History record not found.', 'danger')
            return redirect(url_for('view_subject'))
        
        # Store the subject name for redirection
        subject_name = history_entry.namesub
        
        # Delete the history entry
        db.session.delete(history_entry)
        db.session.commit()
        
        print(f"DEBUG: Deleted history entry - ID: {history_id}, Subject: {subject_name}")
        flash('History record deleted successfully!', 'success')
        
        # Redirect back to the subject details page
        return redirect(url_for('view_subject_details', subject_name=subject_name))
        
    except Exception as e:
        print(f"DEBUG: Error deleting history: {str(e)}")
        db.session.rollback()
        flash(f'Error deleting history record: {str(e)}', 'danger')
        return redirect(url_for('view_subject'))

@app.route('/clear_all_data', methods=['POST'])
def clear_all_data():
    """Clear all data from the system - subjects, histories, remainders, files, conversations, exams"""
    try:
        # Clear in-memory subjects storage
        global subjects_storage
        subjects_storage = []
        
        # Remove the subjects file
        if os.path.exists(SUBJECTS_FILE):
            os.remove(SUBJECTS_FILE)
            print(f"DEBUG: Removed subjects file: {SUBJECTS_FILE}")
        
        print("DEBUG: Cleared subjects_storage")
        
        # Clear all database tables
        SubjectHistory.query.delete()
        print("DEBUG: Cleared SubjectHistory table")
        
        History.query.delete()
        print("DEBUG: Cleared History table")
        
        Remainder.query.delete()
        print("DEBUG: Cleared Remainder table")
        
        FileMeta.query.delete()
        print("DEBUG: Cleared FileMeta table")
        
        Conversation.query.delete()
        print("DEBUG: Cleared Conversation table")
        
        Exam.query.delete()
        print("DEBUG: Cleared Exam table")
        
        # Commit all deletions
        db.session.commit()
        
        # Clear uploaded files from directories
        upload_dirs = ['uploads', 'uplo', 'user_uploads']
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                for filename in os.listdir(upload_dir):
                    file_path = os.path.join(upload_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"Error deleting {file_path}: {e}")
        
        print("DEBUG: System reset completed successfully")
        flash('All data has been cleared successfully! You can now start fresh.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error during system reset: {str(e)}")
        flash(f'Error clearing data: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/reset_system', methods=['GET', 'POST'])
def reset_system():
    """Show confirmation page for system reset"""
    if request.method == 'POST':
        # User confirmed reset
        return redirect(url_for('clear_all_data'))
    
    # Show confirmation page
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reset System - Confirmation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 50px; background-color: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .btn { padding: 10px 20px; margin: 10px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn-danger { background-color: #dc3545; color: white; }
            .btn-secondary { background-color: #6c757d; color: white; }
            .btn:hover { opacity: 0.8; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>⚠️ System Reset Confirmation</h2>
            <div class="warning">
                <strong>Warning!</strong> This action will permanently delete ALL data including:
                <ul>
                    <li>All subjects and their histories</li>
                    <li>All patient records</li>
                    <li>All reminders and remainders</li>
                    <li>All uploaded files</li>
                    <li>All chat conversations</li>
                    <li>All exam schedules</li>
                </ul>
                <strong>This action cannot be undone!</strong>
            </div>
            
            <p>Are you sure you want to clear all data and start from scratch?</p>
            
            <form method="post" style="display: inline;">
                <button type="submit" class="btn btn-danger">Yes, Clear All Data</button>
            </form>
            <a href="/dashboard" class="btn btn-secondary">Cancel</a>
        </div>
    </body>
    </html>
    '''

@app.route('/clear_history_data', methods=['POST'])
def clear_history_data():
    """Clear only subject history data"""
    try:
        # Clear all SubjectHistory records
        SubjectHistory.query.delete()
        print("DEBUG: Cleared SubjectHistory table")
        
        # Commit the deletion
        db.session.commit()
        
        print("DEBUG: History data cleared successfully")
        flash('All history data has been cleared successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error clearing history data: {str(e)}")
        flash(f'Error clearing history data: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/test_email_functionality')
def test_email_functionality():
    """Simple test route to verify email sending works"""
    try:
        # Test email configuration
        test_email = "test@example.com"  # Change this to your email
        subject = "Test Email from MedicoApp"
        message = """
This is a test email to verify that the email functionality is working properly.

If you receive this email, the email system is configured correctly.

Best regards,
MedicoApp Team
        """
        
        success = send_email_reminder(test_email, subject, message)
        
        if success:
            return jsonify({"status": "success", "message": f"Test email sent successfully to {test_email}"})
        else:
            return jsonify({"status": "error", "message": "Failed to send test email"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": f"Email test failed: {str(e)}"})

@app.route('/test_exam_email', methods=['POST'])
def test_exam_email():
    """Test route to verify email functionality"""
    try:
        test_email = request.form.get('test_email', 'test@example.com')
        
        # Create a test email
        email_subject = "Test Exam Reminder - MediTrack"
        email_message = """
Dear Student,

This is a test reminder for your upcoming exam:

Subject: Test Subject
Exam Type: Test Exam
Date: 2025-07-15
Time: 14:00

This is a test email to verify the reminder system is working.

Best regards,
MediTrack Team
        """
        
        # Send test email
        success = send_email_reminder(test_email, email_subject, email_message)
        
        if success:
            flash(f'Test email sent successfully to {test_email}!', 'success')
        else:
            flash(f'Failed to send test email to {test_email}. Check email configuration.', 'danger')
            
    except Exception as e:
        flash(f'Error sending test email: {str(e)}', 'danger')
        print(f"DEBUG: Test email error: {str(e)}")
    
    return redirect(url_for('dashboard'))

# Test route for email functionality
@app.route('/test_email_with_pdf')
def test_email_with_pdf():
    """Test route to verify email with PDF attachment works"""
    try:
        # Test email configuration
        test_email = "your-test-email@gmail.com"  # Replace with your actual email
        subject = "Test Email with PDF from MedicoApp"
        message = """
This is a test email with PDF attachment to verify that the email functionality is working properly.

If you receive this email with a PDF attachment, the email system is configured correctly.

Best regards,
MedicoApp Team
        """
        
        # Create a sample history entry for PDF generation (if any exists)
        sample_history = SubjectHistory.query.first()
        attachments = []
        
        if sample_history:
            pdf_path = generate_history_pdf(sample_history.id)
            if pdf_path:
                attachments.append(pdf_path)
        
        # Send test email with attachments
        if attachments:
            success = send_email_with_attachments(test_email, subject, message, attachments)
        else:
            success = send_email_reminder(test_email, subject, message)
        
        # Clean up generated PDF
        if attachments and os.path.exists(attachments[0]):
            os.remove(attachments[0])
        
        if success:
            return jsonify({"status": "success", "message": f"Test email with PDF sent successfully to {test_email}"})
        else:
            return jsonify({"status": "error", "message": "Failed to send test email"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": f"Email test failed: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True)
