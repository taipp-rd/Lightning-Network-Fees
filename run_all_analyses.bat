@echo off
REM Run all Lightning Network fee analysis scripts (Windows)
REM
REM Usage:
REM   run_all_analyses.bat HOST PORT DB USER PASS
REM
REM Example:
REM   run_all_analyses.bat localhost 5432 lndb readonly secret

setlocal enabledelayedexpansion

if "%~5"==" " (
    echo Usage: %0 HOST PORT DB USER PASS
    echo Example: %0 localhost 5432 lndb readonly secret
    exit /b 1
)

set HOST=%1
set PORT=%2
set DB=%3
set USER=%4
set PASS=%5

echo ==========================================
echo Lightning Network Fee Analysis Suite
echo ==========================================
echo Database: %USER%@%HOST%:%PORT%/%DB%
echo Start time: %date% %time%
echo.

REM Create output directory
for /f "tokens=1-3 delims=/: " %%a in ("%date% %time%") do (
    set OUTPUT_DIR=results_%%c%%a%%b_%%d%%e%%f
)
set OUTPUT_DIR=%OUTPUT_DIR: =0%
mkdir "%OUTPUT_DIR%" 2>nul
echo Output directory: %OUTPUT_DIR%
echo.

REM 1. Base Fee Analysis
echo [1/4] Running Base Fee Analysis...
python 1_base_fee_analysis.py --pg-host "%HOST%" --pg-port "%PORT%" --pg-db "%DB%" --pg-user "%USER%" --pg-pass "%PASS%" --output "%OUTPUT_DIR%\1_base_fee_distribution.png"
if errorlevel 1 (
    echo ERROR: Base fee analysis failed
    exit /b 1
)
echo. Base fee analysis complete
echo.

REM 2. Proportional Fee Rate Analysis
echo [2/4] Running Proportional Fee Rate Analysis...
python 2_fee_rate_analysis.py --pg-host "%HOST%" --pg-port "%PORT%" --pg-db "%DB%" --pg-user "%USER%" --pg-pass "%PASS%" --output "%OUTPUT_DIR%\2_fee_rate_distribution.png"
if errorlevel 1 (
    echo ERROR: Proportional fee rate analysis failed
    exit /b 1
)
echo. Proportional fee rate analysis complete
echo.

REM 3. Inbound Base Fee Analysis
echo [3/4] Running Inbound Base Fee Analysis...
python 3_inbound_base_fee_analysis.py --pg-host "%HOST%" --pg-port "%PORT%" --pg-db "%DB%" --pg-user "%USER%" --pg-pass "%PASS%" --output "%OUTPUT_DIR%\3_inbound_base_fee_distribution.png"
if errorlevel 1 (
    echo ERROR: Inbound base fee analysis failed
    exit /b 1
)
echo. Inbound base fee analysis complete
echo.

REM 4. Inbound Proportional Fee Rate Analysis
echo [4/4] Running Inbound Proportional Fee Rate Analysis...
python 4_inbound_feerate_analysis.py --pg-host "%HOST%" --pg-port "%PORT%" --pg-db "%DB%" --pg-user "%USER%" --pg-pass "%PASS%" --output "%OUTPUT_DIR%\4_inbound_feerate_distribution.png"
if errorlevel 1 (
    echo ERROR: Inbound proportional fee rate analysis failed
    exit /b 1
)
echo. Inbound proportional fee rate analysis complete
echo.

echo ==========================================
echo All analyses completed successfully!
echo Results saved to: %OUTPUT_DIR%
echo End time: %date% %time%
echo ==========================================
echo.
echo Generated files:
dir "%OUTPUT_DIR%"

endlocal
