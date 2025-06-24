from flask import Flask, render_template, redirect, url_for, request, session, jsonify, flash,json
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import requests

# Initialize Flask App
app = Flask(__name__)

# Security & Configurations
app.secret_key = "Sqlpassword@123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newdata.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database & Bcrypt
db = SQLAlchemy(app)
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

# ------------------------- ROUTES -------------------------



@app.route("/index")
def index():
    return redirect(url_for('authenticate'))

@app.route("/")
def dashboard():
        
    return render_template('dashboard.html')
@app.route('/add_history', methods=['POST'])
def add_subjecthistory():
    if request.method == 'POST':
        
        # Retrieve form data
        subname = request.form['namesub']
        postingname = request.form['posting_name']
        patientname = request.form['patient_name']
        disease = request.form['disease_detail']
        remarks = request.form['remarks']
        
        # Retrieve optional fields
        duration = request.form.get('duration_date', None)
        
        # Retrieve remainder date and time
        remainder_date = request.form['remainder_date']
        remainder_time = request.form['remainder_time']
        
        # Combine date and time into a single datetime object
        remainder_datetime = datetime.strptime(f"{remainder_date} {remainder_time}", '%Y-%m-%d %H:%M')
        
        # Handling extra fields if any (for example, extra fields might be dynamically added in the form)
        extra_fields = request.form.get('extra_fields', None)  # For extra fields, assuming it's sent as JSON
        
        # If extra fields are provided as a JSON string, parse them
        if extra_fields:
            extra_fields = json.loads(extra_fields)

        # Handle optional fields with proper date format
        duration_date = datetime.strptime(duration, '%Y-%m-%d').date() if duration else None
        
        # Create a new SubjectHistory entry
        new_history = SubjectHistory(
            namesub=subname,
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            posting_name=postingname,
            patient_name=patientname,
            disease_detail=disease,
            remarks=remarks,
            duration_date=duration_date,
            remainder_date=remainder_datetime.date(),
            remainder_time=remainder_datetime.time(),
            extra_fields=extra_fields
        )

        # Add to the session and commit to the database
        db.session.add(new_history)
        db.session.commit()

        flash("History added successfully!", "success")
        return redirect(url_for('view_subject_details',subject_name=subname))

@app.route('/add_subject', methods=['POST'])
def add_subject():
    # This route is triggered when the Add Subject form is submitted (plus symbol clicked)
    # It adds the subject to the database and redirects to the dashboard
    subname = request.form['subname']
    staffname = request.form['staffname']
    examdate = request.form['examdate']
    note = request.form['note']

    # Convert examdate from string to a date object
    try:
        examdate = datetime.strptime(examdate, "%Y-%m-%d").date()
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
        return redirect(url_for('dashboard'))

    # Create a new SubjectName object
    subject = SubjectName(
        namesub=subname,
        staffname=staffname,
        examdate=examdate,
        note=note
    )

    # Add the subject to the database
    try:
        db.session.add(subject)
        db.session.commit()
        flash('Subject added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding subject: {str(e)}', 'danger')

    return redirect(url_for('dashboard'))

@app.route("/view_history")
def view_history():
    histories = History.query.all()  # Fetch all records
    return render_template('view_history.html', histories=histories)

@app.route("/view_subject")
def view_subject():
    subjects = SubjectName.query.all()
    return render_template('view_subject.html', subjects=subjects)

@app.route('/delete_subject/<namesub>', methods=['GET', 'POST'])
def del_subject(namesub):
    subject = SubjectName.query.filter_by(namesub=namesub).first()
    if subject:
        db.session.delete(subject)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/del_history/<int:id>', methods=['POST'])
def del_history(id):
    history_entry = History.query.get(id)
    if history_entry:
        db.session.delete(history_entry)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/subject_history_page')
def subject_history_page():
    subjects = SubjectName.query.all()
    return render_template('subject_history.html', subjects=subjects)

@app.route('/remainder_dashboard_page')
def remainder_dashboard():
    return render_template('remainder.html')
@app.route('/importants')
def importants():
    return render_template('important.html')
@app.route('/view_subject_details/<subject_name>')
def view_subject_details(subject_name):
    # Fetch all history entries for the given subject name
    subject_history_entries = SubjectHistory.query.filter_by(namesub=subject_name).all()

    if not subject_history_entries:
        # Return a message if no history records found for this subject
        return render_template('no_records_found.html', subject_name=subject_name)  # Pass subject_name instead of subject

    # Render the template and pass the entries for the subject
    return render_template('subject_history_details.html', subject_name=subject_name, subjects=subject_history_entries)

    # Render the template and pass the entries for the subject
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
GEMINI_API_KEY = "AIzaSyABcdZqp5FYzjKqQYEJc234YDbd123Uxa8"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=" + GEMINI_API_KEY

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
            subjects = SubjectName.query.all()
            if subjects:
                response = "Here are the subjects:<br>"
                for s in subjects:
                    response += f"• {s.namesub} (Staff: {s.staffname})<br>"
                return jsonify({"reply": response})

        # Check for staff-related queries
        if 'staff' in msg or 'teacher' in msg:
            staff = SubjectName.query.with_entities(SubjectName.staffname).distinct().all()
            if staff:
                response = "Here are all staff members:<br>"
                response += "<br>".join([f"• {s[0]}" for s in staff])
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
        prompt = f"""User: {user_message}
Context: This is a medical history management system. Topics include:
- Patient medical histories and conditions
- Subject and staff management
- Medical reminders and appointments
- Document management for medical records

Assistant:"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        resp = requests.post(GEMINI_API_URL, json=payload)
        resp.raise_for_status()
        gemini_reply = resp.json()['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"reply": gemini_reply})
    except Exception as e:
        return jsonify({"reply": "Sorry, I couldn't reach Gemini API. (" + str(e) + ")"}), 500

if __name__ == '__main__':
    app.run(debug=True)
