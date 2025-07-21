from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import json, os, smtplib, pdfkit
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = 'admin-login'

RETAILERS = 'retailers.json'
INVOICES = 'invoices.json'

def load_data(file):
    return json.load(open(file, 'r', encoding='utf-8')) if os.path.exists(file) else {}

def save_data(data, file):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@app.route('/')
def home():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_data(RETAILERS)
        u = request.form['username']
        if u in users:
            flash("User exists", "danger")
        else:
            users[u] = {
                'password': request.form['password'],
                'shop': request.form['shop'],
                'email': request.form['email'],
                'license': request.form['license'],
                'owner': request.form['owner']
            }
            save_data(users, RETAILERS)
            flash("Registered. Login now.", "success")
            return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if u == 'admin' and p == 'admin123':
            session['admin'] = True
            return redirect('/admin')
        users = load_data(RETAILERS)
        if u in users and users[u]['password'] == p:
            session['user'] = u
            return redirect('/dashboard')
        flash("Invalid login", "danger")
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    if request.method == 'POST':
        invoices = load_data(INVOICES)
        rid = f"REQ{len(invoices)+1:03}"
        invoices[rid] = {
            'retailer': session['user'],
            'item': request.form['item'],
            'price': request.form['price'],
            'status': 'pending',
            'email': request.form['email']
        }
        save_data(invoices, INVOICES)
        flash(f"Request submitted: {rid}", "success")
    return render_template('dashboard.html', user=session['user'])

@app.route('/status')
def status():
    if 'user' not in session:
        return redirect('/login')
    invoices = load_data(INVOICES)
    filtered = {k:v for k,v in invoices.items() if v['retailer'] == session['user']}
    return render_template('status.html', data=filtered)

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect('/login')
    invoices = load_data(INVOICES)
    return render_template('admin.html', data=invoices)

@app.route('/approve/<rid>')
def approve(rid):
    invoices = load_data(INVOICES)
    data = invoices.get(rid)
    if data:
        data['status'] = 'approved'
        filename = f"static/invoices/invoice_{rid}.pdf"
        html = f"<h1>Invoice</h1><p>Retailer: {data['retailer']}<br>Item: {data['item']}<br>Price: {data['price']}</p>"
        pdfkit.from_string(html, filename)
        send_invoice_email(data['email'], filename)
        save_data(invoices, INVOICES)
        flash(f"Approved and emailed: {rid}", "success")
    return redirect('/admin')

def send_invoice_email(to_email, file_path):
    msg = EmailMessage()
    msg['Subject'] = "Invoice Approved"
    msg['From'] = os.environ.get('EMAIL_USER')
    msg['To'] = to_email
    msg.set_content("Your invoice is attached.")
    with open(file_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(file_path))
    with smtplib.SMTP('smtp.gmail.com', 587) as s:
        s.starttls()
        s.login(os.environ.get('EMAIL_USER'), os.environ.get('EMAIL_PASS'))
        s.send_message(msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    app.run(debug=True)
