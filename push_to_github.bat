@echo off
chcp 65001 >nul
REM =============================================================
REM  SecureMed - Upload project to GitHub using GitHub CLI (Windows)
REM  Usage:
REM    push_to_github.bat                 -^> repo name: SecureMed (private)
REM    push_to_github.bat MyName          -^> repo name: MyName (private)
REM    push_to_github.bat MyName public   -^> repo name: MyName (public)
REM =============================================================
setlocal
set REPO_NAME=%1
if "%REPO_NAME%"=="" set REPO_NAME=SecureMed
set VISIBILITY=%2
if "%VISIBILITY%"=="" set VISIBILITY=private

echo ==========================================
echo   SecureMed -^> GitHub  (%REPO_NAME%, %VISIBILITY%)
echo ==========================================

where git >nul 2>nul
if errorlevel 1 (
  echo [X] Git is not installed. Download: https://git-scm.com
  goto :eof
)
where gh >nul 2>nul
if errorlevel 1 (
  echo [X] GitHub CLI is not installed. Run:  winget install GitHub.cli
  echo     or download from: https://cli.github.com
  goto :eof
)

gh auth status >nul 2>nul
if errorlevel 1 (
  echo Login to GitHub required...
  gh auth login
)

git init 2>nul
git branch -M main 2>nul
git add .

git diff --cached --quiet
if errorlevel 1 (
  git commit -m "SecureMed: Django backend + React frontend + AI service + Android + docs"
) else (
  echo No new changes to commit.
)

git remote get-url origin >nul 2>nul
if errorlevel 1 (
  gh repo create %REPO_NAME% --%VISIBILITY% --source=. --remote=origin --push
  echo ==========================================
  echo   Done! Repository created and pushed.
  echo ==========================================
) else (
  git push -u origin main
  echo ==========================================
  echo   Done! Repository updated.
  echo ==========================================
)
endlocal
