import mysql.connector
from config import DB_CONFIG 

try:
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    # New company data
    new_company = {
        'name': 'Python Solutions LLC',
        'industry': 'Software Development',
        'website': 'www.pythonsolutions.com',
        'city': 'Miami',
        'state': 'Florida'
    }
    
    # Insert query with parameterized values
    insert_query = '''
        INSERT INTO companies (company_name, industry, website, city, state)
        VALUES (%s, %s, %s, %s, %s)
    '''
    
    values = (new_company['name'], new_company['industry'], 
              new_company['website'], new_company['city'], new_company['state'])
    
    cursor.execute(insert_query, values)
    
    # IMPORTANT: Commit the transaction! otherwise changes lost when connection closes
    connection.commit()
    
    print(f'Company added successfully!')
    print(f'New company ID: {cursor.lastrowid}')
    
except mysql.connector.Error as error:
    print(f'Error: {error}')
    if 'connection' in locals() and connection.is_connected():  # connect() may have failed
        connection.rollback()
    
finally:
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
