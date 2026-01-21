FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV OTEL_SERVICE_NAME=order-service
ENV OTEL_EXPORTER_JAEGER_ENDPOINT=http://jaeger:14268/api/traces
ENV OTEL_TRACES_EXPORTER=jaeger-thrift-splunk

EXPOSE 5000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--proxy-headers"]
