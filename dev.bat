@echo off
echo ================================================
echo EduStream AI - Development Server
echo ================================================

:: Start Docker services
echo.
echo Starting Docker services...
docker compose up -d --wait

echo Docker services ready!

:: Setup backend
echo.
echo Setting up backend...
cd backend

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate
pip install -r requirements.txt -q

:: Copy .env if needed
if not exist ".env" (
    if exist "..\.env.example" (
        copy "..\.env.example" ".env" >nul
        echo Created .env from .env.example
    )
)

:: Run migrations (create tables)
echo Running database migrations...
python -m alembic upgrade head 2>nul

cd ..

:: Setup frontend
echo.
echo Setting up frontend...
cd frontend
if not exist "node_modules" (
    echo Installing npm dependencies...
    call npm install
)
cd ..

:: Start servers
echo.
echo ================================================
echo Starting servers...
echo ================================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo Close both windows to stop servers.
echo.

:: Start backend in new window
start "EduStream Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --reload"

:: Start frontend in new window
start "EduStream Frontend" cmd /k "cd frontend && npm run dev"

echo Servers started in separate windows.