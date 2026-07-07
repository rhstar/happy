@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   최초 설치 (처음 한 번만)
echo ============================================
echo.
echo 필요한 패키지를 설치합니다. 몇 분 걸릴 수 있습니다.
echo.
python -m pip install --upgrade pip
python -m pip install streamlit pyvis pandas openpyxl networkx lxml
echo.
echo 설치 완료! 이제 1_앱_실행.bat 으로 실행하세요.
pause
