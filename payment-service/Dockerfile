FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python generate_grpc.py

EXPOSE 5000 50051

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]