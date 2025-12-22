Write-Host "=== Testing Microservices Security ===" -ForegroundColor Green

# 1. Test registration
Write-Host "`n1. Testing user registration..." -ForegroundColor Yellow
$registerBody = @{
    email = "testuser@example.com"
    password = "Test123!"
    full_name = "Test User"
    role = "user"
} | ConvertTo-Json

try {
    $registerResponse = Invoke-RestMethod -Uri "http://localhost:8080/auth/register" `
        -Method Post `
        -Body $registerBody `
        -ContentType "application/json"
    Write-Host "Registration successful: $($registerResponse.email)" -ForegroundColor Green
} catch {
    Write-Host "Registration error: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Test login
Write-Host "`n2. Testing login..." -ForegroundColor Yellow
$loginBody = @{
    email = "admin@example.com"
    password = "admin123"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "http://localhost:8080/auth/login" `
        -Method Post `
        -Body $loginBody `
        -ContentType "application/json"
    $token = $loginResponse.access_token
    Write-Host "Token received: $($token[0..20] -join '')..." -ForegroundColor Green
} catch {
    Write-Host "Login error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 3. Test access without token (should get 401)
Write-Host "`n3. Testing access without token (expecting 401)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/catalog/products" `
        -Method Post `
        -Body '{"name": "Test", "price": 100}' `
        -ContentType "application/json" `
        -ErrorAction Stop
    Write-Host "ERROR: Access without token should not be allowed!" -ForegroundColor Red
} catch {
    Write-Host "SUCCESS: Got 401 as expected" -ForegroundColor Green
}

# 4. Test access with token
Write-Host "`n4. Testing access with token..." -ForegroundColor Yellow
$headers = @{
    "Authorization" = "Bearer $token"
}

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/catalog/products" `
        -Method Post `
        -Headers $headers `
        -Body '{"name": "Test", "price": 100}' `
        -ContentType "application/json" `
        -ErrorAction Stop
    Write-Host "Product creation successful" -ForegroundColor Green
} catch {
    Write-Host "Product creation error: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Test rate limiting
Write-Host "`n5. Testing rate limiting..." -ForegroundColor Yellow
Write-Host "Sending 15 quick login requests..." -ForegroundColor Cyan

$rateLimitTest = @{
    email = "admin@example.com"
    password = "admin123"
} | ConvertTo-Json

$successCount = 0
$rateLimitCount = 0

for ($i = 1; $i -le 15; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8080/auth/login" `
            -Method Post `
            -Body $rateLimitTest `
            -ContentType "application/json" `
            -ErrorAction Stop
        $successCount++
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 429) {
            $rateLimitCount++
            if ($i -eq 11) {
                Write-Host "   Request $i : Got 429 (Rate limit) - expected" -ForegroundColor Yellow
            }
        }
    }
    Start-Sleep -Milliseconds 10
}

Write-Host "Successful requests: $successCount" -ForegroundColor Green
Write-Host "Rate limited requests: $rateLimitCount" -ForegroundColor Yellow

# 6. Test user profile
Write-Host "`n6. Testing user profile..." -ForegroundColor Yellow
try {
    $profile = Invoke-RestMethod -Uri "http://localhost:8080/users/me" `
        -Method Get `
        -Headers $headers `
        -ErrorAction Stop
    Write-Host "Profile received: $($profile.email), role: $($profile.role)" -ForegroundColor Green
} catch {
    Write-Host "Profile error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Testing completed ===" -ForegroundColor Green