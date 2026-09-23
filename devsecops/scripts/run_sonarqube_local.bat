@echo off
echo =====================================================================
echo  SecureMed - Local SonarQube Runner
echo =====================================================================
echo.

:: 1. Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    exit /b 1
)

:: 2. Check if SonarQube container is already up
docker ps --filter "name=sonarqube-local" --format "{{.Names}}" | findstr "sonarqube-local" >nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Starting SonarQube container on http://localhost:9000 ...
    docker run -d --name sonarqube-local -p 9000:9000 sonarqube:lts-community
    echo [INFO] Waiting 30 seconds for SonarQube server to initialize...
    timeout /t 30 /nobreak
) else (
    echo [INFO] SonarQube container is already running.
)

echo.
echo =====================================================================
echo [INFO] Ready to scan!
echo Open your browser to: http://localhost:9000
echo Login: admin / admin (change password on first login if prompted).
echo Create a project named 'securemed' and generate a token.
echo.
echo Once you have your token, run the scanner via Docker:
echo.
echo docker run --rm --network host -v "%cd%:/usr/src" sonarsource/sonar-scanner-cli -Dsonar.projectKey=securemed -Dsonar.host.url=http://localhost:9000 -Dsonar.token=YOUR_GENERATED_TOKEN
echo =====================================================================
pause
