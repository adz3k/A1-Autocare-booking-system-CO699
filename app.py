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
            booking_time TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING'
        );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
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

        return redirect(url_for('confirm'))
    
    return render_template('book.html')


@app.route('/admin/edit')
def edit_bookings():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings")
    bookings = cursor.fetchall()
    conn.close()
    return render_template('admin_edit.html', bookings=bookings)

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def edit_booking(id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # If form was submitted (POST)
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        vehicle = request.form['vehicle']
        make = request.form['make']
        service = request.form['service']
        notes = request.form['notes']
        date = request.form['date']
        booking_time = request.form['booking_time']
        status = request.form['status']

        cursor.execute('''
            UPDATE bookings
            SET name=?, email=?, vehicle=?, make=?, service=?, notes=?, date=?, booking_time=?, status=?
            WHERE id=?
        ''', (name, email, vehicle, make, service, notes, date, booking_time, status, id))

        conn.commit()
        conn.close()
        flash('Booking updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    # If GET request – load the form with current booking data
    cursor.execute('SELECT * FROM bookings WHERE id=?', (id,))
    booking = cursor.fetchone()
    conn.close()

    if booking is None:
        flash('Booking not found.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('edit.html', booking=booking)


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

@app.route('/admin/delete/<int:id>', methods=['POST'])
def delete_booking(id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM bookings WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect('/admin/dashboard')



@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/confirm', methods=['GET', 'POST'])
def confirm():
    if request.method == 'GET':
        # Retrieve query parameters from redirect
        name = request.args.get('name')
        email = request.args.get('email')
        vehicle = request.args.get('vehicle')
        make = request.args.get('make')
        service = request.args.get('service')
        notes = request.args.get('notes')
        date = request.args.get('date')
        booking_time = request.args.get('booking_time')

        # Handle direct access
        if not name:
            return "Please complete a booking first.", 400

    else:  # POST method fallback (if used directly by form)
        name = request.form['name']
        email = request.form['email']
        vehicle = request.form['vehicle']
        make = request.form['make']
        service = request.form['service']
        notes = request.form.get('notes', '')
        date = request.form['date']
        booking_time = request.form['booking_time']

    # Render confirmation page
    return render_template(
        'confirm.html',
        name=name,
        email=email,
        vehicle=vehicle,
        make=make,
        service=service,
        notes=notes,
        date=date,
        booking_time=booking_time
    )


# -----------------------------
# RUN APPLICATION
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
