from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

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
            INSERT INTO bookings (name, email, vehicle, make, service, additional_notes, date,      booking_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, vehicle, make, service, notes, date, booking_time))
        conn.commit()
        conn.close()

        return redirect(url_for('confirmation'))
    
    return render_template('book.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/confirmation')
def confirmation():
    return render_template('confirm.html')

# -----------------------------
# RUN APPLICATION
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
