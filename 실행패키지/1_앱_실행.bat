@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 통합 앱을 실행합니다 (포트 8501)...
echo 브라우저에서 http://localhost:8501 이 열립니다.
echo 왼쪽 사이드바에서 '조회 대시보드', '네트워크 분석', '감시 리스트'를 전환하세요.
python -m streamlit run 통합앱.py --server.port 8501
pause
