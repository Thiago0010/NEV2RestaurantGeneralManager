@echo off
REM =============================================================
REM stop-test-prod.bat
REM Para tudo: backend (janela aberta) + Docker (Postgres/Redis)
REM =============================================================

echo.
echo Parando ambiente de teste...

REM --- Para o backend (procura a janela do uvicorn) ---
echo - Encerrando processo do backend (uvicorn)...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*" 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *uvicorn*" 2>nul
taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /IM python.exe 2>nul

REM --- Para Postgres + Redis ---
echo - Parando Postgres e Redis (Docker)...
docker compose -f docker-compose.test.yml down

echo.
echo Ambiente parado.
echo.
pause
