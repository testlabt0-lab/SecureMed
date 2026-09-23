#!/usr/bin/env bash
# =====================================================================
#  SecureMed - Local SonarQube Runner (Bash)
# =====================================================================

set -euo pipefail

echo "====================================================================="
echo " SecureMed - Local SonarQube Runner"
echo "====================================================================="

if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker is not running. Please start Docker first."
    exit 1
fi

if ! docker ps --filter "name=sonarqube-local" --format '{{.Names}}' | grep -q "sonarqube-local"; then
    echo "[INFO] Starting SonarQube container on http://localhost:9000 ..."
    docker run -d --name sonarqube-local -p 9000:9000 sonarqube:lts-community
    echo "[INFO] Waiting 30s for SonarQube initialization..."
    sleep 30
else
    echo "[INFO] SonarQube container is already running."
fi

echo ""
echo "SonarQube is accessible at http://localhost:9000"
echo "Credentials: admin / admin"
echo ""
echo "To run the scanner on this repository with your token:"
echo "docker run --rm --network host -v \"\$(pwd):/usr/src\" sonarsource/sonar-scanner-cli \\"
echo "  -Dsonar.projectKey=securemed \\"
echo "  -Dsonar.host.url=http://localhost:9000 \\"
echo "  -Dsonar.token=YOUR_GENERATED_TOKEN"
echo "====================================================================="
