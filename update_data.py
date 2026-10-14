import mysql.connector
from config import DB_CONFIG 

try:
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    # Update application status
    application_id = 1
    new_status = 'Offer'  # must be one of the status ENUM values in schema.sql
    
    update_query = '''
        UPDATE applications 
        SET status = %s 
        WHERE application_id = %s
    '''
    
    cursor.execute(update_query, (new_status, application_id))
    connection.commit()
    
    # Check how many rows were affected
    if cursor.rowcount > 0:
        print(f'Updated {cursor.rowcount} application(s)')
        print(f'Application {application_id} status changed to: {new_status}')
    else:
        print('No applications were updated. Check the ID.')
        
except mysql.connector.Error as error:
    print(f'Error: {error}')
    if 'connection' in locals() and connection.is_connected():  # connect() may have failed
        connection.rollback()
    
finally:
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
