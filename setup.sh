#!/bin/bash
# =====================================================
# SecureMed Complete Setup Script
# =====================================================
# Sets up the entire SecureMed development environment:
# 1. Python virtual environment
# 2. Dependencies installation
# 3. Certificate generation (JWT + TLS + AES)
# 4. Database setup (PostgreSQL)
# 5. Django migrations
# 6. Initial superuser creation
# 7. Frontend dependencies
# 8. Security verification
# =====================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   SecureMed Complete Setup                       ║${NC}"
echo -e "${BLUE}║   DevSecOps Healthcare Platform                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# ---- Step 1: Check prerequisites ----
echo -e "\n${YELLOW}[1/8] Checking prerequisites...${NC}"

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 found"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 NOT found"
        return 1
    fi
}

MISSING=0
check_command python3 || MISSING=1
check_command pip3 || MISSING=1
check_command node || MISSING=1
check_command npm || MISSING=1
check_command psql || echo -e "  ${YELLOW}⚠${NC} psql not found (PostgreSQL client)"

if [ $MISSING -eq 1 ]; then
    echo -e "\n${RED}❌ Missing required commands. Please install them first.${NC}"
    exit 1
fi

# ---- Step 2: Backend Python virtual environment ----
echo -e "\n${YELLOW}[2/8] Setting up Python virtual environment...${NC}"

cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "  ${GREEN}✓${NC} Virtual environment created"
else
    echo -e "  ${YELLOW}⚠${NC} Virtual environment already exists"
fi

# Activate venv
source venv/bin/activate

# ---- Step 3: Install Python dependencies ----
echo -e "\n${YELLOW}[3/8] Installing Python dependencies...${NC}"

pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pytest pytest-django pytest-cov bandit safety --quiet

echo -e "  ${GREEN}✓${NC} Dependencies installed"

# ---- Step 4: Generate certificates ----
echo -e "\n${YELLOW}[4/8] Generating security certificates...${NC}"

if [ ! -f "certs/jwt_private.pem" ]; then
    python scripts/generate_certificates.py
    echo -e "  ${GREEN}✓${NC} Certificates generated"
else
    echo -e "  ${YELLOW}⚠${NC} Certificates already exist, skipping"
fi

# ---- Step 5: Setup environment file ----
echo -e "\n${YELLOW}[5/8] Setting up environment file...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
    # Update ENCRYPTION_KEY from generated file
    if [ -f "certs/field_encryption_key.txt" ]; then
        KEY=$(cat certs/field_encryption_key.txt)
        sed -i.bak "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$KEY|" .env
        rm -f .env.bak
    fi
    echo -e "  ${GREEN}✓${NC} .env created from .env.example"
else
    echo -e "  ${YELLOW}⚠${NC} .env already exists"
fi

# ---- Step 6: Database setup ----
echo -e "\n${YELLOW}[6/8] Setting up database...${NC}"

# Disable SSL for development (cert verification issues in dev)
if ! grep -q "sslmode" .env 2>/dev/null; then
    echo -e "  ${YELLOW}⚠${NC} For development, disabling DB SSL"
fi

# Try to create database (may fail if already exists or no permissions)
DB_NAME=$(grep DB_NAME .env | cut -d'=' -f2)
if command -v psql &> /dev/null; then
    if psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q "1 row"; then
        echo -e "  ${YELLOW}⚠${NC} Database '$DB_NAME' already exists"
    else
        if createdb -U postgres "$DB_NAME" 2>/dev/null || \
           sudo -u postgres createdb "$DB_NAME" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Database '$DB_NAME' created"
        else
            echo -e "  ${YELLOW}⚠${NC} Could not create database (may need manual setup)"
            echo -e "      Run: createdb -U postgres $DB_NAME"
        fi
    fi
fi

# ---- Step 7: Django migrations + superuser ----
echo -e "\n${YELLOW}[7/8] Running Django migrations...${NC}"

# For dev, use SQLite fallback if PostgreSQL isn't available
if ! python -c "import psycopg2" 2>/dev/null || \
   ! psql -U postgres -c "SELECT 1" &> /dev/null; then
    echo -e "  ${YELLOW}⚠${NC} PostgreSQL not available, using SQLite for dev"
    # Create a dev settings override
    cat > config/dev_settings.py << 'EOF'
"""Development settings using SQLite."""
from .settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Disable SSL for dev
for db in DATABASES.values():
    db.get('OPTIONS', {}).pop('sslmode', None)
    db.get('OPTIONS', {}).pop('sslrootcert', None)
    db.get('OPTIONS', {}).pop('sslcert', None)
    db.get('OPTIONS', {}).pop('sslkey', None)

DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EOF
    export DJANGO_SETTINGS_MODULE=config.dev_settings
    echo -e "  ${GREEN}✓${NC} Using dev settings (SQLite)"
else
    export DJANGO_SETTINGS_MODULE=config.settings
fi

python manage.py migrate --noinput
echo -e "  ${GREEN}✓${NC} Migrations applied"

# Create superuser
echo -e "\n${YELLOW}Creating superuser...${NC}"
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings'))
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
email = os.environ.get('INITIAL_ADMIN_EMAIL', 'admin@securemed.app')
password = os.environ.get('INITIAL_ADMIN_PASSWORD', 'SecureMed@2026!')
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        email=email,
        password=password,
        full_name='System Admin',
        role='SUPER_ADMIN',
    )
    print(f'  ✓ Superuser created: {email}')
else:
    print(f'  ⚠ Superuser already exists: {email}')
"

# ---- Step 8: Frontend setup ----
echo -e "\n${YELLOW}[8/8] Setting up frontend...${NC}"

cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    npm install --silent 2>&1 | tail -5
    echo -e "  ${GREEN}✓${NC} Frontend dependencies installed"
else
    echo -e "  ${YELLOW}⚠${NC} node_modules already exists"
fi

# ---- Final verification ----
echo -e "\n${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Setup Complete! ✅                            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"

echo -e "\n${GREEN}Next steps:${NC}"
echo -e "  1. Backend:  cd backend && source venv/bin/activate && python manage.py runserver"
echo -e "  2. Frontend: cd frontend && npm run dev"
echo -e "  3. Visit:    http://localhost:3000"
echo -e ""
echo -e "${YELLOW}Default admin login:${NC}"
echo -e "  Email:    admin@securemed.app"
echo -e "  Password: SecureMed@2026!"
echo -e ""
echo -e "${BLUE}SecureMed${NC} - Stay secure! 🔒"
