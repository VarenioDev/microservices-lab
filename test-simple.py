import requests
import time

print("=== Простой тест безопасности ===")

# 1. Логин админа
print("\n1. Логин админа...")
admin_resp = requests.post("http://localhost:8080/auth/token", 
                          params={"username": "admin", "password": "admin123"})
admin_token = admin_resp.json()["access_token"]
print(f"   Токен: {admin_token[:20]}...")

# 2. Логин пользователя
print("\n2. Логин пользователя...")
user_resp = requests.post("http://localhost:8080/auth/token",
                         params={"username": "user", "password": "user123"})
user_token = user_resp.json()["access_token"]
print(f"   Токен: {user_token[:20]}...")

# 3. Пользователь пытается создать товар
print("\n3. Пользователь пытается создать товар...")
resp = requests.post("http://localhost:8080/catalog/products",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={"name": "Test", "price": 100})
if resp.status_code == 403:
    print("   ✓ 403 Forbidden (правильно)")
else:
    print(f"   ✗ Ожидался 403, получили {resp.status_code}")

# 4. Админ создает товар
print("\n4. Админ создает товар...")
resp = requests.post("http://localhost:8080/catalog/products",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"name": "Admin Product", "price": 999})
if resp.status_code == 200:
    print("   ✓ Товар создан")
else:
    print(f"   ✗ Ошибка: {resp.status_code}")

# 5. Rate limiting
print("\n5. Тест rate limiting...")
for i in range(10):
    resp = requests.post("http://localhost:8080/auth/token",
                        params={"username": "test", "password": "wrong"})
    print(f"   Запрос {i+1}: {resp.status_code}")
    if resp.status_code == 429:
        print("   ✓ Rate limiting сработал!")
        break
    time.sleep(0.1)

print("\n=== Готово ===")