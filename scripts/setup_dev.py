#!/usr/bin/env python3
import os
import sys
import subprocess
import requests
import json
from pathlib import Path
import time
import psycopg2
from twilio.rest import Client
import openai

def print_step(message):
    """Print a formatted step message."""
    print("\n" + "="*80)
    print(f">>> {message}")
    print("="*80)

def check_python_version():
    """Verify Python version meets requirements."""
    print_step("Checking Python version")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Error: Python 3.9 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print("✅ Python version OK")

def check_poetry_installation():
    """Verify Poetry is installed and install if missing."""
    print_step("Checking Poetry installation")
    try:
        subprocess.run(["poetry", "--version"], check=True, capture_output=True)
        print("✅ Poetry is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Poetry not found. Installing...")
        try:
            subprocess.run(
                ["curl", "-sSL", "https://install.python-poetry.org", "|", "python3", "-"],
                check=True
            )
            print("✅ Poetry installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing Poetry: {e}")
            sys.exit(1)

def setup_virtual_environment():
    """Create and configure virtual environment."""
    print_step("Setting up virtual environment")
    try:
        subprocess.run(["poetry", "install"], check=True)
        print("✅ Virtual environment created and dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up virtual environment: {e}")
        sys.exit(1)

def check_environment_variables():
    """Verify all required environment variables are set."""
    print_step("Checking environment variables")
    required_vars = [
        'DATABASE_URL',
        'OPENAI_API_KEY',
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_FROM_NUMBER'
    ]
    
    missing_vars = []
    env_file = Path('.env')
    
    if not env_file.exists():
        print("Creating .env file from template...")
        template = Path('.env.example').read_text()
        env_file.write_text(template)
        print("Please edit .env file with your credentials")
        sys.exit(1)
    
    # Load .env file
    with env_file.open() as f:
        env_contents = f.read()
        for var in required_vars:
            if var not in env_contents or f"{var}=" in env_contents:
                missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        sys.exit(1)
    
    print("✅ Environment variables configured")

def verify_database_connection():
    """Test database connection."""
    print_step("Verifying database connection")
    try:
        # Get database URL from environment
        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

def verify_openai_api():
    """Test OpenAI API connection."""
    print_step("Verifying OpenAI API connection")
    try:
        openai.api_key = os.getenv('OPENAI_API_KEY')
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10
        )
        print("✅ OpenAI API connection successful")
    except Exception as e:
        print(f"❌ OpenAI API connection failed: {e}")
        sys.exit(1)

def verify_twilio_api():
    """Test Twilio API connection."""
    print_step("Verifying Twilio API connection")
    try:
        client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        # Just verify the account
        client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
        print("✅ Twilio API connection successful")
    except Exception as e:
        print(f"❌ Twilio API connection failed: {e}")
        sys.exit(1)

def run_database_migrations():
    """Run database migrations."""
    print_step("Running database migrations")
    try:
        subprocess.run(["poetry", "run", "alembic", "upgrade", "head"], check=True)
        print("✅ Database migrations completed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Database migration failed: {e}")
        sys.exit(1)

def run_tests():
    """Run test suite."""
    print_step("Running tests")
    try:
        subprocess.run(["poetry", "run", "pytest"], check=True)
        print("✅ All tests passed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed: {e}")
        sys.exit(1)

def setup_git_hooks():
    """Set up Git pre-commit hooks."""
    print_step("Setting up Git hooks")
    hooks_dir = Path(".git/hooks")
    if not hooks_dir.exists():
        print("Git not initialized. Skipping hooks setup.")
        return
    
    pre_commit = hooks_dir / "pre-commit"
    hook_content = """#!/bin/sh
poetry run black . --check
poetry run flake8 .
poetry run pytest
"""
    
    pre_commit.write_text(hook_content)
    pre_commit.chmod(0o755)
    print("✅ Git hooks configured")

def verify_local_server():
    """Start local server and verify it's running."""
    print_step("Verifying local server")
    try:
        # Start server in background
        server = subprocess.Popen(
            ["poetry", "run", "flask", "run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(2)
        
        # Check health endpoint
        response = requests.get("http://localhost:5000/health")
        response.raise_for_status()
        
        print("✅ Local server running correctly")
    except Exception as e:
        print(f"❌ Local server verification failed: {e}")
    finally:
        if 'server' in locals():
            server.terminate()

def main():
    """Run all setup and verification steps."""
    try:
        check_python_version()
        check_poetry_installation()
        setup_virtual_environment()
        check_environment_variables()
        verify_database_connection()
        verify_openai_api()
        verify_twilio_api()
        run_database_migrations()
        run_tests()
        setup_git_hooks()
        verify_local_server()
        
        print("\n" + "="*80)
        print("🎉 Development environment setup complete!")
        print("="*80)
        print("\nNext steps:")
        print("1. Review the documentation in docs/PROJECT_GUIDE.md")
        print("2. Start the development server: poetry run flask run")
        print("3. Start the scheduler: poetry run python -m src.cli schedule_messages")
        print("4. Start the processor: poetry run python -m src.cli process_messages")
        
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
