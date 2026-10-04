# Windows PowerShell startup script for Requisition Portal
# Run this in PowerShell: .\run.ps1

# Load environment variables from .env file
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Host "Loaded environment from .env" -ForegroundColor Green
} else {
    Write-Warning "No .env file found - using defaults"
    $env:DJANGO_SECRET_KEY = "django-insecure-dev-key-change-in-production-abc123xyz"
    $env:DJANGO_DEBUG = "True"
    $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
    $env:DB_ENGINE = "django.db.backends.sqlite3"
    $env:DB_NAME = "db.sqlite3"
    $env:DJANGO_BASE_URL = "http://127.0.0.1:8000"
}

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated" -ForegroundColor Green
} else {
    Write-Error "Virtual environment not found. Run: python -m venv venv"
    exit 1
}

# Run migrations
Write-Host "Running migrations..." -ForegroundColor Cyan
python manage.py migrate

# Collect static files
Write-Host "Collecting static files..." -ForegroundColor Cyan
python manage.py collectstatic --noinput

# Start server
Write-Host "Starting server at http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
python manage.py runserver