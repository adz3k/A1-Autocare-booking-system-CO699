from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import math
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = 'A1AutoCareSecretKey'


# --------------------------------------
# BRANCH LOCATIONS
# --------------------------------------
BRANCHES = [
    {"name": "Milton Keynes", "lat": 52.0406, "lon": -0.7594},
    {"name": "Wembley", "lat": 51.5530, "lon": -0.2960},
    {"name": "Luton", "lat": 51.8787, "lon": -0.4200},
]


# --------------------------------------
# INITIALISE DATABASE
# --------------------------------------
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


# --------------------------------------
# ADMIN CREDENTIALS
# --------------------------------------
ADMIN_EMAIL = "admin@a1autocare.com"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123")


# --------------------------------------
# POSTCODE TO COORDINATES
# --------------------------------------
def get_coordinates_from_postcode(postcode):
    postcode = postcode.replace(" ", "")

    try:
        res = requests.get(f"https://api.postcodes.io/postcodes/{postcode}")
        data = res.json()

        if data.get("status") == 200:
            return data["result"]["latitude"], data["result"]["longitude"]
        return None

    except Exception:
        return None


# --------------------------------------
# HAVERSINE DISTANCE
# --------------------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(d_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# --------------------------------------
# FIND NEAREST BRANCH
# --------------------------------------
def find_nearest_branch(user_lat, user_lon):
    nearest = None
    shortest = float("inf")

    for branch in BRANCHES:
        dist = calculate_distance(user_lat, user_lon, branch["lat"], branch["lon"])
        if dist < shortest:
            shortest = dist
            nearest = branch

    return nearest, round(shortest, 1)


# --------------------------------------
# ROUTES
# --------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


# --------------------------------------
# BOOKING PAGE
# --------------------------------------
@app.route("/book", methods=["GET", "POST"])
def book():
    if request.method == "POST":

        # ------------------------------
        # SERVER-SIDE VALIDATION
        # ------------------------------
        errors = []

        required_fields = {
            "name": request.form["name"],
            "email": request.form["email"],
            "vehicle": request.form["vehicle"],
            "make": request.form["make"],
            "service": request.form["service"],
            "postcode": request.form["postcode"],
            "date": request.form["date"],
            "booking_time": request.form["booking_time"]
        }

        for field, value in required_fields.items():
            if not value or value.strip() == "":
                errors.append(f"{field.capitalize()} is required.")

        # Email validation
        if "@" not in request.form["email"] or "." not in request.form["email"]:
            errors.append("Please enter a valid email address.")

        # Date validation
        try:
            user_date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            if user_date < date.today():
                errors.append("Booking date cannot be in the past.")
        except:
            errors.append("Invalid date format.")

        # Postcode validation
        if len(request.form["postcode"].replace(" ", "")) < 5:
            errors.append("Please enter a valid UK postcode.")

        # If errors exist
        if errors:
            for err in errors:
                flash(err, "danger")
            return redirect(url_for("book"))

        # ------------------------------
        # SAFE EXTRACTION AFTER VALIDATION
        # ------------------------------
        name = request.form["name"]
        email = request.form["email"]
        vehicle = request.form["vehicle"]
        make = request.form["make"]
        service = request.form["service"]
        notes = request.form["notes"]
        date_val = request.form["date"]
        booking_time = request.form["booking_time"]
        postcode = request.form["postcode"]

        # Postcode → Coordinates
        coords = get_coordinates_from_postcode(postcode)
        branch_name = "Unknown"
        branch_distance = None

        if coords:
            user_lat, user_lon = coords
            nearest_branch, distance_km = find_nearest_branch(user_lat, user_lon)
            branch_name = nearest_branch["name"]
            branch_distance = distance_km
        else:
            flash("Invalid postcode. Could not calculate nearest branch.", "warning")

        # Save in session for confirm page
        session["nearest_branch_name"] = branch_name
        session["nearest_branch_distance"] = branch_distance

        # Insert booking
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO bookings 
            (name, email, vehicle, make, service, notes, date, booking_time, postcode, branch)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, vehicle, make, service, notes, date_val, booking_time, postcode, branch_name))
        conn.commit()
        conn.close()

        return redirect(url_for("confirm"))

    return render_template("book.html", min_date=date.today())


# --------------------------------------
# CONFIRMATION PAGE
# --------------------------------------
@app.route("/confirm")
def confirm():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM bookings ORDER BY id DESC LIMIT 1")
    booking = c.fetchone()
    conn.close()

    if booking is None:
        return "Please complete a booking first.", 400

    return render_template(
        "confirm.html",
        booking=booking,
        nearest_branch_name=session.get("nearest_branch_name"),
        nearest_branch_distance=session.get("nearest_branch_distance"),
    )


# --------------------------------------
# LOGIN
# --------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid credentials.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


# --------------------------------------
# ADMIN DASHBOARD
# --------------------------------------
@app.route("/admin/dashboard")
def dashboard():
    if not session.get("admin_logged_in"):
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM bookings")
    bookings = c.fetchall()
    conn.close()

    return render_template("dashboard.html", bookings=bookings)


# --------------------------------------
# EDIT BOOKING
# --------------------------------------
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
        status = request.form["status"]
        postcode = request.form["postcode"]

        coords = get_coordinates_from_postcode(postcode)
        branch_name = "Unknown"

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

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("dashboard"))

    return render_template("edit.html", booking=booking)


# --------------------------------------
# DELETE BOOKING
# --------------------------------------
@app.route("/admin/delete/<int:id>", methods=["POST"])
def delete_booking(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM bookings WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


# --------------------------------------
# LOGOUT
# --------------------------------------
@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# --------------------------------------
# START APPLICATION
# --------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
