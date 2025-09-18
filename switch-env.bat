@echo off
REM Environment switcher script for Windows
REM Usage: switch-env.bat local|railway

if "%1"=="local" (
    echo Switching to LOCAL environment...
    if exist .env.local (
        copy .env.local .env >nul
        echo ✅ Switched to local development environment
        echo 📝 Using: Docker PostgreSQL + Docker MinIO
    ) else (
        echo ❌ .env.local file not found!
        exit /b 1
    )
) else if "%1"=="railway" (
    echo Switching to RAILWAY environment...
    if exist .env.railway (
        copy .env.railway .env >nul
        echo ✅ Switched to Railway production environment
        echo 📝 Using: Railway PostgreSQL + Railway MinIO
    ) else (
        echo ❌ .env.railway file not found!
        exit /b 1
    )
) else (
    echo Usage: switch-env.bat [local^|railway]
    echo.
    echo Current environment configuration:
    for /f "tokens=2 delims==" %%i in ('findstr "DATABASE_HOST" .env 2^>nul') do echo DATABASE_HOST: %%i
    for /f "tokens=2 delims==" %%i in ('findstr "MINIO_ENDPOINT" .env 2^>nul') do echo MINIO_ENDPOINT: %%i  
    for /f "tokens=2 delims==" %%i in ('findstr "MINIO_SECURE" .env 2^>nul') do echo MINIO_SECURE: %%i
)