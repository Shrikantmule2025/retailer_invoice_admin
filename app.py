
from flask import Flask, render_template, request, redirect, session, send_file
import os
import json
import pdfkit
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Constants
INVOICES = "static/invoices.json"
USERS = {"admin": "admin123"}
RETAILERS = {"ret1": "1234", "ret2": "5678"}

# Utilities
def load_data(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS and USERS[username] == password:
            session['user'] = username
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    invoices = load_data(INVOICES)
    return render_template('dashboard.html', invoices=invoices)

@app.route('/approve/<rid>', methods=['POST'])
def approve(rid):
    invoices = load_data(INVOICES)
    if rid in invoices:
        invoices[rid]['status'] = 'approved'
        file_path = generate_pdf(invoices[rid], rid)
        send_invoice_email(invoices[rid]['email'], file_path)
        save_data(INVOICES, invoices)
    return redirect('/dashboard')

def generate_pdf(invoice_data, rid):
    html = render_template('invoice_template.html', invoice=invoice_data)
    path = f"static/invoice_{rid}.pdf"
    pdfkit.from_string(html, path)
    return path

def send_invoice_email(to_email, file_path):
    msg = EmailMessage()
    msg['Subject'] = "Invoice Approved"
    msg['From'] = os.environ.get("EMAIL_USER")
    msg['To'] = to_email
    msg.set_content("Your invoice is attached.")
    with open(file_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(file_path))
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASS"))
        s.send_message(msg)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
