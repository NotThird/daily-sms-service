#!/usr/bin/env python
"""
Database migration script for Render's free tier PostgreSQL.
Handles the required 90-day database recreation process.
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def backup_database(source_url, backup_file):
    """Backup the current database using pg_dump."""
    try:
        print(f"Backing up database to {backup_file}...")
        subprocess.run([
            'pg_dump',
            '-Fc',  # Custom format
            '-v',   # Verbose
            source_url,
            '-f', backup_file
        ], check=True)
        print("Backup completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error backing up database: {e}")
        return False

def restore_database(target_url, backup_file):
    """Restore the database from backup using pg_restore."""
    try:
        print(f"Restoring database from {backup_file}...")
        subprocess.run([
            'pg_restore',
            '-v',   # Verbose
            '-d', target_url,
            '--clean',  # Clean (drop) database objects before recreating
            '--if-exists',  # Don't error if objects don't exist
            backup_file
        ], check=True)
        print("Restore completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restoring database: {e}")
        return False

def create_database(admin_url, db_name):
    """Create a new database."""
    try:
        conn = psycopg2.connect(admin_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        print(f"Creating database {db_name}...")
        cur.execute(f'CREATE DATABASE {db_name}')
        
        cur.close()
        conn.close()
        print("Database created successfully")
        return True
    except psycopg2.Error as e:
        print(f"Error creating database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Migrate Render PostgreSQL database')
    parser.add_argument('--source-url', required=True, help='Source database URL')
    parser.add_argument('--target-url', required=True, help='Target database URL')
    parser.add_argument('--admin-url', required=True, help='Admin database URL (for creating new DB)')
    parser.add_argument('--db-name', required=True, help='New database name')
    args = parser.parse_args()

    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'db_backup_{timestamp}.dump'

    try:
        # 1. Backup current database
        if not backup_database(args.source_url, backup_file):
            sys.exit(1)

        # 2. Create new database
        if not create_database(args.admin_url, args.db_name):
            sys.exit(1)

        # 3. Restore to new database
        if not restore_database(args.target_url, backup_file):
            sys.exit(1)

        print("\nMigration completed successfully!")
        print("Next steps:")
        print("1. Update your application's DATABASE_URL environment variable")
        print("2. Restart your application")
        print(f"3. Verify the new database is working correctly")
        print(f"4. Keep {backup_file} as a backup")

    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)
    finally:
        # Keep the backup file for safety
        if os.path.exists(backup_file):
            print(f"\nBackup file saved as: {backup_file}")

if __name__ == '__main__':
    main()
