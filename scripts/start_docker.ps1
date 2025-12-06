Write-Host "🚀 Initializing Skynet Hive-Mind Protocol..." -ForegroundColor Cyan

# 1. Check if Ollama is running on host
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Head -ErrorAction Stop
    Write-Host "✅ Ollama is online." -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama is NOT running on localhost:11434." -ForegroundColor Red
    Write-Host "Please start Ollama and try again." -ForegroundColor Yellow
    exit 1
}

# 2. Pull required models (Hive-Mind) - Smart Check
Write-Host "🧠 Synchronizing Neural Networks..." -ForegroundColor Cyan

function Check-And-Pull ($model) {
    $list = ollama list
    if ($list -match $model) {
        Write-Host "   - ✅ $model already exists." -ForegroundColor Green
    } else {
        Write-Host "   - ⬇️ Pulling $model..." -ForegroundColor Yellow
        ollama pull $model
    }
}

Check-And-Pull "llama3.2:latest"
Check-And-Pull "deepseek-r1:8b"
Check-And-Pull "qwen2.5-coder:7b"

# 3. Start Docker Environment
Write-Host "🐳 Deploying Containerized Infrastructure..." -ForegroundColor Cyan
Set-Location "$PSScriptRoot/.."
docker-compose -f docker/docker-compose.yml up --build
