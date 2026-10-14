import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG 

class JobTrackerDB:
    def __init__(self):
        self.connection = None
    
    def connect(self):
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            return True
        except Error as e:
            print(f'Connection error: {e}')
            return False
    
    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def get_all_companies(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM companies')
        return cursor.fetchall()
    
    def get_jobs_by_salary(self, min_salary):
        cursor = self.connection.cursor(dictionary=True)
        query = 'SELECT * FROM jobs WHERE salary_min >= %s'
        cursor.execute(query, (min_salary,))
        return cursor.fetchall()
    # Using cursor(dictionary=True) returns results as dictionaries instead of tuples. 
    # This lets you access columns by name (row['company_name']) instead of position (row[1]). Much more readable!
    def add_application(self, job_id, status='Applied'):
        cursor = self.connection.cursor()
        query = '''INSERT INTO applications (job_id, application_date, status)
                   VALUES (%s, CURDATE(), %s)'''
        cursor.execute(query, (job_id, status))
        self.connection.commit()
        return cursor.lastrowid

# Example usage
if __name__ == '__main__':
    db = JobTrackerDB()
    if db.connect():
        companies = db.get_all_companies()
        print(f'Found {len(companies)} companies')
        for c in companies:
            print(f"  - {c['company_name']}")
        db.disconnect()
