import requests
import time
import json

def test_http_endpoints():
    """Тестирование HTTP endpoints с Circuit Breaker"""
    base_url = "http://localhost:5000"
    
    print("Testing HTTP endpoints with Circuit Breaker...")
    print("=" * 60)
    
    # Тест создания платежа
    for i in range(10):
        payment_data = {
            "order_id": f"test_order_{i}",
            "user_id": f"user_{i}",
            "amount": 100.0 + i*5,
            "currency": "USD",
            "payment_method": "card"
        }
        
        try:
            response = requests.post(
                f"{base_url}/create",
                json=payment_data,
                timeout=5
            )
            
            result = response.json()
            
            if "fallback" in str(result).lower():
                print(f"Request {i}: FALLBACK - Circuit Breaker triggered")
            else:
                print(f"Request {i}: SUCCESS - {result.get('gateway')}")
                
        except Exception as e:
            print(f"Request {i}: ERROR - {str(e)}")
        
        time.sleep(0.5)
    
    # Проверка статуса Circuit Breaker'ов
    print("\nCircuit Breaker Status:")
    response = requests.get(f"{base_url}/circuit-breaker/status")
    print(json.dumps(response.json(), indent=2))

def monitor_circuit_breaker():
    """Мониторинг состояния Circuit Breaker'ов"""
    base_url = "http://localhost:5000"
    
    print("\nMonitoring Circuit Breaker states...")
    print("=" * 60)
    
    for i in range(30):
        response = requests.get(f"{base_url}/circuit-breaker/status")
        data = response.json()
        
        print(f"Time: {time.strftime('%H:%M:%S')}")
        for cb in data["circuit_breakers"]:
            state = "🟢" if cb["state"] == "CLOSED" else "🔴" if cb["state"] == "OPEN" else "🟡"
            print(f"  {state} {cb['name']}: {cb['state']} (failures: {cb['failure_count']})")
        
        print("-" * 40)
        time.sleep(1)

if __name__ == "__main__":
    # Даем сервису время на запуск
    print("Waiting for payment service to start...")
    time.sleep(10)
    
    # Тестируем HTTP endpoints
    test_http_endpoints()
    
    # Мониторим Circuit Breaker
    monitor_circuit_breaker()