#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print banner
echo -e "${GREEN}"
echo "======================================================================"
echo "                Daily Positivity SMS Service Setup"
echo "======================================================================"
echo -e "${NC}"

# Check if running with sudo/root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run this script as root or with sudo${NC}"
    exit 1
fi

# Ensure script is run from project root
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: This script must be run from the project root directory${NC}"
    echo "Please run: ./scripts/setup.sh"
    exit 1
fi

# Check Python installation
echo -e "${YELLOW}Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.9 or higher${NC}"
    exit 1
fi

# Make setup_dev.py executable
chmod +x scripts/setup_dev.py

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install Poetry using pip
echo -e "${YELLOW}Installing Poetry...${NC}"
pip install poetry

# Install required packages for setup
echo -e "${YELLOW}Installing setup requirements...${NC}"
pip install requests psycopg2-binary twilio openai

# Run the Python setup script
echo -e "${YELLOW}Running setup script...${NC}"
./scripts/setup_dev.py

# Deactivate virtual environment
deactivate

echo -e "${GREEN}"
echo "======================================================================"
echo "                        Setup Complete!"
echo "======================================================================"
echo -e "${NC}"
echo "To start development:"
echo "1. Activate the virtual environment: source .venv/bin/activate"
echo "2. Start the development server: poetry run flask run"
echo "3. Start the scheduler: poetry run python -m src.cli schedule_messages"
echo "4. Start the processor: poetry run python -m src.cli process_messages"
echo ""
echo "For more information, see docs/PROJECT_GUIDE.md"
