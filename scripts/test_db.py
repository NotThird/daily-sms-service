#!/usr/bin/env python3
import os
import psycopg2
from dotenv import load_dotenv

def main():
    """Test PostgreSQL database connection."""
    print("Loading environment variables...")
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    print(f"\nTesting connection to: {database_url}")
    
    try:
        # Try to connect
        conn = psycopg2.connect(database_url)
        
        # Get server version
        cur = conn.cursor()
        cur.execute('SELECT version()')
        version = cur.fetchone()[0]
        print(f"\nSuccessfully connected to PostgreSQL")
        print(f"Server version: {version}")
        
        # List all tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cur.fetchall()
        print("\nAvailable tables:")
        for table in tables:
            print(f"- {table[0]}")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\nError connecting to database: {str(e)}")
        print("\nPlease verify:")
        print("1. PostgreSQL is running")
        print("2. Database 'daily_positivity' exists")
        print("3. User 'postgres' exists with correct password")
        print("4. PostgreSQL is accepting connections on port 5432")

if __name__ == "__main__":
    main()
