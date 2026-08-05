@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo 서버를 시작합니다... (종료하려면 Ctrl+C)
python main.py
echo.
echo 서버가 종료되었습니다. (이미 실행 중이었다면 위 오류 메시지를 확인하세요)
pause
