#!/bin/bash
# DevSecOps Security Scan Script
# Runs all security tools locally before commit

set -e

echo "🔒 Starting DevSecOps Security Scan..."
echo "============================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Bandit - Python SAST
echo -e "\n${YELLOW}1. Running Bandit (Python SAST)...${NC}"
cd backend
if command -v bandit &> /dev/null; then
    bandit -r . -c .bandit.yml -ll || {
        echo -e "${RED}❌ Bandit found issues${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ Bandit passed${NC}"
else
    echo -e "${YELLOW}⚠️  Bandit not installed, skipping${NC}"
fi
cd ..

# 2. Safety - Python dependency check
echo -e "\n${YELLOW}2. Running Safety (Dependency Check)...${NC}"
cd backend
if command -v safety &> /dev/null; then
    safety check --file requirements.txt || {
        echo -e "${YELLOW}⚠️  Safety found vulnerabilities (review required)${NC}"
    }
else
    echo -e "${YELLOW}⚠️  Safety not installed, skipping${NC}"
fi
cd ..

# 3. NPM Audit
echo -e "\n${YELLOW}3. Running NPM Audit...${NC}"
cd frontend
if [ -f package-lock.json ]; then
    npm audit --audit-level=moderate || {
        echo -e "${YELLOW}⚠️  NPM Audit found vulnerabilities${NC}"
    }
else
    echo -e "${YELLOW}⚠️  No package-lock.json, skipping${NC}"
fi
cd ..

# 4. Semgrep - Multi-language SAST
echo -e "\n${YELLOW}4. Running Semgrep...${NC}"
if command -v semgrep &> /dev/null; then
    semgrep --config p/owasp-top-ten --config p/security-audit \
            --config p/python --config p/django \
            --error backend/ frontend/src/ || {
        echo -e "${RED}❌ Semgrep found issues${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ Semgrep passed${NC}"
else
    echo -e "${YELLOW}⚠️  Semgrep not installed, skipping${NC}"
fi

# 5. Trivy
echo -e "\n${YELLOW}5. Running Trivy (Filesystem)...${NC}"
if command -v trivy &> /dev/null; then
    trivy fs --severity CRITICAL,HIGH . || {
        echo -e "${YELLOW}⚠️  Trivy found issues${NC}"
    }
else
    echo -e "${YELLOW}⚠️  Trivy not installed, skipping${NC}"
fi

# 6. Django security check
echo -e "\n${YELLOW}6. Running Django Security Check...${NC}"
cd backend
if [ -f manage.py ]; then
    python manage.py check --deploy 2>&1 | grep -v "^$" || true
fi
cd ..

echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}✅ DevSecOps Scan Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
