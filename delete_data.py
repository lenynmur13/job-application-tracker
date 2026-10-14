import mysql.connector
from config import DB_CONFIG 

try:
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    # Delete the company we just added (by name to be safe)
    company_name = 'Python Solutions LLC'
    
    # First, show what will be deleted
    cursor.execute('SELECT * FROM companies WHERE company_name = %s', (company_name,))
    to_delete = cursor.fetchall()
    
    if to_delete:
        print(f'About to delete: {to_delete}')
        
        # Perform delete
        delete_query = 'DELETE FROM companies WHERE company_name = %s'
        cursor.execute(delete_query, (company_name,))
        connection.commit()
        
        print(f'Deleted {cursor.rowcount} company(ies)')
    else:
        print('Company not found.')
        
except mysql.connector.Error as error:
    print(f'Error: {error}')
    if 'connection' in locals() and connection.is_connected():  # connect() may have failed
        connection.rollback()
    
finally:
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
