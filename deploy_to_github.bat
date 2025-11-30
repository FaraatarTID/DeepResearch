@echo off
echo ========================================
echo   Deep Research Tool - Streamlit Deploy
echo ========================================
echo.

echo Checking git status...
git status
echo.

echo ========================================
echo Ready to commit and push to GitHub?
echo ========================================
echo.
echo This will:
echo   1. Add all deployment files
echo   2. Commit changes
echo   3. Push to GitHub
echo.
echo After pushing, go to https://share.streamlit.io to deploy!
echo.

set /p confirm="Continue? (y/n): "
if /i "%confirm%" NEQ "y" (
    echo Cancelled.
    exit /b
)

echo.
echo Adding files...
git add .gitignore requirements.txt .python-version .streamlit/ README.md DEPLOYMENT*.md

echo.
echo Committing...
git commit -m "Add Streamlit deployment configuration"

echo.
echo Pushing to GitHub...
git push

echo.
echo ========================================
echo   SUCCESS! Files pushed to GitHub
echo ========================================
echo.
echo Next steps:
echo   1. Go to https://share.streamlit.io
echo   2. Sign in with GitHub
echo   3. Click "New app"
echo   4. Select your repository
echo   5. Set main file to: app.py
echo   6. Add your API keys in Secrets
echo   7. Click Deploy!
echo.
echo See DEPLOYMENT_SUMMARY.md for detailed instructions.
echo.
pause
