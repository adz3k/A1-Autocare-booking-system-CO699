from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

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
            additional notes TEXT,
            date TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

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

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bookings (name, email, vehicle, make, service, additional_notes, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, vehicle, make, service, notes, date))
        conn.commit()
        conn.close()

        return redirect(url_for('confirmation'))
    
    return render_template('book.html')

@app.route('/confirmation')
def confirmation():
    return render_template('confirm.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)