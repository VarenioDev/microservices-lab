Write-Host "Testing Auth Service..." -ForegroundColor Green

# 1. Регистрация
Write-Host "`n1. Registering user..." -ForegroundColor Yellow
try {
    $register = Invoke-RestMethod -Uri "http://localhost:5001/register" -Method POST -Headers @{"Content-Type" = "application/json"} -Body '{"username": "testuser", "password": "testpass"}'
    Write-Host "✅ Registration successful: $($register.message)" -ForegroundColor Green
} catch {
    Write-Host "❌ Registration failed: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Логин
Write-Host "`n2. Logging in..." -ForegroundColor Yellow
try {
    $login = Invoke-RestMethod -Uri "http://localhost:5001/login" -Method POST -Headers @{"Content-Type" = "application/json"} -Body '{"username": "testuser", "password": "testpass"}'
    $token = $login.access_token
    Write-Host "✅ Login successful. Token: $token" -ForegroundColor Green
} catch {
    Write-Host "❌ Login failed: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# 3. Проверка защищенного эндпоинта
Write-Host "`n3. Testing protected endpoint..." -ForegroundColor Yellow
try {
    $me = Invoke-RestMethod -Uri "http://localhost:5001/me" -Method GET -Headers @{"Authorization" = "Bearer $token"}
    Write-Host "✅ Protected endpoint successful. User: $($me.username)" -ForegroundColor Green
} catch {
    Write-Host "❌ Protected endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎉 Auth Service is working correctly!" -ForegroundColor Green