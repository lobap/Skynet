Write-Host "🧹 Cleaning up residual files..." -ForegroundColor Cyan

# Remove local venv if exists
if (Test-Path "venv") {
    Write-Host "Removing venv..." -ForegroundColor Yellow
    Remove-Item -Path "venv" -Recurse -Force
}

# Remove __pycache__
Write-Host "Removing __pycache__..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force

# Remove old scripts
if (Test-Path "fix_memory.sh") {
    Remove-Item "fix_memory.sh" -Force
}

Write-Host "✅ Cleanup complete. Ready for Docker." -ForegroundColor Green
