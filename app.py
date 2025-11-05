from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'A1AutoCareSecretKey'

# -----------------------------
# DATABASE INITIALIZATION
# -----------------------------
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            make TEXT NOT NULL,
            service TEXT NOT NULL,
            notes TEXT,
            date TEXT NOT NULL,
            booking_time TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()

# Initialize database when app starts
init_db()

# -----------------------------
# STATIC ADMIN CREDENTIALS
# -----------------------------
ADMIN_EMAIL = 'admin@a1autocare.com'
ADMIN_PASSWORD_HASH = generate_password_hash('admin123')


# -----------------------------
# ROUTES
# -----------------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        vehicle = request.form['vehicle']
        make = request.form['make']
        service = request.form['service']
        notes = request.form['notes']
        date = request.form['date']
        booking_time = request.form['booking_time']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bookings (name, email, vehicle, make, service, notes, date, booking_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, vehicle, make, service, notes, date, booking_time))
        conn.commit()
        conn.close()

        return redirect(url_for('confirmation'))
    
    return render_template('book.html')


# -----------------------------
# LOGIN + AUTHENTICATION
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/admin/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row   # <- this is the key line
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings')
    bookings = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', bookings=bookings)


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/confirmation')
def confirmation():
    return render_template('confirm.html')


# -----------------------------
# RUN APPLICATION
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
