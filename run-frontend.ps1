# Windows PowerShell script to run React frontend
# Run this in a separate PowerShell window

Write-Host "Starting React frontend dev server..." -ForegroundColor Green
Write-Host "Frontend will be available at http://localhost:5173" -ForegroundColor Cyan
Write-Host "API requests will be proxied to Django at http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host ""

cd frontend
npm run dev