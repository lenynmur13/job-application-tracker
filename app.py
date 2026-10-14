from flask import Flask, render_template
import mysql.connector
from config import DB_CONFIG 

app = Flask(__name__)

def get_db():
    return mysql.connector.connect(**DB_CONFIG)  # Unpacks the dictionary automatically

@app.route('/')
def dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM companies')
    companies = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', companies=companies)

if __name__ == '__main__':
    app.run(debug=True)