from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import math
from datetime import date

app = Flask(__name__)
app.secret_key = 'A1AutoCareSecretKey'

# -----------------------------
# BRANCH DATA
# -----------------------------
BRANCHES = [
    {"name": "Milton Keynes", "lat": 52.0406, "lon": -0.7594},
    {"name": "Wembley", "lat": 51.5530, "lon": -0.2960},
    {"name": "Luton", "lat": 51.8787, "lon": -0.4200},
]

# -----------------------------
# INITIALISE DB
# -----------------------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("""
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
        branch TEXT,
        status TEXT DEFAULT 'PENDING'
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    );
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# ADMIN ACCOUNT
# -----------------------------
ADMIN_EMAIL = "admin@a1autocare.com"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123")

# -----------------------------
# POSTCODE → COORDINATES
# -----------------------------
def get_coordinates_from_postcode(postcode):
    postcode = postcode.replace(" ", "").upper()
    try:
        res = requests.get(f"https://api.postcodes.io/postcodes/{postcode}")
        data = res.json()
        if data.get("status") == 200:
            return data["result"]["latitude"], data["result"]["longitude"]
    except:
        return None
    return None

# -----------------------------
# DISTANCE CALCULATION
# -----------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2)**2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(d_lon / 2)**2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# -----------------------------
# FIND NEAREST BRANCH
# -----------------------------
def find_nearest_branch(user_lat, user_lon):
    nearest = None
    shortest = float("inf")

    for branch in BRANCHES:
        dist = calculate_distance(user_lat, user_lon, branch["lat"], branch["lon"])
        if dist < shortest:
            shortest = dist
            nearest = branch
    return nearest, round(shortest, 1)

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

# -----------------------------
# BOOKING PAGE
# -----------------------------
@app.route("/book", methods=["GET", "POST"])
def book():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        vehicle = request.form["vehicle"]
        make = request.form["make"]
        service = request.form["service"]
        notes = request.form["notes"]
        date_val = request.form["date"]
        booking_time = request.form["booking_time"]
        postcode = request.form["postcode"].replace(" ", "").upper()

        coords = get_coordinates_from_postcode(postcode)

        branch_name = "UNKNOWN"
        branch_distance = None

        if coords:
            user_lat, user_lon = coords
            nearest_branch, distance_km = find_nearest_branch(user_lat, user_lon)
            branch_name = nearest_branch["name"]
            branch_distance = distance_km
        else:
            flash("Invalid postcode. Nearest branch not assigned.", "warning")

        session["nearest_branch_name"] = branch_name
        session["nearest_branch_distance"] = branch_distance

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO bookings 
            (name, email, vehicle, make, service, notes, date, booking_time, postcode, branch, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, vehicle, make, service, notes, date_val, booking_time, postcode, branch_name, "PENDING"))

        conn.commit()
        conn.close()

        return redirect(url_for("confirm"))

    return render_template("book.html", min_date=date.today())

# -----------------------------
# CONFIRMATION PAGE
# -----------------------------
@app.route("/confirm")
def confirm():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM bookings ORDER BY id DESC LIMIT 1")
    booking = c.fetchone()
    conn.close()

    if not booking:
        return "No booking found", 400

    return render_template(
        "confirm.html",
        booking=booking,
        nearest_branch_name=session.get("nearest_branch_name"),
        nearest_branch_distance=session.get("nearest_branch_distance")
    )

# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))

        flash("Invalid login details.", "danger")

    return render_template("login.html")

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/admin/dashboard")
def dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    search = request.args.get("search", "").lower()
    filter_status = request.args.get("status", "ALL")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    query = "SELECT * FROM bookings WHERE 1=1"
    params = []

    if search:
        query += """ AND (
            LOWER(name) LIKE ? OR
            LOWER(email) LIKE ? OR
            LOWER(vehicle) LIKE ? OR
            LOWER(make) LIKE ? OR
            LOWER(service) LIKE ? OR
            LOWER(postcode) LIKE ? OR
            LOWER(branch) LIKE ?
        )"""
        for _ in range(7):
            params.append(f"%{search}%")

    if filter_status != "ALL":
        query += " AND status=?"
        params.append(filter_status)

    c.execute(query, params)
    bookings = c.fetchall()
    conn.close()

    return render_template(
        "dashboard.html",
        bookings=bookings,
        search=search,
        filter_status=filter_status
    )

# -----------------------------
# EDIT BOOKING
# -----------------------------
@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def edit_booking(id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        vehicle = request.form["vehicle"]
        make = request.form["make"]
        service = request.form["service"]
        notes = request.form["notes"]
        date_val = request.form["date"]
        booking_time = request.form["booking_time"]

        postcode = request.form["postcode"].replace(" ", "").upper()
        status = request.form["status"].upper()

        coords = get_coordinates_from_postcode(postcode)
        branch_name = "UNKNOWN"

        if coords:
            user_lat, user_lon = coords
            nearest_branch, _ = find_nearest_branch(user_lat, user_lon)
            branch_name = nearest_branch["name"]

        c.execute("""
            UPDATE bookings
            SET name=?, email=?, vehicle=?, make=?, service=?, notes=?, date=?, booking_time=?, 
                status=?, postcode=?, branch=?
            WHERE id=?
        """, (name, email, vehicle, make, service, notes, date_val, booking_time,
              status, postcode, branch_name, id))

        conn.commit()
        conn.close()

        flash("Booking updated successfully!", "success")
        return redirect(url_for("dashboard"))

    c.execute("SELECT * FROM bookings WHERE id=?", (id,))
    booking = c.fetchone()
    conn.close()

    return render_template("edit.html", booking=booking)

# -----------------------------
# DELETE BOOKING
# -----------------------------
@app.route("/admin/delete/<int:id>", methods=["POST"])
def delete_booking(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM bookings WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
