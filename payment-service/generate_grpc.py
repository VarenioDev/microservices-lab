#!/usr/bin/env python3
import subprocess
import sys
import os

# Генерируем Python код из proto файла
result = subprocess.run([
    sys.executable, '-m', 'grpc_tools.protoc',
    '-I.', '--python_out=.', '--grpc_python_out=.',
    'payment_service.proto'
])

if result.returncode == 0:
    print("Successfully generated gRPC code")
    
    # Патчим импорты в сгенерированном файле
    grpc_file = 'payment_service_pb2_grpc.py'
    if os.path.exists(grpc_file):
        with open(grpc_file, 'r') as f:
            content = f.read()
        
        # Исправляем импорт
        content = content.replace(
            'import payment_service_pb2 as payment__service__pb2',
            'import payment_service_pb2 as payment__service__pb2'
        )
        
        with open(grpc_file, 'w') as f:
            f.write(content)
        
        print(f"Patched {grpc_file}")
else:
    print("Failed to generate gRPC code")
    sys.exit(1)