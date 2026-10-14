import mysql.connector
from config import DB_CONFIG 

try:
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    # Fetch all companies
    cursor.execute('SELECT company_id, company_name, industry, city FROM companies')
    # Get all results
    companies = cursor.fetchall()
    
    print('=== All Companies ===')
    print(f'Total companies: {len(companies)}')
    print()
    
    for company in companies:
        company_id, name, industry, city = company
        print(f'ID: {company_id} | {name} | {industry} | {city}')
        
except mysql.connector.Error as error:
    print(f'Error: {error}')
    
finally:
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
