@echo off
REM Script to run tests with coverage measurement
REM Usage: run_tests_with_coverage.bat

echo ========================================
echo Running SolarSense SCADA Test Suite
echo with Coverage Measurement
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install/upgrade pytest-cov if needed
echo Checking pytest-cov installation...
pip install pytest-cov>=4.0 --quiet

REM Run tests with coverage
echo.
echo Running tests...
pytest

REM Check exit code
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Tests completed successfully!
    echo ========================================
    echo.
    echo Coverage report generated in htmlcov/index.html
    echo Opening coverage report...
    start htmlcov\index.html
) else (
    echo.
    echo ========================================
    echo Tests failed or coverage below 80%%
    echo ========================================
    echo.
    echo Check the output above for details.
)

pause
