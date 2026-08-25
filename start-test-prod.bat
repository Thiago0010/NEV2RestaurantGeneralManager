@echo off
REM =============================================================
REM start-test-prod.bat
REM Sobe ambiente de teste em modo PRODUÇÃO no Windows
REM Simula exatamente o que vai rodar no Render
REM
REM Uso: Duplo clique ou .\start-test-prod.bat no PowerShell
REM =============================================================

setlocal enabledelayedexpansion
chcp 65001 >nul

echo.
echo ============================================================
echo   [NEV]2 - Modo Teste Producao (simula Render)
echo ============================================================
echo.

REM --- Caminho base ---
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

REM --- 1. Verifica Docker ---
echo [1/7] Verificando Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Docker nao encontrado. Instale o Docker Desktop.
    pause
    exit /b 1
)
echo      OK

REM --- 2. Sobe Postgres + Redis ---
echo.
echo [2/7] Limpando containers/conflitos antigos...
docker container prune -f >nul 2>&1
docker compose -f docker-compose.test.yml down --remove-orphans -v >nul 2>&1
echo      Subindo Postgres + Redis em Docker (volume limpo)...
docker compose -f docker-compose.test.yml up -d
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao subir Postgres/Redis.
    pause
    exit /b 1
)

REM --- 3. Espera Postgres ficar pronto ---
echo.
echo [3/7] Aguardando Postgres ficar pronto...
:wait_pg
docker exec nev2-postgres-test pg_isready -U nev2_test >nul 2>&1
if %errorlevel% neq 0 (
    echo      esperando...
    timeout /t 2 >nul
    goto wait_pg
)
echo      Postgres OK!

REM --- 4. Build do frontend (modo prod) ---
echo.
echo [4/7] Buildando o frontend (modo producao)...
if not exist "node_modules" (
    echo      Instalando dependencias npm...
    call npm install
)
set VITE_API_URL=/api/v1
set VITE_WS_URL=/ws
call npm run build
if %errorlevel% neq 0 (
    echo [ERRO] Falha no build do frontend.
    pause
    exit /b 1
)
echo      Frontend buildado em dist/

REM --- 5. Prepara o backend ---
echo.
echo [5/7] Preparando backend...
if not exist "backend\.venv" (
    echo      Criando virtualenv Python...
    cd backend
    python -m venv .venv
    cd ..
)
call backend\.venv\Scripts\activate.bat
echo      Instalando dependencias Python...
pip install -r backend\requirements.txt >nul
echo      OK

REM --- 6. Roda migrations ---
echo.
echo [6/7] Rodando migrations do banco (Alembic)...
set ENV_FILE=..\.env.test
cd backend
set ENV_FILE=..\.env.test
alembic upgrade head
if %errorlevel% neq 0 (
    echo [ERRO] Falha nas migrations.
    cd ..
    pause
    exit /b 1
)
cd ..
echo      Migrations OK!

REM --- 7. Sobe o backend em modo producao ---
echo.
echo [7/7] Subindo backend em modo PRODUCAO (sem reload)...
echo.
echo ============================================================
echo   Tudo pronto!
echo.
echo   Frontend: http://localhost/dist  (servido pelo Vite)
echo   Backend:  http://localhost:8000
echo   Docs API: http://localhost:8000/docs
echo.
echo   OU use o nginx pra simular EXATAMENTE o Render:
echo     Instale o nginx local e use o nginx.test.conf
echo.
echo   Para parar tudo, rode stop-test-prod.bat
echo ============================================================
echo.

REM --- Sobe backend (foreground,Ctrl+C pra parar) ---
set ENV_FILE=..\.env.test
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
