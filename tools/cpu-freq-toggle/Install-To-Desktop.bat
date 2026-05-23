@echo off
REM Install-To-Desktop.bat
REM   VBS 파일들을 사용자 바탕화면에 복사. 더블클릭 한 번이면 끝.
REM   재실행해도 안전 (덮어쓰기).

setlocal
chcp 65001 >nul 2>&1

set "SRC=%~dp0"
set "DST=%USERPROFILE%\Desktop\CPU Freq Toggle"

echo.
echo  [CPU Freq Toggle - 바탕화면 설치]
echo  소스: %SRC%
echo  대상: %DST%
echo.

if not exist "%DST%" (
    mkdir "%DST%"
)

copy /Y "%SRC%cpu-low.vbs"    "%DST%\" >nul
copy /Y "%SRC%cpu-mid.vbs"    "%DST%\" >nul
copy /Y "%SRC%cpu-high.vbs"   "%DST%\" >nul
copy /Y "%SRC%cpu-toggle.vbs" "%DST%\" >nul

if exist "%SRC%cpu_freq.py" (
    copy /Y "%SRC%cpu_freq.py"     "%DST%\" >nul
    copy /Y "%SRC%cpu-low-py.vbs"  "%DST%\" >nul
    copy /Y "%SRC%cpu-high-py.vbs" "%DST%\" >nul
)

echo  [OK] 바탕화면의 "CPU Freq Toggle" 폴더에 설치되었습니다.
echo.
echo  사용법:
echo    - cpu-low.vbs    : CPU 50%% (살치 모드)
echo    - cpu-mid.vbs    : CPU 80%% (보통)
echo    - cpu-high.vbs   : CPU 100%% (고성능, 평소 모드)
echo    - cpu-toggle.vbs : 50%% ↔ 100%% 자동 토글
echo.
echo  더블클릭 시 관리자 권한 요청이 한 번 뜹니다.
echo.
pause
