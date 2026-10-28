import mysql.connector
from config import DB_CONFIG  # please do remember to modify and rename config.example.py :)


def get_db():
    # New connection per call, from DB_CONFIG
    return mysql.connector.connect(**DB_CONFIG)


def fetch_all(query, params=None):
    # SELECT returning every row as a list of dicts (access columns by name)
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())  # params keep queries parameterized
        return cursor.fetchall()
    finally:
        conn.close() 


def fetch_one(query, params=None):
    # SELECT returning a single row as a dict, or None when nothing matches
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchone()
    finally:
        conn.close()


def execute(query, params=None):
    # INSERT / UPDATE / DELETE; commits on success and returns lastrowid (0 for UPDATE/DELETE)
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()  
        return cursor.lastrowid
    except mysql.connector.Error:
        conn.rollback()  
        raise
    finally:
        conn.close()
