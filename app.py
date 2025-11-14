from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import math

app = Flask(__name__)
app.secret_key = 'A1AutoCareSecretKey'

# -----------------------------
# BRANCH LOCATIONS (FAKE EXAMPLE DATA)
# -----------------------------
BRANCHES = [
    {"name": "Milton Keynes", "lat": 52.0406, "lon": -0.7594},
    {"name": "Wembley", "lat": 51.5530, "lon": -0.2960},
    {"name": "Luton", "lat": 51.8787, "lon": -0.4200},
]

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
            postcode TEXT,
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

init_db()

# -----------------------------
# STATIC ADMIN CREDENTIALS
# -----------------------------
ADMIN_EMAIL = 'admin@a1autocare.com'
ADMIN_PASSWORD_HASH = generate_password_hash('admin123')

# -----------------------------
# HELPER FUNCTIONS (POSTCODES + DISTANCE)
# -----------------------------
def get_coordinates_from_postcode(postcode: str):
    """
    Uses Postcodes.io to convert a UK postcode into latitude/longitude.
    Returns (lat, lon) or None if invalid.
    """
    postcode = postcode.replace(" ", "")  # clean spaces
    try:
        res = requests.get(f"https://api.postcodes.io/postcodes/{postcode}")
        data = res.json()
        if data.get('status') == 200:
            lat = data['result']['latitude']
            lon = data['result']['longitude']
            return lat, lon
        else:
            return None
    except Exception:
        return None


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Haversine formula to calculate distance between two lat/lon points in KM.
    """
    R = 6371  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_nearest_branch(user_lat, user_lon):
    """
    Loop through BRANCHES and return (branch_dict, distance_km)
    for the closest branch.
    """
    nearest = None
    shortest = float('inf')

    for branch in BRANCHES:
        dist = calculate_distance(user_lat, user_lon, branch['lat'], branch['lon'])
        if dist < shortest:
            shortest = dist
            nearest = branch

    if nearest is None:
        return None, None
    return nearest, shortest

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
        postcode = request.form['postcode']

        # --- POSTCODES.IO + NEAREST BRANCH LOGIC ---
        nearest_branch_name = "Unknown"
        nearest_branch_distance = None

        coords = get_coordinates_from_postcode(postcode)
        if coords:
            user_lat, user_lon = coords
            branch, distance_km = find_nearest_branch(user_lat, user_lon)
            if branch:
                nearest_branch_name = branch['name']
                nearest_branch_distance = round(distance_km, 1)
        else:
            flash('We could not validate your postcode. Nearest branch not calculated.', 'warning')

        # Store nearest branch info in session for confirmation page
        session['nearest_branch_name'] = nearest_branch_name
        session['nearest_branch_distance'] = nearest_branch_distance

        # Save booking to DB
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
    INSERT INTO bookings (name, email, vehicle, make, service, notes, date, booking_time, postcode)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (name, email, vehicle, make, service, notes, date, booking_time, postcode))

        conn.commit()
        conn.close()

        return redirect(url_for('confirm'))

    return render_template('book.html')


@app.route('/confirm')
def confirm():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bookings ORDER BY id DESC LIMIT 1")
    booking = cursor.fetchone()
    conn.close()

    if booking is None:
        return "Please complete a booking first.", 400

    nearest_branch_name = session.get('nearest_branch_name', "Unknown")
    nearest_branch_distance = session.get('nearest_branch_distance', None)

    return render_template(
        "confirm.html",
        booking=booking,
        nearest_branch_name=nearest_branch_name,
        nearest_branch_distance=nearest_branch_distance
    )


# -----------------------------
# LOGIN / ADMIN / DASHBOARD
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
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings')
    bookings = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', bookings=bookings)


@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def edit_booking(id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

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

        # no return below this

    cursor.execute("SELECT * FROM bookings WHERE id=?", (id,))
    booking = cursor.fetchone()
    conn.close()

    if booking is None:
        flash('Booking not found.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('edit.html', booking=booking)


@app.route('/admin/delete/<int:id>', methods=['POST'])
def delete_booking(id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# -----------------------------
# RUN APP
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
