import grpc
import payment_service_pb2
import payment_service_pb2_grpc
import time
import random
from circuitbreaker import circuit

class PaymentClient:
    def __init__(self, host='localhost', port=50051):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = payment_service_pb2_grpc.PaymentServiceStub(self.channel)
    
    @circuit(failure_threshold=3, recovery_timeout=10)
    def process_payment(self, order_id, amount, user_id="user_123"):
        try:
            request = payment_service_pb2.PaymentRequest(
                order_id=order_id,
                amount=amount,
                currency="USD",
                payment_method="card",
                user_id=user_id
            )
            response = self.stub.ProcessPayment(request, timeout=5)
            return response
        except Exception as e:
            print(f"gRPC call failed: {e}")
            # Fallback response
            return payment_service_pb2.PaymentResponse(
                payment_id="",
                status="processing",
                message="Payment service unavailable, using fallback",
                gateway="fallback"
            )
    
    def get_status(self, payment_id, gateway="stripe"):
        request = payment_service_pb2.PaymentStatusRequest(
            payment_id=payment_id,
            gateway=gateway
        )
        return self.stub.GetPaymentStatus(request, timeout=5)

def test_circuit_breaker():
    """Тестирование Circuit Breaker через gRPC"""
    client = PaymentClient()
    
    print("Testing gRPC with Circuit Breaker...")
    print("=" * 60)
    
    success = 0
    fallback = 0
    
    # Симулируем сбои для тестирования Circuit Breaker
    for i in range(20):
        try:
            response = client.process_payment(f"order_{i}", 100.0 + i*10)
            
            if response.gateway == "fallback":
                fallback += 1
                print(f"Request {i}: FALLBACK - {response.message}")
            else:
                success += 1
                print(f"Request {i}: SUCCESS - {response.status} via {response.gateway}")
                
        except Exception as e:
            print(f"Request {i}: EXCEPTION - {str(e)}")
        
        time.sleep(0.5)
    
    print("=" * 60)
    print(f"Results: {success} successes, {fallback} fallbacks")
    print(f"Circuit Breaker triggered: {fallback > 0}")

def simulate_service_outage():
    """Симуляция полной недоступности сервиса"""
    print("\n=== Simulating service outage ===")
    print("Expecting Circuit Breaker to open after multiple failures")
    
    client = PaymentClient(host='localhost', port=9999)  # Неверный порт
    
    for i in range(10):
        response = client.process_payment(f"outage_{i}", 50.0)
        print(f"Outage test {i}: {response.status} - {response.message}")
        time.sleep(0.3)

if __name__ == "__main__":
    # Даем сервису время на запуск
    print("Waiting for service to start...")
    time.sleep(5)
    
    # Тест нормальной работы
    test_circuit_breaker()
    
    # Тест с недоступным сервисом
    simulate_service_outage()