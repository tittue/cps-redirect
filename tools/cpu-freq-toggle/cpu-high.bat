@echo off
REM CPU 고성능 모드 (100%) - 평소 모드
REM 관리자 권한으로 실행 필요

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] 관리자 권한으로 다시 실행합니다...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 100
powercfg /setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 100
powercfg /setactive SCHEME_CURRENT

echo.
echo [OK] CPU 최대 사용률을 100%%로 설정했습니다. (고성능 모드)
timeout /t 2 >nul
