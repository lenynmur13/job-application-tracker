import mysql.connector
from config import DB_CONFIG 

try:
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    # Get minimum salary from user
    min_salary = 70000  # You can change this value
    
    # SAFE: Parameterized query (prevents SQL injection)
    query = 'SELECT job_title, salary_min, salary_max FROM jobs WHERE salary_min >= %s'
    cursor.execute(query, (min_salary,))  # Note the comma - it's a tuple!
    
    jobs = cursor.fetchall()
    
    print(f'=== Jobs with salary >= ${min_salary:,} ===')
    print(f'Found {len(jobs)} jobs')
    print()
    
    for job in jobs:
        title, sal_min, sal_max = job
        fmt = lambda v: f'${v:,.0f}' if v is not None else 'N/A'  # salaries are nullable
        print(f'{title}: {fmt(sal_min)} - {fmt(sal_max)}')
        
except mysql.connector.Error as error:
    print(f'Error: {error}')
    
finally:
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
