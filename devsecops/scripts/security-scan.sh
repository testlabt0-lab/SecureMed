#!/bin/bash
# DevSecOps Security Scan Script
# Runs all security tools locally before commit
#
# Every tool here is expected to be installed; a scan that "passes" while it
# skipped half its tools is worse than a red X, because the badge claims a
# posture that was never measured. Missing tools therefore FAIL the scan by
# default. Set SCAN_ALLOW_MISSING=1 to keep the historical skip-and-warn
# behaviour for a quick local run — never in CI.
#
# Usage:
#   ./devsecops/scripts/security-scan.sh                # strict (default)
#   SCAN_ALLOW_MISSING=1 ./devsecops/scripts/security-scan.sh

set -e

ALLOW_MISSING="${SCAN_ALLOW_MISSING:-0}"

require_tool() {
    # require_tool <binary> <install hint>
    if command -v "$1" &> /dev/null; then
        return 0
    fi
    if [ "$ALLOW_MISSING" = "1" ]; then
        echo -e "${YELLOW}⚠️  $1 not installed, skipping (SCAN_ALLOW_MISSING=1)${NC}"
        return 1
    fi
    echo -e "${RED}❌ $1 is not installed. Install: $2${NC}"
    echo -e "${RED}   (or run with SCAN_ALLOW_MISSING=1 to skip explicitly)${NC}"
    exit 1
}

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
if require_tool bandit "pip install 'bandit>=1.7,<2'"; then
    bandit -r . -c .bandit.yml -ll || {
        echo -e "${RED}❌ Bandit found issues${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ Bandit passed${NC}"
fi
cd ..

# 2. Safety - Python dependency check
echo -e "\n${YELLOW}2. Running Safety (Dependency Check)...${NC}"
cd backend
if require_tool safety "pip install 'safety>=3,<4'"; then
    safety check --file requirements.txt || {
        echo -e "${YELLOW}⚠️  Safety found vulnerabilities (review required)${NC}"
    }
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
if require_tool semgrep "pip install 'semgrep>=1.60,<2'"; then
    semgrep --config p/owasp-top-ten --config p/security-audit \
            --config p/python --config p/django \
            --error backend/ frontend/src/ || {
        echo -e "${RED}❌ Semgrep found issues${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ Semgrep passed${NC}"
fi

# 5. Trivy
echo -e "\n${YELLOW}5. Running Trivy (Filesystem)...${NC}"
if require_tool trivy "https://trivy.dev/latest/getting-started/installation/"; then
    trivy fs --severity CRITICAL,HIGH . || {
        echo -e "${YELLOW}⚠️  Trivy found issues${NC}"
    }
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
