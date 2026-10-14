@echo off
title MediaCrawler WebUI (port 8090)
cd /d "%~dp0.."
echo ============================================
echo  MediaCrawler WebUI
echo  URL: http://127.0.0.1:8090
echo  (default 8080 is taken by the Strata LLM service)
echo ============================================
echo.
uv run uvicorn api.main:app --host 127.0.0.1 --port 8090
echo.
echo Server stopped. Press any key to close.
pause >nul
