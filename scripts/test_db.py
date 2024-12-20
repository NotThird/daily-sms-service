#!/usr/bin/env python3
import os
import psycopg2
from dotenv import load_dotenv

def main():
    """Show all users in the database."""
    print("Loading environment variables...")
    load_dotenv()
    
    database_url = "postgresql://austin_franklin_user:kZz1yqpwMLlfapljhJTjQgU7E4YTwgNy@dpg-cth7omogph6c73d9brog-a.oregon-postgres.render.com/austin_franklin"
    print(f"\nAttempting to connect to database: {database_url}")
    
    try:
        print("Creating connection...")
        conn = psycopg2.connect(database_url)
        print("Connection successful!")
        
        print("Creating cursor...")
        cur = conn.cursor()
        print("Cursor created!")
        
        # First check if the table exists
        print("\nChecking if recipients table exists...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'recipients'
            );
        """)
        table_exists = cur.fetchone()[0]
        print(f"Recipients table exists: {table_exists}")
        
        if not table_exists:
            print("Recipients table does not exist!")
            return
            
        # Get table structure
        print("\nGetting table structure...")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = 'recipients';
        """)
        columns = cur.fetchall()
        print("\nTable structure:")
        for col in columns:
            print(f"- {col[0]}: {col[1]}")
        
        # Simple query to get all recipients
        print("\nQuerying recipients table...")
        cur.execute("SELECT COUNT(*) FROM recipients;")
        count = cur.fetchone()[0]
        print(f"Total recipients: {count}")
        
        if count > 0:
            print("\nFetching all recipients with their configurations and message history...")
            cur.execute("""
                WITH recent_messages AS (
                    SELECT recipient_id,
                           COUNT(*) as message_count,
                           MAX(sent_at) as last_message_time,
                           STRING_AGG(content, ' | ') as recent_contents
                    FROM message_logs
                    GROUP BY recipient_id
                )
                SELECT r.id, r.phone_number, r.timezone, r.is_active, r.created_at, r.updated_at,
                       uc.name, uc.preferences, uc.personal_info,
                       rm.message_count, rm.last_message_time, rm.recent_contents
                FROM recipients r
                LEFT JOIN user_configs uc ON r.id = uc.recipient_id
                LEFT JOIN recent_messages rm ON r.id = rm.recipient_id
                ORDER BY r.created_at DESC;
            """)
            users = cur.fetchall()
            
            print("\nUsers in database:")
            print("=" * 50)
            for user in users:
                print(f"\nID: {user[0]}")
                print(f"Phone: {user[1]}")
                print(f"Timezone: {user[2]}")
                print(f"Active: {user[3]}")
                print(f"Created: {user[4]}")
                print(f"Updated: {user[5]}")
                print(f"Name: {user[6] if user[6] else 'Not set'}")
                
                print("\nPreferences:")
                if user[7]:  # preferences
                    for k, v in user[7].items():
                        print(f"  {k}: {v}")
                else:
                    print("  No preferences set")
                    
                print("\nPersonal Info:")
                if user[8]:  # personal_info
                    for k, v in user[8].items():
                        print(f"  {k}: {v}")
                else:
                    print("  No personal info set")
                    
                print("\nMessage History:")
                if user[9]:  # message_count
                    print(f"  Total Messages: {user[9]}")
                    print(f"  Last Message: {user[10]}")
                    print("\nRecent Messages:")
                    if user[11]:  # recent_contents
                        for msg in user[11].split(" | "):
                            print(f"  - {msg}")
                else:
                    print("  No messages sent yet")
                print("-" * 30)
        else:
            print("No recipients found in database")
            
        print("\nClosing cursor and connection...")
        cur.close()
        conn.close()
        print("Database connection closed!")
        
    except Exception as e:
        print(f"\nError connecting to database: {str(e)}")
        print("\nPlease verify:")
        print("1. PostgreSQL is running")
        print("2. Database 'daily_positivity' exists")
        print("3. User 'postgres' exists with correct password")
        print("4. PostgreSQL is accepting connections on port 5432")

if __name__ == "__main__":
    main()
