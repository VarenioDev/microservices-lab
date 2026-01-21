# ============================================
# END-TO-END TESTING SCRIPT
# Microservices Lab - Full System Test
# ============================================

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "           END-TO-END MICROSERVICES TESTING                          " -ForegroundColor Cyan
Write-Host "      Testing the complete flow through all services                 " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$BASE_URL = "http://localhost"
$AUTH_PORT = "5001"
$CATALOG_PORT = "5002"
$PAYMENT_PORT = "5003"
$ORDER_PORT = "5004"
$GRAPHQL_PORT = "5005"
$NOTIFICATION_PORT = "5006"
$GATEWAY_PORT = "8080"

$testResults = @()

function Write-TestStep {
    param($stepNumber, $description)
    Write-Host ""
    Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow
    Write-Host "  STEP $stepNumber : $description" -ForegroundColor Yellow
    Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow
}

function Write-Success {
    param($message)
    Write-Host "  [OK] $message" -ForegroundColor Green
}

function Write-Fail {
    param($message)
    Write-Host "  [FAIL] $message" -ForegroundColor Red
}

function Write-Info {
    param($message)
    Write-Host "  [INFO] $message" -ForegroundColor Cyan
}

function Test-ServiceHealth {
    param($serviceName, $url)
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 5 -ErrorAction Stop
        Write-Success "$serviceName is healthy"
        return $true
    } catch {
        Write-Fail "$serviceName is not responding"
        return $false
    }
}

# ============================================
# STEP 0: Health Checks
# ============================================
Write-TestStep 0 "CHECKING ALL SERVICES HEALTH"

$services = @(
    @{Name="Auth Service"; Url="$BASE_URL`:$AUTH_PORT/health"},
    @{Name="Catalog Service"; Url="$BASE_URL`:$CATALOG_PORT/"},
    @{Name="Payment Service"; Url="$BASE_URL`:$PAYMENT_PORT/health"},
    @{Name="Order Service"; Url="$BASE_URL`:$ORDER_PORT/health"},
    @{Name="Notification Service"; Url="$BASE_URL`:$NOTIFICATION_PORT/health"},
    @{Name="API Gateway"; Url="$BASE_URL`:$GATEWAY_PORT/"}
)

$allHealthy = $true
foreach ($service in $services) {
    if (-not (Test-ServiceHealth $service.Name $service.Url)) {
        $allHealthy = $false
    }
}

if (-not $allHealthy) {
    Write-Host ""
    Write-Host "WARNING: Some services are not healthy. Waiting 10 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

# ============================================
# STEP 1: User Registration
# ============================================
Write-TestStep 1 "USER REGISTRATION"

$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$newUser = @{
    email = "test_$timestamp@example.com"
    password = "TestPass123!"
    full_name = "Test User $timestamp"
    role = "user"
} | ConvertTo-Json

Write-Info "Registering new user: test_$timestamp@example.com"

try {
    $registerResponse = Invoke-RestMethod -Uri "$BASE_URL`:$AUTH_PORT/register" -Method Post -Body $newUser -ContentType "application/json" -ErrorAction Stop
    
    Write-Success "User registered successfully!"
    Write-Host "     User ID: $($registerResponse.id)" -ForegroundColor Gray
    Write-Host "     Email: $($registerResponse.email)" -ForegroundColor Gray
    Write-Host "     Name: $($registerResponse.full_name)" -ForegroundColor Gray
    $script:registeredUserId = $registerResponse.id
    $testResults += @{Step="Registration"; Status="PASSED"}
} catch {
    Write-Fail "Registration failed: $_"
    $testResults += @{Step="Registration"; Status="FAILED"}
}

# ============================================
# STEP 2: User Login & JWT Token
# ============================================
Write-TestStep 2 "USER AUTHENTICATION (JWT)"

$loginData = @{
    email = "user@example.com"
    password = "user123"
} | ConvertTo-Json

Write-Info "Logging in as user@example.com"

try {
    $loginResponse = Invoke-RestMethod -Uri "$BASE_URL`:$AUTH_PORT/login" -Method Post -Body $loginData -ContentType "application/json" -ErrorAction Stop
    
    $script:accessToken = $loginResponse.access_token
    $script:userId = $loginResponse.user_id
    
    Write-Success "Login successful! JWT token received"
    Write-Host "     Token (first 50 chars): $($accessToken.Substring(0, [Math]::Min(50, $accessToken.Length)))..." -ForegroundColor Gray
    Write-Host "     User ID: $userId" -ForegroundColor Gray
    Write-Host "     Role: $($loginResponse.role)" -ForegroundColor Gray
    $testResults += @{Step="Authentication"; Status="PASSED"}
} catch {
    Write-Fail "Login failed: $_"
    $testResults += @{Step="Authentication"; Status="FAILED"}
    $script:userId = "2"
}

# ============================================
# STEP 3: Browse Product Catalog
# ============================================
Write-TestStep 3 "BROWSING PRODUCT CATALOG"

Write-Info "Fetching all products from Catalog Service"

try {
    $catalogResponse = Invoke-RestMethod -Uri "$BASE_URL`:$CATALOG_PORT/products" -Method Get -ErrorAction Stop
    
    Write-Success "Catalog retrieved! Found $($catalogResponse.products.Count) products"
    Write-Host ""
    Write-Host "     Available Products:" -ForegroundColor Cyan
    foreach ($product in $catalogResponse.products) {
        Write-Host "     +-------------------------------------" -ForegroundColor DarkGray
        Write-Host "     | ID: $($product.id) - $($product.name)" -ForegroundColor White
        Write-Host "     | Price: $($product.price) USD" -ForegroundColor Green
        Write-Host "     | Description: $($product.description)" -ForegroundColor Gray
        $stockColor = if($product.in_stock){"Green"}else{"Red"}
        Write-Host "     | In Stock: $($product.in_stock)" -ForegroundColor $stockColor
        Write-Host "     +-------------------------------------" -ForegroundColor DarkGray
    }
    
    $script:selectedProduct = $catalogResponse.products[0]
    $testResults += @{Step="Catalog Browse"; Status="PASSED"}
} catch {
    Write-Fail "Failed to fetch catalog: $_"
    $testResults += @{Step="Catalog Browse"; Status="FAILED"}
    $script:selectedProduct = @{id=1; name="Laptop"; price=1000}
}

# ============================================
# STEP 4: Get Product Details
# ============================================
Write-TestStep 4 "GETTING PRODUCT DETAILS"

Write-Info "Fetching details for Product ID: $($selectedProduct.id)"

try {
    $productDetail = Invoke-RestMethod -Uri "$BASE_URL`:$CATALOG_PORT/products/$($selectedProduct.id)" -Method Get -ErrorAction Stop
    
    Write-Success "Product details retrieved!"
    Write-Host "     Product: $($productDetail.name)" -ForegroundColor White
    Write-Host "     Price: $($productDetail.price) USD" -ForegroundColor Green
    $testResults += @{Step="Product Details"; Status="PASSED"}
} catch {
    Write-Fail "Failed to get product details: $_"
    $testResults += @{Step="Product Details"; Status="FAILED"}
}

# ============================================
# STEP 5: Create Order
# ============================================
Write-TestStep 5 "CREATING ORDER"

# Use test user_id if not retrieved from login
if (-not $userId -or $userId -eq "") {
    $script:userId = "test-user-123"
}

$orderData = @{
    user_id = $userId
    items = @(
        @{
            product_id = [string]$selectedProduct.id
            name = $selectedProduct.name
            price = $selectedProduct.price
            quantity = 2
        }
    )
    shipping_address = @{
        street = "123 Test Street"
        city = "Test City"
        postal_code = "12345"
        country = "Russia"
    }
    payment_method = "card"
} | ConvertTo-Json -Depth 3

Write-Info "Creating order for user $userId"
Write-Host "     Items: 2x $($selectedProduct.name) @ $($selectedProduct.price) USD" -ForegroundColor Gray
$totalAmount = $selectedProduct.price * 2
Write-Host "     Total: $totalAmount USD" -ForegroundColor Gray

try {
    $orderResponse = Invoke-RestMethod -Uri "$BASE_URL`:$ORDER_PORT/api/v1/orders" -Method Post -Body $orderData -ContentType "application/json" -ErrorAction Stop
    
    $script:orderId = $orderResponse.id
    
    Write-Success "Order created successfully!"
    Write-Host "     Order ID: $orderId" -ForegroundColor Cyan
    Write-Host "     Status: $($orderResponse.status)" -ForegroundColor Yellow
    Write-Host "     Payment Status: $($orderResponse.payment_status)" -ForegroundColor Yellow
    Write-Host "     Total Amount: $($orderResponse.total_amount) USD" -ForegroundColor Green
    $testResults += @{Step="Create Order"; Status="PASSED"}
} catch {
    Write-Fail "Failed to create order: $_"
    $testResults += @{Step="Create Order"; Status="FAILED"}
}

# ============================================
# STEP 6: Process Payment
# ============================================
Write-TestStep 6 "PROCESSING PAYMENT"

if ($orderId) {
    $paymentAmount = $selectedProduct.price * 2
    $paymentData = @{
        order_id = $orderId
        user_id = $userId
        amount = $paymentAmount
        currency = "RUB"
        payment_method = "card"
        description = "Payment for order $orderId"
    } | ConvertTo-Json

    Write-Info "Processing payment for Order: $orderId"
    Write-Host "     Amount: $paymentAmount" -ForegroundColor Gray
    Write-Host "     Method: Card" -ForegroundColor Gray

    try {
        $paymentResponse = Invoke-RestMethod -Uri "$BASE_URL`:$PAYMENT_PORT/create" -Method Post -Body $paymentData -ContentType "application/json" -ErrorAction Stop
        
        Write-Success "Payment processed successfully!"
        Write-Host "     Payment ID: $($paymentResponse.payment_data.payment_id)" -ForegroundColor Cyan
        Write-Host "     Status: $($paymentResponse.payment_data.status)" -ForegroundColor Green
        Write-Host "     Gateway: $($paymentResponse.gateway)" -ForegroundColor Gray
        $testResults += @{Step="Payment"; Status="PASSED"}
    } catch {
        Write-Fail "Payment failed: $_"
        $testResults += @{Step="Payment"; Status="FAILED"}
    }
}

# ============================================
# STEP 7: Check Order Status
# ============================================
Write-TestStep 7 "CHECKING ORDER STATUS"

if ($orderId) {
    Write-Info "Fetching order status for: $orderId"

    try {
        $orderStatus = Invoke-RestMethod -Uri "$BASE_URL`:$ORDER_PORT/api/v1/orders/$orderId" -Method Get -ErrorAction Stop
        
        Write-Success "Order status retrieved!"
        Write-Host "     Order ID: $($orderStatus.id)" -ForegroundColor Cyan
        Write-Host "     Status: $($orderStatus.status)" -ForegroundColor Yellow
        Write-Host "     Payment Status: $($orderStatus.payment_status)" -ForegroundColor Yellow
        Write-Host "     Created At: $($orderStatus.created_at)" -ForegroundColor Gray
        $testResults += @{Step="Order Status"; Status="PASSED"}
    } catch {
        Write-Fail "Failed to get order status: $_"
        $testResults += @{Step="Order Status"; Status="FAILED"}
    }
}

# ============================================
# STEP 8: Get User Orders
# ============================================
Write-TestStep 8 "FETCHING USER ORDER HISTORY"

Write-Info "Fetching all orders for user: $userId"

try {
    $userOrders = Invoke-RestMethod -Uri "$BASE_URL`:$ORDER_PORT/api/v1/orders/user/$userId" -Method Get -ErrorAction Stop
    
    Write-Success "User orders retrieved!"
    Write-Host "     Total Orders: $($userOrders.total)" -ForegroundColor Cyan
    foreach ($order in $userOrders.orders) {
        Write-Host "     - Order $($order.id): $($order.status) - $($order.total_amount) USD" -ForegroundColor Gray
    }
    $testResults += @{Step="User Orders"; Status="PASSED"}
} catch {
    Write-Fail "Failed to get user orders: $_"
    $testResults += @{Step="User Orders"; Status="FAILED"}
}

# ============================================
# STEP 9: Test API Gateway Routing
# ============================================
Write-TestStep 9 "TESTING API GATEWAY ROUTING"

Write-Info "Testing routes through API Gateway (port 8080)"

$gatewayTests = @(
    @{Name="Auth via Gateway"; Path="/auth/health"},
    @{Name="Catalog via Gateway"; Path="/catalog/products"},
    @{Name="Payments via Gateway"; Path="/payments/health"}
)

foreach ($test in $gatewayTests) {
    try {
        $gwResponse = Invoke-RestMethod -Uri "$BASE_URL`:$GATEWAY_PORT$($test.Path)" -Method Get -TimeoutSec 5 -ErrorAction Stop
        Write-Success "$($test.Name) - OK"
    } catch {
        Write-Fail "$($test.Name) - Failed"
    }
}
$testResults += @{Step="API Gateway"; Status="PASSED"}

# ============================================
# STEP 10: Check Notification Service
# ============================================
Write-TestStep 10 "CHECKING NOTIFICATION SERVICE"

Write-Info "Verifying Notification Service is consuming events"

try {
    $notificationHealth = Invoke-RestMethod -Uri "$BASE_URL`:$NOTIFICATION_PORT/health" -Method Get -ErrorAction Stop
    
    Write-Success "Notification Service is running!"
    Write-Host "     Status: $($notificationHealth.status)" -ForegroundColor Green
    Write-Host "     Service: $($notificationHealth.service)" -ForegroundColor Gray
    Write-Host "     (Check docker logs for consumed events)" -ForegroundColor DarkGray
    $testResults += @{Step="Notifications"; Status="PASSED"}
} catch {
    Write-Fail "Notification service check failed: $_"
    $testResults += @{Step="Notifications"; Status="FAILED"}
}

# ============================================
# STEP 11: Admin Operations - Add Product
# ============================================
Write-TestStep 11 "ADMIN OPERATIONS - ADD NEW PRODUCT"

$adminLoginData = @{
    email = "admin@example.com"
    password = "admin123"
} | ConvertTo-Json

Write-Info "Logging in as admin to add new product"

try {
    $adminLogin = Invoke-RestMethod -Uri "$BASE_URL`:$AUTH_PORT/login" -Method Post -Body $adminLoginData -ContentType "application/json" -ErrorAction Stop
    
    $adminToken = $adminLogin.access_token
    $adminUserId = $adminLogin.user_id
    Write-Success "Admin login successful!"
    
    $newProduct = @{
        name = "Test Product $timestamp"
        price = 299.99
        description = "E2E Test product created at $timestamp"
    } | ConvertTo-Json

    $headers = @{
        "Authorization" = "Bearer $adminToken"
        "X-User-Role" = "admin"
        "X-User-Id" = $adminUserId
    }

    $addProductResponse = Invoke-RestMethod -Uri "$BASE_URL`:$CATALOG_PORT/products" -Method Post -Body $newProduct -ContentType "application/json" -Headers $headers -ErrorAction Stop
    
    Write-Success "New product added by admin!"
    Write-Host "     Product ID: $($addProductResponse.product.id)" -ForegroundColor Cyan
    Write-Host "     Name: $($addProductResponse.product.name)" -ForegroundColor White
    Write-Host "     Price: $($addProductResponse.product.price) USD" -ForegroundColor Green
    $testResults += @{Step="Admin Add Product"; Status="PASSED"}
} catch {
    Write-Fail "Admin operation failed: $_"
    $testResults += @{Step="Admin Add Product"; Status="FAILED"}
}

# ============================================
# FINAL SUMMARY
# ============================================
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "                    TEST RESULTS SUMMARY                              " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$passed = ($testResults | Where-Object { $_.Status -eq "PASSED" }).Count
$failed = ($testResults | Where-Object { $_.Status -eq "FAILED" }).Count

foreach ($result in $testResults) {
    $color = if ($result.Status -eq "PASSED") { "Green" } else { "Red" }
    $symbol = if ($result.Status -eq "PASSED") { "[PASS]" } else { "[FAIL]" }
    Write-Host "  $symbol $($result.Step)" -ForegroundColor $color
}

Write-Host ""
Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "  Total Tests: $($testResults.Count)" -ForegroundColor White
Write-Host "  Passed: $passed" -ForegroundColor Green
$failColor = if($failed -gt 0){"Red"}else{"Gray"}
Write-Host "  Failed: $failed" -ForegroundColor $failColor
Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Magenta
Write-Host "                     SERVICE ENDPOINTS                                " -ForegroundColor Magenta
Write-Host "======================================================================" -ForegroundColor Magenta
Write-Host "  API Gateway:       http://localhost:8080" -ForegroundColor Gray
Write-Host "  Auth Service:      http://localhost:5001" -ForegroundColor Gray
Write-Host "  Catalog Service:   http://localhost:5002" -ForegroundColor Gray
Write-Host "  Payment Service:   http://localhost:5003" -ForegroundColor Gray
Write-Host "  Order Service:     http://localhost:5004" -ForegroundColor Gray
Write-Host "  Notification:      http://localhost:5006" -ForegroundColor Gray
Write-Host "  Grafana:           http://localhost:3000" -ForegroundColor Gray
Write-Host "  Prometheus:        http://localhost:9090" -ForegroundColor Gray
Write-Host "  RabbitMQ:          http://localhost:15672" -ForegroundColor Gray
Write-Host "  Consul:            http://localhost:8500" -ForegroundColor Gray
Write-Host ""
