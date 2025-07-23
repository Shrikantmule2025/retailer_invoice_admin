
from flask import Flask, render_template, request, redirect, session, send_file
import os
import json
import pdfkit
import smtplib
import pdfkit
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
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
@app.route('/approve/<rid>', methods=['POST'])
def approve_invoice(rid):
    invoices = load_data(INVOICES)

    if rid in invoices:
        invoices[rid]['status'] = 'approved'
        save_data(INVOICES, invoices)

        # ✅ Generate PDF
        rendered = render_template("invoice_template.html", data=invoices[rid], rid=rid)
        pdf_path = f"static/invoice_{rid}.pdf"
        pdfkit.from_string(rendered, pdf_path)

        # ✅ Send Email with PDF
        msg = MIMEMultipart()
        msg['From'] = "pawanrajeagro01@gmail.com"
        msg['To'] = invoices[rid]['email']
        msg['Subject'] = "Invoice Approved - Pavanraje Agro"

        body = f"Dear {invoices[rid]['retailer_name']},\n\nYour invoice has been approved. Please find the PDF attached."
        msg.attach(MIMEText(body, 'plain'))

        with open(pdf_path, 'rb') as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
            part['Content-Disposition'] = f'attachment; filename="invoice_{rid}.pdf"'
            msg.attach(part)

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login("pawanrajeagro01@gmail.com", "evoy pclc pzzx mgre")
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print("Email sending failed:", e)

    return redirect('/admin_dashboard')

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

@app.route('/retailer_dashboard')
def retailer_dashboard():
    if 'retailer' not in session:
        return redirect('/retailer_login')

RETAILERS = {
    "retailer1": {"password": "1234", "name": "सिद्धी ट्रेडर्स"},
    "retailer2": {"password": "5678", "name": "कृषी सेवा केंद्र"}
}

@app.route('/retailer_login', methods=['GET', 'POST'])
def retailer_login():
    error = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in RETAILERS and RETAILERS[username]['password'] == password:
            session['retailer'] = username
            return redirect(url_for('retailer_dashboard'))

        error = "Invalid login. Please try again."

    return render_template('retailer_login.html', error=error)

@app.route('/retailer_logout')
def retailer_logout():
    session.pop('retailer', None)
    return redirect('/retailer_login')

    lang = request.args.get('lang', 'en')
    invoices = load_data("static/invoices.json")
    retailer = session['retailer']

    return render_template('retailer_dashboard.html', 
                           invoices=invoices, 
                           retailer=retailer, 
                           lang=lang)
from datetime import datetime
import uuid

@app.route('/retailer_request', methods=['GET', 'POST'])
def retailer_request():
    if 'retailer' not in session:
        return redirect('/retailer_login')

    lang = request.args.get('lang', 'en')
    invoices = load_data(INVOICES)

    if request.method == 'POST':
        retailer = session['retailer']
        retailer_name = request.form['retailer_name']
        email = request.form['email']
        description = request.form['description']
        request_id = str(uuid.uuid4())[:8]
        date_str = datetime.now().strftime('%Y-%m-%d')

        invoices[request_id] = {
            "retailer": retailer,
            "retailer_name": retailer_name,
            "email": email,
            "description": description,
            "date": date_str,
            "status": "pending"
        }

        save_data(INVOICES, invoices)
        return redirect(url_for('retailer_dashboard', lang=lang))

    return render_template('retailer_request.html', lang=lang)


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
