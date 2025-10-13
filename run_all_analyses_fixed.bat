@echo off
REM Run all Lightning Network fee analysis scripts (Fixed version)
REM
REM Usage:
REM   run_all_analyses_fixed.bat HOST PORT DB USER PASS
REM
REM Example:
REM   run_all_analyses_fixed.bat localhost 5432 lndb readonly secret

setlocal enabledelayedexpansion

if "%~5"=="" (
    echo Usage: %~nx0 HOST PORT DB USER PASS
    echo Example: %~nx0 localhost 5432 lndb readonly secret
    exit /b 1
)

set HOST=%~1
set PORT=%~2
set DB=%~3
set USER=%~4
set PASS=%~5

echo ==========================================
echo Lightning Network Fee Analysis Suite (Fixed)
echo ==========================================
echo Database: %USER%@%HOST%:%PORT%/%DB%
echo Start time: %date% %time%
echo.

REM Test database connection first
echo [TEST] Testing database connection...
python -c "import psycopg2; conn = psycopg2.connect(host='%HOST%', port=%PORT%, dbname='%DB%', user='%USER%', password='%PASS%', connect_timeout=10); conn.close(); print('Database connection successful')" 2>nul
if errorlevel 1 (
    echo [ERROR] Cannot connect to database. Please check your credentials.
    exit /b 1
)
echo Database connection OK
echo.

REM Create output directory
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set OUTPUT_DIR=results_fixed_%TIMESTAMP%
mkdir "%OUTPUT_DIR%" 2>nul
echo Output directory: %OUTPUT_DIR%
echo.

set TOTAL=4
set SUCCESS=0
set FAILED=0

REM 1. Base Fee Analysis (Fixed)
if exist "1_base_fee_analysis_fixed.py" (
    echo [1/4] Running Base Fee Analysis...
    python 1_base_fee_analysis_fixed.py --pg-host %HOST% --pg-port %PORT% --pg-db %DB% --pg-user %USER% --pg-pass %PASS% --output "%OUTPUT_DIR%\1_base_fee_distribution_fixed.png" > "%OUTPUT_DIR%\1_base_fee_log.txt" 2>&1
    if errorlevel 1 (
        echo [X] Base fee analysis failed
        set /a FAILED+=1
    ) else (
        echo [OK] Base fee analysis complete
        set /a SUCCESS+=1
    )
) else (
    echo [WARN] 1_base_fee_analysis_fixed.py not found, skipping...
)
echo.

REM 2. Proportional Fee Rate Analysis (Fixed)
if exist "2_fee_rate_analysis_fixed.py" (
    echo [2/4] Running Proportional Fee Rate Analysis...
    python 2_fee_rate_analysis_fixed.py --pg-host %HOST% --pg-port %PORT% --pg-db %DB% --pg-user %USER% --pg-pass %PASS% --output "%OUTPUT_DIR%\2_fee_rate_distribution_fixed.png" > "%OUTPUT_DIR%\2_fee_rate_log.txt" 2>&1
    if errorlevel 1 (
        echo [X] Proportional fee rate analysis failed
        set /a FAILED+=1
    ) else (
        echo [OK] Proportional fee rate analysis complete
        set /a SUCCESS+=1
    )
) else (
    echo [WARN] 2_fee_rate_analysis_fixed.py not found, skipping...
)
echo.

REM 3. Inbound Base Fee Analysis
if exist "3_inbound_base_fee_analysis.py" (
    echo [3/4] Running Inbound Base Fee Analysis...
    python 3_inbound_base_fee_analysis.py --pg-host %HOST% --pg-port %PORT% --pg-db %DB% --pg-user %USER% --pg-pass %PASS% --output "%OUTPUT_DIR%\3_inbound_base_fee_distribution.png" > "%OUTPUT_DIR%\3_inbound_base_fee_log.txt" 2>&1
    if errorlevel 1 (
        echo [X] Inbound base fee analysis failed
        set /a FAILED+=1
    ) else (
        echo [OK] Inbound base fee analysis complete
        set /a SUCCESS+=1
    )
) else (
    echo [WARN] 3_inbound_base_fee_analysis.py not found, skipping...
)
echo.

REM 4. Inbound Proportional Fee Rate Analysis
if exist "4_inbound_feerate_analysis.py" (
    echo [4/4] Running Inbound Proportional Fee Rate Analysis...
    python 4_inbound_feerate_analysis.py --pg-host %HOST% --pg-port %PORT% --pg-db %DB% --pg-user %USER% --pg-pass %PASS% --output "%OUTPUT_DIR%\4_inbound_feerate_distribution.png" > "%OUTPUT_DIR%\4_inbound_feerate_log.txt" 2>&1
    if errorlevel 1 (
        echo [X] Inbound proportional fee rate analysis failed
        set /a FAILED+=1
    ) else (
        echo [OK] Inbound proportional fee rate analysis complete
        set /a SUCCESS+=1
    )
) else (
    echo [WARN] 4_inbound_feerate_analysis.py not found, skipping...
)
echo.

echo ==========================================
echo Analysis Summary
echo ==========================================
echo Successful: %SUCCESS%/%TOTAL%
echo Failed:     %FAILED%/%TOTAL%
echo Results saved to: %OUTPUT_DIR%
echo End time: %date% %time%
echo ==========================================
echo.

echo Generated files:
dir /B "%OUTPUT_DIR%\*.png" 2>nul
echo.
echo Log files:
dir /B "%OUTPUT_DIR%\*_log.txt" 2>nul

if %FAILED% gtr 0 (
    echo.
    echo [WARNING] Some analyses failed. Check log files for details.
    exit /b 1
)

exit /b 0
