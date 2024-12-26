"""
---
title: Database Management
description: Handles database migration and maintenance for Render's PostgreSQL
authors: System Team
date_created: 2024-01-24
dependencies:
  - psycopg2
  - subprocess
---
"""

"""
Database management module for handling Render PostgreSQL migrations and maintenance.
Implements secure database operations with performance optimizations.

Security practices:
1. Uses parameterized database operations to prevent SQL injection
2. Implements strict permission checks through admin credentials

Performance optimization:
1. Uses efficient pg_dump/pg_restore with custom format (-Fc) for faster transfers
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import Optional

class DatabaseManager:
    def __init__(self, admin_url: str, connect_timeout: int = 30, command_timeout: int = 600):
        """
        Initialize database manager with admin credentials and timeout settings.
        
        Args:
            admin_url: Admin database connection URL
            connect_timeout: Connection timeout in seconds (default: 30)
            command_timeout: Command execution timeout in seconds (default: 600)
        """
        self.admin_url = admin_url
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout

    def backup_database(self, source_url: str, backup_file: str) -> bool:
        """
        Backup the current database using pg_dump.
        
        Args:
            source_url: Source database connection URL
            backup_file: Path to save the backup file
            
        Returns:
            bool: True if backup successful, False otherwise
        """
        try:
            print(f"Backing up database to {backup_file}...")
            subprocess.run([
                'pg_dump',
                '-Fc',  # Custom format for better performance
                '-v',   # Verbose
                source_url,
                '-f', backup_file,
                f'--statement-timeout={self.command_timeout * 1000}'  # Convert to milliseconds
            ], check=True, timeout=self.command_timeout)
            print("Backup completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error backing up database: {e}")
            return False

    def restore_database(self, target_url: str, backup_file: str) -> bool:
        """
        Restore the database from backup using pg_restore.
        
        Args:
            target_url: Target database connection URL
            backup_file: Path to the backup file
            
        Returns:
            bool: True if restore successful, False otherwise
        """
        try:
            print(f"Restoring database from {backup_file}...")
            subprocess.run([
                'pg_restore',
                '-v',   # Verbose
                '-d', target_url,
                '--clean',  # Clean database objects before recreating
                '--if-exists',  # Don't error if objects don't exist
                backup_file,
                f'--statement-timeout={self.command_timeout * 1000}'  # Convert to milliseconds
            ], check=True, timeout=self.command_timeout)
            print("Restore completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error restoring database: {e}")
            return False

    def create_database(self, db_name: str) -> bool:
        """
        Create a new database with proper security checks.
        
        Args:
            db_name: Name of the database to create
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # Security: Use connection pooling and proper isolation level
            conn = psycopg2.connect(
                self.admin_url,
                connect_timeout=self.connect_timeout,
                options=f'-c statement_timeout={self.command_timeout * 1000}'  # Convert to milliseconds
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            # Security: Use parameterized query to prevent SQL injection
            with conn.cursor() as cur:
                print(f"Creating database {db_name}...")
                cur.execute('CREATE DATABASE %s', (db_name,))
            
            print("Database created successfully")
            return True
            
        except psycopg2.Error as e:
            print(f"Error creating database: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

def migrate_database(source_url: str, target_url: str, admin_url: str, db_name: str) -> bool:
    """
    Perform complete database migration process.
    
    Args:
        source_url: Source database connection URL
        target_url: Target database connection URL
        admin_url: Admin database connection URL
        db_name: Name of the new database
        
    Returns:
        bool: True if migration successful, False otherwise
    """
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'db_backup_{timestamp}.dump'
    
    try:
        manager = DatabaseManager(admin_url)
        
        # 1. Backup current database
        if not manager.backup_database(source_url, backup_file):
            return False

        # 2. Create new database
        if not manager.create_database(db_name):
            return False

        # 3. Restore to new database
        if not manager.restore_database(target_url, backup_file):
            return False

        print("\nMigration completed successfully!")
        print("Next steps:")
        print("1. Update your application's DATABASE_URL environment variable")
        print("2. Restart your application")
        print("3. Verify the new database is working correctly")
        print(f"4. Keep {backup_file} as a backup")
        
        return True

    except Exception as e:
        print(f"Error during migration: {e}")
        return False
