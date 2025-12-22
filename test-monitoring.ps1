Write-Host "=== Testing Monitoring Stack ===" -ForegroundColor Green

# 1. Проверяем доступность сервисов мониторинга
Write-Host "`n1. Checking monitoring services..." -ForegroundColor Yellow

$services = @(
    @{Name="Prometheus"; Url="http://localhost:9090"},
    @{Name="Grafana"; Url="http://localhost:3000"},
    @{Name="Jaeger"; Url="http://localhost:16686"},
    @{Name="Loki"; Url="http://localhost:3100/ready"}
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri $service.Url -Method Get -TimeoutSec 10
        Write-Host "   $($service.Name) is running" -ForegroundColor Green
    }
    catch {
        Write-Host "   $($service.Name) is NOT running: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 2. Проверяем Loki API
Write-Host "`n2. Checking Loki API..." -ForegroundColor Yellow
try {
    $lokiReady = Invoke-RestMethod -Uri "http://localhost:3100/ready" -Method Get -TimeoutSec 5
    Write-Host "   Loki API is ready" -ForegroundColor Green
}
catch {
    Write-Host "   Loki API is not ready" -ForegroundColor Red
}

# 3. Проверяем метрики микросервисов
Write-Host "`n3. Checking microservices health..." -ForegroundColor Yellow

$microservices = @(
    @{Name="auth-service"; Url="http://localhost:5001/health"},
    @{Name="catalog-service"; Url="http://localhost:5002/health"},
    @{Name="order-service"; Url="http://localhost:5004/health"},
    @{Name="payment-service"; Url="http://localhost:5003/health"}
)

foreach ($service in $microservices) {
    try {
        $response = Invoke-RestMethod -Uri $service.Url -Method Get -TimeoutSec 5
        Write-Host "   $($service.Name) is healthy" -ForegroundColor Green
    }
    catch {
        Write-Host "   $($service.Name) is NOT healthy: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 4. Проверяем API Gateway
Write-Host "`n4. Checking API Gateway..." -ForegroundColor Yellow
try {
    $gateway = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get -TimeoutSec 5
    Write-Host "   API Gateway is working" -ForegroundColor Green
}
catch {
    Write-Host "   API Gateway error: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Создаем тестовый запрос для трассировки
Write-Host "`n5. Creating test request for tracing..." -ForegroundColor Yellow
try {
    # Получаем токен
    $loginBody = @{
        email = "admin@example.com"
        password = "admin123"
    }
    
    $jsonBody = $loginBody | ConvertTo-Json
    
    $loginResponse = Invoke-RestMethod -Uri "http://localhost:8080/auth/login" -Method Post -Body $jsonBody -ContentType "application/json"
    $token = $loginResponse.access_token
    
    Write-Host "   Got JWT token: $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Green
    
    # Делаем запрос к order-service
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    
    $orders = Invoke-RestMethod -Uri "http://localhost:8080/catalog/products" -Method Get -Headers $headers -TimeoutSec 5
    Write-Host "   Successfully called catalog service API" -ForegroundColor Green
    
}
catch {
    Write-Host "   Test request failed: $($_.Exception.Message)" -ForegroundColor Red
}

# 6. Инструкции по использованию
Write-Host "`n6. Monitoring Dashboard URLs:" -ForegroundColor Magenta
Write-Host "   Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor Cyan
Write-Host "   Prometheus: http://localhost:9090" -ForegroundColor Cyan
Write-Host "   Jaeger UI: http://localhost:16686" -ForegroundColor Cyan
Write-Host "   Loki: http://localhost:3100 (API only)" -ForegroundColor Cyan
Write-Host "   API Gateway: http://localhost:8080" -ForegroundColor Cyan

Write-Host "`n=== Monitoring Test Completed ===" -ForegroundColor Green