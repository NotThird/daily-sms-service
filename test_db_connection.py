import psycopg2
from psycopg2 import OperationalError

def test_connection():
    try:
        # Connect to the database
        connection = psycopg2.connect(
            database="daily_positivity",
            user="postgres",
            password="postgres123",
            host="localhost",
            port="5432"
        )
        
        print("Successfully connected to PostgreSQL!")
        
        # Create a cursor
        cursor = connection.cursor()
        
        # Execute a simple query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"PostgreSQL version: {version[0]}")
        
        cursor.close()
        connection.close()
        
    except OperationalError as e:
        print(f"Error connecting to PostgreSQL: {e}")

if __name__ == "__main__":
    test_connection()
