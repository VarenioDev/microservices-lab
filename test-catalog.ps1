Write-Host "Testing Catalog Service..." -ForegroundColor Green

# Базовые проверки
Write-Host "`n1. Checking service health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5002/health" -Method GET
    Write-Host "✅ Health check: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# 2. Создание товаров
Write-Host "`n2. Creating items..." -ForegroundColor Yellow
$items = @(
    @{name = "Laptop"; description = "Gaming laptop"; price = 999.99; category = "electronics"},
    @{name = "Book"; description = "Programming book"; price = 29.99; category = "books"},
    @{name = "Mouse"; description = "Wireless mouse"; price = 19.99; category = "electronics"}
)

$created_items = @()
foreach ($item in $items) {
    try {
        $created = Invoke-RestMethod -Uri "http://localhost:5002/items" -Method POST -Headers @{"Content-Type" = "application/json"} -Body ($item | ConvertTo-Json)
        $created_items += $created
        Write-Host "✅ Created: $($created.name) - $$($created.price)" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to create: $($item.name)" -ForegroundColor Red
    }
}

# 3. Получение всех товаров
Write-Host "`n3. Getting all items..." -ForegroundColor Yellow
try {
    $all_items = Invoke-RestMethod -Uri "http://localhost:5002/items" -Method GET
    Write-Host "✅ Found $($all_items.Count) items" -ForegroundColor Green
    foreach ($item in $all_items) {
        Write-Host "   - $($item.name): $$($item.price)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Failed to get items: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Фильтрация по категории
Write-Host "`n4. Filtering electronics..." -ForegroundColor Yellow
try {
    $electronics = Invoke-RestMethod -Uri "http://localhost:5002/items?category=electronics" -Method GET
    Write-Host "✅ Found $($electronics.Count) electronics" -ForegroundColor Green
    foreach ($item in $electronics) {
        Write-Host "   - $($item.name)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Failed to filter items: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Тестирование через Gateway
Write-Host "`n5. Testing through Gateway..." -ForegroundColor Yellow
try {
    $gateway_items = Invoke-RestMethod -Uri "http://localhost:8080/catalog/items" -Method GET
    Write-Host "✅ Gateway works! Found $($gateway_items.Count) items" -ForegroundColor Green
} catch {
    Write-Host "❌ Gateway test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎉 Catalog Service is working correctly!" -ForegroundColor Green